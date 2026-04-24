"""HTTP page renderers for the four RCM Diligence tabs.

Phase 14 of the UI v2 editorial rework wires every tab to live
backends. Each tab accepts a ``?dataset=<fixture_name>`` query param;
when set, the page runs the real pipeline (ingest → KPI → cohort →
waterfall → advisory) and renders the results under the editorial
shell. With no param, each tab renders a minimal "pick a fixture"
selector so the analyst can drive without leaving the page.

Available datasets (shipped as kpi_truth fixtures under
``tests/fixtures/kpi_truth/``):

- hospital_01_clean_acute
- hospital_02_denial_heavy
- hospital_03_censoring
- hospital_04_mixed_payer
- hospital_05_dental_dso
- hospital_06_waterfall_truth

Auth-aware file uploads are deferred — this wiring uses the existing
kpi_truth fixtures as the demo corpus, so the tabs are immediately
usable without a partner touching the filesystem.
"""
from __future__ import annotations

import html
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..ui._chartis_kit import chartis_shell
from ..ui.brand import PALETTE


FIXTURE_ROOT = (
    Path(__file__).resolve().parent.parent.parent
    / "tests" / "fixtures" / "kpi_truth"
)

# Known fixtures + short labels for the selector. Expanding this list
# costs nothing; the page renderers iterate it.
AVAILABLE_FIXTURES: List[Tuple[str, str]] = [
    ("hospital_01_clean_acute",     "Hospital 01 — Clean acute baseline"),
    ("hospital_02_denial_heavy",    "Hospital 02 — Denial-heavy outpatient"),
    ("hospital_03_censoring",       "Hospital 03 — Cohort censoring (young + mature)"),
    ("hospital_04_mixed_payer",     "Hospital 04 — 5/5/5/5 mixed payer"),
    ("hospital_05_dental_dso",      "Hospital 05 — Dental DSO proxy (OOD test)"),
    ("hospital_06_waterfall_truth", "Hospital 06 — Waterfall hand-computed truth"),
    ("hospital_07_waterfall_concordant", "Hospital 07 — QoR concordant (IMMATERIAL)"),
    ("hospital_08_waterfall_critical",   "Hospital 08 — QoR critical (CRITICAL ~7%)"),
]


# ── Shared fragments ────────────────────────────────────────────────

def _hero(title: str, sub: str) -> str:
    return (
        f'<div style="padding:24px 0 12px 0;">'
        f'  <div style="font-size:11px;color:{PALETTE["text_faint"]};'
        f'letter-spacing:.75px;text-transform:uppercase;margin-bottom:6px;">'
        f'RCM Diligence Workspace</div>'
        f'  <div style="font-size:20px;color:{PALETTE["text"]};font-weight:600;'
        f'margin-bottom:8px;">{html.escape(title)}</div>'
        f'  <div style="font-size:13px;color:{PALETTE["text_dim"]};'
        f'max-width:720px;line-height:1.55;">{html.escape(sub)}</div>'
        f'</div>'
    )


def _fixture_selector(current_tab_route: str, current_dataset: str = "") -> str:
    """Render a compact dropdown with every fixture. Submitting the
    form reloads the same tab with ``?dataset=<picked>``."""
    options = "".join(
        f'<option value="{html.escape(name)}"'
        f'{" selected" if name == current_dataset else ""}>'
        f'{html.escape(label)}</option>'
        for name, label in AVAILABLE_FIXTURES
    )
    return (
        f'<form method="GET" action="{html.escape(current_tab_route)}" '
        f'style="display:flex;align-items:center;gap:12px;margin:16px 0;">'
        f'<label style="font-size:11px;color:{PALETTE["text_faint"]};'
        f'letter-spacing:.14em;text-transform:uppercase;">Dataset:</label>'
        f'<select name="dataset" style="padding:6px 10px;'
        f'border:1px solid {PALETTE["border"]};background:{PALETTE["panel"]};'
        f'color:{PALETTE["text"]};font-size:12px;font-family:inherit;'
        f'min-width:320px;">'
        f'<option value="">— pick a fixture —</option>{options}'
        f'</select>'
        f'<button type="submit" style="padding:6px 14px;'
        f'background:{PALETTE["brand_primary"]};color:{PALETTE["panel"]};'
        f'border:0;font-size:11px;font-weight:600;letter-spacing:.08em;'
        f'text-transform:uppercase;cursor:pointer;">Load</button>'
        f'</form>'
    )


