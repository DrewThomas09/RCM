"""Medicare rate-environment intelligence — setting-level payment updates.

The market-intel survey gap this closes: the desk had reimbursement
*headlines* (news feed) but no structured rate data — nothing answered
"what is Medicare paying this setting next year and what does that do
to the target's revenue?" This module loads the curated CMS update
calendar (``content/rate_updates.yaml``) and computes the blended
dollar impact for a target's setting mix, so the rate environment is a
number in the model rather than a sentence in the memo.

Same fixture pattern as the other market_intel datasets: hand-curated
YAML with source URLs, dataclass loaders, quarterly refresh. Values
are headline net updates; the YAML note per setting carries the policy
nuance the headline hides.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

CONTENT_DIR = Path(__file__).parent / "content"


@dataclass
class RateUpdate:
    period: str            # "FY2026" / "CY2026"
    net_update_pct: float  # headline net payment update, percent
    status: str            # FINAL | PROPOSED

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class SettingRates:
    setting: str           # IPPS, OPPS, PFS, ...
    label: str
    cycle: str             # FY | CY
    updates: List[RateUpdate]
    note: Optional[str] = None

    def latest(self) -> Optional[RateUpdate]:
        return self.updates[-1] if self.updates else None

    def three_year_compound_pct(self) -> float:
        """Compound effect of the listed updates — the cumulative rate
        drift a hold period inherits (3 listed cycles)."""
        factor = 1.0
        for u in self.updates:
            factor *= 1 + u.net_update_pct / 100.0
        return round((factor - 1) * 100, 1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "setting": self.setting,
            "label": self.label,
            "cycle": self.cycle,
            "updates": [u.to_dict() for u in self.updates],
            "note": self.note,
        }


def _load() -> Dict[str, Any]:
    return yaml.safe_load(
        (CONTENT_DIR / "rate_updates.yaml").read_text("utf-8"))


def list_settings() -> List[SettingRates]:
    data = _load()
    out: List[SettingRates] = []
    for row in data.get("settings") or ():
        updates = [
            RateUpdate(period=u["period"],
                       net_update_pct=float(u["net_update_pct"]),
                       status=str(u.get("status", "FINAL")))
            for u in row.get("updates") or ()
        ]
        out.append(SettingRates(
            setting=row["setting"], label=row["label"],
            cycle=row.get("cycle", "FY"), updates=updates,
            note=row.get("note"),
        ))
    return out


def get_setting(setting: str) -> Optional[SettingRates]:
    key = (setting or "").strip().upper()
    for s in list_settings():
        if s.setting == key:
            return s
    return None


@dataclass
class BlendedImpact:
    medicare_revenue_usd: float
    blended_update_pct: float       # mix-weighted latest update
    revenue_impact_usd: float       # dollars gained/lost next cycle
    per_setting: List[Dict[str, Any]]  # setting, share, update, status, dollars
    # True when any blended row's latest update is still a PROPOSED
    # rule. The blend picks each setting's most recent update
    # regardless of status, so once a proposed-rule cycle lands in the
    # YAML the dollar impact is driven by numbers that can shift at
    # finalization — the caller must be able to flag that.
    has_proposed: bool = False
    # Share of the supplied mix that matched no setting in the
    # calendar. Disclosed because the blend renormalizes over the
    # KNOWN settings: fine for a query-string typo, wrong to hide when
    # a material slice of the revenue base is an unrecognized setting.
    unrecognized_share_pct: float = 0.0
    unrecognized_codes: List[str] = field(default_factory=list)


def blended_rate_impact(
    medicare_revenue_usd: float,
    setting_mix: Dict[str, float],
    *,
    settings: Optional[List[SettingRates]] = None,
) -> BlendedImpact:
    """Mix-weighted next-cycle rate impact on a Medicare revenue base.

    ``setting_mix`` maps setting code -> share of Medicare revenue
    (shares are normalized, so callers may pass percentages or
    fractions). Unknown settings are dropped rather than raised: the
    caller is a query-string form and a typo shouldn't 500 the page —
    but the dropped mass is reported via ``unrecognized_share_pct`` /
    ``unrecognized_codes``. Each per-setting row carries the update's
    FINAL/PROPOSED ``status`` and the envelope carries
    ``has_proposed``.

    ``settings`` defaults to the curated calendar; injectable (same
    pattern as ``run_market_analysis(df=...)``) so the PROPOSED-cycle
    path is provable before a proposed rule actually lands in the
    YAML — the current calendar is all-FINAL, which is precisely when
    a status-dropping regression would go unnoticed.
    """
    known = {k.upper(): v for k, v in setting_mix.items() if v and v > 0}
    rates = {s.setting: s for s in (settings if settings is not None
                                    else list_settings())}
    rows = [(k, v, rates[k]) for k, v in known.items() if k in rates]
    unrecognized = sorted(k for k in known if k not in rates)
    input_total = sum(known.values())
    unrecognized_share = (
        round(sum(v for k, v in known.items() if k not in rates)
              / input_total * 100, 1)
        if input_total > 0 else 0.0
    )
    total_share = sum(v for _, v, _ in rows)
    if not rows or total_share <= 0:
        return BlendedImpact(medicare_revenue_usd, 0.0, 0.0, [],
                             unrecognized_share_pct=unrecognized_share,
                             unrecognized_codes=unrecognized)

    per_setting: List[Dict[str, Any]] = []
    blended = 0.0
    has_proposed = False
    for code, share, s in rows:
        weight = share / total_share
        latest = s.latest()
        upd = latest.net_update_pct if latest else 0.0
        status = latest.status if latest else ""
        if status == "PROPOSED":
            has_proposed = True
        dollars = medicare_revenue_usd * weight * upd / 100.0
        blended += weight * upd
        per_setting.append({
            "setting": code,
            "label": s.label,
            "share_pct": round(weight * 100, 1),
            "period": latest.period if latest else "",
            "net_update_pct": upd,
            "status": status,
            "revenue_impact_usd": round(dollars, 2),
        })
    per_setting.sort(key=lambda d: -abs(d["revenue_impact_usd"]))
    return BlendedImpact(
        medicare_revenue_usd=medicare_revenue_usd,
        blended_update_pct=round(blended, 2),
        revenue_impact_usd=round(
            medicare_revenue_usd * blended / 100.0, 2),
        per_setting=per_setting,
        has_proposed=has_proposed,
        unrecognized_share_pct=unrecognized_share,
        unrecognized_codes=unrecognized,
    )
