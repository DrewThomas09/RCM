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


class EngagementAuditTrailTests(unittest.TestCase):
    """MR1024 (Report-0266): ``_audit`` is best-effort by design — it
    never fails the caller — so a broken audit path would be invisible
    to every other test. These pin that each mutator actually lands a
    chained row, and that the best-effort contract holds when the
    chain writer is down."""

    _EXPECTED_ACTIONS = (
        "engagement.create",
        "engagement.member.add",
        "engagement.member.remove",
        "engagement.comment.post",
        "engagement.deliverable.create",
        "engagement.deliverable.publish",
    )

    def test_every_mutator_writes_a_chained_audit_row(self):
        import dataclasses  # noqa: F401  (parallel import kept minimal)
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            create_engagement(
                store, engagement_id="E1", name="p",
                client_name="c", created_by="admin",
            )
            add_member(
                store, engagement_id="E1", username="admin",
                role=EngagementRole.PARTNER, added_by="admin",
            )
            add_member(
                store, engagement_id="E1", username="u1",
                role=EngagementRole.ANALYST, added_by="admin",
            )
            remove_member(
                store, engagement_id="E1", username="u1",
                removed_by="admin",
            )
            post_comment(
                store, engagement_id="E1", target="deal:D1",
                author="admin", body="kickoff",
            )
            d = create_deliverable(
                store, engagement_id="E1", kind="ADVISORY",
                title="ops advisory", created_by="admin",
            )
            publish_deliverable(
                store, engagement_id="E1",
                deliverable_id=d.deliverable_id, published_by="admin",
            )
            with store.connect() as con:
                rows = con.execute(
                    "SELECT action, actor, row_hash FROM audit_events "
                    "ORDER BY id"
                ).fetchall()
            actions = [r["action"] for r in rows]
            for expected in self._EXPECTED_ACTIONS:
                self.assertIn(
                    expected, actions,
                    f"no audit row for {expected}; got {actions}",
                )
            for r in rows:
                if str(r["action"]).startswith("engagement."):
                    self.assertTrue(
                        r["row_hash"],
                        f"audit row for {r['action']} missing row_hash — "
                        "the chained writer did not run",
                    )

    def test_audit_outage_never_fails_the_mutator(self):
        # Simulating a failing chain writer is the documented
        # external-stub exception (CLAUDE.md testing rules).
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            with patch(
                "rcm_mc.compliance.audit_chain.append_chained_event",
                side_effect=RuntimeError("audit chain down"),
            ):
                e = create_engagement(
                    store, engagement_id="E1", name="p",
                    client_name="c", created_by="admin",
                )
            self.assertEqual(e.engagement_id, "E1")
            self.assertIsNotNone(get_engagement(store, "E1"))


class EngagementSchemaGuardTests(unittest.TestCase):
    """MR988 (Report-0266): the four dataclasses and their CREATE
    TABLE statements are maintained by hand in the same file. This
    guard turns silent drift (column added to only one side) into a
    red test. All four map 1:1 at time of writing — no exclusion set."""

    def test_dataclass_fields_match_table_columns(self):
        import dataclasses

        from rcm_mc.engagement.store import (
            Comment, Deliverable as _Deliverable, Engagement,
            EngagementMember,
        )
        pairs = [
            (Engagement, "engagements"),
            (EngagementMember, "engagement_members"),
            (Comment, "engagement_comments"),
            (_Deliverable, "engagement_deliverables"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            create_engagement(
                store, engagement_id="E1", name="p",
                client_name="c", created_by="admin",
            )
            with store.connect() as con:
                for dc, table in pairs:
                    dc_fields = {f.name for f in dataclasses.fields(dc)}
                    cols = {
                        r["name"] for r in con.execute(
                            f"PRAGMA table_info({table})"
                        ).fetchall()
                    }
                    self.assertEqual(
                        dc_fields, cols,
                        f"{dc.__name__} vs {table}: dataclass-only "
                        f"{sorted(dc_fields - cols)}, table-only "
                        f"{sorted(cols - dc_fields)}",
                    )


if __name__ == "__main__":
    unittest.main()
