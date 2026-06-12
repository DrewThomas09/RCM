"""Expert-Call Program — CDD voice-of-customer planner.

Tests pin the question bank's integrity (every lens fully specified,
every question tagged to a valid CDD topic with a listen-for line),
the guide builder, the largest-remainder call-mix plan, the strict
coverage semantics (2+ covered / 1 thin / 0 blind spot — never an
average), and the route/nav/palette/guide wiring.
"""
from __future__ import annotations

import unittest

from rcm_mc.diligence.expert_calls import (
    CDD_TOPICS, QUESTION_BANK, STAKEHOLDER_TYPES,
    COVERED, THIN, UNCOVERED,
    build_call_guide, coverage_read, program_plan, stakeholder,
)
from rcm_mc.ui.expert_calls_page import render_expert_calls_page


class QuestionBankIntegrityTests(unittest.TestCase):
    def test_seven_lenses_fully_specified(self):
        self.assertEqual(len(STAKEHOLDER_TYPES), 7)
        for s in STAKEHOLDER_TYPES:
            for field in ("key", "label", "who", "why", "target_calls",
                          "sourcing", "bias"):
                self.assertTrue(s.get(field), f"{s['key']}.{field} empty")
            self.assertGreaterEqual(s["target_calls"], 2)

    def test_every_lens_has_a_question_set(self):
        for s in STAKEHOLDER_TYPES:
            bank = QUESTION_BANK.get(s["key"], [])
            self.assertGreaterEqual(
                len(bank), 4, f"{s['key']} has too few questions")
            for q in bank:
                self.assertIn(q["topic"], CDD_TOPICS)
                self.assertTrue(q["question"].strip())
                self.assertTrue(q["listen_for"].strip(),
                                f"{s['key']} question missing listen_for")

    def test_core_topics_triangulated_across_lenses(self):
        # The headline CDD topics must be askable through 2+ different
        # stakeholder lenses, or the program can't triangulate them.
        for topic in ("demand", "competition", "pricing_reimbursement",
                      "risks"):
            lenses = [k for k, bank in QUESTION_BANK.items()
                      if any(q["topic"] == topic for q in bank)]
            self.assertGreaterEqual(
                len(lenses), 2, f"topic {topic} single-lens")


class CallGuideTests(unittest.TestCase):
    def test_guide_built_in_topic_order_with_all_questions(self):
        g = build_call_guide("payer_exec", deal_name="Project Falcon")
        self.assertEqual(g["deal_name"], "Project Falcon")
        self.assertTrue(g["opening"])
        self.assertTrue(g["closing"])
        topics = [sec["topic"] for sec in g["sections"]]
        self.assertEqual(topics,
                         [t for t in CDD_TOPICS if t in topics])
        n = sum(len(sec["questions"]) for sec in g["sections"])
        self.assertEqual(n, len(QUESTION_BANK["payer_exec"]))
        self.assertEqual(g["question_count"], n)

    def test_unknown_lens_returns_none_not_generic_guide(self):
        self.assertIsNone(build_call_guide("astrologer"))
        self.assertIsNone(stakeholder("astrologer"))


class ProgramPlanTests(unittest.TestCase):
    def test_default_plan_matches_recommended_counts(self):
        # target_calls sum to 20, so the 20-call plan is exactly them.
        plan = program_plan(20)
        self.assertEqual(sum(p["calls"] for p in plan), 20)
        for p in plan:
            self.assertEqual(p["calls"], p["stakeholder"]["target_calls"])

    def test_scaled_plan_sums_exactly_and_keeps_every_lens(self):
        for total in (8, 12, 30, 75):
            plan = program_plan(total)
            self.assertEqual(sum(p["calls"] for p in plan), total,
                             f"total {total} mis-apportioned")
            # A full-size program never designs in a blind spot.
            self.assertTrue(all(p["calls"] >= 1 for p in plan),
                            f"zero-call lens at total {total}")

    def test_tiny_and_zero_programs(self):
        self.assertEqual(sum(p["calls"] for p in program_plan(3)), 3)
        self.assertEqual(sum(p["calls"] for p in program_plan(0)), 0)


