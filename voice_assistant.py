import speech_recognition as sr
import pyttsx3
import os
import keyboard
import json
from groq import Groq
from dotenv import load_dotenv
import subprocess
import webbrowser
import pyautogui
import sys
import winreg
import ctypes
from datetime import datetime
from googlesearch import search
import requests
from bs4 import BeautifulSoup
import wikipedia
import re
import threading
import queue
import signal

# Load environment variables
load_dotenv()

class WebSearch:
    @staticmethod
    def google_search(query, num_results=5):
        """Perform a Google search and return results"""
        try:
            search_results = []
            for url in search(query, num_results=num_results):
                search_results.append(url)
            return search_results
        except Exception as e:
            print(f"Google search error: {str(e)}")
            return []

    @staticmethod
    def get_webpage_content(url):
        """Extract text content from a webpage"""
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            response = requests.get(url, headers=headers, timeout=5)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text and clean it
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            # Limit text length
            return text[:1000]
        except Exception as e:
            print(f"Webpage extraction error: {str(e)}")
            return ""

    @staticmethod
    def search_wikipedia(query):
        """Search Wikipedia for information"""
        try:
            # Search Wikipedia
            result = wikipedia.summary(query, sentences=3)
            return result
        except Exception as e:
            print(f"Wikipedia search error: {str(e)}")
            return ""

class SystemCommands:
    @staticmethod
    def get_chrome_path():
        """Get the Chrome browser path"""
        try:
            # Common Chrome installation paths
            chrome_paths = [
                os.path.join(os.environ.get('PROGRAMFILES', ''), 'Google/Chrome/Application/chrome.exe'),
                os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), 'Google/Chrome/Application/chrome.exe'),
                os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google/Chrome/Application/chrome.exe')
            ]
            
            for path in chrome_paths:
                if os.path.exists(path):
                    return path
            return None
        except Exception:
            return None

    @staticmethod
    def open_application(app_name):
        try:
            if "chrome" in app_name.lower():
                chrome_path = SystemCommands.get_chrome_path()
                if chrome_path:
                    subprocess.Popen(chrome_path)
                    return "Opening Chrome"
                return "Chrome not found. Please make sure it's installed."
            elif "notepad" in app_name.lower():
                subprocess.Popen("notepad.exe")
                return "Opening Notepad"
            elif "calculator" in app_name.lower():
                subprocess.Popen("calc.exe")
                return "Opening Calculator"
            else:
                subprocess.Popen(app_name)
                return f"Opening {app_name}"
        except Exception as e:
            return f"Failed to open {app_name}: {str(e)}"

    @staticmethod
    def open_website(url):
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        webbrowser.open(url)
        return f"Opening {url}"
    
    @staticmethod
    def control_volume(action):
        if action == "mute":
            pyautogui.press('volumemute')
        elif action == "up":
            pyautogui.press('volumeup')
        elif action == "down":
            pyautogui.press('volumedown')
        return f"Volume {action}"
    
    @staticmethod
    def control_media(action):
        if action in ["play", "pause", "next", "previous"]:
            pyautogui.press(f"media{action}")
            return f"Media {action}"
        return "Invalid media command"
    
    @staticmethod
    def create_folder(path):
        try:
            os.makedirs(path, exist_ok=True)
            return f"Created folder at {path}"
        except Exception as e:
            return f"Failed to create folder: {str(e)}"
    
    @staticmethod
    def get_system_info():
        info = []
        info.append(f"OS: {os.name}")
        info.append(f"System: {sys.platform}")
        info.append(f"Current Directory: {os.getcwd()}")
        return "\n".join(info)
    
    @staticmethod
    def lock_computer():
        ctypes.windll.user32.LockWorkStation()
        return "Computer locked"
    
    @staticmethod
    def shutdown_computer():
        os.system("shutdown /s /t 60")
        return "Computer will shutdown in 60 seconds. Say 'cancel shutdown' to abort."
    
    @staticmethod
    def cancel_shutdown():
        os.system("shutdown /a")
        return "Shutdown cancelled"

