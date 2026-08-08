import os
import warnings
from dotenv import load_dotenv

load_dotenv()


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


CONFIG = {
    "NAME": "KEERTHI",
    "FULL_NAME": "Knowledge-Enhanced Engine for Real-Time Human Intelligence",
    "VERSION": "2.0.0",
    "USER_NAME": "Atharva",
    "LOCATION": "Hyderabad, India",
    "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
    "MODEL_NAME": os.getenv("MODEL_NAME", "gemini-1.5-flash"),
    "TTS_RATE": _env_int("TTS_RATE", 175),
    "WAKE_WORDS": ["keerthi", "hey keerthi", "ok keerthi"],
    "USE_MICROPHONE": _env_bool("USE_MICROPHONE", True),
    "STT_LANGUAGE": os.getenv("STT_LANGUAGE", "en-IN"),
    "MAX_HISTORY_TURNS": _env_int("MAX_HISTORY_TURNS", 10),
    "TEMPERATURE": float(os.getenv("TEMPERATURE", "0.7")),
    "MAX_OUTPUT_TOKENS": _env_int("MAX_OUTPUT_TOKENS", 1024),
    "TOP_P": float(os.getenv("TOP_P", "0.95")),
    "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO").upper(),
    "STATE_FILE": os.getenv("STATE_FILE", "keerthi_state.json"),
}

# Initial state for simulation
INITIAL_STATE = {
    "devices": {
        "living_room_light": {"status": "off", "brightness": 0},
        "bedroom_ac": {"status": "on", "temp": 22},
        "main_door": {"status": "locked"},
        "kitchen_fan": {"status": "off", "speed": 0}
    },
    "tasks": [
        "Review project proposal",
        "Call the dentist",
        "Water the indoor plants"
    ]
}

_VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


def validate_config() -> None:
    """Emits warnings for invalid or unsafe configuration values."""
    if not CONFIG["GEMINI_API_KEY"]:
        warnings.warn("GEMINI_API_KEY is missing — brain calls will fail at runtime.", RuntimeWarning)

    if CONFIG["LOG_LEVEL"] not in _VALID_LOG_LEVELS:
        warnings.warn(f"Invalid LOG_LEVEL '{CONFIG['LOG_LEVEL']}' — using INFO.", RuntimeWarning)

    if not 0.0 <= CONFIG["TEMPERATURE"] <= 2.0:
        warnings.warn(f"TEMPERATURE {CONFIG['TEMPERATURE']} outside range [0.0, 2.0].", RuntimeWarning)

    if CONFIG["MAX_OUTPUT_TOKENS"] <= 0:
        warnings.warn("MAX_OUTPUT_TOKENS must be positive.", RuntimeWarning)

    if CONFIG["MAX_HISTORY_TURNS"] <= 0:
        warnings.warn("MAX_HISTORY_TURNS must be positive.", RuntimeWarning)

    if not 50 <= CONFIG["TTS_RATE"] <= 400:
        warnings.warn(f"TTS_RATE {CONFIG['TTS_RATE']} outside comfortable range [50, 400].", RuntimeWarning)
