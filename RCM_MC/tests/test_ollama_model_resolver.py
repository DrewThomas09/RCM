"""The Guide resolves to an installed chat model so a model-name mismatch
(e.g. a default that was never ``ollama pull``-ed) never 503s the live Guide.

The user's intent is "only the free Ollama Gemma model if possible", so the
fallback prefers an installed Gemma before any other chat model, and never
picks an embedding model. ``list_models`` is mocked — it is the only external
(Ollama HTTP) call in the path.
"""
import unittest
from unittest import mock

from rcm_mc.assistant import ollama_client as oc


class TestOllamaModelResolver(unittest.TestCase):
    def _resolve(self, installed, preferred="gemma4:e4b"):
        with mock.patch.object(oc, "list_models", return_value=installed):
            return oc.ollama_resolve_chat_model(preferred)

    def test_configured_model_installed_is_used(self):
        self.assertEqual(
            self._resolve(["gemma4:e4b", "nomic-embed-text"]), "gemma4:e4b")

    def test_unreachable_returns_configured(self):
        # empty install list = host unreachable → keep configured so the clean
        # OllamaError path downstream is unchanged.
        self.assertEqual(self._resolve([]), "gemma4:e4b")

    def test_same_family_fallback(self):
        # configured gemma3:4b missing, another gemma3 tag installed → use it.
        self.assertEqual(
            self._resolve(["gemma3:12b", "nomic-embed-text"], preferred="gemma3:4b"),
            "gemma3:12b",
        )

    def test_any_gemma_preferred_over_other_chat_model(self):
        # configured tag missing, no same-family → a free Gemma is chosen over a
        # non-Gemma chat model ("only the free Gemma model if possible").
        self.assertEqual(
            self._resolve(["llama3:8b", "gemma2:2b", "nomic-embed-text"]),
            "gemma2:2b",
        )

    def test_non_embedding_last_resort(self):
        # no Gemma at all → fall back to a non-embedding chat model, never the
        # embedding model.
        self.assertEqual(
            self._resolve(["nomic-embed-text", "llama3:8b"]), "llama3:8b")

    def test_only_embedding_models_returns_configured(self):
        # nothing usable for chat → return configured so the caller surfaces a
        # clean error rather than silently embedding-as-chat.
        self.assertEqual(self._resolve(["nomic-embed-text"]), "gemma4:e4b")


if __name__ == "__main__":
    unittest.main()
