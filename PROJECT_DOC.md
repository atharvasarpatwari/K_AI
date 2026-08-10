# KEERTHI AI — Project Documentation (for review)

**Document date:** 2026-08-10 · **Version:** 2.4.0 · **Language:** Python 3.13

---

## 1. Overview

KEERTHI (*Knowledge-Enhanced Engine for Real-Time Human Intelligence*) is a
conversational voice assistant for Windows, powered by **Google Gemini 3.5 Flash**.
It combines:

- an LLM "brain" for natural conversation,
- an "executive" layer that parses `[ACTION:...]` tags out of the model's text and
  performs **real operations on the user's computer**,
- a "peripherals" layer for console UI, text-to-speech, and optional speech-to-text.

The assistant has full access to the machine it runs on: it can report live
CPU/memory/disk/battery metrics, list and terminate processes, launch apps, run
commands, browse/open files, automate the keyboard and mouse, capture and analyse
screenshots, control power/volume/brightness, manage open windows, and drive the
browser — with explicit user confirmation for destructive or input-injecting
operations. Task/timer state is persisted to a JSON file so it survives restarts.

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
├── src/                          React frontend (chat + system dashboard)
│   ├── main.tsx
│   ├── App.tsx
│   ├── App.test.tsx
│   └── index.css
├── KEERTHI_Technical_Report (Repaired).docx   Original project report (untouched)
├── keerthi_state.json            Created at runtime (task/timer persistence)
└── keerthi/
    ├── __init__.py               Empty package marker
    ├── config.py                 CONFIG TypedDict, env helpers, validate_config()
    ├── brain.py                  KeerthiBrain (Gemini client + history + vision)
    ├── executive.py              ExecutiveOfficer (action dispatch + timers + persistence)
    ├── peripherals.py            PeripheralController (TTS/STT/console)
    ├── nlp.py                    COMMAND_INTENTS, SAFETY_INTENTS, get_nlp_manifest()
    ├── system.py                 Real system control (psutil + pyautogui + win32)
    ├── server.py                 FastAPI web backend (/api/chat, /api/action, /api/state, ...)
    └── services/
        ├── __init__.py
        └── weather.py            Open-Meteo weather lookup (geocode + current conditions)
