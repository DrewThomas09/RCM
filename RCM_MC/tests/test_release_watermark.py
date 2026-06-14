"""Tests for the release-detection watermark (front of the ingest pipe).

No network: HTTP fingerprints are exercised via a fake header mapping
and via monkeypatched ``http_head_fingerprint``; the orchestrator hook
is exercised with injected refreshers + fingerprints. See
``SECOND_AGENT_BUILD_PROMPT.md`` Appendix A.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from rcm_mc.data import data_refresh as dr
from rcm_mc.data import release_watermark as rw
from rcm_mc.portfolio.store import PortfolioStore


def _temp_store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    s = PortfolioStore(path)
    s.init_db()
    return s, path


class _Headers:
    """Minimal stand-in for an http.client HTTPMessage."""

    def __init__(self, data):
        self._data = {k.lower(): v for k, v in data.items()}

    def get(self, key, default=None):
        return self._data.get(key.lower(), default)


class FingerprintTests(unittest.TestCase):
    def test_etag_preferred_over_last_modified(self):
        fp = rw.fingerprint_from_http_headers(_Headers({
            "ETag": '"abc123"',
            "Last-Modified": "Wed, 21 Oct 2025 07:28:00 GMT",
            "Content-Length": "999",
        }))
        self.assertEqual(fp, 'etag:"abc123"')

    def test_last_modified_normalized_to_iso(self):
        # Two spellings of the same instant compare equal.
        a = rw.fingerprint_from_http_headers(_Headers({
            "Last-Modified": "Wed, 21 Oct 2025 07:28:00 GMT",
            "Content-Length": "100",
        }))
        b = rw.fingerprint_from_http_headers(_Headers({
            "last-modified": "Wed, 21 Oct 2025 07:28:00 +0000",
            "content-length": "100",
        }))
        self.assertEqual(a, b)
        self.assertIn("2025-10-21T07:28:00", a)

    def test_no_validators_returns_none(self):
        self.assertIsNone(rw.fingerprint_from_http_headers(_Headers({})))
        self.assertIsNone(rw.fingerprint_from_http_headers(None))

    def test_file_stat_fingerprint_changes_with_content(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "f.csv"
            p.write_bytes(b"a")
            fp1 = rw.file_stat_fingerprint(p)
            p.write_bytes(b"aaaaaa")  # size changes
            fp2 = rw.file_stat_fingerprint(p)
            self.assertIsNotNone(fp1)
            self.assertNotEqual(fp1, fp2)

    def test_file_stat_fingerprint_missing_is_none(self):
        self.assertIsNone(rw.file_stat_fingerprint("/no/such/path.csv"))

    def test_content_fingerprint_stable_and_sensitive(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "f.bin"
            p.write_bytes(b"hello world" * 1000)
            fp1 = rw.file_content_fingerprint(p)
            fp2 = rw.file_content_fingerprint(p)
            self.assertEqual(fp1, fp2)
            self.assertTrue(fp1.startswith("sha256:"))
            p.write_bytes(b"hello worlx" * 1000)
            self.assertNotEqual(fp1, rw.file_content_fingerprint(p))

    def test_http_head_fingerprint_never_raises_offline(self):
        # Unroutable host: must degrade to None, not raise.
        fp = rw.http_head_fingerprint(
            "http://127.0.0.1:1/nope", timeout=0.05)
        self.assertIsNone(fp)


class WatermarkStoreTests(unittest.TestCase):
    def setUp(self):
        self.store, self.path = _temp_store()

    def tearDown(self):
        try:
            os.remove(self.path)
        except OSError:
            pass

    def test_unknown_source_is_changed(self):
        self.assertTrue(rw.is_release_changed(self.store, "hcris", "etag:x"))

    def test_record_then_same_fingerprint_is_unchanged(self):
        rw.record_release(self.store, "hcris", "etag:x", kind="refresh")
        self.assertFalse(rw.is_release_changed(self.store, "hcris", "etag:x"))
        self.assertTrue(rw.is_release_changed(self.store, "hcris", "etag:y"))

    def test_none_fingerprint_always_changed(self):
        rw.record_release(self.store, "hcris", "etag:x")
        # A probe that couldn't tell must force a refresh.
        self.assertTrue(rw.is_release_changed(self.store, "hcris", None))

    def test_record_upserts(self):
        rw.record_release(self.store, "hcris", "etag:x")
        rw.record_release(self.store, "hcris", "etag:y")
        wm = rw.get_watermark(self.store, "hcris")
        self.assertEqual(wm["fingerprint"], "etag:y")

    def test_select_changed_sources(self):
        rw.record_release(self.store, "hcris", "etag:same")
        rw.record_release(self.store, "irs990", "etag:old")
        changed = rw.select_changed_sources(
            self.store,
            ["hcris", "irs990", "cms_pos"],
            {"hcris": "etag:same", "irs990": "etag:new"},
        )
        # hcris unchanged → dropped; irs990 changed → kept;
        # cms_pos absent from probe → always kept.
        self.assertEqual(set(changed), {"irs990", "cms_pos"})


class OrchestratorHookTests(unittest.TestCase):
    def setUp(self):
        self.store, self.path = _temp_store()

    def tearDown(self):
        try:
            os.remove(self.path)
        except OSError:
            pass

    def _counting_refreshers(self, calls):
        def _mk(name):
            def _fn(store):
                calls.append(name)
                return 1
            return _fn
        return {name: _mk(name) for name in dr.KNOWN_SOURCES}

    def test_unchanged_source_is_skipped_not_parsed(self):
        calls = []
        refreshers = self._counting_refreshers(calls)
        # First run records the watermark for hcris.
        dr.refresh_all_sources(
            self.store, sources=["hcris"], refreshers=refreshers,
            fingerprints={"hcris": "etag:v1"},
        )
        self.assertEqual(calls, ["hcris"])
        # Second run, same fingerprint → skipped, refresher not called.
        calls.clear()
        report = dr.refresh_all_sources(
            self.store, sources=["hcris"], refreshers=refreshers,
            fingerprints={"hcris": "etag:v1"},
        )
        self.assertEqual(calls, [])
        statuses = {r.source: r.status for r in report.per_source}
        self.assertEqual(statuses["hcris"], dr._STATUS_SKIPPED)

    def test_changed_fingerprint_triggers_refresh(self):
        calls = []
        refreshers = self._counting_refreshers(calls)
        dr.refresh_all_sources(
            self.store, sources=["hcris"], refreshers=refreshers,
            fingerprints={"hcris": "etag:v1"},
        )
        calls.clear()
        dr.refresh_all_sources(
            self.store, sources=["hcris"], refreshers=refreshers,
            fingerprints={"hcris": "etag:v2"},
        )
        self.assertEqual(calls, ["hcris"])

    def test_no_fingerprints_preserves_always_refresh(self):
        calls = []
        refreshers = self._counting_refreshers(calls)
        dr.refresh_all_sources(
            self.store, sources=["hcris", "irs990"], refreshers=refreshers,
        )
        dr.refresh_all_sources(
            self.store, sources=["hcris", "irs990"], refreshers=refreshers,
        )
        # Both runs refresh both sources — no watermark gating.
        self.assertEqual(calls.count("hcris"), 2)
        self.assertEqual(calls.count("irs990"), 2)

    def test_failed_refresh_does_not_record_watermark(self):
        def _bad(store):
            raise RuntimeError("boom")
        report = dr.refresh_all_sources(
            self.store, sources=["hcris"], refreshers={"hcris": _bad},
            fingerprints={"hcris": "etag:v1"},
        )
        self.assertTrue(report.any_errors)
        # No watermark stored → next run still sees it as changed.
        self.assertTrue(rw.is_release_changed(self.store, "hcris", "etag:v1"))


if __name__ == "__main__":
    unittest.main()
