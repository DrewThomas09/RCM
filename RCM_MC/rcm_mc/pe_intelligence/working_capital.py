"""Working capital math — one-time cash released from lever programs.

RCM improvements, supplier term renegotiation, and inventory
rationalization release working-capital cash. Partners distinguish
WC release (one-time, doesn't recur) from EBITDA lift (recurring).
Confusing them overstates the enterprise value lift.

Functions:

- :func:`ar_days_to_cash` — $ cash released by reducing DSO.
- :func:`ap_days_to_cash` — $ cash released by extending DPO.
- :func:`inventory_days_to_cash` — $ cash released by DIO reduction.
- :func:`total_wc_release` — all three combined, with partner notes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class WorkingCapitalInputs:
    annual_revenue: float
    annual_cogs: Optional[float] = None
    annual_inventory_cost: Optional[float] = None
    current_dso: Optional[float] = None         # days sales outstanding
    target_dso: Optional[float] = None
    current_dpo: Optional[float] = None         # days payables outstanding
    target_dpo: Optional[float] = None
    current_dio: Optional[float] = None         # days inventory outstanding
    target_dio: Optional[float] = None


@dataclass
class WCRelease:
    component: str               # "ar" | "ap" | "inventory"
    days_improved: float
    cash_released: float         # positive = released from working capital
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component": self.component,
            "days_improved": self.days_improved,
            "cash_released": self.cash_released,
            "partner_note": self.partner_note,
        }


@dataclass
class WCSummary:
    total_cash_released: float
    components: List[WCRelease] = field(default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_cash_released": self.total_cash_released,
            "components": [c.to_dict() for c in self.components],
            "partner_note": self.partner_note,
        }


def ar_days_to_cash(
    revenue: float,
    current_dso: float,
    target_dso: float,
) -> WCRelease:
    """Cash released = revenue × (current_dso - target_dso) / 365."""
    delta = current_dso - target_dso
    cash = revenue * delta / 365.0
    if delta <= 0:
        note = "No AR improvement modeled."
    elif delta <= 5:
        note = "Modest AR release — front-end tuning only."
    elif delta <= 15:
        note = "Meaningful release — tracks a focused AR program."
    else:
        note = ("Large release — consider whether this is sustainable or a "
                "one-time billing-system cleanup.")
    return WCRelease(component="ar", days_improved=delta,
                     cash_released=cash, partner_note=note)


def ap_days_to_cash(
    cogs: float,
    current_dpo: float,
    target_dpo: float,
) -> WCRelease:
    """Cash released = cogs × (target_dpo - current_dpo) / 365."""
    delta = target_dpo - current_dpo
    cash = cogs * delta / 365.0
    if delta <= 0:
        note = "No AP extension modeled."
    elif delta <= 10:
        note = "Modest AP extension — reasonable supplier negotiation outcome."
    elif delta <= 25:
        note = "Aggressive AP extension — supplier relationship risk."
    else:
        note = ("Very aggressive AP extension — suppliers will push back; "
                "discount the release or expect term renegotiation.")
    return WCRelease(component="ap", days_improved=delta,
                     cash_released=cash, partner_note=note)


def inventory_days_to_cash(
    inventory_cost: float,
    current_dio: float,
    target_dio: float,
) -> WCRelease:
    """Cash released = inventory_cost × (current_dio - target_dio) / 365."""
    delta = current_dio - target_dio
    cash = inventory_cost * delta / 365.0
    if delta <= 0:
        note = "No inventory reduction modeled."
    elif delta <= 7:
        note = "Modest inventory reduction — supply-chain tuning."
    elif delta <= 20:
        note = "Meaningful reduction — usually implies SKU rationalization."
    else:
        note = ("Large reduction — check for service-level impact; could "
                "produce stockouts if overdone.")
    return WCRelease(component="inventory", days_improved=delta,
                     cash_released=cash, partner_note=note)


def total_wc_release(inputs: WorkingCapitalInputs) -> WCSummary:
    """Sum all three components where data exists."""
    components: List[WCRelease] = []
    if (inputs.current_dso is not None and inputs.target_dso is not None
            and inputs.annual_revenue > 0):
        components.append(ar_days_to_cash(
            inputs.annual_revenue, inputs.current_dso, inputs.target_dso,
        ))
    if (inputs.current_dpo is not None and inputs.target_dpo is not None
            and inputs.annual_cogs is not None and inputs.annual_cogs > 0):
        components.append(ap_days_to_cash(
            inputs.annual_cogs, inputs.current_dpo, inputs.target_dpo,
        ))
    if (inputs.current_dio is not None and inputs.target_dio is not None
            and inputs.annual_inventory_cost is not None
            and inputs.annual_inventory_cost > 0):
        components.append(inventory_days_to_cash(
            inputs.annual_inventory_cost, inputs.current_dio, inputs.target_dio,
        ))
    total = sum(c.cash_released for c in components)
    if total <= 0:
        note = "No working-capital release modeled."
    elif total < inputs.annual_revenue * 0.03:
        note = "Modest WC release — treat as cash-flow benefit only."
    elif total < inputs.annual_revenue * 0.08:
        note = ("Material WC release — remember: one-time, not recurring. "
                "Don't apply exit multiple.")
    else:
        note = ("Very large WC release — validate assumptions and do not "
                "count this in EBITDA.")
    return WCSummary(total_cash_released=total,
                     components=components,
                     partner_note=note)
