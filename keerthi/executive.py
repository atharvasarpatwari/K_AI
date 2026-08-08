import copy
import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any, Optional

from keerthi.config import CONFIG, INITIAL_STATE

MAX_FAN_SPEED = 5
MAX_BRIGHTNESS = 100


class ExecutiveOfficer:
    """Manages the state and execution of smart actions based on the NLP Library."""

    def __init__(
        self,
        state_file: Optional[str] = None,
        load_state: bool = True,
    ) -> None:
        self.state: dict[str, Any] = copy.deepcopy(INITIAL_STATE)
        self.state_file = Path(state_file or CONFIG["STATE_FILE"])
        if load_state:
            self._load_state()
        self._handlers: dict[str, Callable[[list[str]], Optional[str]]] = {
            "LIGHT_ON": self._light_on,
            "LIGHT_OFF": self._light_off,
            "SET_BRIGHTNESS": self._set_brightness,
            "AC_ON": self._ac_on,
            "AC_OFF": self._ac_off,
            "SET_TEMP": self._set_temp,
            "FAN_ON": self._fan_on,
            "FAN_OFF": self._fan_off,
            "FAN_SPEED": self._fan_speed,
            "LOCK_DOOR": self._lock_door,
            "UNLOCK_DOOR": self._unlock_door,
            "ADD_TASK": self._add_task,
            "REMOVE_TASK": self._remove_task,
            "STATUS_REPORT": self._status_report,
        }

    def parse_and_execute(self, ai_response: str) -> list[str]:
        """Extracts [ACTION:...] tags, updates internal state, and persists it."""
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

        if executed:
            self._save_state()
        return executed

    # ---- Lighting ----

    def _light_on(self, args: list[str]) -> str:
        self.state["devices"]["living_room_light"]["status"] = "on"
        return "Living room light: ACTIVE"

    def _light_off(self, args: list[str]) -> str:
        self.state["devices"]["living_room_light"]["status"] = "off"
        return "Living room light: INACTIVE"

    def _set_brightness(self, args: list[str]) -> Optional[str]:
        match = _first_int(args)
        if match is None:
            return None
        brightness = _clamp(match, 0, MAX_BRIGHTNESS)
        light = self.state["devices"]["living_room_light"]
        light["brightness"] = brightness
        light["status"] = "on" if brightness > 0 else "off"
        return f"Light brightness set to {brightness}%"

    # ---- Climate ----

    def _ac_on(self, args: list[str]) -> str:
        self.state["devices"]["bedroom_ac"]["status"] = "on"
        return "Bedroom AC: COOLING"

    def _ac_off(self, args: list[str]) -> str:
        self.state["devices"]["bedroom_ac"]["status"] = "off"
        return "Bedroom AC: OFF"

    def _set_temp(self, args: list[str]) -> Optional[str]:
        match = _first_int(args, default=22)
        if match is None:
            return None
        temp = match
        self.state["devices"]["bedroom_ac"]["temp"] = temp
        return f"Climate adjusted to {temp}°C"

    def _fan_on(self, args: list[str]) -> str:
        self.state["devices"]["kitchen_fan"]["status"] = "on"
        return "Kitchen fan: ON"

    def _fan_off(self, args: list[str]) -> str:
        self.state["devices"]["kitchen_fan"]["status"] = "off"
        return "Kitchen fan: OFF"

    def _fan_speed(self, args: list[str]) -> Optional[str]:
        match = _first_int(args)
        if match is None:
            return None
        speed = _clamp(match, 0, MAX_FAN_SPEED)
        fan = self.state["devices"]["kitchen_fan"]
        fan["speed"] = speed
        fan["status"] = "on" if speed > 0 else "off"
        return f"Kitchen fan speed set to {speed}"

    # ---- Security ----

    def _lock_door(self, args: list[str]) -> str:
        self.state["devices"]["main_door"]["status"] = "locked"
        return "Main entrance: SECURED"

    def _unlock_door(self, args: list[str]) -> str:
        self.state["devices"]["main_door"]["status"] = "unlocked"
        return "Main entrance: UNLOCKED"

    # ---- Tasks ----

    def _add_task(self, args: list[str]) -> str:
        task_name = args[0].strip() if args else "New Task"
        self.state["tasks"].append(task_name)
        return f"Task synchronization successful: {task_name}"

    def _remove_task(self, args: list[str]) -> str:
        target = args[0].strip() if args else ""
        if not target:
            return "No task name given to remove."
        if target in self.state["tasks"]:
            self.state["tasks"].remove(target)
            return f"Task removed: {target}"
        return f"No task found named '{target}'."

    # ---- Reporting ----

    def _status_report(self, args: list[str]) -> str:
        device_parts = []
        for name, device in self.state["devices"].items():
            detail = device.get("status", "unknown")
            if device.get("brightness") is not None:
                detail += f" at {device['brightness']}% brightness"
            if device.get("temp") is not None:
                detail += f", {device['temp']}°C"
            if device.get("speed") is not None:
                detail += f", speed {device['speed']}"
            device_parts.append(f"{name}: {detail}")
        task_summary = ", ".join(self.state["tasks"]) or "none"
        return "Status report. " + "; ".join(device_parts) + f". Tasks: {task_summary}."

    # ---- Persistence ----

    def _load_state(self) -> None:
        try:
            if self.state_file.exists():
                with open(self.state_file, encoding="utf-8") as f:
                    loaded = json.load(f)
                self.state = copy.deepcopy(loaded)
        except (OSError, ValueError):
            pass

    def _save_state(self) -> None:
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2)
        except OSError:
            pass

    def get_summary(self) -> dict[str, Any]:
        """Returns a snapshot of current status for the UI/Console."""
        return self.state


def _first_int(args: list[str], default: Optional[int] = None) -> Optional[int]:
    """Extracts the first integer from the action args, falling back to default."""
    if not args:
        return default
    match = re.search(r"-?\d+", args[0])
    return int(match.group()) if match is not None else None


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))
