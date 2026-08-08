import re
from typing import Optional

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
        self.engine = None
        self.recognizer = None

        self._init_tts()
        self._init_stt()

    def _init_tts(self) -> None:
        try:
            import pyttsx3
            self.engine = pyttsx3.init()
            self.engine.setProperty("rate", CONFIG["TTS_RATE"])
            self.tts_available = True
        except Exception:
            self.tts_available = False

    def _init_stt(self) -> None:
        try:
            import speech_recognition as sr
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
        console.print(Panel(clean_text, title="[bold cyan]KEERTHI[/bold cyan]", border_style="cyan"))

        if self.tts_available and self.engine is not None:
            self.engine.say(clean_text)
            self.engine.runAndWait()

    def listen(self, use_microphone: Optional[bool] = None) -> str:
        """Capture a voice command via microphone, falling back to text input."""
        if self.stt_available and (CONFIG["USE_MICROPHONE"] if use_microphone is None else use_microphone):
            utterance = self._listen_microphone()
            if utterance is not None:
                return utterance
            console.print("[dim]Microphone unavailable — falling back to text input.[/dim]")
        return self._listen_text()

    def _listen_microphone(self) -> Optional[str]:
        try:
            import speech_recognition as sr
            with sr.Microphone() as source:
                console.print("[bold blue]Listening...[/bold blue]")
                audio = self.recognizer.listen(source, timeout=10, phrase_time_limit=10)
            text = self.recognizer.recognize_google(audio, language=CONFIG["STT_LANGUAGE"])
            console.print(f"[bold blue]You:[/bold blue] {text}")
            return text
        except sr.UnknownValueError:
            console.print("[dim]Couldn't make that out — try again or type it.[/dim]")
        except sr.RequestError:
            console.print("[dim]Speech service unreachable — using text input.[/dim]")
        except Exception:
            console.print("[dim]Microphone error — using text input.[/dim]")
        return None

    def _listen_text(self) -> str:
        try:
            return input(f"\n [bold blue]{CONFIG['USER_NAME']}:[/bold blue] ")
        except EOFError:
            return "exit"

    def show_dashboard(self, state: dict) -> None:
        table = Table(title="System Status", box=box.ROUNDED)
        table.add_column("Category", style="cyan")
        table.add_column("Details", style="white")

        # Devices
        dev_str = ", ".join([f"{k}: {v['status']}" for k, v in state["devices"].items()])
        table.add_row("Smart Home", dev_str)

        # Tasks
        task_str = " | ".join(state["tasks"][-3:])
        table.add_row("Recent Tasks", task_str)

        console.print(table)
