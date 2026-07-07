"""Market intelligence layer — public healthcare operator comps,
PE transaction multiples, and a curated news feed.

The platform's CCD-driven target analytics are opinion-ated about
what's true for one target; market-intel gives the partner the
"what does the market think this is worth" overlay.

Public data only in the seeded YAMLs (10-K filings, public 10-Q
disclosures, published aggregates from Mertz Taggart / SRS
Acquiom / Levin Associates, news headlines from Modern Healthcare
/ STAT / Seeking Alpha / KFF).

When a real Seeking Alpha / PitchBook / Bloomberg subscription is
available, swap the ``StubVendor*Adapter`` classes in
``adapters.py`` for HTTP clients — the shape is documented in each
stub.

Public API::

    from rcm_mc.market_intel import (
        PublicComp, find_comparables, category_bands,
        list_companies, transaction_multiple,
        news_for_target, sector_sentiment,
        StubVendorSeekingAlphaAdapter,
        StubVendorPitchBookAdapter,
        StubVendorBloombergAdapter,
        ManualMarketIntelAdapter,
    )
"""
from __future__ import annotations

from .adapters import (
    ManualMarketIntelAdapter, StubVendorBloombergAdapter,
    StubVendorPitchBookAdapter, StubVendorSeekingAlphaAdapter,
    get_adapter, set_adapter,
)
from .content_vintage import (
    content_freshness_report, content_vintage,
)
from .news_feed import NewsItem, news_for_target, sector_sentiment
from .public_comps import (
    AnalystCoverage, CategoryBand, EarningsLatest, PublicComp,
    category_bands, find_comparables, list_companies,
    peer_physician_turnover_stats,
)
from .peer_snapshot import (
    ASSUMED_EBITDA_MARGIN, PeerSnapshot, compute_peer_snapshot,
)
from .labor_market import (
    LaborStress, RoleEconomics, get_role, labor_cost_stress,
    list_roles,
)
from .ma_penetration import (
    StatePenetration, band_counts, footprint_exposure, get_state,
    list_state_penetration, national_penetration_pct,
)
from .rate_environment import (
    BlendedImpact, RateUpdate, SettingRates, blended_rate_impact,
    get_setting, list_settings,
)
from .pe_transactions import (
    PETransaction, list_transactions, multiple_band_by_specialty,
    sponsor_activity, transactions_for_specialty,
)
from .transaction_multiples import (
    SMALL_SAMPLE_FLOOR, MultipleBand, list_specialty_bands,
    transaction_multiple,
)

__all__ = [
    "ASSUMED_EBITDA_MARGIN",
    "SMALL_SAMPLE_FLOOR",
    "AnalystCoverage",
    "CategoryBand",
    "content_freshness_report",
    "content_vintage",
    "get_adapter",
    "set_adapter",
    "EarningsLatest",
    "ManualMarketIntelAdapter",
    "MultipleBand",
    "NewsItem",
    "PETransaction",
    "PeerSnapshot",
    "PublicComp",
    "BlendedImpact",
    "LaborStress",
    "RoleEconomics",
    "get_role",
    "labor_cost_stress",
    "list_roles",
    "StatePenetration",
    "band_counts",
    "footprint_exposure",
    "get_state",
    "list_state_penetration",
    "national_penetration_pct",
    "RateUpdate",
    "SettingRates",
    "blended_rate_impact",
    "get_setting",
    "list_settings",
    "compute_peer_snapshot",
    "list_transactions",
    "multiple_band_by_specialty",
    "sponsor_activity",
    "transactions_for_specialty",
    "StubVendorBloombergAdapter",
    "StubVendorPitchBookAdapter",
    "StubVendorSeekingAlphaAdapter",
    "category_bands",
    "find_comparables",
    "list_companies",
    "list_specialty_bands",
    "news_for_target",
    "peer_physician_turnover_stats",
    "sector_sentiment",
    "transaction_multiple",
]
