"""SEC EDGAR integration for public hospital systems (Prompt 40).

Maps ~25 public hospital systems (HCA, Tenet, CHS, UHS) to their
SEC CIKs. Fetches revenue, margin, and leverage from the XBRL
company facts API (``data.sec.gov/api/xbrl/companyfacts/``).
Attaches to the packet as ``system_context`` when the hospital is
system-affiliated and the parent is publicly traded.

All network calls go through stdlib ``urllib`` — no new deps.
"""
from __future__ import annotations

import json
import logging
import re
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── CIK registry ──────────────────────────────────────────────────

# Hand-mapped: system name (as it appears in HCRIS's system column)
# → SEC CIK (10-digit zero-padded). Only the ~25 publicly-traded
# systems matter — private systems (Ascension, CommonSpirit, Kaiser)
# don't file 10-Ks.
SYSTEM_CIK_MAP: Dict[str, str] = {
    "HCA Healthcare":               "0000860730",
    "HCA":                          "0000860730",
    "Tenet Healthcare":             "0000070318",
    "Tenet":                        "0000070318",
    "Community Health Systems":     "0001108109",
    "CHS":                          "0001108109",
    "Universal Health Services":    "0000352915",
    "UHS":                          "0000352915",
    "Encompass Health":             "0000785161",
    "Kindred Healthcare":           "0001060349",
    "LifePoint Health":             "0001301611",
    "Quorum Health":                "0001660734",
    "Surgery Partners":             "0001576946",
    "Acadia Healthcare":            "0001520697",
    "Select Medical":               "0001165002",
    "Ardent Health Services":       "0001137774",
    "Brookdale Senior Living":      "0001332349",
    "Molina Healthcare":            "0001179929",
    "DaVita":                       "0000927066",
    "Amedisys":                     "0000014846",
    "LHC Group":                    "0001303313",
    "Pediatrix Medical":            "0001064863",
    "ModivCare":                    "0001060714",
    "Addus HomeCare":               "0001313726",
}


@dataclass
class SystemContext:
    """Public-company context for a hospital's parent system."""
    system_name: str = ""
    cik: str = ""
    latest_annual_revenue: Optional[float] = None
    latest_annual_net_income: Optional[float] = None
    total_assets: Optional[float] = None
    debt_to_ebitda: Optional[float] = None
    fiscal_year: str = ""
    source: str = "SEC_EDGAR"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "system_name": self.system_name,
            "cik": self.cik,
            "latest_annual_revenue": self.latest_annual_revenue,
            "latest_annual_net_income": self.latest_annual_net_income,
            "total_assets": self.total_assets,
            "debt_to_ebitda": self.debt_to_ebitda,
            "fiscal_year": self.fiscal_year,
            "source": self.source,
        }


# ── EDGAR API ──────────────────────────────────────────────────────

_EDGAR_BASE = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
_USER_AGENT = "RCM-MC/1.0 (Healthcare PE diligence platform; contact: noreply@example.com)"


def _fetch_company_facts(cik: str) -> Optional[Dict[str, Any]]:
    """Fetch the XBRL company-facts JSON for one CIK.

    Returns ``None`` on any network error — callers treat this as
    "EDGAR unavailable" and fall back to the HCRIS-only profile.
    """
    url = _EDGAR_BASE.format(cik=cik.zfill(10))
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        logger.debug("EDGAR fetch for CIK %s failed: %s", cik, exc)
        return None


def _extract_latest(
    facts: Dict[str, Any], taxonomy: str, concept: str,
    *, units: str = "USD",
) -> Optional[tuple]:
    """Pull the latest annual value from the XBRL company-facts blob.

    Returns ``(value, fiscal_year)`` or ``None``.
    """
    try:
        concept_data = facts["facts"][taxonomy][concept]["units"][units]
    except (KeyError, TypeError):
        return None
    # Filter to 10-K filings (annual). Pick the most recent by ``end``.
    annual = [
        e for e in concept_data
        if e.get("form") in ("10-K", "10-K/A")
    ]
    if not annual:
        return None
    latest = max(annual, key=lambda e: e.get("end") or "")
    value = latest.get("val")
    fy = latest.get("fy") or (latest.get("end") or "")[:4]
    if value is None:
        return None
    return (float(value), str(fy))


# ── Public entry ──────────────────────────────────────────────────

def match_facility_to_system(
    hospital_name: str, state: str = "",
) -> Optional[str]:
    """Best-effort name → system name → CIK lookup.

    Partners don't always use the exact SEC-registered name; we do a
    case-insensitive substring search against the CIK map's keys.
    Returns the *system name* (not the CIK) so the caller can
    display it; the CIK is an internal detail.
    """
    if not hospital_name:
        return None
    q = hospital_name.upper()
    for system_name in SYSTEM_CIK_MAP:
        if system_name.upper() in q:
            return system_name
    return None


def fetch_system_context(
    system_name: str,
    *,
    skip_network: bool = False,
) -> SystemContext:
    """Build a :class:`SystemContext` from EDGAR for one system.

    ``skip_network=True`` returns a skeleton with just the CIK
    populated — useful for tests and offline environments. The
    skeleton is still meaningful because the CIK confirms the
    system is publicly traded.
    """
    cik = SYSTEM_CIK_MAP.get(system_name) or ""
    ctx = SystemContext(system_name=system_name, cik=cik)
    if not cik or skip_network:
        return ctx

    facts = _fetch_company_facts(cik)
    if facts is None:
        return ctx

    # Revenue — try several XBRL concepts.
    for concept in ("Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
                     "SalesRevenueNet"):
        result = _extract_latest(facts, "us-gaap", concept)
        if result:
            ctx.latest_annual_revenue, ctx.fiscal_year = result
            break

    # Net income.
    result = _extract_latest(facts, "us-gaap", "NetIncomeLoss")
    if result:
        ctx.latest_annual_net_income = result[0]

    # Total assets.
    result = _extract_latest(facts, "us-gaap", "Assets")
    if result:
        ctx.total_assets = result[0]

    return ctx
