"""Tests for the read-only PEdesk Guide context debug endpoint.

GET /api/guide/context?route=<route> returns a JSON-safe GuideContextPacket.
It is a pure builder call over the static context registries — no model,
no Ollama, no RAG, no DB writes, no task/artifact creation. The server
boots in single-user (open) mode here (no users created), so the endpoint
is reachable without a session.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
import urllib.error as _ue
import urllib.request as _u


def _start(tmp):
    import socket as _socket
    import threading
    import time as _time
    from rcm_mc.server import build_server

    s = _socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    server, _ = build_server(port=port, db_path=os.path.join(tmp, "p.db"))
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    _time.sleep(0.05)
    return server, port


def _get(port, path):
    """Return (status, parsed_json). Tolerates error statuses (e.g. 400)."""
    url = f"http://127.0.0.1:{port}{path}"
    try:
        with _u.urlopen(url) as r:
            return r.status, json.loads(r.read().decode())
    except _ue.HTTPError as e:
        return e.code, json.loads(e.read().decode())


class GuideContextEndpointTests(unittest.TestCase):
    def test_hcris_xray(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = _start(tmp)
            try:
                status, data = _get(
                    port, "/api/guide/context?route=/diligence/hcris-xray"
                )
                self.assertEqual(status, 200)
                self.assertIn(data["context_quality"], ("strong", "partial"))
                self.assertTrue(data["found_page_context"])
                self.assertTrue(data["page_context"]["title"])
                self.assertTrue(data["suggested_questions"])
                self.assertIn("identity", data["read_only_policy"])
                self.assertIn("disallowed_behavior", data["read_only_policy"])
                # Linked metric/source contexts surface in the JSON.
                self.assertTrue(
                    data["metric_contexts"] or data["data_source_contexts"]
                )
            finally:
                server.shutdown()
                server.server_close()

    def test_query_string_route_normalizes(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = _start(tmp)
            try:
                status, data = _get(
                    port,
                    "/api/guide/context?route=/diligence/risk-workbench"
                    "?demo=steward",
                )
                self.assertEqual(status, 200)
                self.assertEqual(
                    data["normalized_route"], "/diligence/risk-workbench"
                )
            finally:
                server.shutdown()
                server.server_close()

    def test_dynamic_deal_route(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = _start(tmp)
            try:
                status, data = _get(
                    port, "/api/guide/context?route=/deal/390049"
                )
                self.assertEqual(status, 200)
                self.assertTrue(data["found_page_context"])
                self.assertEqual(data["page_context"]["title"], "Deal Dashboard")
            finally:
                server.shutdown()
                server.server_close()

    def test_dynamic_analysis_route(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = _start(tmp)
            try:
                status, data = _get(
                    port, "/api/guide/context?route=/analysis/390049"
                )
                self.assertEqual(status, 200)
                self.assertTrue(data["found_page_context"])
                self.assertEqual(
                    data["page_context"]["title"], "Analysis Workbench"
                )
            finally:
                server.shutdown()
                server.server_close()

    def test_unknown_route_is_missing_not_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = _start(tmp)
            try:
                status, data = _get(
                    port, "/api/guide/context?route=/unknown-route"
                )
                self.assertEqual(status, 200)
                self.assertEqual(data["context_quality"], "missing")
                self.assertFalse(data["found_page_context"])
                self.assertTrue(data["fallback_message"])
            finally:
                server.shutdown()
                server.server_close()

    def test_missing_route_param_is_400(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = _start(tmp)
            try:
                status, data = _get(port, "/api/guide/context")
                self.assertEqual(status, 400)
                self.assertIn("error", data)
                self.assertEqual(data["code"], "MISSING_ROUTE")
                # Clean error — no stack trace leaked.
                self.assertNotIn("Traceback", json.dumps(data))
            finally:
                server.shutdown()
                server.server_close()

    def test_endpoint_is_pure_and_idempotent(self):
        # No mutation convention exists for read endpoints; assert the
        # builder is pure by checking two identical requests return byte-
        # identical JSON (the packet is a deterministic registry read).
        with tempfile.TemporaryDirectory() as tmp:
            server, port = _start(tmp)
            try:
                _, a = _get(
                    port, "/api/guide/context?route=/diligence/hcris-xray"
                )
                _, b = _get(
                    port, "/api/guide/context?route=/diligence/hcris-xray"
                )
                self.assertEqual(
                    json.dumps(a, sort_keys=True),
                    json.dumps(b, sort_keys=True),
                )
            finally:
                server.shutdown()
                server.server_close()


if __name__ == "__main__":
    unittest.main()
