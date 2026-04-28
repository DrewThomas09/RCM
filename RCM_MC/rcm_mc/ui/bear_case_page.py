"""Bear Case Auto-Generator page.

Route: ``/diligence/bear-case``

Pulls from the Thesis Pipeline (or individual module outputs on
query params) and renders a partner-facing bear case: ranked
evidence cards, per-theme narratives, an IC-memo drop-in block
ready to paste into the deck, and deep links back to every source
module.

Demo moment: paste a dataset slug + target name; 200ms later see
"Your thesis is at risk on 7 CRITICAL items, $46.8M EBITDA at risk,
top 3 drivers are [C1] Net Leverage covenant breach Y3Q2, [R1] V28
MA-margin kill 2027-01-01, [B1] vendor consolidation unsupported
bridge lever."
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional

from ..diligence.bear_case import (
    BearCaseReport, Evidence, EvidenceSeverity, EvidenceSource,
    generate_bear_case_from_pipeline,
)
from ._chartis_kit import P, chartis_shell
from .power_ui import (
    benchmark_chip, bookmark_hint, deal_context_bar,
    export_json_panel, interpret_callout, provenance,
)


# ────────────────────────────────────────────────────────────────────
# Scoped CSS (bc- prefix)
# ────────────────────────────────────────────────────────────────────

def _scoped_styles() -> str:
    css = """
