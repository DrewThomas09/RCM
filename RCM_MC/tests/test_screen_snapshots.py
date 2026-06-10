"""P9 — vintage-diff snapshots of saved screens.

The diff must be honest: sub-threshold numeric wiggle (re-vendored files
round differently) is NOT a change; entered/left/ownership-flip/≥5%-moves
are. Storage is owner-scoped like saved_screens; snapshots die with their
screen (explicit cleanup — no FK chain).
"""
from __future__ import annotations

import os
import tempfile
import unittest

from rcm_mc.portfolio.saved_screens import save_screen
from rcm_mc.portfolio.screen_snapshots import (
    delete_snapshots_for_screen, diff_results, diff_summary,
    latest_snapshot, take_snapshot,
)
from rcm_mc.portfolio.store import PortfolioStore


def _row(name="ALPHA GENERAL", state="TX", own="Voluntary", size=200.0,
         q=0.05):
    return {"name": name, "state": state, "ownership": own,
            "size": size, "q": q}


class DiffTests(unittest.TestCase):
    def test_entered_and_left(self):
        d = diff_results({"a": _row(), "b": _row(name="BRAVO")},
                         {"b": _row(name="BRAVO"), "c": _row(name="CHARLIE")})
        self.assertEqual([e["ccn"] for e in d["entered"]], ["c"])
        self.assertEqual([e["ccn"] for e in d["left"]], ["a"])
        self.assertEqual(d["changed"], [])

    def test_subthreshold_wiggle_is_not_a_change(self):
        # 200 → 204 beds = 2% — rounding noise, not a finding.
        d = diff_results({"a": _row(size=200.0)}, {"a": _row(size=204.0)})
        self.assertEqual(d["changed"], [])

    def test_five_percent_move_is_a_change(self):
        d = diff_results({"a": _row(size=200.0)}, {"a": _row(size=212.0)})
        self.assertEqual(len(d["changed"]), 1)
        self.assertEqual(d["changed"][0]["field"], "size")

    def test_ownership_flip_is_a_change(self):
        d = diff_results({"a": _row(own="Voluntary")},
                         {"a": _row(own="Proprietary")})
        fields = [c["field"] for c in d["changed"]]
        self.assertIn("ownership", fields)

    def test_newly_reported_value_is_a_change(self):
        d = diff_results({"a": _row(q=None)}, {"a": _row(q=0.07)})
        self.assertEqual([c["field"] for c in d["changed"]], ["q"])
        self.assertEqual(d["changed"][0]["old"], "—")

    def test_summary_line_and_silence(self):
        d = diff_results({"a": _row(), "b": _row()},
                         {"a": _row(own="Proprietary"), "c": _row()})
        s = diff_summary(d)
        self.assertIn("+1 entered", s)
        self.assertIn("−1 left", s)
        self.assertIn("1 changed", s)
        # identical snapshots → empty summary (the card renders "no change")
        self.assertEqual(diff_summary(diff_results({"a": _row()},
                                                   {"a": _row()})), "")


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = PortfolioStore(os.path.join(self.tmp.name, "s.db"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_round_trip_owner_scoped(self):
        sid = save_screen(self.store, "alice", "TX hospitals",
                          "view=main&vertical=hospitals&state=TX")
        take_snapshot(self.store, "alice", sid, {"450358": _row()})
        snap = latest_snapshot(self.store, "alice", sid)
        self.assertIsNotNone(snap)
        self.assertIn("450358", snap["results"])
        # bob sees nothing
        self.assertIsNone(latest_snapshot(self.store, "bob", sid))

    def test_latest_wins(self):
        sid = save_screen(self.store, "a", "t", "view=main")
        take_snapshot(self.store, "a", sid, {"x": _row(size=100)})
        take_snapshot(self.store, "a", sid, {"x": _row(size=300)})
        snap = latest_snapshot(self.store, "a", sid)
        self.assertEqual(snap["results"]["x"]["size"], 300)

    def test_delete_cleanup(self):
        sid = save_screen(self.store, "a", "t", "view=main")
        take_snapshot(self.store, "a", sid, {"x": _row()})
        n = delete_snapshots_for_screen(self.store, "a", sid)
        self.assertEqual(n, 1)
        self.assertIsNone(latest_snapshot(self.store, "a", sid))


class CurrentResultsTests(unittest.TestCase):
    def test_same_filter_semantics_as_table(self):
        # The snapshot path reuses the page's loaders + filters — a min_size
        # screen returns only rows meeting it, keyed by CCN.
        from rcm_mc.ui.target_screener_page import screen_results_for_params
        res = screen_results_for_params(
            "view=main&vertical=hospitals&state=TX&min_size=500")
        self.assertGreater(len(res), 0)
        for ccn, r in res.items():
            self.assertEqual(r["state"], "TX")
            self.assertGreaterEqual(r["size"], 500)
            self.assertTrue(ccn)

    def test_diff_of_screen_against_itself_is_empty(self):
        # Re-vendored-data honesty baseline: same params, same data → no
        # entered/left/changed. If this fires, the diff would cry wolf.
        from rcm_mc.ui.target_screener_page import screen_results_for_params
        a = screen_results_for_params("view=main&vertical=hospitals&state=AK")
        b = screen_results_for_params("view=main&vertical=hospitals&state=AK")
        d = diff_results(a, b)
        self.assertEqual((d["entered"], d["left"], d["changed"]),
                         ([], [], []))


class SavedTabRenderTests(unittest.TestCase):
    def test_diff_line_and_snapshot_button_render(self):
        from rcm_mc.ui.target_screener_page import render_target_screener
        saved = [{"id": 7, "title": "TX hospitals",
                  "query_params": "view=main&vertical=hospitals&state=TX",
                  "created_at": "2026-06-01T00:00:00+00:00"}]
        h = render_target_screener(
            {"view": ["saved"]}, saved=saved, owner="alice",
            snap_info={7: {"taken_at": "2026-06-01T00:00:00+00:00",
                           "summary": "+2 entered · 1 changed"}})
        self.assertIn("since 2026-06-01", h)
        self.assertIn("+2 entered", h)
        self.assertIn("re-baseline", h)
        self.assertIn("/api/target-screener/snapshot", h)

    def test_no_snapshot_offers_snapshot_action(self):
        from rcm_mc.ui.target_screener_page import render_target_screener
        saved = [{"id": 7, "title": "T",
                  "query_params": "view=main",
                  "created_at": "2026-06-01T00:00:00+00:00"}]
        h = render_target_screener({"view": ["saved"]}, saved=saved,
                                   owner="alice", snap_info={})
        self.assertIn(">snapshot<", h)
        self.assertNotIn("since 2026", h)

    def test_empty_diff_renders_no_change(self):
        from rcm_mc.ui.target_screener_page import render_target_screener
        saved = [{"id": 7, "title": "T", "query_params": "view=main",
                  "created_at": "2026-06-01T00:00:00+00:00"}]
        h = render_target_screener(
            {"view": ["saved"]}, saved=saved, owner="alice",
            snap_info={7: {"taken_at": "2026-06-05T00:00:00+00:00",
                           "summary": ""}})
        self.assertIn("no change", h)


class DiffDetailViewTests(unittest.TestCase):
    """P9 slice-2 — ?diff=<id> opens row-level entered/left/changed detail."""

    def _detail(self, diff, title="TX watch"):
        from rcm_mc.ui.target_screener_page import render_target_screener
        saved = [{"id": 7, "title": title, "query_params": "view=main",
                  "created_at": "2026-06-01T00:00:00+00:00"}]
        return render_target_screener(
            {"view": ["saved"]}, saved=saved, owner="alice",
            snap_info={7: {"taken_at": "2026-06-01T00:00:00+00:00",
                           "summary": "+1 entered"}},
            diff_detail={"screen_id": 7, "title": title,
                         "taken_at": "2026-06-01T00:00:00+00:00",
                         "diff": diff})

    def test_detail_lists_rows_with_old_new(self):
        h = self._detail({
            "entered": [{"ccn": "450099", "name": "NEWCOMER GENERAL"}],
            "left": [{"ccn": "450001", "name": "DEPARTED MEMORIAL"}],
            "changed": [{"ccn": "450358", "name": "THE METHODIST HOSPITAL",
                         "field": "ownership", "old": "Voluntary",
                         "new": "Proprietary"}]})
        self.assertIn("ENTERED THE SCREEN (1)", h)
        self.assertIn("NEWCOMER GENERAL", h)
        self.assertIn("LEFT THE SCREEN (1)", h)
        self.assertIn("DEPARTED MEMORIAL", h)
        self.assertIn("Voluntary", h)
        self.assertIn("Proprietary", h)
        self.assertIn("hcris-xray?ccn=450358", h)   # drill links

    def test_empty_diff_states_thresholds(self):
        h = self._detail({"entered": [], "left": [], "changed": []})
        self.assertIn("No changes", h)
        self.assertIn("5% relative", h)             # thresholds stated

    def test_hostile_screen_title_is_escaped(self):
        h = self._detail({"entered": [], "left": [], "changed": []},
                         title='<img src=x onerror=alert(1)>')
        self.assertNotIn("<img src=x", h)

    def test_diff_line_links_to_detail(self):
        from rcm_mc.ui.target_screener_page import render_target_screener
        saved = [{"id": 7, "title": "T", "query_params": "view=main",
                  "created_at": "2026-06-01T00:00:00+00:00"}]
        h = render_target_screener(
            {"view": ["saved"]}, saved=saved, owner="alice",
            snap_info={7: {"taken_at": "2026-06-01T00:00:00+00:00",
                           "summary": "+2 entered"}})
        self.assertIn("view=saved&diff=7", h)


class XrayDrillRoutingTests(unittest.TestCase):
    """The per-row X-Ray button must route by vertical: hospitals into the
    rich HCRIS X-Ray (filed financials), every other CMS vertical into the
    generic provider scanner. A hospital row pointing at /diligence/xray
    landed the partner on the wrong page (the user-reported bug)."""

    def test_hospital_rows_link_to_hcris_xray(self):
        import re
        from rcm_mc.ui.target_screener_page import render_target_screener
        h = render_target_screener(
            {"view": ["main"], "vertical": ["hospitals"], "state": ["AK"]})
        # X-Ray buttons on hospital rows go to the HCRIS X-Ray …
        self.assertRegex(h, r'href="/diligence/hcris-xray\?ccn=\w+"')
        # … and NOT the generic provider scanner.
        self.assertNotRegex(
            h, r'href="/diligence/xray\?ccn=\w+&vertical=hospitals"')

    def test_nonhospital_rows_keep_generic_xray(self):
        from rcm_mc.ui.target_screener_page import render_target_screener
        h = render_target_screener(
            {"view": ["main"], "vertical": ["home_health"], "state": ["CA"]})
        self.assertRegex(
            h, r'href="/diligence/xray\?ccn=\w+&vertical=home_health"')


if __name__ == "__main__":
    unittest.main()
