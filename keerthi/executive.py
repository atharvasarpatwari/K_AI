import copy
import json
import re
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from keerthi import system
from keerthi.config import CONFIG, INITIAL_STATE
from keerthi.nlp import SAFETY_INTENTS as SAFETY_INTENTS

PROCESS_REPORT_LIMIT = 10
TIMER_STALE_GRACE_SECONDS = 60
SCHEDULER_POLL_SECONDS = 0.5


class ExecutiveOfficer:
    """Executes system-level actions based on [ACTION:...] tags.

    Live machine access (metrics, processes, apps, commands, files) is
    delegated to :mod:`keerthi.system`; tasks and timers are the only
    persistent state KEERTHI tracks itself.
    """

    def __init__(
        self,
        state_file: str | None = None,
        load_state: bool = True,
    ) -> None:
        self.state: dict[str, Any] = copy.deepcopy(INITIAL_STATE)
        self.state_file = Path(state_file or CONFIG["STATE_FILE"])
        if load_state:
            self._load_state()
        self.state.setdefault("tasks", [])
        self.state.setdefault("timers", [])
        self._prune_stale_timers()
        self._lock = threading.RLock()
        self._notifier: Callable[[str], None] | None = None
        self._running = False
        self._thread: threading.Thread | None = None
        self._weather_provider: Callable[[str], str] | None = None
        self._vision_provider: Callable[[str], str] | None = None
        self._handlers: dict[str, Callable[[list[str]], str | None]] = {
            "SYSTEM_STATUS": self._system_status,
            "CPU_USAGE": self._cpu_usage,
            "MEMORY_USAGE": self._memory_usage,
            "DISK_USAGE": self._disk_usage,
            "BATTERY_STATUS": self._battery_status,
            "LIST_PROCESSES": self._list_processes,
            "KILL_PROCESS": self._kill_process,
            "OPEN_APP": self._open_app,
            "RUN_COMMAND": self._run_command,
            "FILE_LIST": self._file_list,
            "OPEN_FILE": self._open_file,
            "RESET_STATE": self._reset_state,
            "SET_TIMER": self._set_timer,
            "CANCEL_TIMER": self._cancel_timer,
            "CHECK_TIMERS": self._check_timers,
            "WEATHER_REPORT": self._get_weather,
            "ADD_TASK": self._add_task,
            "REMOVE_TASK": self._remove_task,
            "STATUS_REPORT": self._status_report,
            "TYPE_TEXT": self._type_text,
            "PRESS_KEYS": self._press_keys,
            "MOVE_MOUSE": self._move_mouse,
            "CLICK_MOUSE": self._click_mouse,
            "SCROLL_MOUSE": self._scroll_mouse,
            "TAKE_SCREENSHOT": self._take_screenshot,
            "READ_SCREEN": self._read_screen,
            "SHUTDOWN": self._shutdown,
            "RESTART": self._restart,
            "SLEEP": self._sleep,
            "LOCK_SCREEN": self._lock_screen,
            "SET_VOLUME": self._set_volume,
            "MUTE": self._mute,
            "SET_BRIGHTNESS": self._set_brightness,
            "LIST_WINDOWS": self._list_windows,
            "FOCUS_WINDOW": self._focus_window,
            "MINIMIZE_WINDOW": self._minimize_window,
            "MAXIMIZE_WINDOW": self._maximize_window,
            "CLOSE_WINDOW": self._close_window,
            "OPEN_URL": self._open_url,
            "WEB_SEARCH": self._web_search,
        }

    def parse_and_execute(
        self,
        ai_response: str,
        confirm: Callable[[str], bool] | None = None,
    ) -> list[str]:
        """Extracts [ACTION:...] tags, executes them, and persists state.

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

    # ---- System status ----

    def _system_status(self, args: list[str]) -> str:
        m = system.get_metrics()
        battery = _battery_text(m)
        return (
            f"System status — CPU {m['cpu']}% ({m['cores']} cores), "
            f"memory {m['memoryPercent']}%, disk {m['diskPercent']}% used, "
            f"{battery}."
        )

    def _cpu_usage(self, args: list[str]) -> str:
        m = system.get_metrics()
        return f"CPU usage is {m['cpu']}% across {m['cores']} cores."

    def _memory_usage(self, args: list[str]) -> str:
        m = system.get_metrics()
        used = _human_bytes(m["memoryUsed"])
        total = _human_bytes(m["memoryTotal"])
        return f"Memory usage is {m['memoryPercent']}% ({used} of {total})."

    def _disk_usage(self, args: list[str]) -> str:
        m = system.get_metrics()
        used = _human_bytes(m["diskUsed"])
        total = _human_bytes(m["diskTotal"])
        return f"Disk usage is {m['diskPercent']}% ({used} of {total})."

    def _battery_status(self, args: list[str]) -> str:
        m = system.get_metrics()
        return _battery_text(m)

    def _list_processes(self, args: list[str]) -> str:
        limit = _first_int(args, default=PROCESS_REPORT_LIMIT)
        if limit is None:
            limit = PROCESS_REPORT_LIMIT
        rows = system.list_processes(limit)
        if not rows:
            return "No running processes found."
        parts = [
            f"PID {row['pid']} {row['name']} (CPU {row['cpu']}%, MEM {row['memory']}%)"
            for row in rows
        ]
        return "Top processes: " + "; ".join(parts) + "."

    def _kill_process(self, args: list[str]) -> str:
        pid = _first_int(args)
        if pid is None:
            return "Please provide a process PID to kill (e.g. KILL_PROCESS:1234)."
        return system.kill_process(pid)

    def _open_app(self, args: list[str]) -> str:
        return system.open_app(_join_args(args))

    def _run_command(self, args: list[str]) -> str:
        return system.run_command(_join_args(args))

    def _file_list(self, args: list[str]) -> str:
        path = _join_args(args) or "."
        listing = system.list_directory(path)
        if "error" in listing:
            return f"Could not list '{path}': {listing['error']}"
        entries = listing["entries"]
        if not entries:
            return f"The folder '{listing['path']}' is empty."
        names = ", ".join(
            (f"[DIR] {e['name']}" if e["isDir"] else e["name"]) for e in entries
        )
        return f"Contents of {listing['path']}: {names}."

    def _open_file(self, args: list[str]) -> str:
        return system.open_file(_join_args(args))

    # ---- Input automation ----

    def _type_text(self, args: list[str]) -> str:
        text = _join_args(args)
        if not text:
            return "No text given to type."
        result = system.type_text(text)
        return f"Typed: {result}" if result else "Could not type that text."

    def _press_keys(self, args: list[str]) -> str:
        combo = _join_args(args)
        if not combo:
            return "No key combination given."
        result = system.press_keys(combo)
        return f"Pressed {result}." if result else f"Could not press '{combo}'."

    def _move_mouse(self, args: list[str]) -> str:
        parsed = _first_two_ints(args)
        if parsed is None:
            return "Please provide screen coordinates (e.g. MOVE_MOUSE:500:400)."
        x, y = parsed
        result = system.move_mouse(x, y)
        return f"Moved cursor to {result}." if result else "Could not move the cursor."

    def _click_mouse(self, args: list[str]) -> str:
        button = "left"
        x: int | None = None
        y: int | None = None
        parts = args[:3]
        if parts and parts[0].lower() in ("left", "right", "middle"):
            button = parts[0].lower()
            parts = parts[1:]
        parsed = _first_two_ints(parts)
        if parsed is not None:
            x, y = parsed
        result = system.click_mouse(x, y, button=button)
        return f"Performed {result}." if result else "Could not click the mouse."

    def _scroll_mouse(self, args: list[str]) -> str:
        raw = _join_args(args)
        direction = "down"
        if raw.lower() in ("up", "down"):
            direction = raw.lower()
            clicks = 1
        else:
            match = _first_int(args)
            if match is None:
                return "Please specify a scroll direction (up/down)."
            clicks = max(1, min(match, 100))
        result = system.scroll_mouse(direction, clicks)
        return f"Scrolled {result}." if result else "Could not scroll."

    # ---- Screenshots & screen analysis ----

    def _take_screenshot(self, args: list[str]) -> str:
        path = system.take_screenshot()
        return f"Screenshot saved to {path}." if path else "Could not take a screenshot."

    def _read_screen(self, args: list[str]) -> str:
        path = system.take_screenshot()
        if not path:
            return "Could not take a screenshot."
        provider = self._resolve_vision_provider()
        if provider is None:
            return f"Screenshot saved to {path}."
        description = provider(path)
        return description or f"Screenshot saved to {path}."

    def set_vision_provider(self, provider: Callable[[str], str]) -> None:
        """Overrides the screen-analysis source (used by tests and the web server)."""
        self._vision_provider = provider

    def _resolve_vision_provider(self) -> Callable[[str], str] | None:
        return self._vision_provider

    # ---- Power & display ----

    def _shutdown(self, args: list[str]) -> str:
        return system.shutdown_system()

    def _restart(self, args: list[str]) -> str:
        return system.restart_system()

    def _sleep(self, args: list[str]) -> str:
        return system.sleep_system()

    def _lock_screen(self, args: list[str]) -> str:
        return system.lock_screen()

    def _set_volume(self, args: list[str]) -> str:
        level = _first_int(args)
        if level is None:
            return "Please provide a volume percentage (e.g. SET_VOLUME:50)."
        result = system.set_volume(max(0, min(100, level)))
        return f"Volume set to {result}." if result else "Could not set the volume."

    def _mute(self, args: list[str]) -> str:
        raw = _join_args(args).strip().lower()
        on = raw not in ("off", "unmute", "false", "0", "no")
        result = system.set_mute(on)
        return f"Volume {result}." if result else "Could not change mute state."

    def _set_brightness(self, args: list[str]) -> str:
        level = _first_int(args)
        if level is None:
            return "Please provide a brightness percentage (e.g. SET_BRIGHTNESS:70)."
        result = system.set_brightness(level)
        return f"Brightness set to {result}." if result else "Could not set the brightness."

    # ---- Window management ----

    def _list_windows(self, args: list[str]) -> str:
        rows = system.list_windows()
        if not rows:
            return "No open windows found (or window management is unavailable)."
        titles = ", ".join(row["title"] for row in rows[:15])
        return f"Open windows: {titles}."

    def _focus_window(self, args: list[str]) -> str:
        title = _join_args(args)
        if not title:
            return "Please name the window to focus."
        return system.focus_window(title)

    def _minimize_window(self, args: list[str]) -> str:
        title = _join_args(args)
        if not title:
            return "Please name the window to minimize."
        return system.minimize_window(title)

    def _maximize_window(self, args: list[str]) -> str:
        title = _join_args(args)
        if not title:
            return "Please name the window to maximize."
        return system.maximize_window(title)

    def _close_window(self, args: list[str]) -> str:
        title = _join_args(args)
        if not title:
            return "Please name the window to close."
        return system.close_window(title)

    # ---- Browser ----

    def _open_url(self, args: list[str]) -> str:
        url = _join_args(args)
        if not url:
            return "Please provide a URL to open."
        return system.open_url(url)

    def _web_search(self, args: list[str]) -> str:
        query = _join_args(args)
        if not query:
            return "Please provide a search query."
        return system.web_search(query)

    # ---- Tasks ----

    def _add_task(self, args: list[str]) -> str:
        task_name = _join_args(args).strip() or "New Task"
        self.state["tasks"].append(task_name)
        return f"Task synchronization successful: {task_name}"

    def _remove_task(self, args: list[str]) -> str:
        target = _join_args(args).strip()
        if not target:
            return "No task name given to remove."
        if target in self.state["tasks"]:
            self.state["tasks"].remove(target)
            return f"Task removed: {target}"
        return f"No task found named '{target}'."

    # ---- Reset ----

    def _reset_state(self, args: list[str]) -> str:
        self.state = copy.deepcopy(INITIAL_STATE)
        return "Tasks and timers reset to defaults."

    # ---- Timers ----

    def _set_timer(self, args: list[str]) -> str:
        if not args:
            return "Please specify how long the timer should run for."
        match = _first_int(args)
        if match is None:
            return "I couldn't read a duration for that timer."
        seconds = _timer_seconds(match, _join_args(args).lower())
        with self._lock:
            label = f"Timer {len(self.state['timers']) + 1}"
            self.state["timers"].append({"label": label, "due": time.time() + seconds})
        return f"Timer set for {_format_duration(seconds)}. ({label})"

    def _cancel_timer(self, args: list[str]) -> str:
        if not args:
            return "Please specify which timer to cancel."
        raw = _join_args(args).strip()
        with self._lock:
            timers = self.state["timers"]
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
        with self._lock:
            timers = list(self.state["timers"])
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
        with self._lock:
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
        m = system.get_metrics()
        task_summary = ", ".join(self.state["tasks"]) or "none"
        return (
            f"Status report. CPU {m['cpu']}%, memory {m['memoryPercent']}%, "
            f"disk {m['diskPercent']}%. Tasks: {task_summary}."
        )

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
                self.state["tasks"] = list(loaded.get("tasks", self.state["tasks"]))
                self.state["timers"] = list(loaded.get("timers", self.state["timers"]))
        except (OSError, ValueError):
            pass

    def _prune_stale_timers(self) -> None:
        """Drops timers that expired long before this process started.

        A timer that should have fired while the process was down is dropped
        rather than fired late on the next poll.
        """
        now = time.time()
        keep: list[dict[str, Any]] = []
        for timer in self.state.get("timers", []):
            try:
                due = float(timer.get("due", now))
            except (TypeError, ValueError):
                due = now
            if due + TIMER_STALE_GRACE_SECONDS > now:
                keep.append(timer)
        self.state["timers"] = keep

    def _save_state(self) -> None:
        with self._lock:
            try:
                with open(self.state_file, "w", encoding="utf-8") as f:
                    json.dump(self.state, f, indent=2)
            except OSError:
                pass

    def get_summary(self) -> dict[str, Any]:
        """Returns live system metrics plus persistent tasks and timers."""
        return {
            "system": system.get_metrics(),
            "processes": system.list_processes(8),
            "tasks": list(self.state["tasks"]),
            "timers": list(self.state["timers"]),
        }


def extract_intents(ai_response: str) -> list[str]:
    """Returns the intent names present in an [ACTION:...] response (order kept)."""
    return [action.split(":")[0] for action in re.findall(r"\[ACTION:(.*?)\]", ai_response)]


def _first_int(args: list[str], default: int | None = None) -> int | None:
    """Extracts the first integer from the action args, falling back to default."""
    if not args:
        return default
    match = re.search(r"-?\d+", args[0])
    return int(match.group()) if match is not None else None


def _first_two_ints(args: list[str]) -> tuple[int, int] | None:
    """Extracts the first two integers (e.g. screen coordinates) from the args."""
    nums = [int(m.group()) for a in args for m in [re.search(r"-?\d+", a)] if m]
    return (nums[0], nums[1]) if len(nums) >= 2 else None


def _join_args(args: list[str]) -> str:
    """Rejoins colon-split args (paths like C:\\Users survive [ACTION:...])."""
    return ":".join(args)


def _timer_seconds(value: int, raw: str) -> int:
    """Converts a timer value + free-text units into a clamped number of seconds."""
    if "hour" in raw or "hr" in raw:
        return max(1, min(value, 24)) * 3600
    if "min" in raw:
        return max(1, min(value, 1440)) * 60
    return max(1, min(value, 86400))


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


def _battery_text(m: dict[str, Any]) -> str:
    if m.get("batteryPercent") is None:
        return "no battery detected"
    state = "charging" if m.get("batteryCharging") else "on battery"
    return f"battery at {m['batteryPercent']}% ({state})"


def _human_bytes(value: int) -> str:
    size = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{value} B"