.bc-wrap{{font-family:"Helvetica Neue",Arial,sans-serif;}}
.bc-eyebrow{{font-size:11px;letter-spacing:1.6px;text-transform:uppercase;
color:{tf};font-weight:600;}}
.bc-h1{{font-size:26px;color:{tx};font-weight:600;line-height:1.15;
margin:4px 0 0 0;letter-spacing:-.2px;}}
.bc-section-label{{font-size:10px;letter-spacing:1.6px;text-transform:uppercase;
font-weight:700;color:{tf};margin:22px 0 10px 0;}}
.bc-panel{{background:{pn};border:1px solid {bd};border-radius:4px;
padding:14px 20px;margin-bottom:16px;}}
.bc-callout{{background:{pa};padding:12px 16px;border-left:3px solid {ac};
border-radius:0 3px 3px 0;font-size:12px;color:{td};line-height:1.65;
max-width:900px;margin-top:12px;}}
.bc-verdict-card{{background:linear-gradient(135deg,{pn} 0%,{pa} 100%);
border:1px solid {ne};border-radius:4px;padding:20px 24px;
position:relative;overflow:hidden;margin-top:14px;}}
.bc-verdict-card::before{{content:"";position:absolute;top:0;left:0;right:0;
height:3px;background:linear-gradient(90deg,{ne},{wn});}}
.bc-verdict-headline{{font-size:18px;color:{tx};font-weight:600;
line-height:1.45;}}
.bc-verdict-sub{{font-size:13px;color:{td};line-height:1.6;margin-top:10px;
max-width:900px;}}
.bc-kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
gap:14px;margin-top:14px;}}
.bc-kpi__label{{font-size:9px;letter-spacing:1.3px;text-transform:uppercase;
color:{tf};font-weight:600;margin-bottom:3px;}}
.bc-kpi__val{{font-size:28px;line-height:1;font-family:"JetBrains Mono",monospace;
font-variant-numeric:tabular-nums;font-weight:700;color:{tx};}}
.bc-kpi__val.crit{{color:{ne};}}
.bc-kpi__val.hi{{color:{wn};}}
.bc-kpi__val.lo{{color:{po};}}
.bc-evidence-card{{background:{pn};border:1px solid {bd};
border-left:3px solid var(--sev);border-radius:0 3px 3px 0;
padding:14px 18px;margin-bottom:12px;
transition:border-color 120ms, transform 120ms;}}
.bc-evidence-card:hover{{transform:translateX(2px);border-color:var(--sev);}}
.bc-sev-CRITICAL{{--sev:{ne};}}
.bc-sev-HIGH{{--sev:{wn};}}
.bc-sev-MEDIUM{{--sev:{tf};}}
.bc-sev-LOW{{--sev:{bd};}}
.bc-ev-head{{display:flex;gap:12px;flex-wrap:wrap;align-items:baseline;
justify-content:space-between;}}
.bc-ev-citation{{font-family:"JetBrains Mono",monospace;font-size:11px;
letter-spacing:1.2px;font-weight:700;padding:2px 7px;border-radius:2px;
color:#fff;background:var(--sev);}}
.bc-ev-title{{font-size:14.5px;color:{tx};font-weight:600;
line-height:1.4;flex:1 1 0;}}
.bc-ev-source{{font-size:9.5px;letter-spacing:1.2px;text-transform:uppercase;
color:{tf};font-weight:700;}}
.bc-ev-meta{{font-size:10.5px;letter-spacing:0.8px;color:{tf};margin-top:6px;}}
.bc-ev-meta strong{{color:{td};}}
.bc-ev-narrative{{font-size:12.5px;color:{td};line-height:1.65;
margin-top:10px;max-width:860px;}}
.bc-ev-impact{{font-family:"JetBrains Mono",monospace;font-size:14px;
font-weight:700;color:{ne};}}
.bc-theme-title{{font-size:12px;letter-spacing:1.4px;text-transform:uppercase;
font-weight:700;color:var(--sev);margin:18px 0 8px 0;}}
.bc-form-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
gap:14px;}}
.bc-form-field label{{display:block;font-size:10px;color:{tf};
letter-spacing:1.2px;text-transform:uppercase;font-weight:600;margin-bottom:4px;}}
.bc-form-field input{{width:100%;
background:{pa};color:{tx};border:1px solid {bd};padding:8px 10px;
border-radius:3px;font-family:"JetBrains Mono",monospace;font-size:13px;}}
.bc-form-submit{{margin-top:18px;padding:10px 20px;background:{ne};
color:#fff;border:0;border-radius:3px;font-size:12px;letter-spacing:1.3px;
text-transform:uppercase;font-weight:700;cursor:pointer;}}
.bc-form-submit:hover{{filter:brightness(1.15);}}
.bc-memo-block{{background:#fff;color:#1a1a1a;border:2px dashed {wn};
border-radius:4px;padding:22px 28px;margin-top:14px;
font-family:Georgia,serif;}}
.bc-copy-btn{{display:inline-block;padding:6px 12px;background:{ac};
color:#fff;border:0;border-radius:3px;font-size:10.5px;letter-spacing:1.2px;
text-transform:uppercase;font-weight:700;cursor:pointer;margin-top:8px;
font-family:"Helvetica Neue",Arial,sans-serif;}}
.bc-copy-btn:hover{{filter:brightness(1.15);}}
""".format(
        tx=P["text"], td=P["text_dim"], tf=P["text_faint"],
        pn=P["panel"], pa=P["panel_alt"],
        bd=P["border"], ac=P["accent"],
        po=P["positive"], wn=P["warning"], ne=P["negative"],
    )
    return f"<style>{css}</style>"


# ────────────────────────────────────────────────────────────────────
# Composed blocks
# ────────────────────────────────────────────────────────────────────

_THEME_COLORS = {
    "REGULATORY": "#EF4444",
    "CREDIT": "#F59E0B",
    "OPERATIONAL": "var(--sc-navy)",
    "MARKET": "#8b5cf6",
    "STRUCTURAL": "#64748b",
    "PATTERN": "#ec4899",
}


def _verdict_card(
    report: BearCaseReport,
    run_rate_ebitda_usd: Optional[float] = None,
) -> str:
    n_crit = report.critical_count
    tone = "crit" if n_crit >= 3 else "hi" if n_crit >= 1 else "lo"
    # Frame $ at risk as % of run-rate EBITDA — only meaningful
    # when caller supplies a run-rate.  Peer bands reflect the
    # PE-IC "is this a killable thesis?" convention.
    pct_frame = ""
    peer_chip = ""
    if run_rate_ebitda_usd and run_rate_ebitda_usd > 0:
        pct_at_risk = (
            report.combined_ebitda_at_risk_usd
            / run_rate_ebitda_usd * 100
        )
        if pct_at_risk >= 25:
            pct_tone = P["negative"]
            pct_label = "IC-killable"
        elif pct_at_risk >= 10:
            pct_tone = P["warning"]
            pct_label = "material"
        elif pct_at_risk >= 3:
            pct_tone = P["warning"]
            pct_label = "watch"
        else:
            pct_tone = P["positive"]
            pct_label = "clears IC"
        pct_frame = (
            f' <span style="color:{pct_tone};font-weight:700;">'
            f'({pct_at_risk:.0f}% of run-rate — {pct_label})</span>'
        )
        peer_chip = (
            "<div style=\"margin-top:16px;\">"
            + benchmark_chip(
                value=pct_at_risk,
                peer_low=3.0, peer_high=10.0,
                higher_is_better=False,
                format_spec=".0f", suffix="%",
                label="EBITDA at risk · % of run-rate",
                peer_label="IC-critical band",
            )
            + "</div>"
        )
    return (
        f'<div class="bc-verdict-card">'
        f'<div class="bc-eyebrow">Bear Case · auto-synthesized</div>'
        f'<div class="bc-verdict-headline" style="margin-top:6px;">'
        f'{html.escape(report.headline)}</div>'
        f'<div class="bc-verdict-sub">'
        f'{html.escape(report.top_line_summary)}</div>'
        + peer_chip
        + f'<div class="bc-kpi-grid">'
        f'  <div><div class="bc-kpi__label">EBITDA at Risk</div>'
        f'       <div class="bc-kpi__val crit">'
        f'${report.combined_ebitda_at_risk_usd/1e6:,.1f}M{pct_frame}</div>'
        f'       <div style="font-size:10px;color:{P["text_faint"]};'
        f'margin-top:3px;">sum across evidence '
        f'· &lt;3% clears IC · &gt;10% material · &gt;25% killable</div></div>'
        f'  <div><div class="bc-kpi__label">Critical Items</div>'
        f'       <div class="bc-kpi__val {tone}">'
        f'{report.critical_count}</div>'
        f'       <div style="font-size:10px;color:{P["text_faint"]};'
        f'margin-top:3px;">thesis-breaking on their own</div></div>'
        f'  <div><div class="bc-kpi__label">High Items</div>'
        f'       <div class="bc-kpi__val hi">'
        f'{report.high_count}</div>'
        f'       <div style="font-size:10px;color:{P["text_faint"]};'
        f'margin-top:3px;">IC-level risks</div></div>'
        f'  <div><div class="bc-kpi__label">Medium Items</div>'
        f'       <div class="bc-kpi__val">'
        f'{report.medium_count}</div>'
        f'       <div style="font-size:10px;color:{P["text_faint"]};'
        f'margin-top:3px;">worth naming in memo</div></div>'
        f'  <div><div class="bc-kpi__label">Modules Pulled</div>'
        f'       <div class="bc-kpi__val">'
        f'{len(report.sources_active)}</div>'
        f'       <div style="font-size:10px;color:{P["text_faint"]};'
        f'margin-top:3px;">evidence sources active</div></div>'
        f'</div>'
        f'</div>'
    )


def _evidence_card(ev: Evidence) -> str:
    source_label = ev.source.value.replace("_", " ")
    impact_html = ""
    if ev.ebitda_impact_usd is not None:
        impact_html = (
            f'<span class="bc-ev-impact">'
            f'${ev.ebitda_impact_usd/1e6:+,.1f}M</span>'
        )
    meta_parts = [
        f'<strong>{html.escape(source_label)}</strong>',
    ]
    if ev.affected_year:
        meta_parts.append(f"Year {ev.affected_year}")
    if ev.metadata.get("first_kill_date"):
        meta_parts.append(
            f"Effective {ev.metadata['first_kill_date']}"
        )
    if ev.metadata.get("covenant_name"):
        meta_parts.append(
            f"{ev.metadata['covenant_name']} covenant"
        )
    if ev.metadata.get("lever_name"):
        meta_parts.append(
            f"Lever: {ev.metadata['lever_name']}"
        )
    if ev.metadata.get("failure_rate") is not None:
        meta_parts.append(
            f"{int(ev.metadata['failure_rate']*100)}% historical fail rate"
        )
    if ev.metadata.get("matched_deal"):
        meta_parts.append(
            f"Match: {ev.metadata['matched_deal']}"
        )
    link_html = (
        f'<a href="{html.escape(ev.source_link)}" '
        f'style="color:{P["accent"]};text-decoration:none;'
        f'font-size:11px;font-weight:600;">Open source →</a>'
        if ev.source_link else ""
    )
    return (
        f'<div class="bc-evidence-card bc-sev-{ev.severity.value}">'
        f'<div class="bc-ev-head">'
        f'<span class="bc-ev-citation">[{ev.citation_key}] '
        f'{ev.severity.value}</span>'
        f'<div class="bc-ev-title">{html.escape(ev.title)}</div>'
        f'{impact_html}'
        f'</div>'
        f'<div class="bc-ev-meta">'
        f'{" · ".join(meta_parts)}'
        f'</div>'
        f'<div class="bc-ev-narrative">{html.escape(ev.narrative)}</div>'
        f'<div style="margin-top:10px;">{link_html}</div>'
        f'</div>'
    )


def _evidence_by_theme(report: BearCaseReport) -> str:
    by_theme: Dict[str, List[Evidence]] = {}
    for ev in report.evidence:
        by_theme.setdefault(ev.theme.value, []).append(ev)
    theme_order = [
        "REGULATORY", "CREDIT", "OPERATIONAL",
        "MARKET", "STRUCTURAL", "PATTERN",
    ]
    blocks: List[str] = []
    for theme in theme_order:
        items = by_theme.get(theme, [])
        if not items:
            continue
        color = _THEME_COLORS.get(theme, P["text_faint"])
        narrative = report.narrative_by_theme.get(theme, "")
        cards = "".join(_evidence_card(e) for e in items)
        blocks.append(
            f'<div class="bc-theme-title" style="--sev:{color};">'
            f'{theme.title().replace("_", " ")} · '
            f'{len(items)} item{"s" if len(items) != 1 else ""}</div>'
            + (f'<div class="bc-callout" style="border-left-color:{color};">'
               f'{html.escape(narrative)}</div>'
               if narrative else "")
            + cards
        )
    return "".join(blocks)


def _ic_memo_preview(report: BearCaseReport) -> str:
    return (
        f'<div class="bc-callout" style="margin-top:0;">'
        f'<strong style="color:{P["text"]};">IC-memo drop-in: </strong>'
        f'Copy the block below into the IC memo. Every evidence item '
        f'carries a citation key (R1, C1, B1...) mapped to the '
        f'source module. Print-friendly formatting.'
        f'</div>'
        f'<div class="bc-memo-block">{report.ic_memo_html}</div>'
    )


# ────────────────────────────────────────────────────────────────────
# Landing form
# ────────────────────────────────────────────────────────────────────

def _landing(qs: Optional[Dict[str, List[str]]] = None) -> str:
    form = """
