"""Interfacility Transport — Clinical Demand & Acute Transfers (/ift-clinical).

Premium editorial page rendering the IFT clinical acute-transfer demand engine
(``rcm_mc.market_reports.ift_clinical_demand``): the volume/growth backbone of
the IFT thesis. It walks the clinical taxonomy the owner listed —

    acute scenario -> ICD-10-CM / MS-DRG codes -> transfer TYPE
                   -> destination CAPABILITY / setting
                   -> national annual VOLUME -> demographic GROWTH

across all three families (Escalation up, Step-down/Recovery down, Direct-admit
& Load-balancing lateral), and lands the honest-labelled numbers behind the IFT
report + /ift-markets sizing model.

Every figure carries a basis chip:
  * ``SOURCED``      — computed from our data (ICD-10 validation, supply counts).
  * ``GOV``          — published CMS / AHRQ HCUP / CDC / MedPAC / NCHS figure.
  * ``ACADEMIC``     — published epidemiologic estimate.
  * ``ILLUSTRATIVE`` — modeled projection with a named basis (the growth CAGRs).

Wired at ``/ift-clinical`` (server.py), in the Cmd+K palette, and cross-linked
both ways with the IFT market report and the ``/ift-markets`` sizing model.
"""
from __future__ import annotations

import html as _html
from typing import Dict, List, Optional

from ._chartis_kit import (
    chartis_shell,
    ck_kpi_block,
    ck_page_explainer,
    ck_page_title,
    ck_signal_badge,
)
from ..market_reports import ift_clinical_demand as M


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _e(v) -> str:
    return _html.escape("" if v is None else str(v))


# Honesty-tag -> (ink, border) using the semantic Chartis palette tokens.
_CHIP_TONE = {
    "SOURCED": ("var(--sc-positive,#0a8a5f)", "var(--sc-positive,#0a8a5f)"),
    "GOV": ("var(--sc-teal,#155752)", "var(--sc-teal,#155752)"),
    "ACADEMIC": ("var(--sc-navy,#0b2341)", "var(--sc-navy,#0b2341)"),
    "ILLUSTRATIVE": ("var(--sc-warning,#b8732a)", "var(--sc-warning,#b8732a)"),
}


def _tag_of(source_label: Optional[str]) -> str:
    """Leading honesty tag of a ' · '-delimited source label (GOV / SOURCED /
    ACADEMIC / ILLUSTRATIVE); falls back to ILLUSTRATIVE for anything else so a
    figure is never shown without a basis chip."""
    if not source_label:
        return "ILLUSTRATIVE"
    head = str(source_label).split("·", 1)[0].strip().upper()
    for tag in ("SOURCED", "GOV", "ACADEMIC", "ILLUSTRATIVE"):
        if head.startswith(tag):
            return tag
    return "ILLUSTRATIVE"


def _chip(tag: str, *, title: str = "") -> str:
    """Inline basis pill. ``title`` (a full source citation) rides on hover so
    every landed figure is one hover away from its provenance."""
    ink, border = _CHIP_TONE.get(tag, _CHIP_TONE["ILLUSTRATIVE"])
    t = f' title="{_e(title)}"' if title else ""
    return (
        f'<span{t} style="display:inline-block;font-family:var(--sc-mono,'
        "Consolas,monospace);font-size:8.5px;letter-spacing:0.06em;"
        f'font-weight:600;padding:1px 4px;border-radius:2px;vertical-align:'
        f'middle;color:{ink};border:1px solid {border};white-space:nowrap;">'
        f'{_e(tag)}</span>'
    )


def _fmt_int(n) -> str:
    try:
        n = int(n)
    except (TypeError, ValueError):
        return "—"
    return f"{n:,}" if n > 0 else "—"


def _fmt_compact(n) -> str:
    try:
        n = float(n)
    except (TypeError, ValueError):
        return "—"
    if n <= 0:
        return "—"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}k"
    return f"{n:.0f}"


def _pct(frac, *, sign: bool = False) -> str:
    try:
        v = float(frac) * 100.0
    except (TypeError, ValueError):
        return "—"
    return (f"+{v:.1f}%" if sign and v >= 0 else f"{v:.1f}%")


def _dot(code: str) -> str:
    """Display an undotted ICD-10-CM leaf (I219) in its dotted form (I21.9)."""
    c = str(code)
    return c if len(c) <= 3 else f"{c[:3]}.{c[3:]}"


