"""Ollama client resilience: multi-host failover, standard OLLAMA_HOST,
retries/backoff, and the num_ctx / keep_alive options.

These pin the "works in all environments + more power" behaviour without a
live server — urlopen is monkeypatched. No network, no real Ollama.
"""
from __future__ import annotations

import io
import json
import os
import unittest
import urllib.error
from unittest import mock

from rcm_mc.assistant import ollama_client as oc


def _resp(payload: dict):
    """A fake urlopen context manager returning JSON with status 200."""
    cm = mock.MagicMock()
    body = json.dumps(payload).encode("utf-8")
    inner = mock.MagicMock()
    inner.read.return_value = body
    inner.status = 200
    cm.__enter__.return_value = inner
    cm.__exit__.return_value = False
    return cm


class HostResolution(unittest.TestCase):
    def tearDown(self):
        for k in ("PEDESK_GUIDE_OLLAMA_BASE_URL", "OLLAMA_HOST",
                  "PEDESK_GUIDE_OLLAMA_NUM_CTX", "PEDESK_GUIDE_OLLAMA_KEEP_ALIVE"):
            os.environ.pop(k, None)

    def test_default_host_only(self):
        self.assertEqual(oc.ollama_base_urls(), ["http://localhost:11434"])
        self.assertEqual(oc.ollama_base_url(), "http://localhost:11434")

    def test_standard_ollama_host_env_is_honoured(self):
        os.environ["OLLAMA_HOST"] = "my-box:11434"
        urls = oc.ollama_base_urls()
        self.assertEqual(urls[0], "http://my-box:11434")  # scheme added
        self.assertIn("http://localhost:11434", urls)      # default still tried

    def test_comma_separated_multi_host_deduped_in_order(self):
        os.environ["PEDESK_GUIDE_OLLAMA_BASE_URL"] = (
            "http://a:11434, http://b:11434/ , http://a:11434")
        os.environ["OLLAMA_HOST"] = "http://b:11434"
        urls = oc.ollama_base_urls()
        self.assertEqual(urls[:2], ["http://a:11434", "http://b:11434"])
        # dedup: a and b appear once each; default appended last
        self.assertEqual(urls.count("http://a:11434"), 1)
        self.assertEqual(urls.count("http://b:11434"), 1)
        self.assertEqual(urls[-1], "http://localhost:11434")

    def test_num_ctx_and_keep_alive_config(self):
        self.assertIsNone(oc.ollama_num_ctx())
        self.assertEqual(oc.ollama_keep_alive(), "5m")
        os.environ["PEDESK_GUIDE_OLLAMA_NUM_CTX"] = "8192"
        os.environ["PEDESK_GUIDE_OLLAMA_KEEP_ALIVE"] = "30m"
        self.assertEqual(oc.ollama_num_ctx(), 8192)
        self.assertEqual(oc.ollama_keep_alive(), "30m")


class ChatResilience(unittest.TestCase):
    def setUp(self):
        os.environ["PEDESK_GUIDE_OLLAMA_ENABLED"] = "true"
        os.environ["PEDESK_GUIDE_OLLAMA_BASE_URL"] = "http://h1:11434,http://h2:11434"
        os.environ["PEDESK_GUIDE_OLLAMA_RETRIES"] = "1"

    def tearDown(self):
        for k in ("PEDESK_GUIDE_OLLAMA_ENABLED", "PEDESK_GUIDE_OLLAMA_BASE_URL",
                  "PEDESK_GUIDE_OLLAMA_RETRIES", "PEDESK_GUIDE_OLLAMA_NUM_CTX"):
            os.environ.pop(k, None)

    def test_fails_over_to_second_host(self):
        chat_ok = _resp({"message": {"content": "hello from h2"}})

        def fake_urlopen(req, timeout=None):
            if "h1:11434" in req.full_url:
                raise urllib.error.URLError("connection refused")
            return chat_ok

        with mock.patch.object(oc.urllib.request, "urlopen",
                               side_effect=fake_urlopen):
            out = oc.call_ollama_chat("sys", "user")
        self.assertEqual(out, "hello from h2")

    def test_retries_then_succeeds_same_host(self):
        calls = {"n": 0}
        ok = _resp({"message": {"content": "warmed up"}})

        def flaky(req, timeout=None):
            calls["n"] += 1
            if calls["n"] == 1:
                raise TimeoutError("model loading")
            return ok

        with mock.patch.object(oc.urllib.request, "urlopen", side_effect=flaky), \
                mock.patch.object(oc.time, "sleep", return_value=None):
            out = oc.call_ollama_chat("sys", "user")
        self.assertEqual(out, "warmed up")
        self.assertGreaterEqual(calls["n"], 2)  # retried at least once

    def test_all_hosts_down_raises_aggregated(self):
        with mock.patch.object(oc.urllib.request, "urlopen",
                               side_effect=urllib.error.URLError("down")), \
                mock.patch.object(oc.time, "sleep", return_value=None):
            with self.assertRaises(oc.OllamaError) as ctx:
                oc.call_ollama_chat("sys", "user")
        msg = str(ctx.exception)
        self.assertIn("h1:11434", msg)
        self.assertIn("h2:11434", msg)

    def test_num_ctx_and_keep_alive_sent_in_payload(self):
        os.environ["PEDESK_GUIDE_OLLAMA_NUM_CTX"] = "8192"
        captured = {}

        def capture(req, timeout=None):
            captured["body"] = json.loads(req.data.decode("utf-8"))
            return _resp({"message": {"content": "ok"}})

        with mock.patch.object(oc.urllib.request, "urlopen", side_effect=capture):
            oc.call_ollama_chat("sys", "user", temperature=0.1)
        self.assertEqual(captured["body"]["options"]["num_ctx"], 8192)
        self.assertEqual(captured["body"]["options"]["temperature"], 0.1)
        self.assertEqual(captured["body"]["keep_alive"], "5m")

    def test_disabled_raises_without_calling(self):
        os.environ.pop("PEDESK_GUIDE_OLLAMA_ENABLED", None)
        with self.assertRaises(oc.OllamaError):
            oc.call_ollama_chat("sys", "user")


if __name__ == "__main__":
    unittest.main()
