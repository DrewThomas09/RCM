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


def _chain_hhi(chains: List[Dict[str, Any]], pool_label: str) -> Optional[float]:
    """Chain-concentration HHI (DOJ/FTC scale, 0–10,000) over the NAMED
    operators — the fragmented independent/for-profit pool is treated as
    atomized (each unit ~0), which is the standard read: it measures how
    concentrated the CHAIN layer is, the number PE diligence cares about.
    None when there are no named chains to measure."""
    named = [c for c in chains
             if c["org"] not in (pool_label, "Independent", "For-profit",
                                 "Not reported")
             and "for-profit" not in c["org"].lower()
             and "mid-size" not in c["org"].lower()
             and "small" not in c["org"].lower()
             and "large" not in c["org"].lower()
             and "npr not filed" not in c["org"].lower()]
    if not named:
        return None
    return round(sum((c["share"] * 100) ** 2 for c in named), 0)


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



def snf_deep_dive() -> Dict[str, Any]:
    """CMS Nursing Home Care Compare (14.7K facilities, 1.57M certified
    beds) — the richest vertical file: real capacity, occupancy, star
    ratings, and 12-month change-of-ownership flags (live M&A turnover)."""
    import csv
    from pathlib import Path
    data_dir = Path(__file__).resolve().parent.parent / "data"

    by_state: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"facilities": 0, "chain": 0, "independent": 0,
                 "stations": 0})
    ownership: Dict[str, int] = defaultdict(int)
    state_of_ccn: Dict[str, str] = {}
    chow_12mo = 0
    with open(data_dir / "snf_providers.csv", newline="",
              encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            st = (r.get("state") or "").strip().upper()
            if not st:
                continue
            row = by_state[st]
            row["facilities"] += 1
            try:
                row["stations"] += int(float(r.get("certified_beds") or 0))
            except (TypeError, ValueError):
                pass
            own_raw = (r.get("ownership") or "").strip()
            # Collapse the CMS sub-types ("For profit - LLC/Corp/…") to
            # the three buckets the IC reads; keep the detail out of the
            # headline but honest in the bucket name.
            if own_raw.lower().startswith("for profit"):
                own = "For-profit (all forms)"
            elif own_raw.lower().startswith("non profit"):
                own = "Non-profit"
            elif own_raw.lower().startswith("government"):
                own = "Government"
            else:
                own = "Not reported"
            ownership[own] += 1
            if own == "For-profit (all forms)":
                row["independent"] += 1
            else:
                row["chain"] += 1
            if (r.get("changed_ownership_12mo") or "").strip().upper() == "Y":
                chow_12mo += 1
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
        with open(data_dir / "snf_quality.csv", newline="",
                  encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                st = state_of_ccn.get((r.get("ccn") or "").strip())
                if not st:
                    continue
                try:
                    star = float(r.get("overall_rating") or "")
                except ValueError:
                    continue
                per_state[st].append(star)
        for st, vals in per_state.items():
            if len(vals) >= 5:
                quality_by_state[st] = {"value": _median(vals),
                                        "n_reporting": len(vals)}
    except Exception:  # noqa: BLE001
        quality_by_state = {}

    # Whitespace: certified BEDS per 10K seniors, lowest first — supply
    # gaps where the 80+ wave lands hardest.
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
                    "per_10k_seniors": s["stations"] / (seniors / 10_000),
                })
        whitespace.sort(key=lambda r: r["per_10k_seniors"])
        whitespace = whitespace[:10]
    except Exception:  # noqa: BLE001
        whitespace = []

    sector_deals: Dict[str, Any] = {"n": 0}
    try:
        from ..ui.data_public.deal_search_page import _load_corpus
        deals = [d for d in _load_corpus()
                 if (d.get("sector") or "") in ("snf", "post_acute",
                                                "skilled_nursing")]
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
        "industry": "snf",
        "facility_source": ("CMS Nursing Home Care Compare "
                            "(NH_ProviderInfo), vendored snapshot"),
        "n_facilities": total,
        "states": states,
        "top_states": states[:10],
        "chains": own_rows[:8],
        "chains_label": "Ownership type",
        "pool_label": "For-profit",
        "pool_note": (f"for-profit facilities; {chow_12mo:,} facilities "
                      "changed ownership in the last 12 months — the "
                      "live M&A turnover signal"),
        "duopoly_share": None,
        "n_independent": ownership.get("For-profit (all forms)", 0),
        "whitespace_states": whitespace,
        "whitespace_mode": "density",
        "whitespace_note": ("certified BEDS per 10K seniors, lowest "
                            "first — supply gaps where the 80+ wave "
                            "lands hardest"),
        "capacity_label": "Beds",
        "quality_label": "Star rating (med)",
        "quality_by_state": quality_by_state,
        "quality_source": ("CMS overall star rating; state median where "
                           "≥5 facilities report"),
        "chow_12mo": chow_12mo,
        "sector_deals": sector_deals,
        "deals_href": "/deal-search?sector=post_acute",
        "screener_href": "/target-screener?vertical=snf",
    }