<form method="get" action="/diligence/bear-case" class="bc-wrap">
  <div class="bc-panel">
    <div class="bc-section-label" style="margin-top:0;">
      Auto-generate bear case from pipeline</div>
    <div class="bc-form-grid">
      <div class="bc-form-field"><label>Dataset fixture</label>
        <input name="dataset" value="hospital_04_mixed_payer"/></div>
      <div class="bc-form-field"><label>Deal name</label>
        <input name="deal_name" value="Meadowbrook Regional"/></div>
      <div class="bc-form-field"><label>Specialty</label>
        <input name="specialty" value="HOSPITAL"/></div>
      <div class="bc-form-field"><label>Revenue Y0 (USD)</label>
        <input name="revenue_year0_usd" value="450000000"/></div>
      <div class="bc-form-field"><label>EBITDA Y0 (USD)</label>
        <input name="ebitda_year0_usd" value="67500000"/></div>
      <div class="bc-form-field"><label>Enterprise value (USD)</label>
        <input name="enterprise_value_usd" value="600000000"/></div>
      <div class="bc-form-field"><label>Equity check (USD)</label>
        <input name="equity_check_usd" value="250000000"/></div>
      <div class="bc-form-field"><label>Debt (USD)</label>
        <input name="debt_usd" value="350000000"/></div>
      <div class="bc-form-field"><label>Medicare share (0-1)</label>
        <input name="medicare_share" value="0.45"/></div>
      <div class="bc-form-field"><label>Landlord (opt)</label>
        <input name="landlord" value="MPT"/></div>
      <div class="bc-form-field"><label>HOPD rev (USD)</label>
        <input name="hopd_revenue_annual_usd" value="45000000"/></div>
      <div class="bc-form-field"><label>HCRIS CCN (opt)</label>
        <input name="hcris_ccn" placeholder="e.g. 010001"/></div>
      <div class="bc-form-field"><label>N simulation paths</label>
        <input name="n_runs" value="250"/></div>
    </div>
    <button class="bc-form-submit" type="submit">
      Generate bear case</button>
  </div>
