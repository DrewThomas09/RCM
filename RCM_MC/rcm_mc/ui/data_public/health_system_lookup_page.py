"""Health System Lookup — /health-system-lookup.

The master mapping of the US hospital universe: every health system we
can name-match, how many hospitals it runs, where they are, and what
kind of facility each one is — with behavioral health as a first-class
facet rather than a footnote.

Everything on this page derives from ``rcm_mc.data.health_systems``,
which maps the bundled HCRIS universe (6,123 facilities) onto a curated
system registry. Nothing here is modelled or illustrative: the counts
are counts. Where a facility's name carries no system brand it lands in
Independent / Unmapped, and the page says so in the coverage line rather
than quietly dropping it.

Filters are server-side (so a filtered view is a shareable URL); column
sorting is the shell's click-to-sort, which applies to the rendered rows.

The page answers the mapping in both directions:

  - ``?system=<id>`` opens one system's facility roster (system → hospitals)
  - ``?hospital=<name or CCN>`` resolves a facility to its system, which is
    the direction a partner reading a CIM actually starts from
  - ``/health-system-lookup.csv`` exports the same view, one row per
    hospital keyed on CCN so it joins against a target list in Excel

Beyond "who owns what", the page carries the read a deal team asks for
next: bed-share concentration. With a state filter it shows that state's
HHI, top-firm and top-three share; without one it ranks the states by
how concentrated their beds are.
"""
from __future__ import annotations

import html as _html
import urllib.parse
from typing import Any, Dict, List, Mapping, Optional, Sequence

from rcm_mc.ui._chartis_kit import (
    chartis_shell,
    ck_bar_row,
    ck_data_cell,
    ck_empty_state,
    ck_kpi_block,
    ck_page_actions,
    ck_page_title,
    ck_source_purpose,
    ck_value_anchor,
)

ROUTE = "/health-system-lookup"

# Sort keys the master table understands. Click-to-sort reorders the
# rows already on the page; this drives which rows rank to the top
# before that, and keeps a sorted view linkable.
_SORTS: Dict[str, str] = {
    "hospitals": "Hospitals (most first)",
    "beds": "Beds (most first)",
    "behavioral": "Behavioral facilities (most first)",
    "behavioral_share": "Behavioral share (highest first)",
    "states": "State footprint (widest first)",
    "revenue": "Net patient revenue (largest first)",
    "name": "System name (A–Z)",
}

# Facility-type filter options — the "what is behavioral health" facet
# the master mapping exists to answer, alongside its siblings.
_TYPE_FILTERS: Sequence[tuple] = (
    ("", "All facility types"),
    ("behavioral", "Behavioral health"),
    ("general", "Acute care"),
    ("critical_access", "Critical access"),
    ("rehab", "Rehab"),
    ("ltach", "LTACH"),
    ("children", "Children's"),
)


def _esc(v: Any) -> str:
    return _html.escape(str(v if v is not None else ""))


def _fmt_int(v: Any) -> str:
    try:
        return f"{int(round(float(v))):,}"
    except (TypeError, ValueError):
        return "—"


def _fmt_money_m(v: Any) -> str:
    """Financial figures render at 2dp per the house number rules."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "—"
    if not f:
        return "—"
    if abs(f) >= 1e9:
        return f"${f / 1e9:,.2f}B"
    return f"${f / 1e6:,.2f}M"


def _fmt_pct(v: Any) -> str:
    try:
        return f"{float(v) * 100:.1f}%"
    except (TypeError, ValueError):
        return "—"


def _qs(**params: Any) -> str:
    """Build a link back into this page preserving only set filters."""
    clean = {k: str(v) for k, v in params.items() if v not in (None, "", 0)}
    return ROUTE + ("?" + urllib.parse.urlencode(clean) if clean else "")


# ── Filtering ──────────────────────────────────────────────────────


def _matches(row, *, query: str, state: str, kind: str, focus: str,
             ftype: str, min_hospitals: int) -> bool:
    if query and query not in row.system_name.lower() and query not in row.system_id.lower():
        return False
    if state and state not in row.states:
        return False
    if kind and row.kind != kind:
        return False
    if focus and row.focus != focus:
        return False
    if min_hospitals and row.hospitals < min_hospitals:
        return False
    if ftype == "behavioral":
        return row.behavioral_hospitals > 0
    if ftype:
        return row.type_count(ftype) > 0
    return True


_SORT_KEYS = {
    "hospitals": lambda r: (-r.hospitals, -r.beds),
    "beds": lambda r: (-r.beds, -r.hospitals),
    "behavioral": lambda r: (-r.behavioral_hospitals, -r.hospitals),
    "behavioral_share": lambda r: (-r.behavioral_share, -r.behavioral_hospitals),
    "states": lambda r: (-r.state_count, -r.hospitals),
    "revenue": lambda r: (-r.net_patient_revenue, -r.hospitals),
    "name": lambda r: (r.system_name.lower(),),
}


# ── Page fragments ─────────────────────────────────────────────────


def _filter_bar(*, states: Sequence[str], kinds: Sequence[str],
                focuses: Sequence[str], selected: Mapping[str, str]) -> str:
    """GET form — a filtered view has to be a URL a partner can paste."""

    def _select(name: str, label: str, options: Sequence[tuple]) -> str:
        opts = []
        for value, text in options:
            sel = " selected" if str(selected.get(name, "")) == str(value) else ""
            opts.append(f'<option value="{_esc(value)}"{sel}>{_esc(text)}</option>')
        return (
            f'<label class="hsl-f"><span>{_esc(label)}</span>'
            f'<select name="{_esc(name)}">{"".join(opts)}</select></label>'
        )

    q = _esc(selected.get("q", ""))
    min_h = _esc(selected.get("min_hospitals", ""))
    # The export mirrors whatever is on screen — a partner who filtered to
    # "behavioral in TX" wants that list in Excel, not the whole universe.
    csv_href = _esc(_qs(
        state=selected.get("state", ""), kind=selected.get("kind", ""),
        focus=selected.get("focus", ""), type=selected.get("type", ""),
        q=selected.get("q", "")).replace(ROUTE, ROUTE + ".csv", 1))
    return f"""