def _simple_provider_dive(*, industry: str, providers_csv: str,
                          quality_csv: str, quality_col: str,
                          quality_label: str, quality_note: str,
                          facility_source: str, sector_tokens: tuple,
                          screener_vertical: str,
                          pool_match: str = "for profit") -> Dict[str, Any]:
    """Shared dive for the CCN/state/ownership-shaped CMS files (IRF,
    LTCH). Pool = for-profit; whitespace = facilities per 10K seniors."""
    import csv
    from pathlib import Path
    data_dir = Path(__file__).resolve().parent.parent / "data"

    by_state: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"facilities": 0, "chain": 0, "independent": 0,
                 "stations": 0})
    ownership: Dict[str, int] = defaultdict(int)
    state_of_ccn: Dict[str, str] = {}
    with open(data_dir / providers_csv, newline="",
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
            if own.lower().startswith(pool_match):
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
    n_pool = sum(n for own, n in ownership.items()
                 if own.lower().startswith(pool_match))

    quality_by_state: Dict[str, Dict[str, Any]] = {}
    per_state: Dict[str, List[float]] = defaultdict(list)
    try:
        with open(data_dir / quality_csv, newline="",
                  encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                st = state_of_ccn.get((r.get("ccn") or "").strip())
                if not st:
                    continue
                try:
                    v = float(r.get(quality_col) or "")
                except ValueError:
                    continue
                per_state[st].append(v)
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
                 if (d.get("sector") or "") in sector_tokens]
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
        "industry": industry,
        "facility_source": facility_source,
        "n_facilities": total,
        "states": states,
        "top_states": states[:10],
        "chains": own_rows[:8],
        "chains_label": "Ownership type",
        "pool_label": "For-profit",
        "pool_note": "for-profit facilities — the M&A-active pool",
        "duopoly_share": None,
        "n_independent": n_pool,
        "whitespace_states": whitespace,
        "whitespace_mode": "density",
        "whitespace_note": ("facilities per 10K seniors (ACS 65+), "
                            "lowest first"),
        "capacity_label": None,
        "quality_label": quality_label,
        "quality_by_state": quality_by_state,
        "quality_source": quality_note,
        "sector_deals": sector_deals,
        "deals_href": f"/deal-search?sector={sector_tokens[0]}",
        "screener_href": f"/target-screener?vertical={screener_vertical}",
    }


def irf_deep_dive() -> Dict[str, Any]:
    return _simple_provider_dive(
        industry="irf",
        providers_csv="irf_providers.csv",
        quality_csv="irf_quality.csv",
        quality_col="dtc_rs_rate",
        quality_label="DTC rate (med)",
        quality_note=("CMS IRF discharge-to-community rate (risk-"
                      "standardized, higher better); state median where "
                      "≥5 facilities report"),
        facility_source=("CMS Inpatient Rehabilitation Facility Compare, "
                         "vendored snapshot"),
        sector_tokens=("post_acute", "rehabilitation", "irf"),
        screener_vertical="irf",
    )


