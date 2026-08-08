# KEERTHI AI Voice Assistant (Python Suite)

A highly advanced, conversational voice assistant powered by **Gemini 1.5 Flash**.

## Features
- **Intelligent Conversations**: Powered by Google's state-of-the-art LLMs.
- **Executive Logic**: Capable of "parsing intent" from conversational speech (e.g., controlling a simulated smart home).
- **Proactive Personality**: Configured with a calm, witty, and helpful persona.
- **Modular Design**: Clean separation between AI Brain, Peripherals, and Executive Logic.
- **Smart Home Simulation**: Lights, AC, kitchen fan, and door security controlled via `[ACTION:...]` tags.
- **State Persistence**: Smart-home state survives restarts via `keerthi_state.json`.
- **Microphone Input**: Optional speech-to-text via `SpeechRecognition` (falls back to text input).
- **Conversation Management**: `/reset` clears context; wake words acknowledged.

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

## Usage

| Command / phrase          | Effect                                             |
| ------------------------- | -------------------------------------------------- |
| `python main.py`          | Run with microphone input (falls back to typing)   |
| `python main.py --text`   | Force text-input mode                              |
| `python main.py --fresh`  | Ignore saved smart-home state, start fresh         |
| `python main.py --version`| Print version and exit                             |
| `exit` / `quit`           | Power down                                         |
| `/reset`                  | Clear conversation history                         |
| `"keerthi"`               | Wake-word acknowledgment                           |

## Supported Smart-Home Actions
`LIGHT_ON`, `LIGHT_OFF`, `SET_BRIGHTNESS`, `AC_ON`, `AC_OFF`, `SET_TEMP`,
`FAN_ON`, `FAN_OFF`, `FAN_SPEED`, `LOCK_DOOR`, `UNLOCK_DOOR`,
`ADD_TASK`, `REMOVE_TASK`, `STATUS_REPORT`

## Configuration (all optional, via `.env`)
`MODEL_NAME`, `TTS_RATE`, `USE_MICROPHONE`, `STT_LANGUAGE`, `MAX_HISTORY_TURNS`,
`TEMPERATURE`, `MAX_OUTPUT_TOKENS`, `TOP_P`, `LOG_LEVEL`, `STATE_FILE`

## Running Tests
```bash
python -m unittest discover -s tests -v
```

## Customization
- **Persona**: Modify `keerthi/brain.py` system prompt.
- **Smart Home**: Extend `keerthi/executive.py` with real IoT integrations.
- **Hardware**: Update `keerthi/peripherals.py` for specific microphone or speaker setups.

---
*Developed for a seamless, proactive AI experience.*
