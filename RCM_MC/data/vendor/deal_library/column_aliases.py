"""Column-alias map: vendor export headers → canonical Deal Library fields.

Capital IQ screening headers carry long suffixes (units, rate basis, "[LTM]",
"[My Setting] [Latest]"), and other vendors / hand-built sheets use shorter
names. Matching is done on a *normalized* header (lowercased, bracketed
qualifiers and unit/rate parentheticals stripped, whitespace collapsed) so a
header like::

    "Total Enterprise Value [My Setting] [Latest] ($USDmm, Historical rate)"

normalizes to ``"total enterprise value"`` and maps to ``enterprise_value``.

The two licensed exports profiled (Company Screening Reports 1 & 2) are
*company* screens — sponsor-backed healthcare companies — so the canonical
target here is the company schema. Transaction-only aliases are included for
when a CapIQ *Transactions* screen is ingested later; they simply won't match
in a company export.
"""
from __future__ import annotations

import re

# normalized-header  ->  canonical field
ALIASES: dict[str, str] = {
    # ── identity / classification ──
    "company name": "company_name",
    "target": "company_name",
    "target name": "company_name",
    "target company": "company_name",
    "company": "company_name",
    "issuer name": "company_name",
    "exchange:ticker": "ticker",
    "ticker": "ticker",
    "industry classifications": "industry",
    "industry classification": "industry",
    "industry": "industry",
    "gics sub-industry": "industry",
    "primary industry": "industry",
    "company status": "company_status",
    "ownership status": "ownership_status",   # CapIQ packs the sponsor here
    # ── financials (company-level, $USDmm) ──
    "total enterprise value": "enterprise_value",
    "enterprise value": "enterprise_value",
    "tev": "enterprise_value",
    "ebitda": "ebitda",
    "ebitda ltm": "ebitda",
    "total revenue": "revenue",
    "revenue": "revenue",
    "total revenue ltm": "revenue",
    "ltm revenue": "revenue",
    "implied market capitalization": "market_cap",
    "market capitalization": "market_cap",
    "market cap": "market_cap",
    "number of employees - us": "employees",
    "number of employees": "employees",
    "employees": "employees",
    "total amount raised": "amount_raised",
    "amount raised": "amount_raised",
    # ── location / web ──
    "website": "website",
    "primary address": "address",
    "address": "address",
    "geographic locations": "geography",
    "geography": "geography",
    # ── transaction-only (future CapIQ Transactions screen) ──
    "buyer": "buyer_name",
    "acquirer": "buyer_name",
    "seller": "seller_name",
    "vendor": "seller_name",
    "transaction value": "transaction_value",
    "ev/revenue": "ev_revenue_multiple",
    "tev/revenue": "ev_revenue_multiple",
    "ev/ebitda": "ev_ebitda_multiple",
    "tev/ebitda": "ev_ebitda_multiple",
    "announced date": "announcement_date",
    "announcement date": "announcement_date",
    "closed date": "close_date",
    "closing date": "close_date",
}

# Core fields used for the completeness score (company library).
CORE_COMPANY_FIELDS = (
    "company_name", "industry", "ownership_status", "company_status",
    "geography", "revenue", "enterprise_value", "website",
)

_BRACKET = re.compile(r"\[[^\]]*\]")            # [LTM], [My Setting], [Latest]
_PAREN = re.compile(r"\([^)]*\)")               # ($USDmm, Historical rate)
_WS = re.compile(r"\s+")


def normalize_header(raw: str) -> str:
    """Lowercase, strip bracketed/paren qualifiers, collapse whitespace."""
    s = str(raw or "").strip()
    s = _BRACKET.sub("", s)
    s = _PAREN.sub("", s)
    s = _WS.sub(" ", s).strip().lower()
    return s


def map_header(raw: str) -> str | None:
    """Canonical field for an export header, or None if unmapped."""
    return ALIASES.get(normalize_header(raw))
