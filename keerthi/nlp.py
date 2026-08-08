COMMAND_INTENTS = {
    "LIGHT_ON": "Turn on the living room light.",
    "LIGHT_OFF": "Turn off the living room light.",
    "SET_BRIGHTNESS": "Set the living room light brightness 0-100 (e.g. SET_BRIGHTNESS:70).",
    "AC_ON": "Turn on the bedroom air conditioner.",
    "AC_OFF": "Turn off the bedroom air conditioner.",
    "SET_TEMP": "Set the bedroom AC temperature (e.g. SET_TEMP:24).",
    "FAN_ON": "Turn on the kitchen fan.",
    "FAN_OFF": "Turn off the kitchen fan.",
    "FAN_SPEED": "Set the kitchen fan speed 0-5 (e.g. FAN_SPEED:3).",
    "LOCK_DOOR": "Lock the main door.",
    "UNLOCK_DOOR": "Unlock the main door.",
    "ADD_TASK": "Add a task to the list (e.g. ADD_TASK:Call the dentist).",
    "REMOVE_TASK": "Remove a task by name (e.g. REMOVE_TASK:Water the plants).",
    "STATUS_REPORT": "Report the current state of all smart devices and tasks.",
}

def get_nlp_manifest() -> str:
    """Returns the command library manifest injected into the AI's system prompt."""
    lines = ["[ACTION] Command Library (use these EXACT tags to perform actions):"]
    for intent, desc in COMMAND_INTENTS.items():
        lines.append(f"- [ACTION:{intent}] -> {desc}")
    return "\n".join(lines)
