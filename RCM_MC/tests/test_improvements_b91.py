"""Tests for improvement pass B91: OpenAPI completeness, notes pagination.

OPENAPI:
 1. Spec includes /api/deals/bulk.
 2. Spec includes /api/deals/{deal_id}/summary.
 3. Spec includes /api/deals/{deal_id}/duplicate.
 4. Spec includes /api/alerts/active-count.
 5. Spec includes /api/metrics.
 6. Spec includes /api/deals/compare.

NOTES PAGINATION:
 7. /api/deals/<id>/notes returns paginated structure.
 8. limit/offset params work.
 9. list_notes with limit returns correct count.
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

from rcm_mc.infra.openapi import get_openapi_spec
from rcm_mc.portfolio.store import PortfolioStore


def _start(db_path):
    from rcm_mc.server import build_server
    s = socket.socket(); s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]; s.close()
    server, _ = build_server(port=port, db_path=db_path)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start(); time.sleep(0.05)
    return server, port


class TestOpenAPICompleteness(unittest.TestCase):

    def test_bulk_endpoint_documented(self):
        spec = get_openapi_spec()
        self.assertIn("/api/deals/bulk", spec["paths"])

    def test_summary_endpoint_documented(self):
        spec = get_openapi_spec()
        self.assertIn("/api/deals/{deal_id}/summary", spec["paths"])

    def test_duplicate_endpoint_documented(self):
        spec = get_openapi_spec()
        self.assertIn("/api/deals/{deal_id}/duplicate", spec["paths"])

    def test_active_count_documented(self):
        spec = get_openapi_spec()
        self.assertIn("/api/alerts/active-count", spec["paths"])

    def test_metrics_endpoint_documented(self):
        spec = get_openapi_spec()
        self.assertIn("/api/metrics", spec["paths"])

    def test_compare_endpoint_documented(self):
        spec = get_openapi_spec()
        self.assertIn("/api/deals/compare", spec["paths"])


class TestNotesPagination(unittest.TestCase):

    def test_notes_returns_paginated_structure(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="D1")
            from rcm_mc.deals.deal_notes import record_note
            record_note(store, deal_id="d1", body="Note 1", author="t")
            record_note(store, deal_id="d1", body="Note 2", author="t")
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/deals/d1/notes",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertIn("notes", body)
                self.assertIn("limit", body)
                self.assertIn("offset", body)
                self.assertEqual(len(body["notes"]), 2)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_notes_limit_offset(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="D1")
            from rcm_mc.deals.deal_notes import record_note
            for i in range(5):
                record_note(store, deal_id="d1", body=f"Note {i}", author="t")
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/deals/d1/notes?limit=2&offset=1",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertEqual(len(body["notes"]), 2)
                self.assertEqual(body["limit"], 2)
                self.assertEqual(body["offset"], 1)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_list_notes_with_limit(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="D1")
            from rcm_mc.deals.deal_notes import record_note, list_notes
            for i in range(5):
                record_note(store, deal_id="d1", body=f"Note {i}", author="t")
            df = list_notes(store, "d1", limit=3)
            self.assertEqual(len(df), 3)
        finally:
            os.unlink(tf.name)


if __name__ == "__main__":
    unittest.main()
