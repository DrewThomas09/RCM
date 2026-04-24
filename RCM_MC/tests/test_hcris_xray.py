"""Tests for the HCRIS-Native Peer X-Ray."""
from __future__ import annotations

import json
import unittest
from urllib.parse import urlencode
from urllib.request import urlopen

from rcm_mc.diligence.hcris_xray import (
    HospitalMetrics, METRIC_CATALOG, MetricSpec,
    compute_benchmarks, compute_metrics, dataset_summary,
    find_hospital, find_peers, load_all_metrics,
    search_hospitals, xray,
)


class MetricComputationTests(unittest.TestCase):

    def test_compute_metrics_safe_on_empty_row(self):
        m = compute_metrics({})
        self.assertIsInstance(m, HospitalMetrics)
        self.assertEqual(m.ccn, "")
        self.assertEqual(m.beds, 0)
        self.assertEqual(m.operating_margin_on_npr, 0.0)

    def test_compute_metrics_ratios(self):
        m = compute_metrics({
            "ccn": "010001", "name": "Test Hospital",
            "state": "AL", "fiscal_year": 2022,
            "beds": 300,
            "bed_days_available": 109500,  # 300 × 365
            "total_patient_days": 76650,    # 70% occupancy
            "medicare_days": 30000,
            "medicaid_days": 10000,
            "gross_patient_revenue": 1_000_000_000,
            "contractual_allowances": 700_000_000,
            "net_patient_revenue": 300_000_000,
            "operating_expenses": 270_000_000,
            "net_income": 20_000_000,
        })
        self.assertAlmostEqual(m.occupancy_rate, 0.70, places=2)
        self.assertAlmostEqual(
            m.net_to_gross_ratio, 0.30, places=2,
        )
        self.assertAlmostEqual(
            m.operating_margin_on_npr, 0.10, places=2,
        )
        self.assertAlmostEqual(
            m.net_income_margin_on_npr, 20 / 300, places=3,
        )
        self.assertEqual(m.size_cohort, "REGIONAL")
        self.assertEqual(m.margin_band, "HEALTHY")

    def test_size_cohort_bands(self):
        for beds, expected in [
            (25, "MICRO"), (100, "SMALL_COMMUNITY"),
            (300, "REGIONAL"),  # >=300 is REGIONAL, not COMMUNITY
            (250, "COMMUNITY"),  # COMMUNITY is 150-299
            (400, "REGIONAL"), (600, "ACADEMIC_LARGE"),
        ]:
            m = compute_metrics({"beds": beds})
            self.assertEqual(
                m.size_cohort, expected,
                f"beds={beds}: got {m.size_cohort}, "
                f"expected {expected}",
            )


class DataLoadingTests(unittest.TestCase):

    def test_load_all_metrics_nontrivial(self):
        all_m = load_all_metrics()
        self.assertGreater(len(all_m), 10_000)

    def test_dataset_summary(self):
        summary = dataset_summary()
        self.assertIn("total_rows", summary)
        self.assertGreater(summary["total_rows"], 10_000)
        self.assertGreater(len(summary["states"]), 40)
        self.assertGreater(len(summary["cohorts"]), 3)

    def test_find_hospital_by_ccn(self):
        m = find_hospital("010001")
        self.assertIsNotNone(m)
        self.assertEqual(m.ccn, "010001")
        self.assertEqual(m.state, "AL")

    def test_find_hospital_by_name(self):
        m = find_hospital("SOUTHEAST HEALTH")
        self.assertIsNotNone(m)
        self.assertIn("SOUTHEAST", m.name.upper())

    def test_find_hospital_missing(self):
        m = find_hospital("DEFINITELY_DOES_NOT_EXIST_12345")
        self.assertIsNone(m)


class PeerMatchingTests(unittest.TestCase):

    def test_find_peers_returns_nonempty(self):
        target = find_hospital("010001")
        self.assertIsNotNone(target)
        peers, desc = find_peers(target, k=25)
        self.assertGreater(len(peers), 5)
        self.assertTrue(desc)

    def test_peers_match_size_cohort(self):
        target = find_hospital("010001")
        peers, _ = find_peers(target, k=20)
        for p in peers:
            self.assertEqual(
                p.hospital.size_cohort, target.size_cohort,
                f"peer {p.hospital.ccn} in wrong cohort",
            )

    def test_peers_excludes_target_itself(self):
        target = find_hospital("010001")
        peers, _ = find_peers(target, k=25)
        for p in peers:
            if p.hospital.ccn == target.ccn:
                self.assertNotEqual(
                    p.hospital.fiscal_year, target.fiscal_year,
                )


class HistoryAndTrendTests(unittest.TestCase):

    def test_target_history_sorted_ascending(self):
        from rcm_mc.diligence.hcris_xray import get_target_history
        hist = get_target_history("010001")
        self.assertGreaterEqual(len(hist), 2)
        for a, b in zip(hist, hist[1:]):
            self.assertLessEqual(a.fiscal_year, b.fiscal_year)

    def test_xray_populates_trend_signal(self):
        from rcm_mc.diligence.hcris_xray import xray
        r = xray(ccn="010001")
        self.assertIn(
            r.trend_signal,
            {"improving", "deteriorating", "flat", ""},
        )
        if len(r.target_history) >= 2:
            self.assertIn(
                r.trend_signal,
                {"improving", "deteriorating", "flat"},
            )


