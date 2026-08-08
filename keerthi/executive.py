import copy
import re
from collections.abc import Callable
from typing import Any, Optional

from keerthi.config import INITIAL_STATE


class ExecutiveOfficer:
    """Manages the state and execution of smart actions based on the NLP Library."""

    def __init__(self) -> None:
        self.state: dict[str, Any] = copy.deepcopy(INITIAL_STATE)
        self._handlers: dict[str, Callable[[list[str]], Optional[str]]] = {
            "LIGHT_ON": self._light_on,
            "LIGHT_OFF": self._light_off,
            "SET_TEMP": self._set_temp,
            "LOCK_DOOR": self._lock_door,
            "UNLOCK_DOOR": self._unlock_door,
            "ADD_TASK": self._add_task,
        }

    def parse_and_execute(self, ai_response: str) -> list[str]:
        """Extracts [ACTION:...] tags and updates internal state."""
        actions = re.findall(r"\[ACTION:(.*?)\]", ai_response)
        executed: list[str] = []

        for action in actions:
            parts = action.split(":")
            handler = self._handlers.get(parts[0])
            if handler is None:
                continue
            result = handler(parts[1:])
            if result is not None:
                executed.append(result)

        return executed

    def _light_on(self, args: list[str]) -> str:
        self.state["devices"]["living_room_light"]["status"] = "on"
        return "Living room light: ACTIVE"

    def _light_off(self, args: list[str]) -> str:
        self.state["devices"]["living_room_light"]["status"] = "off"
        return "Living room light: INACTIVE"

    def _set_temp(self, args: list[str]) -> Optional[str]:
        raw = args[0].strip() if args else "22"
        match = re.search(r"-?\d+", raw)
        if match is None:
            return None
        temp = int(match.group())
        self.state["devices"]["bedroom_ac"]["temp"] = temp
        return f"Climate adjusted to {temp}°C"

    def _lock_door(self, args: list[str]) -> str:
        self.state["devices"]["main_door"]["status"] = "locked"
        return "Main entrance: SECURED"

    def _unlock_door(self, args: list[str]) -> str:
        self.state["devices"]["main_door"]["status"] = "unlocked"
        return "Main entrance: UNLOCKED"

    def _add_task(self, args: list[str]) -> str:
        task_name = args[0].strip() if args else "New Task"
        self.state["tasks"].append(task_name)
        return f"Task synchronization successful: {task_name}"

    def get_summary(self) -> dict[str, Any]:
        """Returns a snapshot of current status for the UI/Console."""
        return self.state
