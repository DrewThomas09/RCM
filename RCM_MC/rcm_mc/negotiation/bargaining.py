"""Nash bargaining + repeated-game rate-setting.

Standard Nash bargaining for a single round: the negotiated rate
splits the bargaining surplus weighted by each side's bargaining
power. With equal power, the rate sits at the midpoint of the
provider's and payer's reservation prices.

  rate = provider_floor + alpha × (payer_ceiling − provider_floor)

Where alpha ∈ [0, 1] is the provider's share of the surplus —
0.5 = equal power, 0.7 = strong provider, 0.3 = strong payer.

For multi-round dynamics we add a ``leverage`` term that
modulates alpha based on how rerouteable the volume is (lower
re-routability → stronger provider → higher alpha).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

from .outside_options import OutsideOptions


@dataclass
class BargainingState:
    """Inputs + outputs of one bargaining round."""
    npi: str
    code: str
    payer_name: str = ""
    provider_floor: float = 0.0      # provider's reservation
    payer_ceiling: float = 0.0       # payer's reservation
    alpha: float = 0.5               # provider's share of surplus
    leverage: float = 0.5            # 0-1, payer-leverage from referral pkg
    negotiated_rate: float = 0.0
    surplus_split_provider: float = 0.0
    surplus_split_payer: float = 0.0


def nash_bargaining(
    outside: OutsideOptions,
    *,
    payer_name: str = "",
    alpha: float = 0.5,
) -> BargainingState:
    """Single-round Nash bargaining over the outside-options
    surplus.

    ``alpha`` is the provider's share of the surplus. With alpha=0.5
    the negotiated rate sits at the midpoint of the (p25, p75)
    band; with alpha=0.8 the rate is closer to p75 (provider
    strong).
    """
    floor = outside.p25 or 0.0
    ceiling = outside.p75 or floor
    a = max(0.0, min(1.0, alpha))
    rate = floor + a * (ceiling - floor)
    surplus = ceiling - floor

    return BargainingState(
        npi=outside.npi, code=outside.code,
        payer_name=payer_name,
        provider_floor=round(floor, 2),
        payer_ceiling=round(ceiling, 2),
        alpha=a,
        negotiated_rate=round(rate, 2),
        surplus_split_provider=round(a * surplus, 2),
        surplus_split_payer=round((1 - a) * surplus, 2),
    )


def repeated_game_rate(
    outside: OutsideOptions,
    *,
    payer_name: str,
    payer_leverage: float = 0.5,
    rounds: int = 4,
    discount: float = 0.92,
) -> BargainingState:
    """Multi-round bargaining with reputation/concession dynamics.

    Each round, the parties update alpha based on payer_leverage
    (the % of the provider's volume the payer could re-route to
    alternative in-network providers). Higher payer_leverage →
    weaker provider → smaller alpha.

    The discount factor models patience: parties closer to 1.0 are
    willing to wait, which structurally shifts power toward the
    party with more outside options.

    Returns the final bargaining state after ``rounds`` rounds.
    """
    leverage = max(0.0, min(1.0, payer_leverage))
    alpha = 0.5

    for r in range(rounds):
        # Each round nudges alpha toward (1 − leverage) — i.e. the
        # provider's structural share of bargaining power. The pace
        # is governed by the discount factor: lower discount = faster
        # convergence (parties impatient).
        target_alpha = 1.0 - leverage
        speed = 1.0 - discount
        alpha = alpha + speed * (target_alpha - alpha)

    state = nash_bargaining(outside, payer_name=payer_name, alpha=alpha)
    state.leverage = round(leverage, 3)
    return state