def _ccd_summary_card(ccd: Any) -> str:
    """Compact one-card CCD summary: ingest_id, claim count, source
    files, content hash."""
    from .ingest.ccd import CanonicalClaimsDataset  # noqa: F401
    source_list = "".join(
        f'<li style="font-family:\'JetBrains Mono\',monospace;font-size:11px;'
        f'color:{PALETTE["text_dim"]};">{html.escape(str(f))}</li>'
        for f in (ccd.source_files or [])
    )
    return (
        f'<div style="background:{PALETTE["panel"]};'
        f'border:1px solid {PALETTE["border"]};padding:14px 16px;'
        f'margin:12px 0;">'
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:baseline;margin-bottom:10px;">'
        f'<div style="font-size:13px;font-weight:600;color:{PALETTE["text"]};">'
        f'Canonical Claims Dataset</div>'
        f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;'
        f'color:{PALETTE["text_faint"]};letter-spacing:.1em;">'
        f'{html.escape(ccd.ingest_id)}</div>'
        f'</div>'
        f'<div style="display:grid;grid-template-columns:repeat(4,1fr);'
        f'gap:12px;font-size:12px;">'
        f'<div><div style="color:{PALETTE["text_faint"]};font-size:10px;'
        f'letter-spacing:.14em;text-transform:uppercase;">Claims</div>'
        f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:18px;'
        f'color:{PALETTE["text"]};">{len(ccd.claims):,}</div></div>'
        f'<div><div style="color:{PALETTE["text_faint"]};font-size:10px;'
        f'letter-spacing:.14em;text-transform:uppercase;">Schema</div>'
        f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:12px;'
        f'color:{PALETTE["text"]};">{html.escape(ccd.ccd_schema_version)}</div></div>'
        f'<div><div style="color:{PALETTE["text_faint"]};font-size:10px;'
        f'letter-spacing:.14em;text-transform:uppercase;">Source files</div>'
        f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:12px;'
        f'color:{PALETTE["text"]};">{len(ccd.source_files)}</div></div>'
        f'<div><div style="color:{PALETTE["text_faint"]};font-size:10px;'
        f'letter-spacing:.14em;text-transform:uppercase;">Content hash</div>'
        f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:12px;'
        f'color:{PALETTE["text"]};">{html.escape(ccd.content_hash()[:12])}…</div></div>'
        f'</div>'
        f'{("<ul style=\"margin:10px 0 0 20px;padding:0;\">" + source_list + "</ul>") if source_list else ""}'
        f'</div>'
    )


def _resolve_dataset(dataset: str) -> Optional[Path]:
    if not dataset:
        return None
    valid = {name for name, _ in AVAILABLE_FIXTURES}
    if dataset not in valid:
        return None
    path = FIXTURE_ROOT / dataset
    if not path.exists():
        return None
    return path


def _err_panel(title: str, msg: str) -> str:
    return (
        f'<div style="background:{PALETTE["panel"]};'
        f'border-left:3px solid {PALETTE["negative"]};'
        f'padding:14px 16px;margin:12px 0;">'
        f'<div style="color:{PALETTE["negative"]};font-weight:600;'
        f'margin-bottom:4px;">{html.escape(title)}</div>'
        f'<div style="color:{PALETTE["text_dim"]};font-size:13px;">'
        f'{html.escape(msg)}</div></div>'
    )


def _info_strip(text: str) -> str:
    return (
        f'<div style="padding:10px 16px;background:{PALETTE["panel_alt"]};'
        f'border-left:3px solid {PALETTE["accent"]};font-size:12px;'
        f'color:{PALETTE["text_dim"]};margin:8px 0;">{html.escape(text)}</div>'
    )


