"""IFT workbook — the Midwest Medical Transport (MMT) county-by-MSA sheet set.

Surfaces :mod:`ift_mmt` (MMT's footprint resolved to 22 counties across 7 CBSAs)
into the workbook: the footprint overview, the full county table by CBSA, the
county-grain connector coverage map, the ICD-10-validated clinical drivers, and
the per-metro competitive read. Same contract as the sibling excel modules —
stdlib-only :class:`Sheet` rows, every builder DEGRADES (never raises), honesty
travels (colored basis chips), and the big tables get frozen headers + banding.
"""
from __future__ import annotations

from typing import Any, List, Optional, Tuple

from ..exports.xlsx_writer import Sheet, basis_style

_H = "header"
_T = "title"
_S = "subtitle"
_B = "banner"
_N = "note"
_L = "label"


def _safe(fn, default=None):
    try:
        return fn()
    except Exception:  # noqa: BLE001
        return default


def _chip(basis: str):
    return (basis, basis_style(basis))


def _col_letter(i: int) -> str:
    out = ""
    i += 1
    while i:
        i, rem = divmod(i - 1, 26)
        out = chr(65 + rem) + out
    return out


def _title(title: str, sub: str, n_cols: int) -> Tuple[List[List[Any]], List[str]]:
    return ([[(title, _T)], [(sub, _S)], []],
            [f"A1:{_col_letter(max(0, n_cols - 1))}1"])


# ── Overview + counties by CBSA ──────────────────────────────────────────────
def _footprint_sheet() -> Optional[Sheet]:
    from . import ift_mmt as _m
    s = _safe(_m.footprint_summary)
    cbsas = _safe(_m.footprint_cbsas, default=[]) or []
    if not (s and cbsas):
        return None
    rows, merges = _title(
        "Midwest Medical Transport — footprint by MSA (county-resolved)",
        "MMT's served metros resolved to OMB Core-Based Statistical Areas and "
        "their constituent counties. Delineations are OMB 2023 (GOV); county "
        "population is the 2020 Census (GOV); the 65+ split and the modeled "
        "ground-IFT demand are ILLUSTRATIVE (national-anchored per-capita rates).",
        6)
    rows += [
        [("Footprint at a glance", _B)],
        ["CBSAs served", (s.n_cbsa, "num"), "of which MSA / μSA",
         (f"{s.n_msa} / {s.n_micro}")],
        ["Counties", (s.n_county, "num"), "States", (s.n_states, "num")],
        ["Population (2020)", (s.pop_2020, "num"), "65+",
         (s.pop_65_plus, "num")],
        ["65+ share", (s.senior_share, "pct"),
         "Modeled ground-IFT demand", (f"{s.demand_missions:,} legs/yr")],
        ["Modeled demand $", (s.demand_dollars, "money"), "@ $/leg",
         "$1,300 (ILLUSTRATIVE)"],
        [],
        [("Served CBSAs (biggest first)", _B)],
        [("CBSA", _H), ("Type", _H), ("Metro (ift_geo)", _H), ("Counties", _H),
         ("Population 2020", _H), ("65+", _H), ("Demand legs/yr", _H),
         ("Demand $", _H)],
    ]
    band_start = len(rows) + 1
    for b in cbsas:
        rows.append([b.name, b.kind, b.metro, (len(b.counties), "num"),
                     (b.pop_2020, "num"), (b.pop_65_plus, "num"),
                     (b.demand_missions, "num"), (b.demand_dollars, "money")])
    band_end = len(rows)
    rows += [
        [],
        [("Delineation basis", _H), s.cbsa_source],
        [("Population basis", _H), s.pop_source],
        [("Demand basis", _H),
         "ILLUSTRATIVE — ground-IFT legs = 65+ × 0.054 + under-65 × 0.0049 "
         "(national-anchored: US ground IFT ~4.5M legs/yr, 65+ over-indexed) × "
         "$1,300 blended all-payer net revenue/leg."],
    ]
    return Sheet("MMT footprint", rows, col_widths=[30, 10, 22, 10, 16, 12, 14, 16],
                 merges=merges, band_rows=(band_start, band_end))


