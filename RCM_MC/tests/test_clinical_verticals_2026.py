"""Clinical-specialty verticals reference (CY2026) — data + page + route.

Asserts the 13-vertical registry is internally consistent (every vertical
cites sources, every Stat carries provenance, ranges are well-formed),
the query helpers resolve by alias and by code (incl. ICD-10 prefix),
the ASC-site-shift filter matches the brief, the conversion factors are
re-exported (not restated) from fee_schedule_2026, and the /clinical-
verticals page renders + routes over a real HTTP server with no network.
"""
from __future__ import annotations

import http.client
import socket
import tempfile
import threading
import unittest

from rcm_mc.data_public.clinical_verticals_2026 import (
    ASC_CF_2026, CLINICAL_VERTICALS_2026, OPPS_CF_2026, PFS_CF_NONQP_2026,
    POLICY_DRIVERS_2026, ClinicalVertical, Stat, get_vertical, list_verticals,
    search_by_code, verticals_with_asc_cpl_2026, volume_anchors,
)
from rcm_mc.data_public.fee_schedule_2026 import FEE_SCHEDULE_BACKBONE_2026
from rcm_mc.server import build_server


class RegistryShapeTests(unittest.TestCase):
    def test_thirteen_verticals(self):
        self.assertEqual(len(CLINICAL_VERTICALS_2026), 13)

    def test_keys_match_self(self):
        for key, v in CLINICAL_VERTICALS_2026.items():
            self.assertEqual(key, v.key)
            self.assertIsInstance(v, ClinicalVertical)

    def test_every_vertical_has_sources_and_name(self):
        for v in CLINICAL_VERTICALS_2026.values():
            self.assertTrue(v.name, v.key)
            self.assertTrue(v.summary, v.key)
            self.assertGreaterEqual(len(v.sources), 1, v.key)

    def test_every_vertical_has_at_least_one_code_or_taxonomy(self):
        for v in CLINICAL_VERTICALS_2026.values():
            self.assertTrue(v.all_codes() or v.key == "aco_vbc", v.key)

    def test_policy_keys_resolve(self):
        for v in CLINICAL_VERTICALS_2026.values():
            for pk in v.policy_2026:
                self.assertIn(pk, POLICY_DRIVERS_2026, f"{v.key}:{pk}")

    def test_every_viz_has_type_and_description(self):
        for v in CLINICAL_VERTICALS_2026.values():
            self.assertGreaterEqual(len(v.viz), 1, v.key)
            for z in v.viz:
                self.assertTrue(z.chart_type)
                self.assertTrue(z.description)


class StatProvenanceTests(unittest.TestCase):
    def _all_stats(self):
        for v in CLINICAL_VERTICALS_2026.values():
            for s in (v.epidemiology + v.workforce + v.access + v.benchmarks):
                yield v.key, s

    def test_every_stat_cites_a_source(self):
        for key, s in self._all_stats():
            self.assertIsInstance(s, Stat)
            self.assertTrue(s.source, f"{key}:{s.label}")
            self.assertTrue(s.unit, f"{key}:{s.label}")

    def test_ranges_are_well_formed(self):
        # If both bounds are present, low <= central <= high.
        for key, s in self._all_stats():
            if s.low is not None and s.high is not None:
                self.assertLessEqual(s.low, s.high, f"{key}:{s.label}")
                if s.value is not None:
                    self.assertLessEqual(s.low, s.value, f"{key}:{s.label}")
                    self.assertLessEqual(s.value, s.high, f"{key}:{s.label}")


