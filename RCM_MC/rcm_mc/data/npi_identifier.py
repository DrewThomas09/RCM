"""Is this even an NPI? — the check digit, offline.

Why this exists
---------------
The crosswalk accepted any ten digits. That made two very different
answers look identical: "this NPI is not in our data" and "this is not
an NPI". The first is a coverage gap a partner should push on; the
second is a typo they should fix, and telling them apart takes no
network call at all.

Every NPI carries a Luhn check digit. CMS's Final Rule for the Standard
Unique Health Identifier for Health Care Providers (69 FR 3434)
specifies the calculation: prefix the nine-digit identifier with
``80840`` — the ISO 7812 issuer identifier assigned to US health
applications — and the tenth digit is the Luhn check digit over that
string. So validating an NPI means running Luhn over
``"80840" + npi``, all fifteen digits including the check digit itself.

The 80840 prefix is the part that is easy to get wrong and impossible
to notice: Luhn over the bare ten digits passes for a different set of
numbers, so an implementation that skips the prefix rejects real NPIs
and accepts fake ones, and does it quietly.

Borrowed from the rOpenSci ``npi`` package's ``npi_is_valid()``, which
does exactly this. The doubling rule is written out here rather than
pulled from a dependency — it is nine lines, and this package adds no
runtime dependencies.

What it does not tell you
-------------------------
Nothing about whether the NPI was ever issued, whether it is active, or
who holds it. A well-formed NPI is a number that *could* have been
assigned. :mod:`master_provider_file` answers the rest.
"""
from __future__ import annotations

import re
from typing import Any, Iterable, List

#: ISO 7812 issuer identifier for US health applications. Prepended
#: before the Luhn calculation, per 69 FR 3434.
NPI_PREFIX = "80840"

#: An NPI is ten digits and cannot start with zero — CMS issues from
#: the 1xxxxxxxxx and 2xxxxxxxxx ranges.
NPI_RE = re.compile(r"^[12][0-9]{9}$")


def luhn_check_digit(digits: str) -> int:
    """The Luhn check digit for a string of digits with none appended.

    Doubling runs right-to-left over the payload; a doubled value above
    nine has nine subtracted, which is the same as summing its two
    decimal digits.
    """
    total = 0
    for index, char in enumerate(reversed(digits)):
        value = int(char)
        if index % 2 == 0:
            value *= 2
            if value > 9:
                value -= 9
        total += value
    return (10 - total % 10) % 10


def is_valid_npi(value: Any) -> bool:
    """True when ``value`` is a well-formed NPI with a correct check digit.

    Rejects anything that is not exactly ten digits starting 1 or 2,
    without raising — a crosswalk is handed junk constantly and an
    exception is the wrong answer to "is this an NPI".
    """
    text = str(value or "").strip()
    if not NPI_RE.match(text):
        return False
    return luhn_check_digit(NPI_PREFIX + text[:9]) == int(text[9])


def npi_check_digit(nine_digits: Any) -> str:
    """The check digit CMS would assign to a nine-digit base.

    Exposed because it is the only way to build a *valid* fake NPI for a
    fixture. Tests that hard-code ten arbitrary digits are testing the
    validator's rejection path by accident.
    """
    text = str(nine_digits or "").strip()
    if not re.match(r"^[12][0-9]{8}$", text):
        raise ValueError(
            f"expected nine digits starting 1 or 2, got {text!r}")
    return str(luhn_check_digit(NPI_PREFIX + text))


def clean_npi(value: Any) -> str:
    """Strip a pasted NPI to its digits, or return ``""``.

    People paste NPIs out of spreadsheets and PDFs with spaces, hyphens
    and a stray apostrophe Excel added to stop it becoming a float.
    Salvaging those is worth doing; salvaging a number that then fails
    its check digit is not, so the result is validated before it is
    returned.
    """
    digits = "".join(c for c in str(value or "") if c.isdigit())
    return digits if is_valid_npi(digits) else ""


def invalid_npis(values: Iterable[Any]) -> List[str]:
    """Every value in ``values`` that is not a well-formed NPI.

    The reason this returns the offenders rather than a count: a caller
    handed a roster of 4,000 NPIs needs to know *which* eleven are
    malformed, and a number tells them only that they have a problem.
    """
    return [str(v) for v in values if not is_valid_npi(v)]
