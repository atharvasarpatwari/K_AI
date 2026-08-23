# KEERTHI AI — Voice Assistant

**K**nowledge-**E**nhanced **E**ngine for **R**eal-**T**ime **H**uman **I**ntelligence.

A conversational voice assistant for Windows powered by **Google Gemini 3.5 Flash**.
It pairs an LLM "brain" with an executive layer that parses `[ACTION:...]` tags to
operate **the computer it runs on** — live system metrics, process control, app
launching, commands, and file browsing — plus console UI, text-to-speech, and optional
speech-to-text.

> Full architecture, configuration reference, and history live in
> [`PROJECT_DOC.md`](PROJECT_DOC.md).

## Features

- **Gemini-powered conversation** — calm, witty, proactive persona.
- **Full machine access** — live CPU/memory/disk/battery metrics, top-CPU process
  listing, process termination, known-app launcher, command runner, and file browsing.
- **Input automation** — type text, press hotkeys, move/click/scroll the mouse
  (pyautogui, safety-confirmed).
- **Screen analysis** — capture screenshots and have the model describe what is on
  the screen (Gemini vision via `READ_SCREEN`).
- **Power & display control** — shutdown, restart, sleep, lock screen, volume,
  mute, and brightness.
- **Window management** — list, focus, minimize, maximize, and close open windows.
- **Browser automation** — open URLs and run web searches in the default browser.
- **Timers** — set, check, and cancel timers; expiry announced via speech.
- **Weather reports** — current conditions for your location (Open-Meteo, no API key).
- **State persistence** — task/timer state survives restarts via `keerthi_state.json`.
- **Microphone input** — Google STT by default; offline Vosk (`STT_ENGINE=vosk`) or
  faster-whisper (`STT_ENGINE=whisper`) optional.
- **Text-to-speech** — spoken replies via `pyttsx3`.
- **Safety confirmation** — destructive actions (killing processes, running commands,
  typing/clicking, power control, closing windows, removing tasks) ask before executing.
- **Web interface** — chat + live system dashboard (FastAPI + React) with
  WebSocket push for state changes and timer expiries.
- **CI + static checks** — GitHub Actions runs ruff, mypy, 276+ tests, and the web lint/test/build.
- **Streaming chat** — replies stream into the web UI in real time over WebSocket.
- **Optional token auth** — secure the API/WebSocket with `KEERTHI_API_TOKEN` (`X-API-Token` header or `?token=` query).
- **Memory** — KEERTHI remembers key facts about you; add/remove them from the dashboard Memory panel.
- **Scheduled tasks** — queue commands to run at a time (HH:MM) or relative delay (`in:N:unit`).
- **Macro recorder** — record and replay keyboard/mouse macros (pynput/pyautogui).
- **App installer** — install apps via winget (e.g. "install 7zip").
- **Monitor-aware windows** — move windows to coordinates or to another monitor.
- **System tray** — run `main.py --tray` for a background tray icon with dashboard + quit menu.
- **Progressive Web App** — installable dashboard with offline shell (`manifest.webmanifest` + service worker).
- **Native Android app** — `KeerthiAndroid/` is a Kotlin/Compose rebuild of KEERTHI for phones:
  same persona, same `[ACTION:...]` protocol; real timers/scheduled reminders (`AlarmManager`,
  survive reboot), tasks, memory facts, macros, app/URL launching, volume/brightness, screen
  lock (device admin), weather, voice in/out, and honest refusals for what stock Android forbids
  (killing other processes, shell commands, key/mouse simulation).

## Installation

```bash
pip install -r requirements.txt            # runtime
pip install -r requirements-dev.txt        # dev tooling (ruff, mypy)
```

Set your API key in a `.env` file:

```env
GEMINI_API_KEY=your_key_here
```

### Web interface

```bash
pip install -r requirements-web.txt
uvicorn keerthi.server:app --reload --workers 1   # API on :8000 (single worker)
npm install                                       # frontend (first time only)
npm run dev                                       # app on http://localhost:3000
```

State and pending confirmations live in-process, so run the API with `--workers 1`.
`GET /api/health` reports readiness; `GET /api/ws` streams live state and timer
expiries to the dashboard.

### Android app

```bash
cd KeerthiAndroid
gradlew.bat assembleDebug        # Windows  (./gradlew assembleDebug elsewhere)
adb install -r app\build\outputs\apk\debug\app-debug.apk
```

Or open the `KeerthiAndroid` folder in Android Studio and press Run (device/emulator,
API 26+). Paste your own Gemini key into the app's Settings tab — nothing is baked in.
See [`KeerthiAndroid/README.md`](KeerthiAndroid/README.md) for what's real vs. simulated.

## Usage

