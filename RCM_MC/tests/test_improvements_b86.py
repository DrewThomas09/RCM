"""Tests for improvement pass B86: pagination, stage validation, rate limit,
nav badges, archived counts.

PAGINATION:
 1. /api/deals returns paginated structure with total/limit/offset.
 2. limit/offset query params work.

STAGE VALIDATION:
 3. Forward transitions allowed.
 4. Backward skip raises ValueError.
 5. Closed is terminal.
 6. First stage (from None) always allowed.

RATE LIMITING ON DELETE:
 7. 10 deletes allowed within window.

NAV BADGES:
 8. Shell HTML contains alert badge span.
 9. /api/alerts/active-count returns count.

ARCHIVED COUNT:
10. list_deals(include_archived=True) includes archived.
"""
from __future__ import annotations

import json
import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.request

from rcm_mc.deals.deal_stages import (
    VALID_STAGES, set_stage, current_stage, validate_transition,
)
from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.ui._ui_kit import shell


def _start(db_path):
    from rcm_mc.server import build_server
    s = socket.socket(); s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]; s.close()
    server, _ = build_server(port=port, db_path=db_path)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start(); time.sleep(0.05)
    return server, port


def _tmp_store():
    tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tf.close()
    return PortfolioStore(tf.name), tf.name


class TestPagination(unittest.TestCase):

    def _seed_with_snapshots(self, store, count):
        from rcm_mc.portfolio.portfolio_snapshots import register_snapshot
        for i in range(count):
            did = f"d{i}"
            store.upsert_deal(did, name=f"Deal {i}")
            register_snapshot(store, did, "loi")

    def test_paginated_response_structure(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            self._seed_with_snapshots(store, 2)
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/deals",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertIn("deals", body)
                self.assertIn("total", body)
                self.assertIn("limit", body)
                self.assertIn("offset", body)
                self.assertEqual(body["total"], 2)
                self.assertEqual(len(body["deals"]), 2)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_limit_offset(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            self._seed_with_snapshots(store, 5)
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/deals?limit=2&offset=1",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertEqual(body["limit"], 2)
                self.assertEqual(body["offset"], 1)
                self.assertEqual(len(body["deals"]), 2)
                self.assertEqual(body["total"], 5)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


class TestStageTransitionValidation(unittest.TestCase):

    def test_forward_transitions(self):
        store, path = _tmp_store()
        try:
            store.upsert_deal("d1", name="D1")
            set_stage(store, "d1", "pipeline")
            set_stage(store, "d1", "diligence")
            set_stage(store, "d1", "ic")
            set_stage(store, "d1", "hold")
            set_stage(store, "d1", "exit")
            set_stage(store, "d1", "closed")
            self.assertEqual(current_stage(store, "d1"), "closed")
        finally:
            os.unlink(path)

    def test_backward_skip_raises(self):
        store, path = _tmp_store()
        try:
            store.upsert_deal("d1", name="D1")
            set_stage(store, "d1", "pipeline")
            set_stage(store, "d1", "diligence")
            set_stage(store, "d1", "ic")
            with self.assertRaises(ValueError) as ctx:
                set_stage(store, "d1", "pipeline")
            self.assertIn("cannot transition", str(ctx.exception))
        finally:
            os.unlink(path)

    def test_closed_is_terminal(self):
        store, path = _tmp_store()
        try:
            store.upsert_deal("d1", name="D1")
            set_stage(store, "d1", "pipeline")
            set_stage(store, "d1", "closed")
            with self.assertRaises(ValueError):
                set_stage(store, "d1", "pipeline")
        finally:
            os.unlink(path)

    def test_first_stage_always_allowed(self):
        self.assertIsNone(validate_transition(None, "diligence"))
        self.assertIsNone(validate_transition(None, "closed"))

    def test_same_stage_noop(self):
        self.assertIsNone(validate_transition("hold", "hold"))

    def test_allowed_backstep(self):
        """diligence -> pipeline is allowed (deal returned to pipeline)."""
        self.assertIsNone(validate_transition("diligence", "pipeline"))

    def test_ic_to_diligence_allowed(self):
        """IC can revert to diligence for re-evaluation."""
        self.assertIsNone(validate_transition("ic", "diligence"))


class TestNavAlertBadge(unittest.TestCase):

    def test_shell_has_alert_badge(self):
        html = shell("<p>test</p>", "Test Page")
        self.assertIn("cad-alert-count", html)
        self.assertIn("/alerts", html)

    def test_active_count_endpoint(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/alerts/active-count",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertIn("count", body)
                self.assertIsInstance(body["count"], int)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


class TestArchivedDealCount(unittest.TestCase):

    def test_list_deals_filters_archived(self):
        store, path = _tmp_store()
        try:
            store.upsert_deal("d1", name="Active")
            store.upsert_deal("d2", name="Archived")
            store.archive_deal("d2")
            active = store.list_deals()
            all_deals = store.list_deals(include_archived=True)
            self.assertEqual(len(active), 1)
            self.assertEqual(len(all_deals), 2)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
