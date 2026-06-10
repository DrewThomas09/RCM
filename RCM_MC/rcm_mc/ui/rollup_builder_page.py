"""Roll-Up Scenario Builder page — /pipeline/rollup.

Pro-forma combination of N real HCRIS facilities (rcm_mc.pe.rollup_scenario):
filed facility figures (ACTUAL), arithmetic combined column (DERIVED),
day-weighted payer blend, state share + HHI before/after with the 2023
Merger-Guidelines screening note, and an explicitly USER-ASSUMPTION synergy
line that only renders when the cost base is fully covered. CSV export.
"""
from __future__ import annotations

import html as _html
from typing import Dict, List, Optional
from urllib.parse import urlencode

from ..data.hcris import _get_latest_per_ccn
from ..pe.rollup_scenario import (
    RollupScenario, antitrust_note, build_scenario, scenario_csv,
)
from ._chartis_kit import (
    ExhibitFactory, chartis_shell, ck_basis_badge, ck_kpi_block,
    ck_page_title, ck_panel, ck_source_link,
)


def _fmt_m(v: Optional[float]) -> str:
    return "—" if v is None else f"${v/1e6:,.1f}M"


def _fmt_i(v: Optional[float]) -> str:
    return "—" if v is None else f"{v:,.0f}"


def _fmt_p(v: Optional[float]) -> str:
    return "—" if v is None else f"{v*100:,.1f}%"


def _cov(agg) -> str:
    if agg.complete:
        return ""
    return (f' <span style="color:var(--sc-warning,#b8732a);font-size:10px;" '
            f'title="Only {agg.covered} of {agg.n} selected facilities report '
            f'this field — the combined figure covers those filings only.">'
            f'({agg.covered}/{agg.n})</span>')


