"""`rcm-mc data drug` — RxNorm name/NDC normalization.

rxnorm_normalize is patched so the CLI wiring is exercised offline. Covers
name path, the unmatched case, and the mutually-exclusive arg guard.
"""
from __future__ import annotations

import contextlib
import io
import json
import unittest

from rcm_mc.cli import data_main
import rcm_mc.data_public.public_api_clients as pac


def _run(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = data_main(argv)
    return rc, buf.getvalue()


class DrugCliTests(unittest.TestCase):
    def setUp(self):
        self._orig = pac.rxnorm_normalize

    def tearDown(self):
        pac.rxnorm_normalize = self._orig  # type: ignore[assignment]

    def test_name_normalizes(self):
        pac.rxnorm_normalize = (  # type: ignore[assignment]
            lambda v, by="name", opener=None: {
                "rxcui": "83367", "name": "atorvastatin", "tty": "IN",
                "ndcs": ["00071015523"]})
        rc, out = _run(["drug", "--name", "atorvastatin"])
        self.assertEqual(rc, 0)
        self.assertIn("83367", out)
        self.assertIn("atorvastatin", out)

    def test_json_output(self):
        pac.rxnorm_normalize = (  # type: ignore[assignment]
            lambda v, by="name", opener=None: {
                "rxcui": "1", "name": "x", "tty": "IN", "ndcs": []})
        rc, out = _run(["drug", "--ndc", "0002-1433-80", "--json"])
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out)["rxcui"], "1")

    def test_unmatched_prints_message(self):
        pac.rxnorm_normalize = lambda v, by="name", opener=None: {}  # type: ignore[assignment]
        rc, out = _run(["drug", "--name", "not-a-drug"])
        self.assertEqual(rc, 0)
        self.assertIn("no RxNorm concept", out)

    def test_requires_exactly_one_of_name_or_ndc(self):
        rc_none, _ = _run(["drug"])
        rc_both, _ = _run(["drug", "--name", "x", "--ndc", "y"])
        self.assertEqual(rc_none, 2)
        self.assertEqual(rc_both, 2)


if __name__ == "__main__":
    unittest.main()
