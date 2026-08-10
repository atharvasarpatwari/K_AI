import os
import warnings
from typing import TypedDict

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


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except ValueError:
        return default


class ConfigDict(TypedDict):
    NAME: str
    FULL_NAME: str
    VERSION: str
    USER_NAME: str
    LOCATION: str
    GEMINI_API_KEY: str | None
    MODEL_NAME: str
    TTS_RATE: int
    WAKE_WORDS: list[str]
    USE_MICROPHONE: bool
    STT_LANGUAGE: str
    STT_ENGINE: str
    VOSK_MODEL_PATH: str
    WHISPER_MODEL: str
    WHISPER_DEVICE: str
    MAX_HISTORY_TURNS: int
    TEMPERATURE: float
    MAX_OUTPUT_TOKENS: int
    TOP_P: float
    LOG_LEVEL: str
    STATE_FILE: str


CONFIG: ConfigDict = {
    "NAME": "KEERTHI",
    "FULL_NAME": "Knowledge-Enhanced Engine for Real-Time Human Intelligence",
    "VERSION": "2.2.0",
    "USER_NAME": "Atharva",
    "LOCATION": "Hyderabad, India",
    "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
    "MODEL_NAME": os.getenv("MODEL_NAME", "gemini-2.5-flash"),
    "TTS_RATE": _env_int("TTS_RATE", 175),
    "WAKE_WORDS": ["keerthi", "hey keerthi", "ok keerthi"],
    "USE_MICROPHONE": _env_bool("USE_MICROPHONE", True),
    "STT_LANGUAGE": os.getenv("STT_LANGUAGE", "en-IN"),
    "STT_ENGINE": os.getenv("STT_ENGINE", "google").lower(),
    "VOSK_MODEL_PATH": os.getenv("VOSK_MODEL_PATH", "vosk-model-small-en-us-0.15"),
    "WHISPER_MODEL": os.getenv("WHISPER_MODEL", "small.en"),
    "WHISPER_DEVICE": os.getenv("WHISPER_DEVICE", "auto").lower(),
    "MAX_HISTORY_TURNS": _env_int("MAX_HISTORY_TURNS", 10),
    "TEMPERATURE": _env_float("TEMPERATURE", 0.7),
    "MAX_OUTPUT_TOKENS": _env_int("MAX_OUTPUT_TOKENS", 1024),
    "TOP_P": _env_float("TOP_P", 0.95),
    "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO").upper(),
    "STATE_FILE": os.getenv("STATE_FILE", "keerthi_state.json"),
}

# Initial state for simulation
INITIAL_STATE = {
    "devices": {
        "living_room_light": {"status": "off", "brightness": 0},
        "bedroom_ac": {"status": "on", "temp": 22},
        "main_door": {"status": "locked"},
        "kitchen_fan": {"status": "off", "speed": 0},
        "living_room_tv": {"status": "off"},
        "bedroom_curtains": {"status": "closed"},
        "bathroom_heater": {"status": "off", "temp": 40}
    },
    "tasks": [
        "Review project proposal",
        "Call the dentist",
        "Water the indoor plants"
    ],
    "timers": []
}

_VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
_RETIRED_MODEL_PREFIXES = ("gemini-1.5", "gemini-2.0-flash")


def validate_config() -> None:
    """Emits warnings for invalid or unsafe configuration values."""
    if not CONFIG["GEMINI_API_KEY"]:
        warnings.warn(
            "GEMINI_API_KEY is missing — brain calls will fail at runtime.",
            RuntimeWarning,
            stacklevel=2,
        )

    if CONFIG["MODEL_NAME"].startswith(_RETIRED_MODEL_PREFIXES):
        warnings.warn(
            f"MODEL_NAME '{CONFIG['MODEL_NAME']}' is retired — use a current model "
            "such as gemini-2.5-flash.",
            RuntimeWarning,
            stacklevel=2,
        )

    if CONFIG["LOG_LEVEL"] not in _VALID_LOG_LEVELS:
        warnings.warn(
            f"Invalid LOG_LEVEL '{CONFIG['LOG_LEVEL']}' — using INFO.",
            RuntimeWarning,
            stacklevel=2,
        )

    if not 0.0 <= CONFIG["TEMPERATURE"] <= 2.0:
        warnings.warn(
            f"TEMPERATURE {CONFIG['TEMPERATURE']} outside range [0.0, 2.0].",
            RuntimeWarning,
            stacklevel=2,
        )

    if not 0.0 < CONFIG["TOP_P"] <= 1.0:
        warnings.warn(
            f"TOP_P {CONFIG['TOP_P']} outside range (0.0, 1.0].",
            RuntimeWarning,
            stacklevel=2,
        )

    if CONFIG["MAX_OUTPUT_TOKENS"] <= 0:
        warnings.warn(
            "MAX_OUTPUT_TOKENS must be positive.",
            RuntimeWarning,
            stacklevel=2,
        )

    if CONFIG["MAX_HISTORY_TURNS"] <= 0:
        warnings.warn(
            "MAX_HISTORY_TURNS must be positive.",
            RuntimeWarning,
            stacklevel=2,
        )

    if not 50 <= CONFIG["TTS_RATE"] <= 400:
        warnings.warn(
            f"TTS_RATE {CONFIG['TTS_RATE']} outside comfortable range [50, 400].",
            RuntimeWarning,
            stacklevel=2,
        )

    if CONFIG["STT_ENGINE"] not in ("google", "vosk", "whisper"):
        warnings.warn(
            f"STT_ENGINE '{CONFIG['STT_ENGINE']}' unknown — using google.",
            RuntimeWarning,
            stacklevel=2,
        )
