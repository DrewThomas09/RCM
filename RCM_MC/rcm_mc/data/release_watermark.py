"""Release-detection watermark for public-data sources.

This is the *front of the pipe* described in
``SECOND_AGENT_BUILD_PROMPT.md`` Appendix A. The existing incremental
layer (``hcris_incremental``) already avoids re-loading rows it has
seen, but a cron-driven ``refresh_all_sources`` still has to *enumerate*
candidate work to discover there is nothing new — for HCRIS that means
touching multi-GB filings. CMS publishes most datasets on a quarterly /
monthly cadence by overwriting the published file; between releases the
file is byte-identical. A cheap watermark on the *publication* lets a
refresh short-circuit before any parse.

The watermark is a small opaque fingerprint string per source:

  - HTTP sources: ``ETag`` if present, else ``Last-Modified`` +
    ``Content-Length`` (cheap, served by a HEAD request — no body).
  - Local files: ``size`` + ``mtime`` (cheap) or a content hash
    (``file_content_fingerprint``) for files small enough to hash.

A source is "changed" when its current fingerprint differs from the
stored one, or when we *can't tell* (``None`` fingerprint — e.g. the
HEAD request failed): unknown always means refresh, so a flaky probe
degrades to today's always-refresh behavior rather than silently
skipping a real update.

Stored in its own ``release_watermark`` table so this module owns its
schema (mirrors how ``data_refresh`` owns ``data_source_status``).
Stdlib + SQLite only; no new runtime dependencies.
"""
from __future__ import annotations

import hashlib
import logging
import urllib.error
import urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)

# Chunk size for hashing local files without loading them whole — the
# NMRC/ALPHA filings exceed 2GB, so never read a candidate file in one
# shot even when computing a content hash.
_HASH_CHUNK = 1 << 20  # 1 MiB


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Table ─────────────────────────────────────────────────────────────

