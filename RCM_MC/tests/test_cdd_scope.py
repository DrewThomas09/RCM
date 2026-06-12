"""CDD Scope — the four engagement depths of a commercial due diligence.

Tests pin the level/workstream registries' integrity, the depth
matrix's monotonicity contract (L1→L3 never does less; L4 narrows),
the deterministic recommender, the task-list/CSV export, the page
render, and the route/nav/palette/guide wiring.
"""
from __future__ import annotations

import unittest

from rcm_mc.diligence.cdd_scope import (
    CDD_LEVELS, DEPTH_MATRIX, DEPTHS, WORKSTREAMS,
    NONE, DESKTOP, TARGETED, FULL,
    depth_for, level, level_task_list, recommend_level,
)
from rcm_mc.ui.cdd_scope_page import cdd_scope_csv, render_cdd_scope_page


class RegistryIntegrityTests(unittest.TestCase):
    def test_four_levels_fully_specified(self):
        self.assertEqual([lv["key"] for lv in CDD_LEVELS],
                         ["l1", "l2", "l3", "l4"])
        for lv in CDD_LEVELS:
            for field in ("label", "when", "duration", "team",
                          "decision", "deliverable", "calls", "note"):
                self.assertTrue(lv.get(field), f"{lv['key']}.{field}")
            # Durations are convention, never a quote — say so.
            self.assertIn("market convention", lv["duration"])

    def test_matrix_covers_every_cell_with_valid_depths(self):
        for ws in WORKSTREAMS:
            self.assertIn(ws["key"], DEPTH_MATRIX)
            for lv in CDD_LEVELS:
                self.assertIn(depth_for(ws["key"], lv["key"]), DEPTHS)

    def test_depth_monotone_l1_to_l3(self):
        # A deeper engagement never does LESS of a workstream.
        rank = {d: i for i, d in enumerate(DEPTHS)}
        for ws in WORKSTREAMS:
            seq = [rank[depth_for(ws["key"], k)]
                   for k in ("l1", "l2", "l3")]
            self.assertEqual(seq, sorted(seq),
                             f"{ws['key']} depth regresses: {seq}")
            # Full-scope runs everything.
            self.assertEqual(depth_for(ws["key"], "l3"), FULL)

    def test_l4_is_confirmatory_never_full(self):
        for ws in WORKSTREAMS:
            self.assertNotEqual(depth_for(ws["key"], "l4"), FULL,
                                f"{ws['key']} re-runs full at L4")

    def test_every_workstream_surface_route_is_served(self):
        import pathlib
        src = (pathlib.Path(__file__).resolve().parents[1]
               / "rcm_mc" / "server.py").read_text()
        for ws in WORKSTREAMS:
            self.assertIn(f'"{ws["surface"]}"', src,
                          f"{ws['surface']} not served")

    def test_call_program_sizes_scale_with_depth(self):
        calls = {lv["key"]: lv["calls"] for lv in CDD_LEVELS}
        self.assertLess(calls["l1"], calls["l2"])
        self.assertLess(calls["l2"], calls["l3"])
        self.assertLess(calls["l4"], calls["l3"])   # bring-down narrows


class RecommenderTests(unittest.TestCase):
    def test_stage_anchors_the_level(self):
        self.assertEqual(recommend_level("screen", "new", "platform")
                         ["level"]["key"], "l1")
        self.assertEqual(recommend_level("bid", "adjacent", "platform")
                         ["level"]["key"], "l2")
        self.assertEqual(recommend_level("exclusivity", "new",
                                         "platform")["level"]["key"],
                         "l3")
        self.assertEqual(recommend_level("preclose", "known", "addon")
                         ["level"]["key"], "l4")

    def test_known_market_addon_at_exclusivity_right_sizes(self):
        rec = recommend_level("exclusivity", "known", "addon")
        self.assertEqual(rec["level"]["key"], "l2")
        self.assertIn("duplicates the platform", rec["reason"])
        # But an unfamiliar add-on still gets the full build.
        self.assertEqual(recommend_level("exclusivity", "new", "addon")
                         ["level"]["key"], "l3")

    def test_every_recommendation_states_its_reason(self):
        from rcm_mc.diligence.cdd_scope import (
            STAGES, FAMILIARITY, DEAL_TYPES)
        for s in STAGES:
            for f in FAMILIARITY:
                for d in DEAL_TYPES:
                    rec = recommend_level(s, f, d)
                    self.assertTrue(rec and rec["reason"],
                                    f"no reason for {s}/{f}/{d}")

    def test_invalid_inputs_return_none_never_a_guess(self):
        self.assertIsNone(recommend_level("ipo", "new", "platform"))
        self.assertIsNone(recommend_level("bid", "expert", "platform"))
        self.assertIsNone(recommend_level("bid", "new", "carveout"))
        self.assertIsNone(recommend_level("", "", ""))