class QueryHelperTests(unittest.TestCase):
    def test_get_by_key_and_alias(self):
        self.assertEqual(get_vertical("ophthalmology").key, "ophthalmology")
        self.assertEqual(get_vertical("retina").key, "ophthalmology")
        self.assertEqual(get_vertical("  CARDIAC ").key, "cardiology")
        self.assertEqual(get_vertical("mssp").key, "aco_vbc")

    def test_get_unknown_raises(self):
        with self.assertRaises(KeyError):
            get_vertical("dermatology")

    def test_list_is_name_sorted_and_complete(self):
        vs = list_verticals()
        self.assertEqual(len(vs), 13)
        self.assertEqual([v.name for v in vs],
                         sorted(v.name for v in vs))

    def test_search_exact_code(self):
        hits = [v.key for v in search_by_code("66984")]
        self.assertEqual(hits, ["ophthalmology"])

    def test_search_icd10_prefix(self):
        # H25.1 should resolve via the H25 category entry.
        hits = [v.key for v in search_by_code("H25.1")]
        self.assertIn("ophthalmology", hits)

    def test_search_jcode(self):
        self.assertIn("oncology", [v.key for v in search_by_code("J9271")])

    def test_search_empty_and_miss(self):
        self.assertEqual(search_by_code(""), [])
        self.assertEqual(search_by_code("99999"), [])

    def test_asc_filter_matches_brief(self):
        keys = {v.key for v in verticals_with_asc_cpl_2026()}
        # The five procedural verticals the brief flags for the 2026
        # ASC site-shift agenda.
        self.assertEqual(
            keys,
            {"ophthalmology", "cardiology", "urology", "otolaryngology",
             "anesthesia_pain"},
        )

    def test_volume_anchors_sorted_descending(self):
        anchors = volume_anchors()
        self.assertTrue(anchors)
        vals = [s.value for s in anchors]
        self.assertEqual(vals, sorted(vals, reverse=True))
        # The biggest single anchor is the BPH-affected-men figure (~40M).
        self.assertGreaterEqual(anchors[0].value, 30e6)


class ConversionFactorReuseTests(unittest.TestCase):
    def test_cfs_reexported_not_restated(self):
        # The module must mirror fee_schedule_2026 exactly — one source
        # of truth for the dollar constants.
        b = FEE_SCHEDULE_BACKBONE_2026
        self.assertEqual(PFS_CF_NONQP_2026, b["pfs_cf_nonqp"].value)
        self.assertEqual(OPPS_CF_2026, b["opps_cf"].value)
        self.assertEqual(ASC_CF_2026, b["asc_cf"].value)
        self.assertEqual(PFS_CF_NONQP_2026, 33.4009)


class PageRenderTests(unittest.TestCase):
    def test_page_renders_key_content(self):
        import html as _html
        from rcm_mc.ui.clinical_verticals_page import render_clinical_verticals
        page = render_clinical_verticals()
        self.assertIn("Clinical Verticals Reference", page)
        self.assertIn("Ophthalmology", page)
        self.assertIn("Maternity-care-desert", page)
        self.assertIn("33.4009", page)
        # Every vertical name appears on the page (escaped, since names
        # like "OB-GYN / Women's Health" carry an apostrophe).
        for v in CLINICAL_VERTICALS_2026.values():
            self.assertIn(_html.escape(v.name), page, v.key)


def _free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close()
    return p


class RouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls.tf.close()
        cls.port = _free_port()
        cls.server, _ = build_server(port=cls.port, db_path=cls.tf.name)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close()
        import os
        os.unlink(cls.tf.name)

    def _get(self, path):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        c.request("GET", path)
        r = c.getresponse(); b = r.read().decode("utf-8", "replace"); c.close()
        return r.status, b

    def test_route_resolves(self):
        status, body = self._get("/clinical-verticals")
        self.assertEqual(status, 200)
        self.assertIn("Clinical Verticals Reference", body)

    def test_palette_entry_present(self):
        from rcm_mc.ui._chartis_kit import _DEFAULT_PALETTE_MODULES
        routes = {m["route"] for m in _DEFAULT_PALETTE_MODULES}
        self.assertIn("/clinical-verticals", routes)


if __name__ == "__main__":
    unittest.main()
