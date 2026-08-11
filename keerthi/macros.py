"""Macro recording and playback for KEERTHI.

Macros capture keyboard/mouse input as a timed event list, persist them as
JSON, and replay them through pyautogui. Recording uses pynput's global input
listeners; both are optional Windows deps loaded lazily so this module stays
importable (and testable) on CI.
"""

import json
import threading
import time
from pathlib import Path
from typing import Any

from keerthi.config import CONFIG

MAX_MACRO_EVENTS = 20000
MAX_MACROS = 100


def _key_name(key: Any) -> str:
    """Serializes a pynput key object to a replay-friendly string."""
    char = getattr(key, "char", None)
    if char:
        return str(char)
    return str(getattr(key, "name", "unknown"))


def _pyautogui_name(key: str) -> str:
    """Maps a serialized key name to a pyautogui key name."""
    mapping = {
        "ctrl": "ctrl",
        "ctrl_l": "ctrl",
        "ctrl_r": "ctrl",
        "alt": "alt",
        "alt_l": "alt",
        "alt_r": "alt",
        "shift": "shift",
        "shift_l": "shift",
        "shift_r": "shift",
        "cmd": "win",
        "cmd_l": "win",
        "cmd_r": "win",
        "enter": "enter",
        "space": "space",
        "tab": "tab",
        "backspace": "backspace",
        "delete": "delete",
        "esc": "esc",
        "caps_lock": "capslock",
        "page_up": "pageup",
        "page_down": "pagedown",
        "up": "up",
        "down": "down",
        "left": "left",
        "right": "right",
    }
    return mapping.get(key, key)


def _button_name(raw: str) -> str:
    return raw if raw in ("left", "right", "middle") else "left"


def _load_pyautogui() -> Any | None:
    try:
        import pyautogui

        return pyautogui
    except Exception:
        return None


class MacroStore:
    """A JSON-backed store of recorded macros keyed by name."""

    def __init__(self, path: str | None = None) -> None:
        self.path = Path(path or CONFIG["MACRO_FILE"])
        self._macros: dict[str, list[dict[str, Any]]] = {}
        self._load()

    def _load(self) -> None:
        try:
            if self.path.exists():
                with open(self.path, encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    self._macros = {
                        str(k): v
                        for k, v in data.items()
                        if isinstance(v, list)
                    }
        except (OSError, ValueError):
            self._macros = {}

    def _save(self) -> None:
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self._macros, f, indent=2)
        except OSError:
            pass

    def save(self, name: str, events: list[dict[str, Any]]) -> bool:
        name = name.strip()
        if not name or not events:
            return False
        if name not in self._macros and len(self._macros) >= MAX_MACROS:
            return False
        self._macros[name] = events
        self._save()
        return True

    def load(self, name: str) -> list[dict[str, Any]] | None:
        events = self._macros.get(name.strip())
        return list(events) if events is not None else None

    def list(self) -> list[str]:
        return sorted(self._macros)

    def delete(self, name: str) -> bool:
        if name.strip() in self._macros:
            del self._macros[name.strip()]
            self._save()
            return True
        return False


class MacroRecorder:
    """Records a global input stream via pynput in a background thread."""

    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []
        self._started = 0.0
        self._lock = threading.Lock()
        self._threads: list[Any] = []
        self.active = False

    def start(self) -> bool:
        """Starts recording; returns False when pynput is unavailable."""
        try:
            from pynput import keyboard, mouse
        except Exception:
            return False
        self._events = []
        self._started = time.time()
        keyboard_listener = keyboard.Listener(on_press=self._on_key)
        mouse_listener = mouse.Listener(
            on_move=self._on_move,
            on_click=self._on_click,
            on_scroll=self._on_scroll,
        )
        keyboard_listener.start()
        mouse_listener.start()
        self._threads = [keyboard_listener, mouse_listener]
        self.active = True
        return True

    def _now(self) -> float:
        return round(time.time() - self._started, 3)

    def _on_move(self, x: int, y: int) -> None:
        with self._lock:
            self._events.append({"t": self._now(), "type": "move", "x": int(x), "y": int(y)})

    def _on_click(self, x: int, y: int, button: Any, pressed: bool) -> None:
        with self._lock:
            self._events.append(
                {
                    "t": self._now(),
                    "type": "click",
                    "x": int(x),
                    "y": int(y),
                    "button": _button_name(
                        str(getattr(button, "name", "left"))
                    ),
                    "pressed": bool(pressed),
                }
            )

    def _on_scroll(self, x: int, y: int, dx: int, dy: int) -> None:
        with self._lock:
            self._events.append(
                {
                    "t": self._now(),
                    "type": "scroll",
                    "x": int(x),
                    "y": int(y),
                    "dx": int(dx),
                    "dy": int(dy),
                }
            )

    def _on_key(self, key: Any) -> None:
        with self._lock:
            self._events.append({"t": self._now(), "type": "key", "key": _key_name(key)})

    def stop(self) -> list[dict[str, Any]]:
        self.active = False
        for thread in self._threads:
            try:
                thread.stop()
                thread.join(timeout=1.0)
            except Exception:
                pass
        self._threads = []
        with self._lock:
            events = list(self._events)
            self._events = []
        return events[-MAX_MACRO_EVENTS:]


def replay_events(events: list[dict[str, Any]]) -> int:
    """Replays recorded events via pyautogui; returns the number performed."""
    pyautogui = _load_pyautogui()
    if pyautogui is None or not events:
        return 0
    previous = 0.0
    performed = 0
    for event in events:
        try:
            timestamp = float(event.get("t", 0.0))
            delay = max(0.0, timestamp - previous)
            if delay > 0:
                time.sleep(delay)
            previous = timestamp
            _dispatch(pyautogui, event)
            performed += 1
        except Exception:
            continue
    return performed


def _dispatch(pyautogui: Any, event: dict[str, Any]) -> None:
    kind = event.get("type")
    if kind == "move":
        pyautogui.moveTo(int(event["x"]), int(event["y"]), duration=0)
    elif kind == "click":
        if event.get("pressed", True):
            pyautogui.click(
                int(event["x"]), int(event["y"]),
                button=_button_name(str(event.get("button", "left"))),
            )
    elif kind == "scroll":
        amount = -int(event.get("dy", 0))
        if amount:
            pyautogui.scroll(amount)
    elif kind == "key":
        pyautogui.press(_pyautogui_name(str(event.get("key", ""))))