def _ensure_table(store: Any) -> None:
    store.init_db()
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS release_watermark (
                source_name TEXT PRIMARY KEY,
                fingerprint TEXT,
                fingerprint_kind TEXT,
                source_ref TEXT,
                checked_at TEXT
            )"""
        )
        con.commit()


# ── Fingerprint construction ──────────────────────────────────────────

def fingerprint_from_http_headers(headers: Any) -> Optional[str]:
    """Build a fingerprint from an HTTP response/HEAD header mapping.

    Prefers ``ETag`` (servers compute it to mean exactly "did the body
    change"). Falls back to ``Last-Modified`` + ``Content-Length`` which
    together change whenever CMS republishes. Returns ``None`` when the
    server exposes neither — the caller must then treat the source as
    changed (we can't prove it didn't).

    Accepts anything with a case-insensitive ``.get`` (``http.client``
    ``HTTPMessage``, a plain dict with lowercased keys, etc.).
    """
    if headers is None:
        return None
    get = getattr(headers, "get", None)
    if get is None:
        return None
    etag = get("ETag") or get("etag")
    if etag:
        # Strip the weak-validator prefix so W/"x" and "x" compare equal
        # only when the server really means them to; we keep them
        # distinct because a weak ETag is a weaker promise.
        return f"etag:{etag.strip()}"
    last_mod = get("Last-Modified") or get("last-modified")
    length = get("Content-Length") or get("content-length")
    if last_mod or length:
        # Normalize Last-Modified to an ISO instant so equal timestamps
        # in different header spellings compare equal.
        norm = last_mod
        if last_mod:
            try:
                dt = parsedate_to_datetime(last_mod)
                if dt is not None:
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    norm = dt.astimezone(timezone.utc).isoformat()
            except (TypeError, ValueError):
                norm = last_mod
        return f"lm:{norm or ''}|len:{length or ''}"
    return None


def file_stat_fingerprint(path: Any) -> Optional[str]:
    """Cheap local-file fingerprint: size + mtime. ``None`` if missing.

    Use for the big filings where hashing the whole file each cron tick
    is wasteful. mtime can change without content changing (a re-download
    rewrites it), so this errs toward "changed" — acceptable, since a
    false "changed" just costs one extra parse, while a false "unchanged"
    would silently drop a real update.
    """
    p = Path(path)
    try:
        st = p.stat()
    except (OSError, ValueError):
        return None
    mtime = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat()
    return f"size:{st.st_size}|mtime:{mtime}"


def file_content_fingerprint(path: Any) -> Optional[str]:
    """Content hash for files small enough to justify reading. Chunked
    so it never loads the whole file into memory. ``None`` if missing.
    """
    p = Path(path)
    h = hashlib.sha256()
    try:
        with p.open("rb") as fh:
            for chunk in iter(lambda: fh.read(_HASH_CHUNK), b""):
                h.update(chunk)
    except (OSError, ValueError):
        return None
    return f"sha256:{h.hexdigest()}"


def http_head_fingerprint(url: str, *, timeout: float = 15.0) -> Optional[str]:
    """Best-effort HEAD probe → fingerprint, or ``None`` on any failure.

    Network access is governed by the environment's policy and may be
    blocked; this must never raise. A ``None`` return means "couldn't
    tell" and the caller treats the source as changed. Kept out of the
    orchestrator's hot path so tests never touch the network — they pass
    fingerprints in directly.
    """
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return fingerprint_from_http_headers(resp.headers)
    except (urllib.error.URLError, ValueError, OSError) as exc:
        logger.debug("HEAD probe failed for %s: %s", url, exc)
        return None


# ── Read / write ──────────────────────────────────────────────────────

def get_watermark(store: Any, source_name: str) -> Optional[Dict[str, Any]]:
    _ensure_table(store)
    with store.connect() as con:
        row = con.execute(
            "SELECT * FROM release_watermark WHERE source_name = ?",
            (str(source_name),),
        ).fetchone()
    return dict(row) if row is not None else None


def record_release(
    store: Any,
    source_name: str,
    fingerprint: Optional[str],
    *,
    kind: str = "unknown",
    source_ref: Optional[str] = None,
) -> None:
    """Persist the fingerprint observed for the release we just loaded.

    Call this only after a *successful* load — the watermark is the
    promise "we have ingested the release identified by this
    fingerprint." A ``None`` fingerprint is stored as NULL so the next
    run re-checks rather than trusting an unknown.
    """
    _ensure_table(store)
    with store.connect() as con:
        con.execute(
            """INSERT INTO release_watermark
               (source_name, fingerprint, fingerprint_kind, source_ref, checked_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(source_name) DO UPDATE SET
                 fingerprint = excluded.fingerprint,
                 fingerprint_kind = excluded.fingerprint_kind,
                 source_ref = excluded.source_ref,
                 checked_at = excluded.checked_at""",
            (str(source_name), fingerprint, str(kind), source_ref, _utcnow_iso()),
        )
        con.commit()


def is_release_changed(
    store: Any, source_name: str, fingerprint: Optional[str]
) -> bool:
    """True when ``fingerprint`` differs from the stored watermark.

    Returns True (refresh needed) when either side is unknown: no stored
    watermark yet, or a ``None`` probe. The only case that returns False
    — safe to skip — is a known stored fingerprint equal to a known
    current one.
    """
    if fingerprint is None:
        return True
    current = get_watermark(store, source_name)
    if current is None:
        return True
    return current.get("fingerprint") != fingerprint


def select_changed_sources(
    store: Any,
    candidates: Iterable[str],
    fingerprints: Dict[str, Optional[str]],
) -> List[str]:
    """Subset of ``candidates`` whose release looks changed.

    Sources absent from ``fingerprints`` are always included (we have no
    probe → can't prove unchanged). This is the function a cron entry
    point calls to decide what to actually refresh.
    """
    out: List[str] = []
    for name in candidates:
        fp = fingerprints.get(name) if name in fingerprints else None
        if name not in fingerprints:
            out.append(name)
        elif is_release_changed(store, name, fp):
            out.append(name)
    return out
