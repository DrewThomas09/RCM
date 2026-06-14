"""Benford's-law screen for billed-amount integrity — stdlib + numpy.

A fast first-pass integrity check on a distribution of dollar amounts
(billed charges, paid amounts, claim lines). Naturally-occurring
financial figures that span several orders of magnitude follow
Benford's law: the leading digit is 1 about 30% of the time, falling
to ~4.6% for 9. Distributions that *don't* — because amounts were
fabricated, rounded, or clustered just under an authorization /
review threshold — deviate in a way this catches cheaply, before any
expensive claim-level work.

This is a screen, not proof: a failed test is a "look here" flag, not
an accusation. It belongs with the other first-pass guardrails in the
integrity gauntlet.

Method (the practitioner-standard pairing):
    * **Chi-square** goodness-of-fit (8 df for the first-digit test).
      The p-value uses a closed form for even degrees of freedom — the
      regularized upper incomplete gamma Q(k/2, x/2) collapses to a
      finite sum when k/2 is an integer, so no scipy.
    * **Mean Absolute Deviation (MAD)** with Nigrini's conformity
      thresholds. MAD is the primary verdict because chi-square is
      oversensitive at large n (every real dataset "fails" chi-square
      once n is big enough); MAD does not scale with n.

Scope: needs amounts spanning multiple orders of magnitude. Bounded
quantities (ages, percentages, capped copays) do not follow Benford
and will false-positive — ``advisory`` says so when the spread is too
narrow to trust the screen.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Sequence

import numpy as np

CITATION_KEY = "IN-BEN"
SOURCE_MODULE = "diligence.integrity.benford"

# Nigrini first-digit MAD conformity thresholds.
_MAD_CLOSE = 0.006
_MAD_ACCEPTABLE = 0.012
_MAD_MARGINAL = 0.015


class BenfordVerdict(str, Enum):
    CONFORMING = "CONFORMING"            # close / acceptable conformity
    MARGINAL = "MARGINAL"                # marginally acceptable
    NONCONFORMING = "NONCONFORMING"      # deviates — investigate
    INSUFFICIENT = "INSUFFICIENT"        # too few / too narrow to judge


def _first_digit_expected() -> List[float]:
    """Benford first-digit probabilities P(d) = log10(1 + 1/d), d=1..9."""
    return [math.log10(1 + 1 / d) for d in range(1, 10)]


def _chi2_sf_even_df(x: float, df: int) -> float:
    """Upper-tail chi-square probability for EVEN degrees of freedom.

    For even df, Q(df/2, x/2) is a finite sum:
        P(X > x) = e^{-x/2} Σ_{i=0}^{df/2 - 1} (x/2)^i / i!
    Exact and dependency-free. (First-digit test has df=8, even.)"""
    if x <= 0:
        return 1.0
    if df % 2 != 0:
        raise ValueError("closed form requires even df")
    half = x / 2.0
    terms = df // 2
    s = 0.0
    term = 1.0           # (half^0)/0!
    for i in range(terms):
        if i > 0:
            term *= half / i
        s += term
    return math.exp(-half) * s


def _leading_digit(v: float) -> int:
    """Leading significant digit of |v| (1..9); 0 if not extractable."""
    a = abs(float(v))
    if a == 0 or not math.isfinite(a):
        return 0
    # Scale into [1, 10).
    d = a / (10 ** math.floor(math.log10(a)))
    fd = int(d)
    return fd if 1 <= fd <= 9 else 0


def _first_two_digits(v: float) -> int:
    """First two significant digits of |v| (10..99); 0 if not extractable."""
    a = abs(float(v))
    if a == 0 or not math.isfinite(a):
        return 0
    scaled = a / (10 ** math.floor(math.log10(a)))   # [1, 10)
    ft = int(scaled * 10)                            # [10, 99]
    return ft if 10 <= ft <= 99 else 0


# Nigrini first-two-digits MAD conformity thresholds (tighter than
# first-digit because there are more bins).
_MAD2_ACCEPTABLE = 0.0018
_MAD2_MARGINAL = 0.0022


@dataclass
class BenfordResult:
    n: int
    observed_proportions: List[float]
    expected_proportions: List[float]
    observed_counts: List[int]
    chi_square: float
    chi_square_p: float
    mad: float                       # mean absolute deviation
    verdict: BenfordVerdict
    advisory: str = ""
    headline: str = ""
    spread_orders: float = 0.0       # orders of magnitude the data spans
    source_module: str = SOURCE_MODULE
    citation_key: str = CITATION_KEY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n": self.n,
            "observed_proportions": [round(p, 6) for p in self.observed_proportions],
            "expected_proportions": [round(p, 6) for p in self.expected_proportions],
            "observed_counts": list(self.observed_counts),
            "chi_square": round(self.chi_square, 4),
            "chi_square_p": round(self.chi_square_p, 6),
            "mad": round(self.mad, 6),
            "verdict": self.verdict.value,
            "advisory": self.advisory,
            "headline": self.headline,
            "spread_orders": round(self.spread_orders, 3),
            "source_module": self.source_module,
            "citation_key": self.citation_key,
        }


def benford_first_digit(
    values: Sequence[float], min_n: int = 100,
) -> BenfordResult:
    """First-digit Benford screen on a sequence of dollar amounts.

    Zeros, negatives (taken by magnitude), and non-finite values are
    filtered. Returns observed vs Benford-expected first-digit
    proportions, a chi-square goodness-of-fit (8 df) with its p-value,
    Nigrini's MAD with a conformity verdict, and an advisory when the
    sample is too small or too narrow in spread for the screen to be
    meaningful."""
    arr = np.asarray(values, dtype=float)
    arr = np.abs(arr[np.isfinite(arr)])
    arr = arr[arr > 0]
    n = int(arr.size)
    expected = _first_digit_expected()

    if n == 0:
        return BenfordResult(
            0, [0.0] * 9, expected, [0] * 9, 0.0, 1.0, 0.0,
            BenfordVerdict.INSUFFICIENT,
            advisory="No positive finite values to test.",
        )

    spread = float(math.log10(arr.max() / arr.min())) if arr.min() > 0 else 0.0
    digits = np.array([_leading_digit(v) for v in arr])
    digits = digits[digits > 0]
    counts = [int(np.sum(digits == d)) for d in range(1, 10)]
    total = sum(counts)
    obs_prop = [c / total for c in counts] if total else [0.0] * 9

    chi2 = 0.0
    for c, ep in zip(counts, expected):
        exp_count = ep * total
        if exp_count > 0:
            chi2 += (c - exp_count) ** 2 / exp_count
    chi2_p = _chi2_sf_even_df(chi2, 8)
    mad = sum(abs(o - e) for o, e in zip(obs_prop, expected)) / 9

    advisory = ""
    if n < min_n:
        verdict = BenfordVerdict.INSUFFICIENT
        advisory = (
            f"Only {n} values (< {min_n}); Benford screen is unreliable "
            f"at this sample size."
        )
    elif spread < 1.0:
        verdict = BenfordVerdict.INSUFFICIENT
        advisory = (
            f"Values span only {spread:.2f} orders of magnitude; Benford "
            f"assumes a wide multiplicative range — likely a bounded "
            f"quantity, not a Benford candidate."
        )
    else:
        verdict = _mad_verdict(mad)

    res = BenfordResult(
        n=n, observed_proportions=obs_prop, expected_proportions=expected,
        observed_counts=counts, chi_square=chi2, chi_square_p=chi2_p,
        mad=mad, verdict=verdict, advisory=advisory, spread_orders=spread,
    )
    res.headline = _headline(res)
    return res


def _mad_verdict(mad: float) -> BenfordVerdict:
    if mad <= _MAD_ACCEPTABLE:
        return BenfordVerdict.CONFORMING
    if mad <= _MAD_MARGINAL:
        return BenfordVerdict.MARGINAL
    return BenfordVerdict.NONCONFORMING


def _headline(res: BenfordResult) -> str:
    if res.verdict == BenfordVerdict.INSUFFICIENT:
        return f"Benford screen inconclusive: {res.advisory}"
    # Largest single-digit excess (where fabrication/thresholding shows).
    diffs = [
        (d + 1, res.observed_proportions[d] - res.expected_proportions[d])
        for d in range(9)
    ]
    worst = max(diffs, key=lambda t: abs(t[1]))
    over = "over" if worst[1] > 0 else "under"
    return (
        f"Benford first-digit {res.verdict.value} (MAD {res.mad:.4f}, "
        f"χ²={res.chi_square:.1f} p={res.chi_square_p:.3f}, n={res.n}). "
        f"Largest deviation: digit {worst[0]} {over}-represented by "
        f"{abs(worst[1]) * 100:.1f}pp."
    )


def benford_first_two_digits(
    values: Sequence[float], min_n: int = 300,
) -> BenfordResult:
    """First-two-digits Benford screen (digits 10–99) — the fraud-exam
    gold standard.

    The first-digit test is coarse: it cannot see manipulation that
    preserves the leading digit (rounding to ``$X9,900`` to stay under a
    ``$X0,000`` review threshold, padding by a flat percentage). The
    first-two-digits distribution has 90 bins and tighter Nigrini MAD
    cut-offs, so it catches threshold-hugging and round-number padding
    the first-digit test passes. Needs a larger sample (``min_n`` 300)
    because the bins are finer. Reuses :class:`BenfordResult`; the
    ``observed/expected_proportions`` lists hold the 90 two-digit bins
    and ``chi_square`` carries 88 df."""
    arr = np.asarray(values, dtype=float)
    arr = np.abs(arr[np.isfinite(arr)])
    arr = arr[arr > 0]
    n = int(arr.size)
    expected = [math.log10(1 + 1 / d) for d in range(10, 100)]

    if n == 0:
        return BenfordResult(
            0, [0.0] * 90, expected, [0] * 90, 0.0, 1.0, 0.0,
            BenfordVerdict.INSUFFICIENT,
            advisory="No positive finite values to test.",
        )

    spread = float(math.log10(arr.max() / arr.min())) if arr.min() > 0 else 0.0
    ft = np.array([_first_two_digits(v) for v in arr])
    ft = ft[ft > 0]
    counts = [int(np.sum(ft == d)) for d in range(10, 100)]
    total = sum(counts)
    obs_prop = [c / total for c in counts] if total else [0.0] * 90

    chi2 = 0.0
    for c, ep in zip(counts, expected):
        exp_count = ep * total
        if exp_count > 0:
            chi2 += (c - exp_count) ** 2 / exp_count
    chi2_p = _chi2_sf_even_df(chi2, 88)
    mad = sum(abs(o - e) for o, e in zip(obs_prop, expected)) / 90

    advisory = ""
    if n < min_n:
        verdict = BenfordVerdict.INSUFFICIENT
        advisory = (
            f"Only {n} values (< {min_n}); the first-two-digits test needs a "
            f"larger sample than first-digit."
        )
    elif spread < 1.0:
        verdict = BenfordVerdict.INSUFFICIENT
        advisory = (
            f"Values span only {spread:.2f} orders of magnitude — not a "
            f"Benford candidate."
        )
    elif mad <= _MAD2_ACCEPTABLE:
        verdict = BenfordVerdict.CONFORMING
    elif mad <= _MAD2_MARGINAL:
        verdict = BenfordVerdict.MARGINAL
    else:
        verdict = BenfordVerdict.NONCONFORMING

    res = BenfordResult(
        n=n, observed_proportions=obs_prop, expected_proportions=expected,
        observed_counts=counts, chi_square=chi2, chi_square_p=chi2_p,
        mad=mad, verdict=verdict, advisory=advisory, spread_orders=spread,
    )
    if verdict == BenfordVerdict.INSUFFICIENT:
        res.headline = f"Benford first-two-digits inconclusive: {advisory}"
    else:
        diffs = [
            (d + 10, obs_prop[d] - expected[d]) for d in range(90)
        ]
        worst = max(diffs, key=lambda t: abs(t[1]))
        over = "over" if worst[1] > 0 else "under"
        res.headline = (
            f"Benford first-two-digits {verdict.value} (MAD {mad:.4f}, "
            f"χ²={chi2:.1f} p={chi2_p:.3f}, n={n}). Largest deviation: "
            f"digits {worst[0]} {over}-represented by {abs(worst[1]) * 100:.2f}pp."
        )
    return res
