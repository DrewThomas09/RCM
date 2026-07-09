"""IFT health-system demand page (``/ift-hs-demand``).

Sizes IFT demand the buyer's way: off the LARGER health systems' hospital
throughput (HCRIS discharges), SNF dropped, broken down county by county — plus
the demand-data inventory (what we have, what's ingest-ready, what to source).

Reads :mod:`ift_hs_demand`. Renders through ``chartis_shell`` + ``ck_*``;
degrades to honest notes and never raises.

Public API:
    render_ift_hs_demand(qs=None) -> str
"""
from __future__ import annotations

import html as _html
from typing import Dict, List, Optional

from ._chartis_kit import (
    chartis_shell, ck_next_section, ck_page_actions, ck_page_title, ck_panel,
    ck_section_header, ck_section_intro,
)
from ._chart_kit import ck_chart_assets, ck_chart_grid, ck_hbar_chart
from ..market_reports import ift_hs_demand as _hd


def _esc(x: object) -> str:
    return _html.escape(str(x if x is not None else ""))


_BASIS_TITLES = {
    "SOURCED": "Computed from our vendored CMS estate (HCRIS / provider rolls).",
    "CONNECTOR": "A registered connector dataset — ingest-ready, honest fallback.",
    "GOV": "A published government figure / rule.",
    "ACADEMIC": "A published study / analyst series to source.",
    "ILLUSTRATIVE": "Modeled — the basis is named, not a filed figure.",
}
_BASIS_CLASS = {"SOURCED": "sourced", "CONNECTOR": "connector", "GOV": "gov",
                "ACADEMIC": "academic", "ILLUSTRATIVE": "illustrative"}


def _chip(basis: str) -> str:
    b = (basis or "ILLUSTRATIVE").upper()
    key = b if b in _BASIS_TITLES else "ILLUSTRATIVE"
    return (f'<span class="ihd-chip ihd-chip-{_BASIS_CLASS[key]}" '
            f'title="{_esc(_BASIS_TITLES[key])}">{key}</span>')


def _status_badge(status: str) -> str:
    m = {"live": ("ihd-live", "LIVE"),
         "ingest-ready": ("ihd-ready", "INGEST-READY"),
         "to-source": ("ihd-tosrc", "TO SOURCE")}
    cls, lab = m.get(status, ("ihd-tosrc", status.upper()))
    return f'<span class="ihd-st {cls}">{_esc(lab)}</span>'


def _num(x, dash="—") -> str:
    try:
        return f"{int(round(float(x))):,}"
    except (TypeError, ValueError):
        return dash


def _usd_m(x) -> str:
    try:
        return f"${float(x) / 1e6:,.2f}M"
    except (TypeError, ValueError):
        return "—"


def _pct(x) -> str:
    try:
        return f"{float(x) * 100:.1f}%"
    except (TypeError, ValueError):
        return "—"


def _kpi(label, value, sub) -> str:
    return ('<div class="ihd-kpi"><div class="ihd-kpi-l">' + _esc(label)
            + f'</div><div class="ihd-kpi-v">{value}</div>'
            f'<div class="ihd-kpi-s">{_esc(sub)}</div></div>')


def _table(headers, rows) -> str:
    head = "".join(f"<th>{_esc(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>"
                   for r in rows)
    return ('<div class="ihd-wrap"><table class="ihd-tab"><thead><tr>'
            f'{head}</tr></thead><tbody>{body}</tbody></table></div>')


