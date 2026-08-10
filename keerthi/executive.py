import copy
import json
import re
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from keerthi.config import CONFIG, INITIAL_STATE
from keerthi.nlp import SAFETY_INTENTS as SAFETY_INTENTS

MAX_FAN_SPEED = 5
MAX_BRIGHTNESS = 100
MAX_HEATER_TEMP = 50
SCHEDULER_POLL_SECONDS = 0.5


class ExecutiveOfficer:
    """Manages the state and execution of smart actions based on the NLP Library."""

    def __init__(
        self,
        state_file: str | None = None,
        load_state: bool = True,
    ) -> None:
        self.state: dict[str, Any] = copy.deepcopy(INITIAL_STATE)
        self.state_file = Path(state_file or CONFIG["STATE_FILE"])
        if load_state:
            self._load_state()
        self.state.setdefault("timers", [])
        self._notifier: Callable[[str], None] | None = None
        self._running = False
        self._thread: threading.Thread | None = None
        self._weather_provider: Callable[[str], str] | None = None
        self._handlers: dict[str, Callable[[list[str]], str | None]] = {
            "LIGHT_ON": self._light_on,
            "LIGHT_OFF": self._light_off,
            "SET_BRIGHTNESS": self._set_brightness,
            "AC_ON": self._ac_on,
            "AC_OFF": self._ac_off,
            "SET_TEMP": self._set_temp,
            "FAN_ON": self._fan_on,
            "FAN_OFF": self._fan_off,
            "FAN_SPEED": self._fan_speed,
            "TV_ON": self._tv_on,
            "TV_OFF": self._tv_off,
            "CURTAIN_OPEN": self._curtain_open,
            "CURTAIN_CLOSE": self._curtain_close,
            "HEATER_ON": self._heater_on,
            "HEATER_OFF": self._heater_off,
            "HEATER_TEMP": self._heater_temp,
            "RESET_STATE": self._reset_state,
            "SET_TIMER": self._set_timer,
            "CANCEL_TIMER": self._cancel_timer,
            "CHECK_TIMERS": self._check_timers,
            "WEATHER_REPORT": self._get_weather,
            "LOCK_DOOR": self._lock_door,
            "UNLOCK_DOOR": self._unlock_door,
            "ADD_TASK": self._add_task,
            "REMOVE_TASK": self._remove_task,
            "STATUS_REPORT": self._status_report,
        }

    def parse_and_execute(
        self,
        ai_response: str,
        confirm: Callable[[str], bool] | None = None,
    ) -> list[str]:
        """Extracts [ACTION:...] tags, updates internal state, and persists it.

        When a `confirm` callback is provided, intents in SAFETY_INTENTS are
        only executed if the callback returns True for the intent name.
        """
        actions = re.findall(r"\[ACTION:(.*?)\]", ai_response)
        executed: list[str] = []

        for action in actions:
            parts = action.split(":")
            intent = parts[0]
            handler = self._handlers.get(intent)
            if handler is None:
                continue
            if intent in SAFETY_INTENTS and confirm is not None and not confirm(intent):
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

    def _set_brightness(self, args: list[str]) -> str | None:
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

    def _set_temp(self, args: list[str]) -> str | None:
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

    def _fan_speed(self, args: list[str]) -> str | None:
        match = _first_int(args)
        if match is None:
            return None
        speed = _clamp(match, 0, MAX_FAN_SPEED)
        fan = self.state["devices"]["kitchen_fan"]
        fan["speed"] = speed
        fan["status"] = "on" if speed > 0 else "off"
        return f"Kitchen fan speed set to {speed}"

    # ---- Entertainment ----

    def _tv_on(self, args: list[str]) -> str:
        self.state["devices"]["living_room_tv"]["status"] = "on"
        return "Living room TV: ON"

    def _tv_off(self, args: list[str]) -> str:
        self.state["devices"]["living_room_tv"]["status"] = "off"
        return "Living room TV: OFF"

    # ---- Curtains ----

    def _curtain_open(self, args: list[str]) -> str:
        self.state["devices"]["bedroom_curtains"]["status"] = "open"
        return "Bedroom curtains: OPEN"

    def _curtain_close(self, args: list[str]) -> str:
        self.state["devices"]["bedroom_curtains"]["status"] = "closed"
        return "Bedroom curtains: CLOSED"

    # ---- Water heater ----

    def _heater_on(self, args: list[str]) -> str:
        self.state["devices"]["bathroom_heater"]["status"] = "on"
        return "Bathroom heater: ON"

    def _heater_off(self, args: list[str]) -> str:
        self.state["devices"]["bathroom_heater"]["status"] = "off"
        return "Bathroom heater: OFF"

    def _heater_temp(self, args: list[str]) -> str | None:
        match = _first_int(args, default=40)
        if match is None:
            return None
        temp = _clamp(match, 0, MAX_HEATER_TEMP)
        heater = self.state["devices"]["bathroom_heater"]
        heater["temp"] = temp
        heater["status"] = "on" if temp > 0 else "off"
        return f"Bathroom heater temperature set to {temp}°C"

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

    # ---- Reset ----

    def _reset_state(self, args: list[str]) -> str:
        self.state = copy.deepcopy(INITIAL_STATE)
        return "Smart home state reset to defaults."

    # ---- Timers ----

    def _set_timer(self, args: list[str]) -> str:
        if not args:
            return "Please specify how long the timer should run for."
        match = _first_int(args)
        if match is None:
            return "I couldn't read a duration for that timer."
        seconds = _timer_seconds(match, " ".join(args).lower())
        label = f"Timer {len(self.state['timers']) + 1}"
        self.state["timers"].append({"label": label, "due": time.time() + seconds})
        return f"Timer set for {_format_duration(seconds)}. ({label})"

    def _cancel_timer(self, args: list[str]) -> str:
        timers = self.state["timers"]
        if not args:
            return "Please specify which timer to cancel."
        raw = args[0].strip()
        if re.fullmatch(r"\d+", raw):
            index = int(raw)
            if 0 <= index < len(timers):
                label = timers.pop(index)["label"]
                return f"Timer cancelled: {label}"
            return f"No timer at index {index}."
        for timer in timers:
            if timer["label"] == raw:
                timers.remove(timer)
                return f"Timer cancelled: {raw}"
        return f"No timer named '{raw}'."

    def _check_timers(self, args: list[str]) -> str:
        timers = self.state["timers"]
        if not timers:
            return "No timers are currently set."
        now = time.time()
        parts = [
            f"{t['label']} ({_format_duration(max(0, int(t['due'] - now)))})"
            for t in timers
        ]
        return "Pending timers: " + ", ".join(parts) + "."

    def _fire_due_timers(self) -> list[str]:
        """Returns messages for timers that have expired and removes them."""
        now = time.time()
        fired = [t for t in self.state["timers"] if t["due"] <= now]
        self.state["timers"] = [t for t in self.state["timers"] if t["due"] > now]
        if fired:
            self._save_state()
        return [f"Timer '{t['label']}' is up!" for t in fired]

    def set_notifier(self, callback: Callable[[str], None]) -> None:
        """Starts the scheduler so expired timers are reported via `callback`."""
        self._notifier = callback
        self._running = True
        self._thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stops the scheduler thread (safe to call multiple times)."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None

    def _scheduler_loop(self) -> None:
        while self._running:
            time.sleep(SCHEDULER_POLL_SECONDS)
            if self._notifier is not None:
                for message in self._fire_due_timers():
                    self._notifier(message)

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

    def _get_weather(self, args: list[str]) -> str:
        return self._resolve_weather_provider()(CONFIG["LOCATION"])

    def set_weather_provider(self, provider: Callable[[str], str]) -> None:
        """Overrides the weather source (used by tests and the web server)."""
        self._weather_provider = provider

    def _resolve_weather_provider(self) -> Callable[[str], str]:
        if self._weather_provider is None:
            from keerthi.services.weather import fetch_weather

            self._weather_provider = fetch_weather
        return self._weather_provider

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


def extract_intents(ai_response: str) -> list[str]:
    """Returns the intent names present in an [ACTION:...] response (order kept)."""
    return [action.split(":")[0] for action in re.findall(r"\[ACTION:(.*?)\]", ai_response)]


def _first_int(args: list[str], default: int | None = None) -> int | None:
    """Extracts the first integer from the action args, falling back to default."""
    if not args:
        return default
    match = re.search(r"-?\d+", args[0])
    return int(match.group()) if match is not None else None


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def _timer_seconds(value: int, raw: str) -> int:
    """Converts a timer value + free-text units into a clamped number of seconds."""
    if "hour" in raw or "hr" in raw:
        return _clamp(value, 1, 24) * 3600
    if "min" in raw:
        return _clamp(value, 1, 1440) * 60
    return _clamp(value, 1, 86400)


def _format_duration(seconds: int) -> str:
    minutes, sec = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if sec:
        parts.append(f"{sec}s")
    return " ".join(parts) or "0s"
