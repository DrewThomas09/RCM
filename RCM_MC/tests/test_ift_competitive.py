"""Real-path tests for the IFT competitive-landscape module.

Exercises the REAL ``ift_competitive`` functions against the REAL ``ift_geo`` /
``ift_analytics`` spines (no mocks of our own code) and pins the three contract
guarantees the shared brief requires:

  (a) results are non-empty and sane;
  (b) every figure/row carries a valid honesty basis in
      {GOV, SOURCED, ACADEMIC, ILLUSTRATIVE}, operator NAMES carry a PUBLIC-WEB
      note (never a data chip), and any density figure is SOURCED;
  (c) the functions degrade — never raise — if a dependency is unavailable.

Plus the SOW-specific content: the 4-5 archetypes exist, example operators are
REUSED from ift_geo (not invented), per-metro competition classifies every
operator and reads first-call + contestability, and MMT is positioned as the
dedicated outsourced IFT partner anchored to its SOURCED Omaha home market.
"""
from __future__ import annotations

import unittest

from rcm_mc.market_reports import ift_competitive as comp
from rcm_mc.market_reports import ift_geo as geo

_BASES = {"GOV", "SOURCED", "ACADEMIC", "ILLUSTRATIVE"}


def _leads_with_basis(label: str) -> bool:
    """A source_label must LEAD with an honest basis chip (the UI splits on
    ' · '), so its first token before the separator names one of the bases."""
    head = label.split(" · ", 1)[0].strip().upper()
    return any(head.startswith(b) for b in _BASES)


class ArchetypeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.aset = comp.competitive_archetypes()

    def test_available_and_nonempty(self):
        self.assertTrue(self.aset.available)
        # 4-5 archetypes per the SOW; we ship 5 (incl. MMT's own lane).
        self.assertGreaterEqual(len(self.aset.archetypes), 4)
        self.assertLessEqual(len(self.aset.archetypes), 5)
        self.assertTrue(_leads_with_basis(self.aset.source_label))

    def test_the_four_competitor_archetypes_present(self):
        keys = {a.key for a in self.aset.archetypes}
        for k in (comp.ARCH_NATIONAL, comp.ARCH_REGIONAL, comp.ARCH_MOMPOP,
                  comp.ARCH_HOSPITAL, comp.ARCH_DEDICATED):
            self.assertIn(k, keys, f"archetype {k} missing")

    def test_every_archetype_is_sane_and_labelled(self):
        for a in self.aset.archetypes:
            self.assertTrue(a.name and a.description and a.ift_posture, a.key)
            self.assertTrue(a.scale_magnitude and a.mmt_advantage, a.key)
            self.assertTrue(a.pros and a.cons, a.key)
            # honesty: dominant basis + the two figure-level bases are valid
            self.assertIn(a.basis, _BASES, a.key)
            self.assertEqual(a.scale_basis, "ILLUSTRATIVE", a.key)
            self.assertEqual(a.appearances_basis, "SOURCED", a.key)
            # names carry a PUBLIC-WEB note, never a data chip
            self.assertIn("PUBLIC-WEB", a.names_basis, a.key)
            self.assertTrue(_leads_with_basis(a.source_label), a.key)
            # SOURCED appearance count is a real non-negative integer
            self.assertGreaterEqual(a.n_footprint_metros, 0, a.key)

    def test_example_operators_are_reused_from_ift_geo(self):
        # Every example operator name must be derivable from a REAL ift_geo
        # named_operators string (reused, not invented).
        geo_names = set()
        for md in geo.MARKETS:
            for raw in md.named_operators:
                geo_names.add(comp._clean_name(raw))
        for a in self.aset.archetypes:
            for op in a.example_operators:
                self.assertIn(op, geo_names,
                              f"{a.key}: {op!r} not from ift_geo named_operators")

    def test_archetype_specific_operator_placement(self):
        by_key = {a.key: a for a in self.aset.archetypes}
        # MMT is the dedicated pure-play; it must land in its own lane only.
        ded = by_key[comp.ARCH_DEDICATED]
        self.assertTrue(any("Midwest Medical Transport" in o
                            for o in ded.example_operators))
        # National platforms include the footprint AMR/GMR book.
        nat = by_key[comp.ARCH_NATIONAL]
        self.assertTrue(any("AMR" in o or "GMR" in o
                            for o in nat.example_operators))
        # Scaled regionals include the brief's named comparables.
        reg = by_key[comp.ARCH_REGIONAL]
        self.assertTrue(any("AmeriPro" in o for o in reg.example_operators))
        self.assertTrue(any("Superior Air" in o for o in reg.example_operators))
        # Hospital-owned includes the captive Twin Cities / Mayo programs.
        hosp = by_key[comp.ARCH_HOSPITAL]
        joined = " ".join(hosp.example_operators)
        self.assertTrue("Allina" in joined or "Mayo" in joined
                        or "North Memorial" in joined)

    def test_dedicated_lane_is_thinly_contested(self):
        # The whitespace thesis: MMT is essentially alone in the dedicated lane
        # across the footprint, while national platforms appear in many metros.
        by_key = {a.key: a for a in self.aset.archetypes}
        ded = by_key[comp.ARCH_DEDICATED]
        nat = by_key[comp.ARCH_NATIONAL]
        self.assertEqual(len(ded.example_operators), 1)  # only MMT
        self.assertGreaterEqual(nat.n_footprint_metros, ded.n_footprint_metros)