<form class="hsl-filters" method="get" action="{ROUTE}">
  <label class="hsl-f hsl-f-wide"><span>Search system</span>
    <input type="search" name="q" value="{q}" placeholder="Ascension, Encompass, Oceans…"></label>
  {_select("state", "State", [("", "All states")] + [(s, s) for s in states])}
  {_select("kind", "Ownership", [("", "All ownership")] + [(k, k) for k in kinds])}
  {_select("focus", "System focus", [("", "All focuses")] + [(f, f) for f in focuses])}
  {_select("type", "Operates", list(_TYPE_FILTERS))}
  <label class="hsl-f"><span>Min hospitals</span>
    <input type="number" name="min_hospitals" min="1" max="200" value="{min_h}" placeholder="1"></label>
  {_select("sort", "Sort", list(_SORTS.items()))}
  <div class="hsl-f hsl-f-actions">
    <button type="submit" class="hsl-btn">Apply</button>
    <a class="hsl-reset" href="{ROUTE}">Reset</a>
    <a class="hsl-reset" href="{csv_href}">Download CSV</a>
  </div>
</form>"""


def _hospital_lookup_panel(query: str) -> str:
    """Reverse lookup — a facility name or CCN in, its system out.

    A partner reading a CIM has the hospital's name, not its system.
    Without this the page only answered the question in one direction.
    """
    from rcm_mc.data.health_systems import UNMAPPED_ID, find_hospitals

    hits = find_hospitals(query, limit=60)
    header = f"""
<form class="hsl-filters" method="get" action="{ROUTE}">
  <label class="hsl-f hsl-f-wide"><span>Find a hospital → its system</span>
    <input type="search" name="hospital" value="{_esc(query)}"
           placeholder="Facility name or CCN, e.g. 450087 or Crenshaw"></label>
  <div class="hsl-f hsl-f-actions">
    <button type="submit" class="hsl-btn">Look up</button>
    <a class="hsl-reset" href="{ROUTE}">Clear</a>
  </div>
