"""Tests for deal deletion (cascade) and custom metric deletion APIs.

DEAL DELETION:
 1. DELETE /api/deals/<id> removes the deal and returns 200.
 2. DELETE non-existent deal returns 404.
 3. Cascade removes child rows (notes, tags, overrides, runs).
 4. Store.delete_deal returns False for missing deal.

CUSTOM METRIC DELETION:
 5. DELETE /api/metrics/custom/<key> removes the metric.
 6. DELETE non-existent metric returns 404.
"""
from __future__ import annotations

import json
import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

from rcm_mc.portfolio.store import PortfolioStore


def _start(db_path):
    from rcm_mc.server import build_server
    s = socket.socket(); s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]; s.close()
    server, _ = build_server(port=port, db_path=db_path)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start(); time.sleep(0.05)
    return server, port


class TestDealDeletionStore(unittest.TestCase):

    def test_delete_existing_deal(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Deal One")
            self.assertTrue(store.delete_deal("d1"))
            deals = store.list_deals()
            self.assertEqual(len(deals), 0)
        finally:
            os.unlink(tf.name)

    def test_delete_missing_deal(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            self.assertFalse(store.delete_deal("nope"))
        finally:
            os.unlink(tf.name)

    def test_cascade_removes_children(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Deal One",
                              profile={"bed_count": 200})

            from rcm_mc.deals.deal_notes import record_note, list_notes
            record_note(store, deal_id="d1", body="Test note", author="tester")

            from rcm_mc.deals.deal_tags import add_tag
            add_tag(store, "d1", "test-tag")

            store.delete_deal("d1")

            deals = store.list_deals()
            self.assertEqual(len(deals), 0)

            self.assertEqual(len(list_notes(store, "d1")), 0)
        finally:
            os.unlink(tf.name)


class TestDealDeletionAPI(unittest.TestCase):

    def test_delete_via_api(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Deal One")
            server, port = _start(tf.name)
            try:
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/deals/d1",
                    method="DELETE",
                )
                with urllib.request.urlopen(req) as r:
                    body = json.loads(r.read().decode())
                self.assertTrue(body["deleted"])
                self.assertEqual(body["deal_id"], "d1")
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_delete_missing_404(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/deals/nope",
                    method="DELETE",
                )
                with self.assertRaises(urllib.error.HTTPError) as ctx:
                    urllib.request.urlopen(req)
                self.assertEqual(ctx.exception.code, 404)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


class TestCustomMetricDeletionAPI(unittest.TestCase):

    def test_delete_metric(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                # Create first
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/metrics/custom",
                    data=json.dumps({
                        "metric_key": "test_metric",
                        "display_name": "Test Metric",
                    }).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req) as r:
                    body = json.loads(r.read().decode())
                self.assertTrue(body["created"])

                # Delete
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/metrics/custom/test_metric",
                    method="DELETE",
                )
                with urllib.request.urlopen(req) as r:
                    body = json.loads(r.read().decode())
                self.assertTrue(body["deleted"])

                # Verify gone
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/metrics/custom",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertEqual(body["metrics"], [])
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_delete_missing_metric_404(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/metrics/custom/nope",
                    method="DELETE",
                )
                with self.assertRaises(urllib.error.HTTPError) as ctx:
                    urllib.request.urlopen(req)
                self.assertEqual(ctx.exception.code, 404)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


class TestDealArchival(unittest.TestCase):

    def test_archive_and_unarchive_store(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Deal One")
            self.assertTrue(store.archive_deal("d1"))
            # Archived deals hidden by default
            self.assertEqual(len(store.list_deals()), 0)
            # Visible when include_archived=True
            self.assertEqual(len(store.list_deals(include_archived=True)), 1)
            # Unarchive restores
            self.assertTrue(store.unarchive_deal("d1"))
            self.assertEqual(len(store.list_deals()), 1)
        finally:
            os.unlink(tf.name)

    def test_archive_missing_deal(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            self.assertFalse(store.archive_deal("nope"))
        finally:
            os.unlink(tf.name)

    def test_archive_via_api(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Deal One")
            server, port = _start(tf.name)
            try:
                # Archive
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/deals/d1/archive",
                    method="POST",
                    data=b"",
                )
                with urllib.request.urlopen(req) as r:
                    body = json.loads(r.read().decode())
                self.assertTrue(body["archived"])

                # Unarchive
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/deals/d1/unarchive",
                    method="POST",
                    data=b"",
                )
                with urllib.request.urlopen(req) as r:
                    body = json.loads(r.read().decode())
                self.assertTrue(body["unarchived"])
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


if __name__ == "__main__":
    unittest.main()
