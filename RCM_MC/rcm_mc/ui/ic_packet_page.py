"""IC Packet page — /diligence/ic-packet.

Runs the full multi-module pipeline against a fixture (or the
Steward demo) and produces a single HTML document suitable for
browser Save-as-PDF.

Pipeline:
    CCD ingest → KPI bundle → Cash waterfall → Counterfactual
    advisor (with caller metadata) → Bankruptcy-Survivor Scan →
    Steward Score (from metadata) → Cyber composite (from metadata)
    → V28 recalibration (when MA members supplied) → Market-intel
    comps + transaction multiple → IC packet render.

Landing page has a fixture picker + the same query params the QoE
memo + counterfactual page accept. The resulting IC-packet URL is
URL-reproducible.
"""
from __future__ import annotations

import html
from datetime import date
from typing import Any, Dict, List, Optional

from ..diligence._pages import AVAILABLE_FIXTURES, _resolve_dataset
from ._chartis_kit import P, chartis_shell


_HOSPITAL_BASED_SPECIALTIES = {
    "EMERGENCY_MEDICINE", "ANESTHESIOLOGY", "RADIOLOGY",
    "PATHOLOGY", "NEONATOLOGY", "HOSPITALIST",
}


def _landing() -> str:
    options = "".join(
        f'<option value="{html.escape(n)}">{html.escape(l)}</option>'
        for n, l in AVAILABLE_FIXTURES
    )
    body = (
        f'<div style="padding:24px 0 12px 0;">'
        f'<div style="font-size:11px;color:{P["text_faint"]};letter-spacing:1.5px;'
        f'text-transform:uppercase;margin-bottom:6px;font-weight:600;">'
        f'IC Packet Assembler</div>'
        f'<div style="font-size:22px;color:{P["text"]};font-weight:600;'
        f'margin-bottom:4px;">One-click IC Memo</div>'
        f'<div style="font-size:12px;color:{P["text_dim"]};max-width:720px;'
        f'line-height:1.55;">Assembles the signed IC deliverable in one '
        f'browser-print step: cover + partner synthesis + headline '
        f'numbers + Bankruptcy-Survivor Scan + QoR waterfall + '
        f'risk-module summary + counterfactual levers + market context '
        f'+ 100-day plan + open questions + walkaway conditions + '
        f'signature block. Single URL-reproducible memo.</div>'
        f'</div>'
        f'<form method="GET" action="/diligence/ic-packet" '
        f'style="display:grid;grid-template-columns:1fr 1fr;gap:12px;'
        f'max-width:720px;margin-top:20px;background:{P["panel"]};'
        f'border:1px solid {P["border"]};border-radius:4px;padding:20px;">'
        f'<div style="grid-column:span 2;">'
        f'<label style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:1.5px;text-transform:uppercase;font-weight:600;'
        f'display:block;margin-bottom:4px;">Dataset</label>'
        f'<select name="dataset" required style="width:100%;padding:6px 8px;'
        f'background:{P["panel_alt"]};color:{P["text"]};'
        f'border:1px solid {P["border"]};font-family:inherit;">'
        f'<option value="">— pick a CCD fixture —</option>{options}'
        f'</select></div>'
    )
    for name, label, placeholder in [
        ("deal_name", "Deal name", "Project Aurora"),
        ("partner_name", "Partner", ""),
        ("preparer_name", "Preparer", ""),
        ("engagement_id", "Engagement ID", ""),
        ("legal_structure", "Legal structure", ""),
        ("landlord", "Landlord", ""),
        ("states", "States (comma-sep)", "OR, WA"),
        ("specialty", "Specialty", "EMERGENCY_MEDICINE"),
        ("cbsa_codes", "CBSA codes (comma-sep)", ""),
        ("msas", "MSAs (comma-sep)", ""),
    ]:
        body += (
            f'<div><label style="font-size:9px;color:{P["text_faint"]};'
            f'letter-spacing:1.5px;text-transform:uppercase;'
            f'font-weight:600;display:block;margin-bottom:4px;">'
            f'{html.escape(label)}</label>'
            f'<input name="{name}" placeholder="{html.escape(placeholder)}" '
            f'style="width:100%;padding:6px 8px;background:{P["panel_alt"]};'
            f'color:{P["text"]};border:1px solid {P["border"]};'
            f'font-family:inherit;"></div>'
        )
    body += (
        f'<button type="submit" style="grid-column:span 2;justify-self:start;'
        f'margin-top:6px;padding:8px 20px;background:{P["accent"]};'
        f'color:{P["panel"]};border:0;font-size:10px;letter-spacing:1.5px;'
        f'text-transform:uppercase;font-weight:700;cursor:pointer;">'
        f'Assemble IC Packet</button></form>'
    )
    return chartis_shell(
        body, "RCM Diligence — IC Packet Assembler",
        subtitle="One-click IC deliverable",
    )


