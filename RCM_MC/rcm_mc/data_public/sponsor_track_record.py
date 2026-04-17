"""PE sponsor track record analytics — performance attribution by firm across the corpus.

Answers the PE diligence question: "What has this sponsor actually returned
in healthcare, and how consistent are they?"

Public API:
    SponsorRecord                          dataclass
    build_sponsor_records(deals)           -> Dict[str, SponsorRecord]
    sponsor_league_table(deals, min_deals) -> List[SponsorRecord]
    sector_specialization(deals)           -> Dict[str, Dict[str, float]]
    sponsor_consistency_score(record)      -> float
    sponsor_report(record)                 -> str
    league_table_text(records, max_rows)   -> str
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Sponsor name normalization
# ---------------------------------------------------------------------------

_SPONSOR_ALIASES: Dict[str, str] = {
    "kkr": "KKR",
    "kohlberg kravis": "KKR",
    "blackstone": "Blackstone",
    "blackstone group": "Blackstone",
    "carlyle": "Carlyle Group",
    "carlyle group": "Carlyle Group",
    "tpg": "TPG Capital",
    "tpg capital": "TPG Capital",
    "warburg": "Warburg Pincus",
    "warburg pincus": "Warburg Pincus",
    "bain": "Bain Capital",
    "bain capital": "Bain Capital",
    "apollo": "Apollo Global",
    "apollo global": "Apollo Global",
    "welsh carson": "Welsh Carson",
    "welsh carson anderson": "Welsh Carson",
    "new mountain": "New Mountain Capital",
    "new mountain capital": "New Mountain Capital",
    "frazier": "Frazier Healthcare",
    "frazier healthcare": "Frazier Healthcare",
    "gtcr": "GTCR",
    "ta associates": "TA Associates",
    "leonard green": "Leonard Green",
    "leonard green & partners": "Leonard Green",
    "riverside": "Riverside Company",
    "riverside company": "Riverside Company",
    "shore": "Shore Capital",
    "shore capital": "Shore Capital",
    "revelstoke": "Revelstoke Capital",
    "l catterton": "L Catterton",
    "summit": "Summit Partners",
    "summit partners": "Summit Partners",
    "advent": "Advent International",
    "advent international": "Advent International",
    "centerbridge": "Centerbridge Partners",
    "centerbridge partners": "Centerbridge Partners",
    "nautic": "Nautic Partners",
    "nautic partners": "Nautic Partners",
    "ares": "Ares Management",
    "ares management": "Ares Management",
    "eqt": "EQT Partners",
    "nordic capital": "Nordic Capital",
    "general atlantic": "General Atlantic",
    "deerfield": "Deerfield Management",
    "charlesbank": "Charlesbank Capital",
    "abry": "ABRY Partners",
    "harvest": "Harvest Partners",
    "harvest partners": "Harvest Partners",
    "nea": "New Enterprise Associates",
    "greylock": "Greylock Partners",
    "gridiron": "Gridiron Capital",
    "frontenac": "Frontenac Company",
    "martis": "Martis Capital",
    "vista": "Vista Equity Partners",
    "vista equity": "Vista Equity Partners",
    "hig": "H.I.G. Capital",
    "h.i.g.": "H.I.G. Capital",
    "medequity": "MedEquity Capital",
    "apax": "Apax Partners",
    "waud": "Waud Capital Partners",
    "clearlake": "Clearlake Capital",
    "ga": "General Atlantic",
}


def _normalize_sponsor(raw: str) -> str:
    """Canonicalize a sponsor name for grouping."""
    if not raw:
        return "Unknown"
    key = raw.lower().strip()
    # Try direct lookup
    for alias, canonical in _SPONSOR_ALIASES.items():
        if alias in key:
            return canonical
    # Title-case fallback, strip legal suffixes
    cleaned = re.sub(r"\s+(llc|lp|inc|corp|group|capital|partners|management|&.*|/.*)", "", raw, flags=re.I).strip()
    return cleaned.title() or raw


def _extract_sponsors(deal: Dict[str, Any]) -> List[str]:
    """Extract one or more sponsor names from the buyer field."""
    buyer = deal.get("buyer") or ""
    if not buyer:
        return ["Unknown"]
    # Split on common delimiters
    parts = re.split(r"[/,+&]|\band\b", buyer, flags=re.I)
    sponsors = []
    for p in parts:
        p = p.strip()
        if p and len(p) >= 3:
            norm = _normalize_sponsor(p)
            if norm not in sponsors:
                sponsors.append(norm)
    return sponsors or ["Unknown"]


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------

@dataclass
class SponsorRecord:
    sponsor: str
    deal_count: int
    realized_count: int           # deals with realized MOIC
    median_moic: Optional[float]
    mean_moic: Optional[float]
    moic_p25: Optional[float]
    moic_p75: Optional[float]
    median_irr: Optional[float]
    mean_irr: Optional[float]
    median_hold_years: Optional[float]
    loss_rate: float              # fraction of realized deals with MOIC < 1.0
    home_run_rate: float          # fraction with MOIC > 3.0
    sectors: List[str]            # distinct subsectors
    deal_types: List[str]         # distinct deal types
    avg_ev_mm: Optional[float]
    total_ev_mm: Optional[float]
    years_active: List[int]
    consistency_score: float      # 0-100 composite
    deals: List[str] = field(default_factory=list)  # source_ids


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------

def _median(vals: List[float]) -> Optional[float]:
    if not vals:
        return None
    s = sorted(vals)
    n = len(s)
    return round(s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2, 3)


def _mean(vals: List[float]) -> Optional[float]:
    return round(sum(vals) / len(vals), 3) if vals else None


def _percentile(vals: List[float], pct: float) -> Optional[float]:
    if not vals:
        return None
    s = sorted(vals)
    idx = int(pct * (len(s) - 1))
    return round(s[idx], 3)


def build_sponsor_records(deals: List[Dict[str, Any]]) -> Dict[str, SponsorRecord]:
    """Build a SponsorRecord for each PE firm appearing as buyer in the corpus.

    Args:
        deals: List of deal dicts (corpus.list() output or seed dicts)

    Returns:
        Dict mapping canonical sponsor name -> SponsorRecord
    """
    from collections import defaultdict

    sponsor_deals: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for deal in deals:
        for sponsor in _extract_sponsors(deal):
            sponsor_deals[sponsor].append(deal)

    records: Dict[str, SponsorRecord] = {}

    for sponsor, sdeal_list in sponsor_deals.items():
        moics = [float(d["realized_moic"]) for d in sdeal_list
                 if d.get("realized_moic") is not None]
        irrs = [float(d["realized_irr"]) for d in sdeal_list
                if d.get("realized_irr") is not None]
        holds = [float(d["hold_years"]) for d in sdeal_list
                 if d.get("hold_years") is not None]
        evs = [float(d["ev_mm"]) for d in sdeal_list
               if d.get("ev_mm") is not None]
        sectors = list({d.get("sector", "unknown") for d in sdeal_list if d.get("sector")})
        deal_types = list({d.get("deal_type", "unknown") for d in sdeal_list if d.get("deal_type")})
        years = sorted({int(d["year"]) for d in sdeal_list if d.get("year")})
        source_ids = [d.get("source_id", "") for d in sdeal_list]

        loss_rate = sum(1 for m in moics if m < 1.0) / len(moics) if moics else 0.0
        home_run_rate = sum(1 for m in moics if m > 3.0) / len(moics) if moics else 0.0

        consistency = sponsor_consistency_score_raw(moics, irrs, len(sdeal_list))

        records[sponsor] = SponsorRecord(
            sponsor=sponsor,
            deal_count=len(sdeal_list),
            realized_count=len(moics),
            median_moic=_median(moics),
            mean_moic=_mean(moics),
            moic_p25=_percentile(moics, 0.25),
            moic_p75=_percentile(moics, 0.75),
            median_irr=_median(irrs),
            mean_irr=_mean(irrs),
            median_hold_years=_median(holds),
            loss_rate=round(loss_rate, 3),
            home_run_rate=round(home_run_rate, 3),
            sectors=sorted(sectors),
            deal_types=sorted(deal_types),
            avg_ev_mm=_mean(evs),
            total_ev_mm=round(sum(evs), 1) if evs else None,
            years_active=years,
            consistency_score=consistency,
            deals=source_ids,
        )

    return records


def sponsor_consistency_score_raw(moics: List[float], irrs: List[float], n_deals: int) -> float:
    """Composite 0-100 consistency score for a sponsor.

    Weights:
      - Median MOIC vs. 2.0x benchmark (40%)
      - Loss rate penalty (25%)
      - IRR consistency (20%)
      - Deal count credibility (15%)
    """
    if not moics:
        return 0.0

    # Median MOIC score: 2.0x = 50pts, linear, capped at 100
    median_m = _median(moics) or 0.0
    moic_score = min(100.0, max(0.0, (median_m / 2.0) * 50.0))

    # Loss rate penalty: 0% loss = 25pts, 100% loss = 0pts
    loss_penalty = 25.0 * (1.0 - (sum(1 for m in moics if m < 1.0) / len(moics)))

    # IRR score: 20% IRR = full 20pts
    if irrs:
        med_irr = _median(irrs) or 0.0
        irr_score = min(20.0, max(0.0, (med_irr / 0.20) * 20.0))
    else:
        irr_score = 10.0  # neutral if no IRR data

    # Deal count credibility: 5+ deals = full 15pts
    cred_score = min(15.0, n_deals * 3.0)

    return round(moic_score * 0.40 + loss_penalty + irr_score + cred_score, 1)


def sponsor_consistency_score(record: SponsorRecord) -> float:
    """Re-compute consistency score from a SponsorRecord."""
    moics = []  # Can't reconstruct from record; return stored value
    return record.consistency_score


def sponsor_league_table(
    deals: List[Dict[str, Any]],
    min_deals: int = 2,
) -> List[SponsorRecord]:
    """Rank sponsors by consistency_score, filtered to min_deals.

    Returns list sorted by consistency_score descending.
    """
    records = build_sponsor_records(deals)
    filtered = [r for r in records.values() if r.deal_count >= min_deals]
    return sorted(filtered, key=lambda r: r.consistency_score, reverse=True)


def sector_specialization(deals: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    """For each sponsor, compute fraction of deals by subsector.

    Returns Dict[sponsor -> Dict[sector -> fraction]].
    """
    from collections import defaultdict

    sponsor_sector_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for deal in deals:
        sector = deal.get("sector") or "unknown"
        for sponsor in _extract_sponsors(deal):
            sponsor_sector_counts[sponsor][sector] += 1

    result: Dict[str, Dict[str, float]] = {}
    for sponsor, sector_counts in sponsor_sector_counts.items():
        total = sum(sector_counts.values())
        result[sponsor] = {s: round(c / total, 3) for s, c in
                           sorted(sector_counts.items(), key=lambda x: -x[1])}

    return result


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

def sponsor_report(record: SponsorRecord) -> str:
    """Single-sponsor text report for diligence packets."""
    lines = [
        f"Sponsor Track Record: {record.sponsor}",
        "=" * 55,
        f"  Deals in corpus:    {record.deal_count} ({record.realized_count} realized)",
        f"  Years active:       {min(record.years_active) if record.years_active else '—'}–"
        f"{max(record.years_active) if record.years_active else '—'}",
        f"  Median MOIC:        {f'{record.median_moic:.2f}x' if record.median_moic else '—'}",
        f"  Mean MOIC:          {f'{record.mean_moic:.2f}x' if record.mean_moic else '—'}",
        f"  MOIC P25/P75:       {f'{record.moic_p25:.2f}x' if record.moic_p25 else '—'} / "
        f"{f'{record.moic_p75:.2f}x' if record.moic_p75 else '—'}",
        f"  Median IRR:         {f'{record.median_irr:.1%}' if record.median_irr else '—'}",
        f"  Median hold:        {f'{record.median_hold_years:.1f} yrs' if record.median_hold_years else '—'}",
        f"  Loss rate (<1.0x):  {record.loss_rate:.0%}",
        f"  Home run rate (>3x):{record.home_run_rate:.0%}",
        f"  Avg deal size:      {f'${record.avg_ev_mm:,.0f}M' if record.avg_ev_mm else '—'}",
        f"  Consistency score:  {record.consistency_score:.1f}/100",
        f"  Sectors:            {', '.join(record.sectors[:5])}{'…' if len(record.sectors) > 5 else ''}",
    ]
    return "\n".join(lines) + "\n"


def league_table_text(records: List[SponsorRecord], max_rows: int = 20) -> str:
    """Formatted league table of PE sponsors."""
    lines = [
        f"{'Sponsor':<28} {'Deals':>6} {'Med MOIC':>9} {'Med IRR':>8} {'Loss%':>6} {'HR%':>5} {'Score':>6}",
        "-" * 72,
    ]
    for rec in records[:max_rows]:
        moic_s = f"{rec.median_moic:.2f}x" if rec.median_moic is not None else "  —  "
        irr_s = f"{rec.median_irr:.1%}" if rec.median_irr is not None else "  —  "
        loss_s = f"{rec.loss_rate:.0%}"
        hr_s = f"{rec.home_run_rate:.0%}"
        score_s = f"{rec.consistency_score:.1f}"
        lines.append(
            f"{rec.sponsor[:27]:<28} {rec.deal_count:>6} {moic_s:>9} {irr_s:>8} "
            f"{loss_s:>6} {hr_s:>5} {score_s:>6}"
        )
    return "\n".join(lines) + "\n"