_STYLES = """<style>
.ihd-chip{display:inline-block;font-family:var(--sc-mono,Consolas,monospace);
font-size:9px;font-weight:600;letter-spacing:.06em;padding:1px 6px;border-radius:2px;
vertical-align:middle;margin:0 1px;}
.ihd-chip-sourced{background:#e7efe9;color:#154e36;}
.ihd-chip-connector{background:#eef1f5;color:#31465e;border:1px solid #cdd6e2;}
.ihd-chip-gov{background:#e7efe9;color:#154e36;}
.ihd-chip-academic{background:#efeae0;color:#6b5426;}
.ihd-chip-illustrative{background:#f3ecd9;color:#7a5c1a;}
.ihd-st{display:inline-block;font-family:var(--sc-mono,Consolas,monospace);font-size:8.5px;
font-weight:700;letter-spacing:.04em;padding:1px 6px;border-radius:9px;}
.ihd-live{background:#e7efe9;color:#154e36;}
.ihd-ready{background:#eef1f5;color:#31465e;}
.ihd-tosrc{background:#f5ece0;color:#8a5a1a;}
.ihd-prose{font-family:var(--sc-serif,Georgia,serif);font-size:14px;line-height:1.62;
color:var(--sc-text,#1a2332);max-width:92ch;margin:0 0 10px;}
.ihd-sub{font-family:var(--sc-mono,Consolas,monospace);font-size:11px;font-weight:600;
letter-spacing:.06em;text-transform:uppercase;color:var(--sc-teal,#155752);margin:14px 0 6px;}
.ihd-src{font-family:var(--sc-mono,Consolas,monospace);font-size:10px;
color:var(--sc-muted,#6b6357);margin:6px 0 2px;line-height:1.5;}
.ihd-kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
gap:12px;margin:10px 0 6px;}
.ihd-kpi{background:#fff;border:1px solid var(--sc-border,#e4dccb);border-radius:4px;
padding:11px 13px;}
.ihd-kpi-l{font-family:var(--sc-sans,Inter,system-ui,sans-serif);font-size:10px;
font-weight:600;letter-spacing:.05em;text-transform:uppercase;
color:var(--sc-muted,#6b6357);margin-bottom:4px;}
.ihd-kpi-v{font-family:var(--sc-mono,Consolas,monospace);font-size:19px;font-weight:700;
color:var(--sc-navy,#0b2341);font-variant-numeric:tabular-nums;line-height:1.15;}
.ihd-kpi-s{font-size:10.5px;color:var(--sc-muted,#6b6357);margin-top:3px;}
.ihd-wrap{overflow-x:auto;margin:5px 0 10px;}
.ihd-tab{border-collapse:collapse;width:100%;font-size:12px;
font-family:var(--sc-sans,Inter,system-ui,sans-serif);}
.ihd-tab th,.ihd-tab td{border:1px solid var(--sc-border,#e4dccb);padding:6px 9px;
text-align:left;vertical-align:top;line-height:1.42;}
.ihd-tab thead th{background:var(--sc-navy,#0b2341);color:#fff;font-weight:600;
font-size:10.5px;position:sticky;top:0;}
.ihd-tab tbody tr:nth-child(even){background:var(--sc-surface,#faf7f1);}
.ihd-method{border:1px solid var(--sc-border,#e4dccb);border-left:3px solid
var(--sc-teal,#155752);border-radius:6px;background:var(--sc-surface,#faf7f1);
padding:14px 16px;margin:8px 0 14px;}
.ihd-method code{font-family:var(--sc-mono,Consolas,monospace);font-size:12px;
background:#fff;border:1px solid var(--sc-border,#e4dccb);border-radius:3px;
padding:2px 6px;color:var(--sc-navy,#0b2341);}
.ihd-links{display:flex;flex-wrap:wrap;gap:14px;margin:14px 0 4px;
font-family:var(--sc-mono,Consolas,monospace);font-size:11px;font-weight:600;}
.ihd-links a{color:var(--sc-teal,#155752);text-decoration:none;}
.ihd-drop{border-left:3px solid var(--sc-warning,#b8732a);
background:rgba(184,115,42,0.06);padding:8px 12px;margin:8px 0;font-size:12.5px;
line-height:1.5;color:var(--sc-text,#1a2332);}
.ihd-drop b{font-family:var(--sc-mono,Consolas,monospace);font-size:9.5px;
letter-spacing:.06em;text-transform:uppercase;color:var(--sc-warning,#b8732a);}
</style>"""


def _download_bar() -> str:
    """The prominent demand-workbook download — the whole demand side, volume-first,
    as one sourced .xlsx (separate from the market-study pack)."""
    return (
        '<div style="display:flex;flex-wrap:wrap;gap:12px;align-items:center;'
        'justify-content:space-between;margin:18px 0 6px;padding:14px 18px;'
        'border:1px solid var(--sc-teal,#155752);border-radius:4px;'
        'background:rgba(21,87,82,0.05);">'
        '<div style="font-size:13.5px;max-width:70ch;">'
        '<strong>Demand data pack (Excel).</strong> The whole demand side in one '
        'download, volume-first: transports a year (GOV-anchored), by acuity and '
        'emergency split, demand by condition year over year, and the health-system '
        '/ regional / county views — every figure sourced.</div>'
        '<a href="/api/ift/demand.xlsx" download '
        'style="flex:none;font-family:var(--sc-mono,Consolas,monospace);'
        'font-size:12px;font-weight:600;letter-spacing:0.04em;text-decoration:none;'
        'color:#fff;background:var(--sc-teal,#155752);padding:9px 16px;'
        'border-radius:3px;">Download demand Excel &darr;</a></div>')


