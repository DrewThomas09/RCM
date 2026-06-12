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
    COVERED, THIN, UNCOVERED, TRIANGULATED, SINGLE_LENS, DARK,
    build_call_guide, call_sheet_rows, coverage_read, program_plan,
    stakeholder, topic_coverage, topic_lens_matrix, weekly_cadence,
)
from rcm_mc.ui.expert_calls_page import (
    expert_calls_csv, render_expert_calls_page,
)


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


class WeeklyCadenceTests(unittest.TestCase):
    def test_cadence_retimes_never_resizes(self):
        # Per-lens week sums must equal the program plan exactly.
        for total in (8, 20, 33):
            cad = weekly_cadence(total)
            plan = {p["stakeholder"]["key"]: p["calls"]
                    for p in program_plan(total)}
            for key, weeks in cad["by_lens_weeks"].items():
                self.assertEqual(sum(weeks), plan[key],
                                 f"{key} resized at total {total}")
            self.assertEqual(cad["total"], total)
            self.assertEqual(len(cad["weeks"]), 4)

    def test_sequencing_logic_holds(self):
        cad = weekly_cadence(20)["by_lens_weeks"]
        # Former employees front-load (fastest to book, frame the
        # hypotheses); payers wait for precise questions.
        self.assertGreater(cad["former_employee"][0],
                           cad["former_employee"][3])
        self.assertEqual(cad["payer_exec"][0], 0)
        self.assertGreater(sum(cad["payer_exec"][1:3]), 0)

    def test_every_week_has_focus_and_rationale(self):
        for w in weekly_cadence(20)["weeks"]:
            self.assertTrue(w["focus"])
            self.assertTrue(w["rationale"])


class TopicCoverageTests(unittest.TestCase):
    def test_matrix_derived_from_bank(self):
        rows = topic_lens_matrix()
        self.assertEqual([r["topic"] for r in rows], CDD_TOPICS)
        for r in rows:
            for key in r["lenses"]:
                self.assertTrue(
                    any(q["topic"] == r["topic"]
                        for q in QUESTION_BANK[key]),
                    f"{key} listed for {r['topic']} but never asks it")

    def test_triangulation_needs_two_active_lenses(self):
        # No calls → every topic DARK.
        for r in topic_coverage({}):
            self.assertEqual(r["status"], DARK)
        # One active lens → its topics are SINGLE-LENS, never
        # triangulated (two voices from one lens share its bias).
        rows = topic_coverage({"referring_physician": 4})
        by_topic = {r["topic"]: r for r in rows}
        self.assertEqual(by_topic["demand"]["status"], SINGLE_LENS)
        self.assertEqual(
            by_topic["pricing_reimbursement"]["status"], DARK)
        # A second lens that shares a topic triangulates it.
        rows = topic_coverage({"referring_physician": 1,
                               "payer_exec": 1})
        by_topic = {r["topic"]: r for r in rows}
        self.assertEqual(by_topic["demand"]["status"], TRIANGULATED)


class CallSheetTests(unittest.TestCase):
    def test_one_row_per_planned_call_weeks_ascending(self):
        rows = call_sheet_rows(20)
        self.assertEqual(len(rows), 20)
        self.assertEqual([r["call_no"] for r in rows],
                         list(range(1, 21)))
        self.assertEqual([r["week"] for r in rows],
                         sorted(r["week"] for r in rows))
        self.assertTrue(all(r["sourcing"] for r in rows))

    def test_csv_export_shape_and_defang(self):
        out = expert_calls_csv({"n": ["12"], "deal": ["=cmd()|x"]})
        lines = out.strip().splitlines()
        # Header block + blank + column row + 12 call rows.
        self.assertIn("Expert-call sheet", lines[0])
        self.assertIn("'=cmd()", lines[0])     # formula defanged
        self.assertIn("Question bank vintage", out)
        self.assertIn("Thesis tag (SUPPORTS / CONTRADICTS", out)
        data_rows = [l for l in lines
                     if l and l.split(",")[0].isdigit()]
        self.assertEqual(len(data_rows), 12)

    def test_csv_no_deal_states_it(self):
        self.assertIn("(no deal set)", expert_calls_csv({}))


