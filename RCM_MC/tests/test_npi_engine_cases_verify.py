"""Adversarial-verify regressions for the engine-cases front.

The double-check pass found one real defect in the shipped work: the new
title-row / headerless shape heuristics (engine._shape_rows) ran PER
CHUNK on streamed files, but bigfile prepends the FILE's first record to
every chunk as its header line. Chunk 2+ therefore treated that record
as a title or data row:

  * a title-led streamed file silently LOST one data record per chunk
    (verified: 80-row file → 77 rows out), and
  * a headerless streamed file REPLAYED its first record into every
    chunk (verified: 80-row file → 83 rows out with dedupe off) —

exactly the silent-lossy class this front set out to kill. The fix moves
the shaping to the stream level (bigfile._shape_stream_head, one pass
before chunking) and disables per-chunk reshaping
(engine._read_table(reshape=False)). These tests pin the fixed behavior
end-to-end through the real streaming path.
"""
from __future__ import annotations

import csv
import os
import tempfile
import unittest
from unittest.mock import patch

from rcm_mc.npi_cleaner import bigfile, engine

GOOD_A = "1234567893"
GOOD_B = "1679576722"


def _stream(data: bytes, name: str, **kw):
    """Run bytes through the REAL chunked streaming path."""
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, name)
        with open(p, "wb") as fh:
            fh.write(data)
        with patch.object(bigfile, "STREAM_THRESHOLD_BYTES", 512), \
                patch.object(bigfile, "CHUNK_TARGET_BYTES", 1024):
            res = bigfile.clean_path(p, name, **kw)
        out_rows = None
        if res.out_path and os.path.exists(str(res.out_path)):
            with open(str(res.out_path), newline="") as fh:
                out_rows = list(csv.reader(fh))
        return res, out_rows


class TestStreamedTitleRow(unittest.TestCase):
    """A cover line above the header must cost ZERO data records on the
    streamed path — pre-fix it ate one record per chunk."""

    def _data(self, n=80):
        body = "\n".join(
            f"CLM{i},{GOOD_B},PAT {i},2024-01-05,99213,{100 + i}.00"
            for i in range(n))
        return ("Claims Extract Q3 2025\n"
                "ClaimID,BillingNPI,PatientName,DateOfService,HCPCS,"
                "BilledAmt\n" + body + "\n").encode()

    def test_all_rows_survive_and_headers_are_real(self):
        res, out = self._run()
        self.assertEqual(res.n_rows_in, 80)
        self.assertEqual(res.n_rows_out, 80)
        self.assertEqual(res.headers[:3],
                         ["ClaimID", "BillingNPI", "PatientName"])
        self.assertTrue(any("title row" in w for w in res.warnings))
        # The output FILE agrees: real header + every data row, once.
        self.assertEqual(out[0][:2], ["ClaimID", "BillingNPI"])
        self.assertEqual(len(out) - 1, 80)
        claim_ids = [r[0] for r in out[1:]]
        self.assertEqual(len(claim_ids), len(set(claim_ids)))
        self.assertIn("CLM0", claim_ids)
        self.assertIn("CLM79", claim_ids)

    def _run(self):
        return _stream(self._data(), "title.csv", drop_duplicates=False)


class TestStreamedHeaderless(unittest.TestCase):
    """A headerless streamed file must not replay its first record into
    every chunk — pre-fix, dedupe-off runs fabricated duplicates."""

    def _data(self, n=80):
        return ("\n".join(
            f"{GOOD_B},PROVIDER {i},2024-01-0{(i % 9) + 1},99213,"
            f"{100 + i}.00" for i in range(n)) + "\n").encode()

    def test_no_replay_with_dedupe_off(self):
        res, out = _stream(self._data(), "hl.csv", drop_duplicates=False)
        self.assertEqual(res.n_rows_in, 80)
        self.assertEqual(res.n_rows_out, 80)
        self.assertEqual(res.headers[0], "column_1")
        self.assertTrue(any("no header row" in w for w in res.warnings))
        # Row 1 appears exactly once in the output — not once per chunk.
        self.assertEqual(out[0][0], "column_1")
        self.assertEqual(len(out) - 1, 80)
        first = sum(1 for r in out[1:] if "PROVIDER 0" in r)
        self.assertEqual(first, 1)

    def test_no_phantom_duplicates_with_dedupe_on(self):
        res, _out = _stream(self._data(), "hl2.csv", drop_duplicates=True)
        # Every row is distinct — a replayed first record showed up here
        # as phantom "removed duplicates" before the fix.
        self.assertEqual(res.n_dupes_removed, 0)
        self.assertEqual(res.n_rows_out, 80)