def ltch_deep_dive() -> Dict[str, Any]:
    return _simple_provider_dive(
        industry="ltch",
        providers_csv="ltch_providers.csv",
        quality_csv="ltch_quality.csv",
        quality_col="dtc_rs_rate",
        quality_label="DTC rate (med)",
        quality_note=("CMS LTCH discharge-to-community rate (risk-"
                      "standardized, higher better); state median where "
                      "≥5 facilities report"),
        facility_source=("CMS Long-Term Care Hospital Compare, vendored "
                         "snapshot"),
        sector_tokens=("post_acute", "ltch"),
        screener_vertical="ltch",
    )



def _deals_only_dive(*, industry: str, sector_tokens: tuple,
                     note: str) -> Dict[str, Any]:
    """For verticals WITHOUT a vendored CMS facility file: the honest
    layer is the sector's own deal history — geography is omitted rather
    than fabricated."""
    sector_deals: Dict[str, Any] = {"n": 0}
    try:
        from ..ui.data_public.deal_search_page import _load_corpus
        deals = [d for d in _load_corpus()
                 if (d.get("sector") or "").lower().replace(" ", "_")
                 in sector_tokens]
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
        "industry": industry,
        "deals_only": True,
        "geo_note": note,
        "sector_deals": sector_deals,
        "deals_href": f"/deal-search?sector={sector_tokens[0]}",
    }


def behavioral_health_deep_dive() -> Dict[str, Any]:
    return _deals_only_dive(
        industry="behavioral_health",
        sector_tokens=("behavioral_health",),
        note=("CMS publishes no national behavioral-health facility "
              "file — geography is omitted rather than fabricated. The "
              "real layer here is the sector's own deal history."),
    )


def asc_deep_dive() -> Dict[str, Any]:
    return _deals_only_dive(
        industry="asc",
        sector_tokens=("asc", "ambulatory_surgery"),
        note=("The CMS ASC file isn't vendored yet — geography omitted "
              "rather than fabricated; the deal history below is real."),
    )



def fertility_deep_dive() -> Dict[str, Any]:
    return _deals_only_dive(
        industry="fertility_ivf",
        sector_tokens=("fertility", "women's_health"),
        note=("CDC ART clinic-level data isn't vendored yet — geography "
              "omitted rather than fabricated; the corpus fertility "
              "deals below are real."),
    )


def physician_group_deep_dive() -> Dict[str, Any]:
    return _deals_only_dive(
        industry="physician_group",
        sector_tokens=("physician_group", "physician_practice"),
        note=("No national physician-practice facility file exists — "
              "geography omitted rather than fabricated. 17 corpus "
              "deals carry the sector's trading history."),
    )


def dental_deep_dive() -> Dict[str, Any]:
    return _deals_only_dive(
        industry="dental",
        sector_tokens=("dental",),
        note=("No CMS dental facility file — geography omitted rather "
              "than fabricated; the DSO deal history below is real."),
    )


def oncology_deep_dive() -> Dict[str, Any]:
    return _deals_only_dive(
        industry="oncology",
        sector_tokens=("oncology",),
        note=("No national community-oncology facility file — "
              "geography omitted rather than fabricated."),
    )


def urgent_care_deep_dive() -> Dict[str, Any]:
    return _deals_only_dive(
        industry="urgent_care",
        sector_tokens=("urgent_care",),
        note=("No CMS urgent-care file (UCA census is proprietary) — "
              "geography omitted rather than fabricated."),
    )



