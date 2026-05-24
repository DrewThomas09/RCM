"""CMS Provider X-Ray — RAG source cards are indexed and honest.

The four source cards (resolver, benchmarking, vertical metric map, investable
interpretation) must be discoverable in the Guide RAG corpus and must carry
the standing honesty boundaries (not market share, not an investment
recommendation, n>=5 z-score guard, CMS-public-only).
"""
from __future__ import annotations

import pathlib
import unittest

from rcm_mc.assistant.rag.document_sources import iter_guide_documents

_RAG = pathlib.Path(__file__).resolve().parents[1] / "docs" / "rag_sources"
_CARDS = (
    "provider_xray.md",
    "provider_benchmarking.md",
    "cms_vertical_metric_map.md",
    "investable_xray_interpretation.md",
)


class CardsExistTests(unittest.TestCase):
    def test_all_four_cards_on_disk(self):
        for c in _CARDS:
            self.assertTrue((_RAG / c).is_file(), f"missing {c}")


class CardsIndexedTests(unittest.TestCase):
    def setUp(self):
        self.titles = " ".join(
            str(getattr(d, "title", "") or getattr(d, "name", ""))
            for d in iter_guide_documents()
        ).lower()

    def test_xray_cards_indexed(self):
        for needle in ("how it resolves a provider", "peer sets, percentiles",
                       "vertical metric map", "investable evidence"):
            self.assertIn(needle, self.titles, f"not indexed: {needle}")


class HonestyTests(unittest.TestCase):
    def test_cards_carry_boundaries(self):
        blob = "\n".join((_RAG / c).read_text(encoding="utf-8").lower()
                         for c in _CARDS)
        self.assertIn("not market share", blob)
        self.assertIn("not an investment", blob.replace("\n", " ") or blob)
        self.assertIn("peer deviation", blob)
        self.assertIn("n ≥ 5", blob)            # z-score guard
        self.assertIn("leading zeroes", blob)        # identifier discipline
        self.assertIn("never guesses", blob)         # ambiguity discipline


if __name__ == "__main__":
    unittest.main()