```

`tests/` contains 13 test modules (208 tests, stdlib `unittest`).

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
- `INITIAL_STATE` — baseline tasks and timers (no simulated devices).
- `validate_config()` — emits `warnings.warn` at startup for: missing API key,
  invalid `LOG_LEVEL`, `TEMPERATURE` outside [0.0, 2.0], non-positive
  `MAX_OUTPUT_TOKENS` / `MAX_HISTORY_TURNS`, `TTS_RATE` outside [50, 400].

### 4.2 `keerthi/brain.py` — `KeerthiBrain`
- **`__init__`**: raises `ValueError` if `GEMINI_API_KEY` missing; builds the
  Gemini client and a generation `config` (system prompt, `temperature`,
  `max_output_tokens`, `top_p`).
- **`_get_system_prompt()`**: persona + operational rules + the command manifest
  from `nlp.get_nlp_manifest()` + user/location context (includes multi-tag
  chaining and screen-analysis rules).
- **`generate_response(user_input)`**: appends to history, calls
  `client.models.generate_content`, appends the reply, trims history.
  On any exception it logs (`logger.exception`) and returns a generic message —
  raw errors are **not** leaked to the user.
- **`describe_image(image_path)`**: sends a screenshot PNG to the vision model
  (`types.Part.from_bytes`, mime `image/png`) and returns a concise description;
  used as the `READ_SCREEN` provider. Returns `""` on any failure.
- **`_trim_history()`**: caps history at `MAX_HISTORY_TURNS * 2` messages (newest kept).
- **`reset_conversation()`**: clears history (used by `/reset`).

### 4.3 `keerthi/executive.py` — `ExecutiveOfficer`
- Owns `state` (a **deep copy** of `INITIAL_STATE`, so instances never share state).
- `parse_and_execute(ai_response)`: regex-extracts `[ACTION:(.*?)]` tags, splits on
  `:`, looks up the handler in `self._handlers` (unknown intents ignored), collects
  confirmation strings, and **persists state** when any action executed.
- Handlers (all typed `(args: list[str]) -> str | None`; `None` = no confirmation):
  - System status: `SYSTEM_STATUS`, `CPU_USAGE`, `MEMORY_USAGE`, `DISK_USAGE`,
    `BATTERY_STATUS` — live metrics via `keerthi.system.get_metrics()`.
  - Processes: `LIST_PROCESSES` (top-CPU table), `KILL_PROCESS` by PID
    (graceful terminate → force kill) *(SAFETY — needs confirmation)*.
  - Apps & commands: `OPEN_APP` (known launchers + PATH fallback),
    `RUN_COMMAND` (30 s timeout, 4000-char output cap) *(SAFETY — needs
    confirmation)*.
  - Files: `FILE_LIST` (directory listing), `OPEN_FILE` (via `os.startfile`).
  - Tasks: `ADD_TASK` (strips whitespace, default "New Task"), `REMOVE_TASK`
    (reports if not found) *(SAFETY — needs confirmation)*.
  - Reporting: `STATUS_REPORT` (combined system + task summary),
    `WEATHER_REPORT`, `RESET_STATE`, timer intents.
  - Input automation: `TYPE_TEXT`, `PRESS_KEYS`, `MOVE_MOUSE`, `CLICK_MOUSE`,
    `SCROLL_MOUSE` — delegate to `system.type_text`/`press_keys`/`move_mouse`/
    `click_mouse`/`scroll_mouse` *(SAFETY — needs confirmation)*.
  - Screenshots: `TAKE_SCREENSHOT` (saves a PNG, reports the path) and
    `READ_SCREEN` (captures, then asks a vision provider via
    `set_vision_provider` to describe the screen; falls back to the saved path).
  - Power & display: `SHUTDOWN`, `RESTART`, `SLEEP`, `LOCK_SCREEN`
    *(SAFETY — needs confirmation)*, `SET_VOLUME`, `MUTE`, `SET_BRIGHTNESS`.
  - Windows: `LIST_WINDOWS`, `FOCUS_WINDOW`, `MINIMIZE_WINDOW`,
    `MAXIMIZE_WINDOW`, `CLOSE_WINDOW` *(close is SAFETY — needs confirmation)*.
  - Browser: `OPEN_URL`, `WEB_SEARCH`.
- Helpers: `_join_args(args)` rejoins colon-split arguments so Windows paths like
  `C:\Users\me` survive the `[ACTION:...]` tag parser intact.
- `get_summary()` — returns `{system, processes, tasks, timers}` for the web UI.
- Timers: `_prune_stale_timers()` drops timers whose `due` is more than
  `TIMER_STALE_GRACE_SECONDS` (60 s) in the past on startup, so a timer that
  expired while the process was down is dropped instead of firing late. Timer
  list mutations and `_fire_due_timers()` are guarded by a reentrant lock
  (`self._lock`) so the scheduler thread never races the main/web threads.
- Persistence: `_load_state()` on init (ignores missing/corrupt files) and
  `_save_state()` after actions (lock-protected), to `STATE_FILE`
  (default `keerthi_state.json`).

### 4.4 `keerthi/peripherals.py` — `PeripheralController`
- `_init_tts()`: initializes `pyttsx3` (guarded), applies `TTS_RATE`; sets
  `tts_available` flag.
- `_init_stt()`: initializes `speech_recognition` Recognizer with
  `energy_threshold`/`dynamic_energy_threshold`; sets `stt_available` flag.
- `speak(text)`: strips `[ACTION:...]` tags, prints a styled `rich` panel, and (if
  available) speaks via pyttsx3.
- `listen(use_microphone=None)`: mic STT first (unless disabled), falls back to
  text `input()` on any failure. Honors `CONFIG["USE_MICROPHONE"]`.
- `_listen_microphone()`: `adjust_for_ambient_noise` → capture → transcribe.
  Graceful handling of `UnknownValueError` / `RequestError`.
- `_transcribe(audio)`: routes to the configured engine — `google`
  (`recognize_google`), `vosk`, or `whisper` — falling back to Google on empty.
- `_transcribe_vosk(audio)`: lazy `vosk.Model` + `KaldiRecognizer` (16 kHz PCM).
- `_transcribe_whisper(audio)`: lazy `faster_whisper.WhisperModel`
  (`WHISPER_MODEL`/`WHISPER_DEVICE`); converts int16 PCM → float32 via NumPy;
  transcribes with the `STT_LANGUAGE` base code; falls back to Google on error.
- `close()`: stops the TTS engine (called at end of session).
- `show_dashboard(state)`: prints a **System Status** table (CPU/memory/disk
  percentages) using `.get('status', 'unknown')` so missing keys don't crash.

### 4.5 `keerthi/nlp.py`
- `COMMAND_INTENTS`: system intents with descriptions (single source of truth for the
  command library).
- `SAFETY_INTENTS` — `{KILL_PROCESS, RUN_COMMAND, REMOVE_TASK, TYPE_TEXT,
  PRESS_KEYS, MOVE_MOUSE, CLICK_MOUSE, SCROLL_MOUSE, SHUTDOWN, RESTART, SLEEP,
  LOCK_SCREEN, CLOSE_WINDOW}`: destructive or input-injecting operations that
  require explicit user confirmation (CLI prompt / web confirm).
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

### 4.7 `keerthi/server.py` — FastAPI web backend
- Lazy module singletons `_brain` / `_officer` (see §11 limitation: single worker).
- Endpoints:
  - `GET /api/health` — readiness probe (`status`, `version`, `apiKeyPresent`).
  - `GET /api/state` — current system state: live metrics, top processes, tasks, timers.
  - `GET /api/files?path=` — directory listing via `system.list_directory`.
  - `GET /api/screenshot` — returns the most recent screenshot as a PNG
    (`system.latest_screenshot`); 404 when none exists yet.
  - `GET /api/windows` — returns the open top-level windows
    (`system.list_windows`) for the dashboard.
  - `POST /api/action` — executes a single `[ACTION:...]` (e.g. app launcher,
    command runner, file open, timer set) and returns confirmations + fresh state.
  - `POST /api/transcribe` — accepts raw 16 kHz mono int16 PCM audio and returns
    `{text}` using the configured STT engine (google/vosk/whisper). Empty body → 400;
    transcription failure → 422.
  - `POST /api/reset` — clears conversation history.
  - `POST /api/chat` — brain → executive flow. When a reply contains a
    `SAFETY_INTENTS` action and `confirmed` is false, it does **not** execute;
    instead it stores `{reply, intents}` under a single-use `confirmationToken`
    and returns `needsConfirmation: true` (no duplicate LLM call on confirm).
  - `POST /api/confirm` — `{token, confirmed}` executes the **stored** reply's
    intents via `parse_and_execute` without re-generating; unknown tokens → 404;
    `confirmed: false` discards the pending action.
  - `GET /api/ws` — WebSocket pushing `{"type":"state"}` snapshots and
    `{"type":"timer"}` expiry events to connected dashboards.
- `_broadcast` is wired as the officer's notifier; it schedules pushes onto the
  event loop via `asyncio.run_coroutine_threadsafe` (safe from the scheduler thread).
- `startup`/`shutdown` events capture the loop and stop the officer's scheduler
  thread on shutdown.

### 4.8 `keerthi/system.py` — real system control (psutil)
- `get_metrics()`: live CPU %, core count, memory/disk used/total/%, battery
  (percent + charging, absent when no battery), uptime, platform, hostname, Python.
- `list_processes(limit)`: top-CPU processes sorted by CPU (guarded against a
  sampling race that could return a process list in the wrong order).
- `kill_process(pid)`: graceful `terminate()` first, force `kill()` on failure;
  missing pid and denied access reported cleanly.
- `open_app(name)`: known launcher table (notepad, calc, mspaint, explorer, taskmgr,
  cmd, powershell, control, snippingtool) with a PATH-shortcut fallback.
- `run_command(cmd)`: `subprocess.run` with a 30 s timeout and a 4000-char output cap.
- `list_directory(path)`: sorted `{name, isDir, size}` entries for the web file browser.
- `open_file(path)`: opens via `os.startfile`.

**Input automation** (pyautogui, lazy-loaded): `type_text` (with a clipboard-paste
fallback for untypable characters), `press_keys` (splits `ctrl+c` on `+` →
`hotkey`), `move_mouse`, `click_mouse` (coords or current position, any button),
`scroll_mouse` (up/down by clicks). All return `""` on failure or when the
package is unavailable.

**Screenshots** (pyautogui + `SCREENSHOT_DIR`): `take_screenshot()` saves a
timestamped PNG and returns its path; `latest_screenshot()` returns the newest
one (used by the web dashboard).

**Power & display**: `shutdown_system`/`restart_system` (`shutdown /s|/r /t 5`),
`sleep_system`/`lock_screen` (`rundll32`), all via a shared `_run_power_command`.
Volume/mute via `pycaw` (`devices.EndpointVolume`, with a fallback to the older
`Activate` + `QueryInterface` API); `get_volume_state()` feeds the dashboard.
Brightness via PowerShell `WmiMonitorBrightnessMethods.WmiSetBrightness` — may
require admin on some machines and degrades gracefully.

**Window management** (win32gui, lazy-loaded, Windows-only): `list_windows`
(visible top-level windows), `_find_window` (case-insensitive title match),
`focus_window` (restore-if-iconic + `SetForegroundWindow`), `minimize_window` /
`maximize_window` (`ShowWindow`), `close_window` (`PostMessage WM_CLOSE`).

**Browser**: `open_url` (prepends `https://` when no scheme; `webbrowser.open`)
and `web_search` (Google search URL, `urllib.parse.quote`).