# ── Phase 1: /diligence/ingest ─────────────────────────────────────

def render_ingest_page(dataset: str = "") -> str:
    body = [
        _hero(
            "Phase 1 — Ingestion & Normalization",
            "Raw 837 / 835 EDI, Epic / Cerner / Athena exports, and "
            "messy Excel funnelled into a single versioned Canonical "
            "Claims Dataset (CCD). Every transformation is row-logged.",
        ),
        _fixture_selector("/diligence/ingest", dataset),
    ]

    ds_path = _resolve_dataset(dataset)
    if ds_path is not None:
        try:
            from . import ingest_dataset
            ccd = ingest_dataset(ds_path)
            body.append(_ccd_summary_card(ccd))
            body.append(_transformation_log_preview(ccd))
        except Exception as exc:
            body.append(_err_panel(
                "Ingestion failed",
                f"{type(exc).__name__}: {exc}",
            ))
    else:
        body.append(_info_strip(
            "Pick a fixture above to run the Phase 1 ingester against "
            "canonical truth data. Each fixture ships with an "
            "expected.json contract; the regression suite locks the "
            "ingester output against those values."
        ))
    return chartis_shell(
        "\n".join(body), "RCM Diligence — Ingestion",
        subtitle="Phase 1 of 4 · Canonical Claims Dataset",
    )


def _transformation_log_preview(ccd: Any) -> str:
    """Show the TransformationLog summary + first 20 entries."""
    summary = ccd.log.summary()
    if not summary:
        return _info_strip("Transformation log is empty — this "
                           "fixture's rows passed through without "
                           "coercion.")
    ranked = sorted(summary.items(), key=lambda kv: -kv[1])[:8]
    chips = "".join(
        f'<span style="display:inline-flex;align-items:center;gap:6px;'
        f'padding:3px 10px;background:{PALETTE["panel_alt"]};'
        f'border:1px solid {PALETTE["border"]};font-size:11px;'
        f'font-family:\'JetBrains Mono\',monospace;margin:2px;">'
        f'<span style="color:{PALETTE["text"]};">{html.escape(rule)}</span>'
        f'<span style="color:{PALETTE["text_faint"]};">{count}</span>'
        f'</span>'
        for rule, count in ranked
    )
    entries = ccd.log.entries[:20]
    rows = "".join(
        f'<tr>'
        f'<td style="padding:4px 8px;font-family:\'JetBrains Mono\',monospace;'
        f'font-size:10px;color:{PALETTE["text_faint"]};">{html.escape(e.ccd_row_id)}</td>'
        f'<td style="padding:4px 8px;font-family:\'JetBrains Mono\',monospace;'
        f'font-size:10px;color:{PALETTE["text_dim"]};">{html.escape(e.source_file)}</td>'
        f'<td style="padding:4px 8px;font-family:\'JetBrains Mono\',monospace;'
        f'font-size:10px;color:{PALETTE["text_dim"]};">{e.source_row}</td>'
        f'<td style="padding:4px 8px;font-family:\'JetBrains Mono\',monospace;'
        f'font-size:10px;color:{PALETTE["text"]};">{html.escape(e.rule)}</td>'
        f'<td style="padding:4px 8px;font-size:11px;color:{PALETTE["text"]};">'
        f'{html.escape(e.target_field)}</td>'
        f'<td style="padding:4px 8px;font-family:\'JetBrains Mono\',monospace;'
        f'font-size:10px;color:{PALETTE["text_faint"]};">'
        f'{html.escape(e.severity)}</td>'
        f'</tr>'
        for e in entries
    )
    return (
        f'<div style="margin:16px 0;">'
        f'<div style="font-size:11px;color:{PALETTE["text_dim"]};'
        f'letter-spacing:.12em;text-transform:uppercase;margin-bottom:8px;">'
        f'Transformation log · {len(ccd.log.entries):,} total · top rules:'
        f'</div>'
        f'<div style="margin-bottom:12px;">{chips}</div>'
        f'<table style="width:100%;border-collapse:collapse;'
        f'background:{PALETTE["panel"]};border:1px solid {PALETTE["border"]};">'
        f'<thead><tr style="background:{PALETTE["panel_alt"]};">'
        f'<th style="padding:6px 8px;text-align:left;font-size:10px;'
        f'color:{PALETTE["text_dim"]};letter-spacing:.1em;'
        f'text-transform:uppercase;">ccd_row_id</th>'
        f'<th style="padding:6px 8px;text-align:left;font-size:10px;'
        f'color:{PALETTE["text_dim"]};letter-spacing:.1em;'
        f'text-transform:uppercase;">source_file</th>'
        f'<th style="padding:6px 8px;text-align:left;font-size:10px;'
        f'color:{PALETTE["text_dim"]};letter-spacing:.1em;'
        f'text-transform:uppercase;">row</th>'
        f'<th style="padding:6px 8px;text-align:left;font-size:10px;'
        f'color:{PALETTE["text_dim"]};letter-spacing:.1em;'
        f'text-transform:uppercase;">rule</th>'
        f'<th style="padding:6px 8px;text-align:left;font-size:10px;'
        f'color:{PALETTE["text_dim"]};letter-spacing:.1em;'
        f'text-transform:uppercase;">target_field</th>'
        f'<th style="padding:6px 8px;text-align:left;font-size:10px;'
        f'color:{PALETTE["text_dim"]};letter-spacing:.1em;'
        f'text-transform:uppercase;">severity</th>'
        f'</tr></thead><tbody>{rows}</tbody></table>'
        f'{_info_strip(f"Showing 20 of {len(ccd.log.entries):,} entries; every entry traces a coerced value back to its source file + row.") if len(ccd.log.entries) > 20 else ""}'
        f'</div>'
    )


