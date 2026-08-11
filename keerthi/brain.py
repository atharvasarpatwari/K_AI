import logging
import time
from collections.abc import Generator, Iterator
from pathlib import Path
from typing import Any, cast

from google import genai
from google.genai import errors, types

from keerthi.config import CONFIG
from keerthi.memory import MemoryStore
from keerthi.nlp import COMMAND_INTENTS, get_nlp_manifest

logger = logging.getLogger(__name__)


def _should_retry(exc: Exception) -> bool:
    """True for transient failures (5xx, 429, transport errors)."""
    if isinstance(exc, errors.APIError):
        return exc.code >= 500 or exc.code == 429
    return True


def _retry_delay(attempt: int) -> float:
    base = float(CONFIG["GEMINI_RETRY_BASE_DELAY"])
    cap = float(CONFIG["GEMINI_RETRY_MAX_DELAY"])
    delay = base * (2**attempt)
    return cap if delay > cap else delay


def _call_to_action(call: Any) -> str:
    """Converts a Gemini FunctionCall into an [ACTION:...] tag for the executive."""
    name = str(call.name or "")
    args = (call.args or {}).get("args", "") if call.args else ""
    return f"[ACTION:{name}:{args}]" if args else f"[ACTION:{name}]"


def _build_tools() -> types.Tool:
    """Builds Gemini function declarations for every executive intent.

    Each function takes a single ``args`` string, mirroring the colon-separated
    argument format of the [ACTION:...] tags (e.g. OPEN_APP:notepad).
    """
    declarations = [
        types.FunctionDeclaration(
            name=intent,
            description=description,
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "args": types.Schema(
                        type=types.Type.STRING,
                        description=(
                            "Colon-separated arguments, e.g. 'notepad' for OPEN_APP "
                            "or '500:400' for MOVE_MOUSE. Empty string when no "
                            "arguments are needed."
                        ),
                    )
                },
            ),
        )
        for intent, description in COMMAND_INTENTS.items()
    ]
    return types.Tool(function_declarations=declarations)


