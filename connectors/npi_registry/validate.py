"""NPI check-digit validation (Luhn over the ``80840`` prefix).

Per the NPPES check-digit specification, an NPI is a 10-digit number
whose last digit is a Luhn check digit computed over the first 9 digits
**prefixed with the ISO 7812 issuer id ``80840``** (the "United States,
health applications" prefix). This lets us reject transposition/typo
errors instantly, with no API round-trip — the cheap first gate before
any lookup.

No dependencies: pure arithmetic on the digit string.
"""
from __future__ import annotations

from typing import Dict

NPI_PREFIX = "80840"


def _luhn_check_digit(number_without_check: str) -> int:
    """Compute the Luhn check digit for a digit string (no check digit).

    Doubles every second digit counting from the right of the value
    *as if the check digit were already appended* (i.e. the rightmost
    supplied digit is doubled), then returns the digit that makes the
    running total a multiple of 10.
    """
    total = 0
    for i, ch in enumerate(reversed(number_without_check)):
        d = int(ch)
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return (10 - (total % 10)) % 10


def npi_check_digit(first_nine: str) -> int:
    """The correct 10th (check) digit for a 9-digit NPI body."""
    return _luhn_check_digit(NPI_PREFIX + first_nine)


def is_valid_npi(npi: str) -> bool:
    """True iff ``npi`` is 10 digits with a valid Luhn check digit."""
    return validate_npi(npi)["valid"]


def validate_npi(npi: str) -> Dict[str, object]:
    """Validate an NPI, returning ``{"npi", "valid", "reason"}``.

    ``reason`` is ``"ok"`` when valid, else a short human-readable cause
    (wrong length, non-numeric, or bad check digit) — the exact shape the
    ``/v1/validate/npi/{npi}`` route returns.
    """
    raw = "" if npi is None else str(npi).strip()
    if not raw.isdigit():
        return {"npi": raw, "valid": False, "reason": "npi must be 10 digits (non-numeric)"}
    if len(raw) != 10:
        return {"npi": raw, "valid": False,
                "reason": f"npi must be 10 digits (got {len(raw)})"}
    expected = npi_check_digit(raw[:9])
    if expected != int(raw[9]):
        return {"npi": raw, "valid": False,
                "reason": f"bad check digit (expected {expected}, got {raw[9]})"}
    return {"npi": raw, "valid": True, "reason": "ok"}
