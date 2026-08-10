"""Real system introspection and control for KEERTHI.

Exposes live host metrics, process management, application launching,
command execution, filesystem helpers, input automation, screenshots,
power/display control, window management, and browser helpers. Backed by
``psutil``, ``pyautogui``, ``win32gui`` and the standard library.

The heavy Windows-only packages (pyautogui/win32/pycaw) are loaded lazily
so this module stays importable (and testable) on any platform. Every
operation runs in the same user session as the server — KEERTHI only has
the privileges of the account that started it.
"""

from __future__ import annotations

import os
import platform
import subprocess
import time
import webbrowser
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from typing import Any

import psutil  # type: ignore[import-untyped]

from keerthi.config import CONFIG

PROCESS_LIMIT = 25
COMMAND_TIMEOUT_SECONDS = 30
COMMAND_MAX_OUTPUT = 4000
CPU_SAMPLE_SECONDS = 0.1
POWER_COMMAND_TIMEOUT_SECONDS = 15
BRIGHTNESS_TIMEOUT_SECONDS = 15
SCREENSHOT_FILENAME_FORMAT = "%Y%m%d-%H%M%S"

_APP_LAUNCHERS: dict[str, list[str]] = {
    "notepad": ["notepad.exe"],
    "calculator": ["calc.exe"],
    "paint": ["mspaint.exe"],
    "explorer": ["explorer.exe"],
    "file explorer": ["explorer.exe"],
    "task manager": ["taskmgr.exe"],
    "command prompt": ["cmd.exe"],
    "powershell": ["powershell.exe"],
    "control panel": ["control.exe"],
    "snipping tool": ["snippingtool.exe"],
    "chrome": ["chrome.exe"],
    "google chrome": ["chrome.exe"],
    "edge": ["msedge.exe"],
    "microsoft edge": ["msedge.exe"],
    "firefox": ["firefox.exe"],
    "settings": ["ms-settings:"],
    "terminal": ["wt.exe"],
    "word": ["winword.exe"],
    "excel": ["excel.exe"],
}

_KNOWN_APPS: list[str] = [
    "notepad",
    "calculator",
    "paint",
    "explorer",
    "task manager",
    "command prompt",
    "powershell",
    "control panel",
    "snipping tool",
    "chrome",
    "edge",
    "firefox",
    "settings",
    "terminal",
    "word",
    "excel",
]

# Lazy, guarded accessors for optional Windows-control packages.
_pyautogui: Any | None = None
_win32gui: Any | None = None
_win32con: Any | None = None


def known_apps() -> list[str]:
    """Returns the apps KEERTHI can launch with one tap."""
    return list(_KNOWN_APPS)


def _load_pyautogui() -> Any | None:
    global _pyautogui
    if _pyautogui is None:
        with suppress(Exception):
            import pyautogui

            _pyautogui = pyautogui
    return _pyautogui


def _load_win32() -> tuple[Any, Any]:
    global _win32gui, _win32con
    if _win32gui is None or _win32con is None:
        with suppress(Exception):
            if os.name == "nt":
                import win32con
                import win32gui

                _win32gui = win32gui
                _win32con = win32con
    return _win32gui, _win32con


def get_metrics() -> dict[str, Any]:
    """Returns a snapshot of live host metrics for the dashboard."""
    cpu = psutil.cpu_percent(interval=CPU_SAMPLE_SECONDS)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    boot = psutil.boot_time()
    battery = psutil.sensors_battery()
    return {
        "cpu": _percent(cpu),
        "cores": psutil.cpu_count(),
        "memoryUsed": int(mem.used),
        "memoryTotal": int(mem.total),
        "memoryPercent": _percent(mem.percent),
        "diskUsed": int(disk.used),
        "diskTotal": int(disk.total),
        "diskPercent": _percent(disk.percent),
        "batteryPercent": _percent(battery.percent) if battery else None,
        "batteryCharging": bool(battery.power_plugged) if battery else None,
        "uptime": int(time.time() - boot),
        "platform": platform.system(),
        "hostname": platform.node(),
        "python": platform.python_version(),
    }