class BearCaseIntegrationTests(unittest.TestCase):

    def test_hcris_feeds_bear_case(self):
        from rcm_mc.diligence.hcris_xray import xray
        from rcm_mc.diligence.bear_case import (
            extract_hcris_xray_evidence, generate_bear_case,
        )
        r = xray(ccn="010001")
        evidence = extract_hcris_xray_evidence(r)
        # Southeast Health has deteriorating margin → evidence fires
        self.assertGreater(len(evidence), 0)
        bc = generate_bear_case(
            target_name="Test", hcris_xray=r,
        )
        self.assertIn("HCRIS_XRAY", bc.sources_active)
        # Citation prefix H should appear on at least one item
        self.assertTrue(
            any(e.citation_key.startswith("H") for e in bc.evidence),
            "no H-prefixed citation found",
        )

    def test_none_input_returns_empty(self):
        from rcm_mc.diligence.bear_case import (
            extract_hcris_xray_evidence,
        )
        self.assertEqual(extract_hcris_xray_evidence(None), [])


class BenchmarkTests(unittest.TestCase):

    def test_full_xray(self):
        report = xray(ccn="010001")
        self.assertIsNotNone(report)
        self.assertEqual(report.target.ccn, "010001")
        self.assertGreater(len(report.peers), 5)
        self.assertGreater(len(report.metrics), 10)
        self.assertTrue(report.headline)
        for bm in report.metrics:
            self.assertLessEqual(bm.peer_p25, bm.peer_median)
            self.assertLessEqual(bm.peer_median, bm.peer_p75)

    def test_to_dict_roundtrip(self):
        report = xray(ccn="010001", peer_k=10)
        payload = report.to_dict()
        dumped = json.dumps(payload, default=str)
        reloaded = json.loads(dumped)
        self.assertEqual(
            reloaded["target"]["ccn"], "010001",
        )
        self.assertEqual(
            len(reloaded["metrics"]), len(report.metrics),
        )

    def test_unknown_ccn_returns_none(self):
        report = xray(ccn="DOES_NOT_EXIST")
        self.assertIsNone(report)


class SearchTests(unittest.TestCase):

    def test_search_by_name(self):
        hits = search_hospitals("REGIONAL", limit=10)
        self.assertGreater(len(hits), 0)
        for h in hits:
            self.assertIn("REGIONAL", h.name.upper())

    def test_search_state_filter(self):
        hits = search_hospitals("", state="AL", limit=20)
        self.assertGreater(len(hits), 0)
        for h in hits:
            self.assertEqual(h.state, "AL")


class UIRenderTests(unittest.TestCase):

    def test_landing_renders(self):
        from rcm_mc.ui.hcris_xray_page import render_hcris_xray_page
        html = render_hcris_xray_page({})
        self.assertIn("<form", html)
        self.assertIn("HCRIS", html)
        self.assertIn("17", html)  # total rows rendered somewhere

    def test_search_landing(self):
        from rcm_mc.ui.hcris_xray_page import render_hcris_xray_page
        html = render_hcris_xray_page({
            "q": ["REGIONAL"], "state": ["AL"],
        })
        self.assertIn("REGIONAL", html.upper())
        self.assertIn("Search results", html)

    def test_full_xray_renders(self):
        from rcm_mc.ui.hcris_xray_page import render_hcris_xray_page
        html = render_hcris_xray_page({"ccn": ["010001"]})
        self.assertIn("SOUTHEAST", html.upper())
        self.assertIn("data-sortable", html)
        self.assertIn("data-export-json", html)
        # Expect categorical headers
        self.assertIn("Payer Mix", html)
        self.assertIn("Margin", html)


class HTTPEndpointTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import http.server
        import socket
        import threading
        from rcm_mc.server import RCMHandler
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        cls.port = s.getsockname()[1]
        s.close()
        cls.server = http.server.ThreadingHTTPServer(
            ("127.0.0.1", cls.port), RCMHandler,
        )
        cls.thread = threading.Thread(
            target=cls.server.serve_forever, daemon=True,
        )
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_landing_endpoint(self):
        url = f"http://127.0.0.1:{self.port}/diligence/hcris-xray"
        r = urlopen(url, timeout=30)
        self.assertEqual(r.status, 200)
        body = r.read().decode("utf-8")
        self.assertIn("HCRIS", body)

    def test_xray_endpoint(self):
        url = (
            f"http://127.0.0.1:{self.port}"
            f"/diligence/hcris-xray?ccn=010001"
        )
        r = urlopen(url, timeout=30)
        self.assertEqual(r.status, 200)
        body = r.read().decode("utf-8")
        self.assertIn("SOUTHEAST", body.upper())


if __name__ == "__main__":
    unittest.main()
