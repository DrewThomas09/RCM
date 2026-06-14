"""Texas infusion county & proximity workbench —
``/diligence/texas-infusion/counties``.

The referral-convenience read for an AIC platform: all 254 Texas
counties, the modeled patient → nearest-infusion-access distance, and
the demand x distance whitespace ranking. Renders straight from
``rcm_mc.diligence.texas_infusion_geo`` (every figure recomputes from
vendored public data + the documented formula — nothing is typed into
this page). CSV export at ``/diligence/texas-infusion/counties.csv``.
"""
from __future__ import annotations

import html
from typing import Any

from ._chartis_kit import (
    chartis_shell,
    ck_kpi_block,
    ck_page_title,
    ck_panel,
    ck_section_header,
    ck_source_purpose,
)

_TIER_LABEL = {
    "MULTI_SITE": "Multi-site",
    "SINGLE_SITE": "Single-site",
    "NO_IN_COUNTY": "No in-county site",
}
_TIER_COLOR = {
    "MULTI_SITE": "#0a8a5f",
    "SINGLE_SITE": "#b8732a",
    "NO_IN_COUNTY": "#b5321e",
}

_TD = ('style="padding:5px 10px;border-bottom:1px solid '
       'var(--sc-rule,#e4ddcd);font-size:12.5px;"')
_TDN = ('style="padding:5px 10px;border-bottom:1px solid '
        'var(--sc-rule,#e4ddcd);font-size:12.5px;text-align:right;'
        'font-variant-numeric:tabular-nums;font-family:var(--sc-mono);"')
_TH = ('style="padding:6px 10px;border-bottom:2px solid '
       'var(--sc-rule,#c9c1ac);font-size:10.5px;letter-spacing:.06em;'
       'text-transform:uppercase;color:var(--sc-text-dim,#465366);'
       'text-align:left;"')
_THN = _TH.replace('text-align:left', 'text-align:right')


def _tier_chip(tier: str) -> str:
    c = _TIER_COLOR.get(tier, "#8b94a0")
    return (f'<span style="display:inline-flex;align-items:center;gap:5px;">'
            f'<span style="width:8px;height:8px;border-radius:50%;'
            f'background:{c};display:inline-block;"></span>'
            f'{html.escape(_TIER_LABEL.get(tier, tier))}</span>')


def _evidence_chip(cls: str) -> str:
    color = {"REAL": "#0a8a5f", "MODELED": "#15324f",
             "DEFAULT": "#b8732a"}.get(cls, "#8b94a0")
    return (f'<span style="font-family:var(--sc-mono);font-size:9.5px;'
            f'letter-spacing:.06em;color:{color};">{html.escape(cls)}'
            '</span>')


def _county_row(r: dict[str, Any], rank: int) -> str:
    spill = " · metro spillover" if r.get("metro_spillover") else ""
    return (
        f'<tr><td {_TDN}>{rank}</td>'
        f'<td {_TD}><strong>{html.escape(r["county"])}</strong></td>'
        f'<td {_TD}>{html.escape(r["metro_class"])}</td>'
        f'<td {_TDN}>{r["population"]:,}</td>'
        f'<td {_TDN}>{r["seniors_65_plus"]:,}</td>'
        f'<td {_TDN}>{r["pct_rural"]*100:.1f}%</td>'
        f'<td {_TDN}>{r["infusion_patients"]:,}</td>'
        f'<td {_TDN}>{r["access_points"]}</td>'
        f'<td {_TD}>{_tier_chip(r["access_tier"])}'
        f'<span style="color:var(--sc-text-faint,#8b94a0);font-size:11px;">'
        f'{spill}</span></td>'
        f'<td {_TDN}>{r["expected_distance_mi"]:.1f}</td>'
        f'<td {_TD}>{_evidence_chip(r["distance_evidence"])}</td></tr>')


def _rollup_table(groups: list[dict[str, Any]], label: str) -> str:
    rows = "".join(
        f'<tr><td {_TD}>{html.escape(str(g["group"]))}</td>'
        f'<td {_TDN}>{g["counties"]}</td>'
        f'<td {_TDN}>{g["population"]:,}</td>'
        f'<td {_TDN}>{g["infusion_patients"]:,}</td>'
        f'<td {_TDN}>{g["access_points"]}</td>'
        f'<td {_TDN}>{g["weighted_distance_mi"]:.1f}</td></tr>'
        for g in groups)
    return (
        '<table style="width:100%;border-collapse:collapse;">'
        f'<thead><tr><th {_TH}>{html.escape(label)}</th>'
        f'<th {_THN}>Counties</th><th {_THN}>Population</th>'
        f'<th {_THN}>Infusion patients</th><th {_THN}>Access points</th>'
        f'<th {_THN}>Wtd distance (mi)</th></tr></thead>'
        f'<tbody>{rows}</tbody></table>')


