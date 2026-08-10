# KEERTHI AI Voice Assistant (Python Suite)

A highly advanced, conversational voice assistant powered by **Gemini 3.5 Flash**.

## Features
- **Intelligent Conversations**: Powered by Google's state-of-the-art LLMs.
- **Executive Logic**: Capable of "parsing intent" from conversational speech (e.g., controlling the computer it runs on).
- **Proactive Personality**: Configured with a calm, witty, and helpful persona.
- **Modular Design**: Clean separation between AI Brain, Peripherals, and Executive Logic.
- **Full Machine Access**: Live CPU/memory/disk/battery metrics, process listing/kill, app launch, command runner, and file browsing via `[ACTION:...]` tags.
- **Input Automation**: Type text, press hotkeys, move/click/scroll the mouse (pyautogui, safety-confirmed).
- **Screen Analysis**: Screenshots and Gemini vision (`READ_SCREEN`) to see and describe the screen.
- **Power & Display**: Shutdown, restart, sleep, lock, volume, mute, and brightness.
- **Window Management**: List, focus, minimize, maximize, and close open windows.
- **Browser Automation**: Open URLs and run web searches in the default browser.
- **State Persistence**: Task/timer state survives restarts via `keerthi_state.json`.
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
| `python main.py --fresh`  | Ignore saved task/timer state, start fresh     |
| `python main.py --version`| Print version and exit                             |
| `exit` / `quit`           | Power down                                         |
| `/reset`                  | Clear conversation history                         |
| `"keerthi"`               | Wake-word acknowledgment                           |

## Supported System Actions
`SYSTEM_STATUS`, `CPU_USAGE`, `MEMORY_USAGE`, `DISK_USAGE`, `BATTERY_STATUS`,
`LIST_PROCESSES`, `KILL_PROCESS`, `OPEN_APP`, `RUN_COMMAND`, `FILE_LIST`,
`OPEN_FILE`, `ADD_TASK`, `REMOVE_TASK`, `STATUS_REPORT`, `WEATHER_REPORT`,
`SET_TIMER`, `CANCEL_TIMER`, `CHECK_TIMERS`, `RESET_STATE`,
`TYPE_TEXT`, `PRESS_KEYS`, `MOVE_MOUSE`, `CLICK_MOUSE`, `SCROLL_MOUSE`,
`TAKE_SCREENSHOT`, `READ_SCREEN`, `SHUTDOWN`, `RESTART`, `SLEEP`, `LOCK_SCREEN`,
`SET_VOLUME`, `MUTE`, `SET_BRIGHTNESS`, `LIST_WINDOWS`, `FOCUS_WINDOW`,
`MINIMIZE_WINDOW`, `MAXIMIZE_WINDOW`, `CLOSE_WINDOW`, `OPEN_URL`, `WEB_SEARCH`

## Configuration (all optional, via `.env`)
`MODEL_NAME`, `TTS_RATE`, `USE_MICROPHONE`, `STT_LANGUAGE`, `STT_ENGINE`,
`VOSK_MODEL_PATH`, `WHISPER_MODEL`, `WHISPER_DEVICE`, `MAX_HISTORY_TURNS`,
`TEMPERATURE`, `MAX_OUTPUT_TOKENS`, `TOP_P`, `LOG_LEVEL`, `STATE_FILE`,
`SCREENSHOT_DIR`

## Running Tests
```bash
python -m unittest discover -s tests -v
```

## Customization
- **Persona**: Modify `keerthi/brain.py` system prompt.
- **System Control**: Extend `keerthi/executive.py` + `keerthi/system.py` with new capabilities.
- **Hardware**: Update `keerthi/peripherals.py` for specific microphone or speaker setups.

---
*Developed for a seamless, proactive AI experience.*
