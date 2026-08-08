import argparse
import logging
import os
import sys
import time

# Ensure the current directory is in the Python Path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from keerthi.config import CONFIG
from keerthi.brain import KeerthiBrain
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
        "--version",
        action="version",
        version=f"{CONFIG['NAME']} v{CONFIG['VERSION']}",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    setup_logging()
    boot_sequence()

    try:
        brain = KeerthiBrain()
    except ValueError as e:
        console.print(f"[bold red]Startup error:[/bold red] {e}")
        console.print("Add your key to the .env file as GEMINI_API_KEY=... and try again.")
        sys.exit(1)

    officer = ExecutiveOfficer()
    peripherals = PeripheralController()

    peripherals.speak(
        f"Good day, {CONFIG['USER_NAME']}. I am KEERTHI. "
        f"How can I facilitate your productivity today?"
    )

    while True:
        # 1. Listen for input
        user_input = peripherals.listen(use_microphone=not args.text)

        if user_input.lower().strip() in EXIT_PHRASES:
            peripherals.speak(
                f"Understood. Powering down Keerthi. Have a pleasant day, {CONFIG['USER_NAME']}."
            )
            break

        if not user_input.strip():
            continue

        # 2. Reset conversation
        if user_input.lower().strip() in RESET_PHRASES:
            brain.reset_conversation()
            peripherals.speak("Conversation cleared. What shall we work on?")
            continue

        # 3. Wake word acknowledgment
        if user_input.lower().strip() in CONFIG["WAKE_WORDS"]:
            peripherals.speak("Yes, how can I help you?")
            continue

        # 4. Process with AI
        response = brain.generate_response(user_input.strip())

        # 5. Handle Actions
        executed_actions = officer.parse_and_execute(response)

        # 6. Speak response
        peripherals.speak(response)

        # 7. Confirm executed actions and show internal status
        if executed_actions:
            peripherals.speak(" | ".join(executed_actions))
            peripherals.show_dashboard(officer.get_summary())


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nKeerthi signal interrupted.")
        sys.exit(0)