---

## 5. Configuration

All optional — read from `.env` (see `.env.example`), with defaults shown:

| Var                | Default           | Purpose                                  |
| ------------------ | ----------------- | ---------------------------------------- |
| `GEMINI_API_KEY`   | *(required)*      | Gemini API key (missing ⇒ startup error) |
| `MODEL_NAME`       | `gemini-3.5-flash`| Gemini model                              |
| `TTS_RATE`         | `175`             | Speech rate (validated 50–400)           |
| `USE_MICROPHONE`   | `true`            | Enable mic STT (falls back to typing)    |
| `STT_LANGUAGE`     | `en-IN`           | Speech-recognition language              |
| `STT_ENGINE`       | `google`          | `google` (online), `vosk`/`whisper` (offline) |
| `VOSK_MODEL_PATH`  | `vosk-model-small-en-us-0.15` | Vosk model directory            |
| `WHISPER_MODEL`    | `small.en`        | faster-whisper model (e.g. `small.en`) |
| `WHISPER_DEVICE`   | `auto`            | faster-whisper device (`auto`/`cpu`/`cuda`) |
| `MAX_HISTORY_TURNS`| `10`              | Conversation turns retained              |
| `TEMPERATURE`      | `0.7`             | LLM sampling temperature (0.0–2.0)       |
| `MAX_OUTPUT_TOKENS`| `1024`            | Max tokens per reply                     |
| `TOP_P`            | `0.95`            | Nucleus sampling (validated 0.0–1.0)     |
| `LOG_LEVEL`        | `INFO`            | Python logging level                     |
| `STATE_FILE`       | `keerthi_state.json` | Persistence file path                 |
| `SCREENSHOT_DIR`   | `screenshots`     | Folder where `TAKE_SCREENSHOT` saves PNGs |

