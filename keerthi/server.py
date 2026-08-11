"""FastAPI web backend for KEERTHI.

Exposes the brain + executive over HTTP so a browser frontend can chat with
KEERTHI and inspect the live system state.

State lives in-process (module singletons), so run a single worker:

    uvicorn keerthi.server:app --workers 1
"""

import asyncio
import json
import logging
import threading
import time
import uuid
from contextlib import suppress
from typing import Any

from fastapi import (
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Query,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import FileResponse
from pydantic import BaseModel

from keerthi import system
from keerthi.brain import KeerthiBrain
from keerthi.config import CONFIG
from keerthi.executive import (
    SAFETY_INTENTS,
    ExecutiveOfficer,
    extract_intents,
)
from keerthi.logsetup import setup_file_logging
from keerthi.memory import MemoryStore
from keerthi.peripherals import PeripheralController

logger = logging.getLogger(__name__)


def _is_authorized(token: str | None) -> bool:
    expected = CONFIG["KEERTHI_API_TOKEN"]
    return not expected or bool(token) and token == expected


async def require_token(
    x_api_token: str | None = Header(default=None),
    token: str | None = Query(default=None),
) -> None:
    """Optional bearer-style auth: only enforced when KEERTHI_API_TOKEN is set."""
    if not _is_authorized(x_api_token or token):
        raise HTTPException(status_code=401, detail="Unauthorized")


app = FastAPI(title="KEERTHI API", version="3.0.0", dependencies=[Depends(require_token)])

_brain: KeerthiBrain | None = None
_officer: ExecutiveOfficer | None = None
_controller: PeripheralController | None = None
_memory: MemoryStore | None = None
_loop: asyncio.AbstractEventLoop | None = None

# Single-use confirmation tokens for pending safety-critical actions.
_pending_confirmations: dict[str, dict[str, Any]] = {}

# Connected WebSocket clients awaiting live state / timer pushes.
_clients: set[WebSocket] = set()

_started_at = time.monotonic()

_DEGRADED_REPLY = (
    "KEERTHI is running without a Gemini API key. "
    "Add GEMINI_API_KEY to your environment or .env file and restart to enable chat."
)


def get_brain() -> KeerthiBrain:
    global _brain
    if _brain is None:
        _brain = KeerthiBrain()
    return _brain


def get_officer() -> ExecutiveOfficer:
    global _officer
    if _officer is None:
        _officer = ExecutiveOfficer()
        _officer.set_notifier(_broadcast)
    return _officer


def get_controller() -> PeripheralController:
    global _controller
    if _controller is None:
        _controller = PeripheralController()
    return _controller


def get_memory() -> MemoryStore:
    global _memory
    if _memory is None:
        _memory = MemoryStore()
    return _memory


async def _send_events(events: list[dict[str, Any]]) -> None:
    stale: list[WebSocket] = []
    for ws in _clients:
        try:
            for event in events:
                await ws.send_json(event)
        except Exception:
            stale.append(ws)
    for ws in stale:
        _clients.discard(ws)


def _schedule(events: list[dict[str, Any]]) -> None:
    """Schedules an event push on the server loop (safe from other threads)."""
    if _loop is None:
        return
    asyncio.run_coroutine_threadsafe(_send_events(events), _loop)


def _broadcast(message: str) -> None:
    """Called by the executive's scheduler thread when a timer expires."""
    _schedule(
        [
            {"type": "timer", "message": message},
            {"type": "state", "state": get_officer().get_summary()},
        ]
    )


def _push_state() -> None:
    _schedule([{"type": "state", "state": get_officer().get_summary()}])


def _screenshot_url(intents: list[str]) -> str | None:
    """Returns a fresh screenshot URL if the reply captured/described the screen."""
    if any(i in ("TAKE_SCREENSHOT", "READ_SCREEN") for i in intents):
        return f"/api/screenshot?t={int(time.time() * 1000)}"
    return None


def _extract_and_execute(
    reply: str, confirmed: bool
) -> dict[str, Any]:
    """Extracts intents from a reply, running safety gating + execution.

    Mirrors the POST /api/chat pipeline so the WebSocket path shares it.
    Returns the response payload minus `reply`.
    """
    officer = get_officer()
    intents = extract_intents(reply)
    safety = [i for i in intents if i in SAFETY_INTENTS]

    if safety and not confirmed:
        token = uuid.uuid4().hex
        _pending_confirmations[token] = {
            "reply": reply,
            "intents": intents,
        }
        return {
            "actions": [],
            "state": officer.get_summary(),
            "needsConfirmation": True,
            "confirmationToken": token,
            "pendingIntents": safety,
            "screenshotUrl": None,
        }

    actions = officer.parse_and_execute(reply, confirm=lambda _: confirmed)
    if any(i == "SAVE_FACT" for i in intents):
        with suppress(ValueError):
            get_brain().refresh_system_prompt()
    _push_state()
    return {
        "actions": actions,
        "state": officer.get_summary(),
        "needsConfirmation": False,
        "confirmationToken": None,
        "pendingIntents": [],
        "screenshotUrl": _screenshot_url(intents),
    }


class ChatRequest(BaseModel):
    message: str
    confirmed: bool = False


class ConfirmRequest(BaseModel):
    token: str
    confirmed: bool = True


class ActionRequest(BaseModel):
    intent: str
    args: list[str] = []


class MemoryRequest(BaseModel):
    text: str = ""


class MemoryIndexRequest(BaseModel):
    index: int = 0


class ChatResponse(BaseModel):
    reply: str
    actions: list[str]
    state: dict[str, Any]
    needsConfirmation: bool
    confirmationToken: str | None = None
    pendingIntents: list[str] = []
    screenshotUrl: str | None = None


@app.get("/api/health")
def health() -> dict[str, Any]:
    """Readiness probe for CI, load balancers, and the dashboard."""
    history_len = len(_brain.history) if _brain is not None else 0
    return {
        "status": "ok",
        "version": app.version,
        "apiKeyPresent": bool(CONFIG["GEMINI_API_KEY"]),
        "tokenRequired": bool(CONFIG["KEERTHI_API_TOKEN"]),
        "uptime": round(time.monotonic() - _started_at, 1),
        "pendingConfirmations": len(_pending_confirmations),
        "historyMessages": history_len,
    }


@app.get("/api/state")
def get_state() -> dict[str, Any]:
    """Returns the current system state (metrics, processes, tasks, timers)."""
    return get_officer().get_summary()


@app.post("/api/reset")
def reset_conversation() -> dict[str, bool]:
    """Clears the conversation history."""
    get_brain().reset_conversation()
    return {"ok": True}


@app.post("/api/chat")
def chat(request: ChatRequest) -> ChatResponse:
    """Processes one user message through the brain and executive."""
    officer = get_officer()
    if not CONFIG["GEMINI_API_KEY"]:
        return ChatResponse(
            reply=_DEGRADED_REPLY,
            actions=[],
            state=officer.get_summary(),
            needsConfirmation=False,
        )
    brain = get_brain()
    officer.set_vision_provider(brain.describe_image)

    reply = brain.generate_response(request.message)
    result = _extract_and_execute(reply, request.confirmed)
    return ChatResponse(reply=reply, **result)


@app.post("/api/confirm")
def confirm(request: ConfirmRequest) -> ChatResponse:
    """Executes a pending safety-critical action without another LLM call."""
    officer = get_officer()
    pending = _pending_confirmations.pop(request.token, None)
    if pending is None:
        raise HTTPException(status_code=404, detail="Unknown or expired confirmation token.")

    if not request.confirmed:
        return ChatResponse(
            reply=pending["reply"],
            actions=[],
            state=officer.get_summary(),
            needsConfirmation=False,
        )

    result = _extract_and_execute(pending["reply"], True)
    return ChatResponse(reply=pending["reply"], **result)


@app.post("/api/action")
def run_action(request: ActionRequest) -> ChatResponse:
    """Executes a system intent directly (no LLM round-trip)."""
    officer = get_officer()
    with suppress(ValueError):
        officer.set_vision_provider(get_brain().describe_image)
    tag = f"[ACTION:{request.intent}"
    if request.args:
        tag += ":" + ":".join(request.args)
    reply = tag + "]"
    intents = extract_intents(reply)
    safety = [i for i in intents if i in SAFETY_INTENTS]

    if safety:
        token = uuid.uuid4().hex
        _pending_confirmations[token] = {
            "reply": reply,
            "intents": intents,
            "message": "",
        }
        return ChatResponse(
            reply="",
            actions=[],
            state=officer.get_summary(),
            needsConfirmation=True,
            confirmationToken=token,
            pendingIntents=safety,
        )

    actions = officer.parse_and_execute(reply)
    _push_state()
    return ChatResponse(
        reply="",
        actions=actions,
        state=officer.get_summary(),
        needsConfirmation=False,
    )


@app.get("/api/memory")
def list_memory() -> dict[str, Any]:
    """Returns the saved long-term memory facts."""
    return {"facts": get_memory().all()}


@app.post("/api/memory")
def remember_fact(request: MemoryRequest) -> dict[str, Any]:
    """Adds a fact to long-term memory."""
    ok = get_memory().remember(request.text)
    return {"ok": ok, "facts": get_memory().all()}


@app.post("/api/memory/forget")
def forget_fact(request: MemoryIndexRequest) -> dict[str, Any]:
    """Removes a fact by index."""
    ok = get_memory().forget(request.index)
    return {"ok": ok, "facts": get_memory().all()}


@app.get("/api/files")
def list_files(path: str = ".") -> dict[str, Any]:
    """Lists a directory for the browser file explorer."""
    return system.list_directory(path)


@app.get("/api/screenshot")
def get_screenshot() -> FileResponse:
    """Returns the most recent screenshot as a PNG."""
    path = system.latest_screenshot()
    if not path:
        raise HTTPException(status_code=404, detail="No screenshot available yet.")
    return FileResponse(path, media_type="image/png")


@app.get("/api/windows")
def get_windows() -> dict[str, Any]:
    """Returns the open top-level windows for the browser dashboard."""
    return {"windows": system.list_windows()}


@app.post("/api/transcribe")
async def transcribe_audio(request: Request) -> dict[str, str]:
    """Transcribes raw 16 kHz mono int16 PCM audio bytes to text.

    The browser frontend records mic audio, resamples it to 16 kHz mono
    PCM, and POSTs the raw bytes here. The configured STT engine
    (google/vosk/whisper) does the transcription.
    """
    import speech_recognition as sr  # type: ignore[import-untyped]

    data = await request.body()
    if not data:
        raise HTTPException(status_code=400, detail="Empty audio body")
    audio = sr.AudioData(data, 16000, 2)
    text = get_controller()._transcribe(audio)
    if not text:
        raise HTTPException(status_code=422, detail="Could not transcribe audio")
    return {"text": text}


@app.websocket("/api/ws")
async def ws_state(websocket: WebSocket) -> None:
    """Streams live state, timer events, and token-by-token chat replies."""
    await websocket.accept()
    if not _is_authorized(websocket.query_params.get("token")):
        await websocket.close(code=1008, reason="Unauthorized")
        return
    _clients.add(websocket)
    officer = get_officer()
    with suppress(ValueError):
        officer.set_vision_provider(get_brain().describe_image)
    try:
        await websocket.send_json({"type": "state", "state": officer.get_summary()})
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if data.get("type") != "chat" or not data.get("message"):
                continue
            if not CONFIG["GEMINI_API_KEY"]:
                await websocket.send_json({"type": "error", "message": _DEGRADED_REPLY})
                continue
            await _handle_chat_stream(websocket, officer, str(data["message"]))
    except WebSocketDisconnect:
        pass
    finally:
        _clients.discard(websocket)


async def _handle_chat_stream(
    websocket: WebSocket, officer: ExecutiveOfficer, message: str
) -> None:
    """Runs a brain stream in a worker thread, relaying deltas to the socket."""
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[str | None] = asyncio.Queue()
    outcome: dict[str, Any] = {}

    def _run() -> None:
        parts: list[str] = []
        try:
            for delta in get_brain().generate_response_stream(message):
                parts.append(delta)
                loop.call_soon_threadsafe(queue.put_nowait, delta)
            outcome["reply"] = "".join(parts)
        except Exception:
            outcome["error"] = True
            logger.exception("Gemini stream call failed")
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, None)

    threading.Thread(target=_run, daemon=True).start()

    while True:
        delta = await queue.get()
        if delta is None:
            break
        await websocket.send_json({"type": "delta", "text": delta})

    if outcome.get("error"):
        await websocket.send_json(
            {"type": "error", "message": "Streaming failed. Please try that again."}
        )
        return

    result = _extract_and_execute(outcome.get("reply", ""), False)
    await websocket.send_json({"type": "done", "reply": outcome.get("reply", ""), **result})


@app.on_event("startup")
async def _startup() -> None:
    global _loop
    _loop = asyncio.get_running_loop()
    setup_file_logging()


@app.on_event("shutdown")
async def _shutdown() -> None:
    if _officer is not None:
        _officer.stop()
    for ws in list(_clients):
        with suppress(Exception):
            await ws.close()
    _clients.clear()
