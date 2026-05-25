"""Guide context for the Deal Library surfaces.

The in-app Guide must explain the new /deal-library pages accurately —
licensed (not public/scraped) source, sparse financials, sponsor-backed (not
PE-only) framing, and the disclosed-financial scope of the multiples view.
"""
import unittest

from rcm_mc.assistant.context.page_context_registry import PAGE_CONTEXT_REGISTRY
from rcm_mc.assistant.context.types import SourceConfidence


class TestDealLibraryGuideContext(unittest.TestCase):
    def _blob(self, route):
        ctx = PAGE_CONTEXT_REGISTRY.get(route)
        self.assertIsNotNone(ctx, f"{route} missing")
        self.assertEqual(ctx.source_confidence, SourceConfidence.DOCUMENTED, route)
        parts = [ctx.short_description, ctx.model_logic_summary]
        parts += list(ctx.data_sources) + list(ctx.interpretation_guidance) + list(ctx.limitations)
        return " ".join(parts).lower()

    def test_deal_library_states_licensed_and_sparse(self):
        b = self._blob("/deal-library")
        self.assertIn("licensed", b)
        self.assertIn("capital iq", b)
        self.assertTrue("not 0" in b or "never 0" in b or "blank" in b)
        self.assertIn("sponsor-backed", b)

    def test_sponsors_context(self):
        b = self._blob("/deal-library/sponsors")
        self.assertIn("sponsor", b)
        self.assertTrue("vc" in b or "accelerator" in b or "reit" in b)

    def test_comps_context_scopes_and_disclaims(self):
        b = self._blob("/deal-library/comps")
        self.assertIn("ev/revenue", b)
        self.assertTrue("excluded" in b or "never treated as 0" in b)
        self.assertTrue("not a prediction" in b or "directional" in b)


if __name__ == "__main__":
    unittest.main()