---

## 6. CLI Usage

```bash
python main.py                # run (mic → text fallback)
python main.py --text         # force text input
python main.py --fresh        # start with default state (ignore saved)
python main.py --version      # print "KEERTHI v2.4.0" and exit
```

In-session commands: `exit` / `quit` / `shutdown` (power down), `/reset`
(clear conversation), any wake word from `WAKE_WORDS` (acknowledgement only).

---

## 7. System Intents

| Intent           | Arg (optional) | Effect / confirmation                        |
| ---------------- | -------------- | -------------------------------------------- |
| `SYSTEM_STATUS`  | –              | live CPU / memory / disk / battery summary   |
| `CPU_USAGE`      | –              | CPU % and core count                         |
| `MEMORY_USAGE`   | –              | RAM used/total/%                             |
| `DISK_USAGE`     | –              | disk used/total/%                            |
| `BATTERY_STATUS` | –              | battery % + charging (when present)          |
| `LIST_PROCESSES` | –              | top-CPU processes table                      |
| `KILL_PROCESS`   | `pid`          | terminate → force kill *(SAFETY)*            |
| `OPEN_APP`       | `name`         | launch known app (notepad, calc, …) or PATH  |
| `RUN_COMMAND`    | `cmd`          | run shell command (30 s cap) *(SAFETY)*      |
| `FILE_LIST`      | `path`         | list a directory                             |
| `OPEN_FILE`      | `path`         | open file/folder via `os.startfile`          |
| `ADD_TASK`       | `name`         | append task (stripped; default "New Task")   |
| `REMOVE_TASK`    | `name`         | remove task *(SAFETY)*                       |
| `STATUS_REPORT`  | –              | speak combined system + task summary         |
| `WEATHER_REPORT` | –              | current weather for `LOCATION` (Open-Meteo)  |
| `RESET_STATE`    | –              | restore all tasks/timers to defaults         |
| `SET_TIMER`      | `seconds`      | schedule a timer (e.g. `SET_TIMER:90`)      |
| `CANCEL_TIMER`   | `index`/`label`| cancel a pending timer                       |
| `CHECK_TIMERS`   | –              | report pending timers with time remaining    |
| `TYPE_TEXT`      | `text`         | type text as if on the keyboard *(SAFETY)*   |
| `PRESS_KEYS`     | `combo`        | press a shortcut like `ctrl+c` *(SAFETY)*    |
| `MOVE_MOUSE`     | `x:y`          | move cursor to screen coordinates *(SAFETY)* |
| `CLICK_MOUSE`    | `x:y`/`button` | click at coords or current position *(SAFETY)* |
| `SCROLL_MOUSE`   | `up`/`down`    | scroll the wheel (e.g. `down:5`) *(SAFETY)*  |
| `TAKE_SCREENSHOT`| –              | save a PNG, report the path                  |
| `READ_SCREEN`    | –              | screenshot + Gemini vision description       |
| `SHUTDOWN`       | –              | shut down the computer *(SAFETY)*            |
| `RESTART`        | –              | restart the computer *(SAFETY)*              |
| `SLEEP`          | –              | put the computer to sleep *(SAFETY)*         |
| `LOCK_SCREEN`    | –              | lock the screen *(SAFETY)*                   |
| `SET_VOLUME`     | `0-100`        | set system volume percentage                 |
| `MUTE`           | `on`/`off`     | mute or unmute the system volume             |
| `SET_BRIGHTNESS` | `0-100`        | set screen brightness (WMI)                  |
| `LIST_WINDOWS`   | –              | list open top-level windows                  |
| `FOCUS_WINDOW`   | `title`        | bring a window to the front                  |
| `MINIMIZE_WINDOW`| `title`        | minimize a window                            |
| `MAXIMIZE_WINDOW`| `title`        | maximize a window                            |
| `CLOSE_WINDOW`   | `title`        | close a window *(SAFETY)*                    |
| `OPEN_URL`       | `url`          | open a URL in the default browser            |
| `WEB_SEARCH`     | `query`        | search Google in the default browser         |