# ── Phase 2: /diligence/benchmarks ─────────────────────────────────

def render_benchmarks_page(
    dataset: str = "",
    *,
    bundle=None, cohort_report=None, cash_waterfall=None,
) -> str:
    """Delegates to ``rcm_mc.ui.diligence_benchmarks`` for the full
    rendering when a bundle is available. When ``dataset`` is supplied,
    ingests + computes KPIs + cohort + waterfall live and passes them
    through.
    """
    from ..ui.diligence_benchmarks import render_benchmarks_page as _render

    # Fast path: caller passed a pre-computed bundle (old API).
    if bundle is not None:
        return _render(
            bundle=bundle, cohort_report=cohort_report,
            cash_waterfall=cash_waterfall,
        )

    ds_path = _resolve_dataset(dataset)
    if ds_path is None:
        placeholder = _render()  # renders the placeholder
        selector = _fixture_selector("/diligence/benchmarks", dataset)
        # Inject the selector into the placeholder body — crude but
        # keeps the shell consistent with the ingest tab.
        return placeholder.replace("</main>", selector + "</main>", 1) \
            if "</main>" in placeholder else placeholder

    try:
        from . import (
            compute_cohort_liquidation, compute_kpis, ingest_dataset,
        )
        from .benchmarks import compute_cash_waterfall
        ccd = ingest_dataset(ds_path)
        as_of = date(2025, 1, 1)
        bundle = compute_kpis(ccd, as_of_date=as_of, provider_id=dataset)
        cohort = compute_cohort_liquidation(ccd.claims, as_of_date=as_of)
        waterfall = compute_cash_waterfall(ccd.claims, as_of_date=as_of)
    except Exception as exc:
        err_body = (
            _hero("Phase 2 — Benchmarks (error)",
                  "Computation failed. See detail below.")
            + _fixture_selector("/diligence/benchmarks", dataset)
            + _err_panel(f"Pipeline error on {dataset!r}",
                         f"{type(exc).__name__}: {exc}")
        )
        return chartis_shell(
            err_body, "RCM Diligence — Benchmarks",
            subtitle="Phase 2 of 4",
        )

    live_html = _render(bundle=bundle, cohort_report=cohort,
                        cash_waterfall=waterfall)
    selector = _fixture_selector("/diligence/benchmarks", dataset)
    # Prepend the selector to the live page body.
    if "<main" in live_html:
        idx = live_html.find(">", live_html.find("<main"))
        if idx > 0:
            live_html = live_html[: idx + 1] + selector + live_html[idx + 1:]
    return live_html


