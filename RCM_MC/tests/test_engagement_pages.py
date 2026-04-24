"""Engagement UI renderer regression tests.

Scope: string-level checks on the three HTML surfaces exposed at
``/engagements``, ``/engagements/<eid>``, ``/portal/<eid>``. The
viewer-filtering contract is already tested at the store level in
``test_engagement.py``; this file verifies the UI honours those
filters in what it actually renders.

Invariants:
- List view renders all engagements with clickable IDs
- Detail view shows members + deliverables + comments, including
  internal-flagged comments (for PARTNER/LEAD/ANALYST viewers)
- Portal view (same data, CLIENT_VIEWER-filtered) suppresses
  DRAFT deliverables + internal-flagged comments
- Empty-state messages render instead of an empty table
"""
from __future__ import annotations

import os
import tempfile
import unittest

from rcm_mc.engagement import (
    EngagementRole, add_member, create_deliverable, create_engagement,
    get_engagement, list_comments, list_deliverables, list_engagements,
    list_members, post_comment, publish_deliverable,
)
from rcm_mc.engagement.store import get_member_role
from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.ui.engagement_pages import (
    render_client_portal, render_engagement_detail,
    render_engagement_list,
)


def _store(tmp: str) -> PortfolioStore:
    return PortfolioStore(os.path.join(tmp, "p.db"))


def _seed(tmp: str) -> PortfolioStore:
    store = _store(tmp)
    create_engagement(
        store, engagement_id="E1", name="Project Aurora",
        client_name="Aurora Health", created_by="admin",
    )
    add_member(store, engagement_id="E1", username="partner",
               role=EngagementRole.PARTNER, added_by="admin")
    add_member(store, engagement_id="E1", username="analyst",
               role=EngagementRole.ANALYST, added_by="admin")
    add_member(store, engagement_id="E1", username="client",
               role=EngagementRole.CLIENT_VIEWER, added_by="admin")
    d_pub = create_deliverable(
        store, engagement_id="E1", kind="QOE_MEMO",
        title="Published QoE", created_by="analyst",
    )
    publish_deliverable(
        store, engagement_id="E1",
        deliverable_id=d_pub.deliverable_id,
        published_by="partner",
    )
    create_deliverable(
        store, engagement_id="E1", kind="BENCHMARKS",
        title="Draft Bench", created_by="analyst",
    )
    post_comment(
        store, engagement_id="E1",
        target=f"deliverable:{d_pub.deliverable_id}",
        author="partner", body="Client-visible note",
        is_internal=False,
    )
    post_comment(
        store, engagement_id="E1",
        target=f"deliverable:{d_pub.deliverable_id}",
        author="partner", body="Internal debate",
        is_internal=True,
    )
    return store


class EngagementListPageTests(unittest.TestCase):

    def test_renders_engagement_row_with_click_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed(tmp)
            html = render_engagement_list(list_engagements(store))
            self.assertIn("Project Aurora", html)
            self.assertIn("Aurora Health", html)
            self.assertIn('href="/engagements/E1"', html)
            self.assertIn("E1", html)

    def test_empty_list_shows_friendly_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            html = render_engagement_list(list_engagements(store))
            self.assertIn("No engagements", html)


class EngagementDetailPageTests(unittest.TestCase):

    def test_internal_viewer_sees_drafts_and_internal_comments(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed(tmp)
            eng = get_engagement(store, "E1")
            html = render_engagement_detail(
                eng,
                members=list_members(store, "E1"),
                deliverables=list_deliverables(
                    store, engagement_id="E1", viewer="partner",
                ),
                comments=list_comments(
                    store, engagement_id="E1", viewer="partner",
                ),
                viewer_role=get_member_role(
                    store, engagement_id="E1", username="partner",
                ),
            )
            self.assertIn("Published QoE", html)
            self.assertIn("Draft Bench", html)
            self.assertIn("Internal debate", html)
            self.assertIn("PARTNER", html)

    def test_renders_status_badges(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed(tmp)
            eng = get_engagement(store, "E1")
            html = render_engagement_detail(
                eng,
                members=list_members(store, "E1"),
                deliverables=list_deliverables(
                    store, engagement_id="E1", viewer="partner",
                ),
                comments=list_comments(
                    store, engagement_id="E1", viewer="partner",
                ),
            )
            self.assertIn("PUBLISHED", html)
            self.assertIn("DRAFT", html)
            self.assertIn("ACTIVE", html)


class ClientPortalPageTests(unittest.TestCase):

    def test_client_sees_only_published_and_non_internal(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed(tmp)
            eng = get_engagement(store, "E1")
            html = render_client_portal(
                eng,
                deliverables=list_deliverables(
                    store, engagement_id="E1", viewer="client",
                ),
                comments=list_comments(
                    store, engagement_id="E1", viewer="client",
                ),
            )
            self.assertIn("Published QoE", html)
            self.assertIn("Client-visible note", html)
            # Drafts filtered out
            self.assertNotIn("Draft Bench", html)
            # Internal-flagged comments filtered out
            self.assertNotIn("Internal debate", html)

    def test_portal_page_title_and_eyebrow(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed(tmp)
            eng = get_engagement(store, "E1")
            html = render_client_portal(
                eng,
                deliverables=list_deliverables(
                    store, engagement_id="E1", viewer="client",
                ),
                comments=list_comments(
                    store, engagement_id="E1", viewer="client",
                ),
            )
            self.assertIn("Client Portal", html)
            self.assertIn("Project Aurora", html)
            self.assertIn("Aurora Health", html)


if __name__ == "__main__":
    unittest.main()
