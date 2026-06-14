"""`rcm-mc data market` — two-source market structure (NPPES x Census CBP).

Both live calls are patched (NPPES via _request_json, CBP via an injected
opener seam through census_market.fetch_cbp) so the CLI wiring + reconciliation
are exercised offline. Also covers the state_fips lookup.
"""
from __future__ import annotations

import contextlib
import io
import json
import unittest
from unittest import mock

from rcm_mc.cli import data_main
from rcm_mc.data_public import census_market as cm


def _run(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = data_main(argv)
    return rc, buf.getvalue()


class StateFipsTests(unittest.TestCase):
    def test_known_and_unknown(self):
        self.assertEqual(cm.state_fips("co"), "08")
        self.assertEqual(cm.state_fips("TX"), "48")
        self.assertEqual(cm.state_fips("ZZ"), "")


class MarketCliTests(unittest.TestCase):
    def _patched(self, argv):
        import rcm_mc.data_public.nppes_api_client as client

        cbp_payload = [
            ["NAME", "ESTAB", "EMP", "state", "county"],
            ["Denver County", "30", "900", "08", "031"],
            ["El Paso County", "20", "600", "08", "041"],
        ]
        orig_fetch = cm.fetch_cbp
        cm.fetch_cbp = (lambda naics, **kw:  # type: ignore[assignment]
                        orig_fetch(naics, api_key="",
                                   opener=lambda u, h, t: json.dumps(cbp_payload).encode(),
                                   **{k: v for k, v in kw.items() if k != "api_key"}))
        try:
            with mock.patch.object(client, "_request_json",
                                   lambda params, **kw: {"result_count": 100}):
                return _run(argv)
        finally:
            cm.fetch_cbp = orig_fetch  # type: ignore[assignment]

    def test_reconciled_table(self):
        rc, out = self._patched(["market", "--state", "CO",
                                 "--vertical", "home_health"])
        self.assertEqual(rc, 0)
        self.assertIn("home_health", out)
        self.assertIn("621610", out)        # NAICS
        self.assertIn("100", out)           # providers
        self.assertIn("50", out)            # establishments 30+20

    def test_json_has_ratio(self):
        rc, out = self._patched(["market", "--state", "CO",
                                 "--vertical", "home_health", "--json"])
        self.assertEqual(rc, 0)
        rows = json.loads(out)            # list, even for a single vertical
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["providers"], 100)
        self.assertEqual(rows[0]["establishments"], 50)
        self.assertEqual(rows[0]["providers_per_estab"], 2.0)

    def test_sweep_all_verticals_when_omitted(self):
        from rcm_mc.data_public.nucc_taxonomy import VERTICALS
        rc, out = self._patched(["market", "--state", "CO", "--json"])
        self.assertEqual(rc, 0)
        rows = json.loads(out)
        self.assertEqual({r["vertical"] for r in rows}, set(VERTICALS))

    def test_unknown_state_rejected(self):
        rc, _ = _run(["market", "--state", "ZZ", "--vertical", "home_health"])
        self.assertEqual(rc, 2)

    def test_unknown_vertical_rejected(self):
        rc, _ = _run(["market", "--state", "CO", "--vertical", "spaceships"])
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