Example model output: `"Your CPU is at 42%. [ACTION:CPU_USAGE]"`

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

Run: `python -m unittest discover -s tests -v` (stdlib, no extra deps). **208 tests, all passing.**
Frontend: `npm test` (vitest + Testing Library, 7 tests), `npm run lint` (tsc), `npm run build`.

| File                  | # Tests | Covers                                                         |
| --------------------- | ------- | -------------------------------------------------------------- |
| `test_executive.py`   | ~40     | every system intent, safety confirmation gate, timers + stale-fire pruning, weather provider, reset |
| `test_executive_control.py` | ~35 | new control handlers: input automation, screenshots/vision, power/display, windows, browser, safety gates |
| `test_system.py`      | ~10     | psutil metrics (incl. no-battery), process list/kill, app launch, command run, file browse/open |
| `test_system_control.py` | 39   | pyautogui/win32/pycaw/subprocess helpers incl. error + fallback paths |
| `test_persistence.py` | 4       | save/reload, `--fresh`, missing file, corrupt file             |
| `test_config.py`      | 11      | `validate_config` warnings (incl. retired model); `_env_bool`/`_env_int` parsing |
| `test_nlp.py`         | 4       | manifest contents, intent key set, safety markers              |
| `test_brain.py`       | 13      | `_trim_history`, mocked Gemini transport, `describe_image` vision |
| `test_session.py`     | 11      | `handle_input` / `run`, confirmation callback wiring           |
| `test_peripherals.py` | 10      | STT engine routing (google/vosk/whisper), transcription parsing |
| `test_weather.py`     | 5       | Open-Meteo geocode/forecast (mocked HTTP)                      |
| `test_server.py`      | ~17     | `/api/chat` + confirmation flow, `/api/confirm`, `/api/state`, `/api/action`, `/api/files`, `/api/screenshot`, `/api/windows`, `/api/transcribe`, `/api/reset`, `/api/health` |

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

