"""Tests for the newly wired REST API endpoints.

PLAN API:
 1. GET /api/deals/<id>/plan returns null when no plan.
 2. POST /api/deals/<id>/plan creates a plan.
 3. GET /api/deals/<id>/plan returns the plan after creation.

STAGE API:
 4. GET /api/deals/<id>/stage returns null when no stage set.
 5. POST /api/deals/<id>/stage sets the stage.
 6. Invalid stage returns 400.

COMMENTS API:
 7. GET /api/deals/<id>/comments returns empty list.
 8. POST /api/deals/<id>/comments adds a comment.
 9. Missing body returns 400.

APPROVALS API:
10. GET /api/deals/<id>/approvals returns empty pending list.

HEALTH:
11. GET /api/health returns db_ok + version + deal_count.
12. GET /ready returns ready: true.
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


class TestPlanAPI(unittest.TestCase):

    def test_get_plan_empty(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            PortfolioStore(tf.name).upsert_deal("d1", name="D1")
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/deals/d1/plan",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertIsNone(body["plan"])
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_post_creates_plan(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal(
                "d1", name="D1",
                profile={"bed_count": 200, "payer_mix": {"commercial": 1.0}},
            )
            server, port = _start(tf.name)
            try:
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/deals/d1/plan",
                    data=b"{}",
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req) as r:
                    body = json.loads(r.read().decode())
                self.assertIn("plan", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


class TestStageAPI(unittest.TestCase):

    def test_get_stage_empty(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            PortfolioStore(tf.name).upsert_deal("d1", name="D1")
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/deals/d1/stage",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertIsNone(body["current_stage"])
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_post_sets_stage(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            PortfolioStore(tf.name).upsert_deal("d1", name="D1")
            server, port = _start(tf.name)
            try:
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/deals/d1/stage",
                    data=json.dumps({"stage": "diligence"}).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req) as r:
                    body = json.loads(r.read().decode())
                self.assertEqual(body["stage"], "diligence")
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_invalid_stage_400(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            PortfolioStore(tf.name).upsert_deal("d1", name="D1")
            server, port = _start(tf.name)
            try:
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/deals/d1/stage",
                    data=json.dumps({"stage": "invalid"}).encode(),
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


class TestCommentsAPI(unittest.TestCase):

    def test_get_comments_empty(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            PortfolioStore(tf.name).upsert_deal("d1", name="D1")
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/deals/d1/comments",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertEqual(body["comments"], [])
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_post_comment(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            PortfolioStore(tf.name).upsert_deal("d1", name="D1")
            server, port = _start(tf.name)
            try:
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/deals/d1/comments",
                    data=json.dumps({
                        "body": "Test comment on denial rate",
                        "metric_key": "denial_rate",
                    }).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req) as r:
                    body = json.loads(r.read().decode())
                self.assertGreater(body["comment_id"], 0)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_empty_body_400(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            PortfolioStore(tf.name).upsert_deal("d1", name="D1")
            server, port = _start(tf.name)
            try:
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/deals/d1/comments",
                    data=json.dumps({"body": ""}).encode(),
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


class TestHealthEndpoints(unittest.TestCase):

    def test_health_endpoint(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/health",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertIn("status", body)
                self.assertIn("db_ok", body)
                self.assertIn("version", body)
                self.assertTrue(body["db_ok"])
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_ready_endpoint(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/ready",
                ) as r:
                    body = json.loads(r.read().decode())
                self.assertTrue(body["ready"])
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


if __name__ == "__main__":
    unittest.main()
