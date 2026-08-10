import re
from contextlib import suppress
from typing import Any

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from keerthi.config import CONFIG

console = Console()


class PeripheralController:
    def __init__(self) -> None:
        self.tts_available = False
        self.stt_available = False
        self.engine: Any = None
        self.recognizer: Any = None
        self._vosk_model: Any = None
        self._whisper_model: Any = None

        self._init_tts()
        self._init_stt()

    def _init_tts(self) -> None:
        try:
            import pyttsx3  # type: ignore[import-untyped]
            self.engine = pyttsx3.init()
            self.engine.setProperty("rate", CONFIG["TTS_RATE"])
            self.tts_available = True
        except Exception:
            self.tts_available = False

    def _init_stt(self) -> None:
        try:
            import speech_recognition as sr  # type: ignore[import-untyped]
            self.recognizer = sr.Recognizer()
            self.recognizer.energy_threshold = 300
            self.recognizer.dynamic_energy_threshold = True
            self.stt_available = True
        except Exception:
            self.stt_available = False

    def speak(self, text: str) -> None:
        # Strip action tags for speech
        clean_text = re.sub(r"\[ACTION:.*?\]", "", text).strip()

        # Display in console with flair
        console.print(
            Panel(clean_text, title="[bold cyan]KEERTHI[/bold cyan]", border_style="cyan")
        )

        if self.tts_available and self.engine is not None:
            self.engine.say(clean_text)
            self.engine.runAndWait()

    def listen(self, use_microphone: bool | None = None) -> str:
        """Capture a voice command via microphone, falling back to text input."""
        mic_enabled = (
            CONFIG["USE_MICROPHONE"] if use_microphone is None else use_microphone
        )
        if self.stt_available and mic_enabled:
            utterance = self._listen_microphone()
            if utterance is not None:
                return utterance
            console.print("[dim]Microphone unavailable — falling back to text input.[/dim]")
        return self._listen_text()

    def _listen_microphone(self) -> str | None:
        try:
            import speech_recognition as sr
            with sr.Microphone() as source:
                console.print("[bold blue]Listening...[/bold blue]")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(source, timeout=10, phrase_time_limit=10)
        except sr.UnknownValueError:
            console.print("[dim]Couldn't make that out — try again or type it.[/dim]")
            return None
        except sr.RequestError:
            console.print("[dim]Speech service unreachable — using text input.[/dim]")
            return None
        except Exception:
            console.print("[dim]Microphone error — using text input.[/dim]")
            return None

        text = self._transcribe(audio)
        if text:
            console.print(f"[bold blue]You:[/bold blue] {text}")
            return text
        console.print("[dim]Couldn't make that out — try again or type it.[/dim]")
        return None

    def _transcribe(self, audio: Any) -> str:
        """Transcribes audio with the configured engine, falling back to Google."""
        engine = CONFIG["STT_ENGINE"]
        if engine == "vosk":
            text = self._transcribe_vosk(audio)
            if text:
                return text
        elif engine == "whisper":
            text = self._transcribe_whisper(audio)
            if text:
                return text
        return self._transcribe_google(audio)

    def _transcribe_google(self, audio: Any) -> str:
        try:
            return str(self.recognizer.recognize_google(audio, language=CONFIG["STT_LANGUAGE"]))
        except Exception:
            return ""

    def _transcribe_vosk(self, audio: Any) -> str:
        try:
            import json

            import vosk

            if self._vosk_model is None:
                self._vosk_model = vosk.Model(CONFIG["VOSK_MODEL_PATH"])
            recognizer = vosk.KaldiRecognizer(self._vosk_model, 16000)
            data = audio.get_raw_data(convert_rate=16000, convert_width=2)
            if not recognizer.AcceptWaveform(data):
                return ""
            result = json.loads(recognizer.Result())
            return str(result.get("text", "").strip())
        except Exception:
            return ""

    def _transcribe_whisper(self, audio: Any) -> str:
        try:
            import numpy as np
            from faster_whisper import WhisperModel

            if self._whisper_model is None:
                self._whisper_model = WhisperModel(
                    CONFIG["WHISPER_MODEL"],
                    device=CONFIG["WHISPER_DEVICE"],
                    compute_type="auto",
                )
            raw = audio.get_raw_data(convert_rate=16000, convert_width=2)
            samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
            language = CONFIG["STT_LANGUAGE"].split("-")[0]
            segments, _info = self._whisper_model.transcribe(samples, language=language)
            return " ".join(segment.text for segment in segments).strip()
        except Exception:
            return ""

    def _listen_text(self) -> str:
        try:
            return input(f"\n [bold blue]{CONFIG['USER_NAME']}:[/bold blue] ")
        except EOFError:
            return "exit"

    def close(self) -> None:
        """Releases TTS and speech resources."""
        if self.engine is not None:
            with suppress(Exception):
                self.engine.stop()

    def show_dashboard(self, state: dict[str, Any]) -> None:
        table = Table(title="System Status", box=box.ROUNDED)
        table.add_column("Category", style="cyan")
        table.add_column("Details", style="white")

        # Devices
        dev_str = ", ".join(
            [f"{k}: {v.get('status', 'unknown')}" for k, v in state["devices"].items()]
        )
        table.add_row("Smart Home", dev_str)

        # Tasks
        task_str = " | ".join(state["tasks"][-3:])
        table.add_row("Recent Tasks", task_str)

        console.print(table)
