"""Tests for the read-only PEdesk Guide prompt builder + answer cleaner."""
from __future__ import annotations

import unittest

from rcm_mc.assistant.context import build_guide_context_packet
from rcm_mc.assistant.guide_prompt_builder import (
    build_guide_system_prompt,
    build_guide_user_prompt,
    clean_guide_answer,
    packet_to_prompt_context,
    sanitize_onscreen_figures,
)


class PromptBuilderTests(unittest.TestCase):
    def setUp(self):
        self.packet = build_guide_context_packet("/diligence/hcris-xray")

    def test_user_prompt_includes_page_and_sources_and_limits(self):
        prompt = build_guide_user_prompt(
            "Where does this data come from?", self.packet
        )
        self.assertIn("HCRIS X-Ray", prompt)
        self.assertIn("cms_hcris", prompt)  # data-source context present
        self.assertIn("limitations", prompt.lower())
        self.assertIn("Where does this data come from?", prompt)

    def test_user_prompt_includes_metric_common_misread(self):
        """The metric-context block must surface the 'classic mistake'
        line directly to the model. PR #1257-#1258 filled the
        common_misread field for all 81 metrics; the prompt builder must
        actually include it (it used to drop it). A metric that resolves
        on the page (HCRIS X-Ray pulls operating_margin, bed_count,
        etc.) is the simplest path to verify."""
        prompt = build_guide_user_prompt(
            "How should I read operating margin here?", self.packet
        )
        # At least one resolved metric on this page should carry the
        # 'Common misread:' label inside the metric-contexts block.
        self.assertIn("Common misread:", prompt)
        # And the placeholder should never leak through to the prompt.
        self.assertNotIn("Common misread: Needs source documentation",
                         prompt)

    def test_user_prompt_includes_metric_related_routes(self):
        """The metric-context block must surface the metric's
        related_routes ('Discussed on: …') so the Guide can suggest
        other pages where the metric is explained. Distinct from the
        page's own related_routes block. PR #1281 wires this in;
        TestMetricsHaveTwoOrMoreRelatedRoutes guarantees every metric
        has ≥2 entries already."""
        prompt = build_guide_user_prompt(
            "Where else can I see denial_rate?", self.packet
        )
        self.assertIn("Discussed on:", prompt)

    def test_user_prompt_includes_metric_related_metrics(self):
        """The metric-context block must surface related_metrics so
        the Guide can hop between paired concepts (e.g. denial_rate ↔
        net_collection_rate). PR #1258's invariant ensures every metric
        ships ≥1 related_metrics entry that resolves; PR #1274 wires
        the list into the prompt as a tight comma-separated clause.
        /diligence/hcris-xray resolves multiple metrics with populated
        related_metrics."""
        prompt = build_guide_user_prompt(
            "What's related to denial rate?", self.packet
        )
        self.assertIn("Related metrics:", prompt)

    def test_user_prompt_has_no_double_period_artifacts(self):
        """The registry convention is for values (caveats,
        provenance_notes, freshness_lag, etc.) to end in a period.
        Earlier templates also appended their own period, producing
        'foo..' / 'foo.;' artifacts where clauses met. PR #1286
        introduced _dot() to strip trailing punctuation from values
        before composing — this test guards against a future template
        that re-introduces the double-terminator pattern."""
        import re
        prompt = build_guide_user_prompt(
            "test", self.packet
        )
        # Excludes the ellipsis '...' (which is a single token, not a
        # double-period artifact).
        offenders = [
            m.group() for m in re.finditer(r"\.\.+", prompt)
            if m.group() != "..."
        ]
        self.assertEqual(
            offenders, [],
            "Double-period artifacts in prompt — likely a template "
            "appended a period to a value that already ends in one. "
            "Use _dot() on the value first."
        )

    def test_user_prompt_includes_metric_diligence_read(self):
        """The metric-context block must surface diligence_interpretation
        directly to the model — this is what partners actually want
        ('how should I read this for diligence'). Every metric in the
        registry has it populated; this guards against the prompt
        builder dropping it like it used to drop common_misread."""
        prompt = build_guide_user_prompt(
            "How should I read operating margin here?", self.packet
        )
        self.assertIn("Diligence read:", prompt)
        self.assertNotIn("Diligence read: Needs source documentation",
                         prompt)

    def test_user_prompt_collapses_duplicate_desc_and_purpose(self):
        """52 PageContexts (built via the _BATCH7 / _BATCH8 loops) have
        short_description == primary_purpose. The prompt builder must
        emit the line only once when they match, so the prompt doesn't
        carry a wasted-context duplicate. /biosimilars is one of the
        canonical 52 with this property."""
        packet = build_guide_context_packet("/biosimilars")
        prompt = build_guide_user_prompt("What is this page?", packet)
        # The single combined label must appear once.
        self.assertEqual(
            prompt.count("Page description / primary purpose:"), 1
        )
        # And the two separate labels must NOT appear (collapsed away).
        self.assertNotIn("Short description:", prompt)
        self.assertNotIn("Primary purpose:", prompt)

    def test_user_prompt_includes_data_source_ic_ready_flag(self):
        """The data-source-context block must surface the ic_ready
        flag so the model can answer 'Is this IC-ready?' directly from
        the per-source contract. PR #1267 set the flag explicitly on
        every source; PR #1268 wires it into the prompt. /diligence/
        hcris-xray pulls cms_hcris (ic_ready=False) — the 'IC-ready: no'
        clause must appear."""
        prompt = build_guide_user_prompt(
            "Is this data IC-ready?", self.packet
        )
        # cms_hcris is ic_ready=False — the 'no' clause must appear.
        self.assertIn("IC-ready: no", prompt)

    def test_user_prompt_includes_diligence_use_cases(self):
        """The page-context block must surface diligence_use_cases so
        the Guide can answer 'what would I use this page for in
        diligence?' directly. PR #1256 drained the NEEDS placeholder
        on this field across all 360 pages; PR #1271 wires it into the
        prompt. /diligence/hcris-xray has multiple use-case entries —
        the 'Diligence use cases:' label must appear, and the legacy
        placeholder must never appear."""
        prompt = build_guide_user_prompt(
            "What is this page for?", self.packet
        )
        self.assertIn("Diligence use cases:", prompt)
        self.assertNotIn("Diligence use cases:\n- Needs source",
                         prompt)

    def test_user_prompt_includes_model_logic_summary(self):
        """The page-context block must surface model_logic_summary so
        the Guide can answer 'how does this page compute X?' directly.
        PRs #1235-#1244 drained the NEEDS placeholder on this field
        across all 360 pages; PR #1272 wires it into the prompt.
        /diligence/hcris-xray has a real model_logic_summary; the
        'Model logic:' clause must appear, and the legacy placeholder
        must never appear."""
        prompt = build_guide_user_prompt(
            "How does this page compute the figures?", self.packet
        )
        self.assertIn("Model logic:", prompt)
        self.assertNotIn("Model logic: Needs source documentation",
                         prompt)

    def test_user_prompt_includes_intended_users_when_distinct(self):
        """The page-context block emits an 'Intended users:' clause
        ONLY when the page's intended_users differs from the standard
        PE deal team default. PR #1288 wires this so the Guide tailors
        answers for the ~7 pages with a sharper persona (e.g.
        /portfolio/monte-carlo's LP-reporting audience), without
        bloating the prompt for the 91% default case."""
        # /ebitda-bridge declares 'Deal team underwriting an RCM
        # value-creation thesis.' as its intended_users.
        packet = build_guide_context_packet("/ebitda-bridge")
        prompt = build_guide_user_prompt("Who is this for?", packet)
        self.assertIn("Intended users:", prompt)
        self.assertIn("value-creation thesis", prompt)

    def test_user_prompt_omits_intended_users_for_default_pages(self):
        """When the page carries only the standard PE-deal-team
        default, the prompt does NOT emit the clause (it would be
        redundant with the system prompt's audience framing)."""
        # /diligence/hcris-xray uses the default intended_users.
        prompt = build_guide_user_prompt(
            "Who is this for?", self.packet
        )
        self.assertNotIn("Intended users:", prompt)

    def test_user_prompt_includes_route_specific_notes_for_parameterized(self):
        """Parameterized pages (/my/AT, /diligence/risk-workbench,
        /market-data/state/CA) carry route-specific
        notes_for_assistant beyond the standard _BASE_NOTES baseline.
        PR #1270 wires that route-specific layer into the prompt so the
        Guide knows how the trailing path segment maps to a parameter.
        Verify /my/AT shows the 'owner identifier' note."""
        packet = build_guide_context_packet("/my/AT")
        prompt = build_guide_user_prompt("Whose dashboard is this?", packet)
        self.assertIn("Route-specific assistant notes:", prompt)
        # The /my/AT note specifically calls out the 'AT' segment.
        self.assertIn("owner identifier", prompt)

    def test_user_prompt_omits_route_specific_notes_for_standard_pages(self):
        """Pages with only the standard 3-line _BASE_NOTES (the vast
        majority) must NOT carry the 'Route-specific assistant notes'
        section — those baseline notes are already covered by the
        system prompt's policy section, so emitting them again would
        bloat the prompt with redundant boilerplate."""
        # /diligence/hcris-xray carries only the standard 3 base notes.
        prompt = build_guide_user_prompt(
            "What does this page do?", self.packet
        )
        self.assertNotIn("Route-specific assistant notes:", prompt)

    def test_user_prompt_includes_data_source_strengths(self):
        """The data-source-context block must surface the strengths
        list so the model has 'what's this source positively good at'
        alongside description (what it is) and limitations (what it
        is NOT). PR #1262 ensured strengths carries real content for
        every source; PR #1273 wires it into the prompt.
        /diligence/hcris-xray pulls cms_hcris (strengths includes the
        comprehensive/free/comparable phrasing). The Strengths clause
        must appear, and the legacy placeholder must never appear."""
        prompt = build_guide_user_prompt(
            "What is this source good at?", self.packet
        )
        self.assertIn("Strengths:", prompt)
        # Verify the placeholder never leaks through.
        self.assertNotIn("Strengths: Needs source documentation",
                         prompt)

    def test_user_prompt_includes_data_source_provenance(self):
        """The data-source-context block must surface provenance_notes
        so the model can answer 'where does this come from / what
        should I cite?' directly. PR #1262 drained every NEEDS
        placeholder on this field; PR #1269 wires it into the prompt.
        /diligence/hcris-xray pulls cms_hcris (provenance mentions the
        CMS dataset + cost-report year). The Provenance clause must
        appear, and the legacy placeholder must never appear."""
        prompt = build_guide_user_prompt(
            "Where does this come from?", self.packet
        )
        self.assertIn("Provenance:", prompt)
        self.assertNotIn("Provenance: Needs source documentation",
                         prompt)

    def test_user_prompt_keeps_distinct_desc_and_purpose_apart(self):
        """When short_description and primary_purpose carry distinct
        text (the partner-facing case where the author wrote them
        intentionally), the prompt builder must keep both lines so the
        model sees both angles. /diligence/hcris-xray is a real example
        with two distinct lines."""
        prompt = build_guide_user_prompt(
            "What does this page do?", self.packet
        )
        # The combined line must NOT appear.
        self.assertNotIn("Page description / primary purpose:", prompt)
        # Both separate labels must appear.
        self.assertIn("Short description:", prompt)
        self.assertIn("Primary purpose:", prompt)

    def test_system_prompt_has_readonly_policy_and_rules(self):
        sysp = build_guide_system_prompt(self.packet).lower()
        # explicit disallowed behaviors
        self.assertIn("final investment recommendations", sysp)
        self.assertIn("modify data", sysp)
        self.assertIn("do not invent formula", sysp)
        # read-only identity present
        self.assertIn("read-only", sysp)
        # no chain-of-thought
        self.assertIn("<think>", sysp)  # mentioned as forbidden

    def test_system_prompt_invites_analysis_but_keeps_guardrails(self):
        # The Guide should act like an analyst (interpret/connect into analysis
        # + suggest a next step), WITHOUT crossing into buy/sell calls or
        # losing the read-only / no-fabrication contract.
        sysp = build_guide_system_prompt(self.packet).lower()
        self.assertIn("analyze", sysp)
        self.assertIn("driver or risk", sysp)
        self.assertIn("next step", sysp)
        self.assertIn("diligence analyst", sysp)
        # guardrails intact
        self.assertIn("not a buy/sell/hold call", sysp)
        self.assertIn("final investment recommendations", sysp)
        self.assertIn("ground every claim in the provided context", sysp)

    def test_analyst_lens_does_not_trip_the_recommendation_guard(self):
        # The new style language itself must not read as an investment
        # recommendation to the eval gate.
        from rcm_mc.assistant.eval.guide_eval import has_investment_recommendation
        sysp = build_guide_system_prompt(self.packet)
        self.assertFalse(has_investment_recommendation(sysp)[0])

    def test_packet_to_prompt_context_respects_max_chars(self):
        small = packet_to_prompt_context(self.packet, max_chars=400)
        self.assertLessEqual(len(small), 400)
        # limitations / missing notes are never dropped entirely
        self.assertIn("Some context was omitted for length.", small)

    def test_clean_strips_think_blocks(self):
        self.assertEqual(
            clean_guide_answer("<think>secret reasoning</think>Real answer."),
            "Real answer.",
        )
        # dangling unterminated think tail also removed
        self.assertEqual(
            clean_guide_answer("Answer here.\n<think>leaked tail"),
            "Answer here.",
        )
        # multiline think block
        out = clean_guide_answer("<think>\nstep 1\nstep 2\n</think>\nFinal.")
        self.assertNotIn("step 1", out)
        self.assertEqual(out, "Final.")

    def test_clean_trims_repetitive_preamble_but_keeps_caveats(self):
        out = clean_guide_answer(
            "Based on the provided context, HCRIS data may lag operations."
        )
        self.assertNotIn("Based on the provided context", out)
        self.assertIn("HCRIS data may lag operations.", out)

    def test_system_prompt_has_answer_style_guidance(self):
        sysp = build_guide_system_prompt(self.packet).lower()
        # A dedicated readability section with a direct-answer-first rule,
        # a length ceiling, the plain labels, and a no-filler instruction.
        self.assertIn("answer style", sysp)
        self.assertIn("1-2 sentence", sysp)
        self.assertIn("150 words", sysp)
        self.assertIn("filler", sysp)
        for label in ("what it means", "where it comes from",
                      "why it matters", "caveat"):
            self.assertIn(label, sysp)
        # Readability guidance must not weaken the read-only contract.
        self.assertIn("final investment recommendations", sysp)

    def test_system_prompt_has_retrieved_context_rule(self):
        sysp = build_guide_system_prompt(self.packet).lower()
        self.assertIn("retrieved", sysp)
        self.assertIn("primary", sysp)
        self.assertIn("not this deal's data", sysp)

    def test_user_prompt_with_rag_context_keeps_packet_primary(self):
        rag_block = ("=== Additional local Guide context (retrieved) ===\n"
                     "[1] Metric Registry — Denial Rate [metric · denial_rate]: "
                     "Share of claims denied.")
        prompt = build_guide_user_prompt(
            "What does denial rate mean?", self.packet, rag_block)
        # page packet still present + retrieved block appended after it
        self.assertIn("HCRIS X-Ray", prompt)
        self.assertIn("Additional local Guide context", prompt)
        self.assertLess(prompt.index("HCRIS X-Ray"),
                        prompt.index("Additional local Guide context"))
        self.assertIn("page context is primary", prompt)

    def test_user_prompt_without_rag_is_unchanged(self):
        # Backward compatible: omitting rag_context reproduces the v1 prompt.
        a = build_guide_user_prompt("Q?", self.packet)
        b = build_guide_user_prompt("Q?", self.packet, "")
        self.assertEqual(a, b)
        self.assertNotIn("Additional local Guide context", a)

    def test_system_prompt_has_onscreen_figures_rule(self):
        # The Guide must know it may analyze the live on-screen numbers but
        # treat them as displayed (not validated) — and the guardrails stay.
        sysp = build_guide_system_prompt(self.packet).lower()
        self.assertIn("on-screen figures", sysp)
        self.assertIn("displayed, not re-validated", sysp)
        self.assertIn("never invent figures", sysp)
        # guardrail intact: as-displayed values don't become IC-ready
        self.assertIn("ic-ready", sysp)

    def test_user_prompt_includes_onscreen_block_after_page_context(self):
        figs = [{"label": "Operating Margin", "value": "12.3%"},
                {"label": "Net Revenue", "value": "$450.25M"}]
        prompt = build_guide_user_prompt(
            "Is the margin healthy?", self.packet, "", figs)
        self.assertIn("On-screen figures", prompt)
        self.assertIn("Operating Margin: 12.3%", prompt)
        self.assertIn("$450.25M", prompt)
        # as-displayed framing present (honesty)
        self.assertIn("NOT been", prompt)
        self.assertIn("re-validated", prompt)
        # page context stays primary (appears before the on-screen block)
        self.assertLess(prompt.index("HCRIS X-Ray"),
                        prompt.index("On-screen figures"))

    def test_user_prompt_without_onscreen_is_unchanged(self):
        # Backward compatible: omitting on-screen figures (or passing []) must
        # reproduce the v1 prompt exactly.
        a = build_guide_user_prompt("Q?", self.packet)
        b = build_guide_user_prompt("Q?", self.packet, "", [])
        c = build_guide_user_prompt("Q?", self.packet, "", None)
        self.assertEqual(a, b)
        self.assertEqual(a, c)
        self.assertNotIn("On-screen figures", a)

    def test_sanitize_onscreen_figures_bounds_and_filters(self):
        # caps the count at 24
        many = [{"label": f"L{i}", "value": f"{i}"} for i in range(100)]
        self.assertEqual(len(sanitize_onscreen_figures(many)), 24)
        # caps per-string length and collapses whitespace
        out = sanitize_onscreen_figures(
            [{"label": "x" * 200, "value": "  9 \n 9  "}])
        self.assertEqual(len(out[0]["label"]), 80)
        self.assertEqual(out[0]["value"], "9 9")
        # drops malformed / empty / wrong-typed entries
        bad = sanitize_onscreen_figures([
            {"label": "ok", "value": ""},          # empty value
            {"label": "", "value": "9"},            # empty label
            {"label": 1, "value": 2},               # wrong types
            "not a dict",
            {"value": "9"},                          # missing label
        ])
        self.assertEqual(bad, [])
        # non-list input is safe
        self.assertEqual(sanitize_onscreen_figures("nope"), [])
        self.assertEqual(sanitize_onscreen_figures(None), [])

    def test_unknown_route_prompt_is_conservative(self):
        pkt = build_guide_context_packet("/unknown-route")
        prompt = build_guide_user_prompt("What does this page do?", pkt)
        self.assertIn("missing", prompt.lower())  # context_quality / notes
        # builder must not crash on a missing page_context
        self.assertTrue(prompt.strip())


if __name__ == "__main__":
    unittest.main()
