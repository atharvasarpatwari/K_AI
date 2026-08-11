COMMAND_INTENTS = {
    "SYSTEM_STATUS": "Report CPU, memory, disk and battery usage at a glance.",
    "CPU_USAGE": "Report the current CPU usage percentage.",
    "MEMORY_USAGE": "Report memory usage (used / total).",
    "DISK_USAGE": "Report disk usage (used / total).",
    "BATTERY_STATUS": "Report battery level and whether it is charging.",
    "LIST_PROCESSES": "List the top processes by CPU (e.g. LIST_PROCESSES:10).",
    "KILL_PROCESS": "Terminate a process by PID (e.g. KILL_PROCESS:1234).",
    "OPEN_APP": "Launch an application (e.g. OPEN_APP:notepad, OPEN_APP:calculator).",
    "RUN_COMMAND": "Run a shell command on the computer (e.g. RUN_COMMAND:echo hello).",
    "FILE_LIST": "List the contents of a folder (e.g. FILE_LIST:C:\\Users).",
    "OPEN_FILE": "Open a file or folder with the default app (e.g. OPEN_FILE:C:\\readme.txt).",
    "RESET_STATE": "Clear saved tasks and timers back to defaults.",
    "SET_TIMER": "Set a timer (e.g. SET_TIMER:90 for seconds, SET_TIMER:3:minutes).",
    "CANCEL_TIMER": "Cancel a timer by label or index (e.g. CANCEL_TIMER:2).",
    "CHECK_TIMERS": "Report all pending timers.",
    "ADD_TASK": "Add a task to the list (e.g. ADD_TASK:Call the dentist).",
    "REMOVE_TASK": "Remove a task by name (e.g. REMOVE_TASK:Water the plants).",
    "STATUS_REPORT": "Report the current system status and task list.",
    "WEATHER_REPORT": "Report the current weather for the user's location.",
    "TYPE_TEXT": "Type text as if on the keyboard (e.g. TYPE_TEXT:hello world).",
    "PRESS_KEYS": "Press a keyboard shortcut (e.g. PRESS_KEYS:ctrl+c, PRESS_KEYS:win+d).",
    "MOVE_MOUSE": "Move the mouse cursor to screen coordinates (e.g. MOVE_MOUSE:500:400).",
    "CLICK_MOUSE": "Click the mouse (e.g. CLICK_MOUSE:500:400, CLICK_MOUSE:right).",
    "SCROLL_MOUSE": "Scroll the mouse wheel (e.g. SCROLL_MOUSE:up, SCROLL_MOUSE:down:5).",
    "TAKE_SCREENSHOT": "Capture the screen and save an image, reporting the file path.",
    "READ_SCREEN": "Take a screenshot and describe what is currently on the screen.",
    "SHUTDOWN": "Shut down the computer.",
    "RESTART": "Restart the computer.",
    "SLEEP": "Put the computer to sleep.",
    "LOCK_SCREEN": "Lock the computer screen.",
    "SET_VOLUME": "Set the system volume to a percentage (e.g. SET_VOLUME:50).",
    "MUTE": "Mute or unmute the system volume (e.g. MUTE:on).",
    "SET_BRIGHTNESS": "Set the screen brightness to a percentage (e.g. SET_BRIGHTNESS:70).",
    "LIST_WINDOWS": "List the open application windows.",
    "FOCUS_WINDOW": "Bring a window to the front (e.g. FOCUS_WINDOW:Notepad).",
    "MINIMIZE_WINDOW": "Minimize a window (e.g. MINIMIZE_WINDOW:Notepad).",
    "MAXIMIZE_WINDOW": "Maximize a window (e.g. MAXIMIZE_WINDOW:Notepad).",
    "CLOSE_WINDOW": "Close a window (e.g. CLOSE_WINDOW:Notepad).",
    "OPEN_URL": "Open a URL in the default browser (e.g. OPEN_URL:https://example.com).",
    "WEB_SEARCH": "Search the web in the default browser (e.g. WEB_SEARCH:best AI models).",
    "SAVE_FACT": "Save a user fact to long-term memory (e.g. SAVE_FACT:user prefers dark mode).",
    "LIST_FACTS": "List the facts KEERTHI has saved about the user.",
    "MACRO_RECORD": "Start recording a keyboard/mouse macro (e.g. MACRO_RECORD:demo).",
    "MACRO_STOP": "Stop the active macro recording and save it.",
    "MACRO_REPLAY": "Replay a recorded macro (e.g. MACRO_REPLAY:demo).",
    "MACRO_LIST": "List the recorded macros.",
    "MACRO_DELETE": "Delete a recorded macro (e.g. MACRO_DELETE:demo).",
    "SCHEDULE_TASK": (
        "Schedule a command to run later (e.g. SCHEDULE_TASK:notepad:10:30 "
        "or SCHEDULE_TASK:notepad:in:5:minutes)."
    ),
    "CANCEL_SCHEDULED": "Cancel a scheduled task by index (e.g. CANCEL_SCHEDULED:0).",
    "LIST_SCHEDULED": "Report all scheduled tasks.",
    "INSTALL_APP": "Install an app with winget (e.g. INSTALL_APP:7zip).",
    "MOVE_WINDOW": "Move a window to screen coordinates (e.g. MOVE_WINDOW:Notepad:100:100).",
    "MOVE_WINDOW_TO_MONITOR": (
        "Move a window to another monitor (e.g. MOVE_WINDOW_TO_MONITOR:Notepad:1)."
    ),
}

SAFETY_INTENTS = frozenset(
    {
        "KILL_PROCESS",
        "RUN_COMMAND",
        "REMOVE_TASK",
        "TYPE_TEXT",
        "PRESS_KEYS",
        "MOVE_MOUSE",
        "CLICK_MOUSE",
        "SCROLL_MOUSE",
        "SHUTDOWN",
        "RESTART",
        "SLEEP",
        "LOCK_SCREEN",
        "CLOSE_WINDOW",
        "MACRO_REPLAY",
        "SCHEDULE_TASK",
        "INSTALL_APP",
    }
)


def get_nlp_manifest() -> str:
    """Returns the command library manifest injected into the AI's system prompt."""
    lines = ["[ACTION] Command Library (use these EXACT tags to perform actions):"]
    for intent, desc in COMMAND_INTENTS.items():
        marker = " [SAFETY]" if intent in SAFETY_INTENTS else ""
        lines.append(f"- [ACTION:{intent}]{marker} -> {desc}")
    lines.append(
        "IMPORTANT: Before emitting a [SAFETY] tag, ask the user to confirm "
        "explicitly and wait for their approval."
    )
    return "\n".join(lines)
