"""Canonical export path policy.

Two named functions — ``canonical_deal_export_path`` and
``canonical_portfolio_export_path`` — that every export writer in
the codebase routes through. Centralizes the filesystem layout
decision so future changes (cleanup policy, retention TTL, sharding)
happen in one place instead of 12.

Why two functions, not one with ``Optional[str] deal_id``:

  The single-function pattern with ``deal_id=None`` for cross-portfolio
  is the most common source of silent bugs in any codebase that grows
  past a year. The function gets called correctly 99% of the time, then
  someone copy-pastes a call site, modifies one parameter, forgets
  another, and ships. Type checkers don't catch it because ``None`` is
  a valid value. Tests don't catch it because the function still
  returns a path. The artifact lands in ``_portfolio/`` instead of the
  intended ``<deal_id>/``, and the deliverables block silently fails
  to surface it.

  Two named functions sharing one private implementation eliminate
  this entire class of bug. The compiler (and humans) make the right
  choice obvious at the call site:

      from rcm_mc.infra.exports import (
          canonical_deal_export_path,
          canonical_portfolio_export_path,
      )

      # deal-scoped — won't compile without deal_id:
      out = canonical_deal_export_path("ccf_2026", "packet.html")

      # cross-portfolio — explicit at the call site:
      out = canonical_portfolio_export_path("corpus_summary.xlsx")

Layout:

  /data/exports/<deal_id>/<timestamp>_<filename>     (deal-scoped)
  /data/exports/_portfolio/<timestamp>_<filename>    (cross-portfolio)

The leading-underscore on ``_portfolio`` is intentional — it sorts above
any real ``deal_id`` in directory listings, so a partner browsing
``/data/exports/`` always sees portfolio-level exports first.

Why this lives in ``infra/`` (not ``exports/``):

  These functions are policy that every renderer depends on. Putting
  them under ``exports/`` would couple them to the modules they serve;
  ``infra/`` is the right home for cross-cutting concerns, matching
  the established pattern of ``infra/migrations.py``,
  ``infra/cache.py``, ``infra/logger.py``.

Migration policy (per Phase 3 proposal):

  Existing writers keep their current ``out_path`` / ``out_dir`` kwargs
  for back-compat. New callers route through whichever of the two
  canonical_*_export_path functions matches their scope. Phase 3
  commits 2-4 add this code path to each writer family without
  changing the existing path.

Test isolation:

  ``EXPORTS_BASE`` env override redirects the root from
  ``/data/exports`` to a test-friendly tmpdir. Production callers pass
  nothing; tests set the env to a pytest tmpdir. Pattern matches the
  ``RCM_MC_DB`` env override used elsewhere.

  Precedence (documented per review): explicit ``base=`` arg >
  ``EXPORTS_BASE`` env var > ``/data/exports`` default.

Cross-platform safety:

  ISO-8601 timestamps would use ``:`` in the time portion, which fails
  on case-insensitive filesystems and the occasional mounted SMB share.
  We substitute ``:`` with ``-`` throughout. The ``T`` between date
  and time stays — output is still ISO-8601-recognizable, just with
  the time-portion separator swapped.

# TODO(phase 4): cleanup policy. Per Q3.5 product decision (Option 1
# committed during Phase 3 prep), no auto-cleanup is wired in Phase 3.
# Phase 4 adds retention (90-day TTL or LRU eviction or per-deal size
# cap) once we know what real export volume looks like.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


_DEFAULT_BASE = "/data/exports"

# Filename character that's legal everywhere (Linux + macOS + Windows).
# ISO 8601 uses ``:`` in the time portion; substitute with ``-``.
_TIMESTAMP_FMT = "%Y-%m-%dT%H-%M-%S"


def _now_utc_iso() -> str:
    """Filesystem-safe UTC timestamp (no colons, no microseconds)."""
    return datetime.now(timezone.utc).strftime(_TIMESTAMP_FMT)


def _resolve_export_path(
    deal_id: Optional[str],
    filename: str,
    *,
    timestamp: Optional[str],
    base: Optional[Path],
) -> Path:
    """Private implementation shared by the two public functions.

    Performs the filesystem-layout work + filename validation. Callers
    above route through the public ``canonical_*_export_path``
    functions which carry the scope choice in their names.
    """
    if "/" in filename or "\\" in filename:
        raise ValueError(
            f"filename must be a bare name, not a path: {filename!r}"
        )

    if base is None:
        base = Path(os.environ.get("EXPORTS_BASE") or _DEFAULT_BASE)
    else:
        base = Path(base)

    ts = timestamp or _now_utc_iso()

    # Cross-portfolio routing — None or empty deal_id → _portfolio/.
    # The empty-string fallback is defensive: a DB row with a blank
    # deal_id would otherwise write to /data/exports/ root, which is
    # the wrong place. Underscore prefix sorts above any real deal_id.
    scope = (deal_id or "").strip() or "_portfolio"

    parent = base / scope
    parent.mkdir(parents=True, exist_ok=True)

    return (parent / f"{ts}_{filename}").resolve()


def canonical_deal_export_path(
    deal_id: str,
    filename: str,
    *,
    timestamp: Optional[str] = None,
    base: Optional[Path] = None,
) -> Path:
    """Resolve the canonical path for a deal-scoped export artifact.

    Args:
        deal_id: Deal identifier — required, non-empty. Forces the
            artifact under ``/data/exports/<deal_id>/``. Empty / None
            raises ``ValueError`` rather than silently routing to the
            cross-portfolio bucket.
        filename: Bare filename (e.g. ``"diligence_packet.html"``).
            Must not contain path separators. Encode hierarchy in the
            filename itself (``"lp_q1.html"``), not via subdirectories.
        timestamp: Filesystem-safe UTC timestamp string (default: now).
            Format ``YYYY-MM-DDTHH-MM-SS``.
        base: Override the ``/data/exports/`` root. Precedence:
            explicit ``base=`` arg > ``EXPORTS_BASE`` env var >
            ``/data/exports`` default.

    Returns:
        Absolute :class:`pathlib.Path` with parent directories created.

    Raises:
        ValueError: ``deal_id`` is empty / None / not a string, OR
            ``filename`` contains a path separator.
    """
    # Defense-in-depth on the deal_id check — rejecting None/empty isn't
    # enough; a whitespace-only string would pass the truthy check above
    # but ``.strip()`` in _resolve_export_path would fall back to
    # _portfolio, which is exactly the silent-mis-routing failure mode
    # this two-function split exists to prevent.
    if not isinstance(deal_id, str) or not deal_id.strip():
        raise ValueError(
            "deal_id required and must be a non-empty, non-whitespace "
            "string. For cross-portfolio exports, call "
            "canonical_portfolio_export_path() instead."
        )
    return _resolve_export_path(
        deal_id, filename, timestamp=timestamp, base=base,
    )


def canonical_portfolio_export_path(
    filename: str,
    *,
    timestamp: Optional[str] = None,
    base: Optional[Path] = None,
) -> Path:
    """Resolve the canonical path for a cross-portfolio export artifact.

    Routes the file under ``/data/exports/_portfolio/`` for artifacts
    that aren't scoped to a single deal — e.g., corpus summaries,
    fund-level reports, multi-deal comparisons. The underscore prefix
    on ``_portfolio`` sorts above any real ``deal_id`` in directory
    listings, so portfolio-level exports always appear first when a
    partner browses ``/data/exports/``.

    Args:
        filename: Bare filename (e.g. ``"corpus_summary.xlsx"``).
            Must not contain path separators.
        timestamp: Filesystem-safe UTC timestamp string (default: now).
            Format ``YYYY-MM-DDTHH-MM-SS``.
        base: Override the ``/data/exports/`` root. Precedence:
            explicit ``base=`` arg > ``EXPORTS_BASE`` env var >
            ``/data/exports`` default.

    Returns:
        Absolute :class:`pathlib.Path` with parent directories created.

    Raises:
        ValueError: ``filename`` contains a path separator.
    """
    return _resolve_export_path(
        None, filename, timestamp=timestamp, base=base,
    )


__all__ = [
    "canonical_deal_export_path",
    "canonical_portfolio_export_path",
]
