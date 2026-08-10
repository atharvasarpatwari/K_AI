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
}

SAFETY_INTENTS = frozenset({"KILL_PROCESS", "RUN_COMMAND", "REMOVE_TASK"})


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
