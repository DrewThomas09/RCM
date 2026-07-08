"""Market-report analytics — shared, reusable, SOURCED computations.

The market-report *dossiers* (``reports/<slug>.py``) author the qualitative
industry knowledge; this module supplies the **quantitative** deep sections
that must be computed from OUR vendored data rather than typed by hand:

  * :func:`state_breakdown` — per-state facility count, for-profit share, and
    (where a chain field exists) chain concentration / HHI, sorted, with a
    computed one-line ``insight``. SOURCED from the vendored provider roll.
  * :func:`supply_trend` — the certification-vintage cohort of currently-open
    facilities: net adds per year, the cumulative curve, a CAGR over the
    reliable window, and the peak-build (inflection) year — a real trended
    series ready for the renderer's chart. SOURCED where the provider file
    carries usable certification dates; an honest "unavailable offline" marker
    otherwise (the renderer then shows the state table + a note, never a fake
    chart).
  * :func:`hcris_margin_trend` — optional multi-year operating-margin trend;
    returns an honest unavailable marker offline rather than fabricating one.

Design contract (mirrors the honesty invariant of the subsystem):

  * Pure functions, no network, fast (the CSV read is cached per file).
  * Every returned record names the exact dataset in ``source_label``.
  * The degenerate/missing case NEVER raises — it returns ``available=False``
    (or empty rows) so a caller can render an honest note instead of crashing.
  * A per-capita denominator is never fabricated: density here is expressed as
    a share of the national facility base, not per-population, because no
    cleanly-offline state population source is vendored for this module. (The
    deep-dive's density read, where it exists, uses real ACS demographics.)

These are the helpers a subsector module — or the renderer — calls by slug.
The provider-CSV-backed slugs are the six with a vendored facility roll that
carries ``state`` + ``ownership`` (+ often ``certification_date``):
``dialysis, snf, home_health, hospice, irf, ltch``. Every other subsector is
"deals-only" (no national facility file); for those, both functions return an
honest unavailable marker.
"""
from __future__ import annotations

import csv
import functools
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


# ── Which slugs have a vendored provider roll, and how to read it ────────────
@dataclass(frozen=True)
class _CsvSpec:
    csv: str                    # filename under rcm_mc/data/
    dataset: str                # human dataset name for source_label
    ownership_col: str = "ownership"
    chain_col: Optional[str] = None      # named-operator column, if any
    cert_col: str = "certification_date"
    capacity_col: Optional[str] = None
    capacity_label: str = ""


# The chain column exists only for dialysis (chain_org names the real
# operators — DaVita/Fresenius/…). SNF/HH/hospice/IRF/LTCH carry ownership
# TYPE but no operator name, so chain HHI is honestly unavailable there.
_PROVIDER_CSV: Dict[str, _CsvSpec] = {
    "dialysis": _CsvSpec(
        "dialysis_providers.csv",
        "CMS Dialysis Facility Compare (DFC_FACILITY), vendored snapshot",
        chain_col="chain_org", capacity_col="dialysis_stations",
        capacity_label="stations"),
    "snf": _CsvSpec(
        "snf_providers.csv",
        "CMS Nursing Home Care Compare (NH_ProviderInfo), vendored snapshot",
        capacity_col="certified_beds", capacity_label="certified beds"),
    "home_health": _CsvSpec(
        "home_health_providers.csv",
        "CMS Provider Data Catalog — Home Health Care Agencies, vendored "
        "snapshot"),
    "hospice": _CsvSpec(
        "hospice_providers.csv",
        "CMS Provider Data Catalog — Hospice General Information, vendored "
        "snapshot"),
    "irf": _CsvSpec(
        "irf_providers.csv",
        "CMS Inpatient Rehabilitation Facility Compare, vendored snapshot"),
    "ltch": _CsvSpec(
        "ltch_providers.csv",
        "CMS Long-Term Care Hospital Compare, vendored snapshot",
        capacity_col="total_beds", capacity_label="beds"),
}

# The "chain" layer is only meaningful for named operators; these tokens are
# the fragmented/atomized pool, excluded from chain-HHI (mirrors the read in
# industry_deep_dive._chain_hhi).
_NON_CHAIN_TOKENS = ("independent", "other", "not reported", "")


