"""Healthcare Revenue Leakage V2 — snapshot persistence tests."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rcm_mc.diligence.snapshot import run_snapshot
from rcm_mc.diligence.store import list_runs, load_run, save_run

_FIX = Path(__file__).parent / "fixtures" / "edi"


def _result():
    return run_snapshot(
        [_FIX / "clean_837p.edi", _FIX / "clean_835.edi"],
        deal_name="Project Atlas", salt="s")


class TestStore(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self._tmp.name) / "p.db")
        self.res = _result()

    def tearDown(self):
        self._tmp.cleanup()

    def test_save_and_load(self):
        h = save_run(self.db, self.res, project_id="deal1", deal_name="Project Atlas")
        self.assertEqual(h, self.res.ccd.content_hash())
        loaded = load_run(self.db, h, project_id="deal1")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["deal_name"], "Project Atlas")
        self.assertIn("## 1. Executive summary", loaded["memo_markdown"])
        self.assertIn("analytics", loaded["result"])

    def test_idempotent_resave(self):
        save_run(self.db, self.res, project_id="deal1")
        save_run(self.db, self.res, project_id="deal1")  # same content_hash
        self.assertEqual(len(list_runs(self.db, project_id="deal1")), 1)

    def test_project_isolation(self):
        save_run(self.db, self.res, project_id="deal1")
        save_run(self.db, self.res, project_id="deal2")
        self.assertEqual(len(list_runs(self.db, project_id="deal1")), 1)
        self.assertEqual(len(list_runs(self.db, project_id="deal2")), 1)
        self.assertIsNone(load_run(self.db, self.res.ccd.content_hash(), project_id="other"))

    def test_list_returns_summary(self):
        save_run(self.db, self.res, project_id="deal1", deal_name="Project Atlas")
        runs = list_runs(self.db, project_id="deal1")
        self.assertEqual(runs[0].deal_name, "Project Atlas")
        self.assertIsInstance(runs[0].data_confidence_score, int)

    def test_stored_payload_phi_safe(self):
        save_run(self.db, self.res, project_id="deal1")
        loaded = load_run(self.db, self.res.ccd.content_hash(), project_id="deal1")
        blob = str(loaded["result"]) + loaded["memo_markdown"]
        self.assertNotIn("MRN", blob)


if __name__ == "__main__":
    unittest.main()