def hospitals_deep_dive() -> Dict[str, Any]:
    """The flagship dive — computed from the vendored HCRIS universe
    (6.1K cost-report filers): state footprint ranked by REAL filed NPR,
    the size-tier mix (HCRIS carries no ownership field — size is the
    honest structure read), state median operating margins, and the
    corpus's hospital deal history. The "pool" is the $250M–$1B
    mid-size filers — the PE/JV-able middle the template's thesis
    segment names."""
    from ..data.hcris import _get_latest_per_ccn
    df = _get_latest_per_ccn()

    MID_LO, MID_HI = 250e6, 1e9
    by_state: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"facilities": 0, "chain": 0, "independent": 0,
                 "stations": 0, "npr": 0.0})
    margins: Dict[str, List[float]] = defaultdict(list)
    medicare_mix: Dict[str, List[float]] = defaultdict(list)
    tiers: Dict[str, int] = defaultdict(int)
    for _, r in df.iterrows():
        st = str(r.get("state") or "").strip().upper()
        if not st:
            continue
        row = by_state[st]
        row["facilities"] += 1
        try:
            beds = float(r.get("beds") or 0)
            if beds == beds:
                row["stations"] += int(beds)
        except (TypeError, ValueError):
            pass
        nprf = None
        try:
            nprf = float(r.get("net_patient_revenue"))
            if nprf != nprf or nprf <= 0:
                nprf = None
        except (TypeError, ValueError):
            nprf = None
        if nprf:
            row["npr"] += nprf
            if nprf >= MID_HI:
                tiers["Large (>$1B NPR)"] += 1
            elif nprf >= MID_LO:
                tiers["Mid-size ($250M–$1B)"] += 1
                row["independent"] += 1   # the PE-able pool slot
            else:
                tiers["Small (<$250M)"] += 1
        else:
            tiers["NPR not filed"] += 1
        if nprf and not (MID_LO <= nprf < MID_HI):
            row["chain"] += 1
        try:
            opex = float(r.get("operating_expenses") or 0)
            if nprf and opex and nprf > 1e5:
                m = (nprf - opex) / nprf
                if -0.40 <= m <= 0.30:
                    margins[st].append(m)
        except (TypeError, ValueError):
            pass
        # The payer dimension — filed Medicare day share per hospital,
        # state median below. Real HCRIS, never imputed.
        try:
            mp = float(r.get("medicare_day_pct"))
            if mp == mp and 0.0 <= mp <= 1.0:
                medicare_mix[st].append(mp)
        except (TypeError, ValueError):
            pass

    states = [
        {"state": st, **vals,
         "independent_share": (vals["independent"] / vals["facilities"]
                               if vals["facilities"] else 0.0)}
        for st, vals in by_state.items()
    ]
    # Rank by NPR — dollars, not facility count: this is the one dive
    # where the real revenue base is in the data.
    states.sort(key=lambda r: -r["npr"])
    total = sum(r["facilities"] for r in states)
    tier_rows = sorted(
        ({"org": t, "facilities": n, "share": n / total if total else 0}
         for t, n in tiers.items()),
        key=lambda r: -r["facilities"])

    quality_by_state = {
        st: {"value": _median(vals) * 100, "n_reporting": len(vals)}
        for st, vals in margins.items() if len(vals) >= 5
    }
    mcare_by_state = {
        st: _median(vals) for st, vals in medicare_mix.items()
        if len(vals) >= 5
    }
    for s in states:
        mm = mcare_by_state.get(s["state"])
        if mm is not None:
            s["medicare_mix_med"] = mm

    sector_deals: Dict[str, Any] = {"n": 0}
    try:
        from ..ui.data_public.deal_search_page import _load_corpus
        deals = [d for d in _load_corpus()
                 if (d.get("sector") or "") == "hospital"]
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

    n_mid = tiers.get("Mid-size ($250M–$1B)", 0)
    return {
        "industry": "hospitals",
        "facility_source": ("CMS HCRIS cost reports (vendored, latest "
                            "filing per CCN) — state NPR totals are "
                            "real filed dollars"),
        "n_facilities": total,
        "states": states,
        "top_states": states[:10],
        "chains": tier_rows,
        "chains_label": "NPR size tier",
        "pool_label": "Mid-size",
        "pool_note": ("$250M–$1B NPR filers — the PE/JV-able middle "
                      "(HCRIS files no ownership field; size is the "
                      "honest structure read)"),
        "duopoly_share": None,
        "n_independent": n_mid,
        "whitespace_states": sorted(
            states, key=lambda r: -r["independent"])[:10],
        "whitespace_mode": "pool",
        "whitespace_note": "states ranked by mid-size ($250M–$1B) filer "
                           "count",
        "capacity_label": "Beds",
        "quality_label": "Op margin % (med)",
        "quality_by_state": quality_by_state,
        "quality_source": ("HCRIS (NPR − opex) ÷ NPR, −40%..+30% "
                           "plausibility band; state median where ≥5 "
                           "filers"),
        "sector_deals": sector_deals,
        "deals_href": "/deal-search?sector=hospital",
        "screener_href": "/target-screener?vertical=hospitals",
    }