def _methodology(s: dict[str, Any]) -> str:
    mode = s["geo_mode"]
    mode_line = (
        "<strong>gazetteer mode</strong> — cross-county distances are "
        "exact haversine from each county's Census internal point to the "
        "nearest geocoded facility." if mode == "gazetteer" else
        "<strong>model mode</strong> — the Census county-point file is "
        "not vendored, so cross-county legs use the documented spatial "
        "formula. Run <code>scripts/ingest_county_gazetteer.py</code> "
        "once (network required) to upgrade every distance to exact "
        "geometry; this page will state the switch automatically.")
    return ck_panel(
        '<div class="ck-section-body" style="font-size:13px;'
        'line-height:1.55;">'
        '<p><strong>Demand (REAL inputs, stated formula).</strong> '
        'County infusion patients = the state pool (US 3.2M patients, '
        'NHIA, scaled to Texas by Census population share) apportioned '
        '60% by the county\'s share of Texas seniors (65+, real ACS) '
        'and 40% by population share — the same split the verified '
        'metro breakdown uses.</p>'
        '<p><strong>Supply (REAL).</strong> The geocoded CMS '
        'general-acute facilities (short-term acute + critical-access '
        'by CCN convention) — every one operates outpatient infusion '
        'chairs, and they are the only infusion site of care with '
        'public locations. Freestanding AICs bill as physician offices '
        '(POS 11) and have no public census; they are the WHITESPACE '
        'this page measures, not an input. Coverage caveat: the '
        'vendored geocode file resolves 376 of ~640 CMS-listed Texas '
        'hospitals (failed geocodes dropped at ingest — e.g. Midland '
        'Memorial is absent), so supply is undercounted and distances '
        'read conservative (long).</p>'
        f'<p><strong>Distance.</strong> Currently {mode_line}</p>'
        '<p>In-county: urban share (1 - rural share, real ACS) gets '
        'half the county\'s REAL nearest-neighbor facility spacing '
        '(exact haversine); rural share gets 0.5·√(area/sites) — the '
        'standard random-placement nearest-facility result. '
        'No-in-county counties: 0.5·√(own area) plus a same-metro '
        'spillover hop where the county\'s CBSA has facilities, else '
        'a median-county (909 sq mi) hop. Land areas: Census TIGER '
        'constants for the demand-dominant and outlier counties, the '
        '909 sq mi Texas median elsewhere (the ~30-mile county '
        'platting), marked DEFAULT per row.</p>'
        '<p><strong>Sub-county granularity.</strong> The urban/rural '
        'split inside each county is the sub-county lever in the model '
        '(real ACS shares). Member-county metro drilldowns live on the '
        'main Texas Infusion page. Census-tract disease prevalence '
        '(CDC PLACES) is not vendored — '
        '<code>scripts/ingest_cdc_places.py</code> adds it when run '
        'with network access (DATA REQUIRED until then).</p>'
        '</div>',
        title="Methodology & evidence classes",
    )