def _counties_sheet() -> Optional[Sheet]:
    from . import ift_mmt as _m
    counties = list(getattr(_m, "MMT_COUNTIES", ()) or ())
    if not counties:
        return None
    rows, merges = _title(
        "MMT footprint — every county (by CBSA)",
        "The 22 counties MMT's territory spans, with role, 2020 population, the "
        "ILLUSTRATIVE 65+ split, and the modeled ground-IFT demand. Grouped by "
        "CBSA; the anchor hospital nodes are noted where material.",
        10)
    rows += [
        [("County", _H), ("State", _H), ("FIPS", _H), ("CBSA", _H),
         ("Metro", _H), ("Role", _H), ("Pop 2020", _H), ("65+ (est)", _H),
         ("Demand legs/yr", _H), ("County seat / note", _H)],
    ]
    band_start = len(rows) + 1
    # order by CBSA population desc, then county population desc
    cbsas = {b.code: b.pop_2020 for b in (_safe(_m.footprint_cbsas, default=[]) or [])}
    counties.sort(key=lambda c: (-cbsas.get(c.cbsa_code, 0), -c.pop_2020))
    for c in counties:
        d = _m.county_demand(c)
        note = c.seat + ((" — " + c.note) if c.note else "")
        rows.append([
            (c.name, _L), c.state, c.fips, c.cbsa_name, c.metro, c.role,
            (c.pop_2020, "num"), (c.pop_65_plus, "num"),
            (d.demand_missions, "num"), note])
    band_end = len(rows)
    rows += [[], [("Basis", _H),
                  "County↔CBSA: OMB 2023 (GOV). Pop: 2020 Census (GOV). 65+ & "
                  "demand: ILLUSTRATIVE (named rates). Roles: core / suburban / "
                  "rural-feeder."]]
    return Sheet("MMT counties", rows,
                 col_widths=[16, 6, 8, 26, 20, 13, 11, 11, 13, 40],
                 freeze_rows=4, merges=merges, band_rows=(band_start, band_end),
                 autofilter=f"A4:J{band_end}")


def _connectors_sheet() -> Optional[Sheet]:
    from . import ift_mmt as _m
    cov = _safe(_m.county_connector_coverage, default=[]) or []
    if not cov:
        return None
    n_live = sum(1 for c in cov if c.available)
    rows, merges = _title(
        "MMT — county-grain data-connector coverage",
        "Every public-data hook resolvable to MMT's counties (Census 65+, CMS "
        "ambulance saturation + geographic variation, CDC CKD + cardiac, the "
        "hospital origin universe, NPPES ambulance suppliers). Each is wired to "
        "MMT's FIPS/state filters — network-gated offline with an honest "
        "fallback, SOURCED once the estate is ingested.",
        6)
    rows += [
        [(f"{len(cov)} county-grain hooks · {n_live} live / "
          f"{len(cov) - n_live} ingest-ready", _N)],
        [],
        [("Connector", _H), ("Dataset", _H), ("Resolves to", _H),
         ("What it yields for MMT", _H), ("Status", _H),
         ("Source / fallback", _H)],
    ]
    band_start = len(rows) + 1
    for c in cov:
        rows.append([
            (c.title, _L), c.dataset_id, c.grain, c.yields,
            _chip("SOURCED" if c.available else "CONNECTOR"), c.source_label])
    band_end = len(rows)
    return Sheet("MMT connectors", rows,
                 col_widths=[34, 40, 26, 46, 12, 50], freeze_rows=6,
                 merges=merges, band_rows=(band_start, band_end))


def _clinical_sheet() -> Optional[Sheet]:
    from . import ift_mmt as _m
    drivers = _safe(lambda: _m.clinical_drivers(14), default=[]) or []
    if not drivers:
        return None
    rows, merges = _title(
        "MMT — acute-transfer clinical drivers (ICD-10 validated)",
        "The acute conditions (ranked by demographic CAGR) that generate MMT's "
        "interfacility volume in a rural hub-and-spoke geography — each with its "
        "ICD-10-CM codes and a coding-integrity check. Volumes are GOV/ACADEMIC; "
        "codes are SOURCED against the ICD-10-CM set.",
        6)
    rows += [
        [("Condition", _H), ("Family", _H), ("Transfer", _H), ("ICD-10-CM", _H),
         ("Codes valid", _H), ("Codes total", _H)],
    ]
    band_start = len(rows) + 1
    for d in drivers:
        rows.append([
            (d.condition, _L), d.family, d.transfer_type, d.icd10,
            (d.codes_valid, "num"), (d.codes_total, "num")])
    band_end = len(rows)
    rows += [[], [("Basis", _H),
                  "Conditions from the IFT clinical spine (GOV/ACADEMIC volumes, "
                  "ILLUSTRATIVE demographic CAGRs); ICD-10-CM codes validated "
                  "SOURCED against the code set."]]
    return Sheet("MMT clinical drivers", rows,
                 col_widths=[34, 20, 16, 34, 12, 12], freeze_rows=4,
                 merges=merges, band_rows=(band_start, band_end))


