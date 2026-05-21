"""Tiny download helper shared by cms_hcris / cms_care_compare /
cms_utilization / irs990_loader.

Why its own module: the four public-data loaders all need the same
``(cache dir, atomic fetch, respectful retry)`` primitive, and tests
need a single seam to monkey-patch for mocking HTTP. Keep the surface
small — anything fancier (progress bars, parallel fetch) belongs in the
caller, not here.
"""
from __future__ import annotations

import logging
import os
import shutil
import ssl
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_CACHE_ENV = "RCM_MC_DATA_CACHE"
_USER_AGENT = "rcm-mc/1.0 (+https://github.com/anthropics/rcm-mc)"

_SSL_CTX: Optional[ssl.SSLContext] = None


def ssl_context() -> ssl.SSLContext:
    """Shared TLS context for every public-data fetch (CMS / IRS / SEC).

    python.org Python builds (common on macOS) ship without a usable
    system trust store, so ``urlopen`` against https://data.cms.gov,
    the IRS, or SEC EDGAR fails with CERTIFICATE_VERIFY_FAILED and the
    loaders silently fall back to estimates. When the optional ``certifi``
    package is importable we point the context at its CA bundle so
    verification succeeds; otherwise we use the stdlib default. The import
    is guarded — certifi is NOT a hard dependency, so environments without
    it keep their existing graceful-degradation behaviour. Cached so we
    build the context once.
    """
    global _SSL_CTX
    if _SSL_CTX is None:
        try:
            import certifi  # optional; not a declared runtime dep
            _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
        except Exception:
            _SSL_CTX = ssl.create_default_context()
    return _SSL_CTX


class CMSDownloadError(RuntimeError):
    """Raised when a download fails after all retries."""


def cache_dir(source: str) -> Path:
    """Return the cache directory for ``source`` (created if missing).

    Precedence: ``$RCM_MC_DATA_CACHE/<source>`` if set, else
    ``~/.rcm_mc/data/<source>``, else a temp directory (CI/airgap).
    """
    override = os.environ.get(_CACHE_ENV)
    if override:
        p = Path(override) / source
    else:
        home = os.environ.get("HOME") or os.environ.get("USERPROFILE")
        if home:
            p = Path(home) / ".rcm_mc" / "data" / source
        else:
            p = Path(tempfile.gettempdir()) / "rcm_mc_data" / source
    p.mkdir(parents=True, exist_ok=True)
    return p


def fetch_url(
    url: str,
    dest: Path,
    *,
    timeout: float = 60.0,
    overwrite: bool = False,
) -> Path:
    """Download ``url`` to ``dest``. Atomic: writes to ``dest.part`` first.

    Tests monkey-patch this function directly to avoid hitting CMS during
    unit tests. Raises :class:`CMSDownloadError` on any network failure.

    When ``overwrite`` is False and ``dest`` already exists, returns
    immediately — this keeps the second call cheap during development.
    """
    dest = Path(dest)
    if dest.exists() and not overwrite:
        logger.debug("cache hit: %s", dest)
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl_context()) as resp:
            with open(part, "wb") as fh:
                shutil.copyfileobj(resp, fh)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        part.unlink(missing_ok=True)
        raise CMSDownloadError(f"fetch failed for {url}: {exc}") from exc
    part.replace(dest)
    return dest


#
# Test note: consumers import this module as ``_cms_download`` and call
# ``_cms_download.fetch_url(...)`` at each use site, so monkey-patching
# ``rcm_mc.data._cms_download.fetch_url`` in a test swaps the live
# download for a stub without touching the callers.
