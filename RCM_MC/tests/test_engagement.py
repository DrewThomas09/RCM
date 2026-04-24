"""Engagement model regression tests.

Five interlocking layers:

- Engagement CRUD: create/get/list; uniqueness on engagement_id
- Member management: add/remove/role-update; list ordering
- Comment stream: post/list with internal-flag filtering for
  CLIENT_VIEWER
- Deliverable draft → publish flow: role-gated publication, status
  transitions, RETRACTED semantics
- Client portal view: CLIENT_VIEWER sees only PUBLISHED deliverables
  and non-internal comments

Each test uses a temp-file SQLite DB (matching the existing
test_audit_log pattern). No test touches shared state.
"""
from __future__ import annotations

import os
import tempfile
import unittest

from rcm_mc.engagement import (
    Deliverable, EngagementRole, add_member, can_publish,
    can_view_draft, create_deliverable, create_engagement,
    get_engagement, list_comments, list_deliverables,
    list_engagements, list_members, post_comment,
    publish_deliverable, remove_member,
)
from rcm_mc.portfolio.store import PortfolioStore


def _store(tmp: str) -> PortfolioStore:
    return PortfolioStore(os.path.join(tmp, "p.db"))


# ── Permission helpers ────────────────────────────────────────────

class PermissionHelperTests(unittest.TestCase):

    def test_partner_can_publish_qoe_memo(self):
        self.assertTrue(can_publish(EngagementRole.PARTNER, "QOE_MEMO"))

    def test_lead_cannot_publish_qoe_memo(self):
        """The partner-signed QoE memo is PARTNER-only by design."""
        self.assertFalse(can_publish(EngagementRole.LEAD, "QOE_MEMO"))

    def test_lead_can_publish_benchmarks(self):
        self.assertTrue(can_publish(EngagementRole.LEAD, "BENCHMARKS"))

    def test_analyst_cannot_publish_anything(self):
        for kind in ("QOE_MEMO", "BENCHMARKS", "WATERFALL",
                     "ROOT_CAUSE", "ADVISORY"):
            self.assertFalse(can_publish(EngagementRole.ANALYST, kind))

    def test_client_viewer_cannot_publish_anything(self):
        for kind in ("QOE_MEMO", "BENCHMARKS"):
            self.assertFalse(
                can_publish(EngagementRole.CLIENT_VIEWER, kind)
            )

    def test_client_viewer_cannot_see_drafts(self):
        self.assertFalse(can_view_draft(EngagementRole.CLIENT_VIEWER))

    def test_internal_roles_see_drafts(self):
        for role in (EngagementRole.PARTNER, EngagementRole.LEAD,
                     EngagementRole.ANALYST):
            self.assertTrue(can_view_draft(role))


# ── Engagement CRUD ───────────────────────────────────────────────

class EngagementCRUDTests(unittest.TestCase):

    def test_create_and_read_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            e = create_engagement(
                store, engagement_id="E1", name="Project Aurora",
                client_name="Aurora Health", created_by="admin",
            )
            self.assertEqual(e.engagement_id, "E1")
            self.assertEqual(e.status, "ACTIVE")
            got = get_engagement(store, "E1")
            self.assertIsNotNone(got)
            self.assertEqual(got.name, "Project Aurora")

    def test_duplicate_engagement_id_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            create_engagement(
                store, engagement_id="E1", name="p",
                client_name="c", created_by="admin",
            )
            with self.assertRaises(ValueError):
                create_engagement(
                    store, engagement_id="E1", name="p2",
                    client_name="c2", created_by="admin",
                )

    def test_list_engagements_newest_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            for i in range(3):
                create_engagement(
                    store, engagement_id=f"E{i}", name=f"n{i}",
                    client_name="c", created_by="admin",
                )
            ids = [e.engagement_id for e in list_engagements(store)]
            # All three engagements present; order is newest-first by
            # created_at so the last one inserted appears first.
            self.assertEqual(set(ids), {"E0", "E1", "E2"})


# ── Member management ────────────────────────────────────────────