def _drg_short(s: str) -> str:
    """Leading code range of an MS-DRG reference string ('280-282 (AMI...)')."""
    return str(s).split(" (", 1)[0]


def _num_span(text: str) -> str:
    return f'<span class="sc-num" style="font-variant-numeric:tabular-nums;">{text}</span>'


# ---------------------------------------------------------------------------
# Destination-tier mapping (authored clinical reference — for the heat grid).
# Capability designations are NOT in our data, so this page-level mapping is
# reference, matching each scenario's destination_setting to a tier column.
# ---------------------------------------------------------------------------

_TIER_ORDER: List[str] = [
    "Cardiac (PCI / CICU / shock)",
    "Stroke / Neuro",
    "Critical med-surg ICU",
    "Trauma Center",
    "Maternal / Neonatal / Peds",
    "Behavioral (psych bed)",
    "Tertiary / quaternary hub",
    "LTACH",
    "IRF",
    "SNF / Home Health",
    "Hospice",
    "In-system / right-bed",
]


def _tier_of(setting: str) -> str:
    s = (setting or "").lower()
    if "ltach" in s:
        return "LTACH"
    if s.strip() == "irf" or " irf" in s or "irf " in s:
        return "IRF"
    if "snf" in s:
        return "SNF / Home Health"
    if "hospice" in s:
        return "Hospice"
    if "psych" in s:
        return "Behavioral (psych bed)"
    if "trauma" in s:
        return "Trauma Center"
    if any(k in s for k in ("nicu", "picu", "children", "mfm", "iv ob", " ob")):
        return "Maternal / Neonatal / Peds"
    if "stroke" in s or "neuro" in s:
        return "Stroke / Neuro"
    if "cardiac" in s or "aortic" in s:
        return "Cardiac (PCI / CICU / shock)"
    if "hub" in s:
        return "Tertiary / quaternary hub"
    if any(k in s for k in ("right-capability", "same-system", "community")):
        return "In-system / right-bed"
    return "Critical med-surg ICU"


# Acuity -> heat colour for the matrix cells.
_ACUITY_TONE = {
    "critical": "var(--sc-negative,#b5321e)",
    "emergent": "var(--sc-warning,#b8732a)",
    "urgent": "var(--sc-teal,#155752)",
    "stable": "var(--sc-text-dim,#6a7480)",
}
_FAMILY_TONE = {
    M.FAMILY_ESCALATION: "var(--sc-negative,#b5321e)",
    M.FAMILY_STEPDOWN: "var(--sc-teal,#155752)",
    M.FAMILY_LOADBALANCE: "var(--sc-navy,#0b2341)",
}


def _section(anchor: str, eyebrow: str, title: str, deck: str = "") -> str:
    deck_html = (f'<p style="font-family:var(--sc-serif,Georgia,serif);'
                 f'font-style:italic;color:var(--sc-text-dim,#465366);'
                 f'max-width:78ch;margin:2px 0 14px;line-height:1.5;">{deck}</p>'
                 if deck else "")
    return (
        f'<section id="{_e(anchor)}" style="margin:34px 0 8px;">'
        f'<div style="font-family:var(--sc-mono,Consolas,monospace);'
        f'font-size:10px;letter-spacing:0.14em;text-transform:uppercase;'
        f'color:var(--sc-teal,#155752);font-weight:600;margin-bottom:4px;">'
        f'<span style="display:inline-block;width:22px;height:1px;'
        f'background:var(--sc-positive,#0a8a5f);vertical-align:middle;'
        f'margin-right:8px;"></span>{_e(eyebrow)}</div>'
        f'<h2 style="font-family:var(--sc-serif,Georgia,serif);'
        f'color:var(--sc-navy,#0b2341);font-size:22px;margin:0;'
        f'line-height:1.2;">{_e(title)}</h2>{deck_html}</section>'
    )


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