def render_texas_infusion_counties_page(
        qs: dict[str, Any] | None = None) -> str:
    from ..diligence.texas_infusion_geo import (
        aic_whitespace,
        proximity_by_group,
        proximity_summary,
        tx_county_universe,
    )
    s = proximity_summary()
    rows = tx_county_universe()
    tiers = s["tiers"]

    head = ck_page_title(
        "Texas infusion · county proximity",
        eyebrow="DILIGENCE · REFERRAL CONVENIENCE",
        meta=(f"{s['counties']} COUNTIES · {s['access_points']} ACCESS "
              f"POINTS · {s['infusion_patients']:,} PATIENTS · "
              f"{s['geo_mode'].upper()} MODE"),
    )
    src = ck_source_purpose(
        purpose=("Where Texas infusion patients sit relative to the "
                 "nearest infusion access point — the convenience that "
                 "decides referrals, county by county, for AIC site "
                 "selection."),
        universe="cms", source=(
            "ACS county demographics (County Health Rankings vendored "
            "aggregate) · CMS Hospital General Information geocoded via "
            "US Census Geocoder · OMB CBSA crosswalk · NHIA demand "
            "anchors"),
        confidence="modeled",
        next_action="Open the full Texas infusion CDD",
        next_href="/diligence/texas-infusion",
    )

    kpis = (
        '<div class="ck-kpi-row" style="display:grid;grid-template-'
        'columns:repeat(4,1fr);gap:12px;margin:16px 0;">'
        + ck_kpi_block(
            "Demand-weighted distance",
            f"{s['weighted_distance_mi']:.1f} mi",
            "patient → nearest access point, statewide")
        + ck_kpi_block(
            "Patients within 10 miles",
            f"{s['pct_patients_within_10mi']:.1f}%",
            "of an in-county or metro access point")
        + ck_kpi_block(
            "No-in-county-site counties",
            f"{s['no_access_counties']}",
            f"{s['no_access_population']:,} residents · "
            f"{tiers['NO_IN_COUNTY']['infusion_patients']:,} patients")
        + ck_kpi_block(
            "No-access tier distance",
            f"{tiers['NO_IN_COUNTY']['weighted_distance_mi']:.1f} mi",
            "vs "
            f"{tiers['MULTI_SITE']['weighted_distance_mi']:.1f} mi in "
            "multi-site counties")
        + '</div>')

    tier_groups = [
        {"group": _TIER_LABEL[t], **{k: v for k, v in tiers[t].items()
                                     if k != "weighted_distance_mi"},
         "weighted_distance_mi": tiers[t]["weighted_distance_mi"],
         "access_points": sum(r["access_points"] for r in rows
                              if r["access_tier"] == t)}
        for t in ("MULTI_SITE", "SINGLE_SITE", "NO_IN_COUNTY")]
    tier_panel = ck_panel(_rollup_table(tier_groups, "Access tier"),
                          title="Access-tier rollup")

    metro_panel = ck_panel(
        _rollup_table(proximity_by_group("metro_class"), "Metro class"),
        title="Metro / micropolitan / rural rollup")
    cbsa_panel = ck_panel(
        _rollup_table(proximity_by_group("cbsa_title")[:12], "CBSA"),
        title="By metro area (top 12 by demand)")

    ws = aic_whitespace(20)
    ws_rows = "".join(
        f'<tr><td {_TDN}>{i}</td>'
        f'<td {_TD}><strong>{html.escape(w["county"])}</strong></td>'
        f'<td {_TD}>{_tier_chip(w["access_tier"])}</td>'
        f'<td {_TDN}>{w["infusion_patients"]:,}</td>'
        f'<td {_TDN}>{w["expected_distance_mi"]:.1f}</td>'
        f'<td {_TDN}>{w["patient_miles"]:,}</td>'
        f'<td {_TD}>{html.escape(w["cbsa_title"] or "—")}</td></tr>'
        for i, w in enumerate(ws, start=1))
    ws_panel = ck_panel(
        '<p class="ck-section-body" style="font-size:13px;">Patient-miles '
        '= demand x expected distance: real patient pools sitting far '
        'from the nearest access point. Multi-site metro cores rank on '
        'sheer volume (de-novo AIC pulls on convenience inside the '
        'metro); no-in-county rows are referral catchments for an '
        'adjacent-county site.</p>'
        '<table style="width:100%;border-collapse:collapse;">'
        f'<thead><tr><th {_THN}>#</th><th {_TH}>County</th>'
        f'<th {_TH}>Access</th><th {_THN}>Patients</th>'
        f'<th {_THN}>Distance (mi)</th><th {_THN}>Patient-miles</th>'
        f'<th {_TH}>CBSA</th></tr></thead>'
        f'<tbody>{ws_rows}</tbody></table>',
        title="AIC whitespace — demand x distance, top 20")

    county_rows = "".join(_county_row(r, i)
                          for i, r in enumerate(rows, start=1))
    table_panel = ck_panel(
        '<div style="display:flex;justify-content:space-between;'
        'align-items:center;margin:0 0 8px;">'
        '<span class="ck-section-body" style="font-size:12.5px;">All '
        f'{len(rows)} counties, ranked by infusion demand.</span>'
        '<a class="ck-link" href="/diligence/texas-infusion/counties.csv"'
        ' style="font-size:12px;">Download CSV</a></div>'
        '<div style="max-height:560px;overflow-y:auto;">'
        '<table style="width:100%;border-collapse:collapse;">'
        f'<thead><tr><th {_THN}>#</th><th {_TH}>County</th>'
        f'<th {_TH}>Class</th><th {_THN}>Population</th>'
        f'<th {_THN}>65+</th><th {_THN}>Rural</th>'
        f'<th {_THN}>Patients</th><th {_THN}>Sites</th>'
        f'<th {_TH}>Access</th><th {_THN}>Distance (mi)</th>'
        f'<th {_TH}>Evidence</th></tr></thead>'
        f'<tbody>{county_rows}</tbody></table></div>',
        title="County universe — all 254")

    body = (head + src + kpis
            + ck_section_header("How the distances are built")
            + _methodology(s)
            + ck_section_header("Where the patients are")
            + tier_panel + metro_panel + cbsa_panel
            + ck_section_header("The AIC referral-convenience read")
            + ws_panel
            + render_metro_deepdive_sections()
            + ck_section_header("County detail")
            + table_panel)
    return chartis_shell(
        body, "Texas infusion · county proximity",
        active_nav="/diligence/texas-infusion")


