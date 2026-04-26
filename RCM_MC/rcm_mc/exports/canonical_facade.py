"""Canonical-path facades over existing report writers.

Phase 3 commit 2 migrates 5 report writers to the canonical export
path layout (``/data/exports/<deal_id>/<timestamp>_<filename>``)
WITHOUT touching the writers themselves.

The pattern: each facade function below

  1. Computes the canonical path via ``canonical_deal_export_path``
  2. Calls the existing writer with a ``tempfile.TemporaryDirectory()``
     so the writer's output lands in a known scratch location
  3. Moves the writer's output to the canonical location (atomic
     rename within /data/exports)
  4. Records the export in ``generated_exports`` for the deliverables
     manifest
  5. Returns the canonical Path

Why facades instead of changing the writers' signatures:

  Existing writers take ``outdir`` / ``out_path`` args used by ~6
  call sites across server.py + the CLI. Changing each signature
  would touch every call site at once — a big-bang refactor with
  rollback risk. Facades layer on top: existing call sites keep
  using the writers directly with their existing args (no behavior
  change); new call sites use the facade and get canonical paths
  for free.

  Phase 4 (or later) can replace direct writer calls with facade
  calls one-by-one as appetite allows. Facades make canonical paths
  available NOW without forcing the migration timeline.

Per Phase 3 conventions:
  - Pre-computed inputs (store + deal_id are passed; facade doesn't
    re-derive them)
  - One file per migration batch (this file = commit 2's 5 reports;
    commits 3 and 4 will add their own facade modules)
  - All facade functions follow the same shape so future readers
    can see the pattern after reading any one of them
"""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Any, Optional

from rcm_mc.exports.export_store import record_export
from rcm_mc.infra.exports import canonical_deal_export_path


def _move_to_canonical(
    produced: Path,
    canonical: Path,
) -> Path:
    """Move a freshly-written file from a tmp dir to the canonical path.

    Uses ``shutil.move`` rather than ``Path.rename`` because the tmp
    dir lives on a different mountpoint than ``/data/exports/`` in
    most production setups (tmpfs vs. persistent volume), and
    ``rename()`` fails across filesystem boundaries.
    """
    canonical.parent.mkdir(parents=True, exist_ok=True)
    if canonical.exists():
        canonical.unlink()  # idempotent overwrite — same canonical path = same artifact
    shutil.move(str(produced), str(canonical))
    return canonical


def _record(
    store: Any,
    *,
    deal_id: str,
    canonical: Path,
    fmt: str,
    analysis_run_id: Optional[str] = None,
    generated_by: Optional[str] = None,
) -> None:
    """Wrap record_export with the file-size lookup baked in.

    ``record_export`` requires ``file_size_bytes`` as an Optional
    int. Doing the stat() once per facade keeps every call site
    consistent rather than relying on each writer to remember.
    Failures here are absorbed: the artifact is on disk and that's
    the load-bearing thing; the audit row is best-effort.
    """
    try:
        size = canonical.stat().st_size if canonical.exists() else None
    except OSError:
        size = None
    try:
        record_export(
            store,
            deal_id=deal_id,
            analysis_run_id=analysis_run_id,
            format=fmt,
            filepath=str(canonical),
            file_size_bytes=size,
            generated_by=generated_by,
        )
    except Exception:  # noqa: BLE001 — manifest failure must not break the export
        pass


# ── Facade functions (5 reports) ──────────────────────────────────


def export_full_html_report(
    store: Any,
    *,
    deal_id: str,
    actual_path: str,
    benchmark_path: str,
    analysis_run_id: Optional[str] = None,
    generated_by: Optional[str] = None,
    **writer_kwargs: Any,
) -> Path:
    """Canonical-path facade for generate_full_html_report.

    Produces ``/data/exports/<deal_id>/<ts>_full_report.html``.
    Records to generated_exports.
    """
    from rcm_mc.reports.full_report import generate_full_html_report

    canonical = canonical_deal_export_path(deal_id, "full_report.html")
    with tempfile.TemporaryDirectory(prefix="rcm_full_report_") as tmp:
        produced = generate_full_html_report(
            tmp, actual_path, benchmark_path, **writer_kwargs,
        )
        _move_to_canonical(Path(produced), canonical)
    _record(store, deal_id=deal_id, canonical=canonical, fmt="html",
            analysis_run_id=analysis_run_id, generated_by=generated_by)
    return canonical


