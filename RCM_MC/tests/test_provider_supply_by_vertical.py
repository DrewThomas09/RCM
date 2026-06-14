"""Provider-supply-by-vertical aggregator + `rcm-mc data supply` CLI.

NPPES is mocked so the sweep + CLI formatting are exercised offline. A vertical
whose call fails must degrade to live=False (market unknown), not zero.
"""
from __future__ import annotations

import contextlib
import io
import json
import unittest
from unittest import mock

from rcm_mc.cli import data_main
from rcm_mc.data import nppes_infusion as ni
from rcm_mc.data_public import nucc_taxonomy as nt


def _run(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = data_main(argv)
    return rc, buf.getvalue()


class AggregatorTests(unittest.TestCase):
    def test_sweeps_each_vertical(self):
        import rcm_mc.data_public.nppes_api_client as client
        with mock.patch.object(client, "_request_json",
                               lambda params, **kw: {"result_count": 7}):
            rows = ni.supply_by_vertical("CO", ["home_health", "hospice"])
        self.assertEqual([r["vertical"] for r in rows],
                         ["home_health", "hospice"])
        self.assertTrue(all(r["live"] for r in rows))
        # home_health has 1 description → 7; hospice 1 → 7.
        self.assertEqual(rows[0]["count"], 7)

    def test_failed_vertical_degrades_to_unknown_not_zero(self):
        import rcm_mc.data_public.nppes_api_client as client

        def _boom(params, **kw):
            raise client.NppesApiError("blocked")

        with mock.patch.object(client, "_request_json", _boom):
            rows = ni.supply_by_vertical("CO", ["snf"])
        self.assertFalse(rows[0]["live"])
        self.assertNotIn("count", rows[0])

    def test_default_covers_full_crosswalk(self):
        import rcm_mc.data_public.nppes_api_client as client
        with mock.patch.object(client, "_request_json",
                               lambda params, **kw: {"result_count": 1}):
            rows = ni.supply_by_vertical("CO")
        self.assertEqual({r["vertical"] for r in rows}, set(nt.VERTICALS))


class SupplyCliTests(unittest.TestCase):
    def test_table_lists_verticals(self):
        import rcm_mc.data_public.nppes_api_client as client
        with mock.patch.object(client, "_request_json",
                               lambda params, **kw: {"result_count": 5}):
            rc, out = _run(["supply", "--state", "co", "--vertical", "dialysis"])
        self.assertEqual(rc, 0)
        self.assertIn("dialysis", out)
        self.assertIn("5", out)

    def test_unknown_vertical_rejected(self):
        rc, _ = _run(["supply", "--state", "CO", "--vertical", "spaceships"])
        self.assertEqual(rc, 2)

    def test_json_output(self):
        import rcm_mc.data_public.nppes_api_client as client
        with mock.patch.object(client, "_request_json",
                               lambda params, **kw: {"result_count": 9}):
            rc, out = _run(["supply", "--state", "CO", "--vertical",
                            "home_health", "--json"])
        self.assertEqual(rc, 0)
        rows = json.loads(out)
        self.assertEqual(rows[0]["vertical"], "home_health")
        self.assertEqual(rows[0]["count"], 9)


if __name__ == "__main__":
    unittest.main()
