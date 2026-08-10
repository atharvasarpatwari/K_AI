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
    "TV_ON": "Turn on the living room TV.",
    "TV_OFF": "Turn off the living room TV.",
    "CURTAIN_OPEN": "Open the bedroom curtains.",
    "CURTAIN_CLOSE": "Close the bedroom curtains.",
    "HEATER_ON": "Turn on the bathroom water heater.",
    "HEATER_OFF": "Turn off the bathroom water heater.",
    "HEATER_TEMP": "Set the bathroom heater temperature (e.g. HEATER_TEMP:45).",
    "RESET_STATE": "Reset the smart home state back to defaults.",
    "SET_TIMER": "Set a timer (e.g. SET_TIMER:90 for seconds, SET_TIMER:3:minutes).",
    "CANCEL_TIMER": "Cancel a timer by label or index (e.g. CANCEL_TIMER:2).",
    "CHECK_TIMERS": "Report all pending timers.",
    "LOCK_DOOR": "Lock the main door.",
    "UNLOCK_DOOR": "Unlock the main door.",
    "ADD_TASK": "Add a task to the list (e.g. ADD_TASK:Call the dentist).",
    "REMOVE_TASK": "Remove a task by name (e.g. REMOVE_TASK:Water the plants).",
    "STATUS_REPORT": "Report the current state of all smart devices and tasks.",
    "WEATHER_REPORT": "Report the current weather for the user's location.",
}

SAFETY_INTENTS = frozenset({"UNLOCK_DOOR", "REMOVE_TASK"})

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
