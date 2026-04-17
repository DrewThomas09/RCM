"""Regression tests for B149 bugs (fourth audit pass).

Covers:
- CSV formula-injection defanged (= + @ - etc.)
- next_outdir rejects '..' path segments
- Job runner raising KeyboardInterrupt/SystemExit still marks job failed
"""
from __future__ import annotations

import os
import tempfile
import threading
import time
import unittest
import urllib.request as _u

from rcm_mc.deals.deal_notes import record_note
from rcm_mc.deals.deal_sim_inputs import next_outdir
from rcm_mc.infra.job_queue import JobRegistry


class TestCsvDefang(unittest.TestCase):
    def test_defang_equals_prefix(self):
        import pandas as pd
        from rcm_mc.server import RCMHandler
        df = pd.DataFrame([
            {"deal_id": "=SUM(1+1)", "body": "normal"},
            {"deal_id": "+cmd", "body": "-also bad"},
            {"deal_id": "@at", "body": "\tTAB"},
            {"deal_id": "safe", "body": "body has = in middle"},
            {"deal_id": "ccf", "body": "clean"},
        ])
        out = RCMHandler._defang_csv_df(df)
        rows = out.to_dict(orient="records")
        self.assertEqual(rows[0]["deal_id"], "'=SUM(1+1)")
        self.assertEqual(rows[1]["deal_id"], "'+cmd")
        self.assertEqual(rows[1]["body"], "'-also bad")
        self.assertEqual(rows[2]["deal_id"], "'@at")
        self.assertEqual(rows[2]["body"], "'\tTAB")
        # Non-leading special chars pass through untouched
        self.assertEqual(rows[3]["body"], "body has = in middle")
        self.assertEqual(rows[4]["deal_id"], "ccf")

    def test_numeric_cells_untouched(self):
        import pandas as pd
        from rcm_mc.server import RCMHandler
        df = pd.DataFrame([{"score": 60, "band": "amber"}])
        out = RCMHandler._defang_csv_df(df)
        self.assertEqual(out.iloc[0]["score"], 60)
        self.assertEqual(out.iloc[0]["band"], "amber")


class TestCsvExportDefanged(unittest.TestCase):
    def _start(self, tmp):
        import socket as _socket, time as _time
        from rcm_mc.server import build_server
        s = _socket.socket(); s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]; s.close()
        server, _ = build_server(port=port,
                                 db_path=os.path.join(tmp, "p.db"))
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start(); _time.sleep(0.05)
        return server, port

    def test_variance_csv_defangs_injection(self):
        """An attacker who stored a note starting with = shouldn't be
        able to turn a downloaded CSV into an active spreadsheet formula."""
        from rcm_mc.pe.hold_tracking import record_quarterly_actuals
        from tests.test_alerts import _seed_with_pe_math
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "=DROP", headroom=-0.5)
            record_quarterly_actuals(
                store, "=DROP", "2026Q1",
                actuals={"ebitda": 8e6}, plan={"ebitda": 12e6},
            )
            server, port = self._start(tmp)
            try:
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/variance?format=csv"
                ) as r:
                    body = r.read().decode()
                    # deal_id column should have leading ' to defang
                    self.assertIn("'=DROP", body)
                    # Neither the raw formula prefix nor a bare `@` /
                    # `+` string cell should appear — those are always
                    # injection vectors. Leading `-` on numeric cells
                    # (legitimate negative numbers like variance_pct)
                    # is fine because spreadsheet apps parse them as
                    # numbers, not formulas.
                    for line in body.splitlines()[1:]:
                        for cell in line.split(","):
                            self.assertFalse(
                                cell.startswith("=")
                                or cell.startswith("+")
                                or cell.startswith("@"),
                                f"unsafe leading char in CSV cell: {cell!r}",
                            )
            finally:
                server.shutdown(); server.server_close()


class TestPathTraversalRejected(unittest.TestCase):
    def test_parent_segment_rejected(self):
        with self.assertRaises(ValueError):
            next_outdir("ccf", "../../../etc")
        with self.assertRaises(ValueError):
            next_outdir("ccf", "foo/../bar")

    def test_deal_id_with_separator_rejected(self):
        with self.assertRaises(ValueError):
            next_outdir("../evil", "")
        with self.assertRaises(ValueError):
            next_outdir("foo/bar", "")

    def test_normal_usage_still_works(self):
        result = next_outdir("ccf", "runs/ccf")
        self.assertTrue(result.startswith(os.path.join("runs", "ccf")))
        # Default base is fine
        result2 = next_outdir("ccf", "")
        self.assertTrue(result2.startswith(os.path.join("runs", "ccf")))


class TestJobRunnerBaseException(unittest.TestCase):
    def test_systemexit_marks_job_failed(self):
        def _bad_runner(params):
            raise SystemExit("requested exit")

        reg = JobRegistry(runner=_bad_runner)
        try:
            jid = reg.submit_run(
                actual="/a", benchmark="/b", outdir="/o",
            )
            time.sleep(0.15)
            job = reg.get(jid)
            self.assertEqual(job.status, "failed")
            self.assertIn("SystemExit", job.error)
            self.assertTrue(reg._worker_thread.is_alive())
        finally:
            reg.shutdown(timeout=0.5)

    def test_keyboardinterrupt_marks_job_failed(self):
        def _bad_runner(params):
            raise KeyboardInterrupt()

        reg = JobRegistry(runner=_bad_runner)
        try:
            jid = reg.submit_run(
                actual="/a", benchmark="/b", outdir="/o",
            )
            time.sleep(0.15)
            job = reg.get(jid)
            self.assertEqual(job.status, "failed")
            self.assertIn("KeyboardInterrupt", job.error)
            self.assertTrue(reg._worker_thread.is_alive())
        finally:
            reg.shutdown(timeout=0.5)


if __name__ == "__main__":
    unittest.main()