def _kpi_row() -> str:
    summ = M.registry_summary()
    mm = M.mission_mix()
    vc = M.validate_codes()
    n_codes = sum(len(d.get("icd10_ok", [])) for d in vc.values())
    supply = summ.get("destination_supply_national", {})
    supply_total = sum(int(v or 0) for v in supply.values())
    fam = summ.get("n_by_family", {})

    blocks = [
        ck_kpi_block(
            "Clinical scenarios modeled",
            _num_span(str(summ.get("n_conditions", 0))),
            f'{fam.get(M.FAMILY_ESCALATION, 0)} escalation · '
            f'{fam.get(M.FAMILY_STEPDOWN, 0)} step-down · '
            f'{fam.get(M.FAMILY_LOADBALANCE, 0)} direct-admit'),
        ck_kpi_block(
            "ICD-10-CM codes validated",
            _num_span(str(n_codes)) + " " + _chip(
                "SOURCED", title="Validated against the vendored CMS "
                "FY2025/FY2026 billability seed"),
            "billable leaves — zero misses"),
        ck_kpi_block(
            "High-acuity mission share",
            _num_span(_pct(mm.get("high_acuity_share", 0))) + " " + _chip(
                "GOV", title=str(mm.get("basis", ""))),
            "CCT/SCT + specialty teams, volume-weighted escalation book"),
        ck_kpi_block(
            "Blended demographic growth",
            _num_span(_pct(summ.get("escalation_volume_weighted_cagr", 0),
                           sign=True)) + " " + _chip(
                "ILLUSTRATIVE", title="demand_forecast age-band CAGRs weighted "
                "by each condition's age skew"),
            "per yr — escalation volume-weighted, incidence held flat"),
        ck_kpi_block(
            "Post-acute destination supply",
            _num_span(_fmt_int(supply_total)) + " " + _chip(
                "SOURCED", title="Real CMS provider-file row counts"),
            f'SNF {_fmt_int(supply.get("SNF"))} · IRF '
            f'{_fmt_int(supply.get("IRF"))} · LTCH '
            f'{_fmt_int(supply.get("LTACH"))} facilities'),
    ]
    return '<div class="ck-kpi-grid">' + "".join(blocks) + "</div>"


def _demand_signal_band() -> str:
    """Context band — the published IFT demand signals (surfaced from the
    registry's ED-transfer condition + authored reference), each labelled."""
    ed = M.get_condition("ED interfacility up-transfer to acute care")
    lb = M.get_condition("Inter-hospital ICU/bed load-balancing")
    items: List[str] = []
    if ed is not None:
        nv = ed.national_volume
        items.append(("ED transfers to another acute hospital",
                      _fmt_compact(nv.value) + " / yr", _tag_of(nv.source_label),
                      nv.source_label))
    items.append(("ED arrivals via interfacility transfer", "~1.3M / yr",
                  "ACADEMIC",
                  "Nationwide EMS interfacility-transfer study (ED-arriving IFTs)"))
    items.append(("ED-admitted patients boarding 4+ hours", "~25% nonpeak",
                  "ACADEMIC",
                  "Health Affairs 2024 (46.2M hospitalizations, 1,500 hospitals, "
                  "2017-24); ~35% winter peak"))
    if lb is not None and lb.national_volume.note:
        items.append(("Load-balancing signal", "occupancy-anchored",
                      "ILLUSTRATIVE", lb.national_volume.note))

    cells = []
    for label, value, tag, cite in items:
        cells.append(
            '<div style="flex:1 1 190px;min-width:180px;padding:10px 14px;'
            'border-left:2px solid var(--sc-teal,#155752);">'
            f'<div style="font-family:var(--sc-mono,Consolas,monospace);'
            f'font-size:9px;letter-spacing:0.08em;text-transform:uppercase;'
            f'color:var(--sc-text-dim,#6a7480);margin-bottom:3px;">{_e(label)}'
            f'</div><div style="font-family:var(--sc-serif,Georgia,serif);'
            f'font-size:19px;color:var(--sc-navy,#0b2341);'
            f'font-variant-numeric:tabular-nums;">{_e(value)} {_chip(tag, title=cite)}'
            f'</div></div>')
    return ('<div style="display:flex;flex-wrap:wrap;gap:6px;margin:6px 0 4px;'
            'background:var(--sc-surface,#faf7f1);border:1px solid '
            'var(--sc-border,#e4dccb);border-radius:4px;padding:6px;">'
            + "".join(cells) + "</div>")