def _metro_read_sheet() -> Optional[Sheet]:
    from . import ift_mmt as _m
    reads = _safe(_m.mmt_metro_reads, default=[]) or []
    if not reads:
        return None
    rows, merges = _title(
        "MMT — per-metro competitive & moat read (county-tied)",
        "MMT's served metros with the county roll-up and the ift_geo qualitative "
        "read — who competes, the insource-vs-outsource posture, and the moat. "
        "Operator names are PUBLIC/company-web, named honestly; the reads are "
        "analyst knowledge, not our data.",
        5)
    rows += [
        [("Metro", _H), ("Counties / pop", _H), ("Demand legs/yr", _H),
         ("Insource-vs-outsource read", _H), ("Competing operators (PUBLIC)", _H)],
    ]
    for r in reads:
        rows.append([
            (r.metro, _L),
            f"{r.n_counties} counties · {r.pop_2020:,}",
            (r.demand_missions, "num"),
            r.insource_read or "—",
            "; ".join(r.competitors) or "—"])
        if r.moat_note:
            rows.append([("", _N), ("Moat: " + r.moat_note, _N)])
    rows += [[], [("Basis", _H),
                  "County roll-up: OMB/Census (GOV) + ILLUSTRATIVE demand. "
                  "Operators/reads: PUBLIC-WEB + analyst knowledge."]]
    return Sheet("MMT metro read", rows, col_widths=[22, 22, 14, 52, 46],
                 freeze_rows=4, merges=merges)


# ── Serviceable market (SOM) ─────────────────────────────────────────────────
def _serviceable_sheet() -> Optional[Sheet]:
    from . import ift_mmt as _m
    sm = _safe(_m.mmt_serviceable_model)
    if not (sm and sm.rows):
        return None
    rows, merges = _title(
        "MMT serviceable market (SOM) — county demand → winnable book",
        "The funnel for MMT: total county ground-IFT demand × the serviceable "
        "share s(m) [by the metro's insource archetype, reused from the study's "
        "ift_analytics so this SOM agrees with the funnel] × MMT's estimated "
        "share of the outsourced/contestable book. Demand & shares are "
        "ILLUSTRATIVE; s(m) matches the market funnel.", 7)
    rows += [
        [("SOM at a glance", _B)],
        ["Footprint IFT demand", (sm.total_demand, "num"),
         "Serviceable (outsourced)", (sm.total_serviceable, "num")],
        ["Serviceable share of demand", (sm.footprint_serviceable_share, "pct"),
         "MMT SOM legs/yr", (sm.mmt_som_missions, "num")],
        ["MMT SOM revenue", (sm.mmt_som_dollars, "money"), "@ $/leg",
         "$1,300 (ILLUSTRATIVE)"],
        [],
        [("Per-metro serviceable build", _B)],
        [("Metro", _H), ("Insource archetype", _H), ("Demand legs/yr", _H),
         ("s(m)", _H), ("Serviceable legs/yr", _H), ("MMT share", _H),
         ("MMT legs/yr", _H), ("MMT revenue", _H)],
    ]
    band_start = len(rows) + 1
    for r in sm.rows:
        rows.append([r.metro, r.insource_class, (r.demand_missions, "num"),
                     (r.serviceable_share, "pct"), (r.serviceable_missions, "num"),
                     (r.mmt_share, "pct"), (r.mmt_missions, "num"),
                     (r.mmt_revenue, "money")])
    band_end = len(rows)
    rows += [[], [("Basis", _H), sm.note],
             [_chip("ILLUSTRATIVE"), _chip("GOV")]]
    return Sheet("MMT serviceable SOM", rows,
                 col_widths=[22, 30, 14, 8, 16, 11, 12, 16], freeze_rows=8,
                 merges=merges, band_rows=(band_start, band_end))


