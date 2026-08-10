# KEERTHI AI — Project Documentation (for review)

**Document date:** 2026-08-09 · **Version:** 2.1.0 · **Language:** Python 3.13

---

## 1. Overview

KEERTHI (*Knowledge-Enhanced Engine for Real-Time Human Intelligence*) is a
conversational voice assistant for Windows, powered by **Google Gemini 1.5 Flash**.
It combines:

- an LLM "brain" for natural conversation,
- an "executive" layer that parses `[ACTION:...]` tags out of the model's text and
  mutates a **simulated smart home** state,
- a "peripherals" layer for console UI, text-to-speech, and optional speech-to-text.

The smart home is a simulation (no real IoT hardware). State is persisted to a JSON
file so device/task state survives restarts.

---

## 2. Repository Layout

```
E:\KeerthiAI\
├── main.py                       CLI entry point + ConversationSession (loop logic)
├── requirements.txt              Python runtime dependencies
├── requirements-dev.txt          ruff, mypy, types-requests (lint/type-check)
├── requirements-web.txt          fastapi, uvicorn, pydantic, httpx (web server)
├── requirements-stt.txt          vosk (optional offline speech-to-text)
├── pyproject.toml                ruff + mypy configuration
├── project_README.md             Short user-facing README
├── PROJECT_DOC.md                This document
├── README.md                     Primary README
├── metadata.json                 AI Studio app metadata
├── .env.example                  Documented env vars (GEMINI_API_KEY, options)
├── .gitignore                    Ignores .env, state file, build artifacts
├── .github/workflows/ci.yml      GitHub Actions: lint + type-check + tests
├── package.json / tsconfig.json  React/Vite web frontend manifest + TS config
├── vite.config.ts                Vite dev server (proxies /api -> :8000)
├── index.html                    Web app entry HTML
├── src/                          React frontend (chat + smart-home dashboard)
│   ├── main.tsx
│   ├── App.tsx
│   └── index.css
├── KEERTHI_Technical_Report (Repaired).docx   Original project report (untouched)
├── keerthi_state.json            Created at runtime (smart-home persistence)
└── keerthi/
    ├── __init__.py               Empty package marker
    ├── config.py                 CONFIG TypedDict, env helpers, validate_config()
    ├── brain.py                  KeerthiBrain (Gemini client + history)
    ├── executive.py              ExecutiveOfficer (action dispatch + timers + persistence)
    ├── peripherals.py            PeripheralController (TTS/STT/console)
    ├── nlp.py                    COMMAND_INTENTS, SAFETY_INTENTS, get_nlp_manifest()
    ├── server.py                 FastAPI web backend (/api/chat, /api/state, /api/reset)
    └── services/
        ├── __init__.py
        └── weather.py            Open-Meteo weather lookup (geocode + current conditions)
```

`tests/` contains 10 test modules (103 tests, stdlib `unittest`).

---

## 3. Architecture

Clean separation of concerns:

```
                ┌────────────────────────────────────────────┐
 user input ──▶ │  PeripheralController.listen()             │
                │  (mic STT with text fallback)              │
                └─────────────────────┬──────────────────────┘
                                      ▼
                ┌────────────────────────────────────────────┐
                │  ConversationSession.handle_input()        │  (main.py)
                │  - exit / reset / wake-word handling       │
                └─────────────────────┬──────────────────────┘
                                      ▼
                ┌────────────────────────────────────────────┐
                │  KeerthiBrain.generate_response()          │  (keerthi/brain.py)
                │  Gemini + persona + command manifest       │
                │  returns text incl. [ACTION:...] tags      │
                └─────────────────────┬──────────────────────┘
                                      ▼
                ┌────────────────────────────────────────────┐
                │  ExecutiveOfficer.parse_and_execute()      │  (keerthi/executive.py)
                │  runs handlers, updates state, persists    │
                └─────────────────────┬──────────────────────┘
                                      ▼
                ┌────────────────────────────────────────────┐
                │  PeripheralController.speak() + dashboard  │
                └────────────────────────────────────────────┘
```