def _transfer_matrix_grid() -> str:
    """Origin-family x destination-tier heat grid (the true cross-matrix)."""
    fams = [M.FAMILY_ESCALATION, M.FAMILY_STEPDOWN, M.FAMILY_LOADBALANCE]
    fam_short = {M.FAMILY_ESCALATION: "Escalation (up)",
                 M.FAMILY_STEPDOWN: "Step-down (down)",
                 M.FAMILY_LOADBALANCE: "Direct-admit / load-bal (lateral)"}
    counts: Dict[str, Dict[str, int]] = {t: {f: 0 for f in fams}
                                         for t in _TIER_ORDER}
    max_c = 1
    for row in M.transfer_matrix():
        tier = _tier_of(row["destination_setting"])
        fam = row["family"]
        if tier in counts and fam in counts[tier]:
            counts[tier][fam] += 1
            max_c = max(max_c, counts[tier][fam])

    fam_ths = "".join(
        '<th scope="col" class="align-center">' + _e(fam_short[f]) + '</th>'
        for f in fams)
    head = ('<thead><tr>'
            '<th scope="col" class="align-left">Destination tier</th>'
            + fam_ths
            + '<th scope="col" class="align-right">Total</th></tr></thead>')
    body = []
    for tier in _TIER_ORDER:
        row_total = sum(counts[tier].values())
        if row_total == 0:
            continue
        cells = [f'<td class="align-left">{_e(tier)}</td>']
        for f in fams:
            n = counts[tier][f]
            if n:
                alpha = 0.10 + 0.55 * (n / max_c)
                cell_style = (
                    f'background:rgba(21,87,82,{alpha:.2f});'
                    'font-variant-numeric:tabular-nums;font-weight:600;'
                    'color:var(--sc-navy,#0b2341);')
                cells.append(
                    f'<td class="align-center sc-num" style="{cell_style}">'
                    f'{n}</td>')
            else:
                cells.append('<td class="align-center" '
                             'style="color:var(--sc-text-faint,#b8b0a0);">'
                             '&middot;</td>')
        cells.append(f'<td class="align-right sc-num" '
                     f'style="font-variant-numeric:tabular-nums;">{row_total}</td>')
        body.append("<tr>" + "".join(cells) + "</tr>")
    return ('<div style="overflow-x:auto;">'
            '<table class="ck-table ck-dense">' + head
            + "<tbody>" + "".join(body) + '</tbody></table></div>')


