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


# ── public entry point ────────────────────────────────────────────────────────
def mmt_sheets() -> List[Sheet]:
    """Every MMT county-by-MSA sheet, in reading order. Each degrades to skipped
    (never raises)."""
    out: List[Sheet] = []
    for b in (_footprint_sheet, _counties_sheet, _connectors_sheet,
              _clinical_sheet, _metro_read_sheet):
        s = _safe(b)
        if s is not None:
            out.append(s)
    return out