def _crosslinks() -> str:
    return (
        '<div class="ihd-links">'
        '<a href="/ift-demand">Demand deep-dive (national→subcounty) &rarr;</a>'
        '<a href="/ift-clinical">Clinical demand engine &rarr;</a>'
        '<a href="/ift-mmt">MMT county deep-dive &rarr;</a>'
        '<a href="/ift-markets">Geographic markets / TAM-SAM-SOM &rarr;</a>'
        '<a href="/ift-sourcing">Sourcing prompts &rarr;</a>'
        '<a href="/connector-estate">Live data-connector estate &rarr;</a>'
        '</div>')


def _method_section() -> str:
    return (
        ck_section_header("How we size it — the buyer's throughput, not the SNF",
                          eyebrow="THE METHOD")
        + ck_panel(
            '<p class="ihd-prose">The buyer is the <strong>health system</strong>, '
            'and its IFT demand is derived off its hospitals\' throughput. We size '
            'it off <strong>Hospital Cost Reports (HCRIS)</strong>, not off the '
            'destination facilities.</p>'
            '<div class="ihd-method">'
            '<p class="ihd-prose" style="margin:0 0 6px;"><strong>Driver.</strong> '
            'Acute discharges ≈ <code>HCRIS patient_days ÷ ALOS</code> per hospital '
            + _chip("SOURCED") + ' — with a labelled '
            '<code>hospital_count × ~7,300 discharges/hospital/yr</code> fallback '
            + _chip("ILLUSTRATIVE") + ' when the HCRIS panel is not ingested, so '
            'the build is never zero.</p>'
            '<p class="ihd-prose" style="margin:0 0 6px;"><strong>Legs.</strong> '
            '<code>IFT legs = discharges × f_IFT</code> (stretcher-eligible '
            'discharge + up-transfer add, ~7-12%), then <code>× s(m)</code> '
            'serviceable share and <code>× r_IFT</code> ($600 realized) for '
            'dollars.</p>'
            '<p class="ihd-prose" style="margin:0;"><strong>Payer &amp; acuity.</strong> '
            'HCRIS Medicare/Medicaid day-share gives the reimbursement blend; '
            'case-mix drives the BLS/ALS/SCT split.</p>'
            '</div>'
            '<div class="ihd-drop"><b>SNF is not the buyer</b> — a skilled-nursing '
            'facility is where a discharge leg GOES, not who orders or pays it. So '
            'SNF bed counts are NOT a demand node in this model; the recurring-SNF '
            'term is dropped and demand is sized off the ordering hospitals only.</div>'))


def _inventory_section(inv) -> str:
    if not (inv and inv.available):
        return ""
    rows = []
    for s in inv.signals:
        ds = ""
        if s.dataset_id and s.basis == "CONNECTOR":
            ds = (f'<a href="/connector-estate?dataset={_esc(s.dataset_id)}" '
                  f'style="color:var(--sc-teal,#155752);text-decoration:none;">'
                  f'{_esc(s.dataset_id)}</a>')
        else:
            ds = _esc(s.dataset_id or "—")
        rows.append((_esc(s.driver), _esc(s.what_it_yields), _esc(s.source),
                     _chip(s.basis), _status_badge(s.status), ds))
    kpis = (
        '<div class="ihd-kpi-grid">'
        + _kpi("Demand signals", str(len(inv.signals)), "drivers we can source")
        + _kpi("Live now", str(inv.n_live), "SOURCED / vendored")
        + _kpi("Ingest-ready", str(inv.n_ingest_ready), "registered connectors")
        + _kpi("To source", str(inv.n_to_source), "GOV/academic series to pull")
        + '</div>')
    return (
        ck_section_header("Demand-data inventory — what we need & what we have",
                          eyebrow="THE DATA", count=len(inv.signals))
        + ck_panel(
            '<p class="ihd-prose">Sizing this well is a data problem. Every demand '
            'driver we can source, what it yields, its basis, and whether it is '
            'live, ingest-ready, or still to source.</p>'
            + kpis
            + _table(("Demand driver", "What it yields", "Source", "Basis",
                      "Status", "Dataset"), rows)
            + f'<p class="ihd-src">Source: {_esc(inv.source_label)}</p>'))


