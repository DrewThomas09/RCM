"""Tests for ``rcm_mc/reports/_report_sections.py`` — static HTML blocks
assembled into the partner-facing diligence packet.

The module exports six large HTML/JS string constants:

  * ``RISK_REGISTER_HTML`` — risk inventory table
  * ``MODEL_LIMITATIONS_HTML`` — what the model does NOT capture
  * ``KEY_ASSUMPTIONS_HTML`` — assumption table with sensitivity
  * ``GLOSSARY_HTML`` — plain-English glossary of RCM terms
  * ``SCENARIO_EXPLORER_JS`` — interactive scenario explorer widget
  * ``BACK_TO_TOP_HTML`` — sticky footer return-to-top button

Module docstring notes these are 'byte-for-byte identical to the
prior inlined versions' — silent edits would change the partner
brief without anyone noticing. These tests lock the structural
contract (TOC anchor IDs, expected row counts, glossary length,
embedded script tags) before any tweak ships.
"""
from __future__ import annotations

import unittest

from rcm_mc.reports._report_sections import (
    BACK_TO_TOP_HTML,
    GLOSSARY_HTML,
    KEY_ASSUMPTIONS_HTML,
    MODEL_LIMITATIONS_HTML,
    RISK_REGISTER_HTML,
    SCENARIO_EXPLORER_JS,
)


class ConstantsArePresentTests(unittest.TestCase):
    """Every constant is a non-empty string. Catches a refactor that
    silently drops one of the boilerplate blocks."""

    def test_risk_register_is_non_empty_string(self):
        self.assertIsInstance(RISK_REGISTER_HTML, str)
        self.assertGreater(len(RISK_REGISTER_HTML), 200)

    def test_model_limitations_is_non_empty_string(self):
        self.assertIsInstance(MODEL_LIMITATIONS_HTML, str)
        self.assertGreater(len(MODEL_LIMITATIONS_HTML), 200)

    def test_key_assumptions_is_non_empty_string(self):
        self.assertIsInstance(KEY_ASSUMPTIONS_HTML, str)
        self.assertGreater(len(KEY_ASSUMPTIONS_HTML), 200)

    def test_glossary_is_non_empty_string(self):
        self.assertIsInstance(GLOSSARY_HTML, str)
        self.assertGreater(len(GLOSSARY_HTML), 500)

    def test_scenario_explorer_js_is_non_empty_string(self):
        self.assertIsInstance(SCENARIO_EXPLORER_JS, str)
        self.assertGreater(len(SCENARIO_EXPLORER_JS), 200)

    def test_back_to_top_is_non_empty_string(self):
        self.assertIsInstance(BACK_TO_TOP_HTML, str)
        self.assertGreater(len(BACK_TO_TOP_HTML), 10)


class TocAnchorIdsTests(unittest.TestCase):
    """The packet table-of-contents links to these IDs. If any goes
    missing the partner clicks the TOC item and lands on a blank
    page-top instead of the section."""

    def test_risk_register_has_anchor(self):
        # TOC link: <a href='#sec-risks'>Risk Register</a>
        self.assertIn('id="sec-risks"', RISK_REGISTER_HTML)

    def test_glossary_has_anchor(self):
        self.assertIn('id="glossary"', GLOSSARY_HTML)

    def test_model_limitations_has_h2(self):
        # MODEL_LIMITATIONS opens with <h2 id=...> — lock the heading.
        self.assertIn("<h2", MODEL_LIMITATIONS_HTML)


class RiskRegisterStructureTests(unittest.TestCase):

    def test_renders_a_table(self):
        self.assertIn("<table>", RISK_REGISTER_HTML)
        self.assertIn("</table>", RISK_REGISTER_HTML)

    def test_has_expected_columns(self):
        # 5 header columns: Risk / Probability / Impact / Risk Score / Mitigation
        for header in ("Risk", "Probability", "Impact",
                        "Risk Score", "Mitigation"):
            self.assertIn(f"<th>{header}</th>", RISK_REGISTER_HTML)

    def test_risk_register_uses_severity_dots(self):
        # Each risk row has a risk-dot span (low/med/high) per cell.
        self.assertGreater(RISK_REGISTER_HTML.count("risk-dot"), 5)

    def test_risk_register_uses_score_categories(self):
        # 'Critical' / 'Elevated' / 'Moderate' badges colored.
        self.assertIn("risk-score", RISK_REGISTER_HTML)


