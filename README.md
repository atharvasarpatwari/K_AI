# KEERTHI AI — Voice Assistant

**K**nowledge-**E**nhanced **E**ngine for **R**eal-**T**ime **H**uman **I**ntelligence.

A conversational voice assistant for Windows powered by **Google Gemini 2.5 Flash**.
It pairs an LLM "brain" with an executive layer that parses `[ACTION:...]` tags to
control a **simulated smart home**, plus console UI, text-to-speech, and optional
speech-to-text.

> Full architecture, configuration reference, and history live in
> [`PROJECT_DOC.md`](PROJECT_DOC.md).

## Features

- **Gemini-powered conversation** — calm, witty, proactive persona.
- **Smart home simulation** — lights, AC, kitchen fan, TV, curtains, water heater, door security, tasks.
- **Timers** — set, check, and cancel timers; expiry announced via speech.
- **Weather reports** — current conditions for your location (Open-Meteo, no API key).
- **State persistence** — smart-home state survives restarts via `keerthi_state.json`.
- **Microphone input** — Google STT by default; offline Vosk (`STT_ENGINE=vosk`) or
  faster-whisper (`STT_ENGINE=whisper`) optional.
- **Text-to-speech** — spoken replies via `pyttsx3`.
- **Safety confirmation** — destructive actions (unlocking the door, removing tasks) ask before executing.
- **Web interface** — chat + live smart-home dashboard (FastAPI + React) with
  WebSocket push for state changes and timer expiries.
- **CI + static checks** — GitHub Actions runs ruff, mypy, 117+ tests, and the web lint/test/build.

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

## Usage

| Command / phrase             | Effect                                            |
| ---------------------------- | ------------------------------------------------- |
| `python main.py`             | Run with microphone input (falls back to typing)  |
| `python main.py --text`      | Force text-input mode                             |
| `python main.py --fresh`     | Ignore saved smart-home state, start fresh        |
| `python main.py --version`   | Print version and exit                            |
| `exit` / `quit` / `shutdown` | Power down                                        |
| `/reset`                     | Clear conversation history                        |
| `"keerthi"` (wake word)      | Acknowledgment                                    |

## Supported Smart-Home Actions

`LIGHT_ON`, `LIGHT_OFF`, `SET_BRIGHTNESS`, `AC_ON`, `AC_OFF`, `SET_TEMP`,
`FAN_ON`, `FAN_OFF`, `FAN_SPEED`, `TV_ON`, `TV_OFF`, `CURTAIN_OPEN`,
`CURTAIN_CLOSE`, `HEATER_ON`, `HEATER_OFF`, `HEATER_TEMP`, `LOCK_DOOR`,
`UNLOCK_DOOR`, `ADD_TASK`, `REMOVE_TASK`, `STATUS_REPORT`, `WEATHER_REPORT`,
`SET_TIMER`, `CANCEL_TIMER`, `CHECK_TIMERS`, `RESET_STATE`

## Configuration (all optional, via `.env`)

`MODEL_NAME`, `TTS_RATE`, `USE_MICROPHONE`, `STT_LANGUAGE`, `STT_ENGINE`,
`VOSK_MODEL_PATH`, `WHISPER_MODEL`, `WHISPER_DEVICE`, `MAX_HISTORY_TURNS`,
`TEMPERATURE`, `MAX_OUTPUT_TOKENS`, `TOP_P`, `LOG_LEVEL`, `STATE_FILE`

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
│   ├── brain.py           KeerthiBrain — Gemini client + history
│   ├── executive.py       ExecutiveOfficer — actions, timers, persistence
│   ├── peripherals.py     PeripheralController — TTS / STT / console
│   ├── nlp.py             intents + manifest builder
│   ├── server.py          FastAPI web backend
│   └── services/weather.py  Open-Meteo weather lookup
├── src/                   React frontend (chat + dashboard)
└── tests/                 103 unit tests (stdlib unittest)
```

## Customization

- **Persona**: edit the system prompt in `keerthi/brain.py`.
- **Smart home**: extend `keerthi/executive.py` handlers; add intents in `keerthi/nlp.py`.
- **Hardware**: update `keerthi/peripherals.py` for your microphone/speaker setup.

---

*Developed for a seamless, proactive AI experience.*
