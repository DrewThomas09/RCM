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


# ── Facade functions (3 packet/zip exporters — Phase 3 commit 3) ──


def export_diligence_memo(
    store: Any,
    *,
    deal_id: str,
    packet: Any,
    fmt: str = "html",                # "html" | "pptx"
    analysis_run_id: Optional[str] = None,
    generated_by: Optional[str] = None,
) -> Path:
    """Canonical-path facade for PacketRenderer.render_diligence_memo_*.

    Renders the packet's diligence memo in the requested format.
    fmt=='html' calls render_diligence_memo_html; fmt=='pptx' calls
    render_diligence_memo_pptx.
    """
    from rcm_mc.exports.packet_renderer import PacketRenderer

    if fmt not in ("html", "pptx"):
        raise ValueError(f"fmt must be 'html' or 'pptx', got {fmt!r}")
    filename = f"diligence_memo.{fmt}"
    canonical = canonical_deal_export_path(deal_id, filename)
    with tempfile.TemporaryDirectory(prefix="rcm_diligence_memo_") as tmp:
        renderer = PacketRenderer(out_dir=Path(tmp))
        if fmt == "html":
            produced = renderer.render_diligence_memo_html(packet)
        else:
            produced = renderer.render_diligence_memo_pptx(packet)
        _move_to_canonical(Path(produced), canonical)
    _record(store, deal_id=deal_id, canonical=canonical, fmt=fmt,
            analysis_run_id=analysis_run_id, generated_by=generated_by)
    return canonical


def export_diligence_package_zip(
    store: Any,
    *,
    deal_id: str,
    packet: Any,
    inputs_hash: str = "",
    analysis_run_id: Optional[str] = None,
    generated_by: Optional[str] = None,
) -> Path:
    """Canonical-path facade for diligence_package.generate_package.

    Wraps the 9+ documents into a zip and writes to the canonical
    location. The package's INNER manifest path naming (the names of
    files inside the zip) is unchanged — only the zip's location on
    disk is canonicalized.
    """
    from rcm_mc.exports.diligence_package import generate_package

    canonical = canonical_deal_export_path(deal_id, "diligence_package.zip")
    with tempfile.TemporaryDirectory(prefix="rcm_diligence_package_") as tmp:
        produced = generate_package(packet, Path(tmp), inputs_hash=inputs_hash)
        _move_to_canonical(Path(produced), canonical)
    _record(store, deal_id=deal_id, canonical=canonical, fmt="zip",
            analysis_run_id=analysis_run_id, generated_by=generated_by)
    return canonical


def export_exit_package_zip(
    store: Any,
    *,
    deal_id: str,
    analysis_run_id: Optional[str] = None,
    generated_by: Optional[str] = None,
) -> Path:
    """Canonical-path facade for exit_package.generate_exit_package.

    The underlying writer takes ``store`` + ``deal_id`` + optional
    ``out_dir``; the facade threads its tmp dir as out_dir, then
    moves the produced zip to canonical.
    """
    from rcm_mc.exports.exit_package import generate_exit_package

    canonical = canonical_deal_export_path(deal_id, "exit_package.zip")
    with tempfile.TemporaryDirectory(prefix="rcm_exit_package_") as tmp:
        produced = generate_exit_package(store, deal_id, out_dir=Path(tmp))
        _move_to_canonical(Path(produced), canonical)
    _record(store, deal_id=deal_id, canonical=canonical, fmt="zip",
            analysis_run_id=analysis_run_id, generated_by=generated_by)
    return canonical


# ── Facade functions (3 misc writers — Phase 3 commit 4) ──────────


def export_deal_xlsx(
    store: Any,
    *,
    deal_id: str,
    packet: Any,
    inputs_hash: str = "",
    analysis_run_id: Optional[str] = None,
    generated_by: Optional[str] = None,
) -> Path:
    """Canonical-path facade for xlsx_renderer.render_deal_xlsx.

    The 6-sheet workbook (RCM Profile / Bridge / Monte Carlo /
    Risk Flags / Raw Data / Audit). Underlying writer takes
    ``out_dir`` and writes ``<stem>.xlsx`` inside it; the facade
    wraps with a tmp dir + moves to canonical.

    Raises ImportError when openpyxl isn't installed (matches the
    underlying writer's contract — callers should catch + fall back).
    """
    from rcm_mc.exports.xlsx_renderer import render_deal_xlsx

    canonical = canonical_deal_export_path(deal_id, "deal.xlsx")
    with tempfile.TemporaryDirectory(prefix="rcm_deal_xlsx_") as tmp:
        produced = render_deal_xlsx(packet, Path(tmp), inputs_hash=inputs_hash)
        _move_to_canonical(Path(produced), canonical)
    _record(store, deal_id=deal_id, canonical=canonical, fmt="xlsx",
            analysis_run_id=analysis_run_id, generated_by=generated_by)
    return canonical


def export_bridge_xlsx(
    store: Any,
    *,
    deal_id: str,
    bridge: Any,
    hospital_name: str = "",
    ccn: str = "",
    returns_grid: Optional[Any] = None,
    peer_context: Optional[Any] = None,
    analysis_run_id: Optional[str] = None,
    generated_by: Optional[str] = None,
) -> Path:
    """Canonical-path facade for bridge_export.export_bridge_xlsx.

    Underlying writer returns BYTES (no path), so the facade writes
    the bytes to canonical directly — no tmp dir needed.
    """
    from rcm_mc.exports.bridge_export import export_bridge_xlsx as _bridge_xlsx_bytes

    canonical = canonical_deal_export_path(deal_id, "bridge.xlsx")
    payload = _bridge_xlsx_bytes(
        bridge,
        hospital_name=hospital_name,
        ccn=ccn,
        returns_grid=returns_grid,
        peer_context=peer_context,
    )
    canonical.parent.mkdir(parents=True, exist_ok=True)
    canonical.write_bytes(payload)
    _record(store, deal_id=deal_id, canonical=canonical, fmt="xlsx",
            analysis_run_id=analysis_run_id, generated_by=generated_by)
    return canonical


def export_ic_packet_html(
    store: Any,
    *,
    deal_id: str,
    metadata: Any,
    analysis_run_id: Optional[str] = None,
    generated_by: Optional[str] = None,
    **render_kwargs: Any,
) -> Path:
    """Canonical-path facade for ic_packet.render_ic_packet_html.

    Underlying writer returns an HTML string (no path), so the
    facade writes the string to canonical directly. ``metadata`` is
    the only required positional arg of the underlying renderer; all
    other inputs flow through ``**render_kwargs``.
    """
    from rcm_mc.exports.ic_packet import render_ic_packet_html

    canonical = canonical_deal_export_path(deal_id, "ic_packet.html")
    html = render_ic_packet_html(metadata=metadata, **render_kwargs)
    canonical.parent.mkdir(parents=True, exist_ok=True)
    canonical.write_text(html, encoding="utf-8")
    _record(store, deal_id=deal_id, canonical=canonical, fmt="html",
            analysis_run_id=analysis_run_id, generated_by=generated_by)
    return canonical


__all__ = [
    # Reports (commit 2)
    "export_full_html_report",
    "export_html_report",
    "export_markdown_report",
    "export_exit_memo",
    "export_partner_brief",
    # Packet/zip (commit 3)
    "export_diligence_memo",
    "export_diligence_package_zip",
    "export_exit_package_zip",
    # Misc (commit 4)
    "export_deal_xlsx",
    "export_bridge_xlsx",
    "export_ic_packet_html",
]
