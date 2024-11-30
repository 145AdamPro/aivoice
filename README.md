# AI Voice Assistant
Add your groq api in .env
A real-time voice assistant that can interact with your computer using the Groq API for natural language processing.

## Features

- Real-time voice recognition
- Natural language processing using Groq AI
- Text-to-speech responses
- Simple keyboard controls (Spacebar to talk, Esc to exit)

## Installation

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Make sure you have your Groq API key in the `.env` file.

## Usage

1. Run the voice assistant:
```bash
python voice_assistant.py
```

2. Controls:
- Press and hold the Spacebar to talk to the assistant
- Release Spacebar when you're done speaking
- Press Esc to exit the program

## Requirements

- Python 3.7+
- Working microphone
- Internet connection for speech recognition and Groq API
- Groq API key

## Note

Make sure your system has a working microphone and speakers. The assistant uses Google's speech recognition service for converting speech to text, so an internet connection is required.