# ── Phase 3: /diligence/root-cause ─────────────────────────────────

def render_root_cause_page(dataset: str = "") -> str:
    body = [
        _hero(
            "Phase 3 — Root Cause Analysis",
            "Pareto drivers for every off-benchmark KPI. ZBA autopsy "
            "surfaces recoverable write-offs. Every finding is one "
            "click from the underlying rows in the CCD.",
        ),
        _fixture_selector("/diligence/root-cause", dataset),
    ]

    ds_path = _resolve_dataset(dataset)
    if ds_path is None:
        body.append(_info_strip(
            "Pick a fixture above to run the denial stratification + "
            "ZBA autopsy. Every driver row is one click from the "
            "underlying claim IDs that fed it."
        ))
    else:
        try:
            from . import compute_kpis, ingest_dataset
            ccd = ingest_dataset(ds_path)
            bundle = compute_kpis(ccd, as_of_date=date(2025, 1, 1),
                                   provider_id=dataset)
            body.append(_denial_pareto(bundle.denial_stratification))
            body.append(_zba_autopsy(ccd.claims))
        except Exception as exc:
            body.append(_err_panel(
                "Root-cause computation failed",
                f"{type(exc).__name__}: {exc}",
            ))
    return chartis_shell(
        "\n".join(body), "RCM Diligence — Root Cause",
        subtitle="Phase 3 of 4",
    )


def _denial_pareto(rows) -> str:
    """Mini Pareto — category × dollars. Full drill-through is the
    Phase 2 benchmarks surface; this is the compact Phase-3 view."""
    rows = list(rows or [])
    if not rows:
        return _info_strip("No denials in this fixture's claim set.")
    total = sum(r.dollars_denied for r in rows) or 1.0
    items = []
    for r in rows:
        pct = r.dollars_denied / total
        bar = max(pct * 100, 2)
        items.append(
            f'<div style="margin-bottom:10px;">'
            f'<div style="display:flex;justify-content:space-between;'
            f'font-size:12px;margin-bottom:4px;">'
            f'<span style="color:{PALETTE["text"]};font-weight:500;">'
            f'{html.escape(r.category)}</span>'
            f'<span style="font-family:\'JetBrains Mono\',monospace;'
            f'color:{PALETTE["text_dim"]};">'
            f'${r.dollars_denied:,.0f} · {r.count} claims · {pct*100:.1f}%'
            f'</span></div>'
            f'<div style="background:{PALETTE["panel_alt"]};height:5px;">'
            f'<div style="background:{PALETTE["accent"]};height:100%;'
            f'width:{bar}%;"></div></div></div>'
        )
    return (
        f'<div style="margin:16px 0;">'
        f'<div style="font-size:11px;color:{PALETTE["text_dim"]};'
        f'letter-spacing:.14em;text-transform:uppercase;margin-bottom:12px;">'
        f'Denial Pareto by ANSI CARC category</div>'
        f'<div style="background:{PALETTE["panel"]};'
        f'border:1px solid {PALETTE["border"]};padding:14px 16px;">'
        f'{"".join(items)}</div></div>'
    )