def list_processes(limit: int = PROCESS_LIMIT) -> list[dict[str, Any]]:
    """Returns the top CPU-consuming processes on the machine."""
    baseline: list[psutil.Process] = []
    for proc in psutil.process_iter(["pid", "name", "memory_percent"]):
        with suppress(psutil.NoSuchProcess, psutil.AccessDenied):
            proc.cpu_percent(None)
            baseline.append(proc)

    time.sleep(CPU_SAMPLE_SECONDS)

    rows: list[dict[str, Any]] = []
    for proc in baseline:
        with suppress(psutil.NoSuchProcess, psutil.AccessDenied):
            rows.append(
                {
                    "pid": int(proc.pid),
                    "name": str(proc.name()),
                    "cpu": _percent(proc.cpu_percent(None)),
                    "memory": round(float(proc.info.get("memory_percent") or 0), 1),
                }
            )
    rows.sort(key=lambda row: row["cpu"], reverse=True)
    count = max(1, min(limit, PROCESS_LIMIT))
    return rows[:count]


def kill_process(pid: int) -> str:
    """Terminates a process by PID (graceful, then force)."""
    try:
        proc = psutil.Process(pid)
        name = proc.name()
        proc.terminate()
        proc.wait(timeout=5)
        return f"Terminated {name} (PID {pid})."
    except psutil.NoSuchProcess:
        return f"No process found with PID {pid}."
    except psutil.AccessDenied:
        return f"Access denied — cannot terminate PID {pid}."
    except psutil.TimeoutExpired:
        with suppress(Exception):
            proc.kill()
        return f"Force killed {name} (PID {pid})."


def open_app(name: str) -> str:
    """Launches a known app or resolves a name from PATH."""
    app = name.strip()
    if not app:
        return "No app name given to open."
    key = app.lower()
    command = _APP_LAUNCHERS.get(key, [app])
    try:
        subprocess.Popen(command)
        return f"Opened {app}."
    except OSError as exc:
        try:
            subprocess.Popen(f'start "" "{app}"', shell=True)
            return f"Opened {app}."
        except OSError:
            return f"Could not launch '{app}': {exc}"


def run_command(command: str) -> str:
    """Runs a shell command and returns its output (truncated)."""
    if not command.strip():
        return "No command given to run."
    try:
        completed = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
            errors="replace",
        )
    except subprocess.TimeoutExpired:
        return f"Command timed out after {COMMAND_TIMEOUT_SECONDS}s."
    except OSError as exc:
        return f"Could not run command: {exc}"
    output = ((completed.stdout or "") + (completed.stderr or "")).strip()
    if not output:
        return f"Command finished (exit code {completed.returncode})."
    return output[:COMMAND_MAX_OUTPUT]


def list_directory(path: str = ".") -> dict[str, Any]:
    """Lists the contents of a directory for the file browser."""
    try:
        folder = Path(path).expanduser()
        entries: list[dict[str, Any]] = []
        for child in sorted(folder.iterdir(), key=lambda x: (x.is_file(), x.name.lower())):
            with suppress(OSError):
                entries.append({"name": child.name, "isDir": child.is_dir()})
        return {"path": str(folder.resolve()), "entries": entries}
    except OSError as exc:
        return {"path": path, "entries": [], "error": str(exc)}


def open_file(path: str) -> str:
    """Opens a file with its default application."""
    target = Path(path).expanduser()
    try:
        if os.name == "nt":
            os.startfile(target)
        else:
            subprocess.Popen(["xdg-open", str(target)])
        return f"Opened {target}."
    except OSError as exc:
        return f"Could not open '{target}': {exc}"


# ---- Input automation (pyautogui) ----

def type_text(text: str) -> str:
    """Types text as if typed on the keyboard; returns it on success."""
    pyautogui = _load_pyautogui()
    if pyautogui is None:
        return ""
    try:
        pyautogui.write(text, interval=0.05)
        return text
    except Exception:
        with suppress(Exception):
            import pyperclip

            pyperclip.copy(text)
            pyautogui.hotkey("ctrl", "v")
            return text
        return ""


def press_keys(combo: str) -> str:
    """Presses a keyboard shortcut like 'ctrl+c'; returns it on success."""
    keys = [k.strip() for k in combo.split("+") if k.strip()]
    if not keys:
        return ""
    pyautogui = _load_pyautogui()
    if pyautogui is None:
        return ""
    try:
        pyautogui.hotkey(*keys)
        return combo
    except Exception:
        return ""


