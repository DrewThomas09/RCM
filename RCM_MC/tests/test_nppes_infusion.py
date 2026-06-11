"""NPPES infusion-provider count client.

Public NUCC taxonomy codes are facts; the live count must fail closed
(no fabricated count) when the NPI Registry is unreachable, and parse a
mocked payload otherwise. No network required.
"""
from __future__ import annotations

import unittest
from unittest import mock

from rcm_mc.data import nppes_infusion as ni


class TaxonomyTests(unittest.TestCase):
    def test_real_infusion_taxonomies(self):
        codes = {t["code"] for t in ni.INFUSION_TAXONOMIES}
        self.assertIn("261QI0500N", codes)   # Clinic/Center Infusion
        self.assertIn("3336I0012X", codes)   # Pharmacy Infusion
        self.assertIn("251F00000X", codes)   # Home Infusion agency
        for t in ni.INFUSION_TAXONOMIES:
            self.assertTrue(t["label"] and t["kind"])


class CountTests(unittest.TestCase):
    def test_empty_state_fails_closed(self):
        self.assertEqual(ni.count_infusion_providers(""), {"live": False})

    def test_network_error_fails_closed(self):
        import rcm_mc.data_public.nppes_api_client as client

        def _boom(params, **kw):
            raise client.NppesApiError("blocked")

        with mock.patch.object(client, "_request_json", _boom):
            self.assertEqual(
                ni.count_infusion_providers("TX"), {"live": False})

    def test_counts_across_taxonomies(self):
        import rcm_mc.data_public.nppes_api_client as client
        # Two taxonomy descriptions queried → counts summed.
        calls = iter([{"result_count": 25}, {"result_count": 10}])

        with mock.patch.object(
                client, "_request_json",
                lambda params, **kw: next(calls)):
            out = ni.count_infusion_providers("TX", city="Houston")
        self.assertTrue(out["live"])
        self.assertEqual(out["count"], 35)
        self.assertFalse(out["capped"])

    def test_capped_flag_on_full_page(self):
        import rcm_mc.data_public.nppes_api_client as client
        with mock.patch.object(
                client, "_request_json",
                lambda params, **kw: {"result_count": 200}):
            out = ni.count_infusion_providers("TX")
        self.assertTrue(out["capped"])


if __name__ == "__main__":
    unittest.main()
