"""PE Desk Composite Score: 0-100 rating for any hospital.

Combines market position (35%), financial health (25%), operational
quality (20%), and competitive moat (20%) into a single investability
score. Every hospital in HCRIS gets a score.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional

import numpy as np


@dataclass
class ChartisScore:
    ccn: str
    name: str
    score: int
    grade: str
    components: Dict[str, float]
    breakdown: Dict[str, str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ccn": self.ccn,
            "name": self.name,
            "score": self.score,
            "grade": self.grade,
            "components": {k: round(v, 1) for k, v in self.components.items()},
            "breakdown": self.breakdown,
        }


def _grade(score: int) -> str:
    if score >= 90: return "A+"
    if score >= 85: return "A"
    if score >= 80: return "A-"
    if score >= 75: return "B+"
    if score >= 70: return "B"
    if score >= 65: return "B-"
    if score >= 60: return "C+"
    if score >= 55: return "C"
    if score >= 50: return "C-"
    if score >= 40: return "D"
    return "F"


def compute_caduceus_score(
    profile: Dict[str, Any],
    market_data: Optional[Dict[str, Any]] = None,
) -> ChartisScore:
    """Compute the PE Desk score for a hospital.

    Scoring is continuous (not stair-step) so the HCRIS long tail
    doesn't pile up at a single default value. Small hospitals with
    negative margins earn a low score organically rather than hitting
    a hard baseline.
    """
    ccn = str(profile.get("ccn") or profile.get("deal_id") or "")
    name = str(profile.get("name") or "")
    breakdown: Dict[str, str] = {}

    beds = float(profile.get("beds") or profile.get("bed_count") or 0)
    npr = float(profile.get("net_patient_revenue") or profile.get("net_revenue") or 0)

    # ── Market Position (0-35 pts) ──
    # Continuous: beds component saturates at 500, NPR component saturates at $1B.
    # log-scaled for NPR so $50M -> 6pts and $500M -> 15pts, preventing small
    # hospitals from piling up at 0.
    beds_pts = min(15.0, beds / 500.0 * 15.0) if beds > 0 else 0.0
    if npr > 1e6:
        import math
        # log10(NPR): $1M=6, $10M=7, $100M=8, $1B=9, $10B=10
        npr_log = math.log10(max(1.0, npr))
        # Map [6, 10] -> [0, 20]
        npr_pts = max(0.0, min(20.0, (npr_log - 6.0) * 5.0))
    else:
        npr_pts = 0.0
    market_score = beds_pts + npr_pts
    breakdown["beds"] = f"{int(beds)} beds (+{beds_pts:.1f})"
    breakdown["revenue"] = f"${npr/1e6:.0f}M NPR (+{npr_pts:.1f})"

    # ── Financial Health (0-25 pts) ──
    # Piecewise but continuous: -30% margin -> 0pts, 0% -> 8pts, +15% -> 25pts.
    opex = float(profile.get("operating_expenses") or 0)
    margin = (npr - opex) / npr if npr > 1e5 and opex > 0 else 0
    margin = max(-1.0, min(1.0, margin))
    # Piecewise linear continuous scoring
    if margin <= -0.30:
        fin_score = 0.0
    elif margin <= 0.0:
        # -30% → 0, 0% → 8: slope 26.67 pts per unit margin
        fin_score = (margin + 0.30) / 0.30 * 8.0
    elif margin <= 0.15:
        # 0% → 8, 15% → 25: slope 113.33 pts per unit margin
        fin_score = 8.0 + margin / 0.15 * 17.0
    else:
        fin_score = 25.0
    breakdown["margin"] = f"{margin:.1%} margin (+{fin_score:.1f})"

    # Operational Quality (20 points max). RCM-richer profiles score
    # off denial_rate + days_in_ar; HCRIS-only profiles score off
    # public-data proxies (cost ratio, occupancy, commercial-payer
    # share) so the breakdown isn't a flat 0 that partners read as
    # "operations are broken" when the truth is "RCM data not loaded".
    denial_raw = profile.get("denial_rate")
    ar_raw = profile.get("days_in_ar")
    have_ops = denial_raw is not None and ar_raw is not None

    ops_score = 0.0
    if have_ops:
        denial_rate = float(denial_raw)
        ar_days = float(ar_raw)
        ops_score = 8.0

        if denial_rate < 8:
            ops_score += 8
            breakdown["denial"] = f"{denial_rate:.1f}% denial (excellent, +8)"
        elif denial_rate < 12:
            ops_score += 4
            breakdown["denial"] = f"{denial_rate:.1f}% denial (good, +4)"
        else:
            breakdown["denial"] = f"{denial_rate:.1f}% denial (high, +0)"

        if ar_days < 42:
            ops_score += 4
            breakdown["ar_days"] = f"{ar_days:.0f} AR days (excellent, +4)"
        elif ar_days < 50:
            ops_score += 2
            breakdown["ar_days"] = f"{ar_days:.0f} AR days (good, +2)"
        else:
            breakdown["ar_days"] = f"{ar_days:.0f} AR days (slow, +0)"

        ops_score = min(ops_score, 20)
        have_ops = True
    else:
        # HCRIS-proxy operational score — scaled into the same 0–20
        # band so the composite stays comparable:
        #   1. cost ratio (opex / npr) — peer-median is ~0.95, very
        #      operationally efficient hospitals run 0.85–0.92.
        #      0.85 → +8, 0.95 → +4, 1.05 → 0.
        #   2. occupancy proxy (patient_days / bed_days_avail) —
        #      higher is better. ≥0.65 → +6, 0.50 → +3, <0.40 → 0.
        #   3. commercial payer share — lower denial-risk payers.
        #      ≥0.45 → +6, 0.30 → +3, <0.20 → 0.
        # Sum is clamped to [0, 20].
        npr = float(profile.get("net_patient_revenue") or 0.0)
        opex = float(profile.get("operating_expenses") or 0.0)
        cost_ratio = (opex / npr) if npr > 0 else None
        bed_days = float(profile.get("bed_days_available") or 0.0)
        patient_days = float(profile.get("total_patient_days") or 0.0)
        occupancy = (patient_days / bed_days) if bed_days > 0 else None
        comm_share = profile.get("commercial_pct")
        if comm_share is None:
            mcare = float(profile.get("medicare_day_pct") or 0.0)
            mcaid = float(profile.get("medicaid_day_pct") or 0.0)
            # day_pct values are 0–100 on HCRIS; normalize before subtracting
            if mcare > 1.0 or mcaid > 1.0:
                mcare /= 100.0
                mcaid /= 100.0
            comm_share = max(0.0, 1.0 - mcare - mcaid)
        else:
            comm_share = float(comm_share)
            if comm_share > 1.0:
                comm_share /= 100.0

        ops_parts = []
        if cost_ratio is not None:
            if cost_ratio <= 0.88:
                cost_pts = 8.0
            elif cost_ratio <= 0.98:
                # Linear 0.88 → 8 ... 0.98 → 4
                cost_pts = 8.0 - (cost_ratio - 0.88) / 0.10 * 4.0
            elif cost_ratio <= 1.05:
                cost_pts = max(0.0, 4.0 - (cost_ratio - 0.98) / 0.07 * 4.0)
            else:
                cost_pts = 0.0
            ops_score += cost_pts
            ops_parts.append(
                f"cost ratio {cost_ratio:.2f} (+{cost_pts:.1f})"
            )

        if occupancy is not None:
            if occupancy >= 0.65:
                occ_pts = 6.0
            elif occupancy >= 0.40:
                occ_pts = (occupancy - 0.40) / 0.25 * 6.0
            else:
                occ_pts = 0.0
            ops_score += occ_pts
            ops_parts.append(
                f"occupancy {occupancy:.0%} (+{occ_pts:.1f})"
            )

        if comm_share > 0:
            if comm_share >= 0.45:
                cs_pts = 6.0
            elif comm_share >= 0.20:
                cs_pts = (comm_share - 0.20) / 0.25 * 6.0
            else:
                cs_pts = 0.0
            ops_score += cs_pts
            ops_parts.append(
                f"commercial mix {comm_share:.0%} (+{cs_pts:.1f})"
            )

        ops_score = max(0.0, min(20.0, ops_score))
        # Did we have ANY proxy? If yes, score the operational
        # subscore proper (and use the standard 100-pt total below).
        # If no proxies were observable either, fall back to the
        # rescaled 80-pt total so the composite isn't flat.
        if ops_parts:
            have_ops = True
            breakdown["denial"] = (
                "HCRIS proxy — " + ", ".join(ops_parts)
            )
        else:
            breakdown["denial"] = (
                "no RCM or HCRIS proxy data (scored on public data only)"
            )

    # ── Moat (0-20 pts) ── Continuous.
    # Scale component: beds/600 * 8 (large systems score higher on scale)
    moat_scale = min(8.0, beds / 600.0 * 8.0) if beds > 0 else 0.0
    # Market-concentration component: lower HHI (less competition) → more moat
    moat_concentration = 0.0
    if market_data and market_data.get("hhi_index") is not None:
        hhi = float(market_data["hhi_index"])
        # HHI 1500 (competitive) → 0 pts, HHI 4000 (concentrated) → 6 pts
        moat_concentration = max(0.0, min(6.0, (hhi - 1500.0) / 2500.0 * 6.0))
    # Margin-premium component: sustained margin above industry median is moat
    moat_margin = 0.0
    if margin > 0:
        # margin 0% → 0, margin 15% → 6
        moat_margin = min(6.0, margin / 0.15 * 6.0)
    moat_score = moat_scale + moat_concentration + moat_margin
    moat_score = max(0.0, min(20.0, moat_score))
    breakdown["moat"] = f"Moat (+{moat_score:.1f}/20)"

    if have_ops:
        total = int(round(market_score + fin_score + ops_score + moat_score))
    else:
        # Rescale across the 80 points we can observe back to a 100-point
        # scale so HCRIS-only hospitals aren't artificially capped.
        observed = market_score + fin_score + moat_score
        total = int(round(observed * (100.0 / 80.0)))

    total = max(0, min(100, total))

    return ChartisScore(
        ccn=ccn, name=name, score=total, grade=_grade(total),
        components={
            "market_position": market_score,
            "financial_health": fin_score,
            "operational_quality": ops_score,
            "competitive_moat": moat_score,
        },
        breakdown=breakdown,
    )


CaduceusScore = ChartisScore