class TaskListTests(unittest.TestCase):
    def test_task_list_matches_matrix(self):
        for lv in CDD_LEVELS:
            tasks = level_task_list(lv["key"])
            expect = [w for w in WORKSTREAMS
                      if depth_for(w["key"], lv["key"]) != NONE]
            self.assertEqual(len(tasks), len(expect), lv["key"])
            for t in tasks:
                self.assertTrue(t["task"],
                                f"{lv['key']}: {t['workstream']} has "
                                f"a depth but no task text")
                self.assertTrue(t["surface"].startswith("/"))

    def test_unknown_level_returns_empty(self):
        self.assertEqual(level_task_list("l9"), [])
        self.assertIsNone(level("l9"))

    def test_csv_export_shape_and_fallback(self):
        out = cdd_scope_csv({"level": ["l2"]})
        self.assertIn("L2 · Red-flag CDD", out)
        self.assertIn("market convention", out)
        self.assertIn("Workstream,Depth,Task,Platform surface", out)
        n_rows = sum(1 for line in out.splitlines()
                     if line.startswith(("Market", "Demand",
                                         "Competitive", "Target",
                                         "Voice", "Management",
                                         "Pricing", "Regulatory",
                                         "Synthesis")))
        self.assertEqual(n_rows, len(level_task_list("l2")))
        # Unknown level falls back to the full-scope list, never 500s.
        self.assertIn("L3 · Full-scope CDD", cdd_scope_csv(
            {"level": ["bogus"]}))


class CddScopePageTests(unittest.TestCase):
    def test_page_renders_levels_matrix_and_tasks(self):
        page = render_cdd_scope_page({})
        for needle in ("CDD Scope", "L1 · Desktop screen",
                       "L4 · Confirmatory / bring-down",
                       "WORKSTREAM × LEVEL",
                       "TASK LIST — L3 · FULL-SCOPE CDD",
                       "/api/diligence/cdd-scope.csv?level=l3",
                       "/diligence/expert-calls?n=20",
                       "market convention"):
            self.assertIn(needle, page, f"missing: {needle}")

    def test_recommender_drives_selection_and_states_reason(self):
        page = render_cdd_scope_page(
            {"stage": ["exclusivity"], "familiarity": ["known"],
             "type": ["addon"]})
        self.assertIn("Recommended:", page)
        self.assertIn("L2 · Red-flag CDD", page)
        self.assertIn("duplicates the platform", page)
        self.assertIn("TASK LIST — L2 · RED-FLAG CDD", page)

    def test_partial_inputs_never_guess(self):
        page = render_cdd_scope_page({"stage": ["bid"]})
        self.assertNotIn("Recommended:", page)
        self.assertIn("never guesses", page)

    def test_hostile_level_falls_back(self):
        page = render_cdd_scope_page({"level": ["<script>"]})
        self.assertIn("TASK LIST — L3", page)
        self.assertNotIn("<script>alert", page)


class WiringTests(unittest.TestCase):
    def test_palette_section_map_and_catalog(self):
        from rcm_mc.ui._chartis_kit import (
            _DEFAULT_PALETTE_MODULES, _SUB_SECTION_MAP)
        self.assertIn("/diligence/cdd-scope",
                      [m["route"] for m in _DEFAULT_PALETTE_MODULES])
        self.assertEqual(_SUB_SECTION_MAP.get("/diligence/cdd-scope"),
                         "diligence")
        from rcm_mc.ui.diligence_index_page import render_diligence_index
        self.assertIn("/diligence/cdd-scope", render_diligence_index())

    def test_guide_context_registered_with_floor(self):
        from rcm_mc.assistant.context.manual_page_contexts import (
            MANUAL_PAGE_CONTEXTS)
        from rcm_mc.assistant.context.discovered_tool_routes import (
            DISCOVERED_TOOL_ROUTES)
        ctx = MANUAL_PAGE_CONTEXTS.get("/diligence/cdd-scope")
        self.assertIsNotNone(ctx)
        self.assertGreaterEqual(len(ctx.common_questions), 5)
        self.assertTrue(ctx.related_routes)
        self.assertIn("/diligence/cdd-scope",
                      [t.route for t in DISCOVERED_TOOL_ROUTES])

    def test_surface_status_classified(self):
        from rcm_mc.diligence.surface_status import classify_surface
        self.assertEqual(
            classify_surface("/diligence/cdd-scope")["tier"], "navy")


if __name__ == "__main__":
    unittest.main()
