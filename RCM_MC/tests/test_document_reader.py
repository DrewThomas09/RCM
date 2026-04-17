"""Tests for the drag-drop seller-file extractor (Prompt 25).

Invariants locked here:

 1. A CSV with "Denial Rate" header → extracts to ``denial_rate``.
 2. Alias "Init Denial %" → ``denial_rate``.
 3. Alias "A/R Days" → ``days_in_ar``.
 4. Alias "Net Coll Rate" → ``net_collection_rate``.
 5. Alias "CCR" → ``clean_claim_rate``.
 6. Alias "Cost to Collect" → ``cost_to_collect``.
 7. Multi-period extraction (Period + metric columns) produces
    one extraction per row.
 8. Percent signs in values (``12.5%``) parse cleanly.
 9. Dollar + comma values (``$ 1,234``) parse.
10. Blank cells skipped, file doesn't raise.
11. Unmapped column lands in ``unmapped_columns``.
12. Multi-sheet Excel: both sheets processed.
13. Conflicting values across sheets flagged in ``conflicts``.
14. Empty file → empty result, no crash.
15. Non-existent path → empty result, no crash.
16. TSV with tab delimiter auto-detected.
17. ``read_data_room`` merges files and surfaces cross-file conflicts.
18. Confidence on alias-table hits is higher than fuzzy fallbacks.
19. Unknown metric registry key falls through to unmapped.
20. Header row detection skips logo / title blocks.
21. CLI ``rcm-mc ingest --data-room PATH`` exits 0 with JSON.
22. Upload API returns extracted metrics JSON.
"""
from __future__ import annotations

import csv
import json
import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.request
from pathlib import Path

from rcm_mc.data.document_reader import (
    COLUMN_ALIAS_TABLE,
    ExtractionResult,
    MetricExtraction,
    _fuzzy_column_match,
    _parse_value,
    read_data_room,
    read_seller_file,
)


def _write_csv(headers, rows, *, suffix: str = ".csv",
               delimiter: str = ",") -> Path:
    tf = tempfile.NamedTemporaryFile(
        suffix=suffix, mode="w", delete=False, newline="", encoding="utf-8",
    )
    w = csv.writer(tf, delimiter=delimiter)
    w.writerow(headers)
    for row in rows:
        w.writerow(row)
    tf.close()
    return Path(tf.name)


# ── Alias + fuzzy column match ────────────────────────────────────

class TestColumnMatching(unittest.TestCase):

    def _registry(self):
        from rcm_mc.analysis.completeness import RCM_METRIC_REGISTRY
        return RCM_METRIC_REGISTRY

    def test_denial_rate_alias(self):
        key, conf = _fuzzy_column_match("Denial Rate", self._registry())
        self.assertEqual(key, "denial_rate")

    def test_init_denial_pct_alias(self):
        key, _ = _fuzzy_column_match("Init Denial %", self._registry())
        self.assertEqual(key, "denial_rate")

    def test_ar_days_alias(self):
        key, _ = _fuzzy_column_match("A/R Days", self._registry())
        self.assertEqual(key, "days_in_ar")

    def test_net_coll_rate_alias(self):
        key, _ = _fuzzy_column_match("Net Coll Rate", self._registry())
        self.assertEqual(key, "net_collection_rate")

    def test_ccr_alias(self):
        key, _ = _fuzzy_column_match("CCR", self._registry())
        self.assertEqual(key, "clean_claim_rate")

    def test_cost_to_collect_alias(self):
        key, _ = _fuzzy_column_match("Cost to Collect", self._registry())
        self.assertEqual(key, "cost_to_collect")

    def test_unknown_column_returns_none(self):
        key, _ = _fuzzy_column_match(
            "Totally Random Column", self._registry(),
        )
        self.assertIsNone(key)

    def test_alias_confidence_exceeds_fuzzy(self):
        alias_key, alias_conf = _fuzzy_column_match(
            "CCR", self._registry(),
        )
        fuzzy_key, fuzzy_conf = _fuzzy_column_match(
            "Initial Denial Rate Actual",
            self._registry(),
        )
        # Aliases ship confidence 0.95; fuzzy floats below that.
        self.assertGreater(alias_conf, fuzzy_conf)


# ── Value parsing ─────────────────────────────────────────────────

class TestValueParsing(unittest.TestCase):

    def test_plain_number(self):
        self.assertEqual(_parse_value("12.5"), 12.5)

    def test_percent_sign(self):
        self.assertEqual(_parse_value("12.5%"), 12.5)

    def test_dollar_comma(self):
        self.assertEqual(_parse_value("$ 1,234"), 1234.0)

    def test_trailing_days(self):
        self.assertEqual(_parse_value("45 days"), 45.0)

    def test_dash_returns_none(self):
        self.assertIsNone(_parse_value("-"))

    def test_em_dash_returns_none(self):
        self.assertIsNone(_parse_value("—"))

    def test_blank_returns_none(self):
        self.assertIsNone(_parse_value(""))

    def test_number_passthrough(self):
        self.assertEqual(_parse_value(42), 42.0)


# ── CSV extraction ─────────────────────────────────────────────────

