"""
Centralized logging for the rcm_mc package.

Usage in any module:
    from .logger import logger
    logger.warning("something happened")
"""
from __future__ import annotations

import logging

logger = logging.getLogger("rcm_mc")

if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(
        logging.Formatter("[%(levelname)s] rcm_mc: %(message)s")
    )
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)
