"""Industry deep dives — real-data layers under the TAM/SAM builder.

The sizing chain (tam_sam.py) answers "how big". A deep dive answers the
questions the IC asks next, grounded in the vendored public data rather
than template assumptions:

  · WHERE — state footprint: facility counts, capacity, top-10 states;
  · WHO — consolidation map: chain landscape, duopoly share, and the
    INDEPENDENT pool (the acquirable whitespace), state by state;
  · HOW WELL — quality by state where CMS publishes it;
  · WHAT TRADED — the sector's own deal history from the public corpus
    (n, realized MOIC, entry multiples) with drill links.

One registry keyed by TAM/SAM template key; each dive declares its data
sources inline. Everything here is computed from files in rcm_mc/data/
(CMS Dialysis Facility Compare, etc.) — no fabricated geography, no
imputed quality. Missing is missing.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional


def _median(vals: List[float]) -> Optional[float]:
    s = sorted(v for v in vals if v is not None)
    if not s:
        return None
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2.0


def dialysis_deep_dive() -> Dict[str, Any]:
    """CMS Dialysis Facility Compare (7.5K facilities) + deals corpus."""
    from ..data.dialysis import load_dialysis_providers
    provs = load_dialysis_providers()

    by_state: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"facilities": 0, "stations": 0, "chain": 0,
                 "independent": 0})
    chains: Dict[str, int] = defaultdict(int)
    for p in provs.values():
        st = p.state or "??"
        row = by_state[st]
        row["facilities"] += 1
        if p.dialysis_stations:
            row["stations"] += int(p.dialysis_stations)
        org = (p.chain_org or "Independent").strip() or "Independent"
        chains[org] += 1
        if org == "Independent":
            row["independent"] += 1
        else:
            row["chain"] += 1

    states = [
        {"state": st, **vals,
         "independent_share": (vals["independent"] / vals["facilities"]
                               if vals["facilities"] else 0.0)}
        for st, vals in by_state.items() if st != "??"
    ]
    states.sort(key=lambda r: -r["facilities"])

    total = sum(r["facilities"] for r in states)
    chain_rows = sorted(
        ({"org": org, "facilities": n, "share": n / total if total else 0}
         for org, n in chains.items()),
        key=lambda r: -r["facilities"])
    top2_share = sum(r["share"] for r in chain_rows
                     if r["org"] != "Independent")and sum(
        r["share"] for r in chain_rows[:2]
        if r["org"] != "Independent")

    # Quality by state — CMS-published risk-adjusted rates, joined on CCN.
    # Median per state, only where ≥5 facilities report (thin slices lie).
    quality_by_state: Dict[str, Dict[str, Any]] = {}
    try:
        import csv
        from pathlib import Path
        qpath = (Path(__file__).resolve().parent.parent / "data"
                 / "dialysis_quality.csv")
        per_state_rates: Dict[str, List[float]] = defaultdict(list)
        with open(qpath, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                ccn = (r.get("ccn") or "").strip()
                p = provs.get(ccn)
                if p is None or not p.state:
                    continue
                try:
                    hosp = float(r.get("hospitalization_rate") or "")
                except ValueError:
                    continue
                per_state_rates[p.state].append(hosp)
        for st, vals in per_state_rates.items():
            if len(vals) >= 5:
                quality_by_state[st] = {
                    "value": _median(vals),
                    "n_reporting": len(vals),
                }
    except Exception:  # noqa: BLE001 — quality layer is additive
        quality_by_state = {}

    # The acquirable pool — states ranked by INDEPENDENT facility count.
    whitespace = sorted(states, key=lambda r: -r["independent"])[:10]

    # Sector deal history from the public corpus.
    sector_deals: Dict[str, Any] = {"n": 0}
    try:
        from ..ui.data_public.deal_search_page import _load_corpus
        deals = [d for d in _load_corpus()
                 if (d.get("sector") or "") == "dialysis"]
        moics = [float(d["realized_moic"]) for d in deals
                 if d.get("realized_moic") is not None]
        mults = []
        for d in deals:
            ev, eb = d.get("ev_mm"), d.get("ebitda_at_entry_mm")
            if ev and eb and float(eb) > 0:
                mults.append(float(ev) / float(eb))
        years = [int(d["year"]) for d in deals if d.get("year")]
        sector_deals = {
            "n": len(deals),
            "n_realized": len(moics),
            "median_moic": _median(moics),
            "median_entry_multiple": _median(mults),
            "year_min": min(years) if years else None,
            "year_max": max(years) if years else None,
        }
    except Exception:  # noqa: BLE001
        pass

    return {
        "industry": "dialysis",
        "facility_source": ("CMS Dialysis Facility Compare "
                            "(DFC_FACILITY), vendored snapshot"),
        "n_facilities": total,
        "states": states,
        "top_states": states[:10],
        "chains": chain_rows[:8],
        "chains_label": "Chain",
        "pool_label": "Independent",
        "pool_note": "independent facilities — the acquirable pool",
        "duopoly_share": top2_share,
        "n_independent": chains.get("Independent", 0),
        "whitespace_states": whitespace,
        "whitespace_mode": "pool",
        "whitespace_note": "states ranked by independent facility count",
        "capacity_label": "Stations",
        "quality_label": "Hosp. rate (med)",
        "quality_by_state": quality_by_state,
        "quality_source": ("CMS DFC risk-adjusted hospitalization rate; "
                           "state median where ≥5 facilities report"),
        "sector_deals": sector_deals,
        "deals_href": "/deal-search?sector=dialysis",
        "screener_href": "/target-screener?vertical=dialysis",
    }


def home_health_deep_dive() -> Dict[str, Any]:
    """CMS Provider Data Catalog HH agencies (12.4K) + star ratings +
    ACS state demographics for the density read."""
    import csv
    from pathlib import Path
    data_dir = Path(__file__).resolve().parent.parent / "data"

    by_state: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"facilities": 0, "chain": 0, "independent": 0,
                 "stations": 0})
    ownership: Dict[str, int] = defaultdict(int)
    state_of_ccn: Dict[str, str] = {}
    with open(data_dir / "home_health_providers.csv", newline="",
              encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            st = (r.get("state") or "").strip().upper()
            if not st:
                continue
            row = by_state[st]
            row["facilities"] += 1
            own = (r.get("ownership") or "").strip().upper()
            # Source file uses "-" / blank for unreported ownership —
            # label it honestly rather than rendering a bare dash.
            if own in ("", "-", "UNKNOWN"):
                own = "NOT REPORTED"
            ownership[own.title()] += 1
            # In HH the M&A-relevant pool is the PROPRIETARY (for-profit)
            # agencies — that's where platforms tuck in. Mapped onto the
            # schema's "independent" slot with the label set accordingly.
            if own == "PROPRIETARY":
                row["independent"] += 1
            else:
                row["chain"] += 1
            ccn = (r.get("ccn") or "").strip()
            if ccn:
                state_of_ccn[ccn] = st

    states = [
        {"state": st, **vals,
         "independent_share": (vals["independent"] / vals["facilities"]
                               if vals["facilities"] else 0.0)}
        for st, vals in by_state.items()
    ]
    states.sort(key=lambda r: -r["facilities"])
    total = sum(r["facilities"] for r in states)

    own_rows = sorted(
        ({"org": own, "facilities": n, "share": n / total if total else 0}
         for own, n in ownership.items()),
        key=lambda r: -r["facilities"])

    # Quality: CMS star rating, state median where ≥5 agencies report.
    quality_by_state: Dict[str, Dict[str, Any]] = {}
    per_state: Dict[str, List[float]] = defaultdict(list)
    try:
        with open(data_dir / "home_health_quality.csv", newline="",
                  encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                st = state_of_ccn.get((r.get("ccn") or "").strip())
                if not st:
                    continue
                try:
                    star = float(r.get("star_rating") or "")
                except ValueError:
                    continue
                per_state[st].append(star)
        for st, vals in per_state.items():
            if len(vals) >= 5:
                quality_by_state[st] = {"value": _median(vals),
                                        "n_reporting": len(vals)}
    except Exception:  # noqa: BLE001
        quality_by_state = {}

    # Density whitespace: agencies per 10K seniors (65+). LOW density =
    # underserved states — the de-novo / capacity whitespace. Real ACS
    # population × pct_65+, never imputed (states missing demographics
    # are skipped).
    whitespace: List[Dict[str, Any]] = []
    try:
        from ..data.county_demographics import demographics_state
        for s in states:
            d = demographics_state(s["state"]) or {}
            pop, p65 = d.get("population"), d.get("pct_age_65_plus")
            if pop and p65:
                seniors = pop * p65
                whitespace.append({
                    **s,
                    "seniors": seniors,
                    "per_10k_seniors": s["facilities"] / (seniors / 10_000),
                })
        whitespace.sort(key=lambda r: r["per_10k_seniors"])
        whitespace = whitespace[:10]
    except Exception:  # noqa: BLE001
        whitespace = []

    sector_deals: Dict[str, Any] = {"n": 0}
    try:
        from ..ui.data_public.deal_search_page import _load_corpus
        deals = [d for d in _load_corpus()
                 if (d.get("sector") or "") == "home_health"]
        moics = [float(d["realized_moic"]) for d in deals
                 if d.get("realized_moic") is not None]
        mults = []
        for d in deals:
            ev, eb = d.get("ev_mm"), d.get("ebitda_at_entry_mm")
            if ev and eb and float(eb) > 0:
                mults.append(float(ev) / float(eb))
        years = [int(d["year"]) for d in deals if d.get("year")]
        sector_deals = {
            "n": len(deals), "n_realized": len(moics),
            "median_moic": _median(moics),
            "median_entry_multiple": _median(mults),
            "year_min": min(years) if years else None,
            "year_max": max(years) if years else None,
        }
    except Exception:  # noqa: BLE001
        pass

    return {
        "industry": "home_health",
        "facility_source": ("CMS Provider Data Catalog — Home Health "
                            "Care Agencies, vendored snapshot"),
        "n_facilities": total,
        "states": states,
        "top_states": states[:10],
        "chains": own_rows[:8],
        "chains_label": "Ownership type",
        "pool_label": "For-profit",
        "pool_note": ("proprietary agencies — where platform M&A "
                      "actually happens"),
        "duopoly_share": None,
        "n_independent": ownership.get("Proprietary", 0),
        "whitespace_states": whitespace,
        "whitespace_mode": "density",
        "whitespace_note": ("agencies per 10K seniors (ACS 65+) — LOWEST "
                            "density first: the underserved states"),
        "capacity_label": None,
        "quality_label": "Star rating (med)",
        "quality_by_state": quality_by_state,
        "quality_source": ("CMS HH star rating; state median where ≥5 "
                           "agencies report"),
        "sector_deals": sector_deals,
        "deals_href": "/deal-search?sector=home_health",
        "screener_href": "/target-screener?vertical=home_health",
    }



def hospice_deep_dive() -> Dict[str, Any]:
    """CMS Hospice General Information (6.9K providers) + care index +
    ACS density. The CA license glut shows up honestly in the density
    read (saturation, not whitespace)."""
    import csv
    from pathlib import Path
    data_dir = Path(__file__).resolve().parent.parent / "data"

    by_state: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"facilities": 0, "chain": 0, "independent": 0,
                 "stations": 0})
    ownership: Dict[str, int] = defaultdict(int)
    state_of_ccn: Dict[str, str] = {}
    with open(data_dir / "hospice_providers.csv", newline="",
              encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            st = (r.get("state") or "").strip().upper()
            if not st:
                continue
            row = by_state[st]
            row["facilities"] += 1
            own = (r.get("ownership") or "").strip()
            if not own or own == "-":
                own = "Not reported"
            ownership[own] += 1
            if own == "For-Profit":
                row["independent"] += 1
            else:
                row["chain"] += 1
            ccn = (r.get("ccn") or "").strip()
            if ccn:
                state_of_ccn[ccn] = st

    states = [
        {"state": st, **vals,
         "independent_share": (vals["independent"] / vals["facilities"]
                               if vals["facilities"] else 0.0)}
        for st, vals in by_state.items()
    ]
    states.sort(key=lambda r: -r["facilities"])
    total = sum(r["facilities"] for r in states)
    own_rows = sorted(
        ({"org": own, "facilities": n, "share": n / total if total else 0}
         for own, n in ownership.items()),
        key=lambda r: -r["facilities"])

    quality_by_state: Dict[str, Dict[str, Any]] = {}
    per_state: Dict[str, List[float]] = defaultdict(list)
    try:
        with open(data_dir / "hospice_quality.csv", newline="",
                  encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                st = state_of_ccn.get((r.get("ccn") or "").strip())
                if not st:
                    continue
                try:
                    idx = float(r.get("care_index_overall") or "")
                except ValueError:
                    continue
                per_state[st].append(idx)
        for st, vals in per_state.items():
            if len(vals) >= 5:
                quality_by_state[st] = {"value": _median(vals),
                                        "n_reporting": len(vals)}
    except Exception:  # noqa: BLE001
        quality_by_state = {}

    whitespace: List[Dict[str, Any]] = []
    try:
        from ..data.county_demographics import demographics_state
        for s in states:
            d = demographics_state(s["state"]) or {}
            pop, p65 = d.get("population"), d.get("pct_age_65_plus")
            if pop and p65:
                seniors = pop * p65
                whitespace.append({
                    **s,
                    "seniors": seniors,
                    "per_10k_seniors": s["facilities"] / (seniors / 10_000),
                })
        whitespace.sort(key=lambda r: r["per_10k_seniors"])
        whitespace = whitespace[:10]
    except Exception:  # noqa: BLE001
        whitespace = []

    sector_deals: Dict[str, Any] = {"n": 0}
    try:
        from ..ui.data_public.deal_search_page import _load_corpus
        deals = [d for d in _load_corpus()
                 if (d.get("sector") or "") == "hospice"]
        moics = [float(d["realized_moic"]) for d in deals
                 if d.get("realized_moic") is not None]
        mults = []
        for d in deals:
            ev, eb = d.get("ev_mm"), d.get("ebitda_at_entry_mm")
            if ev and eb and float(eb) > 0:
                mults.append(float(ev) / float(eb))
        years = [int(d["year"]) for d in deals if d.get("year")]
        sector_deals = {
            "n": len(deals), "n_realized": len(moics),
            "median_moic": _median(moics),
            "median_entry_multiple": _median(mults),
            "year_min": min(years) if years else None,
            "year_max": max(years) if years else None,
        }
    except Exception:  # noqa: BLE001
        pass

    return {
        "industry": "hospice",
        "facility_source": ("CMS Provider Data Catalog — Hospice General "
                            "Information, vendored snapshot"),
        "n_facilities": total,
        "states": states,
        "top_states": states[:10],
        "chains": own_rows[:8],
        "chains_label": "Ownership type",
        "pool_label": "For-profit",
        "pool_note": ("for-profit providers — 69% of the universe; the "
                      "most PE-penetrated post-acute vertical"),
        "duopoly_share": None,
        "n_independent": ownership.get("For-Profit", 0),
        "whitespace_states": whitespace,
        "whitespace_mode": "density",
        "whitespace_note": ("providers per 10K seniors (ACS 65+), lowest "
                            "first — NOTE the CA glut sits at the other "
                            "end of this ranking"),
        "capacity_label": None,
        "quality_label": "Care index (med)",
        "quality_by_state": quality_by_state,
        "quality_source": ("CMS hospice care-index composite (0–10); "
                           "state median where ≥5 providers report"),
        "sector_deals": sector_deals,
        "deals_href": "/deal-search?sector=hospice",
        "screener_href": "/target-screener?vertical=hospice",
    }


# Registry keyed by TAM/SAM template key. Industries are added one at a
# time as their data layers land (the deep-dive sprint).
DEEP_DIVES: Dict[str, Callable[[], Dict[str, Any]]] = {
    "dialysis": dialysis_deep_dive,
    "home_health": home_health_deep_dive,
    "hospice": hospice_deep_dive,
}


def deep_dive_for(template_key: str) -> Optional[Dict[str, Any]]:
    fn = DEEP_DIVES.get(template_key)
    if fn is None:
        return None
    try:
        return fn()
    except Exception:  # noqa: BLE001 — the dive is additive, never a 500
        return None
