"""tests for the diligence workflow-handoff CTA.

PROMPTS.md Phase 3 / Prompt 39: every diligence module's success page
should end with a "Next: <module>" CTA that names the next step in
the flow. Verbs/labels live in the registered flow so per-page CTAs
update centrally.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._ui_kit import _DILIGENCE_FLOW, next_step_cta


class FlowDefinedAndOrdered(unittest.TestCase):

    def test_flow_starts_with_ingest(self) -> None:
        self.assertEqual(_DILIGENCE_FLOW[0]["key"], "ingest")

    def test_flow_ends_with_ic_packet(self) -> None:
        self.assertEqual(_DILIGENCE_FLOW[-1]["key"], "ic_packet")

    def test_keys_unique(self) -> None:
        keys = [step["key"] for step in _DILIGENCE_FLOW]
        self.assertEqual(len(keys), len(set(keys)))


class CTAGeneration(unittest.TestCase):

    def test_ingest_points_to_benchmarks(self) -> None:
        html = next_step_cta("ingest")
        self.assertIn("Next: Benchmark KPIs", html)
        self.assertIn('href="/diligence/benchmarks"', html)

    def test_root_cause_points_to_value(self) -> None:
        html = next_step_cta("root_cause")
        self.assertIn("Next: Build value-creation model", html)
        self.assertIn('href="/diligence/value"', html)

    def test_last_step_returns_empty_string(self) -> None:
        html = next_step_cta("ic_packet")
        self.assertEqual(html, "")

    def test_unrecognised_key_returns_empty(self) -> None:
        html = next_step_cta("nonsense")
        self.assertEqual(html, "")


class DealContextPropagation(unittest.TestCase):

    def test_deal_id_appended_to_next_href(self) -> None:
        html = next_step_cta("ingest", deal_id="aurora")
        self.assertIn(
            'href="/diligence/benchmarks?deal_id=aurora"',
            html,
        )


class CTAUsesPrimaryWeight(unittest.TestCase):

    def test_primary_button_class(self) -> None:
        html = next_step_cta("ingest")
        self.assertIn("btn-primary", html)


if __name__ == "__main__":
    unittest.main()