class KeerthiBrain:
    def __init__(self) -> None:
        if not CONFIG["GEMINI_API_KEY"]:
            raise ValueError("GEMINI_API_KEY not found in environment.")

        self.client = genai.Client(api_key=CONFIG["GEMINI_API_KEY"])
        self.memory = MemoryStore()
        self.summary = ""
        self.history: list[types.ContentDict] = []
        self.config: types.GenerateContentConfigDict = {
            "system_instruction": self._get_system_prompt(),
            "temperature": CONFIG["TEMPERATURE"],
            "max_output_tokens": CONFIG["MAX_OUTPUT_TOKENS"],
            "top_p": CONFIG["TOP_P"],
        }
        if CONFIG["USE_FUNCTION_CALLING"]:
            self.config["tools"] = [_build_tools()]

    def _get_system_prompt(self) -> str:
        summary_block = (
            f"\nConversation summary from earlier:\n{self.summary}" if self.summary else ""
        )
        memory_block = f"\n{self.memory.recall()}" if self.memory.recall() else ""
        return f"""You are KEERTHI, a highly advanced, conversational personal assistant
running directly on the user's computer. You have full access to the machine: you
can monitor CPU, memory, disk and battery usage, list and terminate running
processes, launch applications, open files and folders, and run commands. The
smart-home layer is replaced by real system control — treat the computer as the
smart home.

Persona:
- Calm, confident, and slightly witty.
- Helpful but not overly emotional.
- Professional yet warm; no flirting, no overly robotic speech.
- Respond concisely but informatively. Use confirmations like "Done", "Scheduled", "Running".

{get_nlp_manifest()}

Operational Rules:
- If ambiguous, ask a single clarifying question.
- For safety-critical actions (terminating processes, running arbitrary commands),
  explicitly ask for confirmation and wait for approval before emitting the tag.
- Proactively suggest actions based on context (e.g. "your CPU is at 92%").
- When confidence is low, say "I'm not certain, but here's what I found..."
- ALWAYS use the [ACTION:XXX] tags from the Command Library above when performing an action.
- When a tag needs an argument that contains a colon (like a file path), keep the
  colon inside the argument, e.g. [ACTION:FILE_LIST:C:\\Users].
- For multi-step tasks, chain multiple tags in one reply, e.g. opening a browser
  and searching: [ACTION:OPEN_APP:chrome][ACTION:WEB_SEARCH:best AI models].
- When the user asks what is on the screen, use [ACTION:READ_SCREEN].
- Before moving the mouse, clicking, typing, or pressing hotkeys, state what you
  are about to do and wait for confirmation (these are [SAFETY] actions).

Context:
User: {CONFIG['USER_NAME']}
Location: {CONFIG['LOCATION']}
Software version: {CONFIG['VERSION']}
Host: (injected live via state)
{summary_block}
{memory_block}
"""

    def refresh_system_prompt(self) -> None:
        """Rebuilds the system prompt (memory/summary may have changed)."""
        self.config["system_instruction"] = self._get_system_prompt()

    _FAILURE_MESSAGE = "I hit a technical snag. Please try that again."

    def generate_response(self, user_input: str) -> str:
        self.history.append({"role": "user", "parts": [{"text": user_input}]})
        try:
            reply = self._generate_content()
            self.history.append({"role": "model", "parts": [{"text": reply}]})
            self._trim_history()
            return reply
        except Exception:
            logger.exception("Gemini call failed")
            return self._FAILURE_MESSAGE

    def _generate_content(self) -> str:
        """Runs one full Gemini generation with retry/backoff on transient errors."""
        max_retries = CONFIG["GEMINI_MAX_RETRIES"]
        for attempt in range(max_retries + 1):
            try:
                response = self.client.models.generate_content(
                    model=CONFIG["MODEL_NAME"],
                    contents=cast(Any, self.history),
                    config=self.config,
                )
                return self._compose_reply(response)
            except Exception as exc:
                if attempt >= max_retries or not _should_retry(exc):
                    raise
                logger.warning(
                    "Gemini call failed (attempt %s/%s), retrying in %.1fs",
                    attempt + 1,
                    max_retries,
                    _retry_delay(attempt),
                )
                time.sleep(_retry_delay(attempt))
        raise RuntimeError("unreachable")

    @staticmethod
    def _compose_reply(response: Any) -> str:
        """Text plus optional function-call tags, in reply order."""
        parts: list[str] = []
        text = getattr(response, "text", None)
        if text:
            parts.append(str(text))
        if CONFIG["USE_FUNCTION_CALLING"]:
            for call in getattr(response, "function_calls", None) or []:
                parts.append(_call_to_action(call))
        return "\n".join(p for p in parts if p).strip()

    def generate_response_stream(self, user_input: str) -> Generator[str, None, None]:
        """Streams the assistant reply as text deltas, updating history at the end.

        Each yielded string is the new text since the previous yield. The caller
        should concatenate the deltas to reconstruct the full reply.
        """
        self.history.append({"role": "user", "parts": [{"text": user_input}]})
        full = ""
        try:
            for chunk in self._iter_stream():
                text = chunk.text or ""
                delta = text[len(full):] if len(text) > len(full) else text
                if delta:
                    yield delta
                full = text
                if CONFIG["USE_FUNCTION_CALLING"]:
                    for call in getattr(chunk, "function_calls", None) or []:
                        tag = _call_to_action(call)
                        yield tag
                        full += tag
            self.history.append({"role": "model", "parts": [{"text": full}]})
            self._trim_history()
        except Exception:
            logger.exception("Gemini stream call failed")
            raise

    def _iter_stream(self) -> Iterator[Any]:
        """Streams chunks, retrying only failures that occur before the first chunk."""
        max_retries = CONFIG["GEMINI_MAX_RETRIES"]
        attempt = 0
        while True:
            started = False
            try:
                for chunk in self.client.models.generate_content_stream(
                    model=CONFIG["MODEL_NAME"],
                    contents=cast(Any, self.history),
                    config=self.config,
                ):
                    started = True
                    yield chunk
                return
            except Exception as exc:
                if started or attempt >= max_retries or not _should_retry(exc):
                    raise
                attempt += 1
                logger.warning(
                    "Gemini stream failed to start (attempt %s/%s), retrying in %.1fs",
                    attempt,
                    max_retries,
                    _retry_delay(attempt - 1),
                )
                time.sleep(_retry_delay(attempt - 1))

    def _trim_history(self) -> None:
        max_messages = CONFIG["MAX_HISTORY_TURNS"] * 2
        if len(self.history) <= max_messages:
            return
        dropped = self.history[: len(self.history) - max_messages]
        self.history = self.history[-max_messages:]
        summary = self._summarize(dropped)
        if summary:
            self.summary = summary
            self.refresh_system_prompt()

    def _summarize(self, messages: list[types.ContentDict]) -> str:
        """Best-effort summary of dropped turns; never raises."""
        try:
            transcript = "\n".join(
                f"{m.get('role', '?')}: {cast(Any, m.get('parts', [{}]))[0].get('text', '')}"
                for m in messages
            )
            response = self.client.models.generate_content(
                model=CONFIG["MODEL_NAME"],
                contents=cast(
                    Any,
                    [
                        {
                            "role": "user",
                            "parts": [
                                {
                                    "text": (
                                        "Summarize the following conversation in 2-3 "
                                        "sentences, preserving key user preferences, names "
                                        "and context:\n\n" + transcript
                                    )
                                }
                            ],
                        }
                    ],
                ),
                config=self.config,
            )
            return response.text or ""
        except Exception:
            logger.exception("Conversation summarization failed")
            return ""

    def reset_conversation(self) -> None:
        self.history = []

    def describe_image(self, image_path: str) -> str:
        """Describes an image file (e.g. a screenshot) using the vision model."""
        try:
            image_bytes = Path(image_path).read_bytes()
            response = self.client.models.generate_content(
                model=CONFIG["MODEL_NAME"],
                contents=cast(
                    Any,
                    [
                        types.Content(
                            role="user",
                            parts=[
                                types.Part(
                                    text="Describe what is on this computer screen in "
                                    "2-3 concise sentences: visible windows, text, buttons "
                                    "and anything notable. Be specific enough that the user "
                                    "can act on it."
                                ),
                                types.Part.from_bytes(
                                    data=image_bytes, mime_type="image/png"
                                ),
                            ],
                        )
                    ],
                ),
                config=self.config,
            )
            return response.text or ""
        except Exception:
            logger.exception("Gemini vision call failed")
            return ""