def _metro_section(hd) -> str:
    if not hd:
        return ""
    sourced = any(m.discharge_basis == "SOURCED" for m in hd)
    rows = [(_esc(m.metro), _esc(m.region_label), _num(m.n_hospitals),
             _num(m.discharges) + " " + _chip(m.discharge_basis),
             _num(m.ift_legs), _num(m.serviceable_legs), _usd_m(m.demand_dollars))
            for m in hd]
    return (
        ck_section_header("Hospital-discharge demand, by metro",
                          eyebrow="THE DRIVER · BY MARKET", count=len(hd))
        + ck_panel(
            '<p class="ihd-prose">Each market\'s demand sized off its hospitals\' '
            'discharges (SNF dropped). ' + (
                'Discharges are SOURCED from the HCRIS panel. '
                if sourced else
                'The HCRIS panel is not ingested in this environment, so '
                'discharges use the labelled hospital-count fallback — they flip '
                'to SOURCED (patient_days ÷ ALOS) once HCRIS is ingested. ')
            + '</p>'
            + _table(("Metro", "Region", "Hospitals", "Discharges/yr",
                      "IFT legs/yr", "Serviceable", "Demand $"), rows)
            + f'<p class="ihd-src">Discharges {_chip("SOURCED")}/{_chip("ILLUSTRATIVE")} '
            f'(HCRIS or hospital-count fallback); legs = discharges × f_IFT; '
            f'demand $ = serviceable legs × $600 realized {_chip("ILLUSTRATIVE")}.</p>'))


def _system_section(sr) -> str:
    if not sr:
        return ""
    rows = [(_esc(s.system), _chip("ACADEMIC") if False else _esc(s.tier),
             _num(s.n_metros), _num(s.ift_legs), _num(s.serviceable_legs),
             _usd_m(s.demand_dollars), _esc(s.strategy)) for s in sr]
    return (
        ck_section_header("The buyers — demand by health system",
                          eyebrow="THE LARGER SYSTEMS", count=len(sr))
        + ck_panel(
            '<p class="ihd-prose">Demand attributed to the larger multi-hospital '
            'health systems — the actual buyers. Each system\'s figure is its '
            '<em>reach</em> (the demand in the metros it anchors); reach overlaps '
            'where two systems share a metro, so this is contested reach, not an '
            'exclusive split.</p>'
            + _table(("Health system", "Tier", "Metros", "IFT legs/yr",
                      "Serviceable", "Demand $ (reach)", "MMT strategy"), rows)
            + f'<p class="ihd-src">System reach {_chip("ILLUSTRATIVE")} on the '
            'SOURCED hospital base; systems &amp; posture public/company-web, '
            'labelled.</p>'))


def _county_section(cd) -> str:
    if not cd:
        return ""
    rows = [(_esc(c.county + ", " + c.state), _esc(c.cbsa_name), _esc(c.role),
             _num(c.pop_2020), _num(c.pop_65_plus), _pct(c.pop_share_of_metro),
             _num(c.ift_legs), _usd_m(c.demand_dollars),
             _esc(", ".join(c.anchor_systems[:2])) or "—")
            for c in cd]
    return (
        ck_section_header("County breakdown — demand across the footprint",
                          eyebrow="BY COUNTY", count=len(cd))
        + ck_panel(
            '<p class="ihd-prose">Each metro\'s hospital-driven demand allocated '
            'to its served counties by 2020 population share, tagged with the '
            'systems that serve the county\'s metro. Population is GOV (2020 '
            'Census); the allocation weight is labelled.</p>'
            + _table(("County", "CBSA", "Role", "Population", "65+",
                      "Pop share", "IFT legs/yr", "Demand $", "Systems served"),
                     rows)
            + f'<p class="ihd-src">County population {_chip("GOV")} (2020 Census); '
            f'metro→county allocation + demand {_chip("ILLUSTRATIVE")}.</p>'))


