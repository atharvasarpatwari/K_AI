"""Real system introspection and control for KEERTHI.

Exposes live host metrics, process management, application launching,
command execution, and filesystem helpers backed by ``psutil`` and the
standard library. Every operation runs in the same user session as the
server — KEERTHI only has the privileges of the account that started it.
"""

from __future__ import annotations

import os
import platform
import subprocess
import time
from contextlib import suppress
from pathlib import Path
from typing import Any

import psutil  # type: ignore[import-untyped]

PROCESS_LIMIT = 25
COMMAND_TIMEOUT_SECONDS = 30
COMMAND_MAX_OUTPUT = 4000
CPU_SAMPLE_SECONDS = 0.1

_APP_LAUNCHERS: dict[str, list[str]] = {
    "notepad": ["notepad.exe"],
    "calculator": ["calc.exe"],
    "paint": ["mspaint.exe"],
    "explorer": ["explorer.exe"],
    "task manager": ["taskmgr.exe"],
    "command prompt": ["cmd.exe"],
    "powershell": ["powershell.exe"],
    "control panel": ["control.exe"],
    "file explorer": ["explorer.exe"],
    "snipping tool": ["snippingtool.exe"],
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
]


def known_apps() -> list[str]:
    """Returns the apps KEERTHI can launch with one tap."""
    return list(_KNOWN_APPS)


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


def _percent(value: float | None) -> int:
    return int(round(value or 0))