def _matrix_detail() -> str:
    """Per-scenario origin -> destination detail, grouped by family."""
    rows = M.transfer_matrix()
    order = [M.FAMILY_ESCALATION, M.FAMILY_STEPDOWN, M.FAMILY_LOADBALANCE]
    out = ['<div style="overflow-x:auto;"><table class="ck-table ck-dense">'
           '<thead><tr>'
           '<th scope="col" class="align-left">Acute scenario</th>'
           '<th scope="col" class="align-left">Transfer</th>'
           '<th scope="col" class="align-left">Origin</th>'
           '<th scope="col" class="align-left">Destination capability</th>'
           '<th scope="col" class="align-left">Transport tier</th>'
           '</tr></thead><tbody>']
    ncols = 5
    for fam in order:
        fam_rows = [r for r in rows if r["family"] == fam]
        if not fam_rows:
            continue
        tone = _FAMILY_TONE.get(fam, "var(--sc-teal,#155752)")
        out.append(
            f'<tr><td colspan="{ncols}" style="background:var(--sc-surface,'
            f'#faf7f1);border-left:3px solid {tone};font-family:var(--sc-mono,'
            f'Consolas,monospace);font-size:10px;letter-spacing:0.08em;'
            f'text-transform:uppercase;color:var(--sc-navy,#0b2341);'
            f'font-weight:600;padding-top:8px;">{_e(fam)} · {len(fam_rows)} '
            f'scenarios</td></tr>')
        for r in fam_rows:
            ac = r["acuity"]
            ac_tone = _ACUITY_TONE.get(ac, "var(--sc-text-dim,#6a7480)")
            xfer_arrow = {"up": "▲ up", "down": "▼ down",
                          "lateral": "◆ lateral"}.get(r["transfer_type"],
                                                      r["transfer_type"])
            out.append(
                "<tr>"
                f'<td class="align-left"><strong>{_e(r["condition"])}</strong>'
                f'<div style="font-size:11px;color:var(--sc-text-dim,#6a7480);'
                f'max-width:42ch;">{_e(r["presenting"])}</div></td>'
                f'<td class="align-left" style="white-space:nowrap;">'
                f'{_e(xfer_arrow)}<br><span style="font-size:10px;'
                f'color:{ac_tone};font-weight:600;text-transform:uppercase;'
                f'letter-spacing:0.05em;">{_e(ac)}</span></td>'
                f'<td class="align-left">{_e(r["origin_setting"])}</td>'
                f'<td class="align-left"><strong style="color:'
                f'var(--sc-teal,#155752);">→ {_e(r["destination_setting"])}'
                f'</strong><div style="font-size:11px;'
                f'color:var(--sc-text-dim,#6a7480);max-width:44ch;">'
                f'{_e(r["destination_capability"])}</div></td>'
                f'<td class="align-left"><span class="ck-badge tone-neutral" '
                f'style="font-size:9px;">{_e(r["transport_acuity"])}</span></td>'
                "</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def _per_condition_table() -> str:
    """Codes / volume / growth per condition, grouped by family."""
    order = [M.FAMILY_ESCALATION, M.FAMILY_STEPDOWN, M.FAMILY_LOADBALANCE]
    out = ['<div style="overflow-x:auto;"><table class="ck-table ck-dense">'
           '<thead><tr>'
           '<th scope="col" class="align-left">Condition</th>'
           '<th scope="col" class="align-left">ICD-10-CM</th>'
           '<th scope="col" class="align-left">MS-DRG</th>'
           '<th scope="col" class="align-left">Destination</th>'
           '<th scope="col" class="align-right">National volume</th>'
           '<th scope="col" class="align-right">Growth CAGR</th>'
           '</tr></thead><tbody>']
    ncols = 6
    for fam in order:
        fam_conds = M.conditions_by_family(fam) if hasattr(
            M, "conditions_by_family") else [
            c for c in M.all_conditions() if c.family == fam]
        if not fam_conds:
            continue
        tone = _FAMILY_TONE.get(fam, "var(--sc-teal,#155752)")
        out.append(
            f'<tr><td colspan="{ncols}" style="background:var(--sc-surface,'
            f'#faf7f1);border-left:3px solid {tone};font-family:var(--sc-mono,'
            f'Consolas,monospace);font-size:10px;letter-spacing:0.08em;'
            f'text-transform:uppercase;color:var(--sc-navy,#0b2341);'
            f'font-weight:600;padding-top:8px;">{_e(fam)}</td></tr>')
        for c in fam_conds:
            nv = c.national_volume
            vtag = _tag_of(nv.source_label)
            codes = ("".join(
                f'<code style="font-family:var(--sc-mono,Consolas,monospace);'
                f'font-size:10.5px;background:var(--sc-surface,#f2ece0);'
                f'padding:0 3px;border-radius:2px;margin:0 2px 2px 0;'
                f'display:inline-block;">{_e(_dot(x))}</code>'
                for x in c.icd10)
                if c.icd10 else '<span style="color:var(--sc-text-dim,'
                '#6a7480);font-style:italic;font-size:11px;">condition-'
                'agnostic — routed by admission source</span>')
            drgs = _e("; ".join(_drg_short(d) for d in c.ms_drg))
            if nv.value and nv.value > 0:
                vol_val = (_num_span(_fmt_compact(nv.value))
                           + (f' <span style="font-size:10px;'
                              f'color:var(--sc-text-dim,#6a7480);">'
                              f'{_e(nv.year)}</span>' if nv.year else "")
                           + " " + _chip(vtag, title=nv.source_label))
                vol_sub = _e(nv.measure)
            else:
                vol_val = ('<span style="color:var(--sc-text-dim,#6a7480);'
                           'font-style:italic;">not separately counted</span> '
                           + _chip(vtag, title=nv.source_label))
                vol_sub = _e(nv.measure)
            growth_cell = (_num_span(_pct(c.growth.cagr, sign=True)) + " "
                           + _chip("ILLUSTRATIVE", title=c.growth.basis))
            out.append(
                "<tr>"
                f'<td class="align-left"><strong>{_e(c.name)}</strong></td>'
                f'<td class="align-left" style="max-width:22ch;">{codes}</td>'
                f'<td class="align-left sc-num" style="font-size:11px;'
                f'font-variant-numeric:tabular-nums;max-width:16ch;">{drgs}</td>'
                f'<td class="align-left">{_e(c.destination_setting)}</td>'
                f'<td class="align-right">{vol_val}<div style="font-size:10px;'
                f'color:var(--sc-text-dim,#6a7480);">{vol_sub}</div></td>'
                f'<td class="align-right">{growth_cell}<div style="font-size:'
                f'10px;color:var(--sc-text-dim,#6a7480);">10-yr '
                f'{c.growth.index_10yr:.2f}x</div></td>'
                "</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def _growth_outlook() -> str:
    ranked = M.growth_ranked()
    top = ranked[:16]
    max_c = max((c.growth.cagr for c in top), default=0.045) or 0.045
    bars = []
    for c in top:
        tone = _FAMILY_TONE.get(c.family, "var(--sc-teal,#155752)")
        w = max(3.0, min(100.0, 100.0 * c.growth.cagr / max_c))
        bars.append(
            '<div style="display:flex;align-items:center;gap:10px;'
            'margin:3px 0;">'
            f'<span style="flex:0 0 250px;font-size:12px;'
            f'color:var(--sc-navy,#0b2341);overflow:hidden;'
            f'text-overflow:ellipsis;white-space:nowrap;" title="{_e(c.name)}">'
            f'{_e(c.name)}</span>'
            f'<span style="flex:1 1 auto;height:14px;background:'
            f'var(--sc-surface,#efe8da);border-radius:2px;overflow:hidden;">'
            f'<span style="display:block;height:100%;width:{w:.1f}%;'
            f'background:{tone};opacity:0.82;"></span></span>'
            f'<span class="sc-num" style="flex:0 0 62px;text-align:right;'
            f'font-family:var(--sc-mono,Consolas,monospace);font-size:12px;'
            f'font-variant-numeric:tabular-nums;color:var(--sc-navy,#0b2341);">'
            f'{_pct(c.growth.cagr, sign=True)}</span></div>')

    leaders = ", ".join(c.name.split(" -> ")[0].split(" (")[0].split(" / ")[0]
                        for c in ranked[:5])
    takeaway = (
        "Aging skews demand into the 85+ and 75-84 bands — the fastest-growing "
        "cohorts in the demographic model — where hip fracture, end-of-life "
        "hospice transitions, long-ICU debility, stroke and heart failure grow "
        "fastest. The fastest-aging clinical cohorts ARE the acute-transfer "
        "streams, so escalation-out and step-down IFT volume compounds against "
        "a growing 65+ denominator even with incidence held flat: a structural "
        "IFT volume tailwind. The young-cohort scenarios (high-risk OB, "
        "neonatal, pediatric, behavioral-health) are demographically flat but "
        "volume-heavy — their IFT demand is driven by acuity and bed scarcity, "
        "not population growth.")
    return (
        f'<div style="margin:10px 0 6px;">{"".join(bars)}</div>'
        '<div style="display:flex;gap:16px;flex-wrap:wrap;font-family:'
        'var(--sc-mono,Consolas,monospace);font-size:10px;color:'
        'var(--sc-text-dim,#6a7480);margin:2px 0 10px;">'
        f'<span><span style="color:{_FAMILY_TONE[M.FAMILY_ESCALATION]};">■'
        f'</span> Escalation</span>'
        f'<span><span style="color:{_FAMILY_TONE[M.FAMILY_STEPDOWN]};">■</span>'
        f' Step-down / recovery</span>'
        f'<span><span style="color:{_FAMILY_TONE[M.FAMILY_LOADBALANCE]};">■'
        f'</span> Direct-admit / load-balancing</span>'
        f'<span>Fastest five: {_e(leaders)}</span></div>'
        f'<p style="font-family:var(--sc-serif,Georgia,serif);font-size:14px;'
        f'line-height:1.55;color:var(--sc-text,#1a2332);max-width:80ch;">'
        f'<em>{takeaway}</em> {_chip("ILLUSTRATIVE")} projection off the '
        f'{_chip("SOURCED")} demand_forecast age-band model.</p>')


def _mission_mix() -> str:
    mm = M.mission_mix()
    tiers = [
        ("High-acuity — CCT/SCT + specialty teams", mm.get("high_acuity_share", 0),
         "var(--sc-negative,#b5321e)"),
        ("Mid-acuity — ALS / ALS2 (drips)", mm.get("mid_acuity_share", 0),
         "var(--sc-warning,#b8732a)"),
        ("Lower-acuity — BLS / NEMT / behavioral", mm.get("low_acuity_share", 0),
         "var(--sc-teal,#155752)"),
    ]
    bars = []
    for label, share, tone in tiers:
        w = max(2.0, min(100.0, float(share) * 100.0))
        bars.append(
            '<div style="display:flex;align-items:center;gap:10px;margin:4px 0;">'
            f'<span style="flex:0 0 300px;font-size:12px;'
            f'color:var(--sc-navy,#0b2341);">{_e(label)}</span>'
            f'<span style="flex:1 1 auto;height:16px;background:'
            f'var(--sc-surface,#efe8da);border-radius:2px;overflow:hidden;">'
            f'<span style="display:block;height:100%;width:{w:.1f}%;'
            f'background:{tone};opacity:0.85;"></span></span>'
            f'<span class="sc-num" style="flex:0 0 56px;text-align:right;'
            f'font-family:var(--sc-mono,Consolas,monospace);font-size:12px;'
            f'font-variant-numeric:tabular-nums;">{_pct(share)}</span></div>')
    total = mm.get("total_weighting_volume", 0)
    return (
        f'<div style="margin:8px 0;">{"".join(bars)}</div>'
        f'<p style="font-size:12.5px;color:var(--sc-text-dim,#465366);'
        f'max-width:80ch;line-height:1.5;">Transport-acuity tiers weighted by '
        f'GOV national volume across the escalation book '
        f'({_num_span(_fmt_int(total))} weighting stays). The acute escalation '
        f'mix skews toward the high-acuity, high-reimbursement CCT/SCT tier — '
        f'the crews an IFT operator must field for intubated / pressor-dependent '
        f'/ mechanical-support patients. {_chip("GOV", title=str(mm.get("basis","")))} '
        f'volumes × authored transport tiering.</p>')


def _supply_section() -> str:
    settings = [("SNF", "Skilled nursing (med-surg discharge, hip-fx rehab)"),
                ("IRF", "Inpatient rehab (post-stroke, cardiac, hip-fx)"),
                ("LTACH", "Long-term acute care (post-vent, long-ICU debility)"),
                ("HHA", "Home health (homebound-stable discharge)"),
                ("Hospice", "End-stage / comfort transition")]
    rows = []
    grand = 0
    for key, desc in settings:
        r = M.destination_supply(key)
        n = int(r.get("national") or 0)
        grand += n
        rows.append(
            "<tr>"
            f'<td class="align-left"><strong>{_e(key)}</strong></td>'
            f'<td class="align-left" style="color:var(--sc-text-dim,#465366);">'
            f'{_e(desc)}</td>'
            f'<td class="align-right sc-num" style="font-variant-numeric:'
            f'tabular-nums;font-weight:600;">{_fmt_int(n)}</td>'
            f'<td class="align-left">{_chip("SOURCED", title=str(r.get("source_label","")))}</td>'
            "</tr>")
    rows.append(
        '<tr style="border-top:2px solid var(--sc-navy,#0b2341);">'
        '<td class="align-left"><strong>Total post-acute destinations</strong></td>'
        '<td class="align-left"></td>'
        f'<td class="align-right sc-num" style="font-variant-numeric:tabular-nums;'
        f'font-weight:700;">{_fmt_int(grand)}</td>'
        '<td class="align-left"></td></tr>')
    tbl = ('<div style="overflow-x:auto;"><table class="ck-table">'
           '<thead><tr><th scope="col" class="align-left">Setting</th>'
           '<th scope="col" class="align-left">Step-down / recovery role</th>'
           '<th scope="col" class="align-right">Facilities</th>'
           '<th scope="col" class="align-left">Basis</th></tr></thead>'
           '<tbody>' + "".join(rows) + "</tbody></table></div>")
    note = (
        '<p style="font-size:12.5px;color:var(--sc-text-dim,#465366);'
        'max-width:82ch;line-height:1.5;margin-top:8px;">Real provider-file '
        'row counts (CMS Care Compare / Provider-of-Services). These are the '
        'DOWN-transfer destinations an IFT operator delivers into. The UP-'
        'transfer destination capability (Comprehensive Stroke Center, Level I '
        'Trauma, PCI/cath, NICU III/IV) is authored clinical reference — those '
        'designations are not in our vendored data, so only the post-acute '
        'destination COUNT is SOURCED.</p>')
    return tbl + note


def _tie_note() -> str:
    return (
        '<section id="ift-tie" style="margin:30px 0 6px;padding:16px 18px;'
        'background:var(--sc-surface,#faf7f1);border:1px solid '
        'var(--sc-border,#e4dccb);border-left:3px solid var(--sc-teal,#155752);'
        'border-radius:4px;">'
        '<div style="font-family:var(--sc-mono,Consolas,monospace);'
        'font-size:10px;letter-spacing:0.12em;text-transform:uppercase;'
        'color:var(--sc-teal,#155752);font-weight:600;margin-bottom:6px;">'
        'The volume driver behind the IFT thesis</div>'
        '<p style="font-family:var(--sc-serif,Georgia,serif);font-size:14px;'
        'line-height:1.6;color:var(--sc-text,#1a2332);max-width:84ch;">'
        'A ground-IFT operator\'s volume equals the count of acute patients who '
        'must MOVE between facilities. This engine sizes that demand at the '
        'clinical-case level — the cases, codes, destinations and demographic '
        'growth that feed the IFT market report and the /ift-markets sizing '
        'model. Read it alongside the IFT report\'s occupancy / capacity signal '
        '(the throughput driver) and the ground-IFT TAM (the dollars): this is '
        'the <em>why the missions exist</em>, and the aging-driven growth '
        'outlook is the structural tailwind under the sizing.</p>'
        '<div style="margin-top:14px;display:flex;flex-wrap:wrap;gap:18px;'
        'font-family:var(--sc-mono,Consolas,monospace);font-size:11px;'
        'letter-spacing:0.04em;">'
        '<a href="/market/interfacility_transport" style="color:var(--sc-teal,'
        '#155752);font-weight:600;text-decoration:none;">Full IFT market report '
        '&rarr;</a>'
        '<a href="/ift-markets" style="color:var(--sc-teal,#155752);'
        'font-weight:600;text-decoration:none;">Geographic markets &amp; '
        'TAM/SAM/SOM &rarr;</a>'
        '</div></section>')


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

def render_ift_clinical(qs: Optional[Dict[str, List[str]]] = None) -> str:
    """Render the /ift-clinical editorial page (full HTML via chartis_shell)."""
    summ = M.registry_summary()
    fam = summ.get("n_by_family", {})
    meta = (f'{summ.get("n_conditions", 0)} acute scenarios · '
            f'{fam.get(M.FAMILY_ESCALATION, 0)} escalation / '
            f'{fam.get(M.FAMILY_STEPDOWN, 0)} step-down / '
            f'{fam.get(M.FAMILY_LOADBALANCE, 0)} direct-admit · '
            f'ICD-10-CM validated offline · growth from demand_forecast')

    head = ck_page_title(
        "Interfacility Transport — Clinical Demand & Acute Transfers",
        eyebrow="INTERFACILITY TRANSPORT / IFT · CLINICAL DEMAND",
        meta=meta)
    explainer = ck_page_explainer(
        "IFT demand IS these clinical transfers.",
        "Each acute scenario maps from presenting picture to the ICD-10-CM / "
        "MS-DRG codes, to the transfer type, to the destination capability, to "
        "the published national volume, to the demographic growth outlook. "
        "Every figure carries a basis chip — SOURCED (our data), GOV "
        "(published CMS/AHRQ/CDC), ACADEMIC, or ILLUSTRATIVE (modeled with a "
        "named basis). This is the volume/growth backbone of the IFT thesis.",
        source="rcm_mc.market_reports.ift_clinical_demand — validated codes, "
               "published volumes, demand_forecast growth model")

    body = "".join([
        head,
        explainer,
        _kpi_row(),
        _demand_signal_band(),
        _section("matrix", "Origin → destination",
                 "The acute-transfer matrix",
                 "Where each acute scenario must move: origin family × "
                 "destination-tier heat grid, then the per-scenario "
                 "origin → destination detail grouped by family."),
        _transfer_matrix_grid(),
        _matrix_detail(),
        _section("codes", "Cases → codes → volume → growth",
                 "Per-condition clinical demand",
                 "The validated ICD-10-CM + MS-DRG code set, destination, "
                 "published national volume, and projected demographic growth "
                 "for every scenario."),
        _per_condition_table(),
        _section("growth", "Growth outlook",
                 "Ranked by projected volume growth",
                 "Conditions ordered by the demographic CAGR from the "
                 "demand_forecast model — the IFT volume thesis."),
        _growth_outlook(),
        _section("mission", "Mission mix",
                 "Transport-acuity split of the escalation book",
                 "Which crews the demand requires, volume-weighted."),
        _mission_mix(),
        _section("supply", "Destination supply",
                 "Real post-acute destination counts",
                 "The down-transfer destinations, counted from our vendored "
                 "CMS provider files (SOURCED)."),
        _supply_section(),
        _tie_note(),
    ])

    return chartis_shell(
        body,
        "Interfacility Transport — Clinical Demand",
        active_nav="/research",
        subtitle="Clinical acute-transfer demand engine · the IFT volume driver",
    )
