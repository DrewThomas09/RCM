"""Tests for the ai/ package — LLM client, memo writer, conversation, document QA.

ALL LLM calls are mocked.  No real API calls are made.
"""
from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional
from unittest.mock import MagicMock, patch

from rcm_mc.ai.llm_client import (
    LLMClient,
    LLMResponse,
    _ensure_tables,
    _lookup_cache,
    _prompt_hash,
    _save_cache,
)
from rcm_mc.ai.memo_writer import (
    ComposedMemo,
    SectionDraft,
    _extract_numbers,
    _fact_check,
    compose_memo,
)
from rcm_mc.ai.conversation import (
    ConversationEngine,
    ConversationResponse,
    _ensure_table as _ensure_conv_table,
    _load_history,
    _save_message,
)
from rcm_mc.ai.document_qa import (
    ChunkMatch,
    DocumentAnswer,
    DocumentIndex,
    _split_into_chunks,
    _tokenize,
    answer_question,
    index_document,
    query_documents,
)


# ── Minimal store for testing ────────────────────────────────────────

class _TestStore:
    """Lightweight SQLite store matching PortfolioStore's interface."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA busy_timeout = 5000")
        try:
            yield con
        finally:
            con.close()

    def init_db(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as con:
            con.execute(
                """CREATE TABLE IF NOT EXISTS deals (
                    deal_id TEXT PRIMARY KEY,
                    name TEXT,
                    created_at TEXT,
                    profile_json TEXT
                )"""
            )
            con.commit()


# ── Fake packet for memo tests ──────────────────────────────────────

@dataclass
class _FakeMetric:
    value: float


@dataclass
class _FakeCompleteness:
    grade: str = "B+"


@dataclass
class _FakeBridge:
    total_ebitda_impact: float = 5_000_000.0


@dataclass
class _FakePacket:
    deal_id: str = "DEAL001"
    deal_name: str = "Test Hospital"
    model_version: str = "1.0"
    observed_metrics: Optional[Dict[str, _FakeMetric]] = None
    completeness: Optional[_FakeCompleteness] = None
    ebitda_bridge: Optional[_FakeBridge] = None
    risk_flags: list = field(default_factory=list)
    diligence_questions: list = field(default_factory=list)
    revenue: float = 10_000_000.0
    margin: float = 15.3


# =====================================================================
# 1. LLM Client tests
# =====================================================================

class TestLLMClientFallback(unittest.TestCase):
    """Graceful no-op when API key is not configured."""

    @patch.dict(os.environ, {}, clear=True)
    def test_no_api_key_returns_fallback(self):
        # Remove ANTHROPIC_API_KEY if present
        os.environ.pop("ANTHROPIC_API_KEY", None)
        client = LLMClient()
        resp = client.complete("system", "user")
        self.assertEqual(resp.text, "[LLM not configured]")
        self.assertEqual(resp.model, "fallback")
        self.assertEqual(resp.input_tokens, 0)
        self.assertEqual(resp.cost_usd_estimate, 0.0)

    @patch.dict(os.environ, {}, clear=True)
    def test_is_configured_false_without_key(self):
        os.environ.pop("ANTHROPIC_API_KEY", None)
        client = LLMClient()
        self.assertFalse(client.is_configured)

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test-123"})
    def test_is_configured_true_with_key(self):
        client = LLMClient()
        self.assertTrue(client.is_configured)


class TestLLMClientCaching(unittest.TestCase):
    """Cache table prevents duplicate API calls for identical prompts."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._db = os.path.join(self._tmpdir, "test.db")
        self._store = _TestStore(self._db)

    def test_cache_round_trip(self):
        phash = _prompt_hash("sys", "usr")
        resp = LLMResponse(
            text="cached answer", model="claude-haiku-4-5",
            input_tokens=10, output_tokens=20,
        )
        _save_cache(self._store, phash, resp)
        cached = _lookup_cache(self._store, phash, "claude-haiku-4-5")
        self.assertIsNotNone(cached)
        self.assertEqual(cached.text, "cached answer")
        self.assertEqual(cached.input_tokens, 10)

    def test_cache_miss_different_prompt(self):
        phash = _prompt_hash("sys", "usr")
        resp = LLMResponse(text="answer", model="claude-haiku-4-5")
        _save_cache(self._store, phash, resp)
        other = _lookup_cache(self._store, _prompt_hash("other", "prompt"), "claude-haiku-4-5")
        self.assertIsNone(other)

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    @patch("rcm_mc.ai.llm_client.urllib.request.urlopen")
    def test_cached_response_skips_api(self, mock_urlopen):
        """Second call with same prompt must not hit the API."""
        # Pre-seed cache
        phash = _prompt_hash("system", "user")
        resp = LLMResponse(text="from cache", model="claude-haiku-4-5",
                           input_tokens=5, output_tokens=10)
        _save_cache(self._store, phash, resp)

        client = LLMClient(store=self._store)
        result = client.complete("system", "user")
        self.assertEqual(result.text, "from cache")
        mock_urlopen.assert_not_called()