class KeyAssumptionsStructureTests(unittest.TestCase):

    def test_renders_a_table(self):
        self.assertIn("<table>", KEY_ASSUMPTIONS_HTML)
        self.assertIn("</table>", KEY_ASSUMPTIONS_HTML)

    def test_lists_the_seven_partner_visible_assumptions(self):
        # Each assumption row mentions its driver — partner brief
        # depends on all seven appearing.
        expected = [
            "Payer mix",
            "Initial Denial Rates",  # IDR
            "Final Write-Off Rates",  # FWR
            "Appeal success rates",
            "Days in A/R",
            "WACC",                  # cost of capital
            "EBITDA multiple",
        ]
        for term in expected:
            self.assertIn(term, KEY_ASSUMPTIONS_HTML,
                          f"missing assumption: {term}")

    def test_each_assumption_has_sensitivity_label(self):
        # Sensitivity column carries one of High/Very High/Medium/Low
        # tone tokens for every row.
        sensitivities = ("High", "Very High", "Medium", "Low")
        for level in sensitivities:
            self.assertIn(level, KEY_ASSUMPTIONS_HTML)


class GlossaryStructureTests(unittest.TestCase):

    def test_uses_definition_list(self):
        self.assertIn("<dl class=\"glossary\">", GLOSSARY_HTML)

    def test_contains_at_least_15_terms(self):
        # Glossary is the partner-facing definition reference. We
        # don't lock the exact count (would over-fit), but require a
        # minimum so an accidental deletion is caught.
        n_terms = GLOSSARY_HTML.count("<dt>")
        self.assertGreaterEqual(
            n_terms, 15,
            f"glossary has {n_terms} terms, expected ≥15",
        )

    def test_balanced_dt_dd_pairs(self):
        # Every term has a definition — count must match.
        self.assertEqual(
            GLOSSARY_HTML.count("<dt>"),
            GLOSSARY_HTML.count("<dd>"),
        )

    def test_canonical_terms_defined(self):
        # The partner brief expects these to be searchable in the
        # glossary — locking the set of must-have terms.
        for term in (
            "A/R (Accounts Receivable)",
            "EBITDA",
            "Monte Carlo",
            "P10 / P90",  # locked at the actual glossary label
        ):
            self.assertIn(term, GLOSSARY_HTML,
                          f"glossary missing canonical term: {term}")


class ScenarioExplorerJsTests(unittest.TestCase):

    def test_starts_with_script_tag(self):
        self.assertTrue(SCENARIO_EXPLORER_JS.lstrip().startswith("<script>"))

    def test_ends_with_script_close(self):
        self.assertIn("</script>", SCENARIO_EXPLORER_JS)

    def test_no_unmatched_script_tags(self):
        # Script open/close count balanced (catches accidental tag-strip).
        self.assertEqual(
            SCENARIO_EXPLORER_JS.count("<script>"),
            SCENARIO_EXPLORER_JS.count("</script>"),
        )

    def test_defines_interactive_handlers(self):
        # Loose smoke — the JS must reference at least one event
        # handler so the widget isn't dead on the page.
        joined = SCENARIO_EXPLORER_JS.lower()
        self.assertTrue(
            "function" in joined or "addeventlistener" in joined,
            "scenario explorer JS has no JS event/function code",
        )


class BackToTopTests(unittest.TestCase):

    def test_renders_anchor_to_exec_summary(self):
        # Back-to-top jumps to the exec summary (the report intro) —
        # locked because the partner brief depends on this anchor ID.
        self.assertIn('href="#exec-summary"', BACK_TO_TOP_HTML)
        self.assertIn('id="back-to-top"', BACK_TO_TOP_HTML)

    def test_has_scroll_threshold_logic(self):
        # JS shows the button only after scrolling past 400px so it
        # doesn't clutter the top of the doc.
        self.assertIn("scrollY>400", BACK_TO_TOP_HTML)

    def test_styles_position_fixed(self):
        # Fixed-position so the button stays in the bottom-right.
        self.assertIn("position:fixed", BACK_TO_TOP_HTML)


class HtmlValidityTests(unittest.TestCase):
    """Light HTML-sanity checks: no obviously-broken tags. Not a
    full validator — just catches tag-mismatch and unclosed elements
    that would corrupt the rendered packet."""

    def test_risk_register_table_tags_balanced(self):
        # Each opening table tag has a matching close.
        for tag in ("table", "tr", "td", "th"):
            opens = RISK_REGISTER_HTML.count(f"<{tag}>")
            closes = RISK_REGISTER_HTML.count(f"</{tag}>")
            # td/th tags can have attributes (so <td class='num'>) —
            # check sum of bare + attributed forms.
            opens_attr = RISK_REGISTER_HTML.count(f"<{tag} ")
            self.assertEqual(
                opens + opens_attr, closes,
                f"<{tag}> tags unbalanced in RISK_REGISTER_HTML "
                f"(bare:{opens} attr:{opens_attr} close:{closes})",
            )

    def test_glossary_dt_dd_tags_balanced(self):
        for tag in ("dt", "dd"):
            opens = GLOSSARY_HTML.count(f"<{tag}>")
            opens_attr = GLOSSARY_HTML.count(f"<{tag} ")
            closes = GLOSSARY_HTML.count(f"</{tag}>")
            self.assertEqual(
                opens + opens_attr, closes,
                f"<{tag}> unbalanced in GLOSSARY_HTML",
            )


if __name__ == "__main__":
    unittest.main()
