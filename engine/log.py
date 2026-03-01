"""Timestamped logging for docx_builder engine.

All user-facing output goes through these helpers so that every line
carries an HH:MM:SS timestamp and a severity prefix (DEBUG / INFO /
WARN / ERROR).
"""

from __future__ import annotations

import datetime


def _stamp() -> str:
    """Return current time as HH:MM:SS."""
    return datetime.datetime.now().strftime("%H:%M:%S")


def debug(message: str) -> None:
    """Log a DEBUG-level message with timestamp."""
    print(f"[{_stamp()}] DEBUG  {message}")  # noqa: T201


def info(message: str) -> None:
    """Log an INFO-level message with timestamp."""
    print(f"[{_stamp()}] INFO   {message}")  # noqa: T201


def warn(message: str) -> None:
    """Log a WARN-level message with timestamp."""
    print(f"[{_stamp()}] WARN   {message}")  # noqa: T201


def error(message: str) -> None:
    """Log an ERROR-level message with timestamp."""
    print(f"[{_stamp()}] ERROR  {message}")  # noqa: T201