def _zba_autopsy(claims) -> str:
    """List every ZBA-flagged row — claims with nonzero adjustment +
    zero paid — showing the preserved original balance."""
    zba = [c for c in claims
           if (c.paid_amount or 0) == 0
           and (c.adjustment_amount or 0) > 0]
    if not zba:
        return _info_strip("No zero-balance write-offs in this fixture.")
    rows = "".join(
        f'<tr>'
        f'<td style="padding:6px 10px;font-family:\'JetBrains Mono\',monospace;'
        f'font-size:11px;color:{PALETTE["text"]};">'
        f'{html.escape(c.claim_id)}</td>'
        f'<td style="padding:6px 10px;font-size:11px;color:{PALETTE["text_dim"]};">'
        f'{html.escape(c.payer_canonical or c.payer_raw or "—")}</td>'
        f'<td style="padding:6px 10px;text-align:right;font-family:\'JetBrains Mono\',monospace;'
        f'font-size:11px;color:{PALETTE["text"]};">${c.charge_amount or 0:,.2f}</td>'
        f'<td style="padding:6px 10px;text-align:right;font-family:\'JetBrains Mono\',monospace;'
        f'font-size:11px;color:{PALETTE["text"]};">${c.allowed_amount or 0:,.2f}</td>'
        f'<td style="padding:6px 10px;text-align:right;font-family:\'JetBrains Mono\',monospace;'
        f'font-size:11px;color:{PALETTE["negative"]};">${c.adjustment_amount or 0:,.2f}</td>'
        f'<td style="padding:6px 10px;font-family:\'JetBrains Mono\',monospace;'
        f'font-size:10px;color:{PALETTE["text_faint"]};">'
        f'{html.escape(", ".join(c.adjustment_reason_codes or ()))}</td>'
        f'</tr>'
        for c in zba[:50]
    )
    return (
        f'<div style="margin:16px 0;">'
        f'<div style="font-size:11px;color:{PALETTE["text_dim"]};'
        f'letter-spacing:.14em;text-transform:uppercase;margin-bottom:8px;">'
        f'ZBA Autopsy · {len(zba)} recoverable write-off(s) '
        f'(charge + allowed + adjustment trail preserved)</div>'
        f'<table style="width:100%;border-collapse:collapse;'
        f'background:{PALETTE["panel"]};border:1px solid {PALETTE["border"]};">'
        f'<thead><tr style="background:{PALETTE["panel_alt"]};">'
        f'<th style="padding:6px 10px;text-align:left;font-size:10px;'
        f'color:{PALETTE["text_dim"]};letter-spacing:.1em;'
        f'text-transform:uppercase;">Claim</th>'
        f'<th style="padding:6px 10px;text-align:left;font-size:10px;'
        f'color:{PALETTE["text_dim"]};letter-spacing:.1em;'
        f'text-transform:uppercase;">Payer</th>'
        f'<th style="padding:6px 10px;text-align:right;font-size:10px;'
        f'color:{PALETTE["text_dim"]};letter-spacing:.1em;'
        f'text-transform:uppercase;">Charge</th>'
        f'<th style="padding:6px 10px;text-align:right;font-size:10px;'
        f'color:{PALETTE["text_dim"]};letter-spacing:.1em;'
        f'text-transform:uppercase;">Allowed</th>'
        f'<th style="padding:6px 10px;text-align:right;font-size:10px;'
        f'color:{PALETTE["text_dim"]};letter-spacing:.1em;'
        f'text-transform:uppercase;">Adjustment</th>'
        f'<th style="padding:6px 10px;text-align:left;font-size:10px;'
        f'color:{PALETTE["text_dim"]};letter-spacing:.1em;'
        f'text-transform:uppercase;">CARCs</th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>'
    )


# ── Phase 4: /diligence/value ──────────────────────────────────────

def render_value_page(dataset: str = "") -> str:
    body = [
        _hero(
            "Phase 4 — Value Creation Model",
            "Per-root-cause recoverable EBITDA feeds the v2 value "
            "bridge. Monte Carlo on payer behavior reuses the "
            "existing two-source simulator. Contract re-pricer "
            "supplies deal-specific payer leverage; the CMS advisory "
            "overlay sets market posture.",
        ),
        _fixture_selector("/diligence/value", dataset),
    ]

    ds_path = _resolve_dataset(dataset)
    if ds_path is None:
        body.append(_info_strip(
            "Pick a fixture above to see the contract re-pricer's "
            "derived payer leverage + a sample CMS advisory overlay. "
            "Full bridge wiring into the packet is a follow-up."
        ))
    else:
        try:
            from . import ingest_dataset
            ccd = ingest_dataset(ds_path)
            body.append(_repricer_summary(ccd))
            body.append(_cms_advisory_summary())
        except Exception as exc:
            body.append(_err_panel(
                "Value computation failed",
                f"{type(exc).__name__}: {exc}",
            ))
    return chartis_shell(
        "\n".join(body), "RCM Diligence — Value Creation",
        subtitle="Phase 4 of 4",
    )


