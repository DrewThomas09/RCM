"""IFT workbook — the *qualitative + narrative* sheet set.

:mod:`ift_excel` builds the quantitative TAM→SAM→SOM data pack (the funnel, the
per-metro structure, the competitive / insourcing / moat / three-lever layers).
This companion module adds EVERYTHING ELSE the IFT work produced so the single
download is genuinely the whole study — every qualitative frame, every authored
research section, the data connectors, and the market-report narrative:

  * the taxonomy matrix (IFT vs 911 / CCT / air / NEMT) and why dedicated IFT
    competes differently;
  * the ecosystem / patient journey and the participants transport connects;
  * the health-system operating models (insource / hybrid / outsource by VOLUME),
    procurement dimensions, and pain points;
  * the company profiles (MMT the subject + the competitive field) and MMT's
    positioning pillars;
  * the competitive landscape BY PROVIDER TYPE (market-level, no company names);
  * the IBISWorld industry-structure frame (ACADEMIC, qualitative only);
  * the nine authored market-research sections (reimbursement, unit economics,
    KPIs, technology, regulatory, segmentation, sizing method, growth, evidence);
  * the data connectors (Part B / NEMT / employment hooks) + the Ambulance Fee
    Schedule ready-reckoner, hospital-occupancy demand proxy, and transport
    deal history;
  * the market-report narrative (executive summary, how-it-works, trends,
    insider lens, connections, market size, reimbursement, unit economics,
    growth, regulatory, competition, risks, diligence questions).

Same contract as :mod:`ift_excel`: stdlib-only :class:`Sheet` rows, every builder
DEGRADES (a missing analytic drops its sheet, never raises), and honesty travels
into the cells — every value/frame carries a basis (GOV / SOURCED / ACADEMIC /
ILLUSTRATIVE / FRAMEWORK), and named operators/systems are labelled PUBLIC-WEB,
not presented as data figures.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..exports.xlsx_writer import Sheet

_H = "header"
_L = "label"


def _safe(fn, default=None):
    """Call a builder, swallow any failure (degrade-never-raise)."""
    try:
        return fn()
    except Exception:  # noqa: BLE001
        return default


def _join(x: Any, sep: str = "; ") -> str:
    """Flatten a list/tuple of strings; pass a plain string through."""
    if isinstance(x, (list, tuple)):
        return sep.join(str(i) for i in x)
    return str(x) if x is not None else ""


# ── Dimension 1 — taxonomy matrix ────────────────────────────────────────────
def _taxonomy_sheet() -> Optional[Sheet]:
    from . import ift_study as _s
    tm = _safe(_s.taxonomy_matrix)
    if not (tm and getattr(tm, "available", False)):
        return None
    rows: List[List[Any]] = [
        [("IFT taxonomy — how IFT differs from 911 / CCT / air / NEMT", _H)],
        [tm.note],
        [],
        [("Dimension", _H)] + [(c, _H) for c in tm.columns],
    ]
    for dim, cells in tm.rows:
        rows.append([(dim, _L)] + list(cells))
    rows += [[], [("Why dedicated IFT competes on different dimensions", _H)],
             [("Factor", _H), ("Why it matters", _H)]]
    for name, why in tm.why_dedicated_different:
        rows.append([(name, _L), why])
    rows += [[], [("Source / basis", _H), tm.source_label]]
    return Sheet("Taxonomy", rows, col_widths=[22, 34, 34, 34, 34, 34])


# ── Dimension 2 — ecosystem / patient journey ────────────────────────────────
def _ecosystem_sheet() -> Optional[Sheet]:
    from . import ift_study as _s
    eco = _safe(_s.ecosystem)
    if not (eco and getattr(eco, "available", False)):
        return None
    rows: List[List[Any]] = [
        [("IFT ecosystem — the acute→post-acute patient journey", _H)],
        [eco.note],
        [],
        [("Site of care", _H), ("Role in the journey", _H), ("What happens", _H)],
    ]
    for site, role, desc in eco.journey:
        rows.append([(site, _L), role, desc])
    rows += [[], [("Participants IFT connects", _H)],
             [("Participant", _H), ("Role in the IFT market", _H)]]
    for name, desc in eco.participants:
        rows.append([(name, _L), desc])
    rows += [
        [],
        [("Quantitative anchors (clinical spine)", _H)],
        ["Acute-transfer scenarios modeled",
         (eco.n_acute_scenarios, "num"), "SOURCED (registry)"],
        ["Post-acute destination count (national)",
         (eco.postacute_destinations, "num"), "SOURCED (CMS rolls)"],
        [],
        [("Source / basis", _H), eco.source_label],
    ]
    return Sheet("Ecosystem & journey", rows, col_widths=[30, 30, 84])


# ── Dimension 3 — operating models / procurement / pain points ───────────────
def _operating_models_sheet() -> Optional[Sheet]:
    from . import ift_study as _s
    om = _safe(_s.operating_models)
    if not (om and getattr(om, "available", False)):
        return None
    rows: List[List[Any]] = [
        [("Health-system operating models — insource / hybrid / outsource", _H)],
        [om.classification_note],
        [],
    ]
    if om.bands:
        rows += [
            [("Operating-model bands (classified by delivered VOLUME, not assets)",
              _H)],
            [("Band", _H), ("Insourced volume share", _H), ("Definition", _H),
             ("Operating requirement", _H), ("Addressable read", _H),
             ("Example systems (PUBLIC-WEB)", _H)],
        ]
        for b in om.bands:
            share = (f"{b.volume_share_low*100:.0f}-{b.volume_share_high*100:.0f}%"
                     if isinstance(getattr(b, "volume_share_low", None),
                                   (int, float)) else "—")
            rows.append([(b.name, _L), share, b.definition,
                         b.operating_requirement, b.addressable_read,
                         _join(b.example_systems)])
    if om.biller_ceiling_pct:
        lo, ce, hi = om.biller_ceiling_pct
        rows += [
            [],
            [("Health-system-biller insource CEILING (upper bound)", _H),
             (lo, "pct"), (ce, "pct"), (hi, "pct")],
        ]
    rows += [[], [("Procurement dimensions", _H)],
             [("Dimension", _H), ("What it means", _H)]]
    for name, desc in om.procurement:
        rows.append([(name, _L), desc])
    rows += [[], [("Pain points under current models", _H)],
             [("Pain point", _H), ("Why it hurts", _H)]]
    for name, desc in om.pain_points:
        rows.append([(name, _L), desc])
    rows += [[], [("Source / basis", _H), om.source_label]]
    return Sheet("Operating models", rows, col_widths=[24, 24, 42, 40, 40, 40])


# ── Dimension 4 — company profiles ───────────────────────────────────────────
def _company_profiles_sheet() -> Optional[Sheet]:
    from . import ift_study as _s
    companies = _safe(_s.all_companies, default=[])
    if not companies:
        return None
    rows: List[List[Any]] = [
        [("Company positioning — MMT (subject) + the competitive field", _H)],
        [("Company facts are PUBLIC-WEB / company-web, named honestly — NOT a "
          "data-derived figure. In-footprint metros are a registry read over "
          "ift_geo's public operator/anchor names.")],
        [],
    ]
    for c in companies:
        tag = "SUBJECT — deep dive" if c.is_subject else c.archetype
        rows += [
            [(c.name, _H), (tag, _H)],
            [("Archetype", _L), c.archetype],
            [("HQ", _L), c.hq],
            [("Footprint", _L), c.footprint],
            [("Operating model", _L), c.operating_model],
            [("Services", _L), _join(c.services)],
            [("Customer relationships", _L), c.customer_relationships],
            [("Dedicated vs 911-EMS", _L), c.dedicated_vs_ems],
            [("Strategic role", _L), c.strategic_role],
            [("Contrast vs MMT", _L), c.mmt_contrast],
            [("In-footprint metros (registry read)", _L),
             _join(c.footprint_markets) or "—"],
            [],
        ]
    rows.append([("Basis", _H),
                 "Company facts PUBLIC-WEB; footprints a registry read over "
                 "ift_geo; archetypes match the competitive framework."])
    return Sheet("Company profiles", rows, col_widths=[30, 104])


# ── MMT positioning pillars ──────────────────────────────────────────────────
def _positioning_sheet() -> Optional[Sheet]:
    try:
        from . import ift_competitive as _c
    except Exception:  # noqa: BLE001
        return None
    mp = _safe(_c.mmt_positioning)
    if not (mp and getattr(mp, "available", False)
            and getattr(mp, "pillars", None)):
        return None
    rows: List[List[Any]] = [
        [("MMT positioning pillars — the dedicated-IFT thesis", _H)],
        [getattr(mp, "headline", "")],
        [],
        [("Pillar", _H), ("MMT stance", _H), ("vs alternatives", _H),
         ("Basis", _H)],
    ]
    for p in mp.pillars:
        rows.append([(p.pillar, _L), p.mmt_stance, p.vs_alternatives,
                     getattr(p, "basis", "ILLUSTRATIVE")])
    ref = getattr(mp, "reference_market", "")
    if ref:
        rows += [
            [],
            [("Home / reference market structure (SOURCED)", _H)],
            ["Reference market", ref],
            ["Hospitals (origins)", (getattr(mp, "home_n_hospitals", 0), "num")],
            ["Post-acute nodes", (getattr(mp, "home_n_nodes", 0), "num")],
            ["SNF beds", (getattr(mp, "home_snf_beds", 0), "num")],
            ["Density tier", getattr(mp, "home_density_tier", "—")],
        ]
    rows += [[], [("Source / basis", _H), getattr(mp, "source_label", "")]]
    return Sheet("MMT positioning", rows, col_widths=[24, 46, 46, 14])


# ── Competitive landscape by TYPE (market-level, no company names) ────────────
def _competitor_types_sheet() -> Optional[Sheet]:
    from . import ift_research as _r
    ct = _safe(_r.competitor_types)
    if not (ct and getattr(ct, "available", False) and ct.rows):
        return None
    rows: List[List[Any]] = [
        [("Competitive landscape by provider TYPE (market-level)", _H)],
        [("Type-level only — company-specific positioning lives on the Company "
          "profiles sheet. No company names here.")],
        [],
        [(c, _H) for c in ct.columns],
    ]
    for r in ct.rows:
        rows.append([(r[0], _L)] + list(r[1:]))
    rows += [[], [("Source / basis", _H), ct.source_label]]
    return Sheet("Competitor types", rows, col_widths=[26, 40, 44, 44])


# ── Industry-structure frame (IBISWorld, ACADEMIC, qualitative only) ──────────
def _industry_context_sheet() -> Optional[Sheet]:
    from . import ift_research as _r
    ic = _safe(_r.industry_context)
    if not (ic and getattr(ic, "available", False) and ic.items):
        return None
    rows: List[List[Any]] = [
        [("Industry-structure frame — IBISWorld 'Ambulance Services in the US'",
          _H)],
        [("ACADEMIC · qualitative market-structure frame ONLY — no numeric series "
          "taken from the report (its charts are images); figures use our "
          "GOV/market-research anchors.")],
        [],
        [("Theme", _H), ("Industry frame", _H)],
    ]
    for theme, text in ic.items:
        rows.append([(theme, _L), text])
    rows += [[], [("Source / basis", _H), ic.source_label]]
    return Sheet("Industry context", rows, col_widths=[26, 104])


# ── The nine authored research sections (generic converter) ───────────────────
# Short, clean tab names per section id (the full titles truncate mid-word at 31).
_RESEARCH_TAB_NAMES: Dict[str, str] = {
    "reimbursement": "R· Reimbursement",
    "unit-economics": "R· Unit economics",
    "kpis": "R· KPIs & metrics",
    "technology": "R· Technology & data",
    "regulatory": "R· Regulatory",
    "segmentation": "R· Segmentation",
    "sizing": "R· Sizing method",
    "growth": "R· Growth & headwinds",
    "evidence": "R· Evidence quality",
}


def _research_section_sheet(sec: Dict[str, Any]) -> Optional[Sheet]:
    """Convert one authored research section (id/title/intro/subsections) into a
    Sheet. Each subsection is a table (columns+rows) or a bullet list, and carries
    its own basis chip + source line. Never raises."""
    if not isinstance(sec, dict) or not sec.get("subsections"):
        return None
    subs = sec["subsections"]
    n_cols = 1
    for ss in subs:
        cols = ss.get("columns") or []
        n_cols = max(n_cols, len(cols))
    n_cols = max(2, min(n_cols, 6))
    rows: List[List[Any]] = [
        [(sec.get("title", "Research section"), _H)],
        [sec.get("intro", "")],
        [],
    ]
    for ss in subs:
        basis = ss.get("basis", "")
        rows.append([(ss.get("heading", ""), _H), (basis, _H)])
        src = ss.get("source")
        if src:
            rows.append(["Source: " + str(src)])
        if ss.get("kind") == "table" and ss.get("columns"):
            rows.append([(c, _H) for c in ss["columns"]])
            for r in ss.get("rows", []):
                cells = list(r)
                # lead cell as a label so the row reads as a keyed record
                rows.append([(cells[0], _L)] + [str(c) for c in cells[1:]])
        else:
            for b in ss.get("bullets", []):
                rows.append(["• " + str(b)])
        rows.append([])
    widths = [34] + [42] * (n_cols - 1)
    name = _RESEARCH_TAB_NAMES.get(
        sec.get("id", ""), "R· " + str(sec.get("title", "section")))
    return Sheet(name[:31], rows, col_widths=widths)


def _research_sheets() -> List[Sheet]:
    from . import ift_research as _r
    secs = _safe(_r.research_sections, default=[]) or []
    out: List[Sheet] = []
    for sec in secs:
        sh = _safe(lambda sec=sec: _research_section_sheet(sec))
        if sh is not None:
            out.append(sh)
    return out


# ── Data connectors (network-gated hooks + fallback GOV citations) ────────────
def _connectors_sheet() -> Optional[Sheet]:
    from . import ift_analytics as _an
    probes = [
        ("Medicare Part B ambulance utilization (A0426-A0436)",
         _safe(_an.ambulance_part_b_utilization)),
        ("Medicaid NEMT state coverage", _safe(_an.nemt_state_coverage)),
        ("BLS QCEW ambulance employment (NAICS 621910)",
         _safe(_an.ambulance_employment)),
    ]
    probes = [(n, p) for n, p in probes if p is not None]
    if not probes:
        return None
    rows: List[List[Any]] = [
        [("Data connectors — network-gated hooks (ingest-ready) + fallbacks", _H)],
        [("Offline these read 'network-gated' and cite an honest GOV/ILLUSTRATIVE "
          "fallback — never a fabricated number. The wiring is real; the label "
          "flips to SOURCED once the estate is ingested.")],
        [],
        [("Connector", _H), ("Dataset id", _H), ("Status", _H), ("Rows", _H),
         ("Source / fallback citation", _H), ("Note", _H)],
    ]
    for name, cr in probes:
        status = "available (SOURCED)" if cr.available else "network-gated offline"
        cite = cr.source_label if cr.available else (cr.fallback_citation
                                                     or cr.source_label)
        rows.append([(name, _L), cr.dataset_id, status,
                     (len(cr.rows), "num"), cite, cr.note])
    return Sheet("Connectors", rows, col_widths=[38, 42, 22, 8, 60, 60])


# ── Ambulance Fee Schedule ready-reckoner (RVU GOV × CF → worked base) ────────
def _fee_schedule_sheet() -> Optional[Sheet]:
    from . import ift_analytics as _an
    fs = _safe(_an.fee_schedule)
    if not (fs and getattr(fs, "available", False) and fs.rows):
        return None
    rows: List[List[Any]] = [
        [("Medicare Ambulance Fee Schedule ready-reckoner", _H)],
        [fs.note],
        [],
        [("HCPCS", _H), ("Level of service", _H), ("RVU (GOV)", _H),
         (f"Base @ CF ${fs.conversion_factor:,.0f} (ILLUSTRATIVE)", _H),
         ("× BLS", _H)],
    ]
    bls = next((r.rvu for r in fs.rows if r.rvu), 1.0) or 1.0
    for r in fs.rows:
        rows.append([r.hcpcs, r.level, (r.rvu, "num2"),
                     (r.base_rate, "money2"), (round(r.rvu / bls, 2), "mult")])
    rows += [
        [],
        [("RVU basis", _H), fs.rvu_source_label],
        [("Rate basis", _H), fs.rate_source_label],
    ]
    return Sheet("Fee schedule", rows, col_widths=[10, 32, 12, 30, 8])


# ── Hospital occupancy — the transfer-demand engine (SOURCED, HCRIS) ──────────
def _occupancy_sheet() -> Optional[Sheet]:
    from . import ift_analytics as _an
    trend = _safe(_an.occupancy_trend)
    state = _safe(_an.occupancy_by_state)
    have_trend = trend and getattr(trend, "available", False) and trend.points
    have_state = state and getattr(state, "available", False) and state.rows
    if not (have_trend or have_state):
        return None
    rows: List[List[Any]] = [
        [("Hospital inpatient occupancy — the transfer-demand engine", _H)],
    ]
    if have_trend:
        rows += [
            [trend.takeaway],
            [],
            [("National occupancy by fiscal year (SOURCED · HCRIS)", _H)],
            [("Fiscal year", _H), ("Inpatient occupancy", _H), ("Filers", _H)],
        ]
        for fy, occ in trend.points:
            rows.append([(fy, "num"), (occ, "pct"),
                         (trend.n_by_year.get(fy, 0), "num")])
    if have_state:
        rows += [
            [],
            [(f"Tightest-census states (FY{state.fiscal_year}) — the tightest "
              "transfer markets", _H)],
            [("State", _H), ("Inpatient occupancy", _H), ("Filers", _H)],
        ]
        for r in state.rows:
            rows.append([r.state, (r.occupancy, "pct"), (r.n_filers, "num")])
        if getattr(state, "insight", ""):
            rows += [[], [("Read", _H), state.insight]]
    src = (trend.source_label if have_trend else state.source_label)
    rows += [[], [("Source / basis", _H), src]]
    return Sheet("Occupancy demand", rows, col_widths=[16, 20, 12])


# ── Transport deal history (SOURCED corpus) ──────────────────────────────────
def _deal_history_sheet() -> Optional[Sheet]:
    from . import ift_analytics as _an
    dh = _safe(_an.transport_deal_history)
    if not (dh and getattr(dh, "available", False)):
        return None
    rows: List[List[Any]] = [
        [("Transport deal history — EMS + NEMT + air-medical union", _H)],
        [dh.note],
        [],
        [("Metric", _H), ("Value", _H)],
        [("Deals in corpus", _L), (dh.n_deals, "num")],
        [("Realized (with MOIC)", _L), (dh.n_realized, "num")],
        [("Median realized MOIC", _L),
         (dh.median_moic, "mult") if dh.median_moic is not None else "—"],
        [("Median entry EV/EBITDA", _L),
         (dh.median_entry_multiple, "mult")
         if dh.median_entry_multiple is not None else "—"],
        [("Entry-multiple sample (n)", _L), (dh.entry_multiple_n, "num")],
        [("Year range", _L),
         (f"{dh.year_min}-{dh.year_max}" if dh.year_min else "—")],
    ]
    if dh.deal_names:
        rows += [[], [("Deals (public names)", _H)]]
        for nm in dh.deal_names:
            if nm:
                rows.append([nm])
    rows += [[], [("Source / basis", _H), dh.source_label]]
    return Sheet("Deal history", rows, col_widths=[30, 60])


# ── Market-report narrative (from the MarketReport for interfacility_transport) ─
def _report():
    try:
        from . import report_for
        return report_for("interfacility_transport")
    except Exception:  # noqa: BLE001
        return None


def _report_narrative_sheet() -> Optional[Sheet]:
    r = _report()
    if r is None:
        return None
    rows: List[List[Any]] = [
        [("IFT market report — narrative findings", _H)],
        [],
        [("Executive summary", _H)],
    ]
    for x in getattr(r, "executive_summary", []) or []:
        rows.append(["• " + str(x)])
    hiw = getattr(r, "how_it_works", None)
    if hiw is not None:
        rows += [[], [("How it works — value chain", _H)]]
        for x in getattr(hiw, "value_chain", []) or []:
            rows.append(["• " + str(x)])
        rows += [
            [],
            [("Money flow", _H)], [getattr(hiw, "money_flow", "")],
            [("Key players", _H)], [getattr(hiw, "key_players", "")],
            [], [("Sites of care", _H)],
        ]
        for x in getattr(hiw, "sites_of_care", []) or []:
            rows.append(["• " + str(x)])
    trends = getattr(r, "trends", "")
    if trends:
        rows += [[], [("Trends", _H)], [trends]]
    lens = getattr(r, "insider_lens", []) or []
    if lens:
        rows += [[], [("Insider lens — what operators know, outsiders miss", _H)]]
        for x in lens:
            rows.append(["• " + str(x)])
    conns = getattr(r, "connections", []) or []
    if conns:
        rows += [[], [("Connections — where IFT touches the rest of the platform",
                       _H)]]
        for x in conns:
            rows.append(["• " + str(x)])
    return Sheet("Report narrative", rows, col_widths=[122])


def _report_economics_sheet() -> Optional[Sheet]:
    r = _report()
    if r is None:
        return None
    rows: List[List[Any]] = [
        [("IFT market report — size, reimbursement, unit economics, growth", _H)],
        [],
    ]
    ms = getattr(r, "market_size", None)
    if ms is not None:
        rows += [[("Market size — segments", _H)],
                 [("Segment", _H), ("Value", _H), ("Source / basis", _H)]]
        for s in getattr(ms, "segments", []) or []:
            rows.append([(s.name, _L), s.value, s.source_label])
        gds = getattr(ms, "growth_drivers", []) or []
        if gds:
            rows += [[("Growth drivers", _H)]]
            for x in gds:
                rows.append(["• " + str(x)])
        rows.append([])
    rb = getattr(r, "reimbursement", None)
    if rb is not None:
        rows += [[("Reimbursement — payer mix (ILLUSTRATIVE, modeled)", _H)],
                 [("Payer", _H), ("Share", _H)]]
        pm = getattr(rb, "payer_mix", {}) or {}
        for k, v in pm.items():
            rows.append([(k, _L), (v, "pct") if isinstance(v, (int, float)) else v])
        rm = getattr(rb, "rate_mechanics", []) or []
        if rm:
            rows += [[("Rate mechanics", _H)]]
            for x in rm:
                rows.append(["• " + str(x)])
        risk = getattr(rb, "reimbursement_risk", "")
        if risk:
            rows += [[("Reimbursement risk", _H)], [risk]]
        rows.append([])
    ue = getattr(r, "unit_economics", None)
    if ue is not None:
        rows += [[("Unit economics — KPIs", _H)],
                 [("Metric", _H), ("Typical range", _H), ("Why it matters", _H)]]
        for k in getattr(ue, "kpis", []) or []:
            rows.append([(k.metric, _L), k.typical_range, k.why])
        mp = getattr(ue, "margin_profile", "")
        if mp:
            rows += [[("Margin profile", _H)], [mp]]
        rows.append([])
    cds = getattr(r, "cost_drivers", []) or []
    if cds:
        rows += [[("Cost drivers", _H)],
                 [("Driver", _H), ("Share / rank", _H), ("Basis", _H),
                  ("Note", _H)]]
        for cd in cds:
            rows.append([(cd.driver, _L), cd.share_or_rank, cd.basis, cd.note])
        rows.append([])
    gls = getattr(r, "growth_levers", []) or []
    if gls:
        rows += [[("Growth levers", _H)],
                 [("Lever", _H), ("Mechanism", _H), ("Magnitude", _H),
                  ("Basis", _H)]]
        for gl in gls:
            rows.append([(gl.lever, _L), gl.mechanism, gl.magnitude, gl.basis])
    vd = getattr(r, "volume_growth_driver", None)
    if vd is not None:
        rows += [
            [], [("Volume growth driver", _H)],
            [("Driver", _L), getattr(vd, "driver", "")],
            [("Analysis", _L), getattr(vd, "analysis", "")],
            [("Basis", _L), getattr(vd, "basis", "")],
        ]
    return Sheet("Report economics", rows, col_widths=[30, 42, 42, 24])


def _report_regrisk_sheet() -> Optional[Sheet]:
    r = _report()
    if r is None:
        return None
    rows: List[List[Any]] = [
        [("IFT market report — regulatory, competition, risks, diligence", _H)],
        [],
    ]
    reg = getattr(r, "regulatory", None)
    if reg is not None:
        rows += [[("Regulatory rules", _H)],
                 [("Rule", _H), ("Why it matters", _H), ("Source", _H)]]
        for rule in getattr(reg, "rules", []) or []:
            rows.append([(rule.name, _L), rule.why_it_matters, rule.source_url])
        pw = getattr(reg, "policy_watch", []) or []
        if pw:
            rows += [[("Policy watch", _H)]]
            for x in pw:
                rows.append(["• " + str(x)])
        rows.append([])
    comp = getattr(r, "competition", None)
    if comp is not None:
        rows += [
            [("Competition", _H)],
            [("Fragmentation", _L), getattr(comp, "fragmentation", "")],
            [("Consolidation", _L), getattr(comp, "consolidation", "")],
            [("PE activity", _L), getattr(comp, "pe_activity", "")],
            [("HHI / share", _L), getattr(comp, "hhi_or_share", "")],
        ]
        np_ = getattr(comp, "notable_players", []) or []
        if np_:
            rows += [[("Notable players (PUBLIC-WEB)", _H)]]
            for x in np_:
                rows.append(["• " + str(x)])
        rows.append([])
    risks = getattr(r, "risks", []) or []
    if risks:
        rows += [[("Risks", _H)]]
        for x in risks:
            rows.append(["• " + str(x)])
        rows.append([])
    dqs = getattr(r, "diligence_questions", []) or []
    if dqs:
        rows += [[("Diligence questions", _H)]]
        for x in dqs:
            rows.append(["• " + str(x)])
    return Sheet("Report reg & risk", rows, col_widths=[30, 66, 40])


# ── public entry point ───────────────────────────────────────────────────────
def extra_sheets() -> List[Sheet]:
    """Every qualitative / narrative / connector / research sheet, in reading
    order. Each builder degrades to skipped (never raises), so the caller can
    append the result unconditionally."""
    out: List[Sheet] = []
    singles = [
        _taxonomy_sheet, _ecosystem_sheet, _operating_models_sheet,
        _company_profiles_sheet, _positioning_sheet, _competitor_types_sheet,
        _industry_context_sheet,
    ]
    for b in singles:
        s = _safe(b)
        if s is not None:
            out.append(s)
    out.extend(_safe(_research_sheets, default=[]) or [])
    for b in (_connectors_sheet, _fee_schedule_sheet, _occupancy_sheet,
              _deal_history_sheet, _report_narrative_sheet,
              _report_economics_sheet, _report_regrisk_sheet):
        s = _safe(b)
        if s is not None:
            out.append(s)
    return out
