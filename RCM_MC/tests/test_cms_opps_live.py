"""CMS OPPS by-Provider-and-Service live client + APC parser fix.

The live client must fail closed (no fabricated service counts) when
egress is blocked, parse a mocked data-api payload at the REAL grain
(CCN × APC: APC_Cd / CAPC_Srvcs / Bene_Cnt), and aggregate the
drug-administration APCs per hospital without summing beneficiary
counts across APCs. Also pins the parser fix: the published file is
APC-grain, so ``parse_opps_csv`` must read APC_Cd/CAPC_Srvcs/Bene_Cnt
rows that the original HCPCS-only aliases silently dropped. No network.
"""
from __future__ import annotations

import json
import unittest
from unittest import mock

from rcm_mc.data import cms_opps_outpatient as op


class _Resp:
    def __init__(self, d):
        self._b = json.dumps(d).encode()

    def read(self):
        return self._b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class ParserApcAliasTests(unittest.TestCase):
    def test_csv_parser_reads_apc_grain(self):
        # The CURRENT published vintage: APC_Cd / CAPC_Srvcs / Bene_Cnt.
        # Pre-fix, these rows yielded nothing (HCPCS aliases only).
        import io, csv, tempfile, os
        rows = [
            {"Rndrng_Prvdr_CCN": "450001", "APC_Cd": "5694",
             "APC_Desc": "Level 4 Drug Administration",
             "CAPC_Srvcs": "1200", "Bene_Cnt": "300",
             "Avg_Mdcr_Pymt_Amt": "350.25"},
        ]
        with tempfile.NamedTemporaryFile(
                "w", suffix=".csv", delete=False, newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
            path = fh.name
        try:
            recs = list(op.parse_opps_csv(path))
        finally:
            os.unlink(path)
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0].hcpcs_code, "5694")
        self.assertEqual(recs[0].total_services, 1200)
        self.assertEqual(recs[0].n_unique_beneficiaries, 300)


class LiveFetchTests(unittest.TestCase):
    def test_drug_admin_apcs_are_the_four_opps_levels(self):
        self.assertEqual(set(op.DRUG_ADMIN_APCS),
                         {"5691", "5692", "5693", "5694"})

    def test_no_dataset_fails_closed(self):
        with mock.patch.object(op, "resolve_opps_provider_dataset",
                               lambda year=0, timeout=0: ""):
            self.assertEqual(op.fetch_opps_apc_state("5694", "TX"), [])
            self.assertEqual(op.fetch_state_drug_admin("TX"), {})

    def test_network_error_fails_closed(self):
        def _boom(req, timeout=0, context=None):
            raise OSError("egress blocked")
        with mock.patch.object(op, "resolve_opps_provider_dataset",
                               lambda year=0, timeout=0: "ds-1"), \
             mock.patch.object(op.urllib.request, "urlopen", _boom):
            self.assertEqual(op.fetch_opps_apc_state("5694", "TX"), [])

    def test_parses_mocked_payload(self):
        payload = [
            {"Rndrng_Prvdr_CCN": "450001",
             "Rndrng_Prvdr_Org_Name": "Houston Methodist",
             "Rndrng_Prvdr_City": "Houston", "APC_Cd": "5694",
             "CAPC_Srvcs": "1200", "Bene_Cnt": "300",
             "Avg_Mdcr_Pymt_Amt": "350.25"},
            {"Rndrng_Prvdr_CCN": "", "APC_Cd": "5694",
             "CAPC_Srvcs": "10"},          # no CCN → dropped
        ]
        with mock.patch.object(op, "resolve_opps_provider_dataset",
                               lambda year=0, timeout=0: "ds-1"), \
             mock.patch.object(
                 op.urllib.request, "urlopen",
                 lambda req, timeout=0, context=None: _Resp(payload)):
            rows = op.fetch_opps_apc_state("5694", "TX")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["ccn"], "450001")
        self.assertEqual(rows[0]["services"], 1200)
        self.assertEqual(rows[0]["benes"], 300)

    def test_aggregate_per_ccn_benes_not_summed(self):
        per_apc = {
            "5693": [{"ccn": "450001", "name": "H", "city": "Houston",
                      "apc": "5693", "services": 800, "benes": 250,
                      "avg_payment": 200.0}],
            "5694": [{"ccn": "450001", "name": "H", "city": "Houston",
                      "apc": "5694", "services": 1200, "benes": 300,
                      "avg_payment": 350.0}],
            "5691": [], "5692": [],
        }
        with mock.patch.object(op, "resolve_opps_provider_dataset",
                               lambda year=0, timeout=0: "ds-1"), \
             mock.patch.object(
                 op, "fetch_opps_apc_state",
                 lambda apc, state, dataset="", timeout=0: per_apc[apc]):
            agg = op.fetch_state_drug_admin("TX")
        h = agg["450001"]
        self.assertEqual(h["services"], 2000)            # services sum
        self.assertEqual(h["benes_max"], 300)            # benes do NOT
        self.assertEqual(h["by_apc"], {"5693": 800, "5694": 1200})
        # $: 800×200 + 1200×350 = 580,000 → 0.58M
        self.assertAlmostEqual(h["payment_mm"], 0.58, places=3)


if __name__ == "__main__":
    unittest.main()
