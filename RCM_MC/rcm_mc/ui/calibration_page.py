"""Per-payer prior-calibration page — `/calibration`.

Aggregates IDR / FWR / DAR clean-days primitives from the
PortfolioStore.list_runs analysis-runs cache, groups them by
payer, and renders a slider-per-payer panel so partners can
intuit calibration priors.

History:
    Lifted out of server.py (was 70 LOC inlined inside the
    dispatcher block at lines 4759-4827) so the page can be tested
    end-to-end and adopt v3 utility classes uniformly. Behaviour
    is preserved bit-for-bit; only the chrome and class names
    moved to v3.

Why this page is exempt from the per-deal DealAnalysisPacket
invariant:
    Calibration is a portfolio-wide aggregation across many runs;
    there is no single deal_id. The page reads
    PortfolioStore.list_runs() (via the existing helper) and
    parses primitives_json — same as the previous inline
    implementation.

Public API::

    render_calibration_page(store) -> str
"""
from __future__ import annotations

import html as _html
import json
from typing import Any, Dict, List, Optional

import pandas as pd

from ._chartis_kit import chartis_shell


def _aggregate_payers(runs_df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    """Group primitives by payer and average IDR/FWR/DAR.

    Returns ``{payer: {"idr_m": .., "fwr_m": .., "dar_m": ..,
    "n_entries": ..}}``. Empty inputs return ``{}``.
    """
    payer_data: Dict[str, List[Dict[str, Any]]] = {}
    for _, r in runs_df.iterrows():
        try:
            prim = json.loads(r.get("primitives_json") or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        for payer, vals in prim.get("payers", {}).items():
            payer_data.setdefault(payer, []).append(vals)

    out: Dict[str, Dict[str, float]] = {}
    for payer, entries in payer_data.items():
        idrs = [e.get("idr_mean") for e in entries if e.get("idr_mean") is not None]
        fwrs = [e.get("fwr_mean") for e in entries if e.get("fwr_mean") is not None]
        dars = [e.get("dar_clean_days_mean") for e in entries if e.get("dar_clean_days_mean") is not None]
        out[payer] = {
            "idr_m": (sum(idrs) / len(idrs)) if idrs else 0.0,
            "fwr_m": (sum(fwrs) / len(fwrs)) if fwrs else 0.0,
            "dar_m": (sum(dars) / len(dars)) if dars else 0.0,
            "n_entries": float(len(entries)),
        }
    return out


def _slider_card(payer: str, agg: Dict[str, float]) -> str:
    """One payer's IDR/FWR/DAR sliders + live readouts.

    The oninput handler updates a sibling <span class="num mono">
    with the current slider value so partners get immediate
    feedback. Pure CSS-variable styling; no JS imports.
    """
    ep = _html.escape(payer)
    n_entries = int(agg["n_entries"])
    idr_m = agg["idr_m"]
    fwr_m = agg["fwr_m"]
    dar_m = agg["dar_m"]
    return (
        '<section style="border:1px solid var(--border,#374151);'
        'background:var(--paper,#1f2937);border-radius:8px;'
        'padding:1rem 1.25rem;margin-bottom:.75rem;">'
        f'<h3 style="margin:0 0 .5rem 0;font-size:1rem;">{ep}</h3>'
        '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;'
        'gap:1rem;">'
        # IDR
        '<div>'
        '<label class="micro" style="font-weight:400;letter-spacing:.04em;'
        'text-transform:none;display:block;margin-bottom:.25rem;">'
        f'IDR mean: <span id="idr-{ep}" class="num mono">{idr_m:.3f}</span></label>'
        f'<input type="range" min="0" max="0.5" step="0.005" value="{idr_m:.3f}" '
        'style="width:100%;accent-color:var(--sc-navy);" '
        f'oninput="document.getElementById(\'idr-{ep}\').textContent=this.value">'
        '</div>'
        # FWR
        '<div>'
        '<label class="micro" style="font-weight:400;letter-spacing:.04em;'
        'text-transform:none;display:block;margin-bottom:.25rem;">'
        f'FWR mean: <span id="fwr-{ep}" class="num mono">{fwr_m:.3f}</span></label>'
        f'<input type="range" min="0" max="0.8" step="0.005" value="{fwr_m:.3f}" '
        'style="width:100%;accent-color:var(--sc-navy);" '
        f'oninput="document.getElementById(\'fwr-{ep}\').textContent=this.value">'
        '</div>'
        # DAR
        '<div>'
        '<label class="micro" style="font-weight:400;letter-spacing:.04em;'
        'text-transform:none;display:block;margin-bottom:.25rem;">'
        f'DAR days: <span id="dar-{ep}" class="num mono">{dar_m:.0f}</span></label>'
        f'<input type="range" min="0" max="120" step="1" value="{dar_m:.0f}" '
        'style="width:100%;accent-color:var(--sc-navy);" '
        f'oninput="document.getElementById(\'dar-{ep}\').textContent=this.value">'
        '</div>'
        '</div>'
        '<p class="micro" style="margin-top:.5rem;font-weight:400;'
        'letter-spacing:.04em;text-transform:none;'
        f'color:var(--muted,#9ca3af);">{n_entries} run(s)</p>'
        '</section>'
    )


def render_calibration_page(store: Any) -> str:
    """Render the calibration UI for the supplied PortfolioStore.

    On an empty cache, surfaces a partner-friendly empty state
    pointing at /analysis. Otherwise, aggregates priors per payer
    and emits one slider card per payer plus a footer link to the
    JSON API.
    """
    try:
        runs_df = store.list_runs()
    except Exception:  # noqa: BLE001 — empty/unbuilt DB falls through
        runs_df = pd.DataFrame()

    if runs_df.empty:
        body = (
            '<section style="max-width:62rem;">'
            '<h1 style="margin:0 0 .5rem 0;">Calibration</h1>'
            '<p style="max-width:48rem;color:var(--muted,#9ca3af);'
            'margin:0 0 1rem 0;">'
            'Per-payer prior calibration. Aggregates IDR / FWR / DAR '
            'primitives across every run in the analysis cache so you '
            'can intuit priors before configuring a new deal.</p>'
            '<div style="background:var(--paper,#111827);'
            'border:1px solid var(--border,#374151);border-radius:8px;'
            'padding:2.5rem;text-align:center;color:var(--muted,#9ca3af);">'
            'No simulation runs yet. Run an analysis first to populate '
            'calibration priors.<br><br>'
            '<a href="/analysis" class="micro" style="font-weight:400;'
            'letter-spacing:.04em;text-transform:none;">'
            'Go to Analysis →</a></div></section>'
        )
        return chartis_shell(
            body,
            "Calibration",
            subtitle="per-payer prior calibration",
        )

    payers = _aggregate_payers(runs_df)
    n_runs = len(runs_df)

    sliders = "".join(_slider_card(p, agg) for p, agg in sorted(payers.items()))

    body = (
        '<section style="max-width:80rem;">'
        '<div style="display:flex;justify-content:space-between;'
        'align-items:baseline;margin-bottom:.75rem;">'
        '<h1 style="margin:0;">Calibration</h1>'
        '<a href="/api/calibration/priors" class="micro" '
        'style="font-weight:400;letter-spacing:.04em;'
        'text-transform:none;">JSON API →</a>'
        '</div>'
        '<p style="max-width:48rem;color:var(--muted,#9ca3af);'
        'margin:0 0 1rem 0;">'
        f'Per-payer prior calibration. Aggregates IDR / FWR / DAR '
        f'primitives across <span class="num">{n_runs}</span> run(s) '
        f'spanning <span class="num">{len(payers)}</span> payer(s). '
        f'Drag a slider to explore priors; values are read-only — the '
        f'underlying analysis cache is the source of truth.</p>'
        + sliders
        + '</section>'
    )

    return chartis_shell(
        body,
        "Calibration",
        subtitle="per-payer prior calibration",
    )
