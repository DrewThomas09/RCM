"""Regression guard for the diligence DQReport HTML renderer.

History: ``rcm_mc_diligence/dq/report.py::_section_html`` built the
optional message block with an f-string whose *expression part* contained
backslash escapes (``f"{('<div class=\"sub\"...')}"``). That is a hard
``SyntaxError`` on Python < 3.12 (PEP 701 only lifts the restriction in
3.12), so on every supported interpreter below 3.12 the *entire* diligence
layer failed to import — ``compileall`` flagged it but no test exercised
the module, so it shipped.

This test does two things on all supported versions (3.10+):
  1. imports the module (a syntax regression makes collection fail loudly);
  2. renders a report whose section carries a message, asserting the
     previously-broken optional message block is emitted.

The renderer is pure stdlib, so this needs none of the optional diligence
extras (duckdb / dbt / pyarrow).
"""
import unittest

from rcm_mc_diligence.dq.report import (
    DQReport,
    DQSectionStatus,
    DQSeverity,
    Section,
)


class TestDQReportRender(unittest.TestCase):
    def test_section_with_message_renders_block(self):
        report = DQReport()
        report.source_inventory = Section(
            status=DQSectionStatus.WARN,
            severity=DQSeverity.WARN,
            message="2 files dropped",
            rows=[],
        )
        out = report.render_html()
        # The optional message block — the exact markup that lived inside
        # the illegal f-string expression part — must render.
        self.assertIn(
            '<div class="sub" style="margin-bottom:8px;">2 files dropped</div>',
            out,
        )
        # Empty section rows still produce the "no rows" placeholder.
        self.assertIn("no rows", out)

    def test_section_without_message_omits_block(self):
        report = DQReport()  # defaults: empty message
        out = report.render_html()
        self.assertNotIn('style="margin-bottom:8px;"', out)


if __name__ == "__main__":
    unittest.main()