**Round 5 — Model migration, correctness & platform hardening (v2.2.0):**
- **Gemini migration**: default `MODEL_NAME` moved to `gemini-3.5-flash` (1.5/2.0/2.5-flash
  are retired for new keys and 404); `validate_config` now warns on known-retired model names.
- **Confirmation fix**: the web flow no longer re-runs the LLM on confirm — `/api/chat`
  returns a single-use `confirmationToken`, and `/api/confirm` executes the stored
  intents (no duplicate API call, no reply drift).
- **Robustness**: `SET_TEMP` clamped 16–30; timers that expired while the process was
  down are pruned on load (no stale fires); timer list + persistence guarded by a
  reentrant lock against scheduler-thread races.
- **Web platform**: `/api/health` probe; `/api/ws` WebSocket push for live dashboard
  state and timer expiries; scheduler thread stopped on server shutdown; single-worker
  requirement documented; WebSocket support via `uvicorn[standard]`.
- **Frontend tests**: vitest + Testing Library (chat + confirmation flows); CI now
  runs the web lint/test/build job (`npm ci`).
- **faster-whisper STT**: `STT_ENGINE=whisper` offline transcription
  (`WHISPER_MODEL`/`WHISPER_DEVICE`) alongside Vosk, with Google fallback.
- Docs updated across README / `project_README` / this document. Python tests: 117;
  frontend tests: 3.

**Round 6 — Real system control & dashboard redesign (v2.3.0):**
- **Full machine access**: new `keerthi/system.py` (psutil) replaces the simulated
  smart home — live CPU/memory/disk/battery metrics, top-CPU process listing, process
  termination, known-app launcher, arbitrary command runner, and a file browser.
- **Reframed intents**: `COMMAND_INTENTS` now covers system status, process control,
  app/command/file operations, plus the existing tasks/timers/weather; `SAFETY_INTENTS`
  (`KILL_PROCESS`, `RUN_COMMAND`, `REMOVE_TASK`) require explicit confirmation.
- **Web API growth**: `GET /api/files` (directory listing) and `POST /api/action`
  (single-intent execution for the sidebar launcher, command runner, and file browser);
  browser mic now sends raw 16 kHz PCM to `POST /api/transcribe` (backend STT).
- **Dashboard redesign**: React frontend rebuilt around system gauges (CPU/RAM/Disk/
  Battery), a process table with kill buttons, an app launcher, a command runner, and a
  file browser, alongside chat, timers, and safety confirmations.
- Docs reframed (README / `project_README` / this document). Python tests: 131;
  frontend tests: 7.

