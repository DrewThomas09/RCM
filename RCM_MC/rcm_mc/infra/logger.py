"""
Centralized logging for the rcm_mc package.

Usage in any module:
    from .logger import logger
    logger.warning("something happened")

Log level is configurable via the ``LOG_LEVEL`` environment variable
(``DEBUG`` / ``INFO`` / ``WARNING`` / ``ERROR`` / ``CRITICAL``); when
unset or unrecognised, falls back to ``INFO``. This lets Azure App
Service Configuration tighten verbosity in production without a
code change.
"""
from __future__ import annotations

import logging
import os


def _resolve_log_level() -> int:
    """Map ``LOG_LEVEL`` env var to a stdlib logging constant.

    Defaults to ``INFO`` when the env is unset or holds a value that
    isn't a recognised level name. Numeric strings (``"10"``, ``"20"``)
    are also accepted for parity with deployment templates that pass
    integer levels.
    """
    raw = (os.environ.get("LOG_LEVEL") or "").strip()
    if not raw:
        return logging.INFO
    try:
        return int(raw)
    except ValueError:
        pass
    level = logging.getLevelName(raw.upper())
    if isinstance(level, int):
        return level
    return logging.INFO


logger = logging.getLogger("rcm_mc")

if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(
        logging.Formatter("[%(levelname)s] rcm_mc: %(message)s")
    )
    logger.addHandler(_handler)
    logger.setLevel(_resolve_log_level())