def _charts(hd, sr) -> str:
    cards: List[str] = []
    try:
        if hd:
            items = [(m.metro, m.demand_dollars / 1e6, "teal") for m in hd[:12]]
            cards.append(ck_hbar_chart(
                "Hospital-driven demand $ by metro ($M)", items,
                value_fmt=lambda v: f"${v:,.2f}M",
                subtitle="Sized off hospital discharges (SNF dropped).",
                source="ift_hs_demand.hospital_demand", label_w=170.0))
    except Exception:  # noqa: BLE001
        pass
    try:
        if sr:
            items = [(s.system, s.demand_dollars / 1e6, "navy") for s in sr[:10]]
            cards.append(ck_hbar_chart(
                "Demand reach by health system ($M)", items,
                value_fmt=lambda v: f"${v:,.2f}M",
                subtitle="The larger systems — the buyers (reach, not exclusive).",
                source="ift_hs_demand.health_system_rollup", label_w=210.0))
    except Exception:  # noqa: BLE001
        pass
    grid = ck_chart_grid(*cards)
    return (ck_section_header("At a glance", eyebrow="THE BUYERS, VISUALLY")
            + grid) if grid else ""


# ═══════════════════════════════════════════════════════════════════════════
def render_ift_hs_demand(qs: Optional[Dict[str, List[str]]] = None) -> str:
    """Render the health-system demand page. Degrades to honest notes, never
    raises."""
    hd = _hd.hospital_demand()
    sr = _hd.health_system_rollup()
    cd = _hd.county_demand()
    inv = _hd.demand_data_inventory()
    summ = _hd.hs_demand_summary()

    meta = (f"{summ['n_systems']} health systems · {summ['n_metros']} metros · "
            f"{summ['n_counties']} counties · {summ['total_discharges']:,} "
            f"discharges/yr → {summ['total_ift_legs']:,} IFT legs · "
            f"{summ['n_signals']} demand signals")
    head = ck_page_title(
        "IFT Demand — Health-System Sizing", eyebrow="INTERFACILITY TRANSPORT · "
        "THE BUYER'S DEMAND, HCRIS-DRIVEN", meta=meta)
    explainer = (
        '<p class="ihd-prose" style="font-size:15px;">Demand sized the buyer\'s '
        'way: off the <strong>larger health systems\'</strong> hospital '
        'throughput, from <strong>Hospital Cost Reports (HCRIS)</strong>, broken '
        'down <strong>county by county</strong> across the footprint. The '
        'destination-side SNF term is <strong>dropped</strong> — a SNF is where a '
        'leg goes, not who buys it. Plus the <strong>demand-data inventory</strong>: '
        'what drives volume, what we have, and what to source. Figures carry their '
        'basis — ' + _chip("SOURCED") + ' ' + _chip("ILLUSTRATIVE") + ' '
        + _chip("GOV") + ' ' + _chip("CONNECTOR") + '.</p>')

    body = "".join([
        _STYLES,
        ck_chart_assets(),
        head,
        explainer,
        _download_bar(),
        _crosslinks(),
        ck_section_intro(
            "HOW TO READ THIS",
            "The method, the data, then the demand by system and county.",
            italic_word="data",
            body=("First how we size it (hospital discharges, SNF dropped), then "
                  "the demand-data inventory, then the demand by metro, by health "
                  "system (the buyers), and county by county.")),
        _charts(hd, sr),
        _method_section(),
        _inventory_section(inv),
        _metro_section(hd),
        _system_section(sr),
        _county_section(cd),
        _crosslinks(),
        ck_next_section(
            "See the national → subcounty demand deep-dive (CMS codes, over time)",
            "/ift-demand", eyebrow="Demand deep-dive", italic_word="national"),
        ck_next_section(
            "Get the sourcing prompts for the demand data still to pull",
            "/ift-sourcing", eyebrow="The sourcing", italic_word="sourcing"),
        ck_page_actions(),
    ])
    return chartis_shell(
        body, "IFT Demand — Health-System Sizing", active_nav="/market",
        subtitle="Interfacility-transport demand sized off the larger health "
                 "systems' hospital throughput (HCRIS), county by county")
