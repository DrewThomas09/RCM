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
    if v is None:
        return "—"
    # House style: roll up to $B at/above a billion — a multi-hospital
    # platform's combined NPR is routinely >$1B and read better as "$10.17B"
    # than "$10,169.2M".
    return f"${v/1e9:,.2f}B" if abs(v) >= 1e9 else f"${v/1e6:,.1f}M"


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


def _demographics_panel(ccns: List[str], xf) -> str:
    """Blended (population-weighted) service-area demographics across the
    platform's home counties — the combined demand backdrop a roll-up's payer
    mix has to live with. Empty when no facility geocodes/matches."""
    try:
        from ..data.county_demographics import blended_demographics_for_ccns
        b = blended_demographics_for_ccns(ccns)
    except Exception:  # noqa: BLE001 — additive, never breaks the page
        return ""
    if not b or not b.get("counties"):
        return ""

    def _pct(v):
        return "—" if v is None else f"{float(v)*100:.1f}%"
    inc = b.get("median_household_income")
    inc_s = f"${float(inc):,.0f}" if inc else "—"
    counties = ", ".join(b["counties"][:6]) + (
        f" +{len(b['counties'])-6}" if len(b["counties"]) > 6 else "")
    inner = (
        '<div class="ck-kpi-grid">'
        + ck_kpi_block("Counties covered", f"{len(b['counties'])}",
                       sub=f"{b['covered']}/{b['n']} facilities geocoded")
        + ck_kpi_block("Blended 65+", _pct(b.get("pct_age_65_plus")),
                       sub="population-weighted · Medicare demand")
        + ck_kpi_block("Blended uninsured", _pct(b.get("uninsured_rate")),
                       sub="bad-debt / self-pay risk")
        + ck_kpi_block("Blended median income", inc_s,
                       sub="commercial-mix proxy")
        + '</div>'
        '<p class="ck-section-body" style="font-size:11px;margin:8px 0 0;'
        'color:var(--sc-text-dim,#6a7480);">Population-weighted Census/ACS '
        f'across the platform\'s home counties ({_html.escape(counties)}) — '
        'the combined service-AREA demand profile, not the platform\'s patient '
        'panel. A high blended 65+/uninsured share caps the realistic '
        'commercial mix for the combined entity.</p>')
    return xf.wrap(inner, title="Blended service-area demographics",
                   units="population-weighted county ACS",
                   source="US Census / ACS county estimates",
                   vintage="latest ACS vintage")


def _platform_composition_svg(facilities: List[Any]) -> str:
    """Anchor-or-equals: each facility's NPR share of the platform.

    One 100% strip of the combined filed NPR — answers whether the
    scenario is a true merger of equals or one anchor plus tuck-ins,
    which the facility table's absolute dollars don't show directly.
    Facilities that don't report NPR are excluded from the strip and
    counted in the caption (shares are of *reported* NPR only — no
    imputation). Fewer than two reporting facilities renders nothing.
    """
    items = [
        (str(f.ccn), str(f.name or f.ccn), float(f.npr))
        for f in facilities
        if getattr(f, "npr", None) and float(f.npr) > 0
    ]
    if len(items) < 2:
        return ""
    items.sort(key=lambda t: -t[2])
    total = sum(npr for _, _, npr in items)
    n_missing = len(facilities) - len(items)

    width, bar_h = 720, 34
    height = bar_h + 22
    tones = ("#0b2341", "#1F7A75", "#46617e", "#6e8b8a")
    segs, x = [], 0.0
    for i, (ccn, name, npr) in enumerate(items):
        share = npr / total
        w = width * share
        tone = tones[i % len(tones)]
        segs.append(
            f'<rect x="{x:.1f}" y="0" width="{max(w - 2, 1):.1f}" '
            f'height="{bar_h}" fill="{tone}" fill-opacity="0.9"/>'
        )
        if w >= 70:
            short = name.split(" ")[0][:12]
            segs.append(
                f'<text x="{x + w / 2:.1f}" y="{bar_h / 2 + 3.5}" '
                f'text-anchor="middle" font-size="10" fill="#ffffff">'
                f'{_html.escape(short)} {share * 100:.0f}%</text>'
            )
        x += w
    top_share = items[0][2] / total
    shape = (
        "ANCHOR + TUCK-INS" if top_share >= 0.5
        else "BALANCED PLATFORM" if top_share <= 0.35
        else "LEAD FACILITY + PEERS"
    )
    caption_bits = [
        f"NPR SHARE OF {len(items)} REPORTING FACILITIES",
        f"TOP FACILITY {top_share * 100:.0f}% → {shape}",
    ]
    if n_missing:
        caption_bits.append(f"{n_missing} FACILIT"
                            f"{'Y' if n_missing == 1 else 'IES'} "
                            "WITHOUT FILED NPR EXCLUDED")
    svg = (
        f'<svg viewBox="0 0 {width} {height}" width="100%" '
        f'style="max-width:{width}px;display:block;" role="img" '
        f'aria-label="Facility share of combined platform NPR">'
        + "".join(segs)
        + f'<text x="0" y="{height - 4}" font-size="9" letter-spacing="1" '
        f'fill="var(--sc-text-dim,#6a7480)">{" · ".join(caption_bits)}</text>'
        "</svg>"
    )
    return (
        '<div class="ck-rollup-composition" style="margin:0 0 12px;">'
        + svg + "</div>"
    )


def render_rollup_builder(qs: Optional[Dict[str, List[str]]] = None,
                          active_deal: Optional[Dict[str, str]] = None) -> str:
    qs = qs or {}
    raw = (qs.get("ccns") or [""])[0]
    ccns = [c.strip() for c in raw.split(",") if c.strip()][:12]
    try:
        import math
        _g = float((qs.get("ga_pct") or ["0"])[0])
        # nan slips through the clamp (min(0.30, nan) → 0.30): a non-finite
        # synergy assumption would silently become the MAX — treat as none.
        ga_pct = max(0.0, min(0.30, _g)) if math.isfinite(_g) else 0.0
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
            _platform_composition_svg(s.facilities)
            + '<div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;">'
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
        body_main = (save_block + combined + markets
                     + _demographics_panel(ccns, xf) + facilities_tbl)

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