**Data flow per turn**
1. `listen()` captures a command (microphone STT, else typed text).
2. `handle_input()` short-circuits: exit phrases, empty input, `/reset`, wake words.
3. Otherwise `brain.generate_response(text)` → Gemini reply (may contain `[ACTION:...]` tags).
4. `officer.parse_and_execute(reply)` extracts tags, runs the matching handler, saves state.
5. The cleaned reply is spoken; executed-action confirmations are spoken, then the
   dashboard table is printed if any action ran.

---

## 4. Modules in Detail

### 4.1 `keerthi/config.py`
- `CONFIG` dict — all settings, read from `.env` with defaults (see §5).
- `_env_bool(name, default)` / `_env_int(name, default)` — tolerant env parsing
  (non-numeric ints fall back to default; bool accepts `1/true/yes/on`).
- `INITIAL_STATE` — baseline simulated devices and tasks.
- `validate_config()` — emits `warnings.warn` at startup for: missing API key,
  invalid `LOG_LEVEL`, `TEMPERATURE` outside [0.0, 2.0], non-positive
  `MAX_OUTPUT_TOKENS` / `MAX_HISTORY_TURNS`, `TTS_RATE` outside [50, 400].

### 4.2 `keerthi/brain.py` — `KeerthiBrain`
- **`__init__`**: raises `ValueError` if `GEMINI_API_KEY` missing; builds the
  Gemini client and a generation `config` (system prompt, `temperature`,
  `max_output_tokens`, `top_p`).
- **`_get_system_prompt()`**: persona + operational rules + the command manifest
  from `nlp.get_nlp_manifest()` + user/location context.
- **`generate_response(user_input)`**: appends to history, calls
  `client.models.generate_content`, appends the reply, trims history.
  On any exception it logs (`logger.exception`) and returns a generic message —
  raw errors are **not** leaked to the user.
- **`_trim_history()`**: caps history at `MAX_HISTORY_TURNS * 2` messages (newest kept).
- **`reset_conversation()`**: clears history (used by `/reset`).

### 4.3 `keerthi/executive.py` — `ExecutiveOfficer`
- Owns `state` (a **deep copy** of `INITIAL_STATE`, so instances never share state).
- `parse_and_execute(ai_response)`: regex-extracts `[ACTION:(.*?)]` tags, splits on
  `:`, looks up the handler in `self._handlers` (unknown intents ignored), collects
  confirmation strings, and **persists state** when any action executed.
- Handlers (all typed `(args: list[str]) -> str | None`; `None` = no confirmation):
  - Lighting: `LIGHT_ON`, `LIGHT_OFF`, `SET_BRIGHTNESS` (clamped 0–100; 0 ⇒ off)
  - Climate: `AC_ON`, `AC_OFF`, `SET_TEMP` (defaults 22 when no arg; non-numeric ignored)
  - Fan: `FAN_ON`, `FAN_OFF`, `FAN_SPEED` (clamped 0–5; 0 ⇒ off)
  - Security: `LOCK_DOOR`, `UNLOCK_DOOR`
  - Tasks: `ADD_TASK` (strips whitespace, default "New Task"), `REMOVE_TASK`
    (reports if not found)
  - Reporting: `STATUS_REPORT` (human-readable device + task summary)
- Helpers: `_first_int(args, default=None)` extracts the first integer from args
  (default only applied when args are empty); `_clamp(value, low, high)`.
- Persistence: `_load_state()` on init (ignores missing/corrupt files) and
  `_save_state()` after actions, to `STATE_FILE` (default `keerthi_state.json`).
- Constants: `MAX_FAN_SPEED = 5`, `MAX_BRIGHTNESS = 100`.

