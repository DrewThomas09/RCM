"""Tests for the streaming TiC payer MRF parser."""
from __future__ import annotations

import gzip
import os
import shutil
import tempfile
import unittest
from pathlib import Path


def _fixture_path():
    """Reuse the existing payer_tic.json fixture."""
    import rcm_mc.pricing as _pkg
    return (Path(_pkg.__file__).parent
            / "fixtures" / "sample_payer_tic.json")


class TestStreamingParser(unittest.TestCase):
    def test_streaming_yields_same_records_as_eager(self):
        """Streaming parser should produce the same record count
        + same payer name as the eager parse."""
        from rcm_mc.pricing.payer_mrf import (
            parse_payer_tic_mrf,
        )
        from rcm_mc.pricing.payer_mrf_streaming import (
            streaming_parse_payer_tic_mrf,
        )
        path = _fixture_path()
        eager = list(parse_payer_tic_mrf(path))
        streaming = list(streaming_parse_payer_tic_mrf(path))
        # Same record count
        self.assertEqual(len(eager), len(streaming))
        # Same payer + plan on every record
        for e, s in zip(eager, streaming):
            self.assertEqual(e.payer_name, s.payer_name)
            self.assertEqual(e.plan_name, s.plan_name)
            self.assertEqual(e.code, s.code)

    def test_handles_gzipped_input(self):
        """Streaming parser should accept .json.gz transparently."""
        from rcm_mc.pricing.payer_mrf_streaming import (
            streaming_parse_payer_tic_mrf,
        )
        src = _fixture_path()
        tmp = tempfile.TemporaryDirectory()
        try:
            gz_path = Path(tmp.name) / "fixture.json.gz"
            with src.open("rb") as fin:
                with gzip.open(gz_path, "wb") as fout:
                    shutil.copyfileobj(fin, fout)
            records = list(streaming_parse_payer_tic_mrf(
                gz_path))
            self.assertGreater(len(records), 0)
            # Payer name normalized correctly
            self.assertIn(records[0].payer_name,
                          ("Aetna (CVS)", "Aetna"))
        finally:
            tmp.cleanup()

    def test_missing_file_raises(self):
        from rcm_mc.pricing.payer_mrf_streaming import (
            streaming_parse_payer_tic_mrf,
        )
        with self.assertRaises(FileNotFoundError):
            # iterator → trigger via list()
            list(streaming_parse_payer_tic_mrf(
                "/nonexistent/path.json"))


class TestStreamingLoader(unittest.TestCase):
    def test_streaming_loader_persists_rows(self):
        from rcm_mc.pricing import PricingStore
        from rcm_mc.pricing.payer_mrf_streaming import (
            load_payer_tic_mrf_streaming,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PricingStore(db)
            n = load_payer_tic_mrf_streaming(
                store, _fixture_path(),
                chunk_commit=2,    # force multiple commits
            )
            self.assertGreater(n, 0)
            # Verify rows landed
            with store.connect() as con:
                count = con.execute(
                    "SELECT COUNT(*) "
                    "FROM pricing_payer_rates").fetchone()[0]
            self.assertEqual(count, n)
            # Load-log entry created
            with store.connect() as con:
                log = con.execute(
                    "SELECT * FROM pricing_load_log "
                    "WHERE source='payer_tic'").fetchone()
            self.assertIsNotNone(log)
            self.assertEqual(log["record_count"], n)
            self.assertIn("streaming", (log["notes"] or ""))
        finally:
            tmp.cleanup()


class TestBoundaryParsing(unittest.TestCase):
    def test_string_with_braces_doesnt_break_depth_tracking(self):
        """A string containing { or } shouldn't affect the
        depth counter."""
        from rcm_mc.pricing.payer_mrf_streaming import (
            streaming_parse_payer_tic_mrf,
        )
        # Synthetic fixture with a bracket-laden description
        synthetic = """{
          "reporting_entity_name": "Aetna",
          "plan_name": "Test",
          "in_network": [
            {
              "billing_code": "12345",
              "billing_code_type": "CPT",
              "description": "Test {with} {curly} {braces}",
              "negotiated_rates": [
                {
                  "provider_groups": [{"npi": ["1234567890"]}],
                  "negotiated_prices": [
                    {"negotiated_type": "negotiated",
                     "negotiated_rate": 100.0}
                  ]
                }
              ]
            }
          ]
        }"""
        tmp = tempfile.TemporaryDirectory()
        try:
            p = Path(tmp.name) / "synth.json"
            p.write_text(synthetic)
            records = list(streaming_parse_payer_tic_mrf(p))
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].code, "12345")
            self.assertEqual(records[0].npi, "1234567890")
            self.assertEqual(records[0].negotiated_rate, 100.0)
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
