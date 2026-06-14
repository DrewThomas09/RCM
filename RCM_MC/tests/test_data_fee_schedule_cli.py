"""Tests for `rcm-mc data fee-schedule` — the CY2026 reference CLI."""
from __future__ import annotations

import contextlib
import io
import json
import unittest

from rcm_mc.cli import data_main
from rcm_mc.data_public.fee_schedule_2026 import FEE_SCHEDULE_BACKBONE_2026


def _run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = data_main(argv)
    return rc, out.getvalue(), err.getvalue()


class FeeScheduleCliTests(unittest.TestCase):
    def test_backbone_table(self):
        rc, out, _ = _run(["fee-schedule"])
        self.assertEqual(rc, 0)
        self.assertIn("33.4009", out)        # non-QP CF
        self.assertIn("281.71", out)         # ESRD base
        self.assertIn("CMS-1832-F", out)     # rule citation

    def test_backbone_json_matches_registry(self):
        rc, out, _ = _run(["fee-schedule", "--json"])
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        self.assertEqual(set(payload), set(FEE_SCHEDULE_BACKBONE_2026))
        self.assertEqual(payload["pfs_cf_nonqp"]["value"], 33.4009)

    def test_migration_sizing(self):
        rc, out, _ = _run(
            ["fee-schedule", "--code", "45378", "--volume", "1000",
             "--from", "hopd", "--to", "asc"]
        )
        self.assertEqual(rc, 0)
        self.assertIn("Diagnostic colonoscopy", out)
        self.assertIn("-335,000.00", out)    # 1000 * (375 - 710)

    def test_migration_json(self):
        rc, out, _ = _run(
            ["fee-schedule", "--code", "45378", "--volume", "1000",
             "--from", "hopd", "--to", "asc", "--json"]
        )
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        self.assertEqual(payload["per_case_delta"], 375.0 - 710.0)
        self.assertEqual(payload["annual_delta"], (375.0 - 710.0) * 1000)

    def test_unknown_code_is_clean_error(self):
        rc, out, err = _run(["fee-schedule", "--code", "99999", "--volume", "10"])
        self.assertEqual(rc, 2)
        self.assertIn("no CY2026 reference rate", err)
        self.assertEqual(out, "")


if __name__ == "__main__":
    unittest.main()
