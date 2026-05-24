"""Guard for the HCRIS X-Ray component-map doc (docs-only migration map).

Asserts the map exists with the contract-required sections and that the
critical honesty calls are recorded (public comps / cap-multiple EV are NOT
real; the Stroger preview is SAMPLE-ONLY). Reviewed before any code lands.
"""
from __future__ import annotations

import pathlib
import unittest

_DOC = (pathlib.Path(__file__).resolve().parent.parent / "docs"
        / "PEDESK_HCRIS_XRAY_COMPONENT_MAP.md")


class ComponentMapDocTests(unittest.TestCase):
    def setUp(self):
        self.t = _DOC.read_text()

    def test_doc_exists_with_required_sections(self):
        for marker in ("Selected variants", "Production route map",
                       "Section inventory", "Data-binding map", "Token map",
                       "Component map", "Implementation plan", "Guardrails",
                       "Tests to add"):
            self.assertIn(marker, self.t)

    def test_selected_variants_recorded(self):
        self.assertIn("B · Workstation", self.t)
        self.assertIn("A v2 · Headline", self.t)

    def test_honesty_calls_recorded(self):
        # Public comps + cap-multiple EV are not real; Stroger is sample-only.
        self.assertIn("SAMPLE-ONLY", self.t)
        self.assertIn("UNAVAILABLE", self.t)
        self.assertIn("ASSUMPTION", self.t)
        self.assertIn("Stroger", self.t)
        self.assertIn("public comp", self.t.lower())

    def test_no_raw_css_in_body_guardrail_present(self):
        self.assertIn("No raw CSS in the page body", self.t)


if __name__ == "__main__":
    unittest.main()
