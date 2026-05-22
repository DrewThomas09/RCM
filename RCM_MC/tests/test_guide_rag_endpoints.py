"""RAG endpoints + ask integration. No real Ollama: retrieval.search and
call_ollama_chat are mocked, RAG/Ollama enabled via env. Server boots in
single-user (open) mode."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
import urllib.error as _ue
import urllib.request as _u
from unittest import mock

from rcm_mc.assistant import ollama_client
from rcm_mc.assistant.rag import retrieval as rag_retrieval
from rcm_mc.assistant.rag.types import RagSearchResult


def _start(tmp):
    import socket as _socket
    import threading
    import time as _time
    from rcm_mc.server import build_server
    s = _socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    server, _ = build_server(port=port, db_path=os.path.join(tmp, "p.db"))
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start(); _time.sleep(0.05)
    return server, port


def _get(port, path):
    try:
        with _u.urlopen(f"http://127.0.0.1:{port}{path}") as r:
            return r.status, json.loads(r.read().decode())
    except _ue.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def _post(port, payload):
    req = _u.Request(f"http://127.0.0.1:{port}/api/guide/ask",
                     data=json.dumps(payload).encode(), method="POST",
                     headers={"Content-Type": "application/json"})
    try:
        with _u.urlopen(req) as r:
            return r.status, json.loads(r.read().decode())
    except _ue.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def _mock_results():
    return [
        RagSearchResult(title="Denial Rate", source_type="metric",
                        text="Share of claims initially denied by payers.",
                        score=0.92, metric_id="denial_rate"),
        RagSearchResult(title="CMS HCRIS", source_type="data_source",
                        text="Medicare hospital cost-report filings.",
                        score=0.81, data_source_id="cms_hcris"),
    ]


def _rag_on():
    return mock.patch.dict(os.environ, {"PEDESK_GUIDE_RAG_ENABLED": "true"})


def _ollama_on():
    return mock.patch.dict(os.environ, {"PEDESK_GUIDE_OLLAMA_ENABLED": "true"})


class RagSearchEndpointTests(unittest.TestCase):
    def test_disabled_returns_clean_json(self):
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.dict(os.environ, {"PEDESK_GUIDE_RAG_ENABLED": "false"}):
            server, port = _start(tmp)
            try:
                status, data = _get(
                    port, "/api/guide/rag/search?q=where+does+hcris+come+from")
                self.assertEqual(status, 200)
                self.assertFalse(data["enabled"])
                self.assertEqual(data["results"], [])
                self.assertIn("PEDESK_GUIDE_RAG_ENABLED", data["detail"])
            finally:
                server.shutdown(); server.server_close()

    def test_enabled_returns_mocked_results(self):
        with tempfile.TemporaryDirectory() as tmp, _rag_on(), \
                mock.patch.object(rag_retrieval, "search",
                                  return_value=_mock_results()):
            server, port = _start(tmp)
            try:
                status, data = _get(
                    port, "/api/guide/rag/search?q=denial+rate")
                self.assertEqual(status, 200)
                self.assertTrue(data["enabled"])
                self.assertEqual(len(data["results"]), 2)
                r0 = data["results"][0]
                self.assertEqual(r0["title"], "Denial Rate")
                self.assertEqual(r0["source_type"], "metric")
                self.assertIn("snippet", r0)
                self.assertIn("metadata", r0)
            finally:
                server.shutdown(); server.server_close()

    def test_enabled_missing_query_is_400(self):
        with tempfile.TemporaryDirectory() as tmp, _rag_on():
            server, port = _start(tmp)
            try:
                status, data = _get(port, "/api/guide/rag/search")
                self.assertEqual(status, 400)
                self.assertEqual(data["code"], "MISSING_QUERY")
            finally:
                server.shutdown(); server.server_close()

    def test_enabled_embeddings_unreachable_is_503(self):
        with tempfile.TemporaryDirectory() as tmp, _rag_on(), \
                mock.patch.object(rag_retrieval, "search",
                                  side_effect=ollama_client.OllamaError("x")):
            server, port = _start(tmp)
            try:
                status, data = _get(port, "/api/guide/rag/search?q=hi")
                self.assertEqual(status, 503)
                self.assertIn("embedding model is unavailable", data["error"])
            finally:
                server.shutdown(); server.server_close()


class AskWithRagTests(unittest.TestCase):
    def test_ask_rag_disabled_behaves_as_v1(self):
        with tempfile.TemporaryDirectory() as tmp, _ollama_on(), \
                mock.patch.dict(os.environ, {"PEDESK_GUIDE_RAG_ENABLED": "false"}), \
                mock.patch.object(ollama_client, "call_ollama_chat",
                                  return_value="HCRIS comes from CMS.") as chat:
            server, port = _start(tmp)
            try:
                status, data = _post(port, {
                    "route": "/diligence/hcris-xray",
                    "question": "Where does this data come from?"})
                self.assertEqual(status, 200)
                self.assertFalse(data["rag_enabled"])
                self.assertEqual(data["rag_results_count"], 0)
                self.assertEqual(data["rag_sources_used"], [])
                self.assertTrue(data["read_only"])
                # Prompt passed to the model had no retrieved-context block.
                user_prompt = chat.call_args[0][1]
                self.assertNotIn("Additional local Guide context", user_prompt)
            finally:
                server.shutdown(); server.server_close()

    def test_ask_rag_enabled_includes_sources_used(self):
        with tempfile.TemporaryDirectory() as tmp, _ollama_on(), _rag_on(), \
                mock.patch.object(rag_retrieval, "search",
                                  return_value=_mock_results()), \
                mock.patch.object(ollama_client, "call_ollama_chat",
                                  return_value="Denial rate is the share of "
                                               "claims denied.") as chat:
            server, port = _start(tmp)
            try:
                status, data = _post(port, {
                    "route": "/diligence/hcris-xray",
                    "question": "What does denial rate mean?"})
                self.assertEqual(status, 200)
                self.assertTrue(data["rag_enabled"])
                self.assertEqual(data["rag_results_count"], 2)
                titles = [s["title"] for s in data["rag_sources_used"]]
                self.assertIn("Denial Rate", titles)
                self.assertTrue(data["read_only"])
                # The retrieved-context block reached the prompt.
                user_prompt = chat.call_args[0][1]
                self.assertIn("Additional local Guide context", user_prompt)
            finally:
                server.shutdown(); server.server_close()

    def test_ask_rag_enabled_but_embeddings_fail_falls_back(self):
        # RAG retrieval errors must NOT break ask — packet-only fallback.
        with tempfile.TemporaryDirectory() as tmp, _ollama_on(), _rag_on(), \
                mock.patch.object(rag_retrieval, "search",
                                  side_effect=ollama_client.OllamaError("x")), \
                mock.patch.object(ollama_client, "call_ollama_chat",
                                  return_value="answer"):
            server, port = _start(tmp)
            try:
                status, data = _post(port, {
                    "route": "/diligence/hcris-xray",
                    "question": "Explain this page."})
                self.assertEqual(status, 200)
                self.assertTrue(data["rag_enabled"])
                self.assertEqual(data["rag_results_count"], 0)
                self.assertTrue(data["read_only"])
            finally:
                server.shutdown(); server.server_close()


class OllamaHealthRichTests(unittest.TestCase):
    def test_health_disabled_has_suggested_fix_and_env(self):
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.dict(os.environ, {"PEDESK_GUIDE_OLLAMA_ENABLED": "false"}):
            server, port = _start(tmp)
            try:
                _, data = _get(port, "/api/guide/ollama-health")
                self.assertFalse(data["enabled"])
                self.assertIn("PEDESK_GUIDE_OLLAMA_ENABLED=true",
                              data["suggested_fix"])
                self.assertIn("PEDESK_GUIDE_OLLAMA_ENABLED", data["required_env"])
                self.assertIn("timeout_seconds", data)
            finally:
                server.shutdown(); server.server_close()

    def test_health_includes_rag_diagnostics(self):
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.dict(os.environ, {"PEDESK_GUIDE_OLLAMA_ENABLED": "false"}):
            server, port = _start(tmp)
            try:
                _, data = _get(port, "/api/guide/ollama-health")
                for key in ("embed_model", "rag_enabled", "rag_index_path",
                            "rag_index_exists", "rag_chunk_count"):
                    self.assertIn(key, data)
                self.assertEqual(data["embed_model"], "nomic-embed-text")
            finally:
                server.shutdown(); server.server_close()

    def test_health_missing_index_suggests_build(self):
        # Ollama enabled + reachable + models present, RAG enabled, but the
        # index file is absent → suggested_fix points at index_builder.
        missing = os.path.join(tempfile.gettempdir(), "no_such_rag_idx.sqlite3")
        if os.path.exists(missing):
            os.remove(missing)
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.dict(os.environ, {
                    "PEDESK_GUIDE_OLLAMA_ENABLED": "true",
                    "PEDESK_GUIDE_RAG_ENABLED": "true",
                    "PEDESK_GUIDE_RAG_INDEX_PATH": missing}), \
                mock.patch.object(ollama_client, "check_ollama_health",
                                  return_value=True), \
                mock.patch.object(ollama_client, "list_models",
                                  return_value=["gemma4:e4b",
                                                "nomic-embed-text:latest"]):
            server, port = _start(tmp)
            try:
                _, data = _get(port, "/api/guide/ollama-health")
                self.assertTrue(data["rag_enabled"])
                self.assertFalse(data["rag_index_exists"])
                self.assertIn("index_builder", data["suggested_fix"])
            finally:
                server.shutdown(); server.server_close()


class AskMissingIndexWarningTests(unittest.TestCase):
    def test_ask_rag_enabled_missing_index_warns_and_falls_back(self):
        missing = os.path.join(tempfile.gettempdir(), "no_such_rag_idx2.sqlite3")
        if os.path.exists(missing):
            os.remove(missing)
        with tempfile.TemporaryDirectory() as tmp, _ollama_on(), \
                mock.patch.dict(os.environ, {
                    "PEDESK_GUIDE_RAG_ENABLED": "true",
                    "PEDESK_GUIDE_RAG_INDEX_PATH": missing}), \
                mock.patch.object(ollama_client, "call_ollama_chat",
                                  return_value="Answered from the page.") as chat:
            server, port = _start(tmp)
            try:
                status, data = _post(port, {
                    "route": "/diligence/hcris-xray",
                    "question": "What does this page do?"})
                self.assertEqual(status, 200)
                self.assertTrue(data["rag_enabled"])
                self.assertEqual(data["rag_results_count"], 0)
                self.assertIsNotNone(data["rag_warning"])
                self.assertIn("index_builder", data["rag_warning"])
                self.assertTrue(data["read_only"])
                # No retrieved-context block reached the prompt (fell back).
                self.assertNotIn("Additional local Guide context",
                                 chat.call_args[0][1])
            finally:
                server.shutdown(); server.server_close()


if __name__ == "__main__":
    unittest.main()