def _repricer_summary(ccd: Any) -> str:
    """Run the contract re-pricer against a synthetic default schedule
    just to demonstrate the derived-leverage output."""
    from .benchmarks import (
        ContractRate, ContractSchedule, payer_leverage_for_bridge,
        reprice_claims,
    )
    # Synthetic default schedule covering the common CPTs in our fixtures.
    rates = [
        ContractRate("COMMERCIAL",         "99213", allowed_amount_usd=100.0),
        ContractRate("COMMERCIAL",         "99214", allowed_amount_usd=150.0),
        ContractRate("MEDICARE",           "99213", allowed_amount_usd=75.0),
        ContractRate("MEDICARE",           "99214", allowed_amount_usd=115.0),
        ContractRate("MEDICARE_ADVANTAGE", "99213", allowed_amount_usd=80.0),
        ContractRate("MEDICAID",           "99213", allowed_amount_usd=50.0),
        ContractRate("SELF_PAY",           "D1110", allowed_amount_usd=125.0),
    ]
    schedule = ContractSchedule(rates=rates, name="demo_default")
    report = reprice_claims(ccd.claims, schedule)
    leverage = payer_leverage_for_bridge(report)
    rows = "".join(
        f'<tr>'
        f'<td style="padding:6px 10px;font-family:\'JetBrains Mono\',monospace;'
        f'font-size:11px;color:{PALETTE["text"]};">{html.escape(pc)}</td>'
        f'<td style="padding:6px 10px;text-align:right;font-family:\'JetBrains Mono\',monospace;'
        f'font-size:11px;color:{PALETTE["text"]};">{lev:.3f}</td>'
        f'</tr>'
        for pc, lev in sorted(leverage.items(), key=lambda x: -x[1])
    )
    return (
        f'<div style="margin:16px 0;">'
        f'<div style="font-size:11px;color:{PALETTE["text_dim"]};'
        f'letter-spacing:.14em;text-transform:uppercase;margin-bottom:8px;">'
        f'Contract re-pricer · derived payer leverage '
        f'({report.matched_claims} matched / {report.unmatched_claims} unmatched '
        f'of {report.total_claims} claims)</div>'
        f'<table style="width:66%;border-collapse:collapse;'
        f'background:{PALETTE["panel"]};border:1px solid {PALETTE["border"]};">'
        f'<thead><tr style="background:{PALETTE["panel_alt"]};">'
        f'<th style="padding:6px 10px;text-align:left;font-size:10px;'
        f'color:{PALETTE["text_dim"]};letter-spacing:.1em;'
        f'text-transform:uppercase;">Payer class (bridge vocab)</th>'
        f'<th style="padding:6px 10px;text-align:right;font-size:10px;'
        f'color:{PALETTE["text_dim"]};letter-spacing:.1em;'
        f'text-transform:uppercase;">Leverage vs Commercial</th>'
        f'</tr></thead><tbody>{rows or "<tr><td colspan=2 style=\"padding:8px 10px;font-size:11px;color:#7a8699;\">No matched claims — contract lacks rates for this fixture's CPTs.</td></tr>"}</tbody></table>'
        f'{_info_strip("These values drop into BridgeAssumptions.payer_revenue_leverage; the v2 bridge uses them instead of the module-level defaults.")}'
        f'</div>'
    )