class TestStreamedOrdinaryHeaderUntouched(unittest.TestCase):
    """Shape heuristics must never fire on a normally-headered stream,
    including narrow 2-column files."""

    def test_two_column_file_not_reshaped(self):
        data = ("NPI,Name\n" + "\n".join(
            f"{GOOD_B},PROV {i}" for i in range(60)) + "\n").encode()
        res, out = _stream(data, "two.csv", drop_duplicates=False)
        self.assertEqual(res.headers, ["NPI", "Name"])
        self.assertEqual(res.n_rows_out, 60)
        self.assertFalse(any("title row" in w for w in res.warnings))
        self.assertFalse(any("no header row" in w for w in res.warnings))
        self.assertEqual(len(out) - 1, 60)


class TestInMemoryShapeStillWorks(unittest.TestCase):
    """The reshape gate must not disturb the in-memory path (default
    reshape=True) — title skip and headerless synthesis keep working."""

    def test_title_and_headerless_in_memory(self):
        data = ("Cover Line\n"
                "ClaimID,BillingNPI,PatientName,DateOfService,HCPCS\n"
                "1,%s,DOE,2024-01-01,99213\n"
                "2,%s,ROE,2024-01-02,99214\n"
                "3,%s,POE,2024-01-03,99215\n"
                % (GOOD_B, GOOD_A, GOOD_B)).encode()
        res = engine.clean_bytes(data, "t.csv")
        self.assertEqual(res.headers[0], "ClaimID")
        self.assertEqual(res.n_rows_out, 3)
        hl = ("%s,DOE JOHN,100.50\n%s,ROE JANE,200.00\n"
              "%s,POE JIM,300.00\n" % (GOOD_B, GOOD_A, GOOD_B)).encode()
        res = engine.clean_bytes(hl, "h.csv")
        self.assertEqual(res.headers[0], "column_1")
        self.assertEqual(res.n_rows_out, 3)

    def test_chunk_mode_never_reshapes(self):
        # _stream_chunk=True is the per-chunk entry: a numeric first line
        # (bigfile's prepended header record on a headerless file, before
        # the stream-level synth existed) must be taken as-is, and title
        # heuristics must not eat records.
        data = ("column_1,column_2,column_3\n" + "\n".join(
            f"{GOOD_B},PROV {i},100" for i in range(6)) + "\n").encode()
        res = engine.clean_bytes(data, "c.csv", _stream_chunk=True)
        self.assertEqual(res.n_rows_out, 6)


class TestShapeStreamHeadUnit(unittest.TestCase):
    """Direct checks on the stream-head shaper (records carry their
    newline bytes, as _iter_records yields them)."""

    def _recs(self, lines):
        return iter([(ln + "\n").encode() for ln in lines])

    def test_title_skip_returns_real_header(self):
        lines = ["ClaimID,BillingNPI,PatientName,DateOfService,HCPCS"] + [
            f"{i},{GOOD_B},P {i},2024-01-01,99213" for i in range(6)]
        hdr, records, skipped, notes = bigfile._shape_stream_head(
            b"Vendor Extract\n", self._recs(lines))
        self.assertTrue(hdr.startswith(b"ClaimID,"))
        self.assertEqual(skipped, len(b"Vendor Extract\n"))
        self.assertTrue(any("title row" in n for n in notes))
        # Every data record comes back out, in order, exactly once.
        got = [r.decode().strip() for r in records]
        self.assertEqual(got, lines[1:])

    def test_headerless_synthesizes_and_keeps_record(self):
        lines = [f"{GOOD_A},PROV {i},100.00" for i in range(1, 7)]
        first = f"{GOOD_B},PROV 0,100.00\n".encode()
        hdr, records, skipped, notes = bigfile._shape_stream_head(
            first, self._recs(lines))
        self.assertEqual(hdr.decode().strip(),
                         "column_1,column_2,column_3")
        self.assertEqual(skipped, 0)
        got = [r for r in records]
        self.assertEqual(got[0], first)          # kept as data, once
        self.assertEqual(len(got), 7)

    def test_ordinary_header_passthrough(self):
        lines = [f"{i},{GOOD_B},100" for i in range(6)]
        hdr, records, skipped, notes = bigfile._shape_stream_head(
            b"ClaimID,BillingNPI,BilledAmt\n", self._recs(lines))
        self.assertEqual(hdr, b"ClaimID,BillingNPI,BilledAmt\n")
        self.assertEqual(skipped, 0)
        self.assertEqual(notes, [])
        self.assertEqual(len(list(records)), 6)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
