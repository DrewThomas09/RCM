"""The NPI check digit — validated against real numbers, not a fixture.

The algorithm has one detail that is easy to get wrong and impossible to
notice: the ``80840`` prefix. Luhn over the bare ten digits also
"validates" numbers, just a different set of them, so an implementation
that drops the prefix rejects real NPIs and accepts fake ones silently.

The only test that catches that is the one below that runs every NPI in
the bundled roster through it. 20,401 real CMS-issued numbers either all
pass or the prefix is wrong.
"""
from __future__ import annotations

import unittest

from rcm_mc.data.npi_identifier import (
    NPI_PREFIX, clean_npi, invalid_npis, is_valid_npi, luhn_check_digit,
    npi_check_digit,
)


class RealNpiTests(unittest.TestCase):
    """The prefix is only provable against numbers CMS actually issued."""

    @classmethod
    def setUpClass(cls) -> None:
        from rcm_mc.data.npi_registry import assign_npi_registry

        cls.npis = [str(n) for n in assign_npi_registry()["npi"]]

    def test_every_real_npi_passes(self) -> None:
        self.assertGreater(len(self.npis), 20_000)
        self.assertEqual(invalid_npis(self.npis), [])

    def test_mutating_any_digit_fails(self) -> None:
        """A check digit that accepts a typo is not a check digit."""
        for npi in self.npis[:50]:
            for position in range(10):
                original = int(npi[position])
                mutated = npi[:position] + str((original + 1) % 10) + npi[position + 1:]
                if mutated == npi:
                    continue
                with self.subTest(npi=npi, position=position):
                    self.assertFalse(is_valid_npi(mutated))

    def test_transposing_adjacent_digits_usually_fails(self) -> None:
        """Luhn's whole point is catching transpositions. It cannot catch
        every one — 09 and 90 double to the same sum — so this asserts
        the rate, not perfection."""
        caught = considered = 0
        for npi in self.npis[:200]:
            for i in range(9):
                if npi[i] == npi[i + 1]:
                    continue
                swapped = npi[:i] + npi[i + 1] + npi[i] + npi[i + 2:]
                considered += 1
                caught += not is_valid_npi(swapped)
        self.assertGreater(considered, 500)
        self.assertGreater(caught / considered, 0.85)


class AlgorithmTests(unittest.TestCase):
    def test_the_prefix_is_the_documented_one(self) -> None:
        self.assertEqual(NPI_PREFIX, "80840")

    def test_dropping_the_prefix_would_change_the_answer(self) -> None:
        """Pinned so nobody 'simplifies' the prefix away: without it the
        validator is a different function that happens to also return
        booleans."""
        npi = "1316943566"
        self.assertTrue(is_valid_npi(npi))
        self.assertNotEqual(luhn_check_digit(npi[:9]),
                            luhn_check_digit(NPI_PREFIX + npi[:9]))

    def test_check_digit_round_trips(self) -> None:
        for base in ("131694356", "128577347", "114422319"):
            with self.subTest(base=base):
                self.assertTrue(is_valid_npi(base + npi_check_digit(base)))

    def test_a_bad_base_raises_rather_than_guessing(self) -> None:
        for junk in ("", "12345", "931694356", "abcdefghi"):
            with self.subTest(junk=junk):
                with self.assertRaises(ValueError):
                    npi_check_digit(junk)


class ShapeTests(unittest.TestCase):
    def test_junk_is_rejected_without_raising(self) -> None:
        """A crosswalk is handed junk constantly; an exception is the
        wrong answer to "is this an NPI"."""
        for junk in ("", None, "   ", "abc", "12345", "12345678901",
                     "0316943566", "3316943566"):
            with self.subTest(junk=junk):
                self.assertFalse(is_valid_npi(junk))

    def test_npis_start_one_or_two(self) -> None:
        """CMS issues from the 1xxxxxxxxx and 2xxxxxxxxx ranges. A
        Luhn-correct number outside them was never an NPI."""
        self.assertFalse(is_valid_npi("0000000000"))
        self.assertFalse(is_valid_npi("9999999995"))

    def test_clean_salvages_a_pasted_npi(self) -> None:
        """Excel adds apostrophes, PDFs add spaces, people add hyphens."""
        for messy in (" 1316943566 ", "13-1694-3566", "'1316943566",
                      "1316 9435 66", "NPI: 1316943566"):
            with self.subTest(messy=messy):
                self.assertEqual(clean_npi(messy), "1316943566")

    def test_clean_refuses_to_salvage_a_wrong_number(self) -> None:
        """Stripping punctuation off a number that then fails its check
        digit produces a confident wrong answer."""
        self.assertEqual(clean_npi("13-1694-3567"), "")

    def test_invalid_npis_names_the_offenders(self) -> None:
        """A roster of 4,000 with eleven bad ones needs the eleven, not
        the number eleven."""
        roster = ["1316943566", "1316943567", "abc", "1285773473"]
        self.assertEqual(invalid_npis(roster), ["1316943567", "abc"])


if __name__ == "__main__":
    unittest.main()