def move_mouse(x: int, y: int) -> str:
    """Moves the mouse cursor to screen coordinates."""
    pyautogui = _load_pyautogui()
    if pyautogui is None:
        return ""
    try:
        pyautogui.moveTo(x, y, duration=0.2)
        return f"({x}, {y})"
    except Exception:
        return ""


def click_mouse(x: int | None = None, y: int | None = None, button: str = "left") -> str:
    """Clicks the mouse at the current or given coordinates."""
    pyautogui = _load_pyautogui()
    if pyautogui is None:
        return ""
    try:
        pyautogui.click(x, y, button=button)
        position = f" at ({x}, {y})" if x is not None and y is not None else ""
        return f"{button} click{position}"
    except Exception:
        return ""


def scroll_mouse(direction: str = "down", clicks: int = 1) -> str:
    """Scrolls the mouse wheel up or down by a number of clicks."""
    pyautogui = _load_pyautogui()
    if pyautogui is None:
        return ""
    try:
        amount = abs(clicks) if direction.lower() == "up" else -abs(clicks)
        pyautogui.scroll(amount)
        return f"{direction} {clicks}"
    except Exception:
        return ""


# ---- Screenshots ----

def take_screenshot() -> str:
    """Captures the whole screen and returns the saved image path."""
    pyautogui = _load_pyautogui()
    if pyautogui is None:
        return ""
    folder = Path(CONFIG["SCREENSHOT_DIR"])
    try:
        folder.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime(SCREENSHOT_FILENAME_FORMAT)
        path = folder / f"screenshot-{stamp}.png"
        pyautogui.screenshot().save(str(path))
        return str(path)
    except Exception:
        return ""


def latest_screenshot() -> str:
    """Returns the most recent screenshot path (for the web dashboard)."""
    folder = Path(CONFIG["SCREENSHOT_DIR"])
    try:
        candidates = sorted(folder.glob("screenshot-*.png"), reverse=True)
    except OSError:
        return ""
    return str(candidates[0]) if candidates else ""


# ---- Power & display ----

def shutdown_system() -> str:
    """Shuts down the computer after a short grace period."""
    return _run_power_command(["shutdown", "/s", "/t", "5"], "Shutdown scheduled")


def restart_system() -> str:
    """Restarts the computer after a short grace period."""
    return _run_power_command(["shutdown", "/r", "/t", "5"], "Restart scheduled")


def sleep_system() -> str:
    """Puts the computer to sleep."""
    return _run_power_command(
        ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], "Sleeping"
    )


def lock_screen() -> str:
    """Locks the computer screen."""
    return _run_power_command(
        ["rundll32.exe", "user32.dll,LockWorkStation"], "Locking the screen"
    )


def _run_power_command(command: list[str], success_hint: str) -> str:
    if os.name != "nt":
        return "Power control is only supported on Windows."
    try:
        subprocess.run(
            command,
            shell=False,
            capture_output=True,
            timeout=POWER_COMMAND_TIMEOUT_SECONDS,
        )
        return f"{success_hint}."
    except subprocess.TimeoutExpired:
        return "The power command timed out."
    except OSError as exc:
        return f"Could not run power command: {exc}"


def set_volume(percent: int) -> str:
    """Sets the system volume (0-100)."""
    volume = _load_volume_interface()
    if volume is None:
        return ""
    try:
        level = max(0.0, min(100.0, float(percent))) / 100.0
        volume.SetMasterVolumeLevelScalar(level, None)
        return f"{percent}%"
    except Exception:
        return ""


def set_mute(on: bool) -> str:
    """Mutes or unmutes the system volume."""
    volume = _load_volume_interface()
    if volume is None:
        return ""
    try:
        volume.SetMute(1 if on else 0, None)
        return "muted" if on else "unmuted"
    except Exception:
        return ""


def get_volume_state() -> dict[str, Any] | None:
    """Returns {'percent': float, 'muted': bool} or None when unavailable."""
    volume = _load_volume_interface()
    if volume is None:
        return None
    try:
        level = float(volume.GetMasterVolumeLevelScalar()) * 100.0
        return {"percent": round(level), "muted": bool(volume.GetMute())}
    except Exception:
        return None


