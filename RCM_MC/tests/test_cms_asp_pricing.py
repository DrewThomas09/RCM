"""CMS Part B ASP drug-pricing client.

The ASP+6 / sequestered formula is exact; the J-code reference is public
CMS fact; and the live pricing fetch must fail closed (no fabricated
dollars) when egress is blocked. Parsing is exercised with a mocked
payload — no network required.
"""
from __future__ import annotations

import unittest
from unittest import mock

from rcm_mc.data import cms_asp_pricing as asp


class FormulaTests(unittest.TestCase):
    def test_payment_limit_formula(self):
        self.assertAlmostEqual(asp.payment_limit(50.0, sequestered=False),
                               53.0, places=4)
        self.assertAlmostEqual(asp.payment_limit(50.0), 50.0 *
                               (1 + asp.ASP_ADDON_SEQUESTERED), places=4)
        # Sequester makes the effective add-on smaller than statutory 6%.
        self.assertLess(asp.ASP_ADDON_SEQUESTERED, asp.ASP_ADDON)
        self.assertGreater(asp.ASP_ADDON_SEQUESTERED, 0.04)

    def test_reference_codes_are_public_facts(self):
        codes = {c["hcpcs"] for c in asp.INFUSION_HCPCS}
        self.assertIn("J1745", codes)   # infliximab
        self.assertIn("J9312", codes)   # rituximab
        self.assertGreaterEqual(len(asp.INFUSION_HCPCS), 10)


class FetchTests(unittest.TestCase):
    def test_fetch_fails_closed_when_no_dataset(self):
        # Dataset resolution blocked → empty dict, never fabricated.
        with mock.patch.object(asp, "_resolve_asp_dataset",
                               lambda timeout=0: ""):
            self.assertEqual(asp.fetch_asp_pricing(["J1745"]), {})

    def test_fetch_parses_payment_limit(self):
        payload = [
            {"HCPCS Code": "J1745", "Payment Limit": "92.50"},
            {"HCPCS Code": "J9312", "ASP Payment Limit": "8.20"},
            {"HCPCS Code": "J0000", "Payment Limit": ""},   # skipped
        ]

        class _Resp:
            def __init__(self, data):
                import json
                self._b = json.dumps(data).encode()
            def read(self):
                return self._b
            def __enter__(self):
                return self
            def __exit__(self, *a):
                return False

        with mock.patch.object(asp, "_resolve_asp_dataset",
                               lambda timeout=0: "abc-123"), \
             mock.patch.object(
                 asp.urllib.request, "urlopen",
                 lambda req, timeout=0, context=None: _Resp(payload)):
            out = asp.fetch_asp_pricing(["J1745", "J9312"])
        self.assertAlmostEqual(out["J1745"], 92.50)
        self.assertAlmostEqual(out["J9312"], 8.20)
        self.assertNotIn("J0000", out)

    def test_fetch_network_error_returns_empty(self):
        def _boom(req, timeout=0, context=None):
            raise OSError("blocked")
        with mock.patch.object(asp, "_resolve_asp_dataset",
                               lambda timeout=0: "abc-123"), \
             mock.patch.object(asp.urllib.request, "urlopen", _boom):
            self.assertEqual(asp.fetch_asp_pricing(["J1745"]), {})


if __name__ == "__main__":
    unittest.main()