def texas_counties_csv() -> str:
    """CSV of the full county universe (Excel-safe via the shared
    defang downstream; plain values here)."""
    from ..diligence.texas_infusion_geo import tx_county_universe
    cols = ["county_fips", "county", "metro_class", "cbsa_title",
            "population", "seniors_65_plus", "pct_age_65_plus",
            "pct_rural", "uninsured_rate", "infusion_patients",
            "patients_per_100k", "access_points", "access_tier",
            "metro_spillover", "facility_nn_mi", "land_sqmi",
            "land_evidence", "expected_distance_mi", "distance_evidence"]
    out = [",".join(cols)]
    for r in tx_county_universe():
        vals = []
        for c in cols:
            v = r.get(c)
            v = "" if v is None else str(v)
            if "," in v or '"' in v:
                v = '"' + v.replace('"', '""') + '"'
            vals.append(v)
        out.append(",".join(vals))
    return "\n".join(out) + "\n"


# ── Four-metro member-county deep-dive section ──────────────────────

def _roster_line(c: dict[str, Any]) -> str:
    roster = c.get("facility_roster") or []
    if not roster:
        return ('<span style="color:var(--sc-text-faint,#8b94a0);">'
                'no in-county facility — see verdict</span>')
    shown = roster[:6]
    extra = len(roster) - len(shown)
    parts = ", ".join(
        f'{html.escape(f["name"].title())}'
        f'{" (CAH)" if f["kind"] == "CAH" else ""}'
        for f in shown)
    more = f' <span style="color:var(--sc-text-faint,#8b94a0);">+{extra} more</span>' if extra > 0 else ""
    return parts + more


def _metro_block(m: dict[str, Any]) -> str:
    head = (
        '<div style="display:flex;gap:18px;flex-wrap:wrap;margin:0 0 10px;'
        'font-family:var(--sc-mono);font-size:11px;color:'
        'var(--sc-text-dim,#465366);">'
        f'<span>{m["member_counties"]} member counties</span>'
        f'<span>{m["population"]:,} residents</span>'
        f'<span>{m["infusion_patients"]:,} infusion patients</span>'
        f'<span>{m["access_points"]} access points</span>'
        f'<span>real facility spacing {m["facility_nn_mi"]} mi</span>'
        f'<span>wtd distance {m["weighted_distance_mi"]:.1f} mi · '
        f'{m["weighted_drive_minutes"]:.1f} min</span>'
        '</div>')
    rows = []
    for c in m["counties"]:
        rows.append(
            f'<tr><td {_TD}><strong>{html.escape(c["county"])}</strong></td>'
            f'<td {_TDN}>{c["population"]:,}</td>'
            f'<td {_TDN}>{c["infusion_patients"]:,}</td>'
            f'<td {_TDN}>{c["patients_65_plus"]:,} / '
            f'{c["patients_under_65"]:,}</td>'
            f'<td {_TDN}>{c["access_points"]}</td>'
            f'<td {_TDN}>{c["expected_distance_mi"]:.1f}</td>'
            f'<td {_TDN}>{c["drive_minutes"]:.1f}</td>'
            f'<td {_TD} style="max-width:300px;">'
            f'{html.escape(c["siting_verdict"])}</td></tr>'
            f'<tr><td></td><td colspan="7" style="padding:0 10px 8px;'
            f'font-size:11px;color:var(--sc-text-dim,#465366);'
            f'border-bottom:1px solid var(--sc-rule,#e4ddcd);">'
            f'{_roster_line(c)}</td></tr>')
    table = (
        '<table style="width:100%;border-collapse:collapse;">'
        f'<thead><tr><th {_TH}>County</th><th {_THN}>Population</th>'
        f'<th {_THN}>Patients</th><th {_THN}>65+ / under-65</th>'
        f'<th {_THN}>Sites</th><th {_THN}>Distance (mi)</th>'
        f'<th {_THN}>Drive (min)</th><th {_TH}>Siting verdict</th>'
        '</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table>')
    return ck_panel(head + table,
                    title=f'{m["metro"]} — {m["cbsa_title"]}')


