"""Loguru sink configuration."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from loguru import logger

LOG_DIR = Path(__file__).resolve().parent / "logs"

CONSOLE_FORMAT = "[<green>{time:YYYY-MM-DD HH:mm:ss}</green>] [<level>{level}</level>] {message}"


def _debug_enabled() -> bool:
    return os.getenv("DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}


def setup_logger() -> None:
    logger.remove()

    debug = _debug_enabled()
    file_level = "DEBUG" if debug else "INFO"

    if debug:
        logger.add(
            sys.stdout,
            colorize=None,
            format=CONSOLE_FORMAT,
            level="DEBUG",
        )
    else:
        logger.add(
            sys.stdout,
            colorize=None,
            format=CONSOLE_FORMAT,
            filter=lambda record: record["level"].name in {"INFO", "SUCCESS"},
        )

    logger.add(sys.stderr, colorize=None, format=CONSOLE_FORMAT, level="WARNING")

    # File logging is optional: if the log folder isn't writable, keep running
    # with console logs instead of crashing.
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)

        logger.add(
            LOG_DIR / "monitor.log",
            rotation="10 MB",
            retention="7 days",
            level=file_level,
            format=CONSOLE_FORMAT,
        )

        logger.add(
            LOG_DIR / "monitor.json",
            serialize=True,
            rotation="10 MB",
            retention="7 days",
            level=file_level,
            format=CONSOLE_FORMAT,
        )
    except OSError as error:
        logger.warning("File logging is unavailable in {}: {}", LOG_DIR, error)
