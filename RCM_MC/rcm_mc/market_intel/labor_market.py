"""Healthcare labor-market intelligence — wage inflation by role.

The market-intel survey's flagged gap: the desk priced revenue risk
(rates, payer mix) but had nothing on the cost side's biggest line —
labor is 50-60% of opex for most healthcare-services targets, and the
wage/turnover environment by role is what decides whether an EBITDA
margin holds through a hold period. This module loads the curated
BLS/staffing-survey cut (``content/labor_market.yaml``) and computes
the wage-inflation EBITDA stress for a target's labor base × role mix
— the same shape as the rate-environment blend, pointed at cost.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

CONTENT_DIR = Path(__file__).parent / "content"


@dataclass
class RoleEconomics:
    role: str
    label: str
    median_hourly_usd: float
    wage_yoy_pct: float
    turnover_pct: float
    vacancy_pct: float
    replacement_weeks: int

    def fragility_score(self) -> float:
        """0-100 staffing-fragility composite: how hard this role is to
        hold and replace. Equal-weight blend of turnover, vacancy, and
        wage pressure, each scaled against the worst plausible value
        (40% turnover / 15% vacancy / 6% wage growth) so the score
        reads absolutely, not relative to the current panel. Each
        component is clamped to [0, 1] — a wage-deflation year must
        floor its component at zero, not drag the composite below the
        documented 0-100 range."""
        t = min(max(self.turnover_pct / 40.0, 0.0), 1.0)
        v = min(max(self.vacancy_pct / 15.0, 0.0), 1.0)
        w = min(max(self.wage_yoy_pct / 6.0, 0.0), 1.0)
        return round((t + v + w) / 3 * 100, 1)

    def to_dict(self) -> Dict[str, Any]:
        d = self.__dict__.copy()
        d["fragility_score"] = self.fragility_score()
        return d


def _load() -> Dict[str, Any]:
    return yaml.safe_load(
        (CONTENT_DIR / "labor_market.yaml").read_text("utf-8"))


def list_roles() -> List[RoleEconomics]:
    return [
        RoleEconomics(
            role=str(r["role"]).upper(), label=r["label"],
            median_hourly_usd=float(r["median_hourly_usd"]),
            wage_yoy_pct=float(r["wage_yoy_pct"]),
            turnover_pct=float(r["turnover_pct"]),
            vacancy_pct=float(r["vacancy_pct"]),
            replacement_weeks=int(r["replacement_weeks"]),
        )
        for r in _load().get("roles") or ()
    ]


def get_role(role: str) -> Optional[RoleEconomics]:
    key = (role or "").strip().upper()
    for r in list_roles():
        if r.role == key:
            return r
    return None


@dataclass
class LaborStress:
    labor_cost_usd: float
    blended_wage_growth_pct: float
    annual_cost_increase_usd: float
    ebitda_margin_impact_bps: float   # on the revenue base, if given
    per_role: List[Dict[str, Any]]
    # Share of the supplied mix that matched no role in the panel.
    # Disclosed because the blend renormalizes over the KNOWN roles:
    # reasonable for a query-string typo, but if 40% of labor spend is
    # an unrecognized role the whole labor base is inflated at the
    # known-roles blend and the caller must be told 40% of the mix was
    # unmatched rather than silently misattributed.
    unrecognized_share_pct: float = 0.0
    unrecognized_codes: List[str] = field(default_factory=list)
    # Review date of the curated wage panel the blend was priced from.
    # Carried on the payload because the stress number reads as a live
    # market read while the panel refreshes quarterly — the vintage
    # must travel with the dollars, not sit in a separate accessor the
    # page may never call.
    content_last_reviewed: Optional[str] = None


def labor_cost_stress(
    labor_cost_usd: float,
    role_mix: Dict[str, float],
    *,
    revenue_usd: float = 0.0,
) -> LaborStress:
    """Mix-weighted next-year wage-inflation cost on a labor base.

    ``role_mix`` maps role code -> share of labor spend (normalized, so
    percentages or fractions both work). Margin impact in bps is
    computed only when a revenue base is supplied — labor inflation
    uncompensated by rate is pure margin compression.

    Unknown role codes are dropped and the remaining weights
    renormalized; the dropped mass is reported via
    ``unrecognized_share_pct`` / ``unrecognized_codes`` so a
    genuinely-different mix can't masquerade as a fully-priced one."""
    from .content_vintage import content_vintage

    reviewed = content_vintage("labor_market")["last_reviewed"]
    known = {k.upper(): v for k, v in role_mix.items() if v and v > 0}
    roles = {r.role: r for r in list_roles()}
    rows = [(k, v, roles[k]) for k, v in known.items() if k in roles]
    unrecognized = sorted(k for k in known if k not in roles)
    input_total = sum(known.values())
    unrecognized_share = (
        round(sum(v for k, v in known.items() if k not in roles)
              / input_total * 100, 1)
        if input_total > 0 else 0.0
    )
    total = sum(v for _, v, _ in rows)
    if not rows or total <= 0:
        return LaborStress(labor_cost_usd, 0.0, 0.0, 0.0, [],
                           unrecognized_share_pct=unrecognized_share,
                           unrecognized_codes=unrecognized,
                           content_last_reviewed=reviewed)

    per_role: List[Dict[str, Any]] = []
    blended = 0.0
    for code, share, r in rows:
        weight = share / total
        dollars = labor_cost_usd * weight * r.wage_yoy_pct / 100.0
        blended += weight * r.wage_yoy_pct
        per_role.append({
            "role": code, "label": r.label,
            "share_pct": round(weight * 100, 1),
            "wage_yoy_pct": r.wage_yoy_pct,
            "cost_increase_usd": round(dollars, 2),
            "fragility_score": r.fragility_score(),
        })
    per_role.sort(key=lambda d: -d["cost_increase_usd"])
    increase = round(labor_cost_usd * blended / 100.0, 2)
    bps = (round(increase / revenue_usd * 10_000, 1)
           if revenue_usd > 0 else 0.0)
    return LaborStress(
        labor_cost_usd=labor_cost_usd,
        blended_wage_growth_pct=round(blended, 2),
        annual_cost_increase_usd=increase,
        ebitda_margin_impact_bps=bps,
        per_role=per_role,
        unrecognized_share_pct=unrecognized_share,
        unrecognized_codes=unrecognized,
        content_last_reviewed=reviewed,
    )
