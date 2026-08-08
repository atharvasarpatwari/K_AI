COMMAND_INTENTS = {
    "LIGHT_ON": "Turn on the living room light.",
    "LIGHT_OFF": "Turn off the living room light.",
    "SET_TEMP": "Set the bedroom AC temperature (e.g. SET_TEMP:24).",
    "LOCK_DOOR": "Lock the main door.",
    "UNLOCK_DOOR": "Unlock the main door.",
    "ADD_TASK": "Add a task to the list (e.g. ADD_TASK:Call the dentist).",
}

def get_nlp_manifest() -> str:
    """Returns the command library manifest injected into the AI's system prompt."""
    lines = ["[ACTION] Command Library (use these EXACT tags to perform actions):"]
    for intent, desc in COMMAND_INTENTS.items():
        lines.append(f"- [ACTION:{intent}] -> {desc}")
    return "\n".join(lines)