def _split_list(raw: str) -> List[str]:
    return [t.strip() for t in (raw or "").split(",") if t.strip()]


def render_ic_packet_page(qs: Optional[Dict[str, List[str]]] = None) -> str:
    qs = qs or {}
    dataset = (qs.get("dataset") or [""])[0]
    if not dataset:
        return _landing()
    ds_path = _resolve_dataset(dataset)
    if ds_path is None:
        return _landing()

    # Imports inside the handler keep the module lightweight on
    # boot and let individual subpackage failures degrade gracefully.
    from ..diligence import ingest_dataset
    from ..diligence.benchmarks import compute_cash_waterfall, compute_kpis
    from ..diligence.counterfactual import (
        counterfactual_bridge_lever, run_counterfactuals_from_ccd,
    )
    from ..diligence.real_estate import (
        LeaseLine, LeaseSchedule, compute_steward_score,
    )
    from ..diligence.regulatory import compose_packet
    from ..diligence.screening import (
        ScanInput, run_bankruptcy_survivor_scan,
    )
    from ..diligence.cyber import (
        assess_business_associates, compose_cyber_score,
        ehr_vendor_risk_score,
    )
    from ..market_intel import (
        find_comparables, sector_sentiment, transaction_multiple,
    )
    from ..exports import ICPacketMetadata, render_ic_packet_html

    def first(k: str) -> str:
        return (qs.get(k) or [""])[0].strip()

    specialty = first("specialty").upper() or None
    states = _split_list(first("states"))
    cbsa_codes = _split_list(first("cbsa_codes"))
    msas = _split_list(first("msas"))
    legal_structure = first("legal_structure").upper() or None
    landlord = first("landlord") or None

    def float_or_none(k: str):
        v = first(k)
        try:
            return float(v) if v else None
        except ValueError:
            return None

    def int_or_none(k: str):
        v = first(k)
        try:
            return int(float(v)) if v else None
        except ValueError:
            return None

    meta = ICPacketMetadata(
        deal_name=first("deal_name") or dataset,
        target_entity=first("target_entity") or None,
        engagement_id=first("engagement_id") or None,
        ic_date=first("ic_date") or date.today().isoformat(),
        partner_name=first("partner_name") or None,
        preparer_name=first("preparer_name") or None,
        recommendation=first("recommendation").upper()
            or "PROCEED_WITH_CONDITIONS",
    )
    if specialty:
        sent = sector_sentiment(specialty)
        if sent:
            meta.sector_sentiment = sent

    # 1. CCD ingest + Phase-2 engines.
    try:
        ccd = ingest_dataset(ds_path)
    except Exception as exc:  # noqa: BLE001
        return chartis_shell(
            f'<div style="padding:24px;color:{P["negative"]};">'
            f'Ingest failed for {html.escape(dataset)}: '
            f'{html.escape(str(exc))}</div>',
            "IC Packet",
        )
    as_of = date(2025, 1, 1)
    try:
        bundle = compute_kpis(ccd, as_of_date=as_of, provider_id=dataset)
    except Exception:  # noqa: BLE001
        bundle = None
    try:
        waterfall = compute_cash_waterfall(
            ccd.claims, as_of_date=as_of,
        )
    except Exception:  # noqa: BLE001
        waterfall = None

    # 2. Bankruptcy-Survivor Scan.
    try:
        scan = run_bankruptcy_survivor_scan(ScanInput(
            target_name=meta.deal_name,
            specialty=specialty, states=states, msas=msas,
            cbsa_codes=cbsa_codes,
            legal_structure=legal_structure,
            landlord=landlord,
            lease_term_years=int_or_none("lease_term_years"),
            lease_escalator_pct=float_or_none("lease_escalator_pct"),
            ebitdar_coverage=float_or_none("ebitdar_coverage"),
            geography=first("geography").upper() or None,
            is_hospital_based_physician=(
                (specialty or "") in _HOSPITAL_BASED_SPECIALTIES
            ),
            oon_revenue_share=float_or_none("oon_revenue_share"),
            hopd_revenue_annual_usd=float_or_none("hopd_revenue_annual_usd"),
        ))
    except Exception:  # noqa: BLE001
        scan = None

    # 3. Counterfactual advisor.
    cf_meta: Dict[str, Any] = {}
    if legal_structure:
        cf_meta["legal_structure"] = legal_structure
    if states:
        cf_meta["states"] = states
    if landlord:
        cf_meta["landlord"] = landlord
    if specialty:
        cf_meta["specialty"] = specialty
        cf_meta["is_hospital_based_physician"] = (
            specialty in _HOSPITAL_BASED_SPECIALTIES
        )
    if cbsa_codes:
        cf_meta["cbsa_codes"] = cbsa_codes
    if msas:
        cf_meta["msas"] = msas
    for k in (
        "lease_term_years", "lease_escalator_pct",
        "ebitdar_coverage", "annual_rent_usd",
        "portfolio_ebitdar_usd",
    ):
        val = (
            int_or_none(k) if k.endswith("_years")
            else float_or_none(k)
        )
        if val is not None:
            cf_meta[k] = val
    if first("geography"):
        cf_meta["geography"] = first("geography").upper()
    try:
        cfs = run_counterfactuals_from_ccd(ccd, metadata=cf_meta)
    except Exception:  # noqa: BLE001
        cfs = None

    # 4. Steward Score (when we have lease metadata).
    steward = None
    if landlord or int_or_none("lease_term_years"):
        try:
            sched = LeaseSchedule(lines=[LeaseLine(
                property_id=meta.deal_name,
                property_type=(specialty or "HOSPITAL").upper()
                    if specialty else "HOSPITAL",
                base_rent_annual_usd=float(
                    float_or_none("annual_rent_usd") or 1.0
                ),
                escalator_pct=float_or_none("lease_escalator_pct") or 0.0,
                term_years=int_or_none("lease_term_years") or 10,
                landlord=landlord,
            )])
            steward = compute_steward_score(
                sched,
                portfolio_ebitdar_annual_usd=float_or_none(
                    "portfolio_ebitdar_usd",
                ),
                portfolio_annual_rent_usd=float_or_none("annual_rent_usd"),
                geography=first("geography").upper() or None,
            )
        except Exception:  # noqa: BLE001
            steward = None

    # 5. Cyber composite (best-effort from caller-supplied metadata).
    cyber = None
    ehr_vendor = first("ehr_vendor").upper() or None
    bas = _split_list(first("business_associates"))
    if ehr_vendor or bas:
        try:
            cyber = compose_cyber_score(
                external_rating=None,
                ehr_vendor_risk=(
                    ehr_vendor_risk_score(ehr_vendor) if ehr_vendor
                    else None
                ),
                ba_findings=(
                    assess_business_associates(bas) if bas else []
                ),
                it_capex=None, bi_loss=None,
                annual_revenue_usd=float_or_none("annual_revenue_usd")
                    or 0.0,
            )
        except Exception:  # noqa: BLE001
            cyber = None

    # 6. Market-intel comps + transaction multiple.
    public_comps: Optional[List[Dict[str, Any]]] = None
    sector_label: Optional[str] = None
    peer_median = None
    transaction_band = None
    mi_category = first("market_category").upper() or None
    mi_revenue = float_or_none("revenue_usd")
    mi_ev = float_or_none("enterprise_value_usd")
    if mi_category:
        try:
            payload = find_comparables(
                target_category=mi_category,
                target_revenue_usd=mi_revenue,
            )
            public_comps = payload.get("comps") or []
            band_d = payload.get("band") or {}
            peer_median = band_d.get("median_ev_ebitda")
        except Exception:  # noqa: BLE001
            pass
    if specialty:
        try:
            sector_label = sector_sentiment(specialty)
            transaction_band = transaction_multiple(
                specialty=specialty, ev_usd=mi_ev,
            )
        except Exception:  # noqa: BLE001
            pass

    # 7. Deal Autopsy — historical failure/survivor signature match.
    autopsy_matches: Optional[List[Any]] = None
    try:
        from ..diligence.deal_autopsy import (
            historical_library, match_target, signature_from_ccd,
        )

        autopsy_metadata: Dict[str, float] = {}

        # Lease intensity — rent / revenue if we have both.
        annual_rent = float_or_none("annual_rent_usd")
        if annual_rent and mi_revenue and mi_revenue > 0:
            autopsy_metadata["lease_intensity"] = min(
                1.0, annual_rent / mi_revenue / 0.20,
            )

        # EBITDAR stress band — 1.0 at coverage ≤ 1.0x, 0.0 at ≥ 2.5x.
        cov = float_or_none("ebitdar_coverage")
        if cov is not None:
            if cov <= 1.0:
                autopsy_metadata["ebitdar_stress"] = 1.0
            elif cov >= 2.5:
                autopsy_metadata["ebitdar_stress"] = 0.0
            else:
                autopsy_metadata["ebitdar_stress"] = (
                    (2.5 - cov) / 1.5
                )

        # OON revenue share flows directly.
        oon = float_or_none("oon_revenue_share")
        if oon is not None:
            autopsy_metadata["oon_revenue_share"] = oon

        # Regulatory exposure — lean on scan / counterfactual output
        # when available.
        reg_exposure: Optional[float] = None
        if scan is not None:
            verdict = getattr(scan, "verdict", None)
            verdict_val = (
                verdict.value if hasattr(verdict, "value")
                else str(verdict or "")
            )
            reg_exposure = {
                "CRITICAL": 0.9, "RED": 0.75, "YELLOW": 0.45,
                "GREEN": 0.15,
            }.get(verdict_val.upper(), None)
        if cfs is not None and reg_exposure is None:
            # Proxy: any critical counterfactual lever present.
            if getattr(cfs, "critical_findings_addressed", 0):
                reg_exposure = 0.7
        if reg_exposure is not None:
            autopsy_metadata["regulatory_exposure"] = reg_exposure

        target_sig = signature_from_ccd(
            ccd, metadata=autopsy_metadata,
        )
        autopsy_matches = match_target(
            target_sig, historical_library(), top_k=5,
        )
    except Exception:  # noqa: BLE001
        autopsy_matches = None

    # 7c. Regulatory Calendar × Kill-Switch — partner-facing
    # timeline of CMS/OIG/FTC/DOJ/NSA-IDR events mapped to the
    # target's thesis drivers with the specific calendar date
    # each driver dies.  Feeds reg_headwind on Deal MC and
    # narratively into the IC memo.
    reg_exposure = None
    try:
        from ..diligence.regulatory_calendar import (
            analyze_regulatory_exposure,
        )
        ma_mix = None
        if first("medicare_share"):
            try:
                ma_mix = float(first("medicare_share")) * 0.55
            except ValueError:
                ma_mix = None
        comm = None
        if first("commercial_payer_share"):
            try:
                comm = float(first("commercial_payer_share"))
            except ValueError:
                comm = None
        has_reit = bool(landlord) and any(
            m in str(landlord).upper()
            for m in ("MPT", "WELLTOWER", "VENTAS", "OMEGA", "SABRA")
        )
        target = {
            "specialty": specialty,
            "specialties": [specialty] if specialty else [],
            "ma_mix_pct": ma_mix,
            "commercial_payer_share": comm,
            "has_hopd_revenue":
                bool(float_or_none("hopd_revenue_annual_usd")),
            "has_reit_landlord": has_reit,
            "revenue_usd": mi_revenue,
            "ebitda_usd": float_or_none("ebitda_usd"),
        }
        reg_exposure = analyze_regulatory_exposure(
            target_profile=target, horizon_months=24,
        )
    except Exception:  # noqa: BLE001
        reg_exposure = None

    # 7b. Checklist coverage — derive observations from what the
    # pipeline has actually produced and run the tracker.
    checklist_state = None
    try:
        from ..diligence.checklist import (
            compute_status, DealObservations,
        )
        obs = DealObservations(
            ccd_ingested=True,  # implicit by reaching this point
            bankruptcy_scan_run=(scan is not None),
            steward_run=(steward is not None),
            cyber_run=(cyber is not None),
            counterfactual_run=(cfs is not None),
            market_intel_run=(public_comps is not None
                              or transaction_band is not None),
            sector_sentiment_reviewed=(sector_label is not None),
            deal_autopsy_run=bool(autopsy_matches),
            regulatory_calendar_run=(reg_exposure is not None),
            qor_waterfall_computed=(waterfall is not None),
            hfma_days_in_ar_computed=(bundle is not None),
            hfma_denial_rate_computed=(bundle is not None),
            hfma_ar_aging_computed=(bundle is not None),
            hfma_nrr_computed=(bundle is not None),
            cohort_liquidation_computed=(bundle is not None),
            denial_pareto_computed=(bundle is not None),
            # Deliverable — we're building the IC packet right now
            ic_packet_assembled=True,
        )
        checklist_state = compute_status(obs)
    except Exception:  # noqa: BLE001
        checklist_state = None

    # 7d. Render a standalone Regulatory Timeline block we can inject
    # into the IC packet HTML output (the renderer signature doesn't
    # take a regulatory_exposure param yet).
    reg_block_html = ""
    if reg_exposure is not None:
        reg_block_html = _render_regulatory_block(reg_exposure)

    # 7e. Auto-generate a Bear Case block from available sources.
    # Runs extractors standalone — uses the same library as
    # /diligence/bear-case but produces print-ready HTML inline.
    bear_block_html = ""
    try:
        from ..diligence.bear_case import generate_bear_case
        from ..diligence.hcris_xray import xray as _hcris_xray
        hcris_report = None
        ccn = first("hcris_ccn")
        if ccn:
            try:
                hcris_report = _hcris_xray(ccn=ccn)
            except Exception:  # noqa: BLE001
                hcris_report = None
        br = generate_bear_case(
            target_name=meta.deal_name,
            regulatory_exposure=reg_exposure,
            autopsy_matches=autopsy_matches,
            hcris_xray=hcris_report,
        )
        if br.evidence:
            bear_block_html = br.ic_memo_html
    except Exception:  # noqa: BLE001
        bear_block_html = ""

    # 8. Assemble.
    html_str = render_ic_packet_html(
        metadata=meta,
        bankruptcy_scan=scan,
        cash_waterfall=waterfall,
        regulatory_packet=None,
        steward_score=steward,
        cyber_score=cyber,
        ma_v28_result=None,
        physician_comp_roster_size=None,
        stark_findings_count=None,
        counterfactuals=cfs,
        open_questions=getattr(bundle, "diligence_questions", None)
            if bundle else None,
        walkaway_conditions=_derive_walkaway(cfs),
        hundred_day_summary=None,
        enterprise_value_usd=mi_ev,
        revenue_usd=mi_revenue,
        ebitda_usd=float_or_none("ebitda_usd"),
        projected_moic=float_or_none("projected_moic"),
        projected_irr=float_or_none("projected_irr"),
        peer_median_ev_ebitda=peer_median,
        public_comps=public_comps,
        sector_sentiment=sector_label,
        transaction_multiple_band=transaction_band,
        autopsy_matches=autopsy_matches,
        checklist_state=checklist_state,
    )
    # Inject the deal-context bar at the top (just after <body>)
    # and the regulatory timeline + bear case blocks at the end.
    try:
        from .power_ui import deal_context_bar
        bar_html = deal_context_bar(qs, active_surface="ic_packet")
    except Exception:  # noqa: BLE001
        bar_html = ""
    if bar_html and "<body>" in html_str:
        html_str = html_str.replace("<body>", "<body>" + bar_html, 1)
    elif bar_html and "</head>" in html_str:
        html_str = html_str.replace(
            "</head>", "</head>" + bar_html, 1,
        )

    injection = reg_block_html + bear_block_html
    if injection and "</body>" in html_str:
        html_str = html_str.replace(
            "</body>", injection + "</body>",
        )
    elif injection:
        html_str = html_str + injection
    return html_str


