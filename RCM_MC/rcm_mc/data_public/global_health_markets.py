"""Curated, source-cited macro indicators for international healthcare markets.

The first international dataset for the platform: current health expenditure
as a share of GDP for the developed and emerging markets where healthcare
private equity is most active. It anchors the global market map and the
country comparison views — a bigger health-spend share is a first-order proxy
for addressable-market size in a healthcare-PE thesis.

Credibility / provenance
------------------------
Figures are **current health expenditure as % of GDP**, the standard
OECD/World Bank "SHA" indicator, latest widely-published year (~2021-2022).
They are rounded to one decimal and are *approximate* — methodology and the
reference year vary slightly by source — but the relative ordering (the US
near 16-17%, Western Europe ~10-13%, emerging markets lower) is robust and is
what the analysis relies on. Source: OECD Health Statistics 2023 + World Bank
World Development Indicators (both public). Not a substitute for a current
data pull in live underwriting.

``HEALTH_MARKETS`` keys are ISO-3166 alpha-2 codes so they join directly to
the vendored world map (``ui/_world_geo_paths.py``).
"""
from __future__ import annotations

from typing import Any, Dict, List

# Source note carried into the UI so the figures are never shown unattributed.
SOURCE_NOTE = (
    "Current health expenditure as % of GDP — OECD Health Statistics 2023 + "
    "World Bank WDI (public), latest available year (~2021-2022), approximate."
)

# Markets where healthcare PE is active. ``pe_active`` flags the most active
# sponsor markets (used as the map's accent set). ``region`` groups for tables.
#   iso2: (name, health_exp_pct_gdp, region, pe_active)
HEALTH_MARKETS: Dict[str, Dict[str, Any]] = {
    "US": {"name": "United States", "health_pct_gdp": 16.6, "region": "North America", "pe_active": True},
    "DE": {"name": "Germany", "health_pct_gdp": 12.7, "region": "Europe", "pe_active": True},
    "FR": {"name": "France", "health_pct_gdp": 12.1, "region": "Europe", "pe_active": True},
    "JP": {"name": "Japan", "health_pct_gdp": 11.5, "region": "Asia-Pacific", "pe_active": True},
    "CA": {"name": "Canada", "health_pct_gdp": 11.2, "region": "North America", "pe_active": True},
    "CH": {"name": "Switzerland", "health_pct_gdp": 11.7, "region": "Europe", "pe_active": True},
    "AT": {"name": "Austria", "health_pct_gdp": 11.4, "region": "Europe", "pe_active": False},
    "GB": {"name": "United Kingdom", "health_pct_gdp": 11.3, "region": "Europe", "pe_active": True},
    "BE": {"name": "Belgium", "health_pct_gdp": 11.1, "region": "Europe", "pe_active": True},
    "SE": {"name": "Sweden", "health_pct_gdp": 11.0, "region": "Europe", "pe_active": True},
    "DK": {"name": "Denmark", "health_pct_gdp": 10.8, "region": "Europe", "pe_active": False},
    "NL": {"name": "Netherlands", "health_pct_gdp": 10.2, "region": "Europe", "pe_active": True},
    "NO": {"name": "Norway", "health_pct_gdp": 10.1, "region": "Europe", "pe_active": False},
    "PT": {"name": "Portugal", "health_pct_gdp": 10.6, "region": "Europe", "pe_active": False},
    "ES": {"name": "Spain", "health_pct_gdp": 10.5, "region": "Europe", "pe_active": True},
    "AU": {"name": "Australia", "health_pct_gdp": 10.6, "region": "Asia-Pacific", "pe_active": True},
    "FI": {"name": "Finland", "health_pct_gdp": 10.0, "region": "Europe", "pe_active": False},
    "NZ": {"name": "New Zealand", "health_pct_gdp": 9.8, "region": "Asia-Pacific", "pe_active": False},
    "IT": {"name": "Italy", "health_pct_gdp": 9.4, "region": "Europe", "pe_active": True},
    "KR": {"name": "South Korea", "health_pct_gdp": 9.7, "region": "Asia-Pacific", "pe_active": True},
    "GR": {"name": "Greece", "health_pct_gdp": 9.1, "region": "Europe", "pe_active": False},
    "SI": {"name": "Slovenia", "health_pct_gdp": 9.5, "region": "Europe", "pe_active": False},
    "CZ": {"name": "Czechia", "health_pct_gdp": 9.1, "region": "Europe", "pe_active": False},
    "BR": {"name": "Brazil", "health_pct_gdp": 9.9, "region": "Latin America", "pe_active": True},
    "CL": {"name": "Chile", "health_pct_gdp": 9.0, "region": "Latin America", "pe_active": False},
    "IL": {"name": "Israel", "health_pct_gdp": 7.4, "region": "Middle East", "pe_active": True},
    "PL": {"name": "Poland", "health_pct_gdp": 6.7, "region": "Europe", "pe_active": True},
    "IE": {"name": "Ireland", "health_pct_gdp": 6.1, "region": "Europe", "pe_active": True},
    "HU": {"name": "Hungary", "health_pct_gdp": 7.0, "region": "Europe", "pe_active": False},
    "MX": {"name": "Mexico", "health_pct_gdp": 5.5, "region": "Latin America", "pe_active": False},
    "CN": {"name": "China", "health_pct_gdp": 5.4, "region": "Asia-Pacific", "pe_active": True},
    "IN": {"name": "India", "health_pct_gdp": 3.3, "region": "Asia-Pacific", "pe_active": True},
}


def health_exp_values() -> Dict[str, float]:
    """ISO2 → health-expenditure-%GDP, for the map choropleth."""
    return {iso2: rec["health_pct_gdp"] for iso2, rec in HEALTH_MARKETS.items()}


def pe_active_markets() -> set:
    """ISO2 set of the most active healthcare-PE sponsor markets (map accent)."""
    return {iso2 for iso2, rec in HEALTH_MARKETS.items() if rec.get("pe_active")}


def ranked_markets() -> List[Dict[str, Any]]:
    """Markets sorted by health-spend share, descending (for the table)."""
    rows = [{"iso2": k, **v} for k, v in HEALTH_MARKETS.items()]
    rows.sort(key=lambda r: -r["health_pct_gdp"])
    return rows
