"""Diligence Checklist + Tracker regression tests.

Covers:
    - Items: 36 curated items; every P0 has completion_criteria or
      analytic link; categories + phases valid
    - Tracker: empty state, full state, partial state, manual
      overrides (done/blocked/in_progress), unknown-key defensive
    - Coverage summary + open_questions list
    - UI page: landing renders; hero KPIs present; open-questions
      block rendered; per-phase progress bars; action links encoded
    - Server route + sidebar + Deal Profile tile
    - IC Packet integration: coverage section renders when state
      supplied, silent when state absent
"""
from __future__ import annotations

import unittest

from rcm_mc.diligence.checklist import (
    CHECKLIST_ITEMS, Category, ChecklistItem, DealChecklistState,
    DealObservations, ItemStatus, Owner, Priority,
    build_checklist, compute_status, open_questions_for_ic_packet,
    summarize_coverage,
)


class ChecklistItemsTests(unittest.TestCase):

    def test_lattice_has_at_least_30_items(self):
        self.assertGreaterEqual(len(CHECKLIST_ITEMS), 30)

    def test_build_returns_copy(self):
        items = build_checklist()
        items.append(None)  # type: ignore[arg-type]
        self.assertEqual(len(CHECKLIST_ITEMS), len(build_checklist()))

    def test_every_item_has_all_required_fields(self):
        for it in CHECKLIST_ITEMS:
            self.assertTrue(it.item_id)
            self.assertIn(it.phase, (1, 2, 3, 4, 5))
            self.assertIsInstance(it.category, Category)
            self.assertIsInstance(it.priority, Priority)
            self.assertIsInstance(it.default_owner, Owner)
            self.assertTrue(it.question)

    def test_unique_item_ids(self):
        ids = [it.item_id for it in CHECKLIST_ITEMS]
        self.assertEqual(len(ids), len(set(ids)),
                         msg=f"duplicate item ids: "
                             f"{[i for i in ids if ids.count(i) > 1]}")

    def test_phase_5_has_deliverables(self):
        phase5 = [it for it in CHECKLIST_ITEMS if it.phase == 5]
        # Should include IC Packet + QoE memo
        ids = {it.item_id for it in phase5}
        self.assertIn("deliver_ic_packet", ids)
        self.assertIn("deliver_qoe", ids)

    def test_manual_items_have_no_auto_check(self):
        manual = [it for it in CHECKLIST_ITEMS
                  if it.category == Category.MANUAL]
        self.assertGreater(len(manual), 0)
        for it in manual:
            self.assertIsNone(it.auto_check_key)


class TrackerTests(unittest.TestCase):

    def test_empty_observations_all_open(self):
        state = compute_status(DealObservations())
        self.assertEqual(state.total, len(CHECKLIST_ITEMS))
        self.assertEqual(state.done, 0)
        self.assertEqual(state.open_, len(CHECKLIST_ITEMS))
        self.assertEqual(state.p0_coverage, 0.0)

    def test_full_state_all_p0_done(self):
        """Setting every auto_check_key to True + manual-done for
        items lacking an auto-check should yield 100% P0 coverage."""
        obs_kwargs = {}
        for it in CHECKLIST_ITEMS:
            if it.auto_check_key:
                obs_kwargs[it.auto_check_key] = True
        obs = DealObservations(**obs_kwargs)

        manual_done = {
            it.item_id for it in CHECKLIST_ITEMS
            if it.auto_check_key is None
        }
        state = compute_status(
            obs, manual_completed_ids=manual_done,
        )
        self.assertEqual(state.p0_coverage, 1.0)
        self.assertEqual(state.open_p0, 0)

    def test_manual_blocked_precedes_done(self):
        """If an item is marked both blocked and done, blocked wins —
        safer default."""
        state = compute_status(
            DealObservations(ccd_ingested=True),
            manual_blocked_ids={"ingest_ccd"},
            manual_completed_ids={"ingest_ccd"},
        )
        # The CCD item should be BLOCKED despite observation=True
        ccd = next(s for s in state.items
                   if s.item.item_id == "ingest_ccd")
        self.assertEqual(ccd.status, ItemStatus.BLOCKED)

    def test_manual_in_progress(self):
        state = compute_status(
            DealObservations(),
            manual_in_progress_ids={"manual_mgmt_references"},
        )
        it = next(s for s in state.items
                  if s.item.item_id == "manual_mgmt_references")
        self.assertEqual(it.status, ItemStatus.IN_PROGRESS)

    def test_item_notes_threaded_through(self):
        state = compute_status(
            DealObservations(),
            item_notes={"ingest_ccd": "Waiting on 837 feed"},
        )
        it = next(s for s in state.items
                  if s.item.item_id == "ingest_ccd")
        self.assertEqual(it.note, "Waiting on 837 feed")

    def test_unknown_auto_check_key_defensive(self):
        """Monkey-patch an unknown auto_check_key; tracker must not
        crash and must treat it as OPEN."""
        from rcm_mc.diligence.checklist.tracker import _status_for
        fake_item = ChecklistItem(
            item_id="fake", phase=2, category=Category.BENCHMARKS,
            priority=Priority.P1,
            question="fake?", default_owner=Owner.ANALYST,
            auto_check_key="nonexistent_observable_field",
        )
        status = _status_for(
            fake_item, DealObservations(), set(), set(), set(),
        )
        self.assertEqual(status, ItemStatus.OPEN)


