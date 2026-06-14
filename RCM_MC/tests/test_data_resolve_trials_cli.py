"""Tests for `rcm-mc data resolve` and `rcm-mc data trials`.

Both subcommands make live calls in production; here the network seams are
patched so the CLI parsing + formatting path is exercised offline and
deterministically. The entity resolver's CCN leg reads local HCRIS (no
network), so a gibberish name keeps it UNMATCHED without a data dependency.
"""
from __future__ import annotations

import contextlib
import io
import json
import unittest

from rcm_mc.cli import data_main
import rcm_mc.data.capiq as capiq
import rcm_mc.data_public.clinical_trials_v2 as ctv2


def _run(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = data_main(argv)
    return rc, buf.getvalue()


class ResolveCliTests(unittest.TestCase):
    def setUp(self):
        # Keep NPI/EIN legs offline; CCN leg uses local HCRIS.
        self._npi, self._ein = capiq._default_npi_fetch, capiq._default_ein_fetch
        capiq._default_npi_fetch = lambda *a, **k: []   # type: ignore[assignment]
        capiq._default_ein_fetch = lambda *a, **k: []   # type: ignore[assignment]

    def tearDown(self):
        capiq._default_npi_fetch = self._npi            # type: ignore[assignment]
        capiq._default_ein_fetch = self._ein            # type: ignore[assignment]

    def test_unmatched_name_prints_card(self):
        rc, out = _run(["resolve", "--name", "Zzqx Nonexistent Holdings LLC"])
        self.assertEqual(rc, 0)
        self.assertIn("Entity identity", out)
        self.assertIn("resolved: none", out)

    def test_json_shape(self):
        rc, out = _run(["resolve", "--name", "Zzqx Nonexistent Holdings LLC",
                        "--json"])
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        for k in ("ccn_status", "npi_status", "ein_status", "resolved_kinds"):
            self.assertIn(k, payload)
        self.assertEqual(payload["resolved_kinds"], [])


class TrialsCliTests(unittest.TestCase):
    def setUp(self):
        self._search = ctv2.clinicaltrials_search

        def _fake_search(*, condition="", term="", sponsor="", phase="",
                         page_size=100, opener=None):
            return [{
                "protocolSection": {
                    "identificationModule": {"nctId": "NCT01"},
                    "sponsorCollaboratorsModule": {"leadSponsor": {"name": "Acme Bio"}},
                    "designModule": {"phases": ["PHASE2"],
                                     "enrollmentInfo": {"count": 150}},
                    "statusModule": {"overallStatus": "RECRUITING"},
                    "conditionsModule": {"conditions": ["Psoriasis"]},
                }
            }]

        ctv2.clinicaltrials_search = _fake_search  # type: ignore[assignment]

    def tearDown(self):
        ctv2.clinicaltrials_search = self._search  # type: ignore[assignment]

    def test_table_shows_sponsor_rollup(self):
        rc, out = _run(["trials", "--condition", "psoriasis"])
        self.assertEqual(rc, 0)
        self.assertIn("Acme Bio", out)
        self.assertIn("150", out)

    def test_json_rollup(self):
        rc, out = _run(["trials", "--condition", "psoriasis", "--json"])
        self.assertEqual(rc, 0)
        rows = json.loads(out)
        self.assertEqual(rows[0]["sponsor"], "Acme Bio")
        self.assertEqual(rows[0]["trials"], 1)
        self.assertEqual(rows[0]["total_enrollment"], 150)


if __name__ == "__main__":
    unittest.main()
