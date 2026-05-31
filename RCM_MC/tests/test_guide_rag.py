"""Local RAG layer — document sources, chunking, vector store, prompt
context. No real Ollama: vectors are supplied directly to the store."""
from __future__ import annotations

import os
import tempfile
import unittest

from rcm_mc.assistant.rag import vector_store
from rcm_mc.assistant.rag.chunking import chunk_document, chunk_documents
from rcm_mc.assistant.rag.document_sources import iter_guide_documents
from rcm_mc.assistant.rag.rag_prompt_context import (
    citation_line,
    format_rag_context,
    rag_sources_used,
)
from rcm_mc.assistant.rag.types import RagDocument, RagSearchResult


class DocumentSourceTests(unittest.TestCase):
    def setUp(self):
        self.docs = iter_guide_documents()
        self.by_type = {}
        for d in self.docs:
            self.by_type.setdefault(d.source_type, []).append(d)

    def test_page_contexts_become_documents(self):
        pages = self.by_type.get("page_context", [])
        self.assertGreaterEqual(len(pages), 70)
        hcris = [d for d in pages if d.route == "/diligence/hcris-xray"]
        self.assertTrue(hcris)
        self.assertIn("HCRIS", hcris[0].text)

    def test_metric_registry_becomes_documents(self):
        metrics = self.by_type.get("metric", [])
        self.assertGreaterEqual(len(metrics), 50)
        dr = [d for d in metrics if d.metric_id == "denial_rate"]
        self.assertTrue(dr)
        self.assertIn("Definition", dr[0].text)

    def test_data_sources_become_documents(self):
        sources = self.by_type.get("data_source", [])
        self.assertGreaterEqual(len(sources), 30)
        hcris = [d for d in sources if d.data_source_id == "cms_hcris"]
        self.assertTrue(hcris)
        self.assertIn("Medicare", hcris[0].text)

    def test_policy_and_docs_present(self):
        self.assertTrue(self.by_type.get("guide_policy"))
        self.assertTrue(self.by_type.get("doc"))

    def test_no_unsafe_sources_indexed(self):
        # No secrets/sessions/credentials/audit-log content slips in.
        blob = "\n".join(d.text.lower() for d in self.docs)
        for bad in ("password=", "secret_key", "session_token",
                    "scrypt", "csrf_secret"):
            self.assertNotIn(bad, blob)


class ChunkingTests(unittest.TestCase):
    def test_registry_entry_is_single_chunk(self):
        doc = RagDocument(source_id="metric:x", source_type="metric",
                          title="X", text="Metric: X\nDefinition: short.",
                          metric_id="x")
        chunks = chunk_document(doc)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].metric_id, "x")
        self.assertEqual(chunks[0].source_type, "metric")
        self.assertTrue(chunks[0].content_hash)

    def test_long_doc_splits_into_multiple_chunks(self):
        big = "\n\n".join(["paragraph %d %s" % (i, "word " * 80)
                           for i in range(40)])
        doc = RagDocument(source_id="doc:big", source_type="doc",
                          title="Big", text=big, file_path="docs/big.md")
        chunks = chunk_document(doc)
        self.assertGreater(len(chunks), 1)
        for c in chunks:
            self.assertEqual(c.title, "Big")
            self.assertEqual(c.file_path, "docs/big.md")
            self.assertTrue(c.section)

    def test_chunk_metadata_round_trips(self):
        chunks = chunk_documents(iter_guide_documents())
        self.assertGreater(len(chunks), 100)
        m = chunks[0].metadata()
        for key in ("source_id", "source_type", "title", "route",
                    "metric_id", "data_source_id"):
            self.assertIn(key, m)