def provider_backed_slugs() -> List[str]:
    """Slugs with a vendored provider roll (state breakdown available)."""
    return list(_PROVIDER_CSV)


# ── Cached CSV read ─────────────────────────────────────────────────────────
@functools.lru_cache(maxsize=16)
def _read_rows(path_str: str) -> Tuple[Dict[str, str], ...]:
    """Read a provider CSV once; cache the parsed rows (immutable tuple).

    Cached because a report render can touch the same file for both the state
    breakdown and the supply trend, and the /market index may render several
    dossiers in one process."""
    p = Path(path_str)
    if not p.exists():
        return ()
    with open(p, newline="", encoding="utf-8") as fh:
        return tuple(dict(r) for r in csv.DictReader(fh))


def _spec_for(slug_or_csv: str) -> Tuple[Optional[_CsvSpec], Optional[Path]]:
    """Resolve the argument to a (spec, path). Accepts a known slug or a
    provider-CSV path/filename (with a default spec)."""
    key = (slug_or_csv or "").strip()
    spec = _PROVIDER_CSV.get(key)
    if spec is not None:
        return spec, _DATA_DIR / spec.csv
    if key.endswith(".csv"):
        p = Path(key)
        if not p.is_absolute():
            p = _DATA_DIR / p.name
        # A bare CSV gets the conservative default shape (ownership + cert,
        # no named-chain column).
        return _CsvSpec(p.name, f"{p.name}, vendored provider roll"), p
    return None, None


# ── Ownership classification ────────────────────────────────────────────────
def _for_profit(own_raw: str) -> Optional[bool]:
    """Classify an ownership string as for-profit / not / unusable.

    Returns True (for-profit), False (non-profit / government / other), or
    None when ownership is genuinely unreported ("", "-") — those rows are
    excluded from the share denominator so the percentage stays honest. The
    matcher handles the vendored quirks: dialysis stores the bare token
    ``Profit`` (not "For profit"), home health uses ``PROPRIETARY``, SNF uses
    ``For profit - LLC/Corp/…``, hospice uses ``For-Profit``."""
    o = (own_raw or "").strip().lower()
    if o in ("", "-", "unknown", "not reported", "npr not filed"):
        return None
    if o.startswith("non"):          # non-profit / non profit
        return False
    if o.startswith("gov"):
        return False
    if (o == "proprietary" or o.startswith("profit")
            or o.startswith("for profit") or o.startswith("for-profit")
            or "for profit" in o or "for-profit" in o):
        return True
    # combination / physician / tribal / other → usable, but not for-profit.
    return False


# ── State breakdown ─────────────────────────────────────────────────────────
@dataclass
class StateRow:
    state: str
    facilities: int
    facilities_share: float            # of the national facility base
    for_profit: int
    for_profit_share: Optional[float]  # within-state, over usable ownership
    chain_top_share: Optional[float]   # largest single operator's local share


@dataclass
class StateBreakdown:
    slug: str
    available: bool
    rows: List[StateRow] = field(default_factory=list)  # sorted desc by count
    n_states: int = 0
    n_facilities: int = 0
    national_for_profit_share: Optional[float] = None
    top5_share: float = 0.0            # top-5 states' share of the base
    chain_hhi: Optional[float] = None  # DOJ/FTC scale 0–10,000 (named chains)
    top_chains: List[Tuple[str, int, float]] = field(default_factory=list)
    for_profit_label: str = ""         # how for-profit was matched (honesty)
    insight: str = ""
    source_label: str = ""
    note: str = ""