### 4.4 `keerthi/peripherals.py` — `PeripheralController`
- `_init_tts()`: initializes `pyttsx3` (guarded), applies `TTS_RATE`; sets
  `tts_available` flag.
- `_init_stt()`: initializes `speech_recognition` Recognizer with
  `energy_threshold`/`dynamic_energy_threshold`; sets `stt_available` flag.
- `speak(text)`: strips `[ACTION:...]` tags, prints a styled `rich` panel, and (if
  available) speaks via pyttsx3.
- `listen(use_microphone=None)`: mic STT first (unless disabled), falls back to
  text `input()` on any failure. Honors `CONFIG["USE_MICROPHONE"]`.
- `_listen_microphone()`: `adjust_for_ambient_noise` → capture → `recognize_google`
  with `STT_LANGUAGE`. Graceful handling of `UnknownValueError` / `RequestError`.
- `close()`: stops the TTS engine (called at end of session).
- `show_dashboard(state)`: prints a status table using `.get('status', 'unknown')`
  so missing keys don't crash.

### 4.5 `keerthi/nlp.py`
- `COMMAND_INTENTS`: 14 intents with descriptions (single source of truth for the
  command library).
- `get_nlp_manifest() -> str`: renders the intents as the `[ACTION]` block injected
  into the system prompt.

### 4.6 `main.py`
- `setup_logging()`: `logging.basicConfig` with `CONFIG["LOG_LEVEL"]`.
- `boot_sequence()`: styled startup banner with brief sleeps.
- `parse_args()`: `--text` (force text input), `--fresh` (ignore saved state),
  `--version`.
- `ConversationSession`:
  - `run()`: greets the user, loops `listen → handle_input` until `"exit"`, and
    always calls `peripherals.close()` via `finally`.
  - `handle_input(text) -> str | None`: single-turn logic; returns `"exit"` to end.
    Handles exit phrases, empty input, `/reset`, wake words, then the normal
    brain → executive → speak → dashboard flow.
- `main()`: parses args, configures logging, runs `validate_config()`, boot, creates
  brain (friendly message + `sys.exit(1)` on missing key), officer (loads state
  unless `--fresh`), peripherals, then runs a `ConversationSession`.
- Top-level: `KeyboardInterrupt` → graceful exit.

---

## 5. Configuration

All optional — read from `.env` (see `.env.example`), with defaults shown:

| Var                | Default           | Purpose                                  |
| ------------------ | ----------------- | ---------------------------------------- |
| `GEMINI_API_KEY`   | *(required)*      | Gemini API key (missing ⇒ startup error) |
| `MODEL_NAME`       | `gemini-1.5-flash`| Gemini model                              |
| `TTS_RATE`         | `175`             | Speech rate (validated 50–400)           |
| `USE_MICROPHONE`   | `true`            | Enable mic STT (falls back to typing)    |
| `STT_LANGUAGE`     | `en-IN`           | Speech-recognition language              |
| `STT_ENGINE`       | `google`          | `google` (online) or `vosk` (offline)    |
| `VOSK_MODEL_PATH`  | `vosk-model-small-en-us-0.15` | Vosk model directory            |
| `MAX_HISTORY_TURNS`| `10`              | Conversation turns retained              |
| `TEMPERATURE`      | `0.7`             | LLM sampling temperature (0.0–2.0)       |
| `MAX_OUTPUT_TOKENS`| `1024`            | Max tokens per reply                     |
| `TOP_P`            | `0.95`            | Nucleus sampling (validated 0.0–1.0)     |
| `LOG_LEVEL`        | `INFO`            | Python logging level                     |
| `STATE_FILE`       | `keerthi_state.json` | Persistence file path                 |

---

## 6. CLI Usage

```bash
python main.py                # run (mic → text fallback)
python main.py --text         # force text input
python main.py --fresh        # start with default state (ignore saved)
python main.py --version      # print "KEERTHI v2.0.0" and exit
```