def _load_volume_interface() -> Any | None:
    if os.name != "nt":
        return None
    try:
        from pycaw.pycaw import AudioUtilities

        devices = AudioUtilities.GetSpeakers()
        endpoint = getattr(devices, "EndpointVolume", None)
        if endpoint is not None:
            return endpoint
        # Fallback for older pycaw releases (devices.Activate + QueryInterface).
        from comtypes import CLSCTX_INPROC_SERVER
        from pycaw.pycaw import IAudioEndpointVolume

        interface = devices.Activate(
            IAudioEndpointVolume._iid_, CLSCTX_INPROC_SERVER, None
        )
        return interface.QueryInterface(IAudioEndpointVolume)
    except Exception:
        return None


def set_brightness(percent: int) -> str:
    """Sets the screen brightness (0-100) via WMI."""
    if os.name != "nt":
        return "Brightness control is only supported on Windows."
    level = max(0, min(100, int(percent)))
    script = (
        f"(Get-CimInstance -Namespace root/WMI "
        f"-ClassName WmiMonitorBrightnessMethods).WmiSetBrightness(1,{level})"
    )
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            timeout=BRIGHTNESS_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return "Brightness command timed out."
    except OSError as exc:
        return f"Could not set brightness: {exc}"
    if completed.returncode != 0:
        return (
            "Could not set brightness — this may require administrator "
            "privileges or an external display."
        )
    return f"{level}%"


# ---- Window management (win32gui) ----

def list_windows() -> list[dict[str, Any]]:
    """Returns visible top-level windows with non-empty titles."""
    win32gui, _win32con = _load_win32()
    if win32gui is None:
        return []

    rows: list[dict[str, Any]] = []

    def _collect(hwnd: int, _extra: Any) -> None:
        if not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd).strip()
        if not title:
            return
        rows.append({"hwnd": int(hwnd), "title": title})

    with suppress(Exception):
        win32gui.EnumWindows(_collect, None)
    return rows


def _find_window(title: str) -> int | None:
    for row in list_windows():
        if title.lower() in row["title"].lower():
            return int(row["hwnd"])
    return None


def focus_window(title: str) -> str:
    """Brings a window matching `title` to the foreground."""
    win32gui, win32con = _load_win32()
    if win32gui is None:
        return "Window management is only supported on Windows."
    hwnd = _find_window(title)
    if hwnd is None:
        return f"No open window matches '{title}'."
    try:
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        return f"Focused '{title}'."
    except Exception:
        return f"Could not bring '{title}' to the foreground."


def minimize_window(title: str) -> str:
    """Minimizes a window matching `title`."""
    win32gui, win32con = _load_win32()
    if win32gui is None:
        return "Window management is only supported on Windows."
    hwnd = _find_window(title)
    if hwnd is None:
        return f"No open window matches '{title}'."
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
        return f"Minimized '{title}'."
    except Exception:
        return f"Could not minimize '{title}'."


def maximize_window(title: str) -> str:
    """Maximizes a window matching `title`."""
    win32gui, win32con = _load_win32()
    if win32gui is None:
        return "Window management is only supported on Windows."
    hwnd = _find_window(title)
    if hwnd is None:
        return f"No open window matches '{title}'."
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
        return f"Maximized '{title}'."
    except Exception:
        return f"Could not maximize '{title}'."


def close_window(title: str) -> str:
    """Closes a window matching `title`."""
    win32gui, _win32con = _load_win32()
    if win32gui is None:
        return "Window management is only supported on Windows."
    hwnd = _find_window(title)
    if hwnd is None:
        return f"No open window matches '{title}'."
    try:
        win32gui.PostMessage(hwnd, 0x0010, 0, 0)  # WM_CLOSE
        return f"Closing '{title}'."
    except Exception:
        return f"Could not close '{title}'."


# ---- Browser ----

def open_url(url: str) -> str:
    """Opens a URL in the default browser."""
    target = url.strip()
    if not target:
        return "No URL given to open."
    if "://" not in target:
        target = "https://" + target
    try:
        opened = webbrowser.open(target)
        return f"Opened {target}." if opened else f"Could not open {target}."
    except Exception:
        return f"Could not open {target}."


def web_search(query: str) -> str:
    """Searches the web in the default browser."""
    term = query.strip()
    if not term:
        return "No search query given."
    return open_url(f"https://www.google.com/search?q={_url_quote(term)}")


def _url_quote(text: str) -> str:
    from urllib.parse import quote

    return quote(text)


def _percent(value: float | None) -> int:
    return int(round(value or 0))
