"""Market-intel vendor adapters + the active-adapter registry.

Same pattern as rcm_mc.integrations.{chart_audit,contract_digitization}:

    ManualMarketIntelAdapter          — reads the curated YAMLs (default)
    StubVendorSeekingAlphaAdapter     — shape-only stub, raises with
                                         the exact HTTP endpoint an
                                         implementer should hit
    StubVendorPitchBookAdapter        — same
    StubVendorBloombergAdapter        — same

Stubs are opinionated: they raise NotImplementedError with a clear
message so a partner who thinks they're getting live data never
silently gets stale or fake values. Replace the stub class with a
real HTTP client when a subscription is in place, then install it via
``set_adapter(...)``.

Registry: ``get_adapter()`` / ``set_adapter(adapter)``. The registry
exists because the stub messages used to promise a "market-intel
adapter registry" that had never been built — installing a real vendor
adapter changed nothing anywhere. Consumers that want vendor-swappable
reads (the peer snapshot's transaction band today) route through
``get_adapter()``; the default is the curated-YAML manual adapter, so
behavior without a subscription is byte-identical to before.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from .news_feed import NewsItem, news_for_target
from .public_comps import PublicComp, list_companies
from .transaction_multiples import MultipleBand, transaction_multiple


@runtime_checkable
class MarketIntelAdapter(Protocol):
    """Common interface every adapter must implement."""

    def public_comps(self) -> List[PublicComp]: ...

    def transaction_multiple(
        self, *, specialty: str, ev_usd: Optional[float] = None,
    ) -> Optional[MultipleBand]: ...

    def news_for_target(
        self, *, specialty: Optional[str] = None,
        tickers: Optional[List[str]] = None,
        limit: int = 20,
    ) -> List[NewsItem]: ...


class ManualMarketIntelAdapter:
    """Default adapter — reads from the curated YAMLs shipped with
    the package. No network I/O."""

    def public_comps(self) -> List[PublicComp]:
        return list_companies()

    def transaction_multiple(
        self, *, specialty: str, ev_usd: Optional[float] = None,
    ) -> Optional[MultipleBand]:
        return transaction_multiple(specialty=specialty, ev_usd=ev_usd)

    def news_for_target(
        self, *, specialty: Optional[str] = None,
        tickers: Optional[List[str]] = None,
        limit: int = 20,
    ) -> List[NewsItem]:
        return news_for_target(
            specialty=specialty, tickers=tickers, limit=limit,
        )


# ---------------------------------------------------------------------------
# Active-adapter registry
# ---------------------------------------------------------------------------

_ACTIVE_ADAPTER: MarketIntelAdapter = ManualMarketIntelAdapter()


def get_adapter() -> MarketIntelAdapter:
    """Return the adapter market-intel reads route through.

    Defaults to :class:`ManualMarketIntelAdapter` (curated YAMLs, no
    network I/O) so offline behavior is unchanged until someone
    explicitly installs a vendor client.
    """
    return _ACTIVE_ADAPTER


def set_adapter(adapter: MarketIntelAdapter) -> MarketIntelAdapter:
    """Install ``adapter`` as the active source; returns the previous one.

    Returning the previous adapter makes temporary swaps restorable
    (``prev = set_adapter(vendor); ... ; set_adapter(prev)``) — tests
    and short-lived vendor trials must not leave a global behind.
    Rejects objects that don't satisfy the protocol so a half-built
    client fails at install time, not on a partner's page load.
    """
    if not isinstance(adapter, MarketIntelAdapter):
        raise TypeError(
            "adapter must implement MarketIntelAdapter "
            "(public_comps / transaction_multiple / news_for_target)"
        )
    global _ACTIVE_ADAPTER
    previous = _ACTIVE_ADAPTER
    _ACTIVE_ADAPTER = adapter
    return previous


class StubVendorSeekingAlphaAdapter:
    """Documents what a Seeking Alpha integration would look like.

    Endpoints (as of Seeking Alpha's published API reference):
        GET https://seekingalpha.com/api/v3/symbols/{ticker}/key-data
        GET https://seekingalpha.com/api/v3/symbols/{ticker}/news
        GET https://seekingalpha.com/api/v3/symbols/{ticker}/consensus-estimates

    Every method raises NotImplementedError with the exact endpoint
    to hit. No silent-fake returns."""

    BASE = "https://seekingalpha.com/api/v3"

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("api_key required")
        self.api_key = api_key

    def public_comps(self) -> List[PublicComp]:
        raise NotImplementedError(
            f"Implement GET {self.BASE}/symbols/{{ticker}}/key-data "
            "for each of HCA, THC, CYH, UHS, EHC, ARDT and map the "
            "response into PublicComp. Install the implemented client "
            "via rcm_mc.market_intel.adapters.set_adapter(...)."
        )

    def transaction_multiple(
        self, *, specialty: str, ev_usd: Optional[float] = None,
    ) -> Optional[MultipleBand]:
        raise NotImplementedError(
            "Seeking Alpha doesn't surface private M&A multiples. "
            "Use StubVendorPitchBookAdapter for that capability."
        )

    def news_for_target(
        self, *, specialty: Optional[str] = None,
        tickers: Optional[List[str]] = None,
        limit: int = 20,
    ) -> List[NewsItem]:
        raise NotImplementedError(
            f"Implement GET {self.BASE}/symbols/{{ticker}}/news for "
            f"each ticker ({tickers or []}) and map response items "
            "into NewsItem. Filter by specialty via the article's "
            "tags. Fall back to the manual adapter when rate-limited."
        )


class StubVendorPitchBookAdapter:
    """PitchBook has private-market deal data. Documents the
    relevant endpoints."""

    BASE = "https://api.pitchbook.com/v1"

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("api_key required")
        self.api_key = api_key

    def public_comps(self) -> List[PublicComp]:
        raise NotImplementedError(
            "PitchBook's main value is private-market comparables, "
            "not public. For public comps, use the Seeking Alpha "
            "or Bloomberg adapter."
        )

    def transaction_multiple(
        self, *, specialty: str, ev_usd: Optional[float] = None,
    ) -> Optional[MultipleBand]:
        raise NotImplementedError(
            f"Implement GET {self.BASE}/deals?industry={specialty}"
            f"&size_usd={ev_usd} and aggregate EV/EBITDA "
            "percentiles from the last 12 months of clears."
        )

    def news_for_target(
        self, *, specialty: Optional[str] = None,
        tickers: Optional[List[str]] = None,
        limit: int = 20,
    ) -> List[NewsItem]:
        raise NotImplementedError(
            f"Implement GET {self.BASE}/news?industry={specialty} "
            "and map response into NewsItem."
        )


class StubVendorBloombergAdapter:
    """Bloomberg Terminal + Bloomberg API data. Requires BBG auth."""

    BASE = "https://api.bloomberg.com/v1"

    def __init__(self, auth_token: str):
        if not auth_token:
            raise ValueError("auth_token required")
        self.auth_token = auth_token

    def public_comps(self) -> List[PublicComp]:
        raise NotImplementedError(
            f"Implement GET {self.BASE}/securities/{{ticker}}/"
            "fundamentals via Bloomberg's BDP fields "
            "(MARKET_CAP, EV_TO_EBITDA, REVENUE, etc.). Map to "
            "PublicComp."
        )

    def transaction_multiple(
        self, *, specialty: str, ev_usd: Optional[float] = None,
    ) -> Optional[MultipleBand]:
        raise NotImplementedError(
            "Bloomberg M&A module: query deals by healthcare "
            "sub-industry + size. Not the right source for PE-only "
            "aggregates; prefer PitchBook."
        )

    def news_for_target(
        self, *, specialty: Optional[str] = None,
        tickers: Optional[List[str]] = None,
        limit: int = 20,
    ) -> List[NewsItem]:
        raise NotImplementedError(
            f"Implement GET {self.BASE}/news/search via Bloomberg's "
            f"NSE function, filtered by ticker list ({tickers or []}) "
            f"and topic. Map to NewsItem. Highest-quality source for "
            "time-sensitive headlines but requires BBG auth."
        )
