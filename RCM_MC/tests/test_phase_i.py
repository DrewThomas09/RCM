"""Tests for Prompt 42 (hold dashboard), 48 (RBAC), 49 (comments), 50 (approvals).

HOLD DASHBOARD:
 1. render_hold_dashboard produces HTML.
 2. Empty actuals shows "no quarterly actuals" hint.
 3. Initiative progress bars rendered from plan.
 4. GET /hold/<id> route returns HTML.

RBAC:
 5. VIEWER can read but not create_deal.
 6. ASSOCIATE can create_deal but not delete_deal.
 7. PARTNER can delete_deal.
 8. ADMIN has all permissions.
 9. Unknown role → empty perms.

COMMENTS:
10. add_comment + list_comments round-trip.
11. Comment scoped to metric_key.
12. Resolve sets flag.
13. @-mention parsed from body.
14. Threaded: parent_id set.

APPROVALS:
15. request_approval creates pending row.
16. decide_approval sets status + decided_at.
17. Invalid status raises ValueError.
18. pending_approvals filters by approver.
"""
from __future__ import annotations

import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.request

from rcm_mc.auth.rbac import Role, check_permission
from rcm_mc.deals.approvals import (
    decide_approval,
    pending_approvals,
    request_approval,
)
from rcm_mc.deals.comments import (
    add_comment,
    list_comments,
    parse_mentions,
    resolve_comment,
)
from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.ui.hold_dashboard import render_hold_dashboard


def _tmp_store():
    tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tf.close()
    return PortfolioStore(tf.name), tf.name


# ── Hold Dashboard ────────────────────────────────────────────────

class TestHoldDashboard(unittest.TestCase):

    def test_renders_html(self):
        store, path = _tmp_store()
        try:
            store.upsert_deal("d1", name="D1")
            html = render_hold_dashboard(store, "d1", "D1")
            self.assertIn("Hold Period", html)
        finally:
            os.unlink(path)

    def test_empty_actuals_hint(self):
        store, path = _tmp_store()
        try:
            store.upsert_deal("d1", name="D1")
            html = render_hold_dashboard(store, "d1", "D1")
            self.assertIn("No quarterly actuals", html)
        finally:
            os.unlink(path)

    def test_initiative_progress_from_plan(self):
        store, path = _tmp_store()
        try:
            store.upsert_deal("d1", name="D1")
            from rcm_mc.pe.value_creation_plan import (
                ValueCreationPlan, Initiative, save_plan,
            )
            plan = ValueCreationPlan(
                deal_id="d1",
                initiatives=[
                    Initiative(
                        initiative_id="i1", name="Reduce denials",
                        status="on_track", lever_key="denial_rate",
                    ),
                ],
            )
            save_plan(store, plan)
            html = render_hold_dashboard(store, "d1", "D1")
            self.assertIn("Reduce denials", html)
            self.assertIn("on_track", html)
        finally:
            os.unlink(path)

    def test_hold_route(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            PortfolioStore(tf.name).upsert_deal("d1", name="D1")
            from rcm_mc.server import build_server
            s = socket.socket(); s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]; s.close()
            server, _ = build_server(port=port, db_path=tf.name)
            t = threading.Thread(target=server.serve_forever, daemon=True)
            t.start(); time.sleep(0.05)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/hold/d1",
                ) as r:
                    self.assertIn("Hold Period", r.read().decode())
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


# ── RBAC ──────────────────────────────────────────────────────────

class TestRBAC(unittest.TestCase):

    def test_viewer_read_only(self):
        self.assertTrue(check_permission("VIEWER", "read"))
        self.assertFalse(check_permission("VIEWER", "create_deal"))

    def test_associate_can_create(self):
        self.assertTrue(check_permission("ASSOCIATE", "create_deal"))
        self.assertFalse(check_permission("ASSOCIATE", "delete_deal"))

    def test_partner_can_delete(self):
        self.assertTrue(check_permission("PARTNER", "delete_deal"))

    def test_admin_has_all(self):
        self.assertTrue(check_permission("ADMIN", "admin"))
        self.assertTrue(check_permission("ADMIN", "delete_deal"))
        self.assertTrue(check_permission("ADMIN", "read"))

    def test_unknown_role_empty(self):
        self.assertFalse(check_permission("INTERN", "read"))


