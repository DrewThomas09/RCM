"""Epic PMS connector stub (Prompt 76).

Placeholder implementation — real FHIR R4 integration is a future sprint.
All methods return empty results so the connector can be instantiated
and wired through tests without network access.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

from .base import PMSConnector

logger = logging.getLogger(__name__)


class EpicConnector(PMSConnector):
    """Stub Epic FHIR connector.

    Config expects:
      - ``base_url``:  Epic FHIR endpoint (e.g. https://fhir.epic.com/R4)
      - ``client_id``: OAuth2 client ID
      - ``private_key``: JWT signing key (PEM)
    """

    def test_connection(self) -> bool:
        """Placeholder — always returns False until FHIR auth is wired."""
        base_url = self.config.get("base_url", "")
        if not base_url:
            logger.warning("EpicConnector: no base_url configured")
            return False
        # Future: POST to /oauth2/token, GET /metadata
        logger.info("EpicConnector: test_connection stub for %s", base_url)
        return False

    def pull_encounters(self, date_range: Tuple[str, str]) -> list[dict]:
        """Placeholder — returns empty list."""
        logger.info(
            "EpicConnector: pull_encounters stub %s–%s",
            date_range[0], date_range[1],
        )
        return []

    def pull_charges(self, date_range: Tuple[str, str]) -> list[dict]:
        """Placeholder — returns empty list."""
        logger.info(
            "EpicConnector: pull_charges stub %s–%s",
            date_range[0], date_range[1],
        )
        return []

    def pull_ar_aging(self) -> dict:
        """Placeholder — returns empty dict."""
        logger.info("EpicConnector: pull_ar_aging stub")
        return {}