def state_breakdown(slug_or_csv: str) -> StateBreakdown:
    """Per-state facility footprint, for-profit mix, and chain concentration.

    SOURCED from the vendored provider roll for ``slug_or_csv``. Returns
    ``available=False`` (empty rows) for a deals-only subsector or a missing
    file — the caller renders an honest note, never a fabricated map."""
    spec, path = _spec_for(slug_or_csv)
    if spec is None or path is None:
        return StateBreakdown(
            slug=slug_or_csv, available=False,
            note=("No vendored facility roll for this subsector — geography is "
                  "omitted rather than fabricated (a deals-only vertical)."))
    rows = _read_rows(str(path))
    if not rows:
        return StateBreakdown(
            slug=slug_or_csv, available=False,
            note=f"Provider file {spec.csv} is not present offline.")

    per_state: Dict[str, Dict[str, object]] = {}
    chains_nat: Dict[str, int] = {}
    fp_nat = 0
    fp_known_nat = 0
    for r in rows:
        st = (r.get("state") or "").strip().upper()
        if not st or len(st) != 2:
            continue
        s = per_state.setdefault(
            st, {"facilities": 0, "fp": 0, "fp_known": 0,
                 "chains": {}})
        s["facilities"] = int(s["facilities"]) + 1  # type: ignore[index]
        fp = _for_profit(r.get(spec.ownership_col, ""))
        if fp is not None:
            s["fp_known"] = int(s["fp_known"]) + 1   # type: ignore[index]
            fp_known_nat += 1
            if fp:
                s["fp"] = int(s["fp"]) + 1           # type: ignore[index]
                fp_nat += 1
        if spec.chain_col:
            org = (r.get(spec.chain_col) or "").strip() or "Independent"
            cd = s["chains"]                          # type: ignore[assignment]
            cd[org] = cd.get(org, 0) + 1              # type: ignore[union-attr]
            if org.strip().lower() not in _NON_CHAIN_TOKENS:
                chains_nat[org] = chains_nat.get(org, 0) + 1

    total = sum(int(s["facilities"]) for s in per_state.values())
    if not total:
        return StateBreakdown(
            slug=slug_or_csv, available=False,
            note=f"No state-tagged rows in {spec.csv}.")

    out_rows: List[StateRow] = []
    for st, s in per_state.items():
        n = int(s["facilities"])
        fpk = int(s["fp_known"])
        chains = s["chains"]                          # type: ignore[assignment]
        top_local = (max(chains.values()) / n         # type: ignore[union-attr]
                     if spec.chain_col and chains else None)
        out_rows.append(StateRow(
            state=st, facilities=n, facilities_share=n / total,
            for_profit=int(s["fp"]),
            for_profit_share=(int(s["fp"]) / fpk if fpk else None),
            chain_top_share=top_local))
    out_rows.sort(key=lambda r: -r.facilities)

    nat_fp = (fp_nat / fp_known_nat) if fp_known_nat else None
    top5 = sum(r.facilities_share for r in out_rows[:5])

    # Chain HHI over NAMED operators (national share² sum, DOJ/FTC scale).
    chain_hhi: Optional[float] = None
    top_chains: List[Tuple[str, int, float]] = []
    if chains_nat:
        named_total = sum(chains_nat.values())
        chain_hhi = round(
            sum((n / total * 100) ** 2 for n in chains_nat.values()), 0)
        top_chains = sorted(
            ((org, n, n / total) for org, n in chains_nat.items()),
            key=lambda t: -t[1])[:6]
        _ = named_total  # (kept for readability; HHI uses the full base)

    fp_label = "PROPRIETARY" if slug_or_csv == "home_health" else "for-profit"
    insight = _state_insight(slug_or_csv, out_rows, nat_fp, top5,
                             chain_hhi, top_chains, fp_label)

    return StateBreakdown(
        slug=slug_or_csv, available=True, rows=out_rows,
        n_states=len(out_rows), n_facilities=total,
        national_for_profit_share=nat_fp, top5_share=top5,
        chain_hhi=chain_hhi, top_chains=top_chains,
        for_profit_label=fp_label, insight=insight,
        source_label=f"SOURCED · {spec.dataset}")