</form>"""
    if not query:
        return header
    if hits.empty:
        return header + ck_empty_state(
            f"No facility matches “{_esc(query)}”.",
            "Try a shorter fragment of the name, or the 6-digit CCN.")

    cols = [("CCN", "left"), ("Facility", "left"), ("City", "left"),
            ("State", "center"), ("Type", "left"), ("Behavioral", "center"),
            ("Beds", "right"), ("Health System", "left"), ("Matched On", "left")]
    ths = "".join(ck_data_cell(c, align=a, is_header=True) for c, a in cols)
    trs = []
    for row in hits.to_dict("records"):
        ccn = str(row.get("ccn", ""))
        beh = bool(row.get("is_behavioral"))
        mapped = row.get("system_id") != UNMAPPED_ID
        system = (
            f'<a class="ck-link" href="{_qs(system=row.get("system_id"))}">'
            f'{_esc(row.get("system_name"))}</a>' if mapped
            else f'<span class="tone-dim">{_esc(row.get("system_name"))}</span>')
        cells = [
            ck_data_cell(_esc(ccn), mono=True, tone="dim"),
            f'<td class="ck-cell ck-cell-w-600">'
            f'<a class="ck-link" href="/hospital/{_esc(ccn)}">'
            f'{_esc(row.get("name", ""))}</a></td>',
            ck_data_cell(_esc(row.get("city", "")), tone="dim"),
            ck_data_cell(_esc(row.get("state", "")), align="center", mono=True),
            ck_data_cell(_esc(row.get("facility_type_label", "")), tone="dim"),
            ck_data_cell("YES" if beh else "—", align="center", mono=True,
                         tone="acc" if beh else "dim", weight=700 if beh else None),
            ck_data_cell(_fmt_int(row.get("beds")), align="right", mono=True),
            f'<td class="ck-cell ck-cell-w-600">{system}</td>',
            ck_data_cell(_esc(row.get("system_match", "")), mono=True, tone="dim"),
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    table = ('<div class="ck-data-table-scroll"><table class="ck-data-table">'
             f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')
    return (header + table +
            f'<div class="hsl-legend">{len(hits):,} facilities match '
            f'“{_esc(query)}”. Independent / Unmapped means the HCRIS name '
            'carries no system brand — not that the hospital is '
            'independently owned.</div>')


def _active_chips(selected: Mapping[str, str], shown: int, total: int) -> str:
    chips: List[str] = []
    label_map = {
        "q": "Search", "state": "State", "kind": "Ownership",
        "focus": "Focus", "min_hospitals": "Min hospitals",
    }
    for key, label in label_map.items():
        val = selected.get(key, "")
        if val:
            chips.append(f'<span class="hsl-chip">{_esc(label)}: {_esc(val)}</span>')
    ftype = selected.get("type", "")
    if ftype:
        name = dict(_TYPE_FILTERS).get(ftype, ftype)
        chips.append(f'<span class="hsl-chip">Operates: {_esc(name)}</span>')
    sort = selected.get("sort", "hospitals")
    chips.append(f'<span class="hsl-chip hsl-chip-quiet">Sorted: {_esc(_SORTS.get(sort, sort))}</span>')
    chips.append(
        f'<span class="hsl-chip hsl-chip-quiet">Showing {shown:,} of {total:,} systems</span>')
    return f'<div class="hsl-chips">{"".join(chips)}</div>'


def _kpi_strip(m, largest) -> str:
    from rcm_mc.data.health_systems import STATUS_DORMANT, STATUS_STOPPED

    return (
        ck_kpi_block("Systems mapped", _fmt_int(m.system_count),
                     "name-matched in registry", "")
        + ck_kpi_block("Operating hospitals", _fmt_int(m.total_hospitals),
                       f"of {m.universe_facilities:,} CCNs in HCRIS", "")
        + ck_kpi_block("Hospitals in systems", _fmt_int(m.mapped_hospitals),
                       f"{m.coverage_pct:.1f}% of operating", "")
        + ck_kpi_block("Behavioral facilities", _fmt_int(m.total_behavioral),
                       f"{m.behavioral_systems} systems operate one", "")
        + ck_kpi_block("Multi-state systems", _fmt_int(m.multi_state_systems),
                       "2+ state footprint", "")
        + ck_kpi_block("Largest system",
                       _esc(largest.system_name) if largest else "—",
                       f"{largest.hospitals} operating" if largest else "", "")
        + ck_kpi_block("Not operating", _fmt_int(m.inactive_hospitals),
                       f"{m.status_total(STATUS_STOPPED)} stopped filing · "
                       f"{m.status_total(STATUS_DORMANT)} dormant", "")
        + ck_kpi_block("Independent / unmapped", _fmt_int(m.unmapped.hospitals),
                       "no system brand in name", "")
    )


def _systems_table(rows) -> str:
    cols = [
        ("#", "right"), ("Health System", "left"), ("Ownership", "left"),
        ("Focus", "left"), ("HQ", "center"), ("Hospitals", "right"),
        ("Beds", "right"), ("Avg Beds", "right"), ("States", "right"),
        ("Acute", "right"), ("Critical Access", "right"), ("Behavioral", "right"),
        ("Rehab", "right"), ("LTACH", "right"), ("Children's", "right"),
        ("Behavioral %", "right"), ("Net Patient Revenue", "right"),
        ("Not Operating", "right"),
    ]
    ths = "".join(ck_data_cell(c, align=a, is_header=True) for c, a in cols)
    max_h = max((r.hospitals for r in rows), default=1) or 1
    trs = []
    for i, r in enumerate(rows, start=1):
        beh_tone = "acc" if r.behavioral_hospitals else "dim"
        link = (f'<a class="ck-link" href="{_qs(system=r.system_id)}">'
                f'{_esc(r.system_name)}</a>')
        cells = [
            ck_data_cell(str(i), align="right", mono=True, tone="dim"),
            f'<td class="ck-cell ck-cell-w-700">{link}</td>',
            ck_data_cell(_esc(r.kind), tone="dim"),
            ck_data_cell(_esc(r.focus), tone="dim"),
            ck_data_cell(_esc(r.hq_state), align="center", mono=True, tone="dim"),
            ck_data_cell(_fmt_int(r.hospitals), align="right", mono=True,
                         weight=700, tone="acc", bar=r.hospitals / max_h * 100),
            ck_data_cell(_fmt_int(r.beds), align="right", mono=True),
            ck_data_cell(_fmt_int(r.avg_beds), align="right", mono=True, tone="dim"),
            ck_data_cell(_fmt_int(r.state_count), align="right", mono=True),
            ck_data_cell(_fmt_int(r.type_count("general")), align="right", mono=True),
            ck_data_cell(_fmt_int(r.type_count("critical_access")), align="right", mono=True),
            ck_data_cell(_fmt_int(r.behavioral_hospitals), align="right", mono=True,
                         weight=700, tone=beh_tone),
            ck_data_cell(_fmt_int(r.type_count("rehab")), align="right", mono=True),
            ck_data_cell(_fmt_int(r.type_count("ltach")), align="right", mono=True),
            ck_data_cell(_fmt_int(r.type_count("children")), align="right", mono=True),
            ck_data_cell(_fmt_pct(r.behavioral_share), align="right", mono=True,
                         tone=beh_tone),
            ck_data_cell(_fmt_money_m(r.net_patient_revenue), align="right",
                         mono=True, tone="pos"),
            ck_data_cell(_fmt_int(r.inactive_hospitals) if r.inactive_hospitals
                         else "—", align="right", mono=True,
                         tone="neg" if r.inactive_hospitals else "dim"),
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return ('<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _behavioral_panel(rows) -> str:
    """Behavioral platforms ranked — the facet the mapping was asked for."""
    ranked = sorted([r for r in rows if r.behavioral_hospitals > 0],
                    key=lambda r: (-r.behavioral_hospitals, -r.beds))[:15]
    if not ranked:
        return ck_empty_state("No behavioral facilities in the current filter.")
    total = sum(r.behavioral_hospitals for r in ranked) or 1
    bars = []
    for r in ranked:
        tone = ("positive" if r.behavioral_share >= 0.9 else
                "teal" if r.behavioral_share >= 0.3 else "warning")
        bars.append(ck_bar_row(
            r.system_name,
            f"{r.behavioral_hospitals} of {r.hospitals}",
            r.behavioral_hospitals / total * 100.0,
            tone=tone,
        ))
    return (
        '<div style="margin-bottom:8px">' + "".join(bars) +
        '<div class="hsl-legend">Bar = share of the behavioral facilities on '
        'this screen · value = behavioral facilities of total facilities · tone '
        '= pure-play (green ≥90%) · behavioral-heavy (teal ≥30%) · '
        'behavioral line inside a broader system (amber)</div></div>'
    )


def _type_mix_panel(m) -> str:
    from rcm_mc.data.health_systems import TYPE_DISPLAY, TYPE_LABELS

    total = sum(m.type_totals.values()) or 1
    rows = []
    for label in TYPE_LABELS:
        count = m.type_totals.get(label, 0)
        if not count:
            continue
        tone = "positive" if label == "psychiatric" else "teal"
        rows.append(ck_bar_row(
            TYPE_DISPLAY.get(label, label),
            f"{count:,} ({count / total * 100:.1f}%)",
            count / total * 100.0,
            tone=tone,
        ))
    return ('<div style="margin-bottom:8px">' + "".join(rows) +
            '<div class="hsl-legend">Whole HCRIS universe (systems + '
            'independents), classified by CCN range with a name fallback — the '
            'same classifier the screeners use.</div></div>')


def _roster_panel(system_id: str, rows) -> str:
    """Facility roster for one system — the drill-down half of a lookup."""
    from rcm_mc.data.health_systems import get_system, system_hospitals

    sysdef = get_system(system_id)
    if sysdef is None:
        return ""
    roster = system_hospitals(system_id)
    if roster.empty:
        return ck_empty_state(f"No facilities mapped to {sysdef.name}.")
    rollup = next((r for r in rows if r.system_id == system_id), None)
    cols = [("CCN", "left"), ("Facility", "left"), ("City", "left"),
            ("State", "center"), ("Type", "left"), ("Behavioral", "center"),
            ("Beds", "right"), ("Net Patient Revenue", "right"),
            ("Status", "left"), ("Matched On", "left")]
    ths = "".join(ck_data_cell(c, align=a, is_header=True) for c, a in cols)
    trs = []
    for _, row in roster.iterrows():
        ccn = str(row.get("ccn", ""))
        beh = bool(row.get("is_behavioral"))
        link = (f'<a class="ck-link" href="/hospital/{_esc(ccn)}">'
                f'{_esc(row.get("name", ""))}</a>')
        cells = [
            ck_data_cell(_esc(ccn), mono=True, tone="dim"),
            f'<td class="ck-cell ck-cell-w-600">{link}</td>',
            ck_data_cell(_esc(row.get("city", "")), tone="dim"),
            ck_data_cell(_esc(row.get("state", "")), align="center", mono=True),
            ck_data_cell(_esc(row.get("facility_type_label", "")), tone="dim"),
            ck_data_cell("YES" if beh else "—", align="center", mono=True,
                         tone="acc" if beh else "dim", weight=700 if beh else None),
            ck_data_cell(_fmt_int(row.get("beds")), align="right", mono=True),
            ck_data_cell(_fmt_money_m(row.get("net_patient_revenue")),
                         align="right", mono=True, tone="pos"),
            ck_data_cell(
                _esc(row.get("facility_status", ""))
                + (" · no reported activity" if row.get("reports_no_activity") else ""),
                tone="dim" if row.get("is_operating") else "neg",
                weight=None if row.get("is_operating") else 600),
            ck_data_cell(_esc(row.get("system_match", "")), mono=True, tone="dim"),
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    table = ('<div class="ck-data-table-scroll"><table class="ck-data-table">'
             f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')
    meta = ""
    if rollup is not None:
        inactive = (f' · {rollup.inactive_hospitals} not operating'
                    if rollup.inactive_hospitals else '')
        meta = (f'{rollup.hospitals} operating facilities{inactive} · '
                f'{_fmt_int(rollup.beds)} beds · {rollup.state_count} states · '
                f'{rollup.behavioral_hospitals} behavioral '
                f'({_fmt_pct(rollup.behavioral_share)}) · '
                f'{_fmt_money_m(rollup.net_patient_revenue)} net patient revenue')
    note = f'<div class="hsl-legend">{_esc(sysdef.note)}</div>' if sysdef.note else ""
    return f"""