def render_rollup_builder(qs: Optional[Dict[str, List[str]]] = None,
                          active_deal: Optional[Dict[str, str]] = None) -> str:
    qs = qs or {}
    raw = (qs.get("ccns") or [""])[0]
    ccns = [c.strip() for c in raw.split(",") if c.strip()][:12]
    try:
        ga_pct = max(0.0, min(0.30, float((qs.get("ga_pct") or ["0"])[0])))
    except ValueError:
        ga_pct = 0.0
    fmt = (qs.get("format") or [""])[0]
    prefill_deal = (qs.get("_prefill_deal") or [""])[0].strip()

    scenario: Optional[RollupScenario] = None
    if len(ccns) >= 2:
        scenario = build_scenario(_get_latest_per_ccn(), ccns)
        if not scenario.facilities:
            scenario = None

    if scenario is not None and fmt == "csv":
        return scenario_csv(scenario)

    _inp = ('style="padding:5px 8px;border:1px solid var(--sc-rule,#c9c1ac);'
            'width:340px;font-variant-numeric:tabular-nums;"')
    prefill_note = (
        '<p class="ck-section-body" style="margin:0 0 10px;font-size:11px;'
        'color:var(--sc-teal,#155752);">Seeded with your active deal '
        f'<strong>{_html.escape(prefill_deal)}</strong> as the platform '
        'anchor — add the CCNs you\'d combine with it.</p>'
        ) if prefill_deal else ""
    form = ck_panel(
        prefill_note +
        '<form method="get" action="/pipeline/rollup" '
        'style="display:flex;gap:12px;align-items:end;flex-wrap:wrap;">'
        '<label style="font-family:var(--sc-mono);font-size:10px;display:block;">'
        'CCNs to combine (comma-separated, 2–12)'
        f'<input name="ccns" value="{_html.escape(raw)}" '
        f'placeholder="450076, 450068, 450358" {_inp}></label>'
        '<label style="font-family:var(--sc-mono);font-size:10px;display:block;">'
        'G&amp;A synergy (% of combined opex, 0–30) — your assumption'
        f'<input name="ga_pct" value="{ga_pct if ga_pct else ""}" '
        'style="padding:5px 8px;border:1px solid var(--sc-rule,#c9c1ac);width:80px;"></label>'
        '<button type="submit" class="tsw-vert" style="cursor:pointer;'
        'padding:7px 14px;">Build scenario</button></form>'
        '<p class="ck-section-body" style="font-size:11px;margin:10px 0 0;'
        'color:var(--sc-text-dim,#6a7480);">Pick facilities from the '
        '<a class="ck-link" href="/target-screener?vertical=hospitals">Target '
        'Screener</a> (the compare basket builds a CCN list), then combine '
        'them here. All facility figures are filed HCRIS values.</p>',
        title="Select facilities")

    if scenario is None:
        body_main = ck_panel(
            '<p class="ck-section-body">Enter at least two CCNs to build a '
            'pro-forma platform: combined volumes, revenue, day-weighted '
            'payer blend, and state share / HHI before vs after — with the '
            'Merger-Guidelines screening note where it applies.</p>',
            title="How this works")
    else:
        s = scenario
        # Exhibit chrome (P5): the pro-forma KPIs and the concentration
        # table are the two blocks a deal team lifts into a deck, so they
        # render as numbered, sourced exhibits — print-to-PDF ready.
        xf = ExhibitFactory(
            deal_label=f"{len(s.facilities)}-facility roll-up",
            source_default=ck_source_link("CMS HCRIS"))
        # facility table — filed values
        frows = ""
        for f in s.facilities:
            frows += (
                '<tr>'
                f'<td style="padding:5px 8px;"><a class="ck-link" '
                f'href="/diligence/hcris-xray?ccn={_html.escape(f.ccn)}">'
                f'{_html.escape(f.ccn)}</a></td>'
                f'<td style="padding:5px 8px;">{_html.escape(f.name[:42])}</td>'
                f'<td style="padding:5px 8px;">{_html.escape(f.state)}</td>'
                f'<td class="num" style="padding:5px 8px;text-align:right;">{_fmt_i(f.beds)}</td>'
                f'<td class="num" style="padding:5px 8px;text-align:right;">{_fmt_i(f.inpatient_days)}</td>'
                f'<td class="num" style="padding:5px 8px;text-align:right;">{_fmt_m(f.npr)}</td>'
                f'<td class="num" style="padding:5px 8px;text-align:right;">{_fmt_p(f.medicare_day_pct)}</td>'
                f'<td class="num" style="padding:5px 8px;text-align:right;">{_fmt_p(f.medicaid_day_pct)}</td>'
                '</tr>')
        syn = s.synergy_ebitda(ga_pct) if ga_pct else None
        syn_row = ""
        if ga_pct:
            if syn is None:
                syn_row = (
                    '<p class="ck-section-body" style="font-size:11px;'
                    'color:var(--sc-warning,#b8732a);margin:8px 0 0;">Synergy '
                    'not computed: operating expenses are not reported by all '
                    'selected facilities — a synergy on a partially-known cost '
                    'base would be fabrication.</p>')
            else:
                syn_row = (
                    '<p class="ck-section-body" style="font-size:11.5px;margin:8px 0 0;">'
                    f'G&amp;A synergy at {ga_pct:.0%} of combined opex'
                    f'{ck_basis_badge("entered")}: '
                    f'<strong>{_fmt_m(syn)}/yr</strong> — your assumption, not '
                    'a modeled or filed figure.</p>')

        combined = xf.wrap(
            '<div class="ck-kpi-grid">'
            + ck_kpi_block("Facilities", f"{len(s.facilities)}")
            + ck_kpi_block("Combined beds", _fmt_i(s.beds.value) + _cov(s.beds))
            + ck_kpi_block("Combined inpatient days",
                           _fmt_i(s.inpatient_days.value) + _cov(s.inpatient_days))
            + ck_kpi_block("Combined NPR (filed)",
                           _fmt_m(s.npr.value) + _cov(s.npr))
            + ck_kpi_block("Blended Medicare days",
                           _fmt_p(s.blended_medicare_pct),
                           sub=f"day-weighted · {s.payer_mix_covered}/{len(s.facilities)} report the split")
            + ck_kpi_block("Blended Medicaid days",
                           _fmt_p(s.blended_medicaid_pct),
                           sub=f"day-weighted · {s.payer_mix_covered}/{len(s.facilities)} report the split")
            + '</div>'
            '<p class="ck-section-body" style="font-size:11px;margin:8px 0 0;'
            'color:var(--sc-text-dim,#6a7480);">Combined figures are '
            'arithmetic on the facilities\' filed HCRIS values '
            f'{ck_basis_badge("actual")} — source {ck_source_link("CMS HCRIS")}.'
            '</p>' + syn_row,
            title="Pro-forma platform — combined filed figures",
            units="NPR in USD; payer mix as % of inpatient days",
            vintage="latest HCRIS filing per CCN")

        mkts = ""
        for m in s.markets:
            note = antitrust_note(m)
            zone = ("var(--sc-warning,#b8732a)"
                    if ("attention" in note or "presumption zone" in note)
                    else "var(--sc-text-dim,#6a7480)")
            mkts += (
                f'<tr><td style="padding:6px 8px;">{_html.escape(m.state)}</td>'
                f'<td class="num" style="padding:6px 8px;text-align:right;">{m.n_market}</td>'
                f'<td class="num" style="padding:6px 8px;text-align:right;">{m.share_after:.1%}</td>'
                f'<td class="num" style="padding:6px 8px;text-align:right;">{m.hhi_before:,.0f}</td>'
                f'<td class="num" style="padding:6px 8px;text-align:right;">{m.hhi_after:,.0f}</td>'
                f'<td class="num" style="padding:6px 8px;text-align:right;">{m.hhi_delta:+,.0f}</td>'
                f'<td style="padding:6px 8px;font-size:11px;color:{zone};">{_html.escape(note)}</td></tr>')
        notes_html = "".join(
            f'<p class="ck-section-body" style="font-size:11px;margin:6px 0 0;'
            f'color:var(--sc-warning,#b8732a);">{_html.escape(n)}</p>'
            for n in s.notes)
        export_qs = urlencode({"ccns": ",".join(ccns), "ga_pct": ga_pct or "",
                               "format": "csv"})
        markets = xf.wrap(
            '<div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;">'
            '<thead><tr style="border-bottom:2px solid var(--sc-rule,#c9c1ac);">'
            '<th style="text-align:left;padding:6px 8px;">Market (state proxy)</th>'
            '<th style="text-align:right;padding:6px 8px;">Hospitals</th>'
            '<th style="text-align:right;padding:6px 8px;">Combined share (NPR)</th>'
            '<th style="text-align:right;padding:6px 8px;">HHI before</th>'
            '<th style="text-align:right;padding:6px 8px;">HHI after</th>'
            '<th style="text-align:right;padding:6px 8px;">Δ</th>'
            '<th style="text-align:left;padding:6px 8px;">Screening note</th>'
            f'</tr></thead><tbody>{mkts}</tbody></table></div>'
            + notes_html +
            '<p class="ck-section-body" style="font-size:11px;margin:10px 0 0;'
            'color:var(--sc-text-dim,#6a7480);">State NPR shares are a '
            'screening proxy, not a relevant-market analysis; thresholds per '
            'the 2023 DOJ/FTC Merger Guidelines §2.1. '
            f'<a class="ck-link" href="/pipeline/rollup?{export_qs}">Scenario CSV ↓</a></p>',
            title="Market concentration — before vs after",
            units="share of state NPR (%); HHI in points (0–10,000)",
            vintage="latest HCRIS filing per CCN")

        facilities_tbl = ck_panel(
            '<div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;">'
            '<thead><tr style="border-bottom:2px solid var(--sc-rule,#c9c1ac);">'
            '<th style="text-align:left;padding:5px 8px;">CCN</th>'
            '<th style="text-align:left;padding:5px 8px;">Facility</th>'
            '<th style="text-align:left;padding:5px 8px;">State</th>'
            '<th style="text-align:right;padding:5px 8px;">Beds</th>'
            '<th style="text-align:right;padding:5px 8px;">Inpatient days</th>'
            '<th style="text-align:right;padding:5px 8px;">NPR (filed)</th>'
            '<th style="text-align:right;padding:5px 8px;">Medicare days</th>'
            '<th style="text-align:right;padding:5px 8px;">Medicaid days</th>'
            f'</tr></thead><tbody>{frows}</tbody></table></div>',
            title="Selected facilities — filed values")

        # Persist-to-deal (backlog #17): a built scenario can be recorded on
        # the ACTIVE deal as a sourced note (visible on the deal page, in
        # notes search, deletable like any note). Only offered when a deal
        # context exists — there is nothing honest to attach it to otherwise.
        save_block = ""
        if active_deal and active_deal.get("id"):
            if (qs.get("saved_note") or [""])[0] == "1":
                save_block = (
                    '<p class="ck-section-body" style="font-size:11.5px;margin:0 0 14px;'
                    'color:var(--sc-positive,#0a8a5f);">Scenario saved to '
                    f'<a class="ck-link" href="/deal/{_html.escape(active_deal["id"])}">'
                    f'{_html.escape(active_deal.get("name") or active_deal["id"])}</a> '
                    'as a note — it lists the facilities, combined figures and a '
                    'link back to this exact scenario.</p>')
            else:
                save_block = (
                    '<form method="post" action="/api/rollup/save-to-deal" '
                    'style="margin:0 0 14px;">'
                    f'<input type="hidden" name="ccns" value="{_html.escape(",".join(ccns))}">'
                    f'<input type="hidden" name="ga_pct" value="{ga_pct or ""}">'
                    f'<input type="hidden" name="deal_id" value="{_html.escape(active_deal["id"])}">'
                    '<button type="submit" class="tsw-vert" style="cursor:pointer;'
                    'padding:6px 12px;">Save scenario to '
                    f'{_html.escape(active_deal.get("name") or active_deal["id"])}</button>'
                    '<span style="font-family:var(--sc-mono);font-size:9.5px;'
                    'color:var(--sc-text-dim,#6a7480);margin-left:8px;">records a '
                    'note on the deal with these facilities + figures</span></form>')
        body_main = save_block + combined + markets + facilities_tbl

    body = (
        ck_page_title(
            "Roll-Up Scenario Builder",
            eyebrow="PIPELINE · PRO-FORMA PLATFORM",
            meta="Combine real HCRIS facilities into a platform view: "
                 "volumes, revenue, payer blend, share and HHI before/after.")
        + form + body_main)
    return chartis_shell(body, "Roll-Up Builder",
                         active_nav="/pipeline/rollup",
                         subtitle="Pro-forma combination of real facilities")