def _state_insight(slug: str, rows: List[StateRow],
                   nat_fp: Optional[float], top5: float,
                   chain_hhi: Optional[float],
                   top_chains: List[Tuple[str, int, float]],
                   fp_label: str) -> str:
    """A computed one-line read of the state breakdown (no fabricated figures —
    every number in the sentence comes from ``rows``)."""
    if not rows:
        return ""
    top = rows[:2]
    top_names = " and ".join(r.state for r in top)
    top_share = sum(r.facilities_share for r in top)
    parts = [
        f"{top_names} hold {top_share * 100:.1f}% of the {len(rows)}-state "
        f"facility base (top-5 states {top5 * 100:.1f}%)."
    ]
    if nat_fp is not None:
        parts.append(f"{fp_label.capitalize()} share runs {nat_fp * 100:.1f}% "
                     "nationally")
        # Call out the state that most skews for-profit among the larger states.
        big = [r for r in rows if r.facilities >= 20
               and r.for_profit_share is not None]
        if big:
            hi = max(big, key=lambda r: r.for_profit_share or 0.0)
            parts[-1] += (f", peaking near {(hi.for_profit_share or 0) * 100:.0f}% "
                          f"in {hi.state}.")
        else:
            parts[-1] += "."
    if chain_hhi is not None and top_chains:
        lead = top_chains[0]
        parts.append(
            f"Chain layer is concentrated (HHI {chain_hhi:,.0f}); "
            f"{lead[0]} leads at {lead[2] * 100:.1f}% of facilities.")
    return " ".join(parts)


# ── Certification-vintage supply trend ──────────────────────────────────────
@dataclass
class SupplyPoint:
    year: int
    net_adds: int          # currently-open facilities certified that year
    cumulative: int


@dataclass
class CohortBar:
    label: str             # e.g. "1990–94"
    net_adds: int


@dataclass
class SupplyTrend:
    slug: str
    available: bool
    points: List[SupplyPoint] = field(default_factory=list)
    cohorts: List[CohortBar] = field(default_factory=list)
    window_start: Optional[int] = None
    window_end: Optional[int] = None
    cagr: Optional[float] = None          # cumulative-count CAGR, fraction/yr
    inflection_year: Optional[int] = None  # peak net-adds year in the window
    peak_cohort: Optional[str] = None
    n_facilities: int = 0
    source_label: str = ""
    note: str = ""
    takeaway: str = ""


def _cert_year(raw: str) -> Optional[int]:
    """Parse a certification date (ISO ``YYYY-MM-DD`` or US ``MM/DD/YYYY``) to
    a 4-digit year. Returns None for blanks/garbage."""
    v = (raw or "").strip()
    if not v:
        return None
    if "-" in v and len(v) >= 4 and v[:4].isdigit():
        y = v[:4]
    elif "/" in v:
        parts = v.split("/")
        y = parts[2] if len(parts) == 3 else ""
    else:
        return None
    if y.isdigit() and len(y) == 4:
        yi = int(y)
        if 1950 <= yi <= 2100:
            return yi
    return None