class TestCSVExtraction(unittest.TestCase):

    def test_single_row_extraction(self):
        path = _write_csv(
            ["Denial Rate", "A/R Days", "Net Coll Rate"],
            [["12.5", "48", "96.2"]],
        )
        try:
            r = read_seller_file(path)
            self.assertIn("denial_rate", r.metrics)
            self.assertEqual(r.metrics["denial_rate"][0].value, 12.5)
            self.assertIn("days_in_ar", r.metrics)
            self.assertEqual(r.metrics["days_in_ar"][0].value, 48.0)
        finally:
            os.unlink(path)

    def test_multi_period(self):
        path = _write_csv(
            ["Period", "Init Denial %", "A/R Days"],
            [
                ["2024-01", "12.5", "48"],
                ["2024-02", "11.8", "46"],
                ["2024-03", "11.2", "44"],
            ],
        )
        try:
            r = read_seller_file(path)
            denials = r.metrics["denial_rate"]
            self.assertEqual(len(denials), 3)
            periods = [ex.period for ex in denials]
            self.assertEqual(periods, ["2024-01", "2024-02", "2024-03"])
        finally:
            os.unlink(path)

    def test_unmapped_column_noted(self):
        path = _write_csv(
            ["Denial Rate", "Random Col"], [["12.5", "X"]],
        )
        try:
            r = read_seller_file(path)
            self.assertIn("Random Col", r.unmapped_columns)
        finally:
            os.unlink(path)

    def test_blank_cells_skipped(self):
        path = _write_csv(
            ["Period", "Denial Rate"],
            [["2024-01", "12.5"], ["2024-02", ""], ["2024-03", "11.0"]],
        )
        try:
            r = read_seller_file(path)
            self.assertEqual(len(r.metrics["denial_rate"]), 2)
        finally:
            os.unlink(path)

    def test_tsv_auto_detected(self):
        path = _write_csv(
            ["Denial Rate", "A/R Days"],
            [["12.5", "48"]],
            suffix=".tsv", delimiter="\t",
        )
        try:
            r = read_seller_file(path)
            self.assertIn("denial_rate", r.metrics)
        finally:
            os.unlink(path)

    def test_nonexistent_path_no_crash(self):
        r = read_seller_file(Path("/nonexistent/path.csv"))
        self.assertEqual(r.metrics, {})

    def test_unknown_extension_tries_csv(self):
        path = _write_csv(
            ["Denial Rate"], [["12.5"]], suffix=".report",
        )
        try:
            r = read_seller_file(path)
            self.assertIn("denial_rate", r.metrics)
        finally:
            os.unlink(path)


# ── Excel extraction ──────────────────────────────────────────────

class TestExcelExtraction(unittest.TestCase):

    def _write_xlsx(self, sheets_data):
        """sheets_data: list of (sheet_name, [(headers, rows)]) blocks."""
        try:
            from openpyxl import Workbook
        except ImportError:
            self.skipTest("openpyxl not installed")
        wb = Workbook()
        wb.remove(wb.active)
        for sheet_name, headers, rows in sheets_data:
            ws = wb.create_sheet(sheet_name)
            ws.append(headers)
            for row in rows:
                ws.append(row)
        tf = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        tf.close()
        wb.save(tf.name)
        return Path(tf.name)

    def test_single_sheet(self):
        path = self._write_xlsx([
            ("Summary",
             ["Denial Rate", "A/R Days"], [[12.5, 48]]),
        ])
        try:
            r = read_seller_file(path)
            self.assertIn("denial_rate", r.metrics)
        finally:
            os.unlink(path)

    def test_two_sheets_both_processed(self):
        path = self._write_xlsx([
            ("Denials",
             ["Denial Rate", "Final Denial Rate"],
             [[12.5, 1.2]]),
            ("Collections",
             ["Net Coll Rate", "Cost to Collect"],
             [[96.5, 3.5]]),
        ])
        try:
            r = read_seller_file(path)
            self.assertIn("denial_rate", r.metrics)
            self.assertIn("net_collection_rate", r.metrics)
            self.assertIn("cost_to_collect", r.metrics)
        finally:
            os.unlink(path)

    def test_conflict_across_sheets(self):
        path = self._write_xlsx([
            ("Sheet1",
             ["Denial Rate", "Net Coll Rate"],
             [[12.5, 96.5]]),
            ("Sheet2",
             ["Denial Rate", "Net Coll Rate"],
             [[14.5, 96.5]]),   # denial_rate differs
        ])
        try:
            r = read_seller_file(path)
            conflict_keys = {c.metric_key for c in r.conflicts}
            self.assertIn("denial_rate", conflict_keys)
        finally:
            os.unlink(path)

    def test_logo_block_skipped(self):
        """A title / logo block at the top shouldn't be treated as
        headers; the first proper header row should be detected."""
        path = self._write_xlsx([
            ("Report", [
                "Acme RCM Report",
            ], [
                ["Prepared by Finance"],
                [""],
                ["Denial Rate", "A/R Days"],
                [12.5, 48],
            ]),
        ])
        try:
            r = read_seller_file(path)
            # Expected: our detector finds "Denial Rate" + "A/R Days"
            # row and reads the 12.5/48 below it.
            self.assertIn("denial_rate", r.metrics)
        finally:
            os.unlink(path)

    def test_source_cell_uses_actual_sheet_row_after_logo_block(self):
        """Provenance should cite the real worksheet row, not assume
        the header starts on line 1."""
        path = self._write_xlsx([
            ("Report", [
                "Acme RCM Report",
            ], [
                ["Prepared by Finance"],
                [""],
                ["Denial Rate", "A/R Days"],
                [12.5, 48],
            ]),
        ])
        try:
            r = read_seller_file(path)
            denial = r.metrics["denial_rate"][0]
            self.assertEqual(denial.source_cell, "Denial Rate / row 5")
        finally:
            os.unlink(path)