def _operating_sheet() -> Optional[Sheet]:
    from . import ift_mmt as _m
    op = _safe(_m.mmt_operating_model)
    if not (op and op.metrics):
        return None
    rows, merges = _title(
        "MMT operating model — footprint unit economics",
        "The cost structure and the operating levers (UHU, deadhead) that decide "
        "whether a dense-metro book or a rural long-leg book makes money. Every "
        "figure is ILLUSTRATIVE with a named basis; labor share is the GADCS "
        "anchor (~69% of ground-ambulance cost).", 4)
    rows += [
        [(op.headline, _S)],
        [],
        [("Metric", _H), ("Value", _H), ("Basis", _H), ("Detail", _H)],
    ]
    band_start = len(rows) + 1
    for mtr in op.metrics:
        rows.append([(mtr.name, _L), mtr.value, _chip(mtr.basis), mtr.detail])
    band_end = len(rows)
    return Sheet("MMT operating model", rows, col_widths=[30, 14, 34, 56],
                 freeze_rows=6, merges=merges, band_rows=(band_start, band_end))


def _diligence_sheet() -> Optional[Sheet]:
    from . import ift_mmt as _m
    d = _safe(_m.mmt_diligence)
    if not (d and (d.value_levers or d.risks or d.questions)):
        return None
    rows, merges = _title(
        "MMT diligence — value levers, risks, and the question list",
        "The thesis a buyer underwrites: the value-creation levers unique to a "
        "dense-metro + I-80-corridor footprint, the structural risks, and the "
        "diligence questions. Analyst framework (FRAMEWORK basis).", 3)
    if d.value_levers:
        rows += [[("Value-creation levers", _B)],
                 [("Lever", _H), ("Category", _H), ("What it is", _H)]]
        for lv in d.value_levers:
            rows.append([(lv.title, _L), lv.tag, lv.detail])
    if d.risks:
        rows += [[], [("Risks", _B)],
                 [("Risk", _H), ("Severity", _H), ("Why it matters", _H)]]
        for rk in d.risks:
            rows.append([(rk.title, _L), rk.tag, rk.detail])
    if d.questions:
        rows += [[], [("Diligence questions", _B)]]
        for q in d.questions:
            rows.append(["• " + q])
    rows += [[], [("Basis", _H),
                  "FRAMEWORK — analyst value-creation / risk framing tied to the "
                  "county model + ift_geo competitive reads; not a filed figure."]]
    return Sheet("MMT diligence", rows, col_widths=[30, 18, 82], merges=merges)


def _scorecard_sheet() -> Optional[Sheet]:
    from . import ift_mmt as _m
    sc = _safe(_m.mmt_positioning_scorecard, default=())
    if not sc:
        return None
    rows, merges = _title(
        "MMT positioning scorecard — vs the competitive field",
        "MMT against a scaled regional private (AmeriPro), a national EMS platform "
        "(GMR/AMR), and municipal / fire-based 911 across the factors that decide "
        "IFT first-call. Reads are analyst knowledge (FRAMEWORK); operator names "
        "are PUBLIC-WEB.", 5)
    rows += [
        [("Factor", _H), ("MMT (subject)", _H), ("AmeriPro (regional)", _H),
         ("National EMS (GMR/AMR)", _H), ("Municipal / 911", _H)],
    ]
    band_start = len(rows) + 1
    for r in sc:
        rows.append([(r.factor, _L), r.mmt, r.ameripro, r.national_ems,
                     r.municipal])
    band_end = len(rows)
    rows += [[], [("Basis", _H),
                  "FRAMEWORK — analyst competitive read; operator names "
                  "PUBLIC-WEB, no exclusivities asserted."]]
    return Sheet("MMT scorecard", rows, col_widths=[24, 30, 28, 26, 24],
                 freeze_rows=4, merges=merges, band_rows=(band_start, band_end))


# ── public entry point ────────────────────────────────────────────────────────
def mmt_sheets() -> List[Sheet]:
    """Every MMT county-by-MSA sheet, in reading order. Each degrades to skipped
    (never raises)."""
    out: List[Sheet] = []
    for b in (_footprint_sheet, _counties_sheet, _serviceable_sheet,
              _operating_sheet, _connectors_sheet, _clinical_sheet,
              _metro_read_sheet, _scorecard_sheet, _diligence_sheet):
        s = _safe(b)
        if s is not None:
            out.append(s)
    return out
