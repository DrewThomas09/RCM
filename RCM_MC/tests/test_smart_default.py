"""tests for ``smart_default`` (P86)."""
from __future__ import annotations

import unittest

from rcm_mc.ui._ui_kit import smart_default


class PriorityOrder(unittest.TestCase):
    """last_submission > corpus_median > sector default > fallback."""

    def test_last_submission_wins(self) -> None:
        v = smart_default(
            "ebitda_margin",
            sector="ASC",
            last_submission=0.40,
            corpus_median=0.30,
            fallback=0.10,
        )
        self.assertEqual(v, 0.40)

    def test_corpus_median_when_no_last(self) -> None:
        v = smart_default(
            "ebitda_margin",
            sector="ASC",
            corpus_median=0.30,
            fallback=0.10,
        )
        self.assertEqual(v, 0.30)

    def test_sector_default_when_no_corpus(self) -> None:
        v = smart_default(
            "ebitda_margin",
            sector="ASC",
            fallback=0.10,
        )
        self.assertAlmostEqual(v, 0.32, places=2)

    def test_fallback_when_no_sector_match(self) -> None:
        v = smart_default(
            "ebitda_margin",
            sector="UnknownSector",
            fallback=0.10,
        )
        self.assertEqual(v, 0.10)

    def test_none_when_no_inputs(self) -> None:
        self.assertIsNone(smart_default("anything"))


class SectorNormalisation(unittest.TestCase):

    def test_case_insensitive(self) -> None:
        v = smart_default("ebitda_margin", sector="asc")
        v2 = smart_default("ebitda_margin", sector="ASC")
        self.assertEqual(v, v2)

    def test_spaces_and_dashes_normalised(self) -> None:
        # "Behavioral Health", "behavioral-health", "Behavioral health"
        # all map to the same key.
        for s in ("Behavioral Health", "behavioral-health",
                  "BEHAVIORAL HEALTH"):
            with self.subTest(sector=s):
                self.assertAlmostEqual(
                    smart_default("ebitda_margin", sector=s),
                    0.18, places=2,
                )


class FieldsCovered(unittest.TestCase):

    def test_all_three_sectors_have_basic_fields(self) -> None:
        for sector in ("ASC", "Hospital", "Behavioral Health"):
            for field in ("ebitda_margin", "growth_rate", "exit_multiple"):
                with self.subTest(sector=sector, field=field):
                    self.assertIsNotNone(
                        smart_default(field, sector=sector),
                    )


if __name__ == "__main__":
    unittest.main()
