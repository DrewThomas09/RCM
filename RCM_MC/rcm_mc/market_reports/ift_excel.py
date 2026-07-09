"""IFT market-study workbook — every sourced figure, by market, in one download.

The MMT investor market study needs an *investor-ready* data pack: the full
TAM -> SAM -> SOM build, every target metro's SOURCED facility structure and
per-market sizing, the clinical demand spine, and the competitive / insourcing /
moat / three-lever layers — all in a single Excel a buyer can audit.

Built on the stdlib-only :mod:`rcm_mc.exports.xlsx_writer` (``Sheet`` +
``write_xlsx``) so it adds NO runtime dependency. Every function degrades — a
missing analytic drops its sheet rather than raising — because the workbook must
always download, even offline where a network-gated connector is dark.

Honesty travels into the workbook: every value-bearing sheet carries a
``Basis`` column (GOV / SOURCED / ACADEMIC / ILLUSTRATIVE) and the Provenance
sheet spells out what is real vs modeled — the same contract the pages enforce.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..exports.xlsx_writer import Sheet, write_xlsx, Link
from . import ift_analytics as _an
from . import ift_clinical_demand as _cd
from . import ift_geo

_H = "header"


# ── helpers ──────────────────────────────────────────────────────────────────
def _bn_to_dollars(bn: Optional[float]) -> Optional[float]:
    """A $B figure -> raw dollars for the ``money`` number format. None-safe."""
    try:
        return float(bn) * 1e9
    except (TypeError, ValueError):
        return None


def _safe(fn, default=None):
    """Call an analytic, swallow any failure (degrade-never-raise)."""
    try:
        return fn()
    except Exception:  # noqa: BLE001
        return default


# ── Overview / funnel ────────────────────────────────────────────────────────
def _overview_sheet() -> Sheet:
    tam = _safe(_an.ground_tam)
    hs = _safe(_an.health_system_sam)
    som = _safe(_an.sam_formula)
    rows: List[List[Any]] = [
        [("Interfacility Transport (IFT) — MMT market study data pack", _H)],
        [("What IFT is: medically-supervised ground ambulance transport BETWEEN "
          "healthcare facilities, ordered by hospitals/health systems.")],
        [("What IFT is NOT: 911 / scene response, NEMT (wheelchair van / livery), "
          "air ambulance, or generic medical logistics — all EXCLUDED.")],
        [],
        [("The funnel", _H), ("Value", _H), ("Basis", _H), ("Definition", _H)],
    ]
    if tam and getattr(tam, "available", False):
        rows.append(["TAM — all US ground IFT",
                     (_bn_to_dollars(tam.allpayer_tam_bn_central), "money"),
                     "ILLUSTRATIVE",
                     "All ground interfacility ambulance missions, all-payer, "
                     "ex-911 / ex-air / ex-NEMT (GOV-anchored, modeled build)."])
    if hs and getattr(hs, "available", False):
        rows.append(["SAM — multi-hospital health systems",
                     (_bn_to_dollars(hs.sam_central_bn), "money"), "ILLUSTRATIVE",
                     "The structural addressable market: multi-hospital-health-"
                     "system IFT an outsourced operator can win (top-down ratio x "
                     "bottoms-up structure, triangulated)."])
    if som and getattr(som, "available", False):
        rows.append(["SOM — operator footprint (current markets)",
                     (som.sam_dollars_central, "money"), "ILLUSTRATIVE",
                     "Serviceable-obtainable in the operator's current metros — "
                     "bottom-up from the real facility structure."])
    if hs and getattr(hs, "available", False):
        rows += [
            [],
            ["Operator current share of SAM (nascent)",
             (hs.operator_share_of_sam, "pct"), "ILLUSTRATIVE",
             "The ~1% nascent share (MMT framing)."],
            ["SAM / SOM headroom multiple",
             ((hs.sam_over_som_multiple, "mult")
              if hs.sam_over_som_multiple else "—"), "ILLUSTRATIVE",
             "Structural headroom beyond the current footprint."],
        ]
    return Sheet("Overview", rows, col_widths=[42, 20, 14, 70])


# ── TAM build ────────────────────────────────────────────────────────────────
def _tam_sheet() -> Optional[Sheet]:
    tam = _safe(_an.ground_tam)
    if not (tam and getattr(tam, "available", False)):
        return None
    rows: List[List[Any]] = [
        [("TAM build — US ground interfacility ambulance (top-down)", _H)],
        [tam.headline],
        [],
        [("Build step", _H), ("Value", _H), ("Basis", _H), ("Detail", _H)],
    ]
    for s in tam.steps:
        rows.append([s.label, s.value, s.basis, s.detail])
    rows += [[], [("Explicitly EXCLUDED from TAM", _H)]]
    for x in tam.exclusions:
        rows.append([x])
    rows += [[], [("Source", _H), tam.source_label], [("Note", _H), tam.note]]
    return Sheet("TAM build", rows, col_widths=[46, 24, 14, 80])


# ── SAM (health systems) ─────────────────────────────────────────────────────
def _sam_sheet() -> Optional[Sheet]:
    hs = _safe(_an.health_system_sam)
    if not (hs and getattr(hs, "available", False)):
        return None
    rows: List[List[Any]] = [
        [("SAM — multi-hospital health systems (structural, two ways)", _H)],
        [hs.headline],
        [],
        [("Method / step", _H), ("Value", _H), ("Basis", _H), ("Detail", _H)],
    ]
    for s in hs.steps:
        rows.append([s.label, s.value, s.basis, s.detail])
    rows += [
        [],
        [("Lever", _H), ("Low", _H), ("Central", _H), ("High", _H), ("Basis", _H)],
        ["Multi-hospital-system share of IFT $",
         (hs.multi_system_ift_share[0], "pct"),
         (hs.multi_system_ift_share[1], "pct"),
         (hs.multi_system_ift_share[2], "pct"), "ILLUSTRATIVE"],
        ["Health-system-biller insource ceiling",
         (hs.insource_ceiling[0], "pct"), (hs.insource_ceiling[1], "pct"),
         (hs.insource_ceiling[2], "pct"), "ILLUSTRATIVE"],
        ["Addressable (outsourceable) share",
         (hs.addressable_share[0], "pct"), (hs.addressable_share[1], "pct"),
         (hs.addressable_share[2], "pct"), "ILLUSTRATIVE"],
        [],
        [("SAM top-down ($B)", _H), (hs.sam_td_central_bn, "num2"),
         ("MSA-restricted", _H), (hs.sam_td_msa_central_bn, "num2")],
        [("SAM bottoms-up ($B)", _H),
         ((hs.sam_bu_central_bn, "num2") if hs.sam_bu_central_bn else "—")],
        [("SAM triangulated ($B)", _H), (hs.sam_central_bn, "num2"),
         ("range", _H), (hs.sam_low_bn, "num2"), (hs.sam_high_bn, "num2")],
        [],
        [("Source", _H), hs.source_label], [("Note", _H), hs.note],
    ]
    return Sheet("SAM health systems", rows, col_widths=[42, 16, 16, 16, 14])


# ── SOM footprint (rollup + per-metro) ───────────────────────────────────────
def _som_sheet() -> Optional[Sheet]:
    som = _safe(_an.sam_formula)
    roll = _safe(ift_geo.footprint_rollup)
    if not (som and getattr(som, "available", False)):
        return None
    rows: List[List[Any]] = [
        [("SOM — operator footprint, serviceable-obtainable (bottom-up)", _H)],
    ]
    if roll and getattr(roll, "available", False):
        rows += [
            [("Footprint at a glance (SOURCED)", _H)],
            ["Target metros", (roll.n_metros, "num"),
             "State regions", (roll.n_regions, "num")],
            ["Hospitals (origins)", (roll.n_hospitals, "num"),
             "HCRIS beds", (roll.hcris_beds, "num")],
            ["SNFs", (roll.n_snf, "num"), "SNF beds", (roll.snf_beds, "num")],
            ["IRFs", (roll.n_irf, "num"), "LTCHs", (roll.n_ltch, "num")],
            ["Hospices", (roll.n_hospice, "num"),
             "Home-health", (roll.n_home_health, "num")],
            ["Dialysis", (roll.n_dialysis, "num")],
            [],
        ]
    rows += [
        [("SOM $ central", _H), (som.sam_dollars_central, "money"),
         ("low", _H), (som.sam_dollars_low, "money"),
         ("high", _H), (som.sam_dollars_high, "money")],
        ["Ground-IFT demand missions/yr", (som.total_demand_missions, "num")],
        ["Serviceable missions/yr", (som.total_serviceable_missions, "num")],
        [],
        [("Per-metro serviceable market (SOURCED structure x ILLUSTRATIVE levers)",
          _H)],
        [("Metro", _H), ("Region", _H), ("HCRIS beds", _H),
         ("Discharge base", _H), ("SNF beds", _H), ("Demand mis/yr", _H),
         ("s(m)", _H), ("$/transport", _H), ("Serv. mis/yr", _H),
         ("SOM $", _H)],
    ]
    for r in som.rows:
        rows.append([
            r.name, r.region_label, (r.hcris_beds, "num"),
            (r.discharge_base, "num"), (r.snf_beds, "num"),
            (r.demand_missions, "num"), (r.serviceable_share, "pct"),
            (r.revenue_per_transport, "money"), (r.serviceable_missions, "num"),
            (r.sam_dollars, "money")])
    rows += [[], [("Source", _H), som.source_label]]
    return Sheet("SOM footprint", rows,
                 col_widths=[22, 20, 12, 14, 10, 14, 8, 13, 12, 16])


# ── Per-metro structure (all facility counts) ────────────────────────────────
def _structure_sheet() -> Optional[Sheet]:
    if not getattr(ift_geo, "MARKETS", None):
        return None
    rows: List[List[Any]] = [
        [("Target markets — SOURCED facility structure", _H)],
        [("Facility counts from the vendored CMS provider rolls + HCRIS beds; "
          "anchor systems / operators are public/company-web, named honestly.")],
        [],
        [("Metro", _H), ("Region", _H), ("States", _H), ("Profile", _H),
         ("Rural", _H), ("Hospitals", _H), ("HCRIS beds", _H), ("SNF", _H),
         ("SNF beds", _H), ("IRF", _H), ("LTCH", _H), ("Hospice", _H),
         ("HomeHealth", _H), ("Dialysis", _H), ("Post-acute nodes", _H),
         ("Density tier", _H)],
    ]
    for md in ift_geo.MARKETS:
        st = _safe(lambda md=md: ift_geo.metro_structure(md.name))
        if not (st and getattr(st, "available", False)):
            rows.append([md.name, md.region_label, "/".join(md.states),
                         md.profile, "yes" if md.rural else "no",
                         "—", "—", "—", "—", "—", "—", "—", "—", "—", "—", "—"])
            continue
        rows.append([
            st.name, st.region_label, "/".join(st.states), st.profile,
            "yes" if st.rural else "no", (st.n_hospitals, "num"),
            (st.hcris_beds, "num"), (st.n_snf, "num"), (st.snf_beds, "num"),
            (st.n_irf, "num"), (st.n_ltch, "num"), (st.n_hospice, "num"),
            (st.n_home_health, "num"), (st.n_dialysis, "num"),
            (st.n_postacute_destinations, "num"), st.density_tier])
    return Sheet("Markets structure", rows,
                 col_widths=[22, 18, 8, 16, 7, 10, 11, 7, 9, 6, 6, 8, 11, 9, 14, 12])


# ── Per-metro qualitative read (anchors / operators / insource / moat) ───────
def _markets_read_sheet() -> Optional[Sheet]:
    if not getattr(ift_geo, "MARKETS", None):
        return None
    rows: List[List[Any]] = [
        [("Target markets — anchor systems, operators, insource & moat read", _H)],
        [("Anchor systems + named operators are PUBLIC / company-web knowledge, "
          "named honestly; the reads are analyst knowledge, not our data.")],
        [],
        [("Metro", _H), ("Anchor health systems", _H), ("Named operators", _H),
         ("Insource-vs-outsource read", _H), ("Moat note", _H)],
    ]
    for md in ift_geo.MARKETS:
        rows.append([
            md.name, "; ".join(md.anchor_systems), "; ".join(md.named_operators),
            md.insource_read, md.moat_note])
    return Sheet("Markets read", rows, col_widths=[20, 46, 40, 60, 60])


# ── Clinical demand (cases -> codes -> volume -> growth) ─────────────────────
def _clinical_sheet() -> Optional[Sheet]:
    conds = _safe(_cd.all_conditions, default=[])
    if not conds:
        return None
    rows: List[List[Any]] = [
        [("Clinical demand — acute transfers (cases -> codes -> volume -> growth)",
          _H)],
        [("A ground-IFT operator's volume equals the acute patients who must move "
          "between facilities. Volumes are published (GOV/ACADEMIC); growth is the "
          "demographic CAGR (ILLUSTRATIVE, named basis).")],
        [],
        [("Condition", _H), ("Family", _H), ("Transfer type", _H),
         ("ICD-10-CM", _H), ("MS-DRG", _H), ("Destination capability", _H),
         ("National volume/yr", _H), ("Measure", _H), ("Volume basis", _H),
         ("Growth CAGR", _H), ("Growth drivers", _H)],
    ]
    for c in conds:
        icd = ", ".join(c.icd10) if c.icd10 else ""
        drg = ", ".join(c.ms_drg) if c.ms_drg else ""
        nv = c.national_volume
        # honesty tag is the leading token of the volume's source_label
        vbasis = (nv.source_label.split()[0] if nv and nv.source_label else "")
        vol = (nv.value if nv and nv.value else 0)
        rows.append([
            c.name, c.family, c.transfer_type, icd, drg,
            c.destination_capability,
            (vol, "num") if vol else "not separately enumerated",
            (nv.measure if nv else ""), vbasis,
            (c.growth.cagr, "pct") if c.growth else "—",
            (c.growth.drivers if c.growth else "")])
    return Sheet("Clinical demand", rows,
                 col_widths=[28, 14, 20, 22, 16, 26, 16, 22, 12, 11, 40])


# ── Destination supply (post-acute counts) ───────────────────────────────────
def _supply_sheet() -> Optional[Sheet]:
    sup = _safe(_cd.destination_supply)
    if not sup or not isinstance(sup, dict):
        return None
    rows: List[List[Any]] = [
        [("Destination supply — real post-acute destination counts (SOURCED)", _H)],
        [],
        [("Destination setting", _H), ("Count", _H), ("Basis", _H)],
    ]
    settings = sup.get("by_setting") or sup.get("settings") or sup
    if isinstance(settings, dict):
        for k, v in settings.items():
            if isinstance(v, (int, float)):
                rows.append([str(k), (v, "num"), "SOURCED"])
            elif isinstance(v, dict) and "count" in v:
                rows.append([str(k), (v["count"], "num"),
                             v.get("basis", "SOURCED")])
    return Sheet("Destination supply", rows, col_widths=[36, 14, 14])


# ── Provenance / honesty legend ──────────────────────────────────────────────
def _provenance_sheet() -> Sheet:
    rows: List[List[Any]] = [
        [("Provenance & honesty legend", _H)],
        [],
        [("Basis label", _H), ("Meaning", _H)],
        ["GOV", "A published government figure (CMS, MedPAC, MACPAC, Census, BLS)."],
        ["SOURCED", "Computed from our vendored data (CMS provider CSVs, HCRIS, "
                    "the target-market facility structure)."],
        ["ACADEMIC", "A published epidemiologic / academic estimate."],
        ["ILLUSTRATIVE", "Modeled with a named basis — a ratio, share, score, or "
                         "index we assume, never a filed figure."],
        [],
        [("What is real vs modeled", _H)],
        ["Real (SOURCED/GOV)", "Facility counts & beds (CMS/HCRIS), occupancy, the "
         "Medicare ambulance fee schedule RVUs + AIF, published transfer volumes."],
        ["Modeled (ILLUSTRATIVE)", "Every dollar of TAM/SAM/SOM, the serviceable "
         "shares s(m), the insource ceiling, growth composites, moat scores, and "
         "the claims gross-up — each carries a named basis."],
        [],
        ["Boundary", "TAM = all US GROUND IFT only. It excludes 911/scene, air "
         "ambulance, and NEMT — reading a whole-ambulance or NEMT number as the "
         "prize is the single biggest sizing error."],
    ]
    return Sheet("Provenance", rows, col_widths=[24, 96])


# ── new-module sheets (competitive / insourcing / moat / tracking) ───────────
# Filled in once ift_competitive / ift_insourcing / ift_moat / ift_tracking land;
# each degrades to None (sheet skipped) until then, so the workbook always builds.
def _competitive_sheet() -> Optional[Sheet]:
    try:
        from . import ift_competitive as _c
    except Exception:  # noqa: BLE001
        return None
    arch = _safe(_c.competitive_archetypes)
    comp = _safe(_c.market_competition)
    pos = _safe(_c.mmt_positioning)
    if not (arch and getattr(arch, "archetypes", None)):
        return None

    def _op(o):
        # OperatorPresence -> "Name (archetype)"; plain strings pass through.
        nm = getattr(o, "operator", None)
        if nm is None:
            return str(o)
        lbl = getattr(o, "archetype_label", "")
        return f"{nm} ({lbl})" if lbl else str(nm)

    def _join(x):
        if isinstance(x, (list, tuple)):
            return "; ".join(_op(i) for i in x)
        return x or ""

    rows: List[List[Any]] = [
        [("Competitive landscape — archetypes, MMT positioning, per-market", _H)],
        [("Operator names are public/company-web, named honestly; scale magnitudes "
          "and shares are ILLUSTRATIVE; node density is SOURCED.")],
        [],
        [("Archetype", _H), ("IFT posture", _H), ("Scale", _H),
         ("Example operators", _H), ("Pros", _H), ("Cons", _H),
         ("MMT advantage", _H)],
    ]
    for a in arch.archetypes:
        rows.append([a.name, a.ift_posture, a.scale_magnitude,
                     _join(a.example_operators), _join(a.pros), _join(a.cons),
                     a.mmt_advantage])
    if pos and getattr(pos, "pillars", None):
        rows += [[], [("MMT positioning pillar", _H), ("MMT stance", _H),
                      ("vs alternatives", _H)]]
        for p in pos.pillars:
            rows.append([p.pillar, p.mmt_stance, p.vs_alternatives])
    if comp and getattr(comp, "rows", None):
        rows += [
            [],
            [("Per-market competition", _H)],
            [("Metro", _H), ("Region", _H), ("Named operators", _H),
             ("Archetype mix", _H), ("MMT present", _H), ("First-call today", _H),
             ("Contestability", _H), ("Nodes", _H), ("Density tier", _H)],
        ]
        def _mix(m):
            # archetype_mix is a tuple of (label, count) pairs.
            try:
                return "; ".join(f"{lbl} x{n}" for lbl, n in m)
            except (TypeError, ValueError):
                return _join(m)

        for r in comp.rows:
            rows.append([r.name, r.region_label, _join(r.operators),
                         _mix(r.archetype_mix), "yes" if r.mmt_present else "no",
                         r.first_call_today, r.contestability_tier,
                         (r.n_nodes, "num"), r.density_tier])
    return Sheet("Competitive", rows, col_widths=[22, 18, 16, 40, 40, 40, 44])


def _insourcing_sheet() -> Optional[Sheet]:
    try:
        from . import ift_insourcing as _i
    except Exception:  # noqa: BLE001
        return None
    fw = _safe(_i.insourcing_framework)
    proxy = _safe(_i.biller_proxy)
    gross = _safe(_i.claims_grossup)
    mkt = _safe(_i.market_insourcing)
    if not (fw and getattr(fw, "bands", None)):
        return None
    rows: List[List[Any]] = [
        [("Insource vs outsource — by transport VOLUME, not asset ownership", _H)],
        [(fw.classification_axis if getattr(fw, "classification_axis", "") else
          "A system that owns a few ambulances but outsources most IFT is HYBRID, "
          "not insourced — classify by transport volume share.")],
        [],
        [("Band", _H), ("Insourced volume share", _H), ("Definition", _H),
         ("Operating requirement", _H), ("Addressable read", _H),
         ("Example systems", _H)],
    ]
    for b in fw.bands:
        share = f"{b.volume_share_low*100:.0f}-{b.volume_share_high*100:.0f}%"
        ex = "; ".join(b.example_systems) if isinstance(b.example_systems, (list, tuple)) else (b.example_systems or "")
        rows.append([b.name, share, b.definition, b.operating_requirement,
                     b.addressable_read, ex])
    if proxy and getattr(proxy, "available", False):
        rows += [
            [],
            [("Health-system-biller proxy = the insource UPPER BOUND", _H)],
            [proxy.proxy_rule],
            [("Insource ceiling", _H), (proxy.ceiling_low, "pct"),
             (proxy.ceiling_central, "pct"), (proxy.ceiling_high, "pct")],
            [("Addressable (1 - ceiling)", _H), (proxy.addressable_low, "pct"),
             (proxy.addressable_central, "pct"), (proxy.addressable_high, "pct")],
            [("Limitations", _H), proxy.limitations],
        ]
    if gross and getattr(gross, "available", False):
        rows += [
            [],
            [("Claims gross-up — why claims UNDERCOUNT (direct-bill / unbilled)", _H)],
            [gross.headline],
            [("Component", _H), ("Missing fraction (low/central/high)", _H),
             ("Mechanism", _H), ("Understatement causes", _H), ("Basis", _H)],
        ]
        for comp in gross.components:
            frac = f"{comp.frac_low*100:.0f}/{comp.frac_central*100:.0f}/{comp.frac_high*100:.0f}%"
            causes = "; ".join(comp.understatement_causes) if isinstance(comp.understatement_causes, (list, tuple)) else (comp.understatement_causes or "")
            rows.append([comp.label, frac, comp.mechanism, causes, comp.basis])
        rows += [
            [("Claims-observed market ($B)", _H), (gross.claims_observed_bn, "num2"),
             ("→ true market ($B)", _H), (gross.true_market_bn, "num2"),
             ("gross-up x", _H), (gross.multiplier_central, "mult")],
        ]
    if mkt and getattr(mkt, "rows", None):
        rows += [
            [],
            [("Per-market insourcing read", _H)],
            [("Metro", _H), ("Region", _H), ("Band", _H),
             ("Insourced vol share", _H), ("Contestable residual", _H),
             ("Volume read", _H)],
        ]
        for r in mkt.rows:
            ins = f"{r.insourced_volume_share_low*100:.0f}-{r.insourced_volume_share_high*100:.0f}%"
            rows.append([r.name, r.region_label, r.framework_band_label, ins,
                         (r.contestable_residual_share, "pct"), r.volume_read])
    return Sheet("Insourcing", rows, col_widths=[22, 22, 44, 40, 40, 40])


def _moat_sheet() -> Optional[Sheet]:
    try:
        from . import ift_moat as _mo
    except Exception:  # noqa: BLE001
        return None
    factors = _safe(_mo.moat_factors, default=())
    board = _safe(_mo.market_moat_scores)
    proofs = _safe(_mo.proof_points)
    if not factors:
        return None
    rows: List[List[Any]] = [
        [("Moat / stickiness scorecard — the 7 factors, per-market, proof points",
          _H)],
        [("Density is SOURCED (facility nodes); the other factors + composite are "
          "ILLUSTRATIVE ordinal reads from analyst market knowledge.")],
        [],
        [("Factor", _H), ("Definition", _H), ("Why it matters", _H),
         ("Target", _H), ("Basis", _H)],
    ]
    for f in factors:
        rows.append([f.name, f.definition, f.why_it_matters, f.target or "—",
                     f.basis])
    if board and getattr(board, "rows", None):
        fnames = [f.name for f in factors]
        rows += [
            [],
            [("Per-market moat scores (ordinal; composite ILLUSTRATIVE 1.00-3.00)",
              _H)],
            [("Metro", _H)] + [(n, _H) for n in fnames]
            + [("Composite", _H), ("Verdict", _H)],
        ]
        for mk in board.rows:
            if not getattr(mk, "available", True):
                continue
            by_name = {fs.factor_name: fs.score for fs in mk.factors}
            rows.append([mk.name] + [by_name.get(n, "—") for n in fnames]
                        + [(mk.composite_index, "num2"), mk.overall_verdict])
    if proofs and getattr(proofs, "points", None):
        rows += [
            [],
            [("Cross-market proof points (a new entrant cannot easily replace)", _H)],
            [("Market", _H), ("Region", _H), ("Factors proven", _H),
             ("Claim", _H), ("Evidence", _H), ("Named operators (PUBLIC-WEB)", _H),
             ("Evidence source", _H)],
        ]
        for pt in proofs.points:
            fns = ("; ".join(pt.factor_names)
                   if isinstance(pt.factor_names, (list, tuple))
                   else pt.factor_names)
            ops = ("; ".join(pt.named_operators)
                   if isinstance(getattr(pt, "named_operators", None),
                                 (list, tuple)) else "")
            rows.append([pt.market, getattr(pt, "region_label", ""), fns,
                         pt.claim, pt.evidence, ops,
                         getattr(pt, "evidence_source", "")])
    return Sheet("Moat scorecard", rows,
                 col_widths=[20, 16, 34, 40, 40, 40, 22])


def _tracking_sheet() -> Optional[Sheet]:
    try:
        from . import ift_tracking as _t
    except Exception:  # noqa: BLE001
        return None
    bridge = _safe(_t.growth_bridge)
    price = _safe(_t.price_lever)
    vol = _safe(_t.volume_lever)
    cons = _safe(_t.consolidation_lever)
    if not (bridge and getattr(bridge, "available", False)):
        return None

    def _p(v):  # percent-value -> fraction for the "pct" xlsx style
        return (v / 100.0) if isinstance(v, (int, float)) else v

    rows: List[List[Any]] = [
        [("Three-lever growth tracker — price x volume + consolidation", _H)],
        [bridge.headline],
        [],
        [("Lever", _H), ("Central %/yr", _H), ("Basis", _H), ("What it is", _H)],
        ["Price / reimbursement inflation", (_p(bridge.price_central_pct), "pct"),
         "ILLUSTRATIVE (GOV AIF-anchored)",
         "AFS Ambulance Inflation Factor + commercial OON leverage + escalators"],
        ["Volume / demographics", (_p(bridge.volume_central_pct), "pct"),
         "ILLUSTRATIVE (demographic CAGR)",
         "Aging + acuity + ED boarding + post-acute utilization"],
        ["= Market growth (price x volume)",
         (_p(bridge.market_growth_central_pct), "pct"), "ILLUSTRATIVE",
         "Organic market growth, compounding"],
        ["Consolidation (share-shift, NOT organic)",
         (_p(bridge.consolidation_share_shift_central_pct), "pct"), "ILLUSTRATIVE",
         "Big systems getting bigger — a platform multiplier / share capture"],
        ["= Platform growth (market x consolidation)",
         (_p(bridge.platform_growth_central_pct), "pct"), "ILLUSTRATIVE",
         "What a well-positioned operator can compound"],
    ]
    for lever, title in ((price, "PRICE lever detail"),
                         (vol, "VOLUME lever detail"),
                         (cons, "CONSOLIDATION lever detail")):
        if lever and getattr(lever, "available", False):
            rows += [[], [(title, _H), (getattr(lever, "headline", ""))],
                     [("Component", _H), ("Value", _H), ("Basis", _H),
                      ("Detail", _H)]]
            for comp in getattr(lever, "components", []):
                rows.append([comp.name, comp.value, comp.basis, comp.detail])
    return Sheet("Three-lever tracker", rows, col_widths=[40, 16, 30, 60])


# ── Contents index (built last, prepended first) ─────────────────────────────
# One line per sheet so a partner can navigate 30+ tabs. Keyed by sheet name; a
# name without an entry still lists (blank description) so nothing is hidden.
_SHEET_DESCRIPTIONS: Dict[str, str] = {
    "Overview": "The TAM → SAM → SOM funnel at a glance.",
    "TAM build": "US ground-IFT TAM, top-down from the GOV Medicare anchor.",
    "SAM health systems": "Structural SAM = multi-hospital health systems (two ways).",
    "SOM footprint": "Serviceable-obtainable market in the operator's current metros.",
    "Markets structure": "SOURCED facility structure for every target metro.",
    "Markets read": "Anchor systems, operators, insource & moat read per metro.",
    "Competitive": "Competitive archetypes, MMT positioning, per-market competition.",
    "Insourcing": "Insource-vs-outsource bands, biller proxy, claims gross-up.",
    "Moat scorecard": "The 7 stickiness factors, per-market scores, proof points.",
    "Clinical demand": "Acute-transfer clinical spine: cases → codes → volume → growth.",
    "Destination supply": "Real post-acute destination counts (SOURCED).",
    "Three-lever tracker": "Price × volume + consolidation growth bridge.",
    "Provenance": "Honesty legend — what is real (GOV/SOURCED) vs modeled.",
    "Taxonomy": "IFT vs 911 / CCT / air / NEMT and why dedicated IFT is different.",
    "Ecosystem & journey": "The acute→post-acute patient journey + participants.",
    "Clinical routing": "How patients move: acute scenario → destination + growth.",
    "Assumptions & levers": "Every model parameter (low/central/high) + basis.",
    "Operating models": "Insource / hybrid / outsource bands, procurement, pain points.",
    "Company profiles": "MMT (subject) + the competitive field, full profiles.",
    "MMT positioning": "MMT's dedicated-IFT positioning pillars.",
    "Competitor types": "Competitive landscape by provider TYPE (no company names).",
    "Industry context": "IBISWorld industry-structure frame (ACADEMIC, qualitative).",
    "R· Reimbursement": "Research: how payment works, statute, why claims undercount.",
    "R· Unit economics": "Research: cost/revenue driver trees + margin levers.",
    "R· KPIs & metrics": "Research: the KPI dictionary by stakeholder.",
    "R· Technology & data": "Research: the request→claim technology map.",
    "R· Regulatory": "Research: the regulatory stack + barriers to entry.",
    "R· Segmentation": "Research: the seven segmentation axes + attractiveness.",
    "R· Sizing method": "Research: the six sizing approaches + assumption tracker.",
    "R· Growth & headwinds": "Research: growth drivers, headwinds, net demand.",
    "R· Evidence quality": "Research: confidence in findings + open gaps.",
    "Connectors": "Network-gated data connectors + fallback GOV citations.",
    "Fee schedule": "Medicare Ambulance Fee Schedule ready-reckoner (RVU × CF).",
    "Occupancy demand": "Hospital inpatient occupancy — the transfer-demand engine.",
    "Deal history": "EMS + NEMT + air-medical transport deal corpus.",
    "Report narrative": "Executive summary, how-it-works, trends, insider lens.",
    "Report economics": "Market size, reimbursement, unit economics, growth levers.",
    "Report reg & risk": "Regulatory, competition, risks, diligence questions.",
}


def _contents_sheet(sheets: List[Sheet]) -> Sheet:
    rows: List[List[Any]] = [
        [("Interfacility Transport (IFT) — MMT market study workbook", _H)],
        [("Every sourced figure, every model, every qualitative frame, the "
          "connectors, and the market-report narrative — one auditable download. "
          "Honesty basis travels on every value-bearing cell.")],
        [],
        [("#", _H), ("Sheet", _H), ("What's on it", _H)],
    ]
    for i, s in enumerate(sheets, start=1):
        rows.append([(i, "num"), (s.name, _H),
                     _SHEET_DESCRIPTIONS.get(s.name, "")])
    # Where the same analysis lives online (clickable) — the interactive pages
    # that this workbook is the downloadable, auditable companion to.
    rows += [
        [],
        [("Where this lives online (click to open)", _H)],
        [("", _H), ("Page", _H), ("What it is", _H)],
        ["", Link("Investor Market Study", "https://pedesk.app/ift-study"),
         "The four-dimension SOW study + MMT deep dive."],
        ["", Link("Market Research Brief", "https://pedesk.app/ift-research"),
         "The deep market-level 20-topic research brief."],
        ["", Link("TAM / SAM / SOM + 20 metros", "https://pedesk.app/ift-markets"),
         "The sized funnel + the target-metro deep dive."],
        ["", Link("Clinical demand engine", "https://pedesk.app/ift-clinical"),
         "The acute-transfer volume + growth spine."],
        ["", Link("IFT market report", "https://pedesk.app/market/interfacility_transport"),
         "The subsector market report."],
        ["", Link("Download this workbook", "https://pedesk.app/api/ift/markets.xlsx"),
         "This Excel — always the latest build."],
    ]
    return Sheet("Contents", rows, col_widths=[5, 30, 78])


# ── the workbook ─────────────────────────────────────────────────────────────
def ift_workbook_xlsx(qs: Optional[Dict[str, List[str]]] = None) -> bytes:
    """Build the full IFT market-study workbook and return .xlsx bytes.

    The quantitative funnel + per-market layers come first, then the qualitative /
    narrative / research / connector sheets from :mod:`ift_excel_extra`, with a
    Contents index prepended. Every sheet degrades to skipped rather than raising,
    so the download always succeeds — even offline where a connector is dark."""
    builders = [
        _overview_sheet, _tam_sheet, _sam_sheet, _som_sheet, _structure_sheet,
        _markets_read_sheet, _competitive_sheet, _insourcing_sheet, _moat_sheet,
        _clinical_sheet, _supply_sheet, _tracking_sheet, _provenance_sheet,
    ]
    sheets: List[Sheet] = []
    for b in builders:
        s = _safe(b)
        if s is not None:
            sheets.append(s)
    # The qualitative / narrative / research / connector sheet set.
    try:
        from . import ift_excel_extra as _extra
        sheets.extend(_extra.extra_sheets())
    except Exception:  # noqa: BLE001 — degrade to the quantitative pack alone
        pass
    if not sheets:  # never emit an empty workbook
        sheets = [_provenance_sheet()]
    return write_xlsx([_contents_sheet(sheets)] + sheets)
