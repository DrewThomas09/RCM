"""Synergy curves — revenue lift + cost-out as a function of
add-on count.

Calibration: PE physician-rollup data (Wexford, Heyman) shows
synergies follow a logistic-saturation curve. The first 3-4 add-
ons in a platform deliver outsized lift; the next 3-4 deliver
half as much; beyond ~10 add-ons the platform sees diminishing
returns and integration friction starts to outweigh cost-out.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import exp


@dataclass
class SynergyCurve:
    """Logistic-saturation curve parametrized by:
      L: maximum cumulative synergy (fraction of platform EBITDA)
      k: steepness — bigger k means synergies front-load more
      x0: number of add-ons at the inflection point
    """
    L: float = 0.25
    k: float = 0.45
    x0: float = 3.5

    def cumulative(self, n_add_ons: int) -> float:
        """Cumulative synergy share at ``n_add_ons``. Returns the
        fraction of the platform's standalone EBITDA delivered as
        synergies once N add-ons have integrated."""
        if n_add_ons <= 0:
            return 0.0
        return self.L / (1.0 + exp(-self.k * (n_add_ons - self.x0)))

    def marginal(self, n_add_ons: int) -> float:
        """Marginal synergy delivered by the n-th add-on."""
        if n_add_ons <= 0:
            return 0.0
        return self.cumulative(n_add_ons) - self.cumulative(n_add_ons - 1)


def default_physician_rollup_curve() -> SynergyCurve:
    """Calibrated to median outcomes in physician/MSO rollups,
    where peak cumulative synergy lands around 25% of platform
    EBITDA after ~8 add-ons."""
    return SynergyCurve(L=0.25, k=0.45, x0=3.5)