def export_html_report(
    store: Any,
    *,
    deal_id: str,
    analysis_run_id: Optional[str] = None,
    generated_by: Optional[str] = None,
    **writer_kwargs: Any,
) -> Path:
    """Canonical-path facade for generate_html_report (the standard
    diligence-run HTML report)."""
    from rcm_mc.reports.html_report import generate_html_report

    canonical = canonical_deal_export_path(deal_id, "report.html")
    with tempfile.TemporaryDirectory(prefix="rcm_html_report_") as tmp:
        produced = generate_html_report(tmp, **writer_kwargs)
        _move_to_canonical(Path(produced), canonical)
    _record(store, deal_id=deal_id, canonical=canonical, fmt="html",
            analysis_run_id=analysis_run_id, generated_by=generated_by)
    return canonical


def export_markdown_report(
    store: Any,
    *,
    deal_id: str,
    analysis_run_id: Optional[str] = None,
    generated_by: Optional[str] = None,
    **writer_kwargs: Any,
) -> Path:
    """Canonical-path facade for generate_markdown_report."""
    from rcm_mc.reports.markdown_report import generate_markdown_report

    canonical = canonical_deal_export_path(deal_id, "report.md")
    with tempfile.TemporaryDirectory(prefix="rcm_md_report_") as tmp:
        produced = generate_markdown_report(tmp, **writer_kwargs)
        _move_to_canonical(Path(produced), canonical)
    _record(store, deal_id=deal_id, canonical=canonical, fmt="markdown",
            analysis_run_id=analysis_run_id, generated_by=generated_by)
    return canonical


def export_exit_memo(
    store: Any,
    *,
    deal_id: str,
    snapshot: Any,
    analysis_run_id: Optional[str] = None,
    generated_by: Optional[str] = None,
    **writer_kwargs: Any,
) -> Path:
    """Canonical-path facade for build_exit_memo.

    Note: ``build_exit_memo`` takes ``out_path`` directly (not
    ``outdir``), so this facade computes the canonical path and
    passes it through as ``out_path`` rather than using a tmp dir.
    """
    from rcm_mc.reports.exit_memo import build_exit_memo

    canonical = canonical_deal_export_path(deal_id, "exit_memo.html")
    build_exit_memo(snapshot, out_path=str(canonical), **writer_kwargs)
    _record(store, deal_id=deal_id, canonical=canonical, fmt="html",
            analysis_run_id=analysis_run_id, generated_by=generated_by)
    return canonical


def export_partner_brief(
    store: Any,
    *,
    deal_id: str,
    outdir: str,
    analysis_run_id: Optional[str] = None,
    generated_by: Optional[str] = None,
    **writer_kwargs: Any,
) -> Path:
    """Canonical-path facade for build_partner_brief.

    Note: build_partner_brief is unusual — it takes a required
    ``outdir`` (where its CSV inputs are read from: summary.csv,
    sensitivity.csv, etc.) AND an optional ``out_path``. The facade
    threads the canonical path as out_path; ``outdir`` stays as
    the input-read directory (caller's responsibility).
    """
    from rcm_mc.reports._partner_brief import build_partner_brief

    canonical = canonical_deal_export_path(deal_id, "partner_brief.html")
    build_partner_brief(
        outdir, out_path=str(canonical), **writer_kwargs,
    )
    _record(store, deal_id=deal_id, canonical=canonical, fmt="html",
            analysis_run_id=analysis_run_id, generated_by=generated_by)
    return canonical


__all__ = [
    "export_full_html_report",
    "export_html_report",
    "export_markdown_report",
    "export_exit_memo",
    "export_partner_brief",
]