**Round 7 — Computer control suite (v2.4.0):**
- **Input automation**: `TYPE_TEXT`, `PRESS_KEYS`, `MOVE_MOUSE`, `CLICK_MOUSE`,
  `SCROLL_MOUSE` via `pyautogui` (lazy-loaded, all `[SAFETY]`), with a
  clipboard-paste fallback for untypable text.
- **Screen analysis**: `TAKE_SCREENSHOT` saves PNGs to `SCREENSHOT_DIR`;
  `READ_SCREEN` feeds the capture to Gemini vision
  (`KeerthiBrain.describe_image`) via a provider wired in `main.py`/`server.py`;
  `GET /api/screenshot` serves the latest capture to the dashboard.
- **Power & display**: `SHUTDOWN`/`RESTART`/`SLEEP`/`LOCK_SCREEN` (subprocess,
  `[SAFETY]`), `SET_VOLUME`/`MUTE` (pycaw, with old-API fallback),
  `SET_BRIGHTNESS` (WMI, graceful admin fallback).
- **Window management**: `LIST_WINDOWS`/`FOCUS_WINDOW`/`MINIMIZE_WINDOW`/
  `MAXIMIZE_WINDOW`/`CLOSE_WINDOW` (win32gui, Windows-only, graceful no-op
  elsewhere); app launcher extended (chrome, edge, firefox, settings, terminal,
  word, excel).
- **Browser**: `OPEN_URL` and `WEB_SEARCH` via `webbrowser` (no new deps).
- **Web UI**: Power & Media card (volume/brightness sliders, mute, lock, sleep,
  restart, shutdown), screenshot capture panel, open-windows list with
  focus/minimize/maximize/close buttons, browser quick-open box, and an
  extended app list — all through the existing safety-confirm flow.
- **Robustness**: Windows-only deps (`pywin32`, `pycaw`, `comtypes`) guarded with
  PEP 508 platform markers in `requirements.txt`; mypy overrides for the untyped
  control packages; `screenshots/` git-ignored. Python tests: 208; frontend tests: 7.

---

## 11. Known Limitations / Future Work

- **Real system control is powerful** — `KILL_PROCESS` / `RUN_COMMAND` /
  `OPEN_FILE`, input automation, power control, and window closing act on the
  actual machine; all destructive or input-injecting intents are gated behind
  explicit confirmation (CLI prompt or web confirm), and the browser UI mirrors
  that gate.
- **Windows-only control packages** — `pyautogui`/`Pillow` are cross-platform,
  but `pywin32`, `pycaw`, and `comtypes` are Windows-only (guarded in
  `requirements.txt` with `sys_platform == "win32"` markers and lazy-imported).
  Volume/brightness/window control degrade to a friendly message on other
  platforms or when no audio endpoint exists.
- **Brightness may need elevation** — `WmiSetBrightness` can require
  administrator privileges or a supported display; failures report a graceful
  message instead of crashing.
- **`psutil`/`pyautogui`/`Pillow` are the main runtime deps** — all pure-Python
  wheels; already in `requirements.txt`.
- **Offline STT needs a model download** — `STT_ENGINE=vosk` needs a Vosk model
  (manual download); `STT_ENGINE=whisper` needs `pip install -r requirements-stt.txt`
  and downloads its model from Hugging Face on first use.
- **Gemini live calls untested** — transport is mocked in tests; live calls need a key.
  Since June 19, 2026 the Gemini API also rejects *unrestricted* API keys — restrict
  your key in Google AI Studio.
- **Web server is stateful in-process** — `keerthi/server.py` keeps brain/officer and
  the pending-confirmation store as module singletons; run with `--workers 1` or move
  to a shared store (Redis) for multi-worker deployments.
- **Weather needs internet** — Open-Meteo is free and keyless but requires connectivity.
- **Timer expiry is lost, not fired late** — timers that expire while the process is
  down are pruned on the next start (within a 60 s grace window) rather than fired late.
- Windows console may render `°C` / unicode inconsistently depending on codepage
  (mitigated by `chcp 65001` on startup).

*End of document.*