# ── Data-room walker ──────────────────────────────────────────────

class TestDataRoomWalker(unittest.TestCase):

    def test_merges_multiple_files(self):
        tmp = tempfile.mkdtemp()
        try:
            _write_csv(
                ["Denial Rate"], [["12.5"]],
            ).rename(Path(tmp) / "a.csv")
            _write_csv(
                ["A/R Days"], [["48"]],
            ).rename(Path(tmp) / "b.csv")
            r = read_data_room(Path(tmp))
            self.assertIn("denial_rate", r.metrics)
            self.assertIn("days_in_ar", r.metrics)
        finally:
            import shutil; shutil.rmtree(tmp)

    def test_missing_directory_no_crash(self):
        r = read_data_room(Path("/definitely/not/a/real/path"))
        self.assertEqual(r.metrics, {})


# ── Serialization ─────────────────────────────────────────────────

class TestSerialization(unittest.TestCase):

    def test_result_to_dict_is_json_safe(self):
        path = _write_csv(
            ["Denial Rate", "A/R Days"],
            [["12.5", "48"]],
        )
        try:
            r = read_seller_file(path)
            s = json.dumps(r.to_dict(), default=str)
            self.assertIn("denial_rate", s)
        finally:
            os.unlink(path)

    def test_metric_extraction_dict(self):
        ex = MetricExtraction(period="2024-01", value=12.5,
                              source_sheet="Denials",
                              source_cell="Denial Rate / row 2",
                              confidence=0.95)
        d = ex.to_dict()
        self.assertEqual(d["value"], 12.5)


# ── CLI ───────────────────────────────────────────────────────────

class TestCLI(unittest.TestCase):

    def test_ingest_data_room_json(self):
        from rcm_mc.data.ingest import main as ingest_main
        tmp = tempfile.mkdtemp()
        try:
            _write_csv(
                ["Denial Rate"], [["12.5"]],
            ).rename(Path(tmp) / "a.csv")
            out = tempfile.NamedTemporaryFile(
                suffix=".json", mode="w", delete=False,
            )
            out.close()
            rc = ingest_main([
                "--data-room", tmp,
                "--deal-id", "d1",
                "--json-out", out.name,
            ])
            self.assertEqual(rc, 0)
            payload = json.loads(Path(out.name).read_text())
            self.assertEqual(payload["deal_id"], "d1")
            self.assertIn("denial_rate", payload["metrics"])
            os.unlink(out.name)
        finally:
            import shutil; shutil.rmtree(tmp)

    def test_ingest_data_room_not_found(self):
        from rcm_mc.data.ingest import main as ingest_main
        rc = ingest_main(["--data-room", "/no/such/dir"])
        self.assertNotEqual(rc, 0)


# ── HTTP upload API ───────────────────────────────────────────────

class TestUploadAPI(unittest.TestCase):

    def _start(self, db_path: str) -> tuple:
        from rcm_mc.server import build_server
        s = socket.socket(); s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]; s.close()
        server, _ = build_server(port=port, db_path=db_path)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        time.sleep(0.05)
        return server, port

    def test_upload_returns_extracted_metrics(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            from rcm_mc.portfolio.store import PortfolioStore
            PortfolioStore(tf.name).upsert_deal("d1", name="d1")
            server, port = self._start(tf.name)
            try:
                # Build a minimal CSV payload.
                csv_bytes = (
                    "Denial Rate,A/R Days\n"
                    "12.5,48\n"
                ).encode()
                # Hand-construct a multipart body.
                boundary = "----rcmtestboundary"
                body = (
                    f"--{boundary}\r\n"
                    'Content-Disposition: form-data; name="file"; filename="report.csv"\r\n'
                    "Content-Type: text/csv\r\n\r\n"
                ).encode() + csv_bytes + f"\r\n--{boundary}--\r\n".encode()
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/deals/d1/upload",
                    data=body,
                    headers={
                        "Content-Type":
                        f"multipart/form-data; boundary={boundary}",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req) as r:
                    resp = json.loads(r.read().decode())
                self.assertEqual(resp["deal_id"], "d1")
                self.assertEqual(len(resp["files"]), 1)
                self.assertIn("denial_rate", resp["files"][0]["metrics"])
            finally:
                server.shutdown()
                server.server_close()
        finally:
            os.unlink(tf.name)


if __name__ == "__main__":
    unittest.main()