def supply_trend(slug_or_csv: str) -> SupplyTrend:
    """Facilities by certification-year cohort — the real supply trajectory.

    Builds the count of *currently-open* facilities by the year they were
    Medicare-certified (net adds), the cumulative curve, the CAGR of that
    cumulative over the reliable window (excluding the partial current year and
    the sparse early tail), and the peak-build (inflection) year. SOURCED where
    the provider file carries usable certification dates; ``available=False``
    otherwise.

    Honesty: this is the certification vintage of the *surviving* stock (closed
    facilities are not in the file), so it reads supply momentum, not a
    reconstructed historical census — the ``note`` says so."""
    spec, path = _spec_for(slug_or_csv)
    if spec is None or path is None:
        return SupplyTrend(
            slug=slug_or_csv, available=False,
            note=("No vendored facility roll for this subsector — a "
                  "certification-vintage supply trend is unavailable offline."))
    rows = _read_rows(str(path))
    if not rows:
        return SupplyTrend(
            slug=slug_or_csv, available=False,
            note=f"Provider file {spec.csv} is not present offline.")

    by_year: Dict[int, int] = {}
    total = 0
    for r in rows:
        y = _cert_year(r.get(spec.cert_col, ""))
        if y is None:
            continue
        by_year[y] = by_year.get(y, 0) + 1
        total += 1
    # Need a real, multi-year spread to call it a trend.
    if total < 100 or len(by_year) < 8:
        return SupplyTrend(
            slug=slug_or_csv, available=False, n_facilities=total,
            note=(f"{spec.csv} carries no usable certification-year spread — "
                  "supply trend unavailable offline; the state breakdown "
                  "stands in its place."))

    yr_min, yr_max = min(by_year), max(by_year)
    cur_year = datetime.now(timezone.utc).year
    # Exclude the partial current/snapshot year from the reliable window.
    window_end = yr_max if yr_max < cur_year else yr_max - 1

    points: List[SupplyPoint] = []
    cum = 0
    for y in range(yr_min, yr_max + 1):
        add = by_year.get(y, 0)
        cum += add
        points.append(SupplyPoint(year=y, net_adds=add, cumulative=cum))

    # Reliable-window start: first year the cumulative clears a small floor,
    # so the CAGR isn't dominated by the noisy first handful of facilities.
    floor = max(10, int(0.05 * total))
    window_start = yr_min
    for p in points:
        if p.cumulative >= floor:
            window_start = p.year
            break

    cum_by_year = {p.year: p.cumulative for p in points}
    cagr: Optional[float] = None
    if window_end > window_start and cum_by_year.get(window_start, 0) > 0:
        c0 = cum_by_year[window_start]
        c1 = cum_by_year[window_end]
        span = window_end - window_start
        if c1 > 0 and span > 0:
            cagr = (c1 / c0) ** (1.0 / span) - 1.0

    # Inflection = peak single-year net adds within the reliable window.
    in_window = [p for p in points if window_start <= p.year <= window_end]
    inflection_year = (max(in_window, key=lambda p: p.net_adds).year
                       if in_window else None)

    # 5-year cohorts for the chart (aligned to …/00/05/… boundaries).
    cohort_adds: Dict[int, int] = {}
    for p in points:
        base = (p.year // 5) * 5
        cohort_adds[base] = cohort_adds.get(base, 0) + p.net_adds
    cohorts = [
        CohortBar(label=f"{b}–{b + 4}", net_adds=cohort_adds[b])
        for b in sorted(cohort_adds)
    ]
    peak_cohort = (max(cohorts, key=lambda c: c.net_adds).label
                   if cohorts else None)

    takeaway = _supply_takeaway(slug_or_csv, cagr, inflection_year,
                                peak_cohort, window_start, window_end, total)
    return SupplyTrend(
        slug=slug_or_csv, available=True, points=points, cohorts=cohorts,
        window_start=window_start, window_end=window_end, cagr=cagr,
        inflection_year=inflection_year, peak_cohort=peak_cohort,
        n_facilities=total,
        source_label=f"SOURCED · {spec.dataset} (certification_date)",
        note=("Certification vintage of the currently-open facility stock — "
              "reads supply momentum, not a reconstructed historical census "
              "(closed facilities are not in the file)."),
        takeaway=takeaway)


def _supply_takeaway(slug: str, cagr: Optional[float],
                     inflection_year: Optional[int], peak_cohort: Optional[str],
                     w0: Optional[int], w1: Optional[int],
                     total: int) -> str:
    """A computed 'what this shows' line — figures come from the series."""
    bits: List[str] = []
    if cagr is not None and w0 and w1:
        bits.append(
            f"The surviving-stock certification base compounded "
            f"{cagr * 100:+.1f}%/yr across {w0}–{w1}")
    if peak_cohort:
        bits.append(f"the heaviest build cohort was {peak_cohort}")
    if inflection_year:
        bits.append(f"net adds peaked in {inflection_year}")
    if not bits:
        return ""
    return "; ".join(bits) + f" ({total:,} facilities in the roll)."


# ── Optional: HCRIS multi-year margin trend ─────────────────────────────────
@dataclass
class MarginTrend:
    slug: str
    available: bool
    points: List[Tuple[int, float]] = field(default_factory=list)  # (FY, margin)
    source_label: str = ""
    note: str = ""


def hcris_margin_trend(slug_or_csv: str = "hospitals") -> MarginTrend:
    """Multi-year operating-margin trend from HCRIS, when cleanly reachable.

    The vendored HCRIS snapshot is a single latest-filing-per-CCN cross-section
    (no multi-year FY panel is vendored, and network fetches are barred at
    runtime), so an honest offline trend is unavailable — this returns
    ``available=False`` with a note rather than fabricating a series. Kept as a
    typed hook so a future vendored multi-FY panel drops straight in."""
    return MarginTrend(
        slug=slug_or_csv, available=False,
        note=("No multi-year HCRIS FY panel is vendored offline (the snapshot "
              "is a single latest-filing cross-section); an operating-margin "
              "trend is omitted rather than fabricated."),
        source_label="SOURCED · CMS HCRIS (single-period snapshot only)")
