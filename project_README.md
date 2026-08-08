# KEERTHI AI Voice Assistant (Python Suite)

A highly advanced, conversational voice assistant powered by **Gemini 1.5 Flash**.

## Features
- **Intelligent Conversations**: Powered by Google's state-of-the-art LLMs.
- **Executive Logic**: Capable of "parsing intent" from conversational speech (e.g., controlling a simulated smart home).
- **Proactive Personality**: Configured with a calm, witty, and helpful persona.
- **Modular Design**: Clean separation between AI Brain, Peripherals, and Executive Logic.

## Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set your API Key in a `.env` file:
   ```env
   GEMINI_API_KEY=your_key_here
   ```

3. Run the assistant:
   ```bash
   python main.py
   ```

## Customization
- **Persona**: Modify `keerthi/brain.py` system prompt.
- **Smart Home**: Extend `keerthi/executive.py` with real IoT integrations.
- **Hardware**: Update `keerthi/peripherals.py` for specific microphone or speaker setups.

---
*Developed for a seamless, proactive AI experience.*
