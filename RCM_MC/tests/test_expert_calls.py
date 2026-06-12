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
    CDD_TOPICS, LEDGER_TAG_ORDER, QUESTION_BANK, STAKEHOLDER_TYPES,
    THESIS_TAGS, COVERED, THIN, UNCOVERED, TRIANGULATED, SINGLE_LENS,
    DARK, build_call_guide, call_sheet_rows, coverage_read,
    findings_ledger, format_call_note, logged_call_counts,
    parse_call_note, program_plan, stakeholder, topic_coverage,
    topic_lens_matrix, weekly_cadence,
)
from rcm_mc.ui.expert_calls_page import (
    expert_calls_csv, findings_csv, render_expert_calls_page,
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


class CallNoteTests(unittest.TestCase):
    def test_note_round_trips_through_the_counter(self):
        bodies = [
            format_call_note("payer_exec", vantage="former VP, TX Blues",
                             finding="Target is top-quartile on rates",
                             tag="CONTRADICTS", as_of="2026-06"),
            format_call_note("payer_exec", vantage="ex-network director",
                             finding="Must-have in two metros",
                             tag="SUPPORTS"),
            format_call_note("referring_physician", vantage="TX PCP",
                             finding="Refers on access alone",
                             tag="NEW QUESTION"),
        ]
        self.assertEqual(logged_call_counts(bodies),
                         {"payer_exec": 2, "referring_physician": 1})

    def test_note_carries_all_fields_and_defaults(self):
        note = format_call_note(
            "industry_expert", vantage="", finding="MFP lands 2028",
            tag="supports", as_of="")
        self.assertIn("EXPERT CALL · Industry / reimbursement expert",
                      note)
        self.assertIn("vantage unstated", note)
        self.assertIn("(as of date unstated)", note)
        self.assertIn("[SUPPORTS]", note)   # tag normalized upper

    def test_invalid_inputs_raise_never_malform(self):
        with self.assertRaises(ValueError):
            format_call_note("astrologer", vantage="x", finding="y",
                             tag="SUPPORTS")
        with self.assertRaises(ValueError):
            format_call_note("payer_exec", vantage="x", finding="y",
                             tag="MAYBE")
        with self.assertRaises(ValueError):
            format_call_note("payer_exec", vantage="x", finding="  ",
                             tag="SUPPORTS")

    def test_free_text_notes_never_inflate_coverage(self):
        bodies = [
            "Talked to a payer exec today — interesting call.",
            "EXPERT CALLBACK · Payer / contracting executive — x: y [Z]",
            "",
            None,
        ]
        self.assertEqual(logged_call_counts(bodies), {})

    def test_thesis_tags_constant(self):
        self.assertEqual(THESIS_TAGS,
                         ("SUPPORTS", "CONTRADICTS", "NEW QUESTION"))


class FindingsLedgerTests(unittest.TestCase):
    def _note(self, lens="payer_exec", finding="Rates above market",
              tag="CONTRADICTS", vantage="ex-VP", as_of="2026-06"):
        return format_call_note(lens, vantage=vantage, finding=finding,
                                tag=tag, as_of=as_of)

    def test_parser_is_the_exact_inverse(self):
        body = self._note(finding="Finding with [brackets] inside")
        f = parse_call_note(body)
        self.assertEqual(f["lens"], "payer_exec")
        self.assertEqual(f["finding"], "Finding with [brackets] inside")
        self.assertEqual(f["tag"], "CONTRADICTS")
        self.assertEqual(f["vantage"], "ex-VP")
        self.assertEqual(f["as_of"], "2026-06")

    def test_parser_rejects_free_text_and_fake_lenses(self):
        self.assertIsNone(parse_call_note("Talked to a payer today"))
        self.assertIsNone(parse_call_note(
            "EXPERT CALL · Astrologer — x (as of y): z [SUPPORTS]"))
        self.assertIsNone(parse_call_note(None))
        self.assertIsNone(parse_call_note(
            "EXPERT CALL · Payer / contracting executive — x "
            "(as of y): z [MAYBE]"))

    def test_ledger_groups_contradictions_first(self):
        ledger = findings_ledger([
            self._note(tag="SUPPORTS", finding="s1"),
            self._note(tag="CONTRADICTS", finding="c1"),
            self._note(tag="NEW QUESTION", finding="q1",
                       lens="referring_physician"),
            "free text never counted",
        ])
        self.assertEqual(ledger["total"], 3)
        self.assertEqual(LEDGER_TAG_ORDER[0], "CONTRADICTS")
        self.assertEqual(ledger["counts"],
                         {"CONTRADICTS": 1, "NEW QUESTION": 1,
                          "SUPPORTS": 1})
        self.assertEqual(ledger["warnings"], [])

    def test_confirmation_bias_warning_fires_only_at_scale(self):
        all_supports = [self._note(tag="SUPPORTS", finding=f"s{i}")
                        for i in range(5)]
        ledger = findings_ledger(all_supports)
        self.assertEqual(len(ledger["warnings"]), 1)
        self.assertIn("isn't listening", ledger["warnings"][0])
        # Four findings is too small a base to call bias.
        self.assertEqual(findings_ledger(all_supports[:4])["warnings"],
                         [])
        # One contradiction clears it at any size.
        self.assertEqual(findings_ledger(
            all_supports + [self._note(tag="CONTRADICTS")])["warnings"],
            [])

    def test_findings_csv_shape_and_defang(self):
        out = findings_csv("=evil()", [
            self._note(finding="=cmd()|x", tag="CONTRADICTS"),
            self._note(tag="SUPPORTS", finding="fine"),
        ])
        self.assertIn("'=evil()", out)
        self.assertIn("'=cmd()", out)
        self.assertIn("CONTRADICTS,1", out.replace('"', ""))
        lines = out.strip().splitlines()
        self.assertIn("Thesis tag,Finding,Lens", out)
        # Contradiction row precedes the supports row.
        self.assertLess(
            next(i for i, l in enumerate(lines)
                 if l.startswith("CONTRADICTS,")),
            next(i for i, l in enumerate(lines)
                 if l.startswith("SUPPORTS,")))

    def test_empty_ledger_csv_is_honest(self):
        out = findings_csv("", [])
        self.assertIn("(no deal set)", out)
        self.assertIn("Total findings,0", out)


class LogCallHTTPTests(unittest.TestCase):
    """POST /api/expert-calls/log records the structured note on an
    EXISTING deal, and the page's coverage tracker derives from the
    logged notes (explicit done_* params win) — over real HTTP."""

    @classmethod
    def setUpClass(cls):
        import os
        import socket
        import tempfile
        import threading
        import time
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.server import build_server
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = os.path.join(cls.tmp.name, "p.db")
        store = PortfolioStore(cls.db)
        store.upsert_deal("buh", name="Bigtown Health",
                          profile={"state": "TX"})
        cls.store = store
        s = socket.socket(); s.bind(("127.0.0.1", 0))
        cls.port = s.getsockname()[1]; s.close()
        cls.server, _ = build_server(
            port=cls.port, host="127.0.0.1", db_path=cls.db, auth=None)
        cls.t = threading.Thread(target=cls.server.serve_forever,
                                 daemon=True)
        cls.t.start(); time.sleep(0.2)
        import urllib.request as _u

        class _NoRedirect(_u.HTTPRedirectHandler):
            def redirect_request(self, *a, **k):
                return None
        cls.opener = _u.build_opener(_NoRedirect)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close()
        cls.t.join(timeout=5); cls.tmp.cleanup()

    @staticmethod
    def _cookie():
        import json
        import urllib.parse
        return "pedesk_active_deal_meta=" + urllib.parse.quote(
            json.dumps({"id": "buh", "name": "Bigtown Health",
                        "state": "TX", "ccn": ""},
                       separators=(",", ":")))

    def _post(self, data):
        import urllib.error
        import urllib.parse
        import urllib.request as _u
        req = _u.Request(
            f"http://127.0.0.1:{self.port}/api/expert-calls/log",
            data=urllib.parse.urlencode(data).encode(), method="POST")
        try:
            resp = self.opener.open(req, timeout=30)
            return resp.status, resp.headers.get("Location", "")
        except urllib.error.HTTPError as e:
            return e.code, e.headers.get("Location", "")

    def _get(self, path, cookie=None):
        import urllib.request as _u
        req = _u.Request(f"http://127.0.0.1:{self.port}{path}")
        if cookie:
            req.add_header("Cookie", cookie)
        with _u.urlopen(req, timeout=20) as r:
            return r.status, r.read().decode()

    def _notes(self):
        from rcm_mc.deals.deal_notes import list_notes
        df = list_notes(self.store, "buh")
        return df["body"].tolist() if len(df) else []

    def test_01_form_only_with_active_deal(self):
        _, body = self._get("/diligence/expert-calls")
        self.assertNotIn("LOG A COMPLETED CALL", body)
        _, body = self._get("/diligence/expert-calls",
                            cookie=self._cookie())
        self.assertIn("LOG A COMPLETED CALL — BIGTOWN HEALTH", body)
        self.assertIn("/api/expert-calls/log", body)

    def test_02_log_then_coverage_reflects_it(self):
        code, loc = self._post(
            {"deal_id": "buh", "lens": "payer_exec",
             "vantage": "former VP, TX Blues",
             "finding": "Target is top-quartile on commercial rates",
             "tag": "CONTRADICTS", "as_of": "2026-06"})
        self.assertEqual(code, 303)
        self.assertIn("logged=1", loc)
        notes = self._notes()
        self.assertTrue(any(
            b.startswith("EXPERT CALL · Payer / contracting executive")
            for b in notes))
        # The page (with the deal context) derives the count.
        _, body = self._get("/diligence/expert-calls?logged=1",
                            cookie=self._cookie())
        self.assertIn("Call logged to", body)
        self.assertIn("logged EXPERT CALL note", body)
        self.assertIn(">THIN<", body)   # payer lens now 1 call
        # Explicit params still win over the notes-derived counts.
        _, body = self._get(
            "/diligence/expert-calls?done_payer_exec=2",
            cookie=self._cookie())
        self.assertNotIn("logged EXPERT CALL note", body)

    def test_04_ledger_renders_logged_findings_grouped(self):
        # Log a contradiction; the on-page ledger groups it under
        # CONTRADICTS with its vantage, and the CSV serves it.
        code, _ = self._post(
            {"deal_id": "buh", "lens": "competitor_exec",
             "vantage": "rival COO, DFW",
             "finding": "They are adding 3 sites in the same metro",
             "tag": "CONTRADICTS", "as_of": "2026-05"})
        self.assertEqual(code, 303)
        _, body = self._get("/diligence/expert-calls",
                            cookie=self._cookie())
        self.assertIn("Findings ledger — Bigtown Health", body)
        self.assertIn("CONTRADICTS (", body)   # grouped section header
        self.assertIn("rival COO, DFW", body)
        self.assertIn("/api/expert-calls/findings.csv?deal_id=buh",
                      body)
        _, csv_out = self._get(
            "/api/expert-calls/findings.csv?deal_id=buh")
        self.assertIn("adding 3 sites", csv_out)
        # Unknown deal → honest empty ledger, never an error.
        _, csv_empty = self._get(
            "/api/expert-calls/findings.csv?deal_id=ghost")
        self.assertIn("Total findings,0", csv_empty)

    def test_05_no_deal_context_no_ledger(self):
        _, body = self._get("/diligence/expert-calls")
        self.assertNotIn("Findings ledger", body)

    def test_03_unknown_deal_or_bad_fields_record_nothing(self):
        before = len(self._notes())
        code, loc = self._post(
            {"deal_id": "ghost", "lens": "payer_exec",
             "finding": "x", "tag": "SUPPORTS"})
        self.assertEqual(code, 303)
        self.assertNotIn("logged=1", loc)
        for bad in ({"deal_id": "buh", "lens": "astrologer",
                     "finding": "x", "tag": "SUPPORTS"},
                    {"deal_id": "buh", "lens": "payer_exec",
                     "finding": "x", "tag": "MAYBE"},
                    {"deal_id": "buh", "lens": "payer_exec",
                     "finding": "  ", "tag": "SUPPORTS"}):
            code, loc = self._post(bad)
            self.assertEqual(code, 303)
            self.assertNotIn("logged=1", loc)
        self.assertEqual(len(self._notes()), before)


if __name__ == "__main__":
    unittest.main()
