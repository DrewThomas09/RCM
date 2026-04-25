"""SDID re-export from the shared causal-inference substrate.

The canonical implementation now lives in
``rcm_mc.causal.sdid`` so multiple downstream packets
(PortfolioSynergyPredictor, future regulatory-impact
trackers, M&A spillover analyzers) can share one SDID
implementation.

Kept here as a thin re-export so existing imports
``from rcm_mc.portfolio_synergy.sdid import sdid_estimate``
continue to work.
"""
from ..causal.sdid import sdid_estimate, SDIDResult

__all__ = ["sdid_estimate", "SDIDResult"]
