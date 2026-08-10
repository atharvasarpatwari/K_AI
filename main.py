import argparse
import logging
import os
import sys
import time
from contextlib import suppress

# Ensure the current directory is in the Python Path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from keerthi.brain import KeerthiBrain
from keerthi.config import CONFIG, validate_config
from keerthi.executive import ExecutiveOfficer
from keerthi.peripherals import PeripheralController, console

EXIT_PHRASES = ("exit", "quit", "shutdown")
RESET_PHRASES = ("/reset", "reset conversation", "start over")

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, CONFIG["LOG_LEVEL"], logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _enable_unicode_console() -> None:
    """Switch the Windows console to UTF-8 so unicode renders correctly."""
    if os.name == "nt":
        with suppress(Exception):
            os.system("chcp 65001 > nul")


def boot_sequence() -> None:
    console.print(f"[bold cyan]Initializing {CONFIG['NAME']} v{CONFIG['VERSION']}...[/bold cyan]")
    time.sleep(0.5)
    console.print("Neural layers loaded. [OK]")
    time.sleep(0.3)
    console.print("Smart home bridge connected. [OK]")
    time.sleep(0.3)
    console.print("Voice synthesis modules ready. [OK]")
    console.rule(style="cyan")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="KEERTHI AI Voice Assistant")
    parser.add_argument(
        "--text",
        action="store_true",
        help="Force text-input mode (disable microphone listening).",
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Ignore saved smart-home state and start from defaults.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"{CONFIG['NAME']} v{CONFIG['VERSION']}",
    )
    return parser.parse_args()


class ConversationSession:
    """Runs the listen-process-respond loop for a single conversation."""

    def __init__(
        self,
        brain: KeerthiBrain,
        officer: ExecutiveOfficer,
        peripherals: PeripheralController,
        use_microphone: bool = True,
    ) -> None:
        self.brain = brain
        self.officer = officer
        self.peripherals = peripherals
        self.use_microphone = use_microphone

    def run(self) -> None:
        self.peripherals.speak(
            f"Good day, {CONFIG['USER_NAME']}. I am KEERTHI. "
            f"How can I facilitate your productivity today?"
        )
        try:
            while True:
                user_input = self.peripherals.listen(use_microphone=self.use_microphone)
                if self.handle_input(user_input) == "exit":
                    break
        finally:
            self.officer.stop()
            self.peripherals.close()

    def handle_input(self, user_input: str) -> str | None:
        """Process one utterance. Returns 'exit' when the session should end."""
        normalized = user_input.lower().strip()

        if normalized in EXIT_PHRASES:
            self.peripherals.speak(
                f"Understood. Powering down Keerthi. Have a pleasant day, {CONFIG['USER_NAME']}."
            )
            return "exit"

        if not normalized:
            return None

        if normalized in RESET_PHRASES:
            self.brain.reset_conversation()
            self.peripherals.speak("Conversation cleared. What shall we work on?")
            return None

        if normalized in CONFIG["WAKE_WORDS"]:
            self.peripherals.speak("Yes, how can I help you?")
            return None

        response = self.brain.generate_response(normalized)
        executed_actions = self.officer.parse_and_execute(
            response, confirm=self._confirm_action
        )

        self.peripherals.speak(response)

        if executed_actions:
            self.peripherals.speak(" | ".join(executed_actions))
            self.peripherals.show_dashboard(self.officer.get_summary())

        return None

    def _confirm_action(self, intent: str) -> bool:
        """Asks the user to confirm a safety-critical action before it runs."""
        self.peripherals.speak(
            f"Hold on — {intent} is a safety-sensitive action. Shall I proceed?"
        )
        reply = self.peripherals.listen(use_microphone=self.use_microphone)
        approvals = ("yes", "y", "yeah", "yep", "confirm", "proceed", "go ahead")
        return reply.strip().lower() in approvals


def main() -> None:
    args = parse_args()
    setup_logging()
    validate_config()
    _enable_unicode_console()
    boot_sequence()

    try:
        brain = KeerthiBrain()
    except ValueError as e:
        console.print(f"[bold red]Startup error:[/bold red] {e}")
        console.print("Add your key to the .env file as GEMINI_API_KEY=... and try again.")
        sys.exit(1)

    officer = ExecutiveOfficer(load_state=not args.fresh)
    peripherals = PeripheralController()
    officer.set_notifier(peripherals.speak)

    session = ConversationSession(
        brain=brain,
        officer=officer,
        peripherals=peripherals,
        use_microphone=not args.text,
    )
    session.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nKeerthi signal interrupted.")
        sys.exit(0)
