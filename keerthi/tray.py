"""System tray integration for KEERTHI.

Uses pystray + Pillow (Windows-only, lazily imported) so the module stays
importable on CI. The icon offers an "Open Dashboard" default action and a
"Quit KEERTHI" action wired to an optional callback.
"""

import threading
from collections.abc import Callable
from contextlib import suppress
from typing import Any

from keerthi.config import CONFIG


def _load_pystray() -> Any | None:
    try:
        import pystray

        return pystray
    except Exception:
        return None


def _icon_image() -> Any:
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (64, 64), "black")
    draw = ImageDraw.Draw(image)
    draw.ellipse((8, 8, 56, 56), fill="cyan")
    draw.rectangle((23, 23, 41, 41), fill="black")
    draw.rectangle((29, 23, 35, 41), fill="black")
    return image


def start_tray(
    on_quit: Callable[[], None] | None = None,
    dashboard_url: str | None = None,
) -> bool:
    """Starts a tray icon in a daemon thread; returns False when unavailable."""
    pystray = _load_pystray()
    if pystray is None:
        return False
    import webbrowser

    url = dashboard_url or CONFIG["DASHBOARD_URL"]

    def _open_dashboard(_icon: Any, _item: Any) -> None:
        with suppress(Exception):
            webbrowser.open(url)

    def _quit(_icon: Any, _item: Any) -> None:
        if on_quit is not None:
            with suppress(Exception):
                on_quit()
        with suppress(Exception):
            _icon.stop()

    menu = pystray.Menu(
        pystray.MenuItem("Open Dashboard", _open_dashboard, default=True),
        pystray.MenuItem("Quit KEERTHI", _quit),
    )
    icon = pystray.Icon("keerthi", _icon_image(), "KEERTHI", menu)
    thread = threading.Thread(target=icon.run, daemon=True)
    thread.start()
    return True