def _cms_advisory_summary() -> str:
    """Run the CMS advisory pipeline on a small synthetic frame to
    demonstrate the consensus rank + regime classifier."""
    try:
        import pandas as pd
        from ..pe.cms_advisory import (
            consensus_rank, momentum_profile, provider_volatility,
            regime_classification, screen_providers, yearly_trends,
        )
        df = pd.DataFrame([
            {"provider_type": "Internal Medicine", "year": y,
             "total_medicare_payment_amt": 1_000_000 * (1 + 0.08) ** i,
             "total_services": 10_000 * (1 + 0.06) ** i,
             "total_unique_benes": 2_000 * (1 + 0.04) ** i,
             "beneficiary_average_risk_score": 1.08,
             "payment_per_service": 100.0 * (1 + 0.02) ** i,
             "payment_per_bene": 500.0 * (1 + 0.04) ** i}
            for i, y in enumerate([2021, 2022, 2023])
        ] + [
            {"provider_type": "Cardiology", "year": y,
             "total_medicare_payment_amt": 3_000_000 * (1 + 0.15) ** i,
             "total_services": 5_000 * (1 + 0.1) ** i,
             "total_unique_benes": 1_000 * (1 + 0.05) ** i,
             "beneficiary_average_risk_score": 1.55,
             "payment_per_service": 600.0 * (1 + 0.05) ** i,
             "payment_per_bene": 3_000.0 * (1 + 0.1) ** i}
            for i, y in enumerate([2021, 2022, 2023])
        ])
        screen = screen_providers(df)
        trends = yearly_trends(df)
        vol = provider_volatility(trends)
        mom = momentum_profile(trends, min_years=2)
        regimes = regime_classification(mom, vol)
        cons = consensus_rank(screen, mom, vol)
    except Exception as exc:
        return _err_panel("CMS advisory demo failed",
                          f"{type(exc).__name__}: {exc}")

    # Render a two-column summary: regime + consensus rank.
    reg_rows = "".join(
        f'<tr>'
        f'<td style="padding:4px 8px;font-size:11px;color:{PALETTE["text"]};">'
        f'{html.escape(str(r.get("provider_type", "")))}</td>'
        f'<td style="padding:4px 8px;font-size:11px;color:{PALETTE["text_dim"]};">'
        f'{html.escape(str(r.get("regime", "")))}</td>'
        f'</tr>'
        for _, r in regimes.iterrows()
    )
    cons_rows = "".join(
        f'<tr>'
        f'<td style="padding:4px 8px;font-size:11px;color:{PALETTE["text"]};">'
        f'{html.escape(str(r.get("provider_type", "")))}</td>'
        f'<td style="padding:4px 8px;text-align:right;font-family:\'JetBrains Mono\',monospace;'
        f'font-size:11px;color:{PALETTE["text_dim"]};">'
        f'{float(r.get("consensus_score", 0)):.3f}</td>'
        f'<td style="padding:4px 8px;text-align:right;font-family:\'JetBrains Mono\',monospace;'
        f'font-size:11px;color:{PALETTE["text"]};">#{int(r.get("consensus_rank", 0))}</td>'
        f'</tr>'
        for _, r in cons.iterrows()
    )
    return (
        f'<div style="margin:16px 0;">'
        f'<div style="font-size:11px;color:{PALETTE["text_dim"]};'
        f'letter-spacing:.14em;text-transform:uppercase;margin-bottom:8px;">'
        f'CMS advisory overlay · synthetic 2-type × 3-year demo</div>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">'
        f'<div><div style="font-size:10px;color:{PALETTE["text_faint"]};'
        f'letter-spacing:.12em;text-transform:uppercase;margin-bottom:4px;">'
        f'Regime classification</div>'
        f'<table style="width:100%;border-collapse:collapse;'
        f'background:{PALETTE["panel"]};border:1px solid {PALETTE["border"]};">'
        f'{reg_rows}</table></div>'
        f'<div><div style="font-size:10px;color:{PALETTE["text_faint"]};'
        f'letter-spacing:.12em;text-transform:uppercase;margin-bottom:4px;">'
        f'Consensus rank</div>'
        f'<table style="width:100%;border-collapse:collapse;'
        f'background:{PALETTE["panel"]};border:1px solid {PALETTE["border"]};">'
        f'{cons_rows}</table></div>'
        f'</div>'
        f'{_info_strip("Regime + consensus flow into packet.risk_flags via rcm_mc.pe.cms_advisory_bridge.")}'
        f'</div>'
    )
