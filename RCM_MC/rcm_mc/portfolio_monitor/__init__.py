"""Portfolio Monitoring Dashboard — actual vs plan + early warnings.

Once a deal closes, the GP needs to track it against the
underwriting plan: is EBITDA on plan? Is the comparable-deal
trajectory consistent with where the asset sits today? Which
assets are ahead of plan, which are behind, and which are
flashing early-warning signals that warrant operating-partner
intervention?

Three modules:

  • snapshot     PortfolioAsset + PortfolioSnapshot dataclasses
                 capturing per-deal plan vs actual + the
                 prediction reference (typically the comparable-
                 deal MOIC distribution at acquisition).
  • variance     compute per-deal variance from plan + classify
                 each into a status band (on-track / watch /
                 early-warning / outperforming). Surfaces the
                 portfolio-wide projected-vs-actual EBITDA
                 bridge for the dashboard cover.
  • dashboard    HTML renderer — sortable per-deal table +
                 KPI tiles + bridge waterfall.

HTTP route: /portfolio/monitor.

Public API::

    from rcm_mc.portfolio_monitor import (
        PortfolioAsset, PortfolioSnapshot,
        compute_variance, AssetVariance, PortfolioVariance,
        render_monitor_dashboard,
    )
"""
from .snapshot import PortfolioAsset, PortfolioSnapshot
from .variance import (
    compute_variance,
    AssetVariance,
    PortfolioVariance,
)
from .dashboard import render_monitor_dashboard

__all__ = [
    "PortfolioAsset", "PortfolioSnapshot",
    "compute_variance", "AssetVariance", "PortfolioVariance",
    "render_monitor_dashboard",
]