class CoverageReadTests(unittest.TestCase):
    def test_strict_statuses(self):
        read = coverage_read({"referring_physician": 5, "payer_exec": 1})
        by_key = {r["stakeholder"]["key"]: r for r in read["rows"]}
        self.assertEqual(by_key["referring_physician"]["status"], COVERED)
        self.assertEqual(by_key["payer_exec"]["status"], THIN)
        self.assertEqual(by_key["competitor_exec"]["status"], UNCOVERED)
        self.assertFalse(read["complete"])

    def test_findings_name_the_gaps_not_an_average(self):
        read = coverage_read({"referring_physician": 5, "payer_exec": 1})
        text = " ".join(read["findings"])
        self.assertIn("Payer / contracting executive", text)
        self.assertIn("Single-source", text)
        self.assertIn("zero calls", text)
        self.assertNotIn("%", text)   # never a percent-done headline

    def test_all_covered_reads_complete(self):
        read = coverage_read({s["key"]: 3 for s in STAKEHOLDER_TYPES})
        self.assertTrue(read["complete"])
        self.assertIn("triangulated", " ".join(read["findings"]))

    def test_no_calls_yet_is_a_plain_starting_state(self):
        read = coverage_read({})
        self.assertEqual(read["total_done"], 0)
        self.assertIn("No calls logged yet", read["findings"][0])


class ExpertCallsPageTests(unittest.TestCase):
    def test_page_renders_plan_guide_and_tracker(self):
        page = render_expert_calls_page({})
        for needle in ("Expert-Call Program", "CALL MIX", "20-CALL",
                       "Referring physician", "Known bias of this lens",
                       "COVERAGE — CALLS COMPLETED PER LENS",
                       "Listen for:", "compliance",
                       "/diligence/cim-crosscheck"):
            self.assertIn(needle, page, f"missing: {needle}")
        self.assertNotIn("None", page.split("</title>")[1][:2000])

    def test_lens_and_size_qs_drive_the_page(self):
        page = render_expert_calls_page(
            {"lens": ["payer_exec"], "n": ["40"], "deal": ["Falcon"]})
        self.assertIn("40-CALL", page)
        self.assertIn("FALCON", page)          # guide stamp (upper-cased)
        self.assertIn("fee schedule", page)    # a payer question rendered

    def test_coverage_qs_renders_statuses(self):
        page = render_expert_calls_page(
            {"done_referring_physician": ["3"], "done_payer_exec": ["1"]})
        self.assertIn(">COVERED<", page)
        self.assertIn(">THIN<", page)
        self.assertIn(">UNCOVERED<", page)
        self.assertIn("Single-source", page)

    def test_hostile_inputs_stay_safe(self):
        page = render_expert_calls_page(
            {"lens": ["<script>alert(1)</script>"],
             "deal": ["<img src=x onerror=alert(1)>"],
             "n": ["nan"], "done_payer_exec": ["1e309"]})
        # The deal stamp renders only escaped; the unknown lens falls
        # back instead of echoing the payload into the lens chips.
        self.assertNotIn("<img src=x", page)
        self.assertIn("&lt;img src=x", page)
        self.assertNotIn("<script>alert", page)
        self.assertIn("Expert-Call Program", page)


class WiringTests(unittest.TestCase):
    def test_palette_and_section_map(self):
        from rcm_mc.ui._chartis_kit import (
            _DEFAULT_PALETTE_MODULES, _SUB_SECTION_MAP)
        routes = [m["route"] for m in _DEFAULT_PALETTE_MODULES]
        self.assertIn("/diligence/expert-calls", routes)
        self.assertEqual(
            _SUB_SECTION_MAP.get("/diligence/expert-calls"), "diligence")

    def test_guide_context_registered(self):
        from rcm_mc.assistant.context.manual_page_contexts import (
            MANUAL_PAGE_CONTEXTS)
        from rcm_mc.assistant.context.discovered_tool_routes import (
            DISCOVERED_TOOL_ROUTES)
        self.assertIn("/diligence/expert-calls", MANUAL_PAGE_CONTEXTS)
        self.assertIn("/diligence/expert-calls",
                      [t.route for t in DISCOVERED_TOOL_ROUTES])

    def test_diligence_index_links_the_page(self):
        from rcm_mc.ui.diligence_index_page import render_diligence_index
        self.assertIn("/diligence/expert-calls", render_diligence_index())


if __name__ == "__main__":
    unittest.main()
