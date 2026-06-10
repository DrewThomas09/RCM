"""Data Quality dashboard — /data-quality (P11, internal certification view).

One screen to certify the data layer before a client demo: every WIRED
source with live-computed row counts, key-field null rates, vintage and an
honest staleness read against the source's OWN publication cadence (HCRIS
cost reports run ~18 months behind fiscal-year end — that lag is the
source's normal, not a defect); the live gap census (reusing
data/gap_fill_registry); a consumer map (which pages read each source); and
the registered-but-not-yet-wired sources from the vendored source registry.

Every number on this page is computed at render time from the SAME loaders
the product uses, so the dashboard cannot drift from what pages display.
"""
from __future__ import annotations

import html as _html
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from ._chartis_kit import (
    chartis_shell, ck_kpi_block, ck_page_title, ck_panel, ck_source_link,
)


@dataclass
class WiredSource:
    name: str
    loader: Callable[[], dict]          # → {"rows": int, "nulls": {field: rate}, "vintage": str}
    cadence_note: str                   # the source's own publication rhythm
    consumers: List[str]                # pages reading it
    source_label: str = "CMS HCRIS"     # ck_source_link key when known
    # Structured staleness inputs (the cadence_note is free text for display;
    # these drive the deterministic green/amber/red chip).
    cadence_days: Optional[int] = None  # nominal refresh interval (31/92/365)
    snapshot_date: Optional[str] = None  # ISO date of the vendored snapshot
    lag_tolerant: bool = False          # True for HCRIS: an ~18mo publication
    #                                     lag is the current normal, not staleness


# Staleness tiers: a source is fresh within ~one publication cycle, aging by
# two-to-three, stale beyond. HCRIS is lag-tolerant (the lag is expected), and
# a source with no stated snapshot date reports "date unstated" rather than a
# fabricated freshness.
_STALE_GREEN = ("var(--sc-positive,#0a8a5f)", "CURRENT")
_STALE_AMBER = ("var(--sc-warning,#b8732a)", "AGING")
_STALE_RED = ("var(--sc-negative,#b5321e)", "STALE")
_STALE_GRAY = ("var(--sc-text-dim,#6a7480)", "DATE UNSTATED")
_STALE_NORMAL = ("var(--sc-positive,#0a8a5f)", "CURRENT NORMAL")


def _staleness_tier(snapshot_date: Optional[str], cadence_days: Optional[int],
                    lag_tolerant: bool, today) -> tuple:
    """(color, label, age_days|None) for a source's freshness chip.

    Compares snapshot age to its OWN publication cadence: ≤1.5× = current,
    ≤3× = aging, >3× = stale. lag_tolerant sources (HCRIS) always read
    'current normal' since their multi-month publication lag is expected, not
    a defect. Missing date/cadence → 'date unstated' (honest, not green)."""
    from datetime import date as _date
    if lag_tolerant:
        return (*_STALE_NORMAL, None)
    if not snapshot_date or not cadence_days:
        return (*_STALE_GRAY, None)
    try:
        y, m, d = (int(x) for x in snapshot_date.split("-"))
        snap = _date(y, m, d)
    except Exception:  # noqa: BLE001 — bad date string → unstated, never raise
        return (*_STALE_GRAY, None)
    age = (today - snap).days
    if age < 0:
        return (*_STALE_GRAY, None)
    ratio = age / cadence_days
    if ratio <= 1.5:
        return (*_STALE_GREEN, age)
    if ratio <= 3.0:
        return (*_STALE_AMBER, age)
    return (*_STALE_RED, age)


def _staleness_chip(src: "WiredSource", today) -> str:
    color, label, age = _staleness_tier(
        src.snapshot_date, src.cadence_days, src.lag_tolerant, today)
    age_bit = (f' · {age}d old' if age is not None else "")
    return (f'<span title="Cadence: {_html.escape(src.cadence_note)}{age_bit}" '
            f'style="font-family:var(--sc-mono);font-size:8.5px;font-weight:700;'
            f'letter-spacing:0.05em;color:{color};border:1px solid {color};'
            f'padding:1px 5px;border-radius:2px;white-space:nowrap;">'
            f'{label}</span>')


