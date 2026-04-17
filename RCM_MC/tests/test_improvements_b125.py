"""Tests for B125: portfolio register API.

 1. POST /api/portfolio/register creates a snapshot.
 2. Missing deal_id returns 400.
 3. Invalid stage returns 400.
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


class TestPortfolioRegister(unittest.TestCase):

    def test_register_creates_snapshot(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Alpha")
            server, port = _start(tf.name)
            try:
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/portfolio/register",
                    data=json.dumps({
                        "deal_id": "d1",
                        "stage": "loi",
                        "notes": "Initial registration",
                    }).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req) as r:
                    body = json.loads(r.read().decode())
                self.assertIn("snapshot_id", body)
                self.assertEqual(body["deal_id"], "d1")
                self.assertEqual(body["stage"], "loi")
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_missing_deal_id_400(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/portfolio/register",
                    data=json.dumps({"stage": "loi"}).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with self.assertRaises(urllib.error.HTTPError) as ctx:
                    urllib.request.urlopen(req)
                self.assertEqual(ctx.exception.code, 400)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_invalid_stage_400(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/portfolio/register",
                    data=json.dumps({
                        "deal_id": "d1", "stage": "bogus",
                    }).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with self.assertRaises(urllib.error.HTTPError) as ctx:
                    urllib.request.urlopen(req)
                self.assertEqual(ctx.exception.code, 400)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


if __name__ == "__main__":
    unittest.main()