class VectorStoreTests(unittest.TestCase):
    def _store(self, tmp):
        return vector_store.connect(os.path.join(tmp, "rag.sqlite3"))

    def _chunk(self, sid, text):
        from rcm_mc.assistant.rag.chunking import chunk_document
        return chunk_document(RagDocument(
            source_id=sid, source_type="metric", title=sid, text=text,
            metric_id=sid))[0]

    def test_upsert_and_cosine_search(self):
        with tempfile.TemporaryDirectory() as tmp:
            con = self._store(tmp)
            # Two orthogonal-ish vectors; query closer to the first.
            vector_store.upsert_chunk(con, self._chunk("a", "alpha alpha"),
                                      [1.0, 0.0, 0.0], "mock")
            vector_store.upsert_chunk(con, self._chunk("b", "beta beta"),
                                      [0.0, 1.0, 0.0], "mock")
            con.commit()
            self.assertEqual(vector_store.count_chunks(con), 2)
            self.assertEqual(vector_store.count_embedded(con), 2)
            results = vector_store.search_similar(con, [0.9, 0.1, 0.0], top_k=2)
            self.assertEqual(len(results), 2)
            self.assertEqual(results[0].title, "a")   # nearest first
            self.assertGreater(results[0].score, results[1].score)
            con.close()

    def test_upsert_idempotent_by_content_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            con = self._store(tmp)
            c = self._chunk("a", "alpha")
            vector_store.upsert_chunk(con, c, [1.0, 0.0], "mock")
            vector_store.upsert_chunk(con, c, [1.0, 0.0], "mock")  # same hash
            con.commit()
            self.assertEqual(vector_store.count_chunks(con), 1)
            con.close()

    def test_delete_stale_chunks(self):
        with tempfile.TemporaryDirectory() as tmp:
            con = self._store(tmp)
            ca = self._chunk("a", "alpha"); cb = self._chunk("b", "beta")
            vector_store.upsert_chunk(con, ca, [1.0], "mock")
            vector_store.upsert_chunk(con, cb, [1.0], "mock")
            con.commit()
            removed = vector_store.delete_stale_chunks(con, {ca.content_hash})
            con.commit()
            self.assertEqual(removed, 1)
            self.assertEqual(vector_store.count_chunks(con), 1)
            con.close()

    def test_search_skips_dimension_mismatched_vectors(self):
        with tempfile.TemporaryDirectory() as tmp:
            con = self._store(tmp)
            vector_store.upsert_chunk(con, self._chunk("good", "g"),
                                      [1.0, 0.0, 0.0], "mock")
            # Stale/other-model vector of a different dimension.
            vector_store.upsert_chunk(con, self._chunk("bad", "b"),
                                      [0.5, 0.5], "other")
            con.commit()
            results = vector_store.search_similar(con, [1.0, 0.0, 0.0], top_k=5)
            titles = [r.title for r in results]
            self.assertIn("good", titles)
            self.assertNotIn("bad", titles)  # mismatched dim skipped
            con.close()

    def test_empty_index_search_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            con = self._store(tmp)
            self.assertEqual(vector_store.search_similar(con, [1.0], top_k=5), [])
            con.close()


class IndexStatusTests(unittest.TestCase):
    def test_missing_index_status(self):
        from rcm_mc.assistant.rag import retrieval
        st = retrieval.index_status(
            os.path.join(tempfile.gettempdir(), "definitely_missing.sqlite3"))
        self.assertFalse(st["exists"])
        self.assertEqual(st["chunk_count"], 0)

    def test_populated_index_status(self):
        from rcm_mc.assistant.rag import retrieval
        from rcm_mc.assistant.rag.chunking import chunk_document
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "rag.sqlite3")
            con = vector_store.connect(path)
            c = chunk_document(RagDocument(
                source_id="metric:x", source_type="metric", title="X",
                text="Metric: X", metric_id="x"))[0]
            vector_store.upsert_chunk(con, c, [1.0, 2.0], "nomic-embed-text")
            con.commit(); con.close()
            st = retrieval.index_status(path)
            self.assertTrue(st["exists"])
            self.assertEqual(st["chunk_count"], 1)
            self.assertEqual(st["embedded_count"], 1)
            self.assertEqual(st["embedding_models"], ["nomic-embed-text"])


class PromptContextTests(unittest.TestCase):
    def _results(self):
        return [
            RagSearchResult(title="Denial Rate", source_type="metric",
                            text="Share of claims initially denied.",
                            score=0.91, metric_id="denial_rate"),
            RagSearchResult(title="CMS HCRIS", source_type="data_source",
                            text="Medicare hospital cost reports.",
                            score=0.84, data_source_id="cms_hcris"),
        ]

    def test_format_rag_context(self):
        ctx = format_rag_context(self._results())
        self.assertIn("Additional local Guide context", ctx)
        self.assertIn("Metric Registry — Denial Rate", ctx)
        self.assertIn("Data Source Registry — CMS HCRIS", ctx)
        self.assertIn("PRIMARY", ctx)
        # explicit not-target-data instruction
        self.assertIn("Do NOT treat retrieved context as target-specific", ctx)
        # labeled with source_type + id
        self.assertIn("[metric · denial_rate]", ctx)
        self.assertIn("[data_source · cms_hcris]", ctx)

    def test_format_empty(self):
        self.assertEqual(format_rag_context([]), "")

    def test_sources_used_metadata(self):
        used = rag_sources_used(self._results())
        self.assertEqual(len(used), 2)
        self.assertEqual(used[0]["title"], "Denial Rate")
        self.assertEqual(used[0]["source_type"], "metric")
        self.assertIn("score", used[0])

    def test_citation_line(self):
        self.assertIn("Guide context used:", citation_line(self._results()))