In-session commands: `exit` / `quit` / `shutdown` (power down), `/reset`
(clear conversation), any wake word from `WAKE_WORDS` (acknowledgement only).

---

## 7. Smart-Home Intents

| Intent           | Arg (optional) | Effect / confirmation                        |
| ---------------- | -------------- | -------------------------------------------- |
| `LIGHT_ON`       | –              | living_room_light → on                       |
| `LIGHT_OFF`      | –              | living_room_light → off                      |
| `SET_BRIGHTNESS` | `0–100`        | set brightness; 0 ⇒ off, clamped             |
| `AC_ON`          | –              | bedroom_ac → on                              |
| `AC_OFF`         | –              | bedroom_ac → off                             |
| `SET_TEMP`       | `number`       | set AC temp (default 22; non-numeric ignored)|
| `FAN_ON`         | –              | kitchen_fan → on                             |
| `FAN_OFF`        | –              | kitchen_fan → off                            |
| `FAN_SPEED`      | `0–5`          | set speed (clamped); 0 ⇒ off                 |
| `LOCK_DOOR`      | –              | main_door → locked                           |
| `UNLOCK_DOOR`    | –              | main_door → unlocked *(SAFETY — needs confirmation)* |
| `ADD_TASK`       | `name`         | append task (stripped; default "New Task")   |
| `REMOVE_TASK`    | `name`         | remove task *(SAFETY — needs confirmation)*  |
| `STATUS_REPORT`  | –              | speak full device + task summary             |
| `WEATHER_REPORT` | –              | current weather for `LOCATION` (Open-Meteo)  |
| `TV_ON` / `TV_OFF` | –           | living_room_tv → on / off                    |
| `CURTAIN_OPEN` / `CURTAIN_CLOSE` | – | bedroom_curtains → open / closed        |
| `HEATER_ON` / `HEATER_OFF` | –   | bathroom_heater → on / off                   |
| `HEATER_TEMP`    | `0–50`          | set heater temp (clamped); 0 ⇒ off          |
| `RESET_STATE`    | –              | restore all devices/tasks/timers to defaults |
| `SET_TIMER`      | `seconds`      | schedule a timer (e.g. `SET_TIMER:90`)      |
| `CANCEL_TIMER`   | `index`/`label`| cancel a pending timer                       |
| `CHECK_TIMERS`   | –              | report pending timers with time remaining    |

Example model output: `"Turning things on for you. [ACTION:LIGHT_ON][ACTION:AC_ON]"`

---

## 8. Persistence

- After any successfully executed action, `ExecutiveOfficer` writes `state` to
  `STATE_FILE` (`keerthi_state.json`) as JSON.
- On startup, `ExecutiveOfficer.__init__` loads the file if present.
- Missing or corrupt files are silently ignored (start from `INITIAL_STATE`).
- `--fresh` forces a clean start (`load_state=False`).
- The file is git-ignored (runtime data, may contain no secrets but is user-local).

---

## 9. Testing

Run: `python -m unittest discover -s tests -v` (stdlib, no extra deps). **103 tests, all passing.**

| File                  | # Tests | Covers                                                         |
| --------------------- | ------- | -------------------------------------------------------------- |
| `test_executive.py`   | ~42     | every intent, clamping, defaults, safety confirmation, timers, weather provider, reset |
| `test_persistence.py` | 4       | save/reload, `--fresh`, missing file, corrupt file             |
| `test_config.py`      | 9       | `validate_config` warnings; `_env_bool`/`_env_int` parsing     |
| `test_nlp.py`         | 4       | manifest contents, intent key set, safety markers              |
| `test_brain.py`       | 10      | `_trim_history` + mocked Gemini transport (no live API)        |
| `test_session.py`     | 11      | `handle_input` / `run`, confirmation callback wiring           |
| `test_peripherals.py` | 6       | STT engine routing, Vosk transcription parsing                 |
| `test_weather.py`     | 5       | Open-Meteo geocode/forecast (mocked HTTP)                      |
| `test_server.py`      | 6       | FastAPI `/api/chat`, `/api/state`, `/api/reset` (TestClient)   |

