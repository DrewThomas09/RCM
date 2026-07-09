"""IFT workbook — the analytical-DEPTH sheet set.

:mod:`ift_excel` builds the funnel + per-market layers and :mod:`ift_excel_extra`
the qualitative / narrative / connector sheets. This third module surfaces the
analytics the first two computed but never fully rendered — the parts of the
study a diligence team actually stress-tests:

  * **Sensitivity** — the TAM→SAM→SOM range and a one-variable-at-a-time tornado
    (swing each SOM lever low↔high, hold the rest central) so a buyer sees which
    assumption the answer hangs on;
  * **Acuity mix** — the CCT/SCT high-acuity concentration (``mission_mix``), the
    module's stated headline thesis, previously unrendered;
  * **Demand build** — the growth leaderboard (``growth_ranked``) + the
    escalation-book projection (``registry_summary``);
  * **Reimbursement rate series** — the year-by-year Ambulance Inflation Factor
    (``price_lever.aif_trend``), previously prose-only;
  * **Footprint vs national** — the footprint's national penetration + the
    per-region roll-up (``footprint_rollup``), previously dropped;
  * **Moat detail** — per-metro contestability + the factor-by-factor evidence
    trail (``market_moat_scores``), the "why this score / is it winnable" read;
  * **Code validation** — the ICD-10-CM coding-integrity QA (``validate_codes``).

Same contract as the sibling modules: stdlib-only :class:`Sheet` rows, every
builder DEGRADES (a missing analytic drops its sheet, never raises), honesty
travels (every value carries a basis, colored by :func:`basis_style`), and the
big tables get frozen headers + autofilter + zebra banding for readability.
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
_ILL = "ILLUSTRATIVE"


def _safe(fn, default=None):
    try:
        return fn()
    except Exception:  # noqa: BLE001
        return default


def _chip(basis: str):
    """A basis cell, colored by its honesty label."""
    return (basis, basis_style(basis))


def _title_rows(title: str, sub: str, n_cols: int) -> Tuple[List[List[Any]], List[str]]:
    """The standard title banner (merged) + subtitle + spacer; returns the rows
    and the merge range for the title so it spans the table width."""
    rows: List[List[Any]] = [[(title, _T)], [(sub, _S)], []]
    last = _col_letter(max(0, n_cols - 1))
    return rows, [f"A1:{last}1"]


def _col_letter(i: int) -> str:
    out = ""
    i += 1
    while i:
        i, rem = divmod(i - 1, 26)
        out = chr(65 + rem) + out
    return out


def _pct(x: Optional[float]) -> Any:
    return (x, "pct") if isinstance(x, (int, float)) else "—"


# ── Sensitivity — funnel range + one-variable-at-a-time tornado ───────────────
def _sensitivity_sheet() -> Optional[Sheet]:
    from . import ift_analytics as _an
    tam = _safe(_an.ground_tam)
    hs = _safe(_an.health_system_sam)
    som = _safe(_an.sam_formula)
    if not (som and getattr(som, "available", False)):
        return None

    def _swing_pct(lo, c, hi):
        if not c:
            return "—"
        return ((hi - lo) / c, "pct")

    rows, merges = _title_rows(
        "Sensitivity — how the funnel moves when a lever swings",
        "Every dollar in the funnel is ILLUSTRATIVE with a named basis. This is "
        "the stress-test: the low/central/high band on each layer, then a "
        "one-variable-at-a-time tornado on the SOM — swing one lever to its "
        "low/high while the others stay central, so a buyer sees which single "
        "assumption the answer hangs on.", 5)
    rows += [
        [("Funnel range (low / central / high)", _B)],
        [("Layer", _H), ("Low", _H), ("Central", _H), ("High", _H),
         ("Range width (% of central)", _H)],
    ]
    if tam and getattr(tam, "available", False):
        rows.append(["TAM — all US ground IFT ($B)",
                     (tam.allpayer_tam_bn_low, "num2"),
                     (tam.allpayer_tam_bn_central, "num2"),
                     (tam.allpayer_tam_bn_high, "num2"),
                     _swing_pct(tam.allpayer_tam_bn_low,
                                tam.allpayer_tam_bn_central,
                                tam.allpayer_tam_bn_high)])
    if hs and getattr(hs, "available", False):
        rows.append(["SAM — multi-hospital health systems ($B)",
                     (hs.sam_low_bn, "num2"), (hs.sam_central_bn, "num2"),
                     (hs.sam_high_bn, "num2"),
                     _swing_pct(hs.sam_low_bn, hs.sam_central_bn, hs.sam_high_bn)])
    rows.append(["SOM — operator footprint ($)",
                 (som.sam_dollars_low, "money"), (som.sam_dollars_central, "money"),
                 (som.sam_dollars_high, "money"),
                 _swing_pct(som.sam_dollars_low, som.sam_dollars_central,
                            som.sam_dollars_high)])
    rows.append([("", _N), ("Basis: every funnel dollar is ILLUSTRATIVE, "
                            "modeled on GOV/SOURCED anchors.", _N)])

    # OVAT tornado on the SOM — re-run sam_formula swinging one lever at a time.
    base = som.sam_dollars_central
    levers = [
        ("f_IFT — ground-IFT fraction of discharges", _an._F_IFT,
         lambda v: _an.sam_formula(f_ift=v),
         "Discharges that need a ground IFT leg — the demand multiplier."),
        ("r_IFT — net revenue per transport ($)", _an._R_IFT,
         lambda v: _an.sam_formula(r_ift=v),
         "Blended all-payer net revenue per IFT leg — the price lever."),
        ("λ_return — recurring SNF legs / occ. bed / yr", _an._LAMBDA_RETURN,
         lambda v: _an.sam_formula(lambda_return=v),
         "Recurring post-acute round-trips per occupied SNF bed — the "
         "recurring-volume lever."),
    ]
    tor: List[Tuple[str, float, float, float, str]] = []
    for name, band, fn, detail in levers:
        lo = _safe(lambda fn=fn, band=band: fn(band[0]).sam_dollars_central)
        hi = _safe(lambda fn=fn, band=band: fn(band[2]).sam_dollars_central)
        if lo is None or hi is None:
            continue
        width = abs(hi - lo)
        tor.append((name, lo, hi, width, detail))
    tor.sort(key=lambda t: t[3], reverse=True)   # widest swing first = tornado
    if tor:
        rows += [
            [],
            [("SOM tornado — swing one lever, hold the rest central "
              "(widest first)", _B)],
            [("Lever (low → high)", _H), ("SOM @ low", _H),
             ("SOM @ central", _H), ("SOM @ high", _H),
             ("Swing (% of central)", _H)],
        ]
        for name, lo, hi, width, _d in tor:
            rows.append([name, (lo, "money"), (base, "money"), (hi, "money"),
                         ((width / base) if base else "—", "pct")])
        rows += [[], [("What each lever is", _B)],
                 [("Lever", _H), ("What it is", _H), ("Basis", _H)]]
        for name, band, _fn, detail in levers:
            rng = f"{band[0]:g} / {band[1]:g} / {band[2]:g}"
            rows.append([(name, _L), f"{detail} (low/central/high = {rng})",
                         _chip(_ILL)])
    rows.append([("Source / basis", _H),
                 "TAM/SAM/SOM ranges from the module spine; the tornado re-runs "
                 "sam_formula() swinging one lever at a time — all ILLUSTRATIVE."])
    hdr = 4  # freeze through the first column-header row
    return Sheet("Sensitivity", rows, col_widths=[46, 18, 18, 18, 22],
                 freeze_rows=hdr, merges=merges)


# ── Acuity mix — the CCT/SCT concentration (mission_mix) ──────────────────────
def _acuity_mix_sheet() -> Optional[Sheet]:
    from . import ift_clinical_demand as _cd
    mm = _safe(_cd.mission_mix)
    if not (mm and isinstance(mm, dict) and mm.get("by_tier_volume")):
        return None
    tiers = mm["by_tier_volume"]
    total = mm.get("total_weighting_volume") or sum(tiers.values()) or 1
    rows, merges = _title_rows(
        "Acuity mix — the high-acuity concentration that IS the IFT thesis",
        "IFT over-indexes on critical-care transport. This is the "
        "volume-weighted acuity book: the CCT/SCT + behavioral high-acuity "
        "tiers dominate, which is what an operator with dedicated crews and "
        "specialty capability monetizes. Weights are ILLUSTRATIVE (named basis).",
        3)
    rows += [
        [("Acuity tier — volume-weighted book", _B)],
        [("Transport tier", _H), ("Weighted volume/yr", _H), ("Share of book", _H)],
    ]
    band_start = len(rows) + 1
    for tier, vol in sorted(tiers.items(), key=lambda kv: kv[1], reverse=True):
        rows.append([(tier, _L), (vol, "num"),
                     ((vol / total) if total else "—", "pct")])
    band_end = len(rows)
    rows += [
        [],
        [("Acuity concentration (the thesis in three numbers)", _B)],
        ["High-acuity share (CCT/SCT/behavioral/neonatal/peds)",
         _pct(mm.get("high_acuity_share")), _chip(_ILL)],
        ["Mid-acuity share (ALS2)", _pct(mm.get("mid_acuity_share")),
         _chip(_ILL)],
        ["Low/base-acuity share (ALS)", _pct(mm.get("low_acuity_share")),
         _chip(_ILL)],
        [],
        [("Source / basis", _H), mm.get("basis", "")],
    ]
    return Sheet("Acuity mix", rows, col_widths=[46, 22, 16],
                 freeze_rows=5, merges=merges, band_rows=(band_start, band_end))


# ── Demand build — growth leaderboard + escalation projection ─────────────────
def _demand_build_sheet() -> Optional[Sheet]:
    from . import ift_clinical_demand as _cd
    ranked = _safe(_cd.growth_ranked, default=[]) or []
    summ = _safe(_cd.registry_summary)
    if not ranked:
        return None
    rows, merges = _title_rows(
        "Demand build — the growth leaderboard behind the volume",
        "The acute-transfer conditions ranked by demographic CAGR (fastest "
        "first) with the 10-year growth index, then the escalation-book "
        "projection. National volumes are GOV/ACADEMIC (published series); "
        "growth is the age-band demographic CAGR (ILLUSTRATIVE, incidence held "
        "constant).", 7)
    rows += [
        [("Growth leaderboard — conditions by demographic CAGR", _B)],
        [("Condition", _H), ("Family", _H), ("Transfer", _H),
         ("National volume/yr", _H), ("Growth CAGR", _H),
         ("10-yr index", _H), ("Volume basis", _H)],
    ]
    band_start = len(rows) + 1
    for c in ranked:
        nv = getattr(c, "national_volume", None)
        vol = getattr(nv, "value", 0) if nv else 0
        vbasis = (nv.source_label.split()[0] if nv and getattr(nv, "source_label", "")
                  else "")
        gr = getattr(c, "growth", None)
        cagr = getattr(gr, "cagr", None) if gr else None
        idx = getattr(gr, "index_10yr", None) if gr else None
        rows.append([
            (getattr(c, "name", ""), _L), getattr(c, "family", ""),
            getattr(c, "transfer_type", ""),
            (vol, "num") if vol else "not separately enumerated",
            _pct(cagr), (idx, "mult") if isinstance(idx, (int, float)) else "—",
            _chip(vbasis) if vbasis else ""])
    band_end = len(rows)
    if summ and isinstance(summ, dict):
        rows += [
            [],
            [("Escalation-book projection (the addressable acute spine)", _B)],
            [("Metric", _H), ("Value", _H), ("Basis", _H)],
        ]
        eav = summ.get("escalation_addressable_volume")
        ecagr = summ.get("escalation_volume_weighted_cagr")
        rows += [
            ["Escalation conditions in registry",
             (summ.get("n_by_family", {}).get("Escalation", 0), "num"),
             _chip("FRAMEWORK")],
            ["Escalation addressable volume/yr",
             (eav, "num") if isinstance(eav, (int, float)) else "—",
             _chip("ACADEMIC")],
            ["Volume-weighted escalation CAGR", _pct(ecagr), _chip(_ILL)],
        ]
        if isinstance(eav, (int, float)) and isinstance(ecagr, (int, float)):
            proj5 = eav * ((1 + ecagr) ** 5)
            rows.append(["→ Projected escalation volume in 5 yrs",
                         (round(proj5), "num"), _chip(_ILL)])
        # family + transfer-type registry counts
        nf = summ.get("n_by_family", {})
        if nf:
            rows += [[], [("Registry composition — by transfer family", _B)],
                     [("Family", _H), ("Conditions", _H)]]
            for fam, n in nf.items():
                rows.append([(fam, _L), (n, "num")])
    rows.append([("Source / basis", _H),
                 "Volumes GOV/ACADEMIC (AHRQ HCUP, CDC, published); CAGRs "
                 "ILLUSTRATIVE (age-band population CAGRs); projection compounds "
                 "the weighted CAGR."])
    return Sheet("Demand build", rows,
                 col_widths=[30, 20, 18, 18, 12, 11, 14],
                 freeze_rows=5, merges=merges, band_rows=(band_start, band_end),
                 autofilter=f"A5:G{band_end}")


# ── Reimbursement rate series — the AIF year-by-year ──────────────────────────
def _aif_series_sheet() -> Optional[Sheet]:
    from . import ift_tracking as _t
    pl = _safe(_t.price_lever)
    if not (pl and getattr(pl, "available", False) and getattr(pl, "aif_trend", None)):
        return None
    rows, merges = _title_rows(
        "Reimbursement rate series — the Ambulance Inflation Factor (AIF)",
        "The Medicare Ambulance Inflation Factor updates the fee schedule each "
        "year (CPI-U − a productivity adjustment). It is the GOV-anchored floor "
        "under the price lever; commercial OON leverage + escalators sit on top. "
        "The AIF values are GOV; the composite price growth is ILLUSTRATIVE.", 3)
    rows += [
        [("AIF by year (GOV)", _B)],
        [("Year", _H), ("AIF %", _H), ("Basis", _H)],
    ]
    band_start = len(rows) + 1
    for yr, pct in pl.aif_trend:
        rows.append([(yr, "num"), ((pct / 100.0), "pct"), _chip("GOV")])
    band_end = len(rows)
    rows += [
        [],
        [("Rate-inflation summary", _B)],
        [("Measure", _H), ("Value", _H), ("Basis", _H)],
        ["Latest AIF (%/yr)",
         ((pl.aif_latest_pct / 100.0), "pct")
         if isinstance(pl.aif_latest_pct, (int, float)) else "—", _chip("GOV")],
        ["Trailing-3yr average AIF",
         ((pl.aif_trailing3_avg_pct / 100.0), "pct")
         if isinstance(pl.aif_trailing3_avg_pct, (int, float)) else "—",
         _chip("GOV")],
        ["Full-window average AIF",
         ((pl.aif_full_avg_pct / 100.0), "pct")
         if isinstance(pl.aif_full_avg_pct, (int, float)) else "—", _chip("GOV")],
        [],
        [("Composite price growth (AIF + commercial leverage + escalators)", _B)],
        [("Scenario", _H), ("%/yr", _H), ("Basis", _H)],
        ["Low", ((pl.composite_low_pct / 100.0), "pct")
         if isinstance(pl.composite_low_pct, (int, float)) else "—", _chip(_ILL)],
        ["Central", ((pl.composite_central_pct / 100.0), "pct")
         if isinstance(pl.composite_central_pct, (int, float)) else "—",
         _chip(_ILL)],
        ["High", ((pl.composite_high_pct / 100.0), "pct")
         if isinstance(pl.composite_high_pct, (int, float)) else "—", _chip(_ILL)],
        [],
        [("Source / basis", _H), getattr(pl, "source_label", "")],
    ]
    return Sheet("Reimbursement AIF series", rows, col_widths=[40, 14, 16],
                 freeze_rows=5, merges=merges, band_rows=(band_start, band_end))


# ── Footprint vs national — penetration + per-region roll-up ──────────────────
def _footprint_national_sheet() -> Optional[Sheet]:
    from . import ift_geo
    roll = _safe(ift_geo.footprint_rollup)
    if not (roll and getattr(roll, "available", False)):
        return None
    rows, merges = _title_rows(
        "Footprint vs national — how much of the US the SOM covers",
        "The operator's current metros against the national facility universe: "
        "the penetration the SOM is bottom-up from, and the per-region roll-up. "
        "Counts + national bases are SOURCED (CMS provider rolls / HCRIS).", 7)
    rows += [
        [("National penetration (SOURCED)", _B)],
        [("Measure", _H), ("Footprint", _H), ("National", _H), ("Share", _H)],
        ["Hospitals (origins)", (roll.n_hospitals, "num"),
         (getattr(roll, "n_hospitals_national", 0), "num"),
         _pct(getattr(roll, "hospitals_national_share", None))],
        ["SNF beds", (roll.snf_beds, "num"),
         (getattr(roll, "snf_beds_national", 0)
          or getattr(roll, "n_snf_national", 0), "num"),
         _pct(getattr(roll, "snf_beds_national_share", None))],
        ["Target metros", (roll.n_metros, "num"), "", ""],
        ["State regions", (roll.n_regions, "num"), "", ""],
        [("", _N), ("Basis: facility counts + national bases SOURCED (CMS "
                    "provider rolls, HCRIS); penetration is the ratio.", _N)],
    ]
    by_region = getattr(roll, "by_region", None)
    if isinstance(by_region, dict) and by_region:
        rows += [
            [],
            [("Per-region roll-up (SOURCED)", _B)],
            [("Region", _H), ("Metros", _H), ("Hospitals", _H),
             ("HCRIS beds", _H), ("SNFs", _H), ("SNF beds", _H),
             ("Post-acute nodes", _H)],
        ]
        band_start = len(rows) + 1
        for _key, r in by_region.items():
            rows.append([
                (r.get("region_label", _key), _L), (r.get("n_metros", 0), "num"),
                (r.get("n_hospitals", 0), "num"), (r.get("hcris_beds", 0), "num"),
                (r.get("n_snf", 0), "num"), (r.get("snf_beds", 0), "num"),
                (r.get("n_postacute", 0), "num")])
        band_end = len(rows)
        rows.append([("Source / basis", _H), getattr(roll, "note", "") or
                     "SOURCED · CMS provider rolls + HCRIS beds"])
        return Sheet("Footprint vs national", rows,
                     col_widths=[22, 10, 12, 13, 8, 11, 16], freeze_rows=8,
                     merges=merges, band_rows=(band_start, band_end))
    rows.append([("Source / basis", _H), getattr(roll, "note", "")])
    return Sheet("Footprint vs national", rows,
                 col_widths=[26, 14, 14, 12], freeze_rows=4, merges=merges)


# ── Moat detail — per-metro contestability + factor evidence trail ────────────
def _moat_detail_sheet() -> Optional[Sheet]:
    from . import ift_moat as _mo
    board = _safe(_mo.market_moat_scores)
    factors = _safe(_mo.moat_factors, default=())
    if not (board and getattr(board, "rows", None) and factors):
        return None
    fnames = [f.name for f in factors]
    rows, merges = _title_rows(
        "Moat detail — per-metro contestability + the evidence trail",
        "The companion to the moat scorecard: for every target metro, the "
        "contestability read (who holds the moat / what is winnable) and the "
        "factor-by-factor evidence behind each ordinal score. Density is "
        "SOURCED; the reads + scores are ILLUSTRATIVE ordinal analyst reads.",
        4)
    vc = getattr(board, "verdict_counts", None)
    if isinstance(vc, dict) and vc:
        rows += [[("Verdict distribution", _B)],
                 [("Verdict", _H), ("Markets", _H)]]
        for v, n in vc.items():
            rows.append([(v, _L), (n, "num")])
        rows.append([])
    for mk in board.rows:
        if not getattr(mk, "available", True):
            continue
        rows += [
            [(mk.name, _B), (f"composite {getattr(mk, 'composite_index', '—')} · "
                             f"{getattr(mk, 'overall_verdict', '')}", _B)],
            ["Contestability", (getattr(mk, "contestability", ""), _L)],
            ["Overall read", (getattr(mk, "overall_read", ""), _L)],
            [("Factor", _H), ("Score", _H), ("Evidence", _H), ("Basis", _H)],
        ]
        by_id = {getattr(fs, "factor_name", ""): fs for fs in mk.factors}
        for n in fnames:
            fs = by_id.get(n)
            if fs is None:
                continue
            sc = getattr(fs, "score", "")
            rows.append([(n, _L),
                         (sc, "num2") if isinstance(sc, (int, float)) else sc,
                         getattr(fs, "evidence", ""),
                         _chip(getattr(fs, "basis", _ILL))])
        rows.append([])
    rows.append([("Source / basis", _H), getattr(board, "source_label", "")])
    return Sheet("Moat detail", rows, col_widths=[24, 14, 60, 16],
                 merges=merges)


# ── Code validation QA — ICD-10-CM coding integrity ──────────────────────────
def _codes_qa_sheet() -> Optional[Sheet]:
    from . import ift_clinical_demand as _cd
    vc = _safe(_cd.validate_codes)
    if not (vc and isinstance(vc, dict)):
        return None
    rows, merges = _title_rows(
        "Clinical code validation — ICD-10-CM coding integrity (QA)",
        "A diligence-grade provenance check: every acute-transfer condition's "
        "ICD-10-CM codes validated against the code set, with the ICD-10-PCS "
        "procedure reference. Confirms the medical-necessity narrative rests on "
        "real, billable codes — SOURCED against the code registry.", 5)
    rows += [
        [("Condition → code validation", _B)],
        [("Condition", _H), ("ICD-10-CM valid", _H), ("Codes (valid)", _H),
         ("Codes (unmatched)", _H), ("ICD-10-PCS reference", _H)],
    ]
    band_start = len(rows) + 1
    n_ok = n_miss = 0
    for cond, v in vc.items():
        if not isinstance(v, dict):
            continue
        ok = v.get("icd10_ok", []) or []
        miss = v.get("icd10_miss", []) or []
        pcs = v.get("pcs_reference", []) or []
        n_ok += len(ok)
        n_miss += len(miss)
        rows.append([
            (cond, _L), (len(ok), "num"), ", ".join(ok),
            ", ".join(miss) if miss else "—",
            ", ".join(pcs) if pcs else "—"])
    band_end = len(rows)
    total = n_ok + n_miss
    rows += [
        [],
        [("Validation summary", _B)],
        ["ICD-10-CM codes validated OK", (n_ok, "num"), _chip("SOURCED")],
        ["ICD-10-CM codes unmatched", (n_miss, "num"),
         _chip("SOURCED" if n_miss == 0 else "ILLUSTRATIVE")],
        ["Validation rate", ((n_ok / total) if total else "—", "pct"),
         _chip("SOURCED")],
        [],
        [("Source / basis", _H),
         "SOURCED · validated against the ICD-10-CM / ICD-10-PCS code set "
         "(NLM Clinical Tables); a coding-integrity check, not a market figure."],
    ]
    return Sheet("Code validation QA", rows, col_widths=[30, 14, 30, 20, 24],
                 freeze_rows=5, merges=merges, band_rows=(band_start, band_end),
                 autofilter=f"A5:E{band_end}")


# ── public entry point ────────────────────────────────────────────────────────
def depth_sheets() -> List[Sheet]:
    """Every analytical-depth sheet, in reading order. Each builder degrades to
    skipped (never raises), so the caller appends the result unconditionally."""
    out: List[Sheet] = []
    for b in (_sensitivity_sheet, _acuity_mix_sheet, _demand_build_sheet,
              _aif_series_sheet, _footprint_national_sheet, _moat_detail_sheet,
              _codes_qa_sheet):
        s = _safe(b)
        if s is not None:
            out.append(s)
    return out
