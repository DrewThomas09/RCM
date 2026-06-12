"""Win/Loss analysis — competitive-conversion evidence for CDD.

A market-share story is only as good as the target's conversion record
against named competitors. The desk's competitive surfaces (industry
deep dive, competitor grids) show *who* the rivals are; nothing showed
*how often the target beats them and why it loses*. This module
decomposes a contested-opportunity log into the three reads an IC
expects: win rate by competitor, loss-reason mix, and the price-gap
read on lost deals (is the target losing on price or on capability —
each implies a different value-creation plan).

The opportunity log is curated and deterministic (the page flags it
illustrative); the schema matches what a target's CRM export or a
win/loss interview program produces, so real data drops in without
changing the analytics.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

# Loss-reason taxonomy. PRICE and CAPABILITY are the two that matter
# strategically; the rest contextualize but rarely change the thesis.
LOSS_REASONS = ["PRICE", "CAPABILITY", "RELATIONSHIP / INCUMBENCY",
                "GEOGRAPHY / COVERAGE", "TIMING / NO DECISION"]


@dataclass
class CompetitorRecord:
    competitor: str
    contested: int              # opportunities where both competed
    wins: int
    win_rate_pct: float
    dominant_loss_reason: str   # most common reason when target lost
    median_price_gap_pct: float # target price vs winner's on losses
                                # (+ = target was more expensive)
    note: str


@dataclass
class SegmentWinRate:
    segment: str
    opportunities: int
    wins: int
    win_rate_pct: float


@dataclass
class QuarterTrend:
    quarter: str
    opportunities: int
    win_rate_pct: float


@dataclass
class WinLossResult:
    sector: str
    total_opportunities: int
    total_wins: int
    overall_win_rate_pct: float
    competitors: List[CompetitorRecord]
    segments: List[SegmentWinRate]
    loss_reason_mix: Dict[str, float]   # reason -> % of losses
    trend: List[QuarterTrend]
    price_loss_share_pct: float         # % of losses that were price-led
    headline: str


_LOGS: Dict[str, Dict] = {
    "Physician Services": {
        "competitors": [
            ("Health-system employed group", 38, 21,
             "RELATIONSHIP / INCUMBENCY", -4.0,
             "Wins on access; loses where the system controls referrals"),
            ("National MSO platform", 26, 11, "PRICE", 7.5,
             "Platform underbids on payer contracts to buy share"),
            ("Independent local groups", 31, 23,
             "GEOGRAPHY / COVERAGE", 1.5,
             "Strongest record — scale and scheduling win head-to-head"),
        ],
        "segments": [
            ("Commercial employer contracts", 24, 14),
            ("Payer network inclusion", 18, 9),
            ("Referral relationships (new PCP groups)", 35, 22),
            ("ASC joint ventures", 18, 10),
        ],
        "trend": [("2025Q2", 21, 52.4), ("2025Q3", 24, 54.2),
                  ("2025Q4", 26, 57.7), ("2026Q1", 24, 58.3)],
        "loss_mix": {"PRICE": 31.0, "CAPABILITY": 14.0,
                     "RELATIONSHIP / INCUMBENCY": 33.0,
                     "GEOGRAPHY / COVERAGE": 12.0,
                     "TIMING / NO DECISION": 10.0},
    },
    "HCIT / SaaS": {
        "competitors": [
            ("EHR-native module", 42, 19, "RELATIONSHIP / INCUMBENCY", -6.0,
             "The 'good-enough and already-bought' problem; wins need ROI proof"),
            ("Venture-backed point solution", 29, 18, "PRICE", 9.0,
             "Entrant discounts 25-30% in year 1; churns on service"),
            ("Legacy on-prem vendor", 22, 16, "CAPABILITY", -3.0,
             "Displacement wins on integration depth and analytics"),
        ],
        "segments": [
            ("Enterprise health systems", 31, 14),
            ("Regional / community systems", 36, 22),
            ("Physician-group market", 26, 17),
        ],
        "trend": [("2025Q2", 22, 50.0), ("2025Q3", 23, 52.2),
                  ("2025Q4", 25, 56.0), ("2026Q1", 23, 60.9)],
        "loss_mix": {"PRICE": 27.0, "CAPABILITY": 11.0,
                     "RELATIONSHIP / INCUMBENCY": 41.0,
                     "GEOGRAPHY / COVERAGE": 2.0,
                     "TIMING / NO DECISION": 19.0},
    },
    "Home Health": {
        "competitors": [
            ("National public operator", 33, 15, "PRICE", 5.0,
             "Scale wins MA network deals on rate; target wins on response time"),
            ("Hospital-owned agency", 27, 17, "RELATIONSHIP / INCUMBENCY", -2.0,
             "Discharge-flow capture is the battleground"),
            ("Local independents", 25, 19, "CAPABILITY", -1.0,
             "Wins on staffing depth and outcomes documentation"),
        ],
        "segments": [
            ("MA plan network contracts", 22, 9),
            ("Hospital discharge referral share", 38, 25),
            ("Hospice transitions", 25, 17),
        ],
        "trend": [("2025Q2", 20, 50.0), ("2025Q3", 22, 54.5),
                  ("2025Q4", 21, 57.1), ("2026Q1", 22, 59.1)],
        "loss_mix": {"PRICE": 36.0, "CAPABILITY": 13.0,
                     "RELATIONSHIP / INCUMBENCY": 28.0,
                     "GEOGRAPHY / COVERAGE": 15.0,
                     "TIMING / NO DECISION": 8.0},
    },
}

SECTORS = list(_LOGS)


def compute_win_loss(sector: str = "Physician Services") -> WinLossResult:
    log = _LOGS.get(sector) or _LOGS[SECTORS[0]]
    if sector not in _LOGS:
        sector = SECTORS[0]

    competitors = [
        CompetitorRecord(
            competitor=name, contested=contested, wins=wins,
            win_rate_pct=round(wins / contested * 100, 1),
            dominant_loss_reason=reason,
            median_price_gap_pct=gap, note=note,
        )
        for name, contested, wins, reason, gap, note in log["competitors"]
    ]
    segments = [
        SegmentWinRate(segment=s, opportunities=opp, wins=w,
                       win_rate_pct=round(w / opp * 100, 1))
        for s, opp, w in log["segments"]
    ]
    total_opp = sum(s.opportunities for s in segments)
    total_wins = sum(s.wins for s in segments)
    trend = [QuarterTrend(quarter=q, opportunities=o, win_rate_pct=r)
             for q, o, r in log["trend"]]
    loss_mix = dict(log["loss_mix"])
    price_share = loss_mix.get("PRICE", 0.0)

    overall = round(total_wins / max(total_opp, 1) * 100, 1)
    worst = min(competitors, key=lambda c: c.win_rate_pct)
    trend_dir = ("improving" if trend[-1].win_rate_pct > trend[0].win_rate_pct
                 else "softening")
    headline = (
        f"{overall:.1f}% overall win rate, {trend_dir} over the last four "
        f"quarters; weakest head-to-head is {worst.competitor.lower()} "
        f"({worst.win_rate_pct:.1f}%), where losses are "
        f"{worst.dominant_loss_reason.split(' /')[0].lower()}-led."
    )
    return WinLossResult(
        sector=sector, total_opportunities=total_opp, total_wins=total_wins,
        overall_win_rate_pct=overall, competitors=competitors,
        segments=segments, loss_reason_mix=loss_mix, trend=trend,
        price_loss_share_pct=price_share, headline=headline,
    )