Brain/Gemini live calls are **not** tested (need a real API key), but the transport is
fully mocked in `test_brain.py` and `test_server.py`.

## 10. Improvement History

**Round 1 — Bug fixes** (made the project runnable):
- `exeutive.py` (typo) → `executive.py`; import in `main.py` fixed.
- `nlp.py` had been overwritten with a duplicate class → restored `COMMAND_INTENTS`
  + `get_nlp_manifest()`; fixed circular self-imports.
- Removed duplicate `def main()` in `main.py` (boot sequence was shadowed).

**Round 2 — Reliability & quality:**
- TTS rate now applied; removed dead imports; mic STT implemented with fallback.
- API-key startup handled gracefully; `/reset`, `--text`, `--version`.
- History capped; raw Gemini errors no longer spoken; action confirmations spoken.
- Typed method signatures; dispatch table refactor; deep-copied initial state.
- Added 21 stdlib unit tests.

**Round 3 — Features & polish:**
- 8 new smart-home intents with clamping/validation.
- State persistence + `--fresh` flag.
- `validate_config()` startup checks; env-overridable settings.
- `ConversationSession` refactor for a testable loop; `close()` releases TTS.
- Ambient-noise calibration in STT; safer dashboard.
- Docs: README + this document. Tests grown to 53.

**Round 4 — Hardening, features & web interface (current):**
- **Tooling**: ruff + mypy (strict) via `pyproject.toml`, `requirements-dev.txt`,
  GitHub Actions CI (lint + type-check + 103 tests). Code is fully statically checked.
- **Config robustness**: tolerant `_env_float` (no more crash on bad `TEMPERATURE`/`TOP_P`);
  `CONFIG` is now a typed `TypedDict`; new `TOP_P`/`STT_ENGINE` validation warnings.
- **Git hygiene**: `__pycache__`/`*.pyc` ignored and untracked; corrupt `README.md` replaced.
- **Safety**: `SAFETY_INTENTS` (`UNLOCK_DOOR`, `REMOVE_TASK`) gated behind an interactive
  confirmation prompt in the CLI; the web API returns `needsConfirmation`.
- **New devices**: TV, curtains, bathroom water heater (+ `RESET_STATE`).
- **Timers**: `SET_TIMER`/`CANCEL_TIMER`/`CHECK_TIMERS` with a background scheduler
  thread that announces expiry via TTS; state persisted.
- **Offline STT**: optional `STT_ENGINE=vosk` (see `requirements-stt.txt`) with graceful
  fallback to Google.
- **Weather**: `WEATHER_REPORT` intent via Open-Meteo (no API key) in `keerthi/services/weather.py`.
- **Web interface**: FastAPI backend (`keerthi/server.py`) + React/Vite frontend (`src/`)
  with chat, confirmation flow, and a live smart-home dashboard.
- Windows UTF-8 console handling (`chcp 65001`). Tests grown to 103.

---

## 11. Known Limitations / Future Work

- **Simulated hardware only** — `executive.py` handlers are the IoT integration point.
- **Google STT needs internet** — offline Vosk supported via `STT_ENGINE=vosk`, but it
  needs a model download and `pip install -r requirements-stt.txt`.
- **Gemini live calls untested** — transport is mocked in tests; live calls need a key.
- **Timer expiry is non-persistent at fire-time** — scheduled timers survive restarts in
  state, but a timer that expires while the process is down fires on next poll.
- **Weather needs internet** — Open-Meteo is free and keyless but requires connectivity.
- **Web server is stateful in-process** — `keerthi/server.py` keeps brain/officer as
  module singletons; multiple workers would need a shared store.
- Windows console may render `°C` / unicode inconsistently depending on codepage
  (mitigated by `chcp 65001` on startup).

*End of document.*
