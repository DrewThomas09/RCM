"""Quality of Earnings (QoE) auto-flagger.

Identifies the EBITDA adjustments PE diligence teams hand-find by
combining two complementary detection paths:

  1. **Rule-based detectors** — deterministic checks for the six
     standard QoE adjustment categories:
       a. Non-recurring items (one-time gains, lawsuit settlements)
       b. Owner compensation (excess vs benchmark)
       c. Revenue recognition (premature recognition, channel stuffing)
       d. NWC manipulation (year-end inventory or AR stuffing)
       e. Related-party transactions (off-market terms)
       f. Proof-of-cash gaps (revenue vs cash receipts)

  2. **Isolation-forest anomaly detection** — pure-numpy isolation
     forest over the financial line-items panel; flags rows whose
     value-in-period is anomalous given the same line in prior
     periods.

Plus three healthcare-specific signals:

  • 340B accumulator revenue (drug discount margin trapped in WC)
  • OON balance billing (revenue with elevated bad-debt risk)
  • Cash-pay mix shifts (margin-distorting business mix changes)

Output is partner-ready: a list of flagged adjustments with
confidence, the resulting EBITDA bridge from reported → adjusted,
and a normalized NWC schedule.

Public API::

    from rcm_mc.qoe import (
        QoEFlag, QoEResult,
        run_qoe_flagger,
        compute_ebitda_bridge,
        normalize_nwc,
        IsolationForest, isolation_forest_scores,
    )
"""
from .detectors import QoEFlag, run_rule_detectors
from .isolation_forest import (
    IsolationForest,
    isolation_forest_scores,
)
from .bridge import (
    compute_ebitda_bridge,
    normalize_nwc,
    EBITDABridge,
    NWCNormalization,
)
from .flagger import run_qoe_flagger, QoEResult

__all__ = [
    "QoEFlag",
    "QoEResult",
    "run_qoe_flagger",
    "run_rule_detectors",
    "compute_ebitda_bridge",
    "normalize_nwc",
    "EBITDABridge",
    "NWCNormalization",
    "IsolationForest",
    "isolation_forest_scores",
]