class TestLLMClientCostTracking(unittest.TestCase):
    """Cost tracking in the llm_calls table."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._db = os.path.join(self._tmpdir, "test.db")
        self._store = _TestStore(self._db)

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    @patch("rcm_mc.ai.llm_client.urllib.request.urlopen")
    def test_call_logged_to_db(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"content":[{"type":"text","text":"hi"}],"usage":{"input_tokens":100,"output_tokens":50}}'
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        client = LLMClient(store=self._store)
        result = client.complete("sys", "usr")
        self.assertEqual(result.text, "hi")
        self.assertEqual(result.input_tokens, 100)
        self.assertEqual(result.output_tokens, 50)
        self.assertGreater(result.cost_usd_estimate, 0)

        # Verify DB row
        with self._store.connect() as con:
            row = con.execute("SELECT * FROM llm_calls").fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["input_tokens"], 100)


# =====================================================================
# 2. Memo Writer tests
# =====================================================================

class TestExtractNumbers(unittest.TestCase):

    def test_dollar_amounts(self):
        nums = _extract_numbers("Revenue was $10M and costs were $2.5K")
        self.assertIn(10_000_000, nums)
        self.assertIn(2500, nums)

    def test_percentages(self):
        nums = _extract_numbers("Denial rate is 15.3% and margin at 22%")
        self.assertIn(15.3, nums)
        self.assertIn(22.0, nums)

    def test_mixed(self):
        nums = _extract_numbers("$4.5M EBITDA with 12.1% margin")
        self.assertEqual(len(nums), 2)

    def test_no_numbers(self):
        nums = _extract_numbers("No numbers here.")
        self.assertEqual(nums, [])


class TestFactCheck(unittest.TestCase):

    def test_valid_numbers_pass(self):
        packet = _FakePacket(revenue=10_000_000.0, margin=15.3)
        warnings = _fact_check([10_000_000.0, 15.3], packet)
        self.assertEqual(warnings, [])

    def test_fabricated_number_caught(self):
        packet = _FakePacket(revenue=10_000_000.0, margin=15.3)
        warnings = _fact_check([99_999_999.0], packet)
        self.assertTrue(len(warnings) > 0)
        self.assertIn("99999999.0", warnings[0])

    def test_tolerance_within_1_percent(self):
        packet = _FakePacket(revenue=10_000_000.0)
        # 1% of 10M = 100K, so 10_050_000 is within tolerance
        warnings = _fact_check([10_050_000.0], packet)
        self.assertEqual(warnings, [])

    def test_tolerance_beyond_1_percent(self):
        packet = _FakePacket(revenue=10_000_000.0)
        # 2% off should fail
        warnings = _fact_check([10_200_000.0], packet)
        self.assertTrue(len(warnings) > 0)


class TestComposeMemo(unittest.TestCase):

    def test_template_mode_no_llm(self):
        packet = _FakePacket(completeness=_FakeCompleteness(grade="A"))
        memo = compose_memo(packet, use_llm=False)
        self.assertIn("executive_summary", memo.sections)
        self.assertIn("Test Hospital", memo.sections["executive_summary"].text)
        self.assertEqual(memo.total_cost_usd, 0.0)
        self.assertTrue(memo.sections["executive_summary"].fact_checks_passed)

    def test_template_mode_all_sections(self):
        packet = _FakePacket(
            completeness=_FakeCompleteness(),
            ebitda_bridge=_FakeBridge(),
        )
        memo = compose_memo(packet)
        self.assertEqual(len(memo.sections), 5)

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_llm_mode_with_mock(self):
        packet = _FakePacket(revenue=10_000_000.0, margin=15.3)
        mock_client = MagicMock(spec=LLMClient)
        mock_client.is_configured = True
        mock_client.complete.return_value = LLMResponse(
            text="Revenue is $10M with 15.3% margin.",
            model="claude-haiku-4-5",
            input_tokens=100, output_tokens=50,
            cost_usd_estimate=0.001,
        )
        memo = compose_memo(packet, use_llm=True, llm_client=mock_client)
        self.assertGreater(memo.total_cost_usd, 0)
        # All sections should pass fact check since numbers match packet
        for section in memo.sections.values():
            self.assertTrue(section.fact_checks_passed)

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_llm_mode_catches_hallucination(self):
        packet = _FakePacket(revenue=10_000_000.0)
        mock_client = MagicMock(spec=LLMClient)
        mock_client.is_configured = True
        mock_client.complete.return_value = LLMResponse(
            text="Revenue is $50M which is very high.",
            model="claude-haiku-4-5",
            cost_usd_estimate=0.001,
        )
        memo = compose_memo(packet, use_llm=True, llm_client=mock_client)
        # $50M = 50_000_000 is not in packet → warning
        self.assertTrue(len(memo.fact_check_warnings) > 0)


# =====================================================================
# 3. Conversation tests
# =====================================================================

class TestConversationFallback(unittest.TestCase):

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._db = os.path.join(self._tmpdir, "conv.db")
        self._store = _TestStore(self._db)

    @patch.dict(os.environ, {}, clear=True)
    def test_no_api_key_returns_fallback(self):
        os.environ.pop("ANTHROPIC_API_KEY", None)
        engine = ConversationEngine(self._store)
        resp = engine.process_message("sess1", "hello", self._store)
        self.assertIn("/screen", resp.answer_text)
        self.assertEqual(resp.tool_calls_made, [])

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_tool_dispatch_find_deals(self):
        mock_client = MagicMock(spec=LLMClient)
        mock_client.is_configured = True
        mock_client.complete.return_value = LLMResponse(
            text="I found some deals for you.",
            model="claude-haiku-4-5",
        )
        engine = ConversationEngine(self._store, llm_client=mock_client)
        resp = engine.process_message("sess1", "find deals in IL", self._store)
        self.assertIn("find_deals", resp.tool_calls_made)

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_tool_dispatch_portfolio_stats(self):
        mock_client = MagicMock(spec=LLMClient)
        mock_client.is_configured = True
        mock_client.complete.return_value = LLMResponse(
            text="Portfolio has 10 deals.", model="claude-haiku-4-5",
        )
        engine = ConversationEngine(self._store, llm_client=mock_client)
        resp = engine.process_message("sess1", "how many total deals in portfolio", self._store)
        self.assertIn("get_portfolio_stats", resp.tool_calls_made)


class TestConversationSessions(unittest.TestCase):

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._db = os.path.join(self._tmpdir, "conv.db")
        self._store = _TestStore(self._db)

    def test_session_persistence(self):
        _save_message(self._store, "s1", "user", "hello")
        _save_message(self._store, "s1", "assistant", "hi there")
        history = _load_history(self._store, "s1")
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[1]["content"], "hi there")

    def test_sessions_isolated(self):
        _save_message(self._store, "s1", "user", "msg1")
        _save_message(self._store, "s2", "user", "msg2")
        h1 = _load_history(self._store, "s1")
        h2 = _load_history(self._store, "s2")
        self.assertEqual(len(h1), 1)
        self.assertEqual(len(h2), 1)
        self.assertEqual(h1[0]["content"], "msg1")


# =====================================================================
# 4. Document QA tests
# =====================================================================

class TestDocumentChunking(unittest.TestCase):

    def test_short_text_single_chunk(self):
        chunks = _split_into_chunks("A short sentence.")
        self.assertEqual(len(chunks), 1)

    def test_long_text_multiple_chunks(self):
        text = "This is a sentence. " * 100  # ~2000 chars
        chunks = _split_into_chunks(text, chunk_size=500)
        self.assertGreater(len(chunks), 1)
        for c in chunks:
            # Allow some tolerance for sentence boundary splitting
            self.assertLessEqual(len(c), 500 * 1.6)

    def test_empty_text(self):
        self.assertEqual(_split_into_chunks(""), [])

    def test_chunk_count_correct(self):
        # 10 sentences of ~50 chars each = ~500 chars total
        text = "Hello world this is a test. " * 20  # ~540 chars
        chunks = _split_into_chunks(text, chunk_size=200)
        self.assertGreater(len(chunks), 1)


class TestDocumentIndex(unittest.TestCase):

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._db = os.path.join(self._tmpdir, "doc.db")
        self._store = _TestStore(self._db)

    def test_index_document_creates_chunks(self):
        doc_path = os.path.join(self._tmpdir, "report.txt")
        text = "This is the first sentence. " * 40
        Path(doc_path).write_text(text)
        count = index_document(self._store, "DEAL001", doc_path)
        self.assertGreater(count, 0)
        # Verify in DB
        with self._store.connect() as con:
            rows = con.execute(
                "SELECT COUNT(*) as cnt FROM document_chunks WHERE deal_id = ?",
                ("DEAL001",),
            ).fetchone()
        self.assertEqual(rows["cnt"], count)

    def test_index_document_preserves_name(self):
        doc_path = os.path.join(self._tmpdir, "financials.txt")
        Path(doc_path).write_text("Some financial data here. Revenue is strong.")
        index_document(self._store, "DEAL002", doc_path)
        with self._store.connect() as con:
            row = con.execute(
                "SELECT document_name FROM document_chunks WHERE deal_id = ? LIMIT 1",
                ("DEAL002",),
            ).fetchone()
        self.assertEqual(row["document_name"], "financials.txt")


class TestDocumentSearch(unittest.TestCase):

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._db = os.path.join(self._tmpdir, "doc.db")
        self._store = _TestStore(self._db)
        # Index a multi-topic document
        doc_path = os.path.join(self._tmpdir, "analysis.txt")
        text = (
            "The hospital denial rate has been increasing over the past quarter. "
            "Initial denial rates rose from 8% to 12% driven by payer mix changes. "
            "Management has implemented new pre-authorization workflows. "
            "Revenue cycle improvements are expected to reduce denials by 3 percentage points. "
            "The facility has 250 beds and operates in Illinois. "
            "EBITDA margins have compressed due to labor cost inflation. "
            "Working capital requirements remain stable at current levels. "
            "The surgical volume has increased by 15% year over year. "
        )
        Path(doc_path).write_text(text)
        index_document(self._store, "DEAL001", doc_path)

    def test_keyword_search_returns_relevant(self):
        results = query_documents(self._store, "DEAL001", "denial rate")
        self.assertGreater(len(results), 0)
        # Top result should mention denial
        self.assertIn("denial", results[0].text_snippet.lower())

    def test_keyword_search_empty_deal(self):
        results = query_documents(self._store, "NONEXISTENT", "denial rate")
        self.assertEqual(results, [])

    def test_top_k_limits_results(self):
        results = query_documents(self._store, "DEAL001", "hospital", top_k=2)
        self.assertLessEqual(len(results), 2)


class TestDocumentAnswer(unittest.TestCase):

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._db = os.path.join(self._tmpdir, "doc.db")
        self._store = _TestStore(self._db)
        doc_path = os.path.join(self._tmpdir, "report.txt")
        Path(doc_path).write_text(
            "The denial rate is 12%. Revenue is $50M. "
            "The hospital has strong surgical volumes."
        )
        index_document(self._store, "DEAL001", doc_path)

    @patch.dict(os.environ, {}, clear=True)
    def test_fallback_without_llm(self):
        os.environ.pop("ANTHROPIC_API_KEY", None)
        ans = answer_question(self._store, "DEAL001", "What is the denial rate?")
        self.assertIn("relevant passages", ans.answer_text.lower())
        self.assertGreater(len(ans.cited_chunks), 0)
        self.assertEqual(ans.confidence, 0.5)

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"})
    def test_llm_synthesis(self):
        mock_client = MagicMock(spec=LLMClient)
        mock_client.is_configured = True
        mock_client.complete.return_value = LLMResponse(
            text="The denial rate is 12% according to report.txt page 1.",
            model="claude-haiku-4-5",
        )
        ans = answer_question(
            self._store, "DEAL001", "denial rate",
            llm_client=mock_client,
        )
        self.assertIn("12%", ans.answer_text)
        self.assertGreater(len(ans.cited_chunks), 0)

    def test_no_documents_found(self):
        ans = answer_question(self._store, "NO_DEAL", "anything")
        self.assertIn("No relevant documents", ans.answer_text)
        self.assertEqual(ans.confidence, 0.0)


if __name__ == "__main__":
    unittest.main()
