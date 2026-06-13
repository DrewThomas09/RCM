"""Tests for `rcm-mc data apis` — the scriptable public-data API catalog."""
from __future__ import annotations

import contextlib
import io
import json
import unittest

from rcm_mc.cli import data_main
from rcm_mc.data_public import public_api_catalog as cat


def _run(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = data_main(argv)
    return rc, buf.getvalue()


class DataApisCliTests(unittest.TestCase):
    def test_table_lists_every_source(self):
        rc, out = _run(["apis"])
        self.assertEqual(rc, 0)
        for s in cat.all_sources():
            self.assertIn(s.name, out)

    def test_json_payload_matches_catalog(self):
        rc, out = _run(["apis", "--json"])
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        self.assertEqual(payload["summary"]["total"], len(cat.all_sources()))
        self.assertEqual(len(payload["sources"]), len(cat.all_sources()))

    def test_category_filter(self):
        rc, out = _run(["apis", "--json", "--category", "drugs_devices"])
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        self.assertTrue(payload["sources"])
        self.assertTrue(all(s["category"] == "drugs_devices"
                            for s in payload["sources"]))

    def test_wired_only_filter(self):
        rc, out = _run(["apis", "--json", "--wired-only"])
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        self.assertEqual(len(payload["sources"]), len(cat.wired_sources()))
        self.assertTrue(all(s["is_wired"] for s in payload["sources"]))


if __name__ == "__main__":
    unittest.main()
