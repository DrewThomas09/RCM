"""NPI validation.

A National Provider Identifier (NPI) is a 10-digit number whose final
digit is a Luhn check digit. CMS computes the Luhn over the NPI *prefixed*
with the constant ``80840`` (the ISO 7812 issuer identifier assigned to
CMS for health-care provider numbering). So the digit string actually run
through Luhn is the 15-digit ``80840`` + the 9-digit base + check digit.

Reference: NPI Final Rule, 45 CFR 162.406; CMS "NPI Check Digit" guidance.

This module is the single source of truth for "is this NPI well-formed?".
Invalid NPIs are *quarantined*, never silently dropped (see ``pipeline``).
"""
from __future__ import annotations

# ISO 7812 issuer prefix CMS folds into the NPI Luhn computation.
NPI_LUHN_PREFIX = "80840"


def luhn_check_digit(payload: str) -> int:
    """Return the Luhn check digit for ``payload`` (a digit string).

    Standard Luhn: double every second digit from the right, sum digit
    values, the check digit is what makes the running total a multiple
    of 10.
    """
    total = 0
    # We are computing the digit that will be *appended*, so the
    # rightmost payload digit is in a "doubled" position.
    double = True
    for ch in reversed(payload):
        d = ord(ch) - 48
        if double:
            d *= 2
            if d > 9:
                d -= 9
        total += d
        double = not double
    return (10 - (total % 10)) % 10


def is_valid_npi(npi: object) -> bool:
    """True iff ``npi`` is a 10-digit string with a valid Luhn check
    digit computed over the ``80840`` prefix."""
    if npi is None:
        return False
    s = str(npi).strip()
    if len(s) != 10 or not s.isdigit():
        return False
    base, check = s[:9], int(s[9])
    return luhn_check_digit(NPI_LUHN_PREFIX + base) == check


def make_valid_npi(base9: str) -> str:
    """Given a 9-digit base, return the full 10-digit NPI with the
    correct check digit. Used by the synthetic universe generator and
    by tests; never used on ingested data."""
    base9 = str(base9).strip().zfill(9)[:9]
    chk = luhn_check_digit(NPI_LUHN_PREFIX + base9)
    return f"{base9}{chk}"
