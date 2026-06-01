"""Cross-helper invariant test for the chartis primitive layer.

Most ``ck_*`` value-driven helpers share a contract: when handed
``None`` or a non-numeric value where a number is expected, they
return ``""`` (the caller can drop the cell) rather than crashing
or rendering noise. This file walks every helper that lives by
that contract and verifies it in one place — catching future
additions that forget the fallback before they ship.

Two helpers explicitly OPT OUT of the empty-string contract because
their partner-facing semantic requires a visible 'unknown' cell:

  * ``ck_band_dot`` — neutral-gray dot for unknown bands so the
    column doesn't appear broken
  * ``ck_data_freshness_pill`` — neutral-gray 'Never updated' pill
    so partner sees 'unknown', not 'invisible'

Those opt-outs are explicitly asserted here too, so the contract is
documented + enforced both ways.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui import _chartis_kit as ck


# ---------------------------------------------------------------------------
# Helpers that MUST return "" on None / NaN / non-numeric value inputs
# ---------------------------------------------------------------------------


# Each entry is (helper_name, kwargs_to_call_with). The first positional
# arg is replaced with the test sentinel; remaining kwargs supply
# whatever other required arguments the helper needs.
EMPTY_FALLBACK_HELPERS = [
    # ---- recently-shipped primitives (this session) ----
    ("ck_growth_arrow",       {"prior": 100}),
    ("ck_threshold_gauge",    {"warning_threshold": 1.5,
                               "breach_threshold": 1.2}),
    ("ck_micro_ranking_strip", {"cohort_size": 100}),
    ("ck_signal_chip",        {}),
    ("ck_progress_dot_track", {"total": 5}),
    # ---- design-loop foundation siblings ----
    ("ck_spread_strip",       {"benchmark_value": 100}),
    ("ck_distribution_strip", {"target_value": 50}),
    ("ck_trajectory_strip",   {}),
    ("ck_payer_mix_microbar", {}),
]


class EmptyOnNoneFirstArgTests(unittest.TestCase):
    """The first positional value-driven arg → None must return ''."""

    def test_each_helper_returns_empty_on_none(self):
        for name, kwargs in EMPTY_FALLBACK_HELPERS:
            with self.subTest(helper=name):
                fn = getattr(ck, name)
                # The first positional is the value-like arg by convention.
                result = fn(None, **kwargs)
                self.assertEqual(
                    result, "",
                    f"{name}(None, **{kwargs}) → expected '' but got "
                    f"{result!r}",
                )


class EmptyOnNonNumericTests(unittest.TestCase):
    """Non-numeric strings (e.g. accidental 'N/A' passed in) should
    also return '' on the value-like first arg, for every helper that
    needs a numeric."""

    NUMERIC_FALLBACK_HELPERS = [
        ("ck_growth_arrow",        {"prior": 100}),
        ("ck_threshold_gauge",     {"warning_threshold": 1.5,
                                    "breach_threshold": 1.2}),
        ("ck_micro_ranking_strip", {"cohort_size": 100}),
        ("ck_progress_dot_track",  {"total": 5}),
        ("ck_spread_strip",        {"benchmark_value": 100}),
    ]

    def test_each_numeric_helper_returns_empty_on_junk_string(self):
        for name, kwargs in self.NUMERIC_FALLBACK_HELPERS:
            with self.subTest(helper=name):
                fn = getattr(ck, name)
                result = fn("junk", **kwargs)
                self.assertEqual(
                    result, "",
                    f"{name}('junk', **{kwargs}) → expected '' but got "
                    f"{result!r}",
                )


class EmptyOnNaNAndInfTests(unittest.TestCase):
    """NaN / Inf inputs should NOT render an arrow/marker — silent ''."""

    NAN_HELPERS = [
        ("ck_growth_arrow",     {"prior": 100}),
        ("ck_threshold_gauge",  {"warning_threshold": 1.5,
                                 "breach_threshold": 1.2}),
        ("ck_spread_strip",     {"benchmark_value": 100}),
    ]

    def test_nan_first_arg_returns_empty(self):
        for name, kwargs in self.NAN_HELPERS:
            with self.subTest(helper=name):
                fn = getattr(ck, name)
                result = fn(float("nan"), **kwargs)
                self.assertEqual(
                    result, "",
                    f"{name}(nan, **{kwargs}) → expected ''",
                )

    def test_inf_first_arg_returns_empty(self):
        for name, kwargs in self.NAN_HELPERS:
            with self.subTest(helper=name):
                fn = getattr(ck, name)
                result = fn(float("inf"), **kwargs)
                self.assertEqual(
                    result, "",
                    f"{name}(inf, **{kwargs}) → expected ''",
                )


# ---------------------------------------------------------------------------
# Helpers that DELIBERATELY opt out of the empty-string contract
# ---------------------------------------------------------------------------


class OptOutHelpersStillRenderTests(unittest.TestCase):
    """Two helpers explicitly render an 'unknown' cell instead of an
    empty string. Locking the opt-out so a future refactor can't
    silently flip them to empty-fallback and leave partner cells
    looking broken."""

    def test_ck_band_dot_renders_gray_on_none(self):
        out = ck.ck_band_dot(None)
        self.assertNotEqual(out, "")
        # Neutral gray fallback color appears.
        self.assertIn("#a8a8a8", out)

    def test_ck_band_dot_renders_gray_on_empty(self):
        out = ck.ck_band_dot("")
        self.assertNotEqual(out, "")
        self.assertIn("#a8a8a8", out)

    def test_ck_data_freshness_pill_renders_unknown_on_none(self):
        out = ck.ck_data_freshness_pill(None)
        self.assertNotEqual(out, "")
        self.assertIn("ck-freshness-none", out)
        self.assertIn("Never updated", out)

    def test_ck_data_freshness_pill_renders_unknown_on_nan(self):
        out = ck.ck_data_freshness_pill(float("nan"))
        self.assertIn("ck-freshness-none", out)


# ---------------------------------------------------------------------------
# Helpers that MUST handle empty containers without crashing
# ---------------------------------------------------------------------------


class EmptyContainerHelpersTests(unittest.TestCase):
    """Helpers that take a sequence-like first arg should treat an
    empty/None container as 'no signal' and return ''."""

    SEQUENCE_HELPERS = [
        ("ck_distribution_strip", {"target_value": 50}),
        ("ck_trajectory_strip",   {}),
        ("ck_payer_mix_microbar", {}),
    ]

    def test_empty_list_returns_empty(self):
        for name, kwargs in self.SEQUENCE_HELPERS:
            with self.subTest(helper=name):
                fn = getattr(ck, name)
                result = fn([], **kwargs)
                self.assertEqual(
                    result, "",
                    f"{name}([], **{kwargs}) → expected ''",
                )

    def test_none_returns_empty(self):
        for name, kwargs in self.SEQUENCE_HELPERS:
            with self.subTest(helper=name):
                fn = getattr(ck, name)
                result = fn(None, **kwargs)
                self.assertEqual(result, "")


# ---------------------------------------------------------------------------
# Smoke: every shipped primitive returns a non-empty render on good input
# ---------------------------------------------------------------------------


class HappyPathSmokeTests(unittest.TestCase):
    """Quick sanity that the helpers DO render something when handed
    valid input — pairs with the empty-fallback tests to detect a
    regression where a helper starts returning '' for every input."""

    def test_each_helper_renders_on_good_input(self):
        cases = [
            ("ck_growth_arrow",        (125, 100), {}),
            ("ck_threshold_gauge",     (2.0,),
             {"warning_threshold": 1.5, "breach_threshold": 1.2}),
            ("ck_micro_ranking_strip", (10, 100), {}),
            ("ck_signal_chip",         ("Live",), {}),
            ("ck_progress_dot_track",  (3, 5), {}),
            ("ck_spread_strip",        (120, 100), {}),
            ("ck_band_dot",            ("A",), {}),
            ("ck_data_freshness_pill", (3600,), {}),
        ]
        for name, args, kwargs in cases:
            with self.subTest(helper=name):
                fn = getattr(ck, name)
                out = fn(*args, **kwargs)
                self.assertNotEqual(
                    out, "",
                    f"{name}{args} {kwargs} should render non-empty",
                )
                self.assertIsInstance(out, str)


if __name__ == "__main__":
    unittest.main()