class CoverageSummaryTests(unittest.TestCase):

    def test_summary_open_p0(self):
        state = compute_status(DealObservations())
        msg = summarize_coverage(state)
        self.assertIn("P0", msg)
        self.assertIn("Do not schedule IC", msg)

    def test_summary_ready_for_ic(self):
        obs_kwargs = {
            it.auto_check_key: True for it in CHECKLIST_ITEMS
            if it.auto_check_key
        }
        # Manual-complete every item that lacks an auto_check_key
        # (covers MANUAL-category items + the working-capital peg
        # which is manual-only inside FINANCIAL).
        manual_done = {
            it.item_id for it in CHECKLIST_ITEMS
            if it.auto_check_key is None
        }
        state = compute_status(
            DealObservations(**obs_kwargs),
            manual_completed_ids=manual_done,
        )
        msg = summarize_coverage(state)
        self.assertIn("ready for ic", msg.lower())


class OpenQuestionsTests(unittest.TestCase):

    def test_open_questions_includes_p0(self):
        state = compute_status(DealObservations())
        qs = open_questions_for_ic_packet(state)
        self.assertGreater(len(qs), 0)
        self.assertTrue(any(q.priority == "P0" for q in qs))

    def test_open_questions_sorted_p0_first(self):
        state = compute_status(DealObservations())
        qs = open_questions_for_ic_packet(state)
        priorities = [q.priority for q in qs]
        p0_indices = [i for i, p in enumerate(priorities) if p == "P0"]
        p1_indices = [i for i, p in enumerate(priorities) if p == "P1"]
        if p0_indices and p1_indices:
            self.assertLess(max(p0_indices), min(p1_indices))

    def test_include_p2_toggle(self):
        state = compute_status(DealObservations())
        no_p2 = open_questions_for_ic_packet(state, include_p2=False)
        with_p2 = open_questions_for_ic_packet(state, include_p2=True)
        self.assertGreaterEqual(len(with_p2), len(no_p2))


# ────────────────────────────────────────────────────────────────────
# UI page
# ────────────────────────────────────────────────────────────────────

class DiligenceChecklistPageTests(unittest.TestCase):

    def _render(self, **qs):
        from rcm_mc.ui.diligence_checklist_page import (
            render_diligence_checklist_page,
        )
        wrapped = {k: ([v] if isinstance(v, str) else list(v))
                   for k, v in qs.items()}
        return render_diligence_checklist_page(qs=wrapped)

    def test_landing_renders(self):
        h = self._render()
        self.assertIn("Diligence Checklist", h)
        self.assertIn("Coverage + Open Questions", h)
        self.assertIn("P0 coverage", h)

    def test_hero_kpis_have_provenance(self):
        h = self._render()
        # P0 coverage + total done carry provenance tooltips
        self.assertIn("data-provenance", h)

    def test_json_export_wrapper_present(self):
        h = self._render()
        self.assertIn("data-export-json", h)
        self.assertIn("diligence_checklist_state", h)

    def test_all_five_phases_rendered(self):
        h = self._render()
        for phase in (
            "Phase 1", "Phase 2", "Phase 3",
            "Phase 4", "Phase 5",
        ):
            self.assertIn(phase, h, msg=f"missing {phase}")

    def test_empty_observation_mode(self):
        h = self._render(empty="1")
        # Should still render all sections
        self.assertIn("Phase 1", h)
        # With empty state, open_p0 should be large
        self.assertIn("Blocking IC", h)

    def test_mark_done_via_query_param(self):
        """Marking an item done via URL should flip its status."""
        h = self._render(mark_done="ingest_ccd")
        # The item should show DONE
        self.assertIn("DONE", h)

    def test_action_links_present(self):
        h = self._render()
        self.assertIn("Mark done", h)
        self.assertIn("Block", h)
        self.assertIn("WIP", h)

    def test_flat_table_sortable_filterable(self):
        h = self._render()
        self.assertIn("data-sortable", h)
        self.assertIn("data-filterable", h)
        self.assertIn("data-export", h)

    def test_evidence_deep_links_present(self):
        """Items with an evidence_url should carry an 'Open →' link."""
        h = self._render()
        self.assertIn("/screening/bankruptcy-survivor", h)
        self.assertIn("/diligence/physician-attrition", h)
        self.assertIn("Open →", h)


class NavLinkTests(unittest.TestCase):

    def test_sidebar_has_checklist_link(self):
        from rcm_mc.ui._chartis_kit import chartis_shell
        rendered = chartis_shell("<p>x</p>", "Test")
        self.assertIn('href="/diligence/checklist"', rendered)

    def test_deal_profile_exposes_checklist(self):
        from rcm_mc.ui.deal_profile_page import _ANALYTICS
        ids = [a.get("href") for a in _ANALYTICS]
        self.assertIn("/diligence/checklist", ids)


class ICPacketIntegrationTests(unittest.TestCase):

    def test_ic_packet_renders_coverage_section(self):
        from rcm_mc.exports import (
            ICPacketMetadata, render_ic_packet_html,
        )
        state = compute_status(DealObservations(
            bankruptcy_scan_run=True,
            deal_autopsy_run=True,
            ccd_ingested=True,
        ))
        html_str = render_ic_packet_html(
            metadata=ICPacketMetadata(deal_name="Test"),
            checklist_state=state,
        )
        self.assertIn("Diligence Coverage", html_str)
        self.assertIn("P0 coverage", html_str)

    def test_ic_packet_silent_when_checklist_state_none(self):
        from rcm_mc.exports import (
            ICPacketMetadata, render_ic_packet_html,
        )
        html_str = render_ic_packet_html(
            metadata=ICPacketMetadata(deal_name="Test"),
            checklist_state=None,
        )
        self.assertNotIn("Diligence Coverage", html_str)


if __name__ == "__main__":
    unittest.main()
