"""IRR-Attribution Packet — orthogonal decomposition of deal IRR.

ILPA 2.0 Performance Templates (effective Q1 2026) require LPs to
report deal-level IRR decomposed into orthogonal value-creation
components. Revenue growth now drives 71% of PE value creation
(vs ~25% in the 2008 era when multiple expansion dominated), so
LPs increasingly want the breakdown stated explicitly.

Components decomposed:

  1. Revenue growth — split into:
        a. Organic (same-store)
        b. M&A (add-on contribution)
  2. Margin expansion — entry margin → exit margin
  3. Multiple expansion — entry EV/EBITDA → exit EV/EBITDA
  4. Leverage — net-debt paydown over hold
  5. FX — non-USD currency translation
  6. Dividend recaps — distributions to fund LP partway through hold
  7. Sub-line credit usage — credit-line interest savings vs. LP capital

The Bain-style additive decomposition keeps the components
ORTHOGONAL — no double-counting, no cross-term arbitrariness.
Cross-terms are surfaced explicitly so the partner can see them
rather than hide them inside one of the headline components.

Public API::

    from rcm_mc.irr_attribution import (
        DealCashflows, AttributionResult,
        compute_irr, decompose_value_creation,
        format_ilpa_2_0, render_lp_narrative,
    )
"""
from .components import (
    DealCashflows,
    AttributionComponents,
    AttributionResult,
)
from .irr import compute_irr, compute_moic
from .decompose import decompose_value_creation
from .ilpa import format_ilpa_2_0, render_lp_narrative
from .fund import (
    aggregate_fund_attribution,
    format_fund_ilpa,
    FundAttributionResult,
    FundDealRow,
)

__all__ = [
    "DealCashflows",
    "AttributionComponents",
    "AttributionResult",
    "compute_irr",
    "compute_moic",
    "decompose_value_creation",
    "format_ilpa_2_0",
    "render_lp_narrative",
    "aggregate_fund_attribution",
    "format_fund_ilpa",
    "FundAttributionResult",
    "FundDealRow",
]