class ClassifierTests(unittest.TestCase):
    def test_known_operators_classify_correctly(self):
        cases = {
            "Midwest Medical Transport (MMT, Omaha HQ)": comp.ARCH_DEDICATED,
            "AMR / GMR KC Metro (dual KS+MO-licensed)": comp.ARCH_NATIONAL,
            "Lifecare Medical Transports (Priority Ambulance brand)": comp.ARCH_NATIONAL,
            "AmeriPro Health (Lancaster County)": comp.ARCH_REGIONAL,
            "Priority Medical Transport (acquired by AmeriPro)": comp.ARCH_REGIONAL,
            "Superior Air-Ground (Mount Carmel)": comp.ARCH_REGIONAL,
            "Ryan Brothers Ambulance (dominant private)": comp.ARCH_REGIONAL,
            "Bell Ambulance (IFT-specialized)": comp.ARCH_REGIONAL,
            "Allina Health EMS (hospital-owned)": comp.ARCH_HOSPITAL,
            "Mayo Clinic Ambulance (ex-Gold Cross)": comp.ARCH_HOSPITAL,
            "MercyOne Des Moines Ambulance (hospital-based)": comp.ARCH_HOSPITAL,
            "Omaha Fire Department (municipal 911)": comp.TAG_MUNICIPAL,
            "Sedgwick County EMS (public-utility 911 + IFT)": comp.TAG_MUNICIPAL,
            "CRMC-UCHealth LifeLine + Banner-MedTrans (air, EXCLUDED from TAM)": comp.TAG_AIR,
            "Curtis Ambulance (since 1858)": comp.ARCH_MOMPOP,
        }
        for raw, expect in cases.items():
            self.assertEqual(comp.classify_operator(raw), expect,
                             f"{raw!r} → {comp.classify_operator(raw)} != {expect}")

    def test_classifier_degrades_on_junk(self):
        # Empty / unknown never raise; unknown private defaults to mom-and-pop.
        self.assertEqual(comp.classify_operator(""), comp.ARCH_MOMPOP)
        self.assertEqual(comp.classify_operator("   "), comp.ARCH_MOMPOP)
        self.assertEqual(comp.classify_operator("Some Unlisted Local LLC"),
                         comp.ARCH_MOMPOP)

    def test_every_registry_operator_classifies_to_a_known_tag(self):
        valid = {comp.ARCH_NATIONAL, comp.ARCH_REGIONAL, comp.ARCH_MOMPOP,
                 comp.ARCH_HOSPITAL, comp.ARCH_DEDICATED, comp.TAG_MUNICIPAL,
                 comp.TAG_AIR}
        for md in geo.MARKETS:
            for raw in md.named_operators:
                tag = comp.classify_operator(raw)
                self.assertIn(tag, valid, f"{raw!r} → {tag}")
                self.assertTrue(comp.archetype_label(tag))


class MarketCompetitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mc = comp.market_competition()

    def test_available_and_one_row_per_market(self):
        self.assertTrue(self.mc.available)
        self.assertEqual(len(self.mc.rows), len(geo.MARKETS))
        self.assertTrue(_leads_with_basis(self.mc.source_label))

    def test_every_row_is_sane_and_labelled(self):
        for r in self.mc.rows:
            self.assertTrue(r.name and r.region_label and r.insource_class, r.name)
            self.assertTrue(r.operators, f"{r.name}: no operators")
            self.assertTrue(r.first_call_today, r.name)       # PUBLIC-WEB read
            self.assertTrue(r.contestability_tier and r.contestability, r.name)
            self.assertTrue(r.moat_note, r.name)
            # (b) honesty bases
            self.assertIn(r.basis, _BASES, r.name)
            self.assertTrue(r.density_basis.startswith("SOURCED"), r.name)
            self.assertIn("PUBLIC-WEB", r.names_basis, r.name)
            self.assertEqual(r.contestability_basis.split(" · ")[0], "ILLUSTRATIVE",
                             r.name)
            self.assertTrue(_leads_with_basis(r.source_label), r.name)
            # SOURCED density is a non-negative count
            self.assertGreaterEqual(r.n_nodes, 0, r.name)
            # every operator present carries a real archetype classification
            for p in r.operators:
                self.assertTrue(p.operator, r.name)
                self.assertTrue(p.archetype and p.archetype_label, r.name)

    def test_serviceable_share_matches_sizing_model(self):
        # The contestability score reuses ift_analytics.sam_formula's s(m).
        from rcm_mc.market_reports import ift_analytics as an
        sam = an.sam_formula()
        if not sam.available:
            self.skipTest("sam_formula unavailable offline")
        s_by = {row.name: row.serviceable_share for row in sam.rows}
        for r in self.mc.rows:
            self.assertAlmostEqual(r.serviceable_share, s_by[r.name], places=6,
                                   msg=r.name)

    def test_mmt_present_in_nebraska_corridor(self):
        by_name = {r.name: r for r in self.mc.rows}
        for neb in ("Omaha", "Lincoln"):
            self.assertTrue(by_name[neb].mmt_present, f"MMT missing in {neb}")
        # Rochester (Mayo captive) is NOT an MMT market.
        self.assertFalse(by_name["Rochester (MN)"].mmt_present)

    def test_density_matches_metro_structure(self):
        # SOURCED node density must equal the live ift_geo structure.
        for r in self.mc.rows:
            st = geo.metro_structure(r.name)
            if st.available:
                self.assertEqual(r.n_nodes, st.n_nodes, r.name)
                self.assertEqual(r.density_tier, st.density_tier, r.name)


class MmtPositioningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mp = comp.mmt_positioning()

    def test_available_and_structured(self):
        self.assertTrue(self.mp.available)
        self.assertEqual(len(self.mp.pillars), 5)
        self.assertEqual(len(self.mp.vs_archetype), 4)   # vs the 4 competitors
        self.assertTrue(self.mp.headline and self.mp.reference_note)
        self.assertTrue(_leads_with_basis(self.mp.source_label))

    def test_all_five_pillars_named(self):
        names = " ".join(p.pillar.lower() for p in self.mp.pillars)
        for token in ("dedicated", "dispatch", "revenue", "workflow", "partnership"):
            self.assertIn(token, names, f"pillar theme {token} missing")

    def test_pillars_labelled_and_sane(self):
        for p in self.mp.pillars:
            self.assertTrue(p.pillar and p.mmt_stance and p.vs_alternatives, p.pillar)
            self.assertIn(p.basis, _BASES, p.pillar)

    def test_omaha_reference_is_sourced(self):
        # MMT is the Omaha reference incumbent; density snapshot is SOURCED and
        # matches the live ift_geo structure.
        self.assertEqual(self.mp.reference_market, "Omaha")
        self.assertTrue(self.mp.home_structure_basis.startswith("SOURCED"))
        st = geo.metro_structure("Omaha")
        if st.available:
            self.assertEqual(self.mp.home_n_hospitals, st.n_hospitals)
            self.assertEqual(self.mp.home_n_nodes, st.n_nodes)
            self.assertEqual(self.mp.home_snf_beds, st.snf_beds)
            self.assertGreater(self.mp.home_n_hospitals, 0)

    def test_vs_archetype_covers_the_four_competitors(self):
        labels = " ".join(name for name, _ in self.mp.vs_archetype)
        for token in ("National", "regional", "Mom-and-pop", "Hospital-owned"):
            self.assertIn(token, labels, f"vs-archetype missing {token}")
        for _, edge in self.mp.vs_archetype:
            self.assertTrue(edge.strip())


class DegradeTests(unittest.TestCase):
    """(c) The functions must degrade — never raise — when a dependency is
    unavailable. We simulate an unreadable ift_geo by monkeypatching the module's
    cached MARKETS accessor to return empty, then confirm honest unavailability."""

    def setUp(self):
        comp._markets.cache_clear()
        comp._serviceable_share_by_metro.cache_clear()
        comp.competitive_archetypes.cache_clear()
        comp.market_competition.cache_clear()
        comp.mmt_positioning.cache_clear()

    def tearDown(self):
        # Restore + drop any patched caches so later tests see the real data.
        comp._markets.cache_clear()
        comp._serviceable_share_by_metro.cache_clear()
        comp.competitive_archetypes.cache_clear()
        comp.market_competition.cache_clear()
        comp.mmt_positioning.cache_clear()

    def test_archetypes_degrade_without_markets(self):
        orig = comp._markets
        comp._markets = lambda: tuple()  # type: ignore[assignment]
        try:
            aset = comp.competitive_archetypes.__wrapped__()  # bypass cache
            self.assertFalse(aset.available)
            self.assertTrue(_leads_with_basis(aset.source_label))
            self.assertIn("unavailable", aset.note.lower())
        finally:
            comp._markets = orig

    def test_market_competition_degrades_without_markets(self):
        orig = comp._markets
        comp._markets = lambda: tuple()  # type: ignore[assignment]
        try:
            mc = comp.market_competition.__wrapped__()
            self.assertFalse(mc.available)
            self.assertEqual(mc.rows, [])
            self.assertTrue(_leads_with_basis(mc.source_label))
        finally:
            comp._markets = orig

    def test_positioning_degrades_without_ift_geo(self):
        # Positioning still returns available=True (its pillars are authored), but
        # the SOURCED Omaha snapshot degrades to zeros with an honest basis note
        # rather than raising when metro_structure is unreadable. ``from . import
        # ift_geo`` resolves the submodule off the PACKAGE attribute, so we patch
        # that (not sys.modules) to simulate the dependency blowing up.
        import rcm_mc.market_reports as pkg
        real_geo = pkg.ift_geo

        class _Boom:
            def metro_structure(self, *a, **k):
                raise RuntimeError("simulated ift_geo failure")

        pkg.ift_geo = _Boom()  # type: ignore[assignment]
        try:
            mp = comp.mmt_positioning.__wrapped__()
            self.assertTrue(mp.available)          # authored content still renders
            self.assertEqual(mp.home_n_nodes, 0)   # SOURCED snapshot degraded
            self.assertIn("unavailable", mp.home_structure_basis.lower())
        finally:
            pkg.ift_geo = real_geo


if __name__ == "__main__":
    unittest.main()
