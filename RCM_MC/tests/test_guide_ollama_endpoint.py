"""Tests for the read-only local-Ollama PEdesk Guide answer endpoint.

No real Ollama server is required: ``call_ollama_chat`` is monkeypatched,
and the model is "enabled" via env. The PEdesk server boots in
single-user (open) mode so the endpoint is reachable without a session.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
import urllib.error as _ue
import urllib.request as _u
from unittest import mock

from rcm_mc.assistant import ollama_client


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


def _post(port, payload, *, raw=None):
    url = f"http://127.0.0.1:{port}/api/guide/ask"
    body = raw if raw is not None else json.dumps(payload).encode()
    req = _u.Request(url, data=body, method="POST",
                     headers={"Content-Type": "application/json"})
    try:
        with _u.urlopen(req) as r:
            return r.status, json.loads(r.read().decode())
    except _ue.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def _enabled_env():
    return mock.patch.dict(os.environ, {"PEDESK_GUIDE_OLLAMA_ENABLED": "true"})


class GuideAskEndpointTests(unittest.TestCase):
    def test_ask_returns_answer_with_mocked_ollama(self):
        with tempfile.TemporaryDirectory() as tmp, _enabled_env(), \
                mock.patch.object(
                    ollama_client, "call_ollama_chat",
                    return_value="<think>reasoning</think>"
                                 "HCRIS data comes from CMS cost-report "
                                 "filings.",
                ) as mocked:
            server, port = _start(tmp)
            try:
                status, data = _post(port, {
                    "route": "/diligence/hcris-xray",
                    "question": "Where does this data come from?",
                })
                self.assertEqual(status, 200)
                self.assertTrue(mocked.called)
                self.assertEqual(data["read_only"], True)
                self.assertTrue(data["ollama_enabled"])
                self.assertIn(data["context_quality"], ("strong", "partial"))
                # <think> stripped from the returned answer
                self.assertNotIn("<think>", data["answer"])
                self.assertNotIn("reasoning", data["answer"])
                self.assertIn("CMS cost-report", data["answer"])
                self.assertEqual(
                    data["context_used"]["page_title"], "HCRIS X-Ray"
                )
                self.assertIn("cms_hcris", data["context_used"]["data_sources"])
            finally:
                server.shutdown()
                server.server_close()

    def test_missing_question_is_400(self):
        with tempfile.TemporaryDirectory() as tmp, _enabled_env():
            server, port = _start(tmp)
            try:
                status, data = _post(port, {"route": "/diligence/hcris-xray"})
                self.assertEqual(status, 400)
                self.assertEqual(data["code"], "MISSING_QUESTION")
                self.assertNotIn("Traceback", json.dumps(data))
            finally:
                server.shutdown()
                server.server_close()

    def test_missing_route_is_400(self):
        with tempfile.TemporaryDirectory() as tmp, _enabled_env():
            server, port = _start(tmp)
            try:
                status, data = _post(port, {"question": "What is this?"})
                self.assertEqual(status, 400)
                self.assertEqual(data["code"], "MISSING_ROUTE")
            finally:
                server.shutdown()
                server.server_close()

    def test_bad_json_is_400(self):
        with tempfile.TemporaryDirectory() as tmp, _enabled_env():
            server, port = _start(tmp)
            try:
                status, data = _post(port, None, raw=b"{not json")
                self.assertEqual(status, 400)
                self.assertEqual(data["code"], "BAD_JSON")
            finally:
                server.shutdown()
                server.server_close()

    def test_unknown_route_is_conservative_not_crash(self):
        with tempfile.TemporaryDirectory() as tmp, _enabled_env(), \
                mock.patch.object(
                    ollama_client, "call_ollama_chat",
                    return_value="PEdesk Guide has no documented context for "
                                 "that page.",
                ):
            server, port = _start(tmp)
            try:
                status, data = _post(port, {
                    "route": "/unknown-route",
                    "question": "What does this page do?",
                })
                self.assertEqual(status, 200)
                self.assertEqual(data["context_quality"], "missing")
                self.assertEqual(data["read_only"], True)
                self.assertTrue(data["answer"])
            finally:
                server.shutdown()
                server.server_close()

    def test_ollama_disabled_returns_clean_503(self):
        # No PEDESK_GUIDE_OLLAMA_ENABLED → disabled → 503, no model call.
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.dict(os.environ,
                                {"PEDESK_GUIDE_OLLAMA_ENABLED": "false"}):
            server, port = _start(tmp)
            try:
                status, data = _post(port, {
                    "route": "/diligence/hcris-xray",
                    "question": "Where does this data come from?",
                })
                self.assertEqual(status, 503)
                self.assertEqual(
                    data["error"], "PEdesk Guide local model is unavailable."
                )
                self.assertEqual(data["read_only"], True)
                self.assertNotIn("Traceback", json.dumps(data))
            finally:
                server.shutdown()
                server.server_close()

    def test_ollama_unreachable_returns_clean_503(self):
        # Enabled but the call raises OllamaError → clean 503.
        with tempfile.TemporaryDirectory() as tmp, _enabled_env(), \
                mock.patch.object(
                    ollama_client, "call_ollama_chat",
                    side_effect=ollama_client.OllamaError("boom"),
                ):
            server, port = _start(tmp)
            try:
                status, data = _post(port, {
                    "route": "/diligence/hcris-xray",
                    "question": "Where does this data come from?",
                })
                self.assertEqual(status, 503)
                self.assertIn("unavailable", data["error"])
                self.assertIn("could not be reached", data["detail"])
                self.assertEqual(data["read_only"], True)
            finally:
                server.shutdown()
                server.server_close()

    def test_response_is_read_only_no_mutation(self):
        # The endpoint only builds the packet and calls the (mocked) model.
        # There is no PEdesk read-endpoint mutation-test convention, so we
        # assert the read_only contract flag and that no DB is required
        # (server booted with an empty temp db; the call touches neither).
        with tempfile.TemporaryDirectory() as tmp, _enabled_env(), \
                mock.patch.object(
                    ollama_client, "call_ollama_chat", return_value="ok",
                ):
            server, port = _start(tmp)
            try:
                status, data = _post(port, {
                    "route": "/diligence/hcris-xray",
                    "question": "Explain this page.",
                })
                self.assertEqual(status, 200)
                self.assertIs(data["read_only"], True)
            finally:
                server.shutdown()
                server.server_close()


class OllamaHealthEndpointTests(unittest.TestCase):
    def test_health_disabled(self):
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.dict(os.environ,
                                {"PEDESK_GUIDE_OLLAMA_ENABLED": "false"}):
            server, port = _start(tmp)
            try:
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/api/guide/ollama-health"
                ) as r:
                    data = json.loads(r.read().decode())
                self.assertFalse(data["enabled"])
                self.assertFalse(data["reachable"])
                self.assertEqual(data["default_model"], "gemma4:e4b")
                self.assertTrue(data["base_url"])
            finally:
                server.shutdown()
                server.server_close()


if __name__ == "__main__":
    unittest.main()
