"""Guide context for the Diligence pages reformed in the honesty stack.

PRs 4/5/8 changed the data-source story for Payer Stress, Cost Structure,
Debt Service and CMS APM. Their Guide context must state that story
accurately — real HCRIS where supported, honest degradation / illustrative
overlay where not — so the in-app assistant never reads a model as live.
"""
import unittest

from rcm_mc.assistant.context.page_context_registry import PAGE_CONTEXT_REGISTRY
from rcm_mc.assistant.context.types import SourceConfidence


class TestChangedDiligenceGuideContext(unittest.TestCase):
    def _ctx(self, route):
        ctx = PAGE_CONTEXT_REGISTRY.get(route)
        self.assertIsNotNone(ctx, f"{route} not in registry")
        # Must be a hand-written documented context, not a placeholder stub.
        self.assertEqual(ctx.source_confidence, SourceConfidence.DOCUMENTED, route)
        return ctx

    def _blob(self, ctx) -> str:
        parts = [ctx.short_description, ctx.model_logic_summary]
        parts += list(ctx.data_sources) + list(ctx.interpretation_guidance)
        return " ".join(parts).lower()

    def test_payer_stress_real_hcris_and_degradation(self):
        blob = self._blob(self._ctx("/payer-stress"))
        self.assertIn("hcris", blob)
        self.assertIn("ccn", blob)
        self.assertTrue("illustrative" in blob or "default" in blob)

    def test_cost_structure_real_opex_illustrative_split(self):
        blob = self._blob(self._ctx("/cost-structure"))
        self.assertIn("hcris", blob)
        self.assertIn("illustrative", blob)

    def test_debt_service_proxy_and_data_required(self):
        blob = self._blob(self._ctx("/debt-service"))
        self.assertIn("proxy", blob)
        self.assertIn("data required", blob)

    def test_cms_apm_real_cmmi_illustrative_overlay(self):
        blob = self._blob(self._ctx("/cms-apm"))
        self.assertIn("cmmi", blob)
        self.assertIn("illustrative", blob)


if __name__ == "__main__":
    unittest.main()