class VoiceAssistant:
    def __init__(self):
        # Initialize the speech recognizer
        self.recognizer = sr.Recognizer()
        
        # Initialize text-to-speech engine
        self.speaker = pyttsx3.init()
        
        # Initialize Groq client
        self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        
        # Initialize system commands and web search
        self.system = SystemCommands()
        self.web_search = WebSearch()
        
        # Set the assistant's voice properties
        voices = self.speaker.getProperty('voices')
        self.speaker.setProperty('voice', voices[1].id)  # Index 1 is usually a female voice
        self.speaker.setProperty('rate', 180)  # Speed of speech
        
        # Control flags
        self.is_active = True
        self.is_speaking = False
        self.should_stop_speaking = False
        
        # Conversation memory
        self.conversation_history = []
        
        # Setup keyboard event handlers
        keyboard.on_press_key('space', self.on_space_press)
        keyboard.on_release_key('space', self.on_space_release)
        keyboard.on_press_key('esc', self.on_esc_press)
        
        # Speech queue for interrupt handling
        self.speech_queue = queue.Queue()
        self.speech_thread = None
    
    def on_space_press(self, event):
        """Handle spacebar press event"""
        if self.is_speaking:
            self.interrupt_speech()
    
    def on_space_release(self, event):
        """Handle spacebar release event"""
        pass
    
    def on_esc_press(self, event):
        """Handle escape key press event"""
        print("Exiting voice assistant...")
        self.is_active = False
        self.interrupt_speech()
        os._exit(0)
    
    def interrupt_speech(self):
        """Interrupt current speech"""
        self.should_stop_speaking = True
        self.speaker.stop()
        self.is_speaking = False
        with self.speech_queue.mutex:
            self.speech_queue.queue.clear()
    
    def speak(self, text):
        """Convert text to speech with interrupt support"""
        if not self.is_active:
            return
            
        print(f"Assistant: {text}")
        
        # Add text to speech queue
        self.speech_queue.put(text)
        
        # Start speech thread if not already running
        if not self.speech_thread or not self.speech_thread.is_alive():
            self.speech_thread = threading.Thread(target=self._process_speech_queue)
            self.speech_thread.daemon = True
            self.speech_thread.start()
    
    def _process_speech_queue(self):
        """Process speech queue in a separate thread"""
        while self.is_active:
            try:
                # Get text from queue
                text = self.speech_queue.get(timeout=0.1)
                
                # Reset stop flag
                self.should_stop_speaking = False
                self.is_speaking = True
                
                # Split text into sentences for better interrupt handling
                sentences = re.split('[.!?]+', text)
                
                for sentence in sentences:
                    if sentence.strip():
                        if self.should_stop_speaking:
                            break
                            
                        self.speaker.say(sentence.strip())
                        self.speaker.runAndWait()
                
                self.is_speaking = False
                self.speech_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Speech error: {str(e)}")
                self.is_speaking = False
    
    def listen(self):
        """Listen for user input through microphone"""
        with sr.Microphone() as source:
            print("Listening...")
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            try:
                audio = self.recognizer.listen(source, timeout=5)
                text = self.recognizer.recognize_google(audio)
                print(f"You said: {text}")
                return text.lower()
            except sr.WaitTimeoutError:
                return ""
            except sr.UnknownValueError:
                return ""
            except sr.RequestError:
                self.speak("Sorry, there was an error with the speech recognition service.")
                return ""

    def add_to_conversation(self, role, content):
        """Add a message to the conversation history"""
        self.conversation_history.append({"role": role, "content": content})
        # Keep only the last 10 messages to maintain context without using too much memory
        if len(self.conversation_history) > 10:
            self.conversation_history = self.conversation_history[-10:]

    def get_ai_response(self, user_input):
        """Get a response from the AI model"""
        # Add user input to conversation
        self.add_to_conversation("user", user_input)
        
        # Create the system message
        system_message = {
            "role": "system",
            "content": """You are a helpful and friendly AI assistant named Alex. You should:
            1. Be conversational and engaging
            2. Maintain context of the conversation
            3. Ask follow-up questions when appropriate
            4. Be concise but informative
            5. Show personality and empathy
            6. If you don't know something, be honest about it
            7. Use appropriate tone based on the context"""
        }
        
        # Create the messages list with system message and conversation history
        messages = [system_message] + self.conversation_history
        
        try:
            # Get response from Groq
            chat_completion = self.groq_client.chat.completions.create(
                messages=messages,
                model="mixtral-8x7b-32768",
                temperature=0.7,
                max_tokens=800,
            )
            
            response = chat_completion.choices[0].message.content
            
            # Add AI response to conversation
            self.add_to_conversation("assistant", response)
            
            return response
        except Exception as e:
            print(f"Error getting AI response: {str(e)}")
            return "I apologize, but I'm having trouble thinking right now. Could you please try again?"

    def execute_system_command(self, command):
        """Execute system commands based on voice input"""
        if "search" in command or "look up" in command or "tell me about" in command:
            # Extract the search query
            search_terms = ["search", "look up", "tell me about"]
            for term in search_terms:
                if term in command:
                    query = command.split(term)[-1].strip()
                    break
            
            result = self.search_and_summarize(query)
            if result:
                return result
            return "I couldn't find any relevant information."

        if "open" in command:
            if "chrome" in command or "browser" in command:
                return self.system.open_application("chrome")
            elif "notepad" in command:
                return self.system.open_application("notepad")
            elif "calculator" in command:
                return self.system.open_application("calculator")
            elif "website" in command:
                url = command.split("website")[-1].strip()
                return self.system.open_website(url)
                
        elif "volume" in command:
            if "up" in command:
                return self.system.control_volume("up")
            elif "down" in command:
                return self.system.control_volume("down")
            elif "mute" in command:
                return self.system.control_volume("mute")
                
        elif "media" in command:
            if "play" in command or "pause" in command:
                return self.system.control_media("playpause")
            elif "next" in command:
                return self.system.control_media("next")
            elif "previous" in command:
                return self.system.control_media("previous")
                
        elif "create folder" in command:
            folder_name = command.split("create folder")[-1].strip()
            path = os.path.join(os.path.expanduser("~"), "Desktop", folder_name)
            return self.system.create_folder(path)
            
        elif "system info" in command:
            return self.system.get_system_info()
            
        elif "lock computer" in command:
            return self.system.lock_computer()
            
        elif "shutdown" in command:
            if "cancel" in command:
                return self.system.cancel_shutdown()
            return self.system.shutdown_computer()
            
        return None

    def search_and_summarize(self, query):
        """Search the web and summarize information"""
        # Try Wikipedia first
        wiki_result = self.web_search.search_wikipedia(query)
        if wiki_result:
            return f"According to Wikipedia: {wiki_result}"

        # If no Wikipedia result, try Google search
        urls = self.web_search.google_search(query, num_results=3)
        if not urls:
            return None

        # Get content from the first successful URL
        for url in urls:
            content = self.web_search.get_webpage_content(url)
            if content:
                # Use Groq to summarize the content
                summary_prompt = f"Summarize this text in a clear and concise way: {content}"
                
                chat_completion = self.groq_client.chat.completions.create(
                    messages=[
                        {
                            "role": "user",
                            "content": summary_prompt
                        }
                    ],
                    model="mixtral-8x7b-32768",
                    temperature=0.7,
                    max_tokens=200,
                )
                
                summary = chat_completion.choices[0].message.content
                return f"Based on my search: {summary}"

        return None

    def process_command(self, command):
        """Process the voice command using Groq API or system commands"""
        if not command:
            return
            
        # First try to execute system command
        system_response = self.execute_system_command(command)
        if system_response:
            self.speak(system_response)
            return
            
        # If not a system command, get AI response
        response = self.get_ai_response(command)
        self.speak(response)

    def run(self):
        """Main loop for the voice assistant"""
        self.speak("Hello! I'm Alex, your AI assistant. Press and hold the spacebar to talk to me. Press Esc to exit.")
        self.speak("You can interrupt me anytime by pressing the spacebar.")
        self.speak("Try asking me anything or give me commands like: Open chrome, Search for news, or Tell me about yourself!")
        
        while self.is_active:
            try:
                # Wait for spacebar to be pressed
                keyboard.wait('space')
                if not self.is_active:
                    break
                
                # Listen while spacebar is held
                command = self.listen()
                
                # Process the command
                if command:
                    self.process_command(command)
                    
            except Exception as e:
                print(f"Error: {str(e)}")
                self.speak("Sorry, something went wrong. Please try again.")

if __name__ == "__main__":
    # Handle Ctrl+C gracefully
    def signal_handler(signum, frame):
        print("\nExiting voice assistant...")
        os._exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    assistant = VoiceAssistant()
    assistant.run()