def _hcris_stats() -> dict:
    from ..data.hcris import _get_latest_per_ccn
    df = _get_latest_per_ccn()
    nulls = {c: float(df[c].isna().mean())
             for c in ("beds", "medicaid_day_pct", "gross_patient_revenue",
                       "net_patient_revenue")}
    return {"rows": int(len(df)),
            "nulls": nulls,
            "vintage": f"FY{int(df['fiscal_year'].min())}–{int(df['fiscal_year'].max())} filings"}


def _vertical_stats(mod_name: str, fn_name: str, vintage: str):
    def _f() -> dict:
        import importlib
        m = importlib.import_module(f"rcm_mc.data.{mod_name}")
        providers = getattr(m, fn_name)()
        return {"rows": int(len(providers)), "nulls": {}, "vintage": vintage}
    return _f


# Vintages per the loader docstrings (the vendoring dates documented there).
WIRED: List[WiredSource] = [
    WiredSource("HCRIS hospital cost reports", _hcris_stats,
                "Annual; CMS publishes ~18 months after FY end — FY2020–22 "
                "filings are the current normal, not staleness.",
                ["/target-screener (hospitals)", "/diligence/hcris-xray",
                 "/command-center", "/market-data", "/predictive-screener",
                 "/pipeline/rollup", "/diligence/cim-crosscheck",
                 "/ebitda-bridge", "/regression"],
                "CMS HCRIS", cadence_days=365, lag_tolerant=True),
    WiredSource("Home Health Compare", _vertical_stats(
        "home_health", "load_home_health_providers", "vendored snapshot (dataset 6jpm-sxkc)"),
        "Quarterly refresh at CMS.", ["/target-screener (home_health)"],
        "CMS Home Health Compare", cadence_days=92),
    WiredSource("Hospice Compare", _vertical_stats(
        "hospice", "load_hospice_providers", "vendored snapshot (yc9t-dgbk)"),
        "Quarterly refresh at CMS.", ["/target-screener (hospice)"],
        "CMS Hospice Compare", cadence_days=92),
    WiredSource("Nursing Home Care Compare", _vertical_stats(
        "snf", "load_snf_providers", "vendored snapshot (Apr 2026 NH_ProviderInfo)"),
        "Monthly refresh at CMS.", ["/target-screener (snf)"],
        "CMS Nursing Home Compare", cadence_days=31, snapshot_date="2026-04-01"),
    WiredSource("Dialysis Facility Compare", _vertical_stats(
        "dialysis", "load_dialysis_providers", "vendored snapshot (Mar 2026 DFC_FACILITY)"),
        "Quarterly refresh at CMS.", ["/target-screener (dialysis)"],
        "CMS Dialysis Compare", cadence_days=92, snapshot_date="2026-03-01"),
    WiredSource("IRF Compare", _vertical_stats(
        "irf", "load_irf_providers", "vendored snapshot (Feb 2026)"),
        "Quarterly refresh at CMS.", ["/target-screener (irf)"],
        "CMS IRF Compare", cadence_days=92, snapshot_date="2026-02-01"),
    WiredSource("LTCH Compare", _vertical_stats(
        "ltch", "load_ltch_providers", "vendored snapshot (Feb 2026)"),
        "Quarterly refresh at CMS.", ["/target-screener (ltch)"],
        "CMS LTCH Compare", cadence_days=92, snapshot_date="2026-02-01"),
]


def _registered_unwired() -> List[dict]:
    """Sources catalogued in the vendor registry that no loader serves yet —
    the named backlog, not a hidden gap."""
    import pandas as pd
    from pathlib import Path
    reg = Path(__file__).resolve().parent.parent / "data" / "vendor" / "source_registry.csv"
    if not reg.exists():
        return []
    try:
        df = pd.read_csv(reg)
    except Exception:  # noqa: BLE001
        return []
    out = []
    for _, r in df.iterrows():
        out.append({"source_id": str(r.get("source_id") or ""),
                    "url": str(r.get("source_url") or ""),
                    "year": str(r.get("year") or ""),
                    "publisher": str(r.get("publisher") or "")})
    return out


