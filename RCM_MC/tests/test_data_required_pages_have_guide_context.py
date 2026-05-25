"""Every DATA REQUIRED surface must have a DOCUMENTED Guide context that
explains what to upload and who to request it from — so the in-app Guide can
answer "why isn't this live yet and what do I provide?"."""
import unittest

from rcm_mc.diligence.surface_status import _DATA_REQUIRED
from rcm_mc.assistant.context.page_context_registry import PAGE_CONTEXT_REGISTRY


class DataRequiredGuideContextTests(unittest.TestCase):
    def test_every_data_required_route_is_documented(self):
        missing = []
        for route in sorted(_DATA_REQUIRED):
            ctx = PAGE_CONTEXT_REGISTRY.get(route)
            sc = getattr(getattr(ctx, "source_confidence", None), "name", "")
            if sc != "DOCUMENTED":
                missing.append(f"{route}: guide context is {sc or 'MISSING'}, not DOCUMENTED")
        self.assertEqual(missing, [], "DATA REQUIRED pages without a DOCUMENTED Guide context:\n"
                         + "\n".join(missing))

    def test_documented_context_explains_upload(self):
        for route in sorted(_DATA_REQUIRED):
            ctx = PAGE_CONTEXT_REGISTRY.get(route)
            blob = " ".join(list(getattr(ctx, "data_sources", []))
                            + list(getattr(ctx, "interpretation_guidance", []))).lower()
            self.assertIn("upload", blob, f"{route}: context doesn't say what to upload")


if __name__ == "__main__":
    unittest.main()
