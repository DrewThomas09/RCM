"""Normalize raw deal dicts to the canonical public_deals schema.

Handles column-name aliases from various sources (EDGAR, PE firm pages,
manual entry, CSV imports) and normalizes units (B→M, %, x multiples).

Canonical output keys:
    source_id, source, deal_name, year, buyer, seller,
    ev_mm, ebitda_at_entry_mm, hold_years,
    realized_moic, realized_irr, payer_mix, notes

Public API:
    normalize_raw(raw: dict)        -> dict
    normalize_batch(raws: list)     -> list
    validate(deal: dict)            -> list[str]   (list of warning strings)
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Column alias maps — maps known variant names → canonical name
# ---------------------------------------------------------------------------
_ALIAS_SOURCE_ID = {"id", "deal_id", "external_id", "filing_id", "source_id"}
_ALIAS_SOURCE    = {"data_source", "origin", "source"}
_ALIAS_NAME      = {"name", "deal_name", "deal", "transaction", "transaction_name",
                    "company", "target_company"}
_ALIAS_YEAR      = {"year", "close_year", "deal_year", "year_closed", "vintage"}
_ALIAS_BUYER     = {"buyer", "acquirer", "sponsor", "pe_firm", "investor"}
_ALIAS_SELLER    = {"seller", "target", "divesting_party", "previous_owner"}
_ALIAS_EV        = {"ev_mm", "ev", "enterprise_value", "enterprise_value_mm",
                    "transaction_value", "purchase_price_mm", "total_consideration_mm"}
_ALIAS_EBITDA    = {"ebitda_at_entry_mm", "ebitda_entry", "entry_ebitda",
                    "ebitda", "ebitda_mm", "lqe_ebitda"}
_ALIAS_HOLD      = {"hold_years", "hold_period", "hold_period_years", "years_held"}
_ALIAS_MOIC      = {"realized_moic", "moic", "exit_moic", "gross_moic", "tvpi",
                    "gross_tvpi", "money_multiple"}
_ALIAS_IRR       = {"realized_irr", "irr", "gross_irr", "net_irr", "exit_irr"}
_ALIAS_PAYER_MIX = {"payer_mix", "payer_mix_json", "payer_breakdown", "mix"}
_ALIAS_NOTES     = {"notes", "description", "comment", "remarks", "memo"}


def _pick(raw: Dict[str, Any], aliases: set, default: Any = None) -> Any:
    """Return the first value found in raw for any alias in the alias set."""
    for key in aliases:
        if key in raw:
            return raw[key]
    return default


def _parse_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().replace(",", "").replace("$", "").replace("%", "")
    try:
        return float(s)
    except ValueError:
        return None


def _parse_int(val: Any) -> Optional[int]:
    f = _parse_float(val)
    return int(round(f)) if f is not None else None


def _normalize_ev(raw: Dict[str, Any]) -> Optional[float]:
    """Return EV in $M, handling B/M suffixes and x-EBITDA strings."""
    raw_val = _pick(raw, _ALIAS_EV)
    if raw_val is None:
        return None

    if isinstance(raw_val, str):
        s = raw_val.strip()
        # "$4.3B" or "4.3 billion"
        m = re.match(r"^\$?\s*([\d,.]+)\s*([BbMmKk])?(?:illion|illion)?$", s)
        if m:
            num = float(m.group(1).replace(",", ""))
            suffix = (m.group(2) or "M").upper()
            if suffix == "B":
                return num * 1_000
            if suffix == "K":
                return num / 1_000
            return num
        return _parse_float(raw_val)

    val = _parse_float(raw_val)
    if val is None:
        return None
    # Heuristic: values < 10 are probably in $B (e.g., 4.3 → $4,300M)
    if val < 10:
        val *= 1_000
    return val


def _normalize_moic(val: Any) -> Optional[float]:
    if val is None:
        return None
    f = _parse_float(val)
    if f is None:
        return None
    # Values > 50 are almost certainly percentage-form (200% = 2.0x MOIC)
    if f > 50:
        return f / 100.0
    return f


def _normalize_irr(val: Any) -> Optional[float]:
    if val is None:
        return None
    f = _parse_float(val)
    if f is None:
        return None
    # IRR stored as 23.5 (percent) vs 0.235 (decimal)
    if abs(f) > 1.5:
        return f / 100.0
    return f


def _normalize_payer_mix(val: Any) -> Optional[Dict[str, float]]:
    if val is None:
        return None
    if isinstance(val, dict):
        return {k: float(v) for k, v in val.items()}
    if isinstance(val, str):
        try:
            d = json.loads(val)
            if isinstance(d, dict):
                return {k: float(v) for k, v in d.items()}
        except (json.JSONDecodeError, ValueError):
            pass
    return None


def normalize_raw(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize one raw deal dict into the canonical public_deals schema.

    Unknown keys are silently dropped.  None is used for genuinely missing
    values so callers can distinguish "zero" from "not disclosed".
    """
    source_id = _pick(raw, _ALIAS_SOURCE_ID, default="")
    if not source_id:
        # Build a deterministic ID from name + year when none provided
        name = str(_pick(raw, _ALIAS_NAME, default="unknown"))
        year = str(_pick(raw, _ALIAS_YEAR, default="0"))
        source_id = re.sub(r"[^a-z0-9_]", "_", f"auto_{name}_{year}".lower())[:80]

    return {
        "source_id":            source_id,
        "source":               str(_pick(raw, _ALIAS_SOURCE, default="manual")),
        "deal_name":            str(_pick(raw, _ALIAS_NAME, default="Unknown Deal")),
        "year":                 _parse_int(_pick(raw, _ALIAS_YEAR)),
        "buyer":                _pick(raw, _ALIAS_BUYER),
        "seller":               _pick(raw, _ALIAS_SELLER),
        "ev_mm":                _normalize_ev(raw),
        "ebitda_at_entry_mm":   _parse_float(_pick(raw, _ALIAS_EBITDA)),
        "hold_years":           _parse_float(_pick(raw, _ALIAS_HOLD)),
        "realized_moic":        _normalize_moic(_pick(raw, _ALIAS_MOIC)),
        "realized_irr":         _normalize_irr(_pick(raw, _ALIAS_IRR)),
        "payer_mix":            _normalize_payer_mix(_pick(raw, _ALIAS_PAYER_MIX)),
        "notes":                str(_pick(raw, _ALIAS_NOTES, default="")),
    }