<div class="hsl-roster">
  <div class="hsl-roster-head">
    <div>
      <div class="hsl-roster-eyebrow">SYSTEM ROSTER</div>
      <div class="hsl-roster-title">{_esc(sysdef.name)}</div>
      <div class="hsl-roster-meta">{_esc(meta)}</div>
    </div>
    <a class="hsl-reset" href="{ROUTE}">← Back to all systems</a>
  </div>
  {note}
  {table}
  <div class="hsl-legend">"Matched On" is the registry pattern that pulled the
  facility into this system — the audit trail behind every count above. The
  roster lists every CCN mapped to the system; only the ones marked Active
  count toward its operating estate.</div>
</div>"""


def _concentration_panel(state: str) -> str:
    """Who controls the beds in one state.

    The mapping answers "who owns what"; this answers the question a
    deal team asks next. Share is on beds rather than facility count —
    a 400-bed flagship and a 15-bed critical-access hospital are not
    one unit of market power each.
    """
    from rcm_mc.data.health_systems import state_concentration

    c = state_concentration(state)
    if c is None:
        return ""
    band_tone = ("negative" if c.hhi >= 2500 else
                 "warning" if c.hhi >= 1500 else "teal")
    top = c.shares[:12]
    bars = []
    for share in top:
        label = share.system_name + (" · independent" if share.is_independent else "")
        tone = "positive" if not share.is_independent else "navy"
        bars.append(ck_bar_row(
            label,
            f"{share.bed_share * 100:.1f}%",
            share.bed_share * 100.0,
            tone=tone,
        ))
    rest = len(c.shares) - len(top)
    tail = (f'<div class="hsl-legend">+{rest:,} smaller firms not shown.</div>'
            if rest > 0 else "")
    anchor = ck_value_anchor(
        f"{_esc(c.state)} bed-share concentration",
        f"HHI {c.hhi:,.0f} · {c.band}",
        delta=(f"Top firm {c.cr1 * 100:.1f}% · top three {c.cr3 * 100:.1f}% · "
               f"{c.hospitals:,} operating hospitals · {c.beds:,.0f} beds"),
        opportunity=(f"{c.independent_share * 100:.1f}% of beds sit outside a "
                     f"mapped system ({c.independent_facilities:,} facilities)"),
        tone=band_tone,
    )
    return anchor + "".join(bars) + tail + (
        '<div class="hsl-legend">Share is of the state\u2019s operating beds. '
        'Each mapped system is one firm and <strong>each unmapped facility is '
        'its own firm</strong> — the conservative reading when ownership is '
        'unknown, so every HHI here is a <strong>floor</strong>: real '
        'concentration is at least this high, and higher wherever an unmapped '
        'facility is quietly part of a system. Bands are the DOJ/FTC '
        'merger-guideline thresholds (1,500 / 2,500).</div>')


def _concentration_ranking_panel() -> str:
    """States ranked by how concentrated their beds are — a sourcing lens."""
    from rcm_mc.data.health_systems import concentration_ranking

    ranked = concentration_ranking(limit=15)
    if not ranked:
        return ""
    cols = [("State", "center"), ("HHI (floor)", "right"), ("Band", "left"),
            ("Top Firm", "right"), ("Top 3", "right"), ("Leading Firm", "left"),
            ("Hospitals", "right"), ("Beds", "right"), ("Outside a System", "right")]
    ths = "".join(ck_data_cell(c, align=a, is_header=True) for c, a in cols)
    trs = []
    for c in ranked:
        leader = c.leader
        tone = ("neg" if c.hhi >= 2500 else "acc" if c.hhi >= 1500 else "dim")
        leader_html = (
            f'{_esc(leader.system_name)}'
            + (' <span class="tone-dim">· independent</span>'
               if leader and leader.is_independent else '')) if leader else "—"
        cells = [
            f'<td class="ck-cell ck-cell-c ck-cell-mono ck-cell-w-700">'
            f'<a class="ck-link" href="{_qs(state=c.state)}">{_esc(c.state)}</a></td>',
            ck_data_cell(f"{c.hhi:,.0f}", align="right", mono=True, weight=700,
                         tone=tone),
            ck_data_cell(_esc(c.band), tone=tone),
            ck_data_cell(f"{c.cr1 * 100:.1f}%", align="right", mono=True),
            ck_data_cell(f"{c.cr3 * 100:.1f}%", align="right", mono=True),
            f'<td class="ck-cell">{leader_html}</td>',
            ck_data_cell(_fmt_int(c.hospitals), align="right", mono=True),
            ck_data_cell(_fmt_int(c.beds), align="right", mono=True),
            ck_data_cell(f"{c.independent_share * 100:.1f}%", align="right",
                         mono=True, tone="dim"),
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return ('<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _inactive_panel(status_filter: str = "") -> str:
    """Every facility excluded from the operating counts, by name.

    The exclusion is only trustworthy if it is auditable — a partner has
    to be able to see which hospitals were dropped and why, rather than
    take a smaller number on faith.
    """
    from rcm_mc.data.health_systems import (
        STATUS_DORMANT, STATUS_ORDER, STATUS_STOPPED, get_system_map,
        inactive_facilities,
    )

    # One pass over the held-out set: the counts on the status tabs are
    # derived from it rather than re-running the filter per tab, which
    # was four full passes over the universe per render.
    everything = inactive_facilities()
    by_status = (everything["facility_status"].value_counts().to_dict()
                 if not everything.empty else {})
    rows = (everything[everything["facility_status"] == status_filter]
            if status_filter else everything)
    if rows.empty:
        return ck_empty_state("No inactive facilities under this filter.")

    tabs = ['<div class="hsl-chips">']
    tabs.append(
        f'<a class="hsl-chip{"" if status_filter else " hsl-chip-on"}" '
        f'href="{_qs()}#inactive">All non-operating ({len(everything):,})</a>')
    for st in STATUS_ORDER[1:]:
        n = int(by_status.get(st, 0))
        on = " hsl-chip-on" if status_filter == st else ""
        tabs.append(f'<a class="hsl-chip{on}" href="{_qs(status=st)}#inactive">'
                    f'{_esc(st.split(" — ")[0])} ({n:,})</a>')
    tabs.append("</div>")

    tone_for = {STATUS_STOPPED: "neg", STATUS_DORMANT: "acc"}
    cols = [("CCN", "left"), ("Facility", "left"), ("City", "left"),
            ("State", "center"), ("Type", "left"), ("Health System", "left"),
            ("Last Cost Report", "right"), ("Last Year With Activity", "right"),
            ("Last Reported Beds", "right"), ("Status", "left")]
    ths = "".join(ck_data_cell(c, align=a, is_header=True) for c, a in cols)
    trs = []
    for row in rows.to_dict("records"):
        ccn = str(row.get("ccn", ""))
        status = str(row.get("facility_status", ""))
        fy = row.get("last_fiscal_year")
        la = row.get("last_active_fiscal_year")
        cells = [
            ck_data_cell(_esc(ccn), mono=True, tone="dim"),
            f'<td class="ck-cell ck-cell-w-600">'
            f'<a class="ck-link" href="/hospital/{_esc(ccn)}">'
            f'{_esc(row.get("name", ""))}</a></td>',
            ck_data_cell(_esc(row.get("city", "")), tone="dim"),
            ck_data_cell(_esc(row.get("state", "")), align="center", mono=True),
            ck_data_cell(_esc(row.get("facility_type_label", "")), tone="dim"),
            ck_data_cell(_esc(row.get("system_name", "")), tone="dim"),
            ck_data_cell("—" if fy is None or fy != fy else _esc(fy),
                         align="right", mono=True),
            ck_data_cell(_esc(la) if la is not None and la == la else "never",
                         align="right", mono=True, tone="dim"),
            ck_data_cell(_fmt_int(row.get("beds")), align="right", mono=True,
                         tone="dim"),
            ck_data_cell(_esc(status), tone=tone_for.get(status, "dim"),
                         weight=600),
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    table = ('<div class="ck-data-table-scroll"><table class="ck-data-table">'
             f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')
    zero = get_system_map().zero_activity_hospitals
    flagged = (
        f'<div class="hsl-legend"><strong>Separately:</strong> {zero:,} '
        'facilities filed a current cost report reporting zero beds, zero '
        'patient days and zero net patient revenue. They are NOT held out — '
        'a current filing is evidence the CCN is live, and this group is '
        "mostly children's and specialty hospitals (Mary Bridge Children's, "
        'Shriners, Texas Scottish Rite) that do not report those fields the '
        'way a general acute hospital does. They count as hospitals while '
        "contributing nothing to beds or revenue, which is why a system's "
        'bed count can read light against its hospital count.</div>')
    return "".join(tabs) + table + flagged


def _candidates_panel(m) -> str:
    """The registry's visible backlog, so coverage gaps aren't invisible."""
    if not m.candidates:
        return ""
    cols = [("Name Stem", "left"), ("State", "center"), ("Facilities", "right"),
            ("Beds", "right"), ("Examples", "left")]
    ths = "".join(ck_data_cell(c, align=a, is_header=True) for c, a in cols)
    trs = []
    for c in m.candidates[:25]:
        cells = [
            ck_data_cell(_esc(c.stem), mono=True, weight=600),
            ck_data_cell(_esc(c.state), align="center", mono=True),
            ck_data_cell(_fmt_int(c.hospitals), align="right", mono=True, tone="acc"),
            ck_data_cell(_fmt_int(c.beds), align="right", mono=True),
            ck_data_cell(_esc(" · ".join(c.examples)), tone="dim"),
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return ('<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


_PAGE_CSS = """
<style>
.hsl-filters{display:flex;flex-wrap:wrap;gap:10px 14px;align-items:flex-end;
  background:var(--sc-panel-alt,#efeae1);border:1px solid var(--sc-border,#ded6c8);
  padding:12px 14px;margin-bottom:12px}
.hsl-f{display:flex;flex-direction:column;gap:4px}
.hsl-f>span{font-family:JetBrains Mono,monospace;font-size:9px;letter-spacing:0.08em;
  text-transform:uppercase;color:var(--sc-text-faint,#7d7566)}
.hsl-f select,.hsl-f input{font-family:Inter Tight,system-ui,sans-serif;font-size:12px;
  padding:5px 8px;border:1px solid var(--sc-border,#ded6c8);background:var(--sc-panel,#faf7f1);
  color:var(--sc-text,#1a2332);min-width:150px}
.hsl-f-wide input{min-width:230px}
.hsl-f-actions{flex-direction:row;align-items:center;gap:10px}
.hsl-btn{font-family:Inter Tight,system-ui,sans-serif;font-size:12px;font-weight:600;
  padding:6px 16px;border:1px solid var(--sc-teal,#155752);background:var(--sc-teal,#155752);
  color:#fff;cursor:pointer}
.hsl-reset{font-size:11px;color:var(--sc-teal,#155752);text-decoration:none}
.hsl-chips{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:14px}
.hsl-chip{font-family:JetBrains Mono,monospace;font-size:10px;letter-spacing:0.05em;
  padding:3px 8px;border:1px solid var(--sc-teal,#155752);color:var(--sc-teal,#155752)}
.hsl-chip-quiet{border-color:var(--sc-border,#ded6c8);color:var(--sc-text-faint,#7d7566)}
.hsl-chips a.hsl-chip{text-decoration:none}
.hsl-chip-on{background:var(--sc-teal,#155752);color:#fff}
.hsl-legend{font-family:JetBrains Mono,monospace;font-size:10px;
  color:var(--sc-text-faint,#7d7566);margin-top:6px;line-height:1.5}
.hsl-roster{background:var(--sc-panel,#faf7f1);border:1px solid var(--sc-border,#ded6c8);
  border-left:3px solid var(--sc-teal,#155752);padding:14px 16px;margin-bottom:16px}
.hsl-roster-head{display:flex;justify-content:space-between;align-items:flex-start;
  gap:16px;margin-bottom:10px}
.hsl-roster-eyebrow{font-family:JetBrains Mono,monospace;font-size:9px;
  letter-spacing:0.12em;color:var(--sc-text-faint,#7d7566)}
.hsl-roster-title{font-family:Source Serif 4,Georgia,serif;font-size:20px;
  color:var(--sc-navy,#0b2341)}
.hsl-roster-meta{font-family:JetBrains Mono,monospace;font-size:10px;
  color:var(--sc-text-faint,#7d7566);margin-top:3px}
</style>
"""


def render_health_system_lookup(params: Optional[Mapping[str, str]] = None) -> str:
    """Render the master health-system mapping."""
    from rcm_mc.data.health_systems import (
        KIND_ACADEMIC, KIND_CATHOLIC, KIND_FOR_PROFIT, KIND_GOVERNMENT,
        KIND_NONPROFIT, get_system_map, registry_size,
    )

    params = dict(params or {})
    query = str(params.get("q", "")).strip().lower()
    state = str(params.get("state", "")).strip().upper()
    kind = str(params.get("kind", "")).strip()
    focus = str(params.get("focus", "")).strip()
    ftype = str(params.get("type", "")).strip()
    system_id = str(params.get("system", "")).strip()
    hospital_q = str(params.get("hospital", "")).strip()[:80]
    status = str(params.get("status", "")).strip()[:60]
    sort = str(params.get("sort", "hospitals")).strip()
    if sort not in _SORTS:
        sort = "hospitals"
    try:
        min_hospitals = max(0, min(200, int(params.get("min_hospitals") or 0)))
    except (TypeError, ValueError):
        min_hospitals = 0

    m = get_system_map()
    all_states = sorted({s for row in m.systems for s in row.states})
    kinds = [KIND_FOR_PROFIT, KIND_NONPROFIT, KIND_CATHOLIC, KIND_ACADEMIC,
             KIND_GOVERNMENT]
    focuses = sorted({row.focus for row in m.systems if row.focus})

    rows = [r for r in m.systems
            if _matches(r, query=query, state=state, kind=kind, focus=focus,
                        ftype=ftype, min_hospitals=min_hospitals)]
    rows.sort(key=_SORT_KEYS[sort])

    selected = {"q": params.get("q", ""), "state": state, "kind": kind,
                "focus": focus, "type": ftype, "sort": sort,
                "min_hospitals": str(min_hospitals or "")}

    largest = m.systems[0] if m.systems else None
    shown_hospitals = sum(r.hospitals for r in rows)
    shown_behavioral = sum(r.behavioral_hospitals for r in rows)

    page_title = ck_page_title(
        "Health System Lookup",
        eyebrow="MASTER MAPPING",
        meta=(f"{m.system_count} health systems mapped across "
              f"{m.mapped_hospitals:,} of {m.total_hospitals:,} operating "
              f"hospitals ({m.coverage_pct:.1f}% name-matched) · "
              f"{m.total_behavioral:,} behavioral facilities · "
              f"{m.multi_state_systems} multi-state systems · "
              f"{m.states_covered} states and territories · "
              f"{m.inactive_hospitals:,} closed or dormant CCNs excluded"),
    )

    anchor = ck_value_anchor(
        "Systems on this screen",
        f"{len(rows):,} systems · {shown_hospitals:,} hospitals",
        delta=(f"{shown_behavioral:,} behavioral facilities · "
               f"{sum(r.type_count('critical_access') for r in rows):,} critical access · "
               f"{sum(r.type_count('rehab') for r in rows):,} rehab · "
               f"{sum(r.type_count('ltach') for r in rows):,} LTACH"),
        opportunity=(f"{m.unmapped.hospitals:,} hospitals still carry no system "
                     f"brand in their HCRIS name"),
        tone="teal",
    )

    roster = _roster_panel(system_id, m.systems) if system_id else ""
    lookup = _hospital_lookup_panel(hospital_q)
    inactive = _inactive_panel(status)
    concentration = (_concentration_panel(state) if state
                     else _concentration_ranking_panel())
    concentration_title = (f"Market Concentration — {_esc(state)}" if state
                           else "Most Concentrated States — Bed Share")
    table = _systems_table(rows) if rows else ck_empty_state(
        "No systems match these filters. Widen the state or ownership filter, "
        "or reset.")

    cell = ("background:var(--sc-panel,#faf7f1);border:1px solid "
            "var(--sc-border,#ded6c8);padding:16px;margin-bottom:16px")
    h3 = ("font-size:11px;font-weight:600;letter-spacing:0.08em;"
          "color:var(--sc-text-dim,#5b5545);text-transform:uppercase;margin-bottom:10px")

    body = f"""
{_PAGE_CSS}
<div class="ck-page-wrap">
  {page_title}
  {ck_source_purpose(
      purpose="Map any hospital to its health system, and any system to the "
              "hospitals, states and facility types it actually operates.",
      universe="hcris", confidence="derived",
      source=(f"CMS HCRIS cost reports — latest filing per CCN "
              f"({m.total_hospitals:,} facilities) mapped against a curated "
              f"{registry_size()}-system registry (name + state matching)"),
      next_action="Open a system to see its facility roster")}
  <div class="ck-kpi-grid" style="margin-bottom:20px">{_kpi_strip(m, largest)}</div>
  {anchor}
  {roster}
  <div style="{cell}">
    <div style="{h3}">Hospital Lookup — Which System Owns This Facility?</div>
    {lookup}
  </div>
  <div style="{cell}">
    <div style="{h3}">Master Mapping — Every System, Every Hospital Count</div>
    {_filter_bar(states=all_states, kinds=kinds, focuses=focuses, selected=selected)}
    {_active_chips(selected, len(rows), m.system_count)}
    {table}
    <div class="hsl-legend">Click any column header to re-sort the rows on this
    screen. Click a system name to open its facility roster. Behavioral counts a
    facility as behavioral when its CCN falls in the psychiatric range or its
    name carries a behavioral / psychiatric / BH signal.</div>
  </div>
  <div style="{cell}">
    <div style="{h3}">Behavioral Health Platforms — Ranked</div>
    {_behavioral_panel(rows)}
  </div>
  <div style="{cell}">
    <div style="{h3}">{concentration_title}</div>
    {concentration}
  </div>
  <div style="{cell}">
    <div style="{h3}">Facility-Type Mix — Whole Universe</div>
    {_type_mix_panel(m)}
  </div>
  <div style="{cell}" id="inactive">
    <div style="{h3}">Not Operating — Closed, Merged, Converted or Dark</div>
    {inactive}
    <div class="hsl-legend">HCRIS has no closed flag — a hospital leaves the
    data by not filing another cost report, and that silence is the only
    closure signal the source carries. Every facility here is excluded from
    the hospital counts, beds, revenue and behavioral counts above.
    <strong>Stopped filing</strong> = two or more years behind the corpus
    (closed, merged into another CCN, or converted — a Rural Emergency
    Hospital conversion looks the same from here).
    <strong>Dormant</strong> = one year behind, where a late filer and a
    mid-year closure are indistinguishable, so the status claims neither.
    "Last Year With Activity" reads off the full cost-report history, so a
    facility that ran until 2021 and went quiet is distinguishable from a CCN
    that never reported at all.</div>
  </div>
  <div style="{cell}">
    <div style="{h3}">Unmapped Name Families — Registry Backlog</div>
    {_candidates_panel(m)}
    <div class="hsl-legend">Two or more unmapped facilities sharing a name stem
    in one state — usually a real local system the registry does not carry yet.
    These are candidates, not assignments: a shared name stem is evidence, not
    ownership.</div>
  </div>
  <div style="background:var(--sc-panel-alt,#efeae1);border:1px solid
    var(--sc-border,#ded6c8);border-left:3px solid var(--sc-teal,#155752);
    padding:12px 16px;font-size:11px;color:var(--sc-text-dim,#5b5545);margin-bottom:16px">
    <strong style="color:var(--sc-text,#1a2332)">How to read this mapping:</strong>
    Every count on this page is the <em>operating</em> estate:
    {m.inactive_hospitals:,} of the {m.universe_facilities:,} CCNs in the HCRIS
    extract stopped filing cost reports or last filed a year behind, and they
    are held out of hospital counts, beds, revenue and behavioral counts
    alike — then listed by name above so the exclusion is auditable rather
    than a smaller number taken on faith.
    CMS publishes no parent-system field, so system membership is matched from
    the facility name (plus a state scope wherever a brand names more than one
    unrelated organization — MERCY, BAPTIST, METHODIST, SAINT LUKE'S and AURORA
    each name several). {m.mapped_hospitals:,} of {m.total_hospitals:,}
    facilities carry a matchable brand; the remaining {m.unmapped.hospitals:,}
    sit in Independent / Unmapped, which means "the name does not say", not
    "independently owned" — Community Health Systems, Tenet and Steward keep
    acquired local names almost everywhere. The mapping under-claims on purpose:
    a missing hospital is recoverable, a wrongly-attributed one is not.
  </div>
</div>"""

    body = body + ck_page_actions()
    return chartis_shell(
        body, "Health System Lookup", active_nav=ROUTE,
        editorial_intro={
            "eyebrow": "MASTER MAPPING",
            "headline": "Every health system, every hospital it runs, grouped.",
            "italic_word": "grouped",
        })
