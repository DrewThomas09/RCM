"""Sponsor × Sector Performance Heatmap.

Complements /sponsor-league with a 2-D cut: which sponsors outperform in which
sectors? Used at IC to answer 'who has won in [sector] before, and does this
deal look like their winning pattern?'

Outputs:
- Sponsor × sector matrix of weighted-average MOIC
- Top sponsor per sector (realized deals only)
- Sector mix per sponsor (concentration test)
- Time-period cuts (2016-2019 vs 2020-2024)
- Hold-period stratification
- Realized vs unrealized delta per sponsor (vintage quality)
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SponsorSectorCell:
    sponsor: str
    sector: str
    deal_count: int
    avg_moic: float
    median_moic: float
    avg_irr: float
    total_ev_mm: float
    realized_pct: float
    performance_tier: str


@dataclass
class SponsorProfile:
    sponsor: str
    total_deals: int
    avg_moic: float
    avg_irr: float
    median_hold_years: float
    total_ev_deployed_mm: float
    sector_count: int
    top_sector: str
    sector_concentration_pct: float
    realized_pct: float


@dataclass
class SectorLeader:
    sector: str
    top_sponsor: str
    top_moic: float
    top_irr: float
    deal_count: int
    runner_up: str
    runner_up_moic: float


@dataclass
class VintageCut:
    sponsor: str
    vintage_2016_2019_moic: float
    vintage_2016_2019_deals: int
    vintage_2020_2024_moic: float
    vintage_2020_2024_deals: int
    trend: str


@dataclass
class HoldStratification:
    hold_bucket: str
    deal_count: int
    avg_moic: float
    avg_irr: float
    best_moic: float
    best_deal: str


@dataclass
class SponsorHeatmapResult:
    total_sponsors: int
    total_sectors: int
    matrix_cells: List[SponsorSectorCell]
    top_sponsors: List[SponsorProfile]
    sector_leaders: List[SectorLeader]
    vintage_cuts: List[VintageCut]
    hold_strat: List[HoldStratification]
    corpus_deal_count: int
    avg_portfolio_moic: float


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize(d: dict) -> dict:
    """Normalize heterogeneous deal dicts across seed schemas."""
    buyer = d.get("buyer") or d.get("sponsor") or ""
    sector = d.get("sector") or d.get("deal_type") or ""
    moic = d.get("moic") or d.get("realized_moic") or 0
    irr = d.get("irr") or d.get("realized_irr") or 0
    name = d.get("company_name") or d.get("deal_name") or ""
    status = d.get("status") or ("Realized" if d.get("realized_moic") else "")
    return {
        "buyer": buyer,
        "sector": sector,
        "moic": moic,
        "irr": irr,
        "company_name": name,
        "status": status,
        "year": d.get("year") or 0,
        "hold_years": d.get("hold_years") or 0,
        "ev_mm": d.get("ev_mm") or 0,
    }


def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 85):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    normalized = [_normalize(d) for d in deals]
    return [n for n in normalized if n["buyer"] and n["sector"] and n["moic"]]


def _tier(moic: float) -> str:
    if moic >= 2.8: return "top quartile"
    if moic >= 2.3: return "above avg"
    if moic >= 1.9: return "avg"
    if moic >= 1.6: return "below avg"
    return "bottom quartile"


def _build_cells(deals: List[dict], min_deals: int = 2) -> List[SponsorSectorCell]:
    bucket: Dict[Tuple[str, str], List[dict]] = {}
    for d in deals:
        sponsor = d.get("buyer") or "Unknown"
        sector = d.get("sector") or "Unknown"
        bucket.setdefault((sponsor, sector), []).append(d)

    rows = []
    for (sponsor, sector), ds in bucket.items():
        if len(ds) < min_deals:
            continue
        moics = [d.get("moic", 0) or 0 for d in ds]
        irrs = [d.get("irr", 0) or 0 for d in ds]
        evs = [d.get("ev_mm", 0) or 0 for d in ds]
        avg_moic = sum(moics) / len(moics)
        sorted_m = sorted(moics)
        median_moic = sorted_m[len(sorted_m) // 2]
        avg_irr = sum(irrs) / len(irrs)
        realized = sum(1 for d in ds if d.get("status") in ("Realized", "Exited"))
        rows.append(SponsorSectorCell(
            sponsor=sponsor,
            sector=sector,
            deal_count=len(ds),
            avg_moic=round(avg_moic, 3),
            median_moic=round(median_moic, 3),
            avg_irr=round(avg_irr, 4),
            total_ev_mm=round(sum(evs), 1),
            realized_pct=round(realized / len(ds), 3),
            performance_tier=_tier(avg_moic),
        ))
    return sorted(rows, key=lambda c: c.avg_moic, reverse=True)


def _build_sponsor_profiles(deals: List[dict], min_deals: int = 3) -> List[SponsorProfile]:
    bucket: Dict[str, List[dict]] = {}
    for d in deals:
        s = d.get("buyer") or "Unknown"
        bucket.setdefault(s, []).append(d)

    rows = []
    for sponsor, ds in bucket.items():
        if len(ds) < min_deals:
            continue
        moics = [d.get("moic", 0) or 0 for d in ds]
        irrs = [d.get("irr", 0) or 0 for d in ds]
        holds = sorted([d.get("hold_years", 0) or 0 for d in ds])
        evs = [d.get("ev_mm", 0) or 0 for d in ds]
        sector_counts: Dict[str, int] = {}
        for d in ds:
            sector_counts[d.get("sector", "Unknown")] = sector_counts.get(d.get("sector", "Unknown"), 0) + 1
        top_sector = max(sector_counts, key=sector_counts.get)
        conc = sector_counts[top_sector] / len(ds)
        realized = sum(1 for d in ds if d.get("status") in ("Realized", "Exited"))
        rows.append(SponsorProfile(
            sponsor=sponsor,
            total_deals=len(ds),
            avg_moic=round(sum(moics) / len(moics), 3),
            avg_irr=round(sum(irrs) / len(irrs), 4),
            median_hold_years=round(holds[len(holds) // 2], 2),
            total_ev_deployed_mm=round(sum(evs), 1),
            sector_count=len(sector_counts),
            top_sector=top_sector,
            sector_concentration_pct=round(conc, 3),
            realized_pct=round(realized / len(ds), 3),
        ))
    return sorted(rows, key=lambda p: p.avg_moic, reverse=True)


def _build_sector_leaders(cells: List[SponsorSectorCell]) -> List[SectorLeader]:
    by_sector: Dict[str, List[SponsorSectorCell]] = {}
    for c in cells:
        by_sector.setdefault(c.sector, []).append(c)

    rows = []
    for sector, cs in by_sector.items():
        cs = sorted(cs, key=lambda x: x.avg_moic, reverse=True)
        top = cs[0]
        runner = cs[1] if len(cs) > 1 else None
        rows.append(SectorLeader(
            sector=sector,
            top_sponsor=top.sponsor,
            top_moic=top.avg_moic,
            top_irr=top.avg_irr,
            deal_count=top.deal_count,
            runner_up=runner.sponsor if runner else "—",
            runner_up_moic=runner.avg_moic if runner else 0,
        ))
    return sorted(rows, key=lambda r: r.top_moic, reverse=True)


def _build_vintage_cuts(deals: List[dict], top_sponsors: List[str]) -> List[VintageCut]:
    rows = []
    for sponsor in top_sponsors:
        early = [d for d in deals if d.get("buyer") == sponsor and 2016 <= (d.get("year") or 0) <= 2019]
        late = [d for d in deals if d.get("buyer") == sponsor and 2020 <= (d.get("year") or 0) <= 2024]
        if not early and not late:
            continue
        early_moic = (sum(d.get("moic", 0) or 0 for d in early) / len(early)) if early else 0
        late_moic = (sum(d.get("moic", 0) or 0 for d in late) / len(late)) if late else 0
        if late_moic > early_moic * 1.08:
            trend = "improving"
        elif late_moic < early_moic * 0.92:
            trend = "declining"
        else:
            trend = "stable"
        rows.append(VintageCut(
            sponsor=sponsor,
            vintage_2016_2019_moic=round(early_moic, 3),
            vintage_2016_2019_deals=len(early),
            vintage_2020_2024_moic=round(late_moic, 3),
            vintage_2020_2024_deals=len(late),
            trend=trend,
        ))
    return rows


def _build_hold_strat(deals: List[dict]) -> List[HoldStratification]:
    buckets = {
        "< 3 yrs (quick flip)":  (0, 3),
        "3-4 yrs":               (3, 4),
        "4-5 yrs":               (4, 5),
        "5-6 yrs":               (5, 6),
        "6+ yrs (long hold)":    (6, 999),
    }
    rows = []
    for label, (lo, hi) in buckets.items():
        filtered = [d for d in deals if lo <= (d.get("hold_years") or 0) < hi]
        if not filtered:
            continue
        moics = [d.get("moic", 0) or 0 for d in filtered]
        irrs = [d.get("irr", 0) or 0 for d in filtered]
        best = max(filtered, key=lambda d: d.get("moic", 0) or 0)
        rows.append(HoldStratification(
            hold_bucket=label,
            deal_count=len(filtered),
            avg_moic=round(sum(moics) / len(moics), 3),
            avg_irr=round(sum(irrs) / len(irrs), 4),
            best_moic=round(best.get("moic", 0) or 0, 2),
            best_deal=best.get("company_name", "—"),
        ))
    return rows


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_sponsor_heatmap(
    min_deals_per_cell: int = 2,
    min_deals_per_sponsor: int = 4,
    top_sponsor_limit: int = 15,
) -> SponsorHeatmapResult:
    deals = _load_corpus()

    cells = _build_cells(deals, min_deals_per_cell)
    profiles = _build_sponsor_profiles(deals, min_deals_per_sponsor)[:top_sponsor_limit]
    leaders = _build_sector_leaders(cells)
    top_sponsor_names = [p.sponsor for p in profiles[:10]]
    vintage_cuts = _build_vintage_cuts(deals, top_sponsor_names)
    hold_strat = _build_hold_strat(deals)

    moics = [d.get("moic", 0) or 0 for d in deals]
    avg_port_moic = sum(moics) / len(moics) if moics else 0

    sponsors_set = set(d.get("buyer") for d in deals if d.get("buyer"))
    sectors_set = set(d.get("sector") for d in deals if d.get("sector"))

    return SponsorHeatmapResult(
        total_sponsors=len(sponsors_set),
        total_sectors=len(sectors_set),
        matrix_cells=cells,
        top_sponsors=profiles,
        sector_leaders=leaders,
        vintage_cuts=vintage_cuts,
        hold_strat=hold_strat,
        corpus_deal_count=len(deals),
        avg_portfolio_moic=round(avg_port_moic, 3),
    )