def _state_context_panel(ctx: dict[str, Any]) -> str:
    bits = []
    ma = ctx.get("ma")
    if ma:
        bits.append(
            f'<strong>Medicare Advantage steerage ({ma["year"]}, '
            f'{html.escape(ma["source"])}):</strong> '
            f'{ma["ma_enrollment"]:,} TX MA enrollees, avg age '
            f'{ma["avg_age"]:.0f}, {ma["female_pct"]*100:.1f}% female, '
            f'{ma["dual_eligible_pct"]*100:.1f}% dual-eligible. MA plans '
            'steer infusion to the lowest-cost site of care — the AIC '
            'tailwind.')
    pl = ctx.get("places")
    if pl:
        bits.append(
            f'<strong>Disease burden ({html.escape(pl["source"])}):</strong>'
            f' diabetes {pl["diabetes_pct"]:.1f}%, obesity '
            f'{pl["obesity_pct"]:.1f}%, fair/poor health '
            f'{pl["fair_poor_health_pct"]:.1f}%, uninsured 18-64 '
            f'{pl["uninsured_18_64_pct"]:.1f}% — state level; county/'
            'tract rates need scripts/ingest_cdc_places.py (DATA '
            'REQUIRED).')
    hp = ctx.get("hpsa")
    if hp:
        bits.append(
            f'<strong>Access shortage ({html.escape(hp["source"])}):'
            f'</strong> {hp["designated_pc_hpsas"]} designated '
            'primary-care HPSAs in Texas (median score '
            f'{hp["median_hpsa_score"]:.0f}) — referral-network gaps an '
            'AIC fills.')
    body = "".join(f'<p style="margin:0 0 8px;font-size:13px;'
                   f'line-height:1.5;">{b}</p>' for b in bits)
    return ck_panel(body or "<p>No state context vendored.</p>",
                    title="Texas payer & health context (state level, REAL)")


def render_metro_deepdive_sections() -> str:
    from ..diligence.texas_infusion_geo import (
        metro_county_deepdive,
        metro_state_context,
    )
    metros = metro_county_deepdive()
    blocks = "".join(_metro_block(m) for m in metros)
    return (
        ck_section_header("Inside the four metros — county by county",
                          eyebrow="DFW · HOUSTON · SAN ANTONIO · AUSTIN")
        + ('<p style="margin:0 0 10px;font-size:12.5px;">'
           '<a class="ck-link" '
           'href="/diligence/texas-infusion/metros.csv">Download the '
           'member-county deep-dive CSV (rosters included)</a></p>')
        + _state_context_panel(metro_state_context())
        + blocks)


def texas_metros_csv() -> str:
    """Member-county deep-dive as CSV (one row per metro county)."""
    from ..diligence.texas_infusion_geo import metro_county_deepdive
    cols = ["metro", "county_fips", "county", "population",
            "seniors_65_plus", "pct_rural", "uninsured_rate",
            "median_household_income", "infusion_patients",
            "patients_65_plus", "patients_under_65", "access_points",
            "access_tier", "metro_spillover", "facility_nn_mi",
            "expected_distance_mi", "drive_minutes", "patient_miles",
            "siting_verdict", "facility_names"]
    out = [",".join(cols)]
    for m in metro_county_deepdive():
        for c in m["counties"]:
            row = dict(c, metro=m["metro"], facility_names="; ".join(
                f["name"] for f in c.get("facility_roster", [])))
            vals = []
            for col in cols:
                v = row.get(col)
                v = "" if v is None else str(v)
                if "," in v or '"' in v:
                    v = '"' + v.replace('"', '""') + '"'
                vals.append(v)
            out.append(",".join(vals))
    return "\n".join(out) + "\n"
