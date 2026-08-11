"""Centralised logging setup for KEERTHI.

Attaches a rotating file handler to the ``keerthi`` logger tree so both the
CLI (``main.py``) and the web server (``server.py``) write to the same log
file. Idempotent — safe to call from multiple entry points.
"""

import logging
from logging.handlers import RotatingFileHandler
from typing import Any

from keerthi.config import CONFIG

_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def setup_file_logging(handler_kwargs: dict[str, Any] | None = None) -> None:
    """Attaches a rotating file handler to the ``keerthi`` logger tree."""
    root = logging.getLogger("keerthi")
    if any(isinstance(h, RotatingFileHandler) for h in root.handlers):
        return

    kwargs: dict[str, Any] = {
        "maxBytes": 1_000_000,
        "backupCount": 2,
        "encoding": "utf-8",
    }
    if handler_kwargs:
        kwargs.update(handler_kwargs)

    handler = RotatingFileHandler(CONFIG["LOG_FILE"], **kwargs)
    handler.setFormatter(logging.Formatter(_FORMAT))
    root.addHandler(handler)
    root.setLevel(CONFIG["LOG_LEVEL"])
    root.propagate = True