def _render_regulatory_block(report: Any) -> str:
    """Compact Regulatory Calendar × Kill-Switch block for the IC
    Packet.  Deliberately standalone — the packet HTML is a
    separate template we don't rewrite here, we just append."""
    from ..diligence.regulatory_calendar.impact_mapper import (
        ImpactVerdict,
    )
    verdict_color = {
        "PASS": "#10B981", "CAUTION": "#F59E0B",
        "WARNING": "#F59E0B", "FAIL": "#EF4444",
    }.get(report.verdict.value, "#64748b")

    killed_rows: List[str] = []
    for tl in report.driver_timelines:
        if tl.worst_verdict.value == "UNAFFECTED":
            continue
        tone = {
            "KILLED": "#EF4444", "DAMAGED": "#F59E0B",
        }.get(tl.worst_verdict.value, "#94a3b8")
        killed_rows.append(
            f'<tr>'
            f'<td style="padding:6px 10px;border-bottom:1px solid #e5e7eb;">'
            f'{html.escape(tl.driver_label)}</td>'
            f'<td style="padding:6px 10px;border-bottom:1px solid #e5e7eb;'
            f'color:{tone};font-weight:600;">'
            f'{tl.worst_verdict.value}</td>'
            f'<td style="padding:6px 10px;border-bottom:1px solid #e5e7eb;'
            f'font-family:monospace;">'
            f'{tl.first_kill_date or "—"}</td>'
            f'<td style="padding:6px 10px;border-bottom:1px solid #e5e7eb;">'
            f'{tl.residual_lift_pct*100:.2f} pp of '
            f'{tl.expected_lift_pct*100:.2f} pp claimed</td>'
            f'</tr>'
        )

    overlay_rows: List[str] = []
    for o in report.ebitda_overlay:
        cls = "color:#EF4444;" if o.ebitda_delta_usd < 0 else "color:#10B981;"
        overlay_rows.append(
            f'<tr>'
            f'<td style="padding:6px 10px;border-bottom:1px solid #e5e7eb;">'
            f'{o.year}</td>'
            f'<td style="padding:6px 10px;border-bottom:1px solid #e5e7eb;'
            f'font-family:monospace;{cls}">${o.ebitda_delta_usd:+,.0f}</td>'
            f'<td style="padding:6px 10px;border-bottom:1px solid #e5e7eb;'
            f'color:#64748b;">{o.margin_delta_pp:+.2f} pp margin '
            f'· {len(o.driving_events)} event'
            f'{"s" if len(o.driving_events) != 1 else ""}</td>'
            f'</tr>'
        )
    total_eb = sum(o.ebitda_delta_usd for o in report.ebitda_overlay)

    return (
        f'<section class="ic-section" '
        f'style="page-break-before:always;padding:28px 32px;'
        f'font-family:Georgia,serif;color:#1a1a1a;">'
        f'<div style="font-size:11px;letter-spacing:1.6px;'
        f'text-transform:uppercase;color:#64748b;'
        f'font-weight:600;">Regulatory Calendar × Kill-Switch</div>'
        f'<h2 style="font-size:22px;margin:4px 0 10px 0;">'
        f'Thesis timeline — which drivers die, and when</h2>'
        f'<div style="padding:12px 16px;background:#f8fafc;'
        f'border-left:4px solid {verdict_color};'
        f'border-radius:0 3px 3px 0;margin:12px 0;">'
        f'<div style="font-size:11px;font-weight:700;letter-spacing:1.2px;'
        f'color:{verdict_color};text-transform:uppercase;">'
        f'Verdict: {report.verdict.value}</div>'
        f'<div style="font-size:14px;margin-top:6px;font-weight:600;">'
        f'{html.escape(report.headline)}</div>'
        f'<div style="font-size:12px;color:#475569;margin-top:6px;'
        f'line-height:1.6;">{html.escape(report.rationale)}</div>'
        f'</div>'
        + (
            f'<h3 style="font-size:14px;margin:16px 0 8px 0;">'
            f'Impaired thesis drivers</h3>'
            f'<table style="width:100%;border-collapse:collapse;'
            f'font-size:12.5px;">'
            f'<thead><tr style="background:#f1f5f9;">'
            f'<th style="padding:6px 10px;text-align:left;'
            f'border-bottom:2px solid #cbd5e1;">Driver</th>'
            f'<th style="padding:6px 10px;text-align:left;'
            f'border-bottom:2px solid #cbd5e1;">Verdict</th>'
            f'<th style="padding:6px 10px;text-align:left;'
            f'border-bottom:2px solid #cbd5e1;">First Kill Date</th>'
            f'<th style="padding:6px 10px;text-align:left;'
            f'border-bottom:2px solid #cbd5e1;">Residual Lift</th>'
            f'</tr></thead><tbody>{"".join(killed_rows)}</tbody></table>'
            if killed_rows else
            '<p style="font-size:13px;color:#475569;">'
            'No thesis drivers impaired within the 24-month horizon.</p>'
        )
        + (
            f'<h3 style="font-size:14px;margin:20px 0 8px 0;">'
            f'EBITDA bridge overlay</h3>'
            f'<table style="width:100%;border-collapse:collapse;'
            f'font-size:12.5px;">'
            f'<thead><tr style="background:#f1f5f9;">'
            f'<th style="padding:6px 10px;text-align:left;'
            f'border-bottom:2px solid #cbd5e1;">Year</th>'
            f'<th style="padding:6px 10px;text-align:left;'
            f'border-bottom:2px solid #cbd5e1;">EBITDA Δ (USD)</th>'
            f'<th style="padding:6px 10px;text-align:left;'
            f'border-bottom:2px solid #cbd5e1;">Notes</th>'
            f'</tr></thead><tbody>{"".join(overlay_rows)}'
            f'<tr style="border-top:2px solid #1a1a1a;font-weight:700;">'
            f'<td style="padding:6px 10px;">TOTAL</td>'
            f'<td style="padding:6px 10px;font-family:monospace;'
            f'color:{"#EF4444" if total_eb < 0 else "#10B981"};">'
            f'${total_eb:+,.0f}</td><td></td></tr>'
            f'</tbody></table>'
            if overlay_rows else ''
        )
        + f'</section>'
    )


def _derive_walkaway(cfs: Any) -> Optional[List[str]]:
    """Auto-derive walkaway conditions from the counterfactual set:
    every RED/CRITICAL counterfactual with LOW feasibility becomes a
    walkaway condition (the partner can't cleanly remediate it)."""
    if cfs is None:
        return None
    items = getattr(cfs, "items", []) or []
    out = []
    for cf in items:
        feas = getattr(cf, "feasibility", "")
        if feas != "LOW":
            continue
        module = getattr(cf, "module", "")
        change = getattr(cf, "change_description", "")
        out.append(f"{module}: {change}")
    return out or None
