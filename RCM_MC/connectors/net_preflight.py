"""Bounded network reachability preflight for opt-in networked jobs.

The NPI cleaner's deep-recovery mode is a networked batch job guarded by a
wall-clock watchdog. On a no-egress box the job used to hold its progress bar
for the full watchdog (minutes) before the honest timeout message; a single
bounded TCP connect answers "can this box plausibly reach data.cms.gov?" in
seconds.

This lives in the connectors namespace — the codebase's home for code that is
*allowed* to touch the network — so the offline cleaner package
(``rcm_mc.npi_cleaner``) stays free of network modules. Callers import it
lazily and treat an ImportError as "no preflight available: proceed and let
the watchdog guard", which is exactly the pre-preflight behavior.
"""
from __future__ import annotations

import os
import socket
from urllib.parse import urlparse

#: Default TCP-connect budget in seconds. Small enough that a blocked box
#: answers fast, large enough for a slow-but-real route.
DEFAULT_TIMEOUT_S = 4.0

#: The origin deep recovery actually needs (CMS data catalog).
_CMS_HOST, _CMS_PORT = "data.cms.gov", 443


def can_reach_cms(timeout: float = DEFAULT_TIMEOUT_S) -> bool:
    """Can this box plausibly reach data.cms.gov? A single bounded TCP
    connect — to the configured HTTPS proxy when one is set (the HTTP client
    would route through it, so probing the origin directly would falsely
    fail), otherwise to the origin itself. Never raises."""
    host, port = _CMS_HOST, _CMS_PORT
    proxy = (os.environ.get("HTTPS_PROXY")
             or os.environ.get("https_proxy") or "").strip()
    if proxy:
        try:
            p = urlparse(proxy if "://" in proxy else "//" + proxy)
            if p.hostname:
                host, port = p.hostname, int(p.port or 3128)
        except (ValueError, TypeError):
            pass
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False
