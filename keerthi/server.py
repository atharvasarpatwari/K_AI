"""FastAPI web backend for KEERTHI.

Exposes the brain + executive over HTTP so a browser frontend can chat with
KEERTHI and inspect the simulated smart-home state.

Run with:  uvicorn keerthi.server:app --reload
"""

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

from keerthi.brain import KeerthiBrain
from keerthi.executive import (
    SAFETY_INTENTS,
    ExecutiveOfficer,
    extract_intents,
)

app = FastAPI(title="KEERTHI API", version="2.1.0")

_brain: KeerthiBrain | None = None
_officer: ExecutiveOfficer | None = None


def get_brain() -> KeerthiBrain:
    global _brain
    if _brain is None:
        _brain = KeerthiBrain()
    return _brain


def get_officer() -> ExecutiveOfficer:
    global _officer
    if _officer is None:
        _officer = ExecutiveOfficer()
    return _officer


class ChatRequest(BaseModel):
    message: str
    confirmed: bool = False


class ChatResponse(BaseModel):
    reply: str
    actions: list[str]
    state: dict[str, Any]
    needsConfirmation: bool


@app.get("/api/state")
def get_state() -> dict[str, Any]:
    """Returns the current smart-home state."""
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
    actions: list[str] = []
    if not needs_confirmation:
        actions = officer.parse_and_execute(
            reply, confirm=lambda _: request.confirmed
        )

    return ChatResponse(
        reply=reply,
        actions=actions,
        state=officer.get_summary(),
        needsConfirmation=needs_confirmation,
    )
