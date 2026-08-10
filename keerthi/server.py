"""FastAPI web backend for KEERTHI.

Exposes the brain + executive over HTTP so a browser frontend can chat with
KEERTHI and inspect the live system state.

State lives in-process (module singletons), so run a single worker:

    uvicorn keerthi.server:app --workers 1
"""

import asyncio
import uuid
from contextlib import suppress
from typing import Any

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from keerthi import system
from keerthi.brain import KeerthiBrain
from keerthi.config import CONFIG
from keerthi.executive import (
    SAFETY_INTENTS,
    ExecutiveOfficer,
    extract_intents,
)
from keerthi.peripherals import PeripheralController

app = FastAPI(title="KEERTHI API", version="2.3.0")

_brain: KeerthiBrain | None = None
_officer: ExecutiveOfficer | None = None
_controller: PeripheralController | None = None
_loop: asyncio.AbstractEventLoop | None = None

# Single-use confirmation tokens for pending safety-critical actions.
_pending_confirmations: dict[str, dict[str, Any]] = {}

# Connected WebSocket clients awaiting live state / timer pushes.
_clients: set[WebSocket] = set()


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


class ChatRequest(BaseModel):
    message: str
    confirmed: bool = False


class ConfirmRequest(BaseModel):
    token: str
    confirmed: bool = True


class ActionRequest(BaseModel):
    intent: str
    args: list[str] = []


class ChatResponse(BaseModel):
    reply: str
    actions: list[str]
    state: dict[str, Any]
    needsConfirmation: bool
    confirmationToken: str | None = None
    pendingIntents: list[str] = []


@app.get("/api/health")
def health() -> dict[str, Any]:
    """Readiness probe for CI and load balancers."""
    return {
        "status": "ok",
        "version": app.version,
        "apiKeyPresent": bool(CONFIG["GEMINI_API_KEY"]),
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
    brain = get_brain()
    officer = get_officer()

    reply = brain.generate_response(request.message)
    intents = extract_intents(reply)
    safety = [i for i in intents if i in SAFETY_INTENTS]

    needs_confirmation = bool(safety) and not request.confirmed
    if needs_confirmation:
        token = uuid.uuid4().hex
        _pending_confirmations[token] = {
            "reply": reply,
            "intents": intents,
            "message": request.message,
        }
        return ChatResponse(
            reply=reply,
            actions=[],
            state=officer.get_summary(),
            needsConfirmation=True,
            confirmationToken=token,
            pendingIntents=safety,
        )

    actions = officer.parse_and_execute(reply, confirm=lambda _: request.confirmed)
    _push_state()
    return ChatResponse(
        reply=reply,
        actions=actions,
        state=officer.get_summary(),
        needsConfirmation=False,
    )


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

    actions = officer.parse_and_execute(pending["reply"], confirm=lambda _: True)
    _push_state()
    return ChatResponse(
        reply=pending["reply"],
        actions=actions,
        state=officer.get_summary(),
        needsConfirmation=False,
    )


@app.post("/api/action")
def run_action(request: ActionRequest) -> ChatResponse:
    """Executes a system intent directly (no LLM round-trip)."""
    officer = get_officer()
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


@app.get("/api/files")
def list_files(path: str = ".") -> dict[str, Any]:
    """Lists a directory for the browser file explorer."""
    return system.list_directory(path)


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
    """Streams live state snapshots and timer-expiry events to the dashboard."""
    await websocket.accept()
    _clients.add(websocket)
    try:
        await websocket.send_json({"type": "state", "state": get_officer().get_summary()})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        _clients.discard(websocket)


@app.on_event("startup")
async def _startup() -> None:
    global _loop
    _loop = asyncio.get_running_loop()


@app.on_event("shutdown")
async def _shutdown() -> None:
    if _officer is not None:
        _officer.stop()
    for ws in list(_clients):
        with suppress(Exception):
            await ws.close()
    _clients.clear()