# ── Comments ──────────────────────────────────────────────────────

class TestComments(unittest.TestCase):

    def test_add_and_list(self):
        store, path = _tmp_store()
        try:
            store.upsert_deal("d1", name="D1")
            cid = add_comment(store, "d1", "Hello world", "analyst")
            self.assertGreater(cid, 0)
            comments = list_comments(store, "d1")
            self.assertEqual(len(comments), 1)
            self.assertEqual(comments[0]["body"], "Hello world")
        finally:
            os.unlink(path)

    def test_metric_scoped(self):
        store, path = _tmp_store()
        try:
            store.upsert_deal("d1", name="D1")
            add_comment(store, "d1", "On denial", "a",
                        metric_key="denial_rate")
            add_comment(store, "d1", "On AR", "a",
                        metric_key="days_in_ar")
            denial_comments = list_comments(store, "d1",
                                             metric_key="denial_rate")
            self.assertEqual(len(denial_comments), 1)
        finally:
            os.unlink(path)

    def test_resolve(self):
        store, path = _tmp_store()
        try:
            store.upsert_deal("d1", name="D1")
            cid = add_comment(store, "d1", "Fix this", "a")
            self.assertTrue(resolve_comment(store, cid))
            comments = list_comments(store, "d1", resolved=True)
            self.assertEqual(len(comments), 1)
        finally:
            os.unlink(path)

    def test_mention_parsing(self):
        mentions = parse_mentions("Hey @alice and @bob, please review.")
        self.assertEqual(set(mentions), {"alice", "bob"})

    def test_threading(self):
        store, path = _tmp_store()
        try:
            store.upsert_deal("d1", name="D1")
            parent = add_comment(store, "d1", "Parent", "a")
            child = add_comment(store, "d1", "Reply", "b",
                                parent_id=parent)
            comments = list_comments(store, "d1")
            reply = next(c for c in comments if c["id"] == child)
            self.assertEqual(reply["parent_id"], parent)
        finally:
            os.unlink(path)


# ── Approvals ─────────────────────────────────────────────────────

class TestApprovals(unittest.TestCase):

    def test_request_creates_pending(self):
        store, path = _tmp_store()
        try:
            store.upsert_deal("d1", name="D1")
            rid = request_approval(store, "d1", "ic_review",
                                   "vp_user", "associate_user")
            self.assertGreater(rid, 0)
            pending = pending_approvals(store)
            self.assertEqual(len(pending), 1)
            self.assertEqual(pending[0]["status"], "pending")
        finally:
            os.unlink(path)

    def test_decide_approval(self):
        store, path = _tmp_store()
        try:
            store.upsert_deal("d1", name="D1")
            rid = request_approval(store, "d1", "ic_review",
                                   "vp", "assoc")
            ok = decide_approval(store, rid, "approved", notes="LGTM")
            self.assertTrue(ok)
            self.assertEqual(pending_approvals(store), [])
        finally:
            os.unlink(path)

    def test_invalid_status_raises(self):
        store, path = _tmp_store()
        try:
            store.upsert_deal("d1", name="D1")
            rid = request_approval(store, "d1", "ic_review", "vp", "a")
            with self.assertRaises(ValueError):
                decide_approval(store, rid, "maybe")
        finally:
            os.unlink(path)

    def test_filter_by_approver(self):
        store, path = _tmp_store()
        try:
            store.upsert_deal("d1", name="D1")
            store.upsert_deal("d2", name="D2")
            request_approval(store, "d1", "ic_review", "alice", "a")
            request_approval(store, "d2", "ic_review", "bob", "a")
            alice_pending = pending_approvals(store, approver="alice")
            self.assertEqual(len(alice_pending), 1)
            self.assertEqual(alice_pending[0]["deal_id"], "d1")
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