| Command / phrase             | Effect                                            |
| ---------------------------- | ------------------------------------------------- |
| `python main.py`             | Run with microphone input (falls back to typing)  |
| `python main.py --text`      | Force text-input mode                             |
| `python main.py --fresh`     | Ignore saved task/timer state, start fresh      |
| `python main.py --tray`      | Also run a system-tray icon with dashboard/quit |
| `python main.py --version`   | Print version and exit                            |
| `exit` / `quit` / `shutdown` | Power down                                        |
| `/reset`                     | Clear conversation history                        |
| `"keerthi"` (wake word)      | Acknowledgment                                    |

## Supported System Actions

`SYSTEM_STATUS`, `CPU_USAGE`, `MEMORY_USAGE`, `DISK_USAGE`, `BATTERY_STATUS`,
`LIST_PROCESSES`, `KILL_PROCESS`, `OPEN_APP`, `RUN_COMMAND`, `FILE_LIST`,
`OPEN_FILE`, `ADD_TASK`, `REMOVE_TASK`, `STATUS_REPORT`, `WEATHER_REPORT`,
`SET_TIMER`, `CANCEL_TIMER`, `CHECK_TIMERS`, `RESET_STATE`,
`TYPE_TEXT`, `PRESS_KEYS`, `MOVE_MOUSE`, `CLICK_MOUSE`, `SCROLL_MOUSE`,
`TAKE_SCREENSHOT`, `READ_SCREEN`, `SHUTDOWN`, `RESTART`, `SLEEP`, `LOCK_SCREEN`,
`SET_VOLUME`, `MUTE`, `SET_BRIGHTNESS`, `LIST_WINDOWS`, `FOCUS_WINDOW`,
`MINIMIZE_WINDOW`, `MAXIMIZE_WINDOW`, `CLOSE_WINDOW`, `OPEN_URL`, `WEB_SEARCH`,
`SAVE_FACT`, `LIST_FACTS`, `MACRO_RECORD`, `MACRO_STOP`, `MACRO_REPLAY`,
`MACRO_LIST`, `MACRO_DELETE`, `SCHEDULE_TASK`, `CANCEL_SCHEDULED`,
`LIST_SCHEDULED`, `INSTALL_APP`, `MOVE_WINDOW`, `MOVE_WINDOW_TO_MONITOR`

## Configuration (all optional, via `.env`)

`MODEL_NAME`, `TTS_RATE`, `USE_MICROPHONE`, `STT_LANGUAGE`, `STT_ENGINE`,
`VOSK_MODEL_PATH`, `WHISPER_MODEL`, `WHISPER_DEVICE`, `MAX_HISTORY_TURNS`,
`TEMPERATURE`, `MAX_OUTPUT_TOKENS`, `TOP_P`, `LOG_LEVEL`, `STATE_FILE`,
`SCREENSHOT_DIR`, `LOG_FILE`, `MACRO_FILE`, `MEMORY_FILE`, `DASHBOARD_URL`,
`KEERTHI_API_TOKEN`, `USE_FUNCTION_CALLING`, `GEMINI_MAX_RETRIES`,
`GEMINI_RETRY_BASE_DELAY`, `GEMINI_RETRY_MAX_DELAY`

## Development

```bash
# run tests
python -m unittest discover -s tests -v

# lint + type-check
ruff check .
mypy

# web type-check + build
npm run lint
npm run build
```

## Project Layout

```
├── main.py                CLI entry point + conversation loop
├── keerthi/
│   ├── config.py          CONFIG TypedDict, env helpers, validation
│   ├── brain.py           KeerthiBrain — Gemini client + history + vision
│   ├── executive.py       ExecutiveOfficer — actions, timers, persistence
│   ├── peripherals.py     PeripheralController — TTS / STT / console
│   ├── nlp.py             intents + manifest builder
│   ├── system.py          real system control (psutil, pyautogui, win32)
│   ├── memory.py          persistent fact store (keerthi_memory.json)
│   ├── macros.py          macro recording + replay (pynput/pyautogui)
│   ├── tray.py            pystray system-tray icon
│   ├── server.py          FastAPI web backend
│   └── services/weather.py  Open-Meteo weather lookup
├── public/                PWA manifest, service worker, app icons
├── src/                   React frontend (chat + system dashboard)
├── tests/                 276 unit tests (stdlib unittest)
└── KeerthiAndroid/        native Android client (Kotlin + Compose, Gradle wrapper included)
```

## Customization

- **Persona**: edit the system prompt in `keerthi/brain.py`.
- **System control**: extend `keerthi/executive.py` handlers + `keerthi/system.py`;
  add intents in `keerthi/nlp.py`.
- **Hardware**: update `keerthi/peripherals.py` for your microphone/speaker setup.

---

*Developed for a seamless, proactive AI experience.*