</form>
"""
    body = (
        _scoped_styles()
        + '<div class="bc-wrap">'
        + deal_context_bar(qs or {}, active_surface="bear")
        + '<div style="padding:22px 0 16px 0;">'
        + '<div class="bc-eyebrow">Bear Case Auto-Generator</div>'
        + '<div class="bc-h1">What could break this thesis?</div>'
        + f'<div class="bc-callout">Runs the full Thesis Pipeline '
        + 'and synthesizes the counter-narrative every IC memo '
        + 'needs: ranked evidence from Regulatory Calendar × '
        + 'Covenant Stress × Bridge Audit × Deal MC × Deal '
        + 'Autopsy × Exit Timing, with citation keys, per-theme '
        + 'narratives, and a print-ready IC-memo drop-in block. '
        + 'What partners spend 3-5 hours writing by hand, '
        + 'auto-generated in under a second.</div>'
        + '</div>'
        + form
        + '</div>'
    )
    return chartis_shell(
        body, "RCM Diligence — Bear Case Auto-Generator",
        subtitle="Evidence synthesis × 6 source modules",
    )


# ────────────────────────────────────────────────────────────────────
# Public entry
# ────────────────────────────────────────────────────────────────────

def _render_bear_case_no_ccd(
    qs: Dict[str, List[str]], deal_name: str,
) -> str:
    """Bear Case without a CCD fixture. Runs the standalone
    evidence sources (Regulatory Calendar, HCRIS X-Ray) that don't
    require claims data.  Partners with a live deal but no
    synthetic fixture still get a cited bear case."""
    def first(k: str, d: str = "") -> str:
        return (qs.get(k) or [d])[0].strip()

    def fnum(k: str) -> Optional[float]:
        v = first(k)
        if not v:
            return None
        try:
            return float(v)
        except ValueError:
            return None

    from ..diligence.bear_case import generate_bear_case
    from ..diligence.regulatory_calendar import (
        analyze_regulatory_exposure,
    )
    from ..diligence.hcris_xray import xray as hcris_xray_fn

    regulatory_exposure = None
    try:
        specialties = [first("specialty")] if first("specialty") else []
        regulatory_exposure = analyze_regulatory_exposure(
            target_profile={
                "specialties": specialties,
                "ma_mix_pct": fnum("medicare_share"),
                "revenue_usd": fnum("revenue_year0_usd"),
                "ebitda_usd": fnum("ebitda_year0_usd"),
                "has_hopd_revenue": bool(
                    fnum("hopd_revenue_annual_usd"),
                ),
                "has_reit_landlord": bool(first("landlord")),
            },
        )
    except Exception:  # noqa: BLE001
        pass

    hcris_xray = None
    ccn = first("hcris_ccn")
    if ccn:
        try:
            hcris_xray = hcris_xray_fn(ccn=ccn)
        except Exception:  # noqa: BLE001
            pass

    report = generate_bear_case(
        target_name=deal_name,
        regulatory_exposure=regulatory_exposure,
        hcris_xray=hcris_xray,
    )

    hero = (
        f'<div style="padding:22px 0 16px 0;border-bottom:1px solid '
        f'{P["border"]};margin-bottom:22px;">'
        f'<div class="bc-eyebrow">Bear Case · no CCD fixture</div>'
        f'<div class="bc-h1">{html.escape(deal_name)}</div>'
        f'<div style="font-size:11px;color:{P["text_faint"]};'
        f'margin-top:4px;">'
        f'{len(report.evidence)} evidence items · '
        f'{len(report.sources_active)} sources (no claims data) · '
        f'fast-path bear case'
        f'</div>'
        + _verdict_card(
            report,
            run_rate_ebitda_usd=fnum("ebitda_year0_usd"),
        )
        + interpret_callout(
            "How to use this:",
            "Fast-path bear case: runs only the modules that don't "
            "need a CCD claims fixture (Regulatory Calendar + HCRIS "
            "X-Ray). For the full 7-source bear case including "
            "denial prediction, physician attrition, and Deal MC, "
            "supply a dataset fixture.", tone="warn",
        )
        + f'</div>'
    )

    body = (
        _scoped_styles()
        + '<div class="bc-wrap">'
        + deal_context_bar(qs, active_surface="bear")
        + hero
        + (
            f'<div class="bc-section-label">Evidence</div>'
            + _evidence_by_theme(report)
            if report.evidence else
            f'<div class="bc-callout" '
            f'style="border-left-color:{P["positive"]};">'
            f'No bear-case evidence surfaced from the standalone '
            f'sources. Supply a dataset fixture to run the full '
            f'pipeline.</div>'
        )
        + _ic_memo_preview(report)
        + export_json_panel(
            '<div class="bc-section-label" style="margin-top:22px;">'
            'JSON export</div>',
            payload=report.to_dict(),
            name=f"bear_case_nocc_{deal_name.replace(' ', '_')}",
        )
        + bookmark_hint()
        + '</div>'
    )
    return chartis_shell(
        body, f"Bear Case (no CCD) — {deal_name}",
        subtitle=(
            f"{report.critical_count} critical · "
            f"${report.combined_ebitda_at_risk_usd/1e6:,.1f}M at risk"
        ),
    )


def render_bear_case_page(
    qs: Optional[Dict[str, List[str]]] = None,
) -> str:
    qs = qs or {}

    def first(k: str, d: str = "") -> str:
        return (qs.get(k) or [d])[0].strip()

    def fnum(k: str) -> Optional[float]:
        v = first(k)
        if not v:
            return None
        try:
            return float(v)
        except ValueError:
            return None

    def fint(k: str, default: int) -> int:
        v = first(k)
        if not v:
            return default
        try:
            return int(float(v))
        except ValueError:
            return default

    dataset = first("dataset")
    # Allow a bear case with no dataset fixture — partners with a
    # live deal but no synthetic CCD available can still get the
    # Regulatory / Covenant / Bridge / HCRIS / Autopsy evidence
    # (everything except denial prediction + physician attrition,
    # which require claims data).  Without a dataset we skip the
    # Thesis Pipeline entirely and run standalone evidence extractors.
    if not dataset and not first("deal_name") and not first("hcris_ccn"):
        return _landing(qs)

    deal_name = first("deal_name") or "Target"

    if not dataset:
        return _render_bear_case_no_ccd(qs, deal_name)

    # Build the pipeline input defensively
    from ..diligence.thesis_pipeline import (
        PipelineInput, run_thesis_pipeline,
    )
    try:
        inp = PipelineInput(
            dataset=dataset,
            deal_name=deal_name,
            specialty=first("specialty") or None,
            revenue_year0_usd=fnum("revenue_year0_usd"),
            ebitda_year0_usd=fnum("ebitda_year0_usd"),
            enterprise_value_usd=fnum("enterprise_value_usd"),
            equity_check_usd=fnum("equity_check_usd"),
            debt_usd=fnum("debt_usd"),
            medicare_share=fnum("medicare_share"),
            landlord=first("landlord") or None,
            hopd_revenue_annual_usd=fnum("hopd_revenue_annual_usd"),
            hcris_ccn=first("hcris_ccn") or None,
            n_runs=max(100, min(1000, fint("n_runs", 250))),
        )
    except Exception as exc:  # noqa: BLE001
        return chartis_shell(
            _scoped_styles()
            + f'<div class="bc-wrap" style="padding:28px;">'
            + f'<div class="bc-eyebrow">Bear Case</div>'
            + f'<div class="bc-h1" style="color:{P["negative"]};">'
            + f'Could not build pipeline input.</div>'
            + f'<div class="bc-callout">{html.escape(str(exc))}</div>'
            + f'<a href="/diligence/bear-case" '
            + f'style="color:{P["accent"]};">← Back</a></div>',
            "Bear Case",
        )

    try:
        pipeline_report = run_thesis_pipeline(inp)
    except Exception as exc:  # noqa: BLE001
        return chartis_shell(
            _scoped_styles()
            + f'<div class="bc-wrap" style="padding:28px;">'
            + f'<div class="bc-eyebrow">Bear Case</div>'
            + f'<div class="bc-h1" style="color:{P["negative"]};">'
            + f'Pipeline run failed.</div>'
            + f'<div class="bc-callout">{html.escape(str(exc))}</div>'
            + f'<a href="/diligence/bear-case" '
            + f'style="color:{P["accent"]};">← Back</a></div>',
            "Bear Case",
        )

    report = generate_bear_case_from_pipeline(
        pipeline_report, target_name=deal_name,
    )

    if not report.evidence:
        return chartis_shell(
            _scoped_styles()
            + '<div class="bc-wrap">'
            + '<div style="padding:22px 0 16px 0;">'
            + '<div class="bc-eyebrow">Bear Case Auto-Generator</div>'
            + f'<div class="bc-h1">{html.escape(deal_name)}</div>'
            + f'<div class="bc-callout" '
            + f'style="border-left-color:{P["positive"]};">'
            + f'<strong style="color:{P["text"]};">No bear-case '
            + f'evidence surfaced.</strong> Every automated source '
            + f'module (Regulatory Calendar, Covenant Stress, '
            + f'Bridge Audit, Deal MC, Autopsy) passed screening '
            + f'without flagging material thesis risk. Partners '
            + f'should still write a manual counter-narrative '
            + f'before IC — auto-screens are not a substitute '
            + f'for partner judgment.</div>'
            + '</div></div>',
            f"Bear Case — {deal_name}",
        )

    # Build the hero + body
    plain = (
        "The bear case below is auto-synthesized from every source "
        "module that fired in the Thesis Pipeline. Citation keys "
        "(R1, C1, B1, M1, A1, E1) map to the source module — click "
        "'Open source →' on any evidence card for the underlying "
        "calculation. Copy the IC-memo block at the bottom directly "
        "into the deck."
    )

    hero = (
        f'<div style="padding:22px 0 16px 0;border-bottom:1px solid '
        f'{P["border"]};margin-bottom:22px;">'
        f'<div class="bc-eyebrow">Bear Case · auto-generated</div>'
        f'<div class="bc-h1">{html.escape(deal_name)}</div>'
        f'<div style="font-size:11px;color:{P["text_faint"]};'
        f'margin-top:4px;">'
        f'{len(report.evidence)} evidence items · '
        f'{len(report.sources_active)} source modules · '
        f'synthesized in {getattr(pipeline_report, "total_compute_ms", 0):.0f}ms '
        f'pipeline runtime'
        f'</div>'
        + _verdict_card(
            report,
            run_rate_ebitda_usd=fnum("ebitda_year0_usd"),
        )
        + interpret_callout(
            "How to use this:", plain, tone="bad",
        )
        + f'</div>'
    )

    evidence_panel = (
        f'<div class="bc-section-label">'
        f'Evidence · grouped by theme, ranked by severity</div>'
        + _evidence_by_theme(report)
    )

    memo_panel = (
        f'<div class="bc-panel">'
        f'<div class="bc-section-label" style="margin-top:0;">'
        f'IC memo section · copy-paste ready</div>'
        + _ic_memo_preview(report)
        + f'</div>'
    )

    cross_links = (
        f'<div class="bc-panel">'
        f'<div class="bc-section-label" style="margin-top:0;">'
        f'Sources cited in this bear case</div>'
        f'<div style="font-size:13px;color:{P["text_dim"]};'
        f'line-height:1.7;">'
        + " · ".join(
            f'<a href="{link}" style="color:{P["accent"]};">'
            f'{label}</a>'
            for link, label in [
                ("/diligence/regulatory-calendar", "Regulatory Calendar"),
                ("/diligence/covenant-stress", "Covenant Stress"),
                ("/diligence/bridge-audit", "Bridge Audit"),
                ("/diligence/deal-mc", "Deal MC"),
                ("/diligence/deal-autopsy", "Deal Autopsy"),
                ("/diligence/exit-timing", "Exit Timing"),
            ]
        )
        + f'</div></div>'
    )

    body = (
        _scoped_styles()
        + '<div class="bc-wrap">'
        + deal_context_bar(qs, active_surface="bear")
        + hero
        + evidence_panel
        + memo_panel
        + cross_links
        + export_json_panel(
            '<div class="bc-section-label" style="margin-top:22px;">'
            'JSON export — full bear-case payload</div>',
            payload=report.to_dict(),
            name=f"bear_case_{deal_name.replace(' ', '_')}",
        )
        + bookmark_hint()
        + '</div>'
    )
    return chartis_shell(
        body, f"Bear Case — {deal_name}",
        subtitle=(
            f"{report.critical_count} critical · "
            f"${report.combined_ebitda_at_risk_usd/1e6:,.1f}M at risk"
        ),
    )