def render_data_quality(qs: Optional[Dict[str, List[str]]] = None) -> str:
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).date()
    # ── wired sources, live-computed ──
    rows_html = ""
    total_rows = 0
    n_sources_ok = 0
    for src in WIRED:
        try:
            stats = src.loader()
            n_sources_ok += 1
        except Exception as exc:  # noqa: BLE001 — a broken loader IS the finding
            rows_html += (
                f'<tr><td style="padding:6px 8px;">{_html.escape(src.name)}</td>'
                f'<td colspan="4" style="padding:6px 8px;color:var(--sc-negative,#b5321e);">'
                f'LOADER FAILED: {_html.escape(str(exc)[:80])}</td></tr>')
            continue
        total_rows += stats["rows"]
        nulls = stats.get("nulls") or {}
        null_s = " · ".join(f"{k} {v*100:.1f}%" for k, v in nulls.items()) or "—"
        consumers = ", ".join(src.consumers[:4]) + (
            f" +{len(src.consumers)-4} more" if len(src.consumers) > 4 else "")
        rows_html += (
            '<tr style="border-bottom:1px solid var(--sc-rule,#e4ddca);">'
            f'<td style="padding:6px 8px;">{ck_source_link(src.source_label)}'
            f'<div style="font-size:10px;color:var(--sc-text-dim,#6a7480);">'
            f'{_html.escape(src.name)}</div></td>'
            f'<td class="num" style="padding:6px 8px;text-align:right;'
            f'font-variant-numeric:tabular-nums;">{stats["rows"]:,}</td>'
            f'<td style="padding:6px 8px;font-size:11px;">'
            f'{_staleness_chip(src, today)} {_html.escape(stats["vintage"])}'
            f'<div style="font-size:10px;color:var(--sc-text-dim,#6a7480);">'
            f'{_html.escape(src.cadence_note)}</div></td>'
            f'<td style="padding:6px 8px;font-size:10.5px;font-variant-numeric:tabular-nums;">{_html.escape(null_s)}</td>'
            f'<td style="padding:6px 8px;font-size:10.5px;">{_html.escape(consumers)}</td>'
            '</tr>')

    wired_panel = ck_panel(
        '<div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;">'
        '<thead><tr style="border-bottom:2px solid var(--sc-rule,#c9c1ac);">'
        '<th style="text-align:left;padding:6px 8px;">Source</th>'
        '<th style="text-align:right;padding:6px 8px;">Rows (live count)</th>'
        '<th style="text-align:left;padding:6px 8px;">Vintage · cadence</th>'
        '<th style="text-align:left;padding:6px 8px;">Null rates (key fields)</th>'
        '<th style="text-align:left;padding:6px 8px;">Pages consuming</th>'
        f'</tr></thead><tbody>{rows_html}</tbody></table></div>'
        '<p class="ck-section-body" style="font-size:11px;margin:8px 0 0;'
        'color:var(--sc-text-dim,#6a7480);">Counts and null rates are computed '
        'at render from the same loaders the product uses — this table cannot '
        'drift from what pages display. The freshness chip compares each '
        'snapshot\'s age to its own publication cadence — '
        '<strong style="color:var(--sc-positive,#0a8a5f);">CURRENT</strong> '
        '(≤1.5 cycles) · '
        '<strong style="color:var(--sc-warning,#b8732a);">AGING</strong> '
        '(≤3) · '
        '<strong style="color:var(--sc-negative,#b5321e);">STALE</strong> '
        '(&gt;3). HCRIS reads CURRENT NORMAL because its ~18-month publication '
        'lag is expected, not staleness.</p>',
        title="Wired sources — live stats")

    # ── gap census (reuse the registry the red dots map to) ──
    gap_rows = ""
    try:
        from ..data.gap_fill_registry import gap_report
        from ..diligence.hcris_xray import load_all_metrics
        rep = gap_report(load_all_metrics())
        for r in rep:
            kind = {"reingest": "RE-INGEST", "external": "EXTERNAL",
                    "artifact": "ARTIFACT"}.get(r["fill_kind"], "?")
            kcolor = ("var(--sc-warning,#b8732a)" if kind != "ARTIFACT"
                      else "var(--sc-text-dim,#6a7480)")
            gap_rows += (
                '<tr style="border-bottom:1px solid var(--sc-rule,#e4ddca);">'
                f'<td style="padding:5px 8px;">{_html.escape(r["label"])}</td>'
                f'<td class="num" style="padding:5px 8px;text-align:right;">'
                f'{r["gaps"]:,} ({r["gap_pct"]:.1f}%)</td>'
                f'<td style="padding:5px 8px;"><span style="font-family:var(--sc-mono);'
                f'font-size:9px;color:{kcolor};border:1px solid {kcolor};'
                f'padding:1px 5px;border-radius:2px;">{kind}</span></td>'
                f'<td style="padding:5px 8px;font-size:10.5px;">{_html.escape(r["source"])}</td>'
                '</tr>')
    except Exception as exc:  # noqa: BLE001
        gap_rows = (f'<tr><td colspan="4" style="padding:6px 8px;'
                    f'color:var(--sc-negative,#b5321e);">gap census failed: '
                    f'{_html.escape(str(exc)[:80])}</td></tr>')
    gaps_panel = ck_panel(
        '<div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;">'
        '<thead><tr style="border-bottom:2px solid var(--sc-rule,#c9c1ac);">'
        '<th style="text-align:left;padding:5px 8px;">Metric</th>'
        '<th style="text-align:right;padding:5px 8px;">Gaps (hospital-years)</th>'
        '<th style="text-align:left;padding:5px 8px;">Fill kind</th>'
        '<th style="text-align:left;padding:5px 8px;">Fill source / reason</th>'
        f'</tr></thead><tbody>{gap_rows}</tbody></table></div>'
        '<p class="ck-section-body" style="font-size:11px;margin:8px 0 0;'
        'color:var(--sc-text-dim,#6a7480);">Same census as '
        '<code>rcm-mc data gaps</code>; red dots across the product map here. '
        'ARTIFACT = the filing itself is inconsistent — flagged, not fillable.</p>',
        title="Gap census — where red dots come from")

    # ── registered-but-unwired catalog ──
    unwired = _registered_unwired()
    uw_rows = "".join(
        '<tr style="border-bottom:1px solid var(--sc-rule,#e4ddca);">'
        f'<td style="padding:4px 8px;font-family:var(--sc-mono);font-size:10.5px;">'
        f'{_html.escape(u["source_id"])}</td>'
        f'<td style="padding:4px 8px;font-size:10.5px;">{_html.escape(u["year"])}</td>'
        f'<td style="padding:4px 8px;font-size:10.5px;">{_html.escape(u["url"][:60])}</td>'
        '</tr>' for u in unwired)
    unwired_panel = ck_panel(
        '<div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;">'
        '<thead><tr style="border-bottom:2px solid var(--sc-rule,#c9c1ac);">'
        '<th style="text-align:left;padding:4px 8px;">source_id</th>'
        '<th style="text-align:left;padding:4px 8px;">Vintage</th>'
        '<th style="text-align:left;padding:4px 8px;">Origin</th>'
        f'</tr></thead><tbody>{uw_rows}</tbody></table></div>'
        '<p class="ck-section-body" style="font-size:11px;margin:8px 0 0;'
        'color:var(--sc-text-dim,#6a7480);">Catalogued in '
        'rcm_mc/data/vendor/source_registry.csv with vintages — the named '
        'wiring backlog, not hidden gaps.</p>',
        title=f"Registered, not yet wired ({len(unwired)})")

    kpis = (
        '<div class="ck-kpi-grid">'
        + ck_kpi_block("Wired sources", f"{n_sources_ok}/{len(WIRED)}")
        + ck_kpi_block("Live rows served", f"{total_rows:,}")
        + ck_kpi_block("Registered (unwired)", f"{len(unwired)}")
        + '</div>')

    body = (
        ck_page_title(
            "Data Quality",
            eyebrow="LIBRARY · INTERNAL CERTIFICATION",
            meta="Certify the data layer in 60 seconds: live row counts, "
                 "null rates, vintages, gap census, and consumers per source.")
        + kpis + wired_panel + gaps_panel + unwired_panel)
    return chartis_shell(body, "Data Quality", active_nav="/data-quality",
                         subtitle="Live source stats · gap census · consumers")
