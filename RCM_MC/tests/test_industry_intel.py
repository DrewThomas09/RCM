"""PEdesk Industry Intelligence — derived-data loader + license guardrails.

Data is licensed-IBISWorld-derived structured facts (raw PDFs never committed).
Tests assert the 5 reports load with full provenance, metrics/segments are real
and carry source attribution, NO long verbatim narrative leaks into the derived
JSON, NO raw PDFs are committed, and the source is registered. No runtime
network (loaders read committed files only).
"""
from __future__ import annotations

import http.client
import socket
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path

from rcm_mc.data import industry_intel as ii
from rcm_mc.server import build_server


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p

_MAX_SUMMARY = 400
_EXPECTED_SLUGS = {
    "healthcare-social-assistance", "primary-care-doctors", "specialist-doctors",
    "outpatient-care-centers", "hospitals",
}


class IndustryIntelLoaderTests(unittest.TestCase):
    def test_five_reports_with_provenance(self):
        reports = ii.load_industry_reports()
        self.assertEqual(len(reports), 5)
        self.assertEqual({r["slug"] for r in reports}, _EXPECTED_SLUGS)
        for r in reports:
            for field in ("naics_code", "report_title", "publisher",
                          "publication_date", "source_file", "license_note"):
                self.assertTrue(r.get(field), f"{r['slug']} missing {field}")
            self.assertEqual(r["source_kind"], "LICENSED_REPORT_DERIVED")
            self.assertEqual(r["publisher"], "IBISWorld")

    def test_lookups_resolve(self):
        self.assertEqual(ii.report_by_slug("hospitals")["naics_code"], "622110")
        self.assertEqual(ii.industry_for_naics("622110")["slug"], "hospitals")
        self.assertEqual(ii.industry_for_vertical("primary_care")["slug"],
                         "primary-care-doctors")
        self.assertTrue(ii.industry_for_keyword("dialysis"))

    def test_metrics_real_and_attributed(self):
        m = ii.load_industry_metrics("62111a")
        self.assertTrue(m)
        names = {x["metric_name"] for x in m}
        self.assertIn("Revenue", names)
        self.assertIn("Profit Margin", names)
        for row in m:
            self.assertTrue(row["license_note"])
            self.assertTrue(row["source_section"])
        # Primary-care revenue is ~$370bn ($370,800M) — a real extracted figure.
        rev = next(x for x in m if x["metric_name"] == "Revenue")
        self.assertGreater(float(rev["value"]), 300000)

    def test_segments_and_benchmarks_present(self):
        segs = ii.load_industry_segments("62111a")
        self.assertGreaterEqual(len(segs), 3)
        self.assertTrue(all(0 <= float(s["share"]) <= 100 for s in segs))
        bm = ii.load_industry_benchmarks("62211")
        self.assertTrue(bm)
        self.assertTrue(any("Cost:" in b["benchmark_name"] for b in bm))

    def test_questions_are_pedesk_authored(self):
        qs = ii.load_industry_questions("62211")
        self.assertTrue(qs)
        self.assertTrue(all(q["source_basis"] == "PEDESK" for q in qs))

    def test_no_verbatim_narrative_in_derived_json(self):
        # Guardrail: summaries are paraphrase-length, not copied report passages.
        for r in ii.load_industry_reports():
            self.assertLessEqual(len(r.get("summary_nonverbatim", "")), _MAX_SUMMARY)

    def test_no_raw_pdfs_committed(self):
        root = Path(__file__).resolve().parent.parent
        tracked = subprocess.run(
            ["git", "ls-files", "*.pdf"], cwd=root, capture_output=True, text=True)
        offenders = [l for l in tracked.stdout.splitlines()
                     if "Industry Report" in l or "industry_intel" in l]
        self.assertEqual(offenders, [], f"raw report PDFs committed: {offenders}")

    def test_source_registered(self):
        src = ii.industry_intel_sources()
        self.assertTrue(src)
        self.assertEqual(src[0]["source_id"], "industry_intel")


class IndustryRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls.tf.close()
        cls.port = _free_port()
        cls.server, _ = build_server(port=cls.port, db_path=cls.tf.name)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        import os
        os.unlink(cls.tf.name)

    def _get(self, path):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        c.request("GET", path)
        r = c.getresponse()
        b = r.read().decode("utf-8", "replace")
        c.close()
        return r.status, b

    def test_index_and_detail_render(self):
        s, b = self._get("/industry")
        self.assertEqual(s, 200)
        self.assertIn("Industry Intelligence", b)
        s, b = self._get("/industry/hospitals")
        self.assertEqual(s, 200)
        self.assertIn("Hospitals in the US", b)
        # Hospital page links to the real HCRIS X-Ray surface (value-add).
        self.assertIn("/diligence/hcris-xray", b)
        # Provenance / license chip present.
        self.assertIn("Licensed report derived", b)

    def test_primary_care_shows_real_and_connections(self):
        s, b = self._get("/industry/primary-care-doctors")
        self.assertEqual(s, 200)
        self.assertIn("Public data connections", b)
        self.assertIn("/physician-productivity", b)

    def test_unknown_slug_safe(self):
        s, b = self._get("/industry/not-an-industry")
        self.assertEqual(s, 200)
        self.assertIn("not found", b.lower())

    def test_brief_builder_renders(self):
        s, b = self._get("/industry/hospitals/brief")
        self.assertEqual(s, 200)
        self.assertIn("PEdesk Brief", b)
        # The brief includes the CMS/HCRIS validation layer (value-add).
        self.assertIn("/diligence/hcris-xray", b)
        self.assertIn("Diligence questions", b)
        s2, b2 = self._get("/industry/not-real/brief")
        self.assertEqual(s2, 200)
        self.assertIn("not found", b2.lower())

    def test_login_unaffected(self):
        s, _ = self._get("/login")
        self.assertIn(s, (200, 303, 302))


if __name__ == "__main__":
    unittest.main()