class SliceTwoPageTests(unittest.TestCase):
    def test_cadence_matrix_and_csv_link_render(self):
        page = render_expert_calls_page({})
        for needle in ("CADENCE — THE STANDARD 4-WEEK SPRINT",
                       "Week 4 — Close",
                       "TOPIC × LENS — WHO CAN ANSWER WHAT",
                       "/api/diligence/expert-calls.csv?n=20",
                       "Download call sheet (CSV)"):
            self.assertIn(needle, page, f"missing: {needle}")
        # No coverage entered → matrix shows no triangulation chips.
        self.assertNotIn(">TRIANGULATED<", page)

    def test_topic_chips_follow_done_counts(self):
        page = render_expert_calls_page(
            {"done_referring_physician": ["1"], "done_payer_exec": ["1"]})
        self.assertIn(">TRIANGULATED<", page)
        self.assertIn(">DARK<", page)

    def test_guide_renders_in_exhibit_chrome(self):
        page = render_expert_calls_page({"deal": ["Project Falcon"]})
        self.assertIn("EXHIBIT 1", page.upper())
        self.assertIn("PEdesk curated question bank", page)
        self.assertIn("bank 2026-06", page)

    def test_csv_link_carries_deal_but_never_prefill_key(self):
        page = render_expert_calls_page(
            {"deal": ["Falcon"], "_prefill_deal": ["Falcon"]})
        self.assertIn("/api/diligence/expert-calls.csv?n=20&deal=Falcon",
                      page)
        self.assertNotIn("_prefill_deal=", page.split("expert-calls.csv")[1]
                         .split('"')[0])


class ActiveDealPrefillHTTPTests(unittest.TestCase):
    """The active-deal cookie pre-stamps the program (visible note;
    explicit ?deal= wins) — exercised over real HTTP like the other
    deal-context prefill suites."""

    @classmethod
    def setUpClass(cls):
        import os
        import socket
        import tempfile
        import threading
        import time
        from rcm_mc.server import build_server
        cls.tmp = tempfile.TemporaryDirectory()
        s = socket.socket(); s.bind(("127.0.0.1", 0))
        cls.port = s.getsockname()[1]; s.close()
        cls.server, _ = build_server(
            port=cls.port, host="127.0.0.1",
            db_path=os.path.join(cls.tmp.name, "p.db"), auth=None)
        cls.t = threading.Thread(target=cls.server.serve_forever,
                                 daemon=True)
        cls.t.start(); time.sleep(0.2)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close()
        cls.t.join(timeout=5); cls.tmp.cleanup()

    def _get(self, path, cookie=None):
        import urllib.request as _u
        req = _u.Request(f"http://127.0.0.1:{self.port}{path}")
        if cookie:
            req.add_header("Cookie", cookie)
        with _u.urlopen(req, timeout=20) as r:
            return r.status, r.read().decode()

    @staticmethod
    def _cookie(name="Bigtown Health"):
        import json
        import urllib.parse
        meta = {"id": "buh", "name": name, "state": "TX",
                "ccn": "450076"}
        return "pedesk_active_deal_meta=" + urllib.parse.quote(
            json.dumps(meta, separators=(",", ":")))

    def test_cookie_prefills_deal_with_visible_note(self):
        status, body = self._get("/diligence/expert-calls",
                                 cookie=self._cookie())
        self.assertEqual(status, 200)
        self.assertIn("Pre-scoped to your active deal", body)
        self.assertIn("Bigtown Health", body)
        self.assertIn("BIGTOWN HEALTH", body)   # guide stamp

    def test_explicit_deal_param_wins(self):
        status, body = self._get(
            "/diligence/expert-calls?deal=Project+Orca",
            cookie=self._cookie())
        self.assertEqual(status, 200)
        self.assertIn("Project Orca", body)
        self.assertNotIn("Pre-scoped to your active deal", body)

    def test_csv_endpoint_serves_sheet(self):
        status, body = self._get(
            "/api/diligence/expert-calls.csv?n=10&deal=Falcon")
        self.assertEqual(status, 200)
        self.assertIn("Expert-call sheet", body)
        self.assertEqual(
            sum(1 for l in body.splitlines()
                if l and l.split(",")[0].isdigit()), 10)

    def test_no_cookie_no_note(self):
        status, body = self._get("/diligence/expert-calls")
        self.assertEqual(status, 200)
        self.assertNotIn("Pre-scoped to your active deal", body)


if __name__ == "__main__":
    unittest.main()
