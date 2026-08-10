import logging
from typing import Any, cast

from google import genai
from google.genai import types

from keerthi.config import CONFIG
from keerthi.nlp import get_nlp_manifest

logger = logging.getLogger(__name__)

class KeerthiBrain:
    def __init__(self) -> None:
        if not CONFIG["GEMINI_API_KEY"]:
            raise ValueError("GEMINI_API_KEY not found in environment.")

        self.client = genai.Client(api_key=CONFIG["GEMINI_API_KEY"])
        self.config: types.GenerateContentConfigDict = {
            "system_instruction": self._get_system_prompt(),
            "temperature": CONFIG["TEMPERATURE"],
            "max_output_tokens": CONFIG["MAX_OUTPUT_TOKENS"],
            "top_p": CONFIG["TOP_P"],
        }
        self.history: list[types.ContentDict] = []

    def _get_system_prompt(self) -> str:
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

Context:
User: {CONFIG['USER_NAME']}
Location: {CONFIG['LOCATION']}
Host: (injected live via state)
"""

    def generate_response(self, user_input: str) -> str:
        try:
            self.history.append({"role": "user", "parts": [{"text": user_input}]})

            response = self.client.models.generate_content(
                model=CONFIG["MODEL_NAME"],
                contents=cast(Any, self.history),
                config=self.config
            )

            reply = response.text or ""
            self.history.append({"role": "model", "parts": [{"text": reply}]})
            self._trim_history()
            return reply
        except Exception:
            logger.exception("Gemini call failed")
            return "I hit a technical snag. Please try that again."

    def _trim_history(self) -> None:
        max_messages = CONFIG["MAX_HISTORY_TURNS"] * 2
        if len(self.history) > max_messages:
            self.history = self.history[-max_messages:]

    def reset_conversation(self) -> None:
        self.history = []
