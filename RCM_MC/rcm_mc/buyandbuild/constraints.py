"""Sequence constraints: regulatory blocking + geographic density.

Two checks the optimizer runs at every branch:

  • Regulatory-blocking probability: each add-on's regulatory
    topics drive a per-add-on probability of FTC/DOJ/state-AG
    blocking (or material divestiture). Compounded across a
    sequence.

  • Geographic density: an add-on in the platform's existing CBSA
    has higher synergy AND higher antitrust risk than one in a
    new market.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional

from .candidates import AddOnCandidate, Platform


# Per-topic blocking probability lifts. These are calibrated
# against the public FTC enforcement record for the named topics:
#   • ftc_noncompete deals get scrutinized at higher rates
#   • state_con_cpom adds state-AG review where applicable
#   • site_neutral / v28 don't drive transaction blocking directly
_TOPIC_BLOCK_LIFTS = {
    "ftc_noncompete":     0.04,
    "state_con_cpom":     0.06,
    "antitrust_market":   0.10,
    "stark_kickback":     0.02,
}


def regulatory_block_prob(addon: AddOnCandidate) -> float:
    """Per-add-on probability of regulatory blocking. Combines the
    base closing risk with topic-specific lifts."""
    base = max(0.0, min(1.0, addon.closing_risk_pct))
    lift = 0.0
    for topic in (addon.regulatory_topics or []):
        lift += _TOPIC_BLOCK_LIFTS.get(topic, 0.01)
    # Compound: 1 − (1 − base)(1 − lift)
    return min(0.95, 1.0 - (1.0 - base) * (1.0 - lift))


def geographic_density_score(
    platform: Platform,
    addon: AddOnCandidate,
) -> float:
    """0-1 density score. Same CBSA = 1.0, same state different CBSA
    = 0.6, different state = 0.2. The optimizer rewards higher
    density (synergy) but pairs it against antitrust risk."""
    if platform.cbsa and addon.cbsa and platform.cbsa == addon.cbsa:
        return 1.0
    if platform.state and addon.state and platform.state == addon.state:
        return 0.6
    return 0.2


@dataclass
class SequenceConstraints:
    """Hard limits the optimizer respects."""
    max_addons: int = 8
    max_total_capital_mm: float = 500.0
    max_cumulative_block_prob: float = 0.5  # walk if expected
                                            # blocking exceeds this