def normalize_batch(raws: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [normalize_raw(r) for r in raws]


def validate(deal: Dict[str, Any]) -> List[str]:
    """Return a list of warning strings for suspicious or missing values.

    Empty list means the deal looks clean.
    """
    warnings: List[str] = []

    if not deal.get("deal_name") or deal["deal_name"] == "Unknown Deal":
        warnings.append("deal_name missing")
    if deal.get("year") and (deal["year"] < 1980 or deal["year"] > 2030):
        warnings.append(f"year {deal['year']} out of expected range 1980-2030")

    ev = deal.get("ev_mm")
    ebitda = deal.get("ebitda_at_entry_mm")
    if ev is not None and ev <= 0:
        warnings.append(f"ev_mm {ev} is non-positive")
    if ebitda is not None and ebitda <= 0:
        warnings.append(f"ebitda_at_entry_mm {ebitda} is non-positive")
    if ev and ebitda and ebitda > 0:
        multiple = ev / ebitda
        if multiple < 3.0:
            warnings.append(f"implied EV/EBITDA {multiple:.1f}x unusually low (< 3x)")
        if multiple > 30.0:
            warnings.append(f"implied EV/EBITDA {multiple:.1f}x unusually high (> 30x)")

    moic = deal.get("realized_moic")
    irr = deal.get("realized_irr")
    hold = deal.get("hold_years")

    if moic is not None and moic < 0:
        warnings.append(f"realized_moic {moic:.2f}x is negative (total loss scenario — verify)")
    if moic is not None and moic > 10:
        warnings.append(f"realized_moic {moic:.2f}x is very high (> 10x) — verify")

    if irr is not None and irr < -1.0:
        warnings.append(f"realized_irr {irr:.1%} below -100% — verify decimal vs. percentage")
    if irr is not None and irr > 1.0:
        warnings.append(f"realized_irr {irr:.1%} above 100% — verify decimal vs. percentage")

    if hold is not None and hold < 0:
        warnings.append(f"hold_years {hold} is negative")
    if hold is not None and hold > 20:
        warnings.append(f"hold_years {hold} > 20 years — verify")

    pm = deal.get("payer_mix")
    if pm and isinstance(pm, dict):
        total = sum(pm.values())
        if abs(total - 1.0) > 0.05:
            warnings.append(f"payer_mix sums to {total:.2f}, expected ~1.0")
        for payer, share in pm.items():
            if share < 0 or share > 1:
                warnings.append(f"payer_mix[{payer}] = {share} outside [0,1]")

    return warnings