def infusion_deep_dive() -> Dict[str, Any]:
    return _deals_only_dive(
        industry="infusion",
        sector_tokens=("infusion", "home_infusion"),
        note=("No CMS infusion-suite facility file exists — geography "
              "omitted rather than fabricated; the corpus infusion "
              "deals below are real."),
    )


def imaging_deep_dive() -> Dict[str, Any]:
    return _deals_only_dive(
        industry="imaging",
        sector_tokens=("radiology", "radiology_imaging", "imaging"),
        note=("The IMV imaging-center census is proprietary — geography "
              "omitted rather than fabricated; the corpus radiology "
              "deals below are real."),
    )


def physical_therapy_deep_dive() -> Dict[str, Any]:
    return _deals_only_dive(
        industry="physical_therapy",
        sector_tokens=("physical_therapy", "physical therapy"),
        note=("No national PT-clinic facility file — geography omitted "
              "rather than fabricated; the corpus PT deals below are "
              "real."),
    )



def veterinary_deep_dive() -> Dict[str, Any]:
    return _deals_only_dive(
        industry="veterinary",
        sector_tokens=("veterinary", "vet", "animal_health"),
        note=("No public veterinary facility census (AVMA data is "
              "member-gated) — geography omitted rather than "
              "fabricated."),
    )


def medspa_deep_dive() -> Dict[str, Any]:
    return _deals_only_dive(
        industry="medspa",
        sector_tokens=("medspa", "aesthetics", "medical_aesthetics"),
        note=("AmSpa's location census is proprietary — geography "
              "omitted rather than fabricated."),
    )


def ems_deep_dive() -> Dict[str, Any]:
    return _deals_only_dive(
        industry="ems",
        sector_tokens=("ems", "ambulance", "medical_transport"),
        note=("NEMSIS agency-level data isn't vendored — geography "
              "omitted rather than fabricated."),
    )


# Registry keyed by TAM/SAM template key. Industries are added one at a
# time as their data layers land (the deep-dive sprint).
DEEP_DIVES: Dict[str, Callable[[], Dict[str, Any]]] = {
    "dialysis": dialysis_deep_dive,
    "home_health": home_health_deep_dive,
    "hospice": hospice_deep_dive,
    "snf": snf_deep_dive,
    "irf": irf_deep_dive,
    "ltch": ltch_deep_dive,
    "behavioral_health": behavioral_health_deep_dive,
    "asc": asc_deep_dive,
    "physician_group": physician_group_deep_dive,
    "dental": dental_deep_dive,
    "oncology": oncology_deep_dive,
    "urgent_care": urgent_care_deep_dive,
    "hospitals": hospitals_deep_dive,
    "fertility_ivf": fertility_deep_dive,
    "infusion": infusion_deep_dive,
    "imaging": imaging_deep_dive,
    "physical_therapy": physical_therapy_deep_dive,
    "veterinary": veterinary_deep_dive,
    "medspa": medspa_deep_dive,
    "ems": ems_deep_dive,
}


def deep_dive_for(template_key: str) -> Optional[Dict[str, Any]]:
    fn = DEEP_DIVES.get(template_key)
    if fn is None:
        return None
    try:
        return fn()
    except Exception:  # noqa: BLE001 — the dive is additive, never a 500
        return None
