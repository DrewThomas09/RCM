"""X-Ray Guide/RAG source cards (Part 4).

The three design/interpretation cards must be on disk, indexed into the Guide
RAG corpus, and carry the standing honesty boundaries (peer deviation, not a
forecast/recommendation/market-share; risk indicators are not trained models).
"""
from __future__ import annotations

import pathlib
import unittest

from rcm_mc.assistant.rag.document_sources import iter_guide_documents

_RAG = pathlib.Path(__file__).resolve().parents[1] / "docs" / "rag_sources"
_CARDS = (
    "hcris_xray_design_and_interpretation.md",
    "xray_benchmark_visuals.md",
    "provider_xray_design_pattern.md",
)


class CardsTests(unittest.TestCase):
    def test_cards_on_disk(self):
        for c in _CARDS:
            self.assertTrue((_RAG / c).is_file(), f"missing {c}")

    def test_cards_indexed(self):
        titles = " ".join(str(getattr(d, "title", "")) for d in
                          iter_guide_documents()).lower()
        for needle in ("hcris x-ray: what it does", "x-ray benchmark visuals",
                       "cms provider x-ray design pattern"):
            self.assertIn(needle, titles, f"not indexed: {needle}")

    def test_cards_carry_honesty_boundaries(self):
        blob = "\n".join((_RAG / c).read_text(encoding="utf-8").lower()
                         for c in _CARDS)
        self.assertIn("not market share", blob)
        self.assertIn("peer deviation", blob)
        self.assertIn("never a forecast", blob)       # benchmark visuals card
        self.assertIn("not forecasts", blob)          # provider design card
        self.assertIn("hcris x-ray vs", blob)         # the differentiation Q

    def test_explains_peer_band_and_percentile(self):
        vis = (_RAG / "xray_benchmark_visuals.md").read_text(encoding="utf-8").lower()
        self.assertIn("p25 to p75", vis)
        self.assertIn("target diamond", vis)
        self.assertIn("n ≥ 5", vis) if "n ≥ 5" in vis else self.assertIn("n=5", vis.replace(" ", ""))


if __name__ == "__main__":
    unittest.main()
