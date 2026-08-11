"""Persistent long-term memory (facts) for KEERTHI.

Facts are saved via the [ACTION:SAVE_FACT:...] tag and injected into the
system prompt so KEERTHI remembers the user across conversations.
"""

import json
import time
from pathlib import Path
from typing import Any

from keerthi.config import CONFIG

MAX_FACTS = 200


class MemoryStore:
    """A small JSON-backed store of user facts, deduplicated by text."""

    def __init__(self, path: str | None = None) -> None:
        self.path = Path(path or CONFIG["MEMORY_FILE"])
        self.facts: list[dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        try:
            if self.path.exists():
                with open(self.path, encoding="utf-8") as f:
                    data = json.load(f)
                self.facts = data.get("facts", []) if isinstance(data, dict) else []
                if not isinstance(self.facts, list):
                    self.facts = []
        except (OSError, ValueError):
            self.facts = []

    def _save(self) -> None:
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump({"facts": self.facts}, f, indent=2)
        except OSError:
            pass

    def remember(self, text: str) -> bool:
        """Adds a fact unless it already exists. Returns True when saved."""
        text = text.strip()
        if not text:
            return False
        normalized = text.lower()
        for fact in self.facts:
            if str(fact.get("text", "")).lower() == normalized:
                return False
        self.facts.append({"text": text, "time": time.time()})
        if len(self.facts) > MAX_FACTS:
            self.facts = self.facts[-MAX_FACTS:]
        self._save()
        return True

    def forget(self, index: int) -> bool:
        if 0 <= index < len(self.facts):
            del self.facts[index]
            self._save()
            return True
        return False

    def all(self) -> list[dict[str, Any]]:
        return list(self.facts)

    def recall(self) -> str:
        """Returns a prompt-ready block describing the saved facts."""
        if not self.facts:
            return ""
        lines = [f"- {f['text']}" for f in self.facts]
        return "Known facts about the user:\n" + "\n".join(lines)