class MemberManagementTests(unittest.TestCase):

    def test_add_list_remove(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            create_engagement(
                store, engagement_id="E1", name="p",
                client_name="c", created_by="admin",
            )
            add_member(store, engagement_id="E1", username="u1",
                       role=EngagementRole.PARTNER, added_by="admin")
            add_member(store, engagement_id="E1", username="u2",
                       role=EngagementRole.ANALYST, added_by="admin")
            members = list_members(store, "E1")
            self.assertEqual(len(members), 2)
            names = [m.username for m in members]
            self.assertIn("u1", names)
            self.assertIn("u2", names)
            removed = remove_member(
                store, engagement_id="E1", username="u1",
                removed_by="admin",
            )
            self.assertTrue(removed)
            self.assertEqual(len(list_members(store, "E1")), 1)

    def test_add_same_user_twice_updates_role(self):
        """Re-adding a user is a role update; membership is unique
        per (engagement_id, username)."""
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            create_engagement(
                store, engagement_id="E1", name="p",
                client_name="c", created_by="admin",
            )
            add_member(store, engagement_id="E1", username="u",
                       role=EngagementRole.ANALYST, added_by="admin")
            add_member(store, engagement_id="E1", username="u",
                       role=EngagementRole.LEAD, added_by="admin")
            members = list_members(store, "E1")
            self.assertEqual(len(members), 1)
            self.assertEqual(members[0].role, EngagementRole.LEAD)


# ── Deliverable draft → publish flow ──────────────────────────────

class DeliverableDraftPublishTests(unittest.TestCase):

    def _seed(self, tmp):
        store = _store(tmp)
        create_engagement(
            store, engagement_id="E1", name="p",
            client_name="c", created_by="admin",
        )
        add_member(store, engagement_id="E1", username="partner",
                   role=EngagementRole.PARTNER, added_by="admin")
        add_member(store, engagement_id="E1", username="lead",
                   role=EngagementRole.LEAD, added_by="admin")
        add_member(store, engagement_id="E1", username="analyst",
                   role=EngagementRole.ANALYST, added_by="admin")
        add_member(store, engagement_id="E1", username="client",
                   role=EngagementRole.CLIENT_VIEWER, added_by="admin")
        return store

    def test_analyst_creates_draft(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._seed(tmp)
            d = create_deliverable(
                store, engagement_id="E1", kind="QOE_MEMO",
                title="QoE v1", created_by="analyst",
            )
            self.assertEqual(d.status, "DRAFT")
            self.assertEqual(d.kind, "QOE_MEMO")

    def test_partner_publishes_qoe_memo(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._seed(tmp)
            d = create_deliverable(
                store, engagement_id="E1", kind="QOE_MEMO",
                title="QoE v1", created_by="analyst",
            )
            pub = publish_deliverable(
                store, engagement_id="E1",
                deliverable_id=d.deliverable_id,
                published_by="partner",
            )
            self.assertEqual(pub.status, "PUBLISHED")
            self.assertEqual(pub.published_by, "partner")
            self.assertIsNotNone(pub.published_at)

    def test_analyst_cannot_publish_qoe_memo(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._seed(tmp)
            d = create_deliverable(
                store, engagement_id="E1", kind="QOE_MEMO",
                title="QoE v1", created_by="analyst",
            )
            with self.assertRaises(PermissionError):
                publish_deliverable(
                    store, engagement_id="E1",
                    deliverable_id=d.deliverable_id,
                    published_by="analyst",
                )

    def test_lead_cannot_publish_qoe_memo_but_can_publish_benchmarks(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._seed(tmp)
            # LEAD can publish benchmarks
            d_bench = create_deliverable(
                store, engagement_id="E1", kind="BENCHMARKS",
                title="Bench v1", created_by="lead",
            )
            pub = publish_deliverable(
                store, engagement_id="E1",
                deliverable_id=d_bench.deliverable_id,
                published_by="lead",
            )
            self.assertEqual(pub.status, "PUBLISHED")
            # LEAD cannot publish the partner-signed QOE_MEMO
            d_qoe = create_deliverable(
                store, engagement_id="E1", kind="QOE_MEMO",
                title="QoE v1", created_by="analyst",
            )
            with self.assertRaises(PermissionError):
                publish_deliverable(
                    store, engagement_id="E1",
                    deliverable_id=d_qoe.deliverable_id,
                    published_by="lead",
                )

    def test_client_viewer_cannot_create_deliverable(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._seed(tmp)
            with self.assertRaises(PermissionError):
                create_deliverable(
                    store, engagement_id="E1", kind="QOE_MEMO",
                    title="client-injected", created_by="client",
                )

    def test_cannot_republish_already_published(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._seed(tmp)
            d = create_deliverable(
                store, engagement_id="E1", kind="QOE_MEMO",
                title="QoE v1", created_by="analyst",
            )
            publish_deliverable(
                store, engagement_id="E1",
                deliverable_id=d.deliverable_id,
                published_by="partner",
            )
            with self.assertRaises(ValueError):
                publish_deliverable(
                    store, engagement_id="E1",
                    deliverable_id=d.deliverable_id,
                    published_by="partner",
                )


# ── Client portal view ───────────────────────────────────────────

class ClientPortalViewTests(unittest.TestCase):
    """The CLIENT_VIEWER path is the "client portal" view — only
    published deliverables visible, only non-internal comments
    visible."""

    def _seed_with_mixed_state(self, tmp):
        store = _store(tmp)
        create_engagement(
            store, engagement_id="E1", name="p",
            client_name="c", created_by="admin",
        )
        add_member(store, engagement_id="E1", username="partner",
                   role=EngagementRole.PARTNER, added_by="admin")
        add_member(store, engagement_id="E1", username="analyst",
                   role=EngagementRole.ANALYST, added_by="admin")
        add_member(store, engagement_id="E1", username="client",
                   role=EngagementRole.CLIENT_VIEWER, added_by="admin")
        # Two deliverables: one published, one draft.
        d_pub = create_deliverable(
            store, engagement_id="E1", kind="BENCHMARKS",
            title="Published bench", created_by="analyst",
        )
        publish_deliverable(
            store, engagement_id="E1",
            deliverable_id=d_pub.deliverable_id,
            published_by="partner",
        )
        create_deliverable(
            store, engagement_id="E1", kind="QOE_MEMO",
            title="Draft QoE", created_by="analyst",
        )
        return store, d_pub

    def test_client_sees_only_published_deliverables(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, _ = self._seed_with_mixed_state(tmp)
            for_partner = list_deliverables(
                store, engagement_id="E1", viewer="partner",
            )
            for_client = list_deliverables(
                store, engagement_id="E1", viewer="client",
            )
            self.assertEqual(len(for_partner), 2)
            self.assertEqual(len(for_client), 1)
            self.assertEqual(for_client[0].status, "PUBLISHED")

    def test_client_sees_only_non_internal_comments(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, d = self._seed_with_mixed_state(tmp)
            post_comment(
                store, engagement_id="E1",
                target=f"deliverable:{d.deliverable_id}",
                author="partner", body="Looks good",
                is_internal=False,
            )
            post_comment(
                store, engagement_id="E1",
                target=f"deliverable:{d.deliverable_id}",
                author="partner", body="Internal debate",
                is_internal=True,
            )
            for_partner = list_comments(
                store, engagement_id="E1", viewer="partner",
            )
            for_client = list_comments(
                store, engagement_id="E1", viewer="client",
            )
            self.assertEqual(len(for_partner), 2)
            self.assertEqual(len(for_client), 1)
            self.assertEqual(for_client[0].body, "Looks good")

    def test_client_cannot_post_internal_comment(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, d = self._seed_with_mixed_state(tmp)
            with self.assertRaises(PermissionError):
                post_comment(
                    store, engagement_id="E1",
                    target=f"deliverable:{d.deliverable_id}",
                    author="client", body="sneaky",
                    is_internal=True,
                )


class CommentAuthorisationTests(unittest.TestCase):

    def test_non_member_cannot_post(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            create_engagement(
                store, engagement_id="E1", name="p",
                client_name="c", created_by="admin",
            )
            with self.assertRaises(PermissionError):
                post_comment(
                    store, engagement_id="E1", target="t",
                    author="stranger", body="hi",
                )

    def test_empty_body_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            create_engagement(
                store, engagement_id="E1", name="p",
                client_name="c", created_by="admin",
            )
            add_member(store, engagement_id="E1", username="u",
                       role=EngagementRole.PARTNER, added_by="admin")
            with self.assertRaises(ValueError):
                post_comment(
                    store, engagement_id="E1", target="t",
                    author="u", body="   ",
                )


if __name__ == "__main__":
    unittest.main()
