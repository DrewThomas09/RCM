"""HTTP page stubs for the four RCM Diligence tabs.

Phase 1's ingest tab is the only one that has real work behind it in
this session; the others are intentional placeholders so partners can
see the workspace shape. Each page renders under the shared chartis
shell so the nav + theme are coherent with the rest of the app.
"""
from __future__ import annotations

import html
from typing import Iterable, Tuple

from ..ui._chartis_kit import P, chartis_shell


def render_ingest_page() -> str:
    body = (
        _hero(
            "Phase 1 — Ingestion & Normalization",
            "Raw 837 / 835 EDI, Epic / Cerner / Athena exports, and messy Excel "
            "funnelled into a single versioned Canonical Claims Dataset (CCD). "
            "Every transformation is row-logged.",
        )
        + _capability_grid([
            ("Source formats", "CSV · TSV · Parquet · Excel · EDI 837 · EDI 835"),
            ("Canonical grain", "claim_id × line_number × source_system"),
            ("Transformation log", "Every coerced value → source file + row + rule"),
            ("Idempotency", "Same inputs produce the same content hash"),
        ])
        + _link_line(
            "Ingester API",
            "from rcm_mc.diligence import ingest_dataset",
        )
    )
    return chartis_shell(body, "RCM Diligence — Ingestion",
                        subtitle="Phase 1 of 4 · Canonical Claims Dataset")


def render_benchmarks_page(bundle=None, cohort_report=None) -> str:
    """Delegates to the real renderer in ``rcm_mc.ui.diligence_benchmarks``.

    When ``bundle`` is None (no CCD attached yet), the real renderer
    returns the placeholder variant, so callers don't need to branch.
    The legacy stub that lived here in session 1 is replaced — the
    full implementation now lives in the ui module so KPI data can
    drive the page.
    """
    from ..ui.diligence_benchmarks import render_benchmarks_page as _render
    return _render(bundle=bundle, cohort_report=cohort_report)


def render_root_cause_page() -> str:
    body = _hero(
        "Phase 3 — Root Cause Analysis",
        "Pareto drivers for every off-benchmark KPI. ZBA autopsy surfaces "
        "recoverable write-offs. Every finding is one click from the "
        "underlying rows in the CCD.",
    ) + _phase_placeholder("Phase 3 implementation ships in a follow-up session.")
    return chartis_shell(body, "RCM Diligence — Root Cause",
                        subtitle="Phase 3 of 4")


def render_value_page() -> str:
    body = _hero(
        "Phase 4 — Value Creation Model",
        "Per-root-cause recoverable EBITDA feeds the v2 value bridge. "
        "Monte Carlo on payer behavior reuses the existing two-source "
        "simulator. QoE-ready output reuses the packet renderer. Phase 4 "
        "is wiring the UI — not new math.",
    ) + _phase_placeholder("Phase 4 wiring ships in a follow-up session.")
    return chartis_shell(body, "RCM Diligence — Value Creation",
                        subtitle="Phase 4 of 4")


# ── Building blocks ─────────────────────────────────────────────────

def _hero(title: str, sub: str) -> str:
    return (
        f'<div style="padding:24px 0 12px 0;">'
        f'  <div style="font-size:11px;color:{P["text_faint"]};letter-spacing:.75px;'
        f'text-transform:uppercase;margin-bottom:6px;">RCM Diligence Workspace</div>'
        f'  <div style="font-size:20px;color:{P["text"]};font-weight:600;'
        f'margin-bottom:8px;">{html.escape(title)}</div>'
        f'  <div style="font-size:13px;color:{P["text_dim"]};max-width:720px;'
        f'line-height:1.55;">{html.escape(sub)}</div>'
        f'</div>'
    )


def _capability_grid(rows: Iterable[Tuple[str, str]]) -> str:
    items = []
    for label, value in rows:
        items.append(
            f'<div style="background:{P["panel"]};border:1px solid {P["border"]};'
            f'border-radius:4px;padding:14px 16px;">'
            f'  <div style="font-size:10px;color:{P["text_faint"]};letter-spacing:.5px;'
            f'text-transform:uppercase;margin-bottom:6px;">{html.escape(label)}</div>'
            f'  <div style="font-size:13px;color:{P["text"]};">{html.escape(value)}</div>'
            f'</div>'
        )
    return (
        '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));'
        'gap:12px;margin:16px 0 12px 0;">' + "".join(items) + '</div>'
    )


def _link_line(label: str, code: str) -> str:
    return (
        f'<div style="margin-top:14px;font-size:12px;color:{P["text_dim"]};">'
        f'  {html.escape(label)}: '
        f'<code style="background:{P["panel_alt"]};padding:2px 6px;'
        f'border-radius:3px;color:{P["accent"]};font-family:'
        '\'JetBrains Mono\',monospace;">' + html.escape(code) + '</code>'
        '</div>'
    )


def _phase_placeholder(note: str) -> str:
    return (
        f'<div style="margin-top:20px;padding:14px 16px;background:{P["panel"]};'
        f'border:1px solid {P["border"]};border-radius:4px;'
        f'color:{P["text_dim"]};font-size:12px;">'
        f'{html.escape(note)} The Canonical Claims Dataset produced by Phase 1 '
        f'is the load-bearing input; when it lands, this tab becomes active '
        f'without migration.'
        f'</div>'
    )