class RetrievalDedupeTests(unittest.TestCase):
    """The per-source diversity cap (search() over-fetches then trims)."""

    def _r(self, title, stype, score, **ids):
        return RagSearchResult(title=title, source_type=stype, text="x",
                               score=score, **ids)

    def test_caps_chunks_per_source(self):
        from rcm_mc.assistant.rag.retrieval import dedupe_keep_diverse
        # Three chunks from the same doc would otherwise dominate the top-3.
        results = [
            self._r("Denial doc", "doc", 0.95, source_id="d1"),
            self._r("Denial doc", "doc", 0.94, source_id="d1"),
            self._r("Denial doc", "doc", 0.93, source_id="d1"),
            self._r("Denial Rate", "metric", 0.80, metric_id="denial_rate"),
        ]
        out = dedupe_keep_diverse(results, k=3, per_source=2)
        # at most 2 from the doc, leaving room for the metric source
        self.assertEqual(len(out), 3)
        self.assertEqual(sum(1 for r in out if r.source_id == "d1"), 2)
        self.assertIn("denial_rate", [r.metric_id for r in out])

    def test_preserves_score_order_and_k(self):
        from rcm_mc.assistant.rag.retrieval import dedupe_keep_diverse
        results = [
            self._r("A", "metric", 0.9, metric_id="a"),
            self._r("B", "metric", 0.8, metric_id="b"),
            self._r("C", "metric", 0.7, metric_id="c"),
        ]
        out = dedupe_keep_diverse(results, k=2, per_source=2)
        self.assertEqual([r.title for r in out], ["A", "B"])

    def test_distinct_sources_not_dropped(self):
        from rcm_mc.assistant.rag.retrieval import dedupe_keep_diverse
        results = [
            self._r("A", "metric", 0.9, metric_id="a"),
            self._r("B", "data_source", 0.8, data_source_id="b"),
        ]
        out = dedupe_keep_diverse(results, k=5, per_source=2)
        self.assertEqual(len(out), 2)


class ExactMetricPromotionTests(unittest.TestCase):
    """Reorder-only promotion of an exactly-named metric."""

    def _r(self, title, stype, score, **ids):
        return RagSearchResult(title=title, source_type=stype, text="x",
                               score=score, **ids)

    ALIASES = {"denial rate": "denial_rate", "clean dar": "clean_dar"}

    def test_named_metric_is_promoted_to_front(self):
        from rcm_mc.assistant.rag.retrieval import promote_exact_metric_match
        results = [
            self._r("Some doc", "doc", 0.92, source_id="d1"),
            self._r("Denial Rate", "metric", 0.71, metric_id="denial_rate"),
        ]
        out = promote_exact_metric_match(
            results, "What does denial rate mean?", self.ALIASES)
        self.assertEqual(out[0].metric_id, "denial_rate")
        self.assertEqual(len(out), len(results))  # reorder only, no drops

    def test_no_named_metric_keeps_order(self):
        from rcm_mc.assistant.rag.retrieval import promote_exact_metric_match
        results = [
            self._r("Doc", "doc", 0.9, source_id="d1"),
            self._r("Metric", "metric", 0.8, metric_id="denial_rate"),
        ]
        out = promote_exact_metric_match(
            results, "How is the platform doing overall?", self.ALIASES)
        self.assertEqual([r.title for r in out], ["Doc", "Metric"])

    def test_substring_does_not_falsely_match(self):
        # "moderate" must not trigger the "rate" family; aliases match as
        # whole space-delimited phrases only.
        from rcm_mc.assistant.rag.retrieval import promote_exact_metric_match
        results = [self._r("Doc", "doc", 0.9, source_id="d1")]
        out = promote_exact_metric_match(
            results, "is growth moderate here?", {"rate": "denial_rate"})
        self.assertEqual([r.title for r in out], ["Doc"])

    def test_alias_map_built_from_registry(self):
        from rcm_mc.assistant.rag.retrieval import metric_alias_map
        m = metric_alias_map()
        self.assertIsInstance(m, dict)
        self.assertTrue(m)  # registry has metrics
        # values are metric_ids (strings)
        self.assertTrue(all(isinstance(v, str) for v in m.values()))


if __name__ == "__main__":
    unittest.main()
