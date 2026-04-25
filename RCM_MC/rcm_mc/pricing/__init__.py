"""Price-transparency foundation: NPPES, Hospital MRF, Payer TiC.

This package is the shared data substrate that downstream systems
build on:

  • NPPES (National Plan & Provider Enumeration System) — public
    NPI registry with organizational identities, taxonomies, and
    addresses. The Type-2 (organizational) subset is the join key
    for everything downstream.
  • Hospital Machine-Readable Files (CMS Hospital Price Transparency
    rule, effective 2021) — every hospital must publish all five
    charge types (gross, discounted cash, payer-specific negotiated,
    de-identified min, de-identified max) for every shoppable
    service. Schema: CMS Hospital Price Transparency JSON v2.0.
  • Transparency in Coverage (TiC) Payer MRFs — every commercial
    payer must publish in-network negotiated rates keyed by
    billing-provider NPI + CPT/HCPCS/DRG. Schema: CMS TiC v1.1.

Public API::

    from rcm_mc.pricing import (
        # Storage
        PricingStore,
        # Normalization
        normalize_code, normalize_payer_name, zip_to_cbsa,
        # Parsers
        parse_nppes_csv, parse_hospital_mrf, parse_payer_tic_mrf,
        # Loaders (parser → store)
        load_nppes, load_hospital_mrf, load_payer_tic_mrf,
        # Read helpers (downstream systems consume these)
        get_provider_npi, list_charges_by_code,
        list_negotiated_rates_by_npi,
    )

Downstream systems (PayerNegotiationSimulator, ReferralNetworkPacket,
BuyAndBuildOptimizer, ESG packet, VBC-ContractValuator) read from
the normalized tables this package writes — they should never parse
raw MRF files directly.
"""
from .store import PricingStore
from .normalize import (
    normalize_code,
    normalize_payer_name,
    zip_to_cbsa,
    classify_service_line,
)
from .nppes import parse_nppes_csv, load_nppes
from .hospital_mrf import parse_hospital_mrf, load_hospital_mrf
from .payer_mrf import parse_payer_tic_mrf, load_payer_tic_mrf
from .reads import (
    get_provider_npi,
    list_charges_by_code,
    list_negotiated_rates_by_npi,
    list_negotiated_rates_for_code,
)

__all__ = [
    "PricingStore",
    "normalize_code",
    "normalize_payer_name",
    "zip_to_cbsa",
    "classify_service_line",
    "parse_nppes_csv",
    "load_nppes",
    "parse_hospital_mrf",
    "load_hospital_mrf",
    "parse_payer_tic_mrf",
    "load_payer_tic_mrf",
    "get_provider_npi",
    "list_charges_by_code",
    "list_negotiated_rates_by_npi",
    "list_negotiated_rates_for_code",
]
