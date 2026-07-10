"""Tests for the 2026-07-10 research-ingestion modules: the MMT company
dossier, the hospital-system profiles, the growth-evidence registry, and the
NPPES landscape. These guard the suite's grounding contract: no ILLUSTRATIVE
basis anywhere, every entry carries a source URL, and the vendored NPPES
registry loads and counts."""
import unittest

from rcm_mc.market_reports import ift_company as co
from rcm_mc.market_reports import ift_growth_evidence as ge
from rcm_mc.market_reports import ift_health_systems as hs
from rcm_mc.market_reports import ift_npi_landscape as npi


class CompanyDossierTests(unittest.TestCase):
    def test_npi_estate_shape(self):
        locs = co.MMT_NPI_LOCATIONS
        self.assertGreaterEqual(len(locs), 20)
        # every NPI is a 10-digit string, unique
        npis = [l.npi for l in locs]
        self.assertEqual(len(npis), len(set(npis)))
        for l in locs:
            self.assertEqual(len(l.npi), 10)
            self.assertTrue(l.npi.isdigit())
            self.assertTrue(l.city and l.state)

    def test_footprint_is_multistate(self):
        states = co.npi_states()
        # The research headline: MMT is NOT a NE/IA-only operator.
        for st in ("NE", "IA", "SD", "MO", "OH", "IN", "WI", "CO", "RI"):
            self.assertIn(st, states)
        self.assertGreater(len(co.expansion_locations()), 5)
        self.assertGreater(len(co.legacy_core_locations()), 10)

    def test_every_source_has_url_and_basis(self):
        for s in co.SOURCES.values():
            self.assertTrue(s.url.startswith("http"))
            self.assertIn(s.basis,
                          {"NPPES", "PRESS", "NEWS", "COURT", "ESTIMATE"})

    def test_ownership_timeline_and_litigation_sourced(self):
        self.assertGreaterEqual(len(co.OWNERSHIP_TIMELINE), 4)
        for ev in co.OWNERSHIP_TIMELINE:
            self.assertIn(ev.source_key, co.SOURCES)
        self.assertGreaterEqual(len(co.LITIGATION), 3)
        for lit in co.LITIGATION:
            self.assertIn(lit.source_key, co.SOURCES)

    def test_no_illustrative_label(self):
        import inspect
        src = inspect.getsource(co)
        self.assertNotIn('"ILLUSTRATIVE"', src)


class HealthSystemsTests(unittest.TestCase):
    def test_profiles_present(self):
        keys = {s.key for s in hs.systems()}
        for want in ("nebraska_medicine", "chi_health", "methodist",
                     "childrens", "bryan", "madonna", "great_plains",
                     "independents"):
            self.assertIn(want, keys)

    def test_every_profile_cited_and_complete(self):
        for s in hs.systems():
            self.assertTrue(s.sources, s.key)
            for u in s.sources:
                self.assertTrue(u.startswith("http"), s.key)
            self.assertTrue(s.facilities, s.key)
            self.assertTrue(s.ems_posture, s.key)
            self.assertTrue(s.ift_read, s.key)

    def test_ccn_registry(self):
        reg = dict(hs.ccn_registry())
        self.assertGreaterEqual(len(reg), 12)
        self.assertEqual(reg["Nebraska Medical Center"], "280013")
        # CCNs are 6 chars (or slash-joined pairs)
        for name, ccn in reg.items():
            for part in ccn.split("/"):
                self.assertEqual(len(part.strip()), 6, (name, ccn))

    def test_lookup(self):
        self.assertIsNotNone(hs.system_by_key("bryan"))
        self.assertIsNone(hs.system_by_key("nope"))


class GrowthEvidenceTests(unittest.TestCase):
    def test_registry_shape(self):
        evs = ge.all_evidence()
        self.assertGreaterEqual(len(evs), 25)
        keys = [e.key for e in evs]
        self.assertEqual(len(keys), len(set(keys)))
        for e in evs:
            self.assertIn(e.basis, {"GOV", "SOURCED", "ACADEMIC", "DERIVED"})
            self.assertTrue(e.url.startswith("http"), e.key)
            self.assertTrue(e.source, e.key)

    def test_every_theme_populated(self):
        for theme, _label in ge.THEMES:
            self.assertTrue(ge.by_theme(theme), theme)

    def test_verbatim_entries_have_quotes(self):
        for e in ge.all_evidence():
            if e.verbatim and e.key != "nppes_universe":
                self.assertTrue(e.quote, e.key)

    def test_headline_anchor(self):
        e = ge.evidence("ift_ed_trend")
        self.assertIsNotNone(e)
        self.assertTrue(e.verbatim)
        self.assertIn("35%", e.value)

    def test_reverify_queue_tracked(self):
        q = ge.reverify_queue()
        self.assertTrue(q)
        for e in q:
            self.assertFalse(e.verbatim, e.key)


class NpiLandscapeTests(unittest.TestCase):
    def test_registry_loads(self):
        reg = npi.registry()
        self.assertGreaterEqual(len(reg), 700)
        npis = [r.npi for r in reg]
        self.assertEqual(len(npis), len(set(npis)))

    def test_counts(self):
        ne = npi.counts_by_category("NE")
        ia = npi.counts_by_category("IA")
        self.assertGreater(ne.get("municipal-fire-volunteer", 0), 200)
        self.assertGreater(ne.get("private", 0), 30)
        self.assertGreater(ia.get("hospital-owned", 0), 20)

    def test_mmt_present_in_registry(self):
        names = {r.org_name.upper() for r in npi.registry()}
        self.assertTrue(any("MIDWEST MEDICAL TRANSPORT" in n
                            for n in names))

    def test_competitors_cited(self):
        for c in npi.COMPETITORS:
            self.assertTrue(c.npis, c.name)
            self.assertTrue(c.source_url.startswith("http"), c.name)

    def test_summary_degrades_never_raises(self):
        s = npi.summary()
        self.assertTrue(s["available"])
        self.assertIn("read", s)

    def test_claims_recipe_pinned(self):
        self.assertIn("2023", npi.CLAIMS_RECIPE["uuids"])
        self.assertEqual(len(npi.CLAIMS_RECIPE["hcpcs"]), 10)


if __name__ == "__main__":
    unittest.main()
