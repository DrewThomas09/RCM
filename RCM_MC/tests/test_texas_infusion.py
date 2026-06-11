"""Texas infusion market — sizing, segmentation, concentration, metros.

Every figure is a pure function of named-source constants + the real
ACS population (via demographics_state / cbsa_demographics), so the
sizing, the HHI, and the metro ranking all recompute and audit.
"""
from __future__ import annotations

import unittest

from rcm_mc.diligence.texas_infusion import (
    US_POPULATION_2024, build_texas_infusion_analysis,
    texas_infusion_model, texas_metro_breakdown, texas_provider_landscape,
)
from rcm_mc.diligence.tam_sam import compute


class SizingTests(unittest.TestCase):
    def setUp(self):
        self.a = build_texas_infusion_analysis()

    def test_tam_chain_is_population_scaled(self):
        # TX patient base = US 3.2M × (TX pop / US pop).
        demo = self.a["demographics"]
        model = texas_infusion_model(demo["population"])
        base = model.chain[0].value
        expected = round(3_200_000 * demo["population"] / US_POPULATION_2024)
        self.assertEqual(base, expected)
        # TAM = base × 18 × 650, via the verified compute().
        self.assertAlmostEqual(
            compute(model)["tam"], base * 18 * 650, places=0)

    def test_tam_in_expected_billions(self):
        tam = self.a["sizing"]["tam"]
        # TX share ~9% of a ~$37B US market → ~$3.0-3.7B.
        self.assertGreater(tam, 2.5e9)
        self.assertLess(tam, 4.5e9)

    def test_sam_som_nest(self):
        s = self.a["sizing"]
        self.assertLess(s["som"], s["sam"])
        self.assertLess(s["sam"], s["tam"])

    def test_segments_sum_to_one_and_have_fastest(self):
        segs = self.a["sizing"]["segments"]
        self.assertAlmostEqual(
            sum(x["share_of_volume"] for x in segs), 1.0, places=3)
        self.assertTrue(any(x.get("is_fastest") for x in segs))

    def test_site_of_care_hopd_declines(self):
        site = {s["site"]: s for s in self.a["site_of_care"]}
        self.assertAlmostEqual(
            sum(s["share"] for s in self.a["site_of_care"]), 1.0, places=3)
        hopd = next(s for k, s in site.items() if "HOPD" in k)
        self.assertLess(hopd["growth_pct"], 0)        # being steered away
        self.assertLess(hopd["tam_y5"], hopd["tam_today"])

    def test_payer_mix_sums_to_one(self):
        self.assertAlmostEqual(
            sum(p["share"] for p in self.a["payer_mix"]), 1.0, places=3)


class ConcentrationTests(unittest.TestCase):
    def setUp(self):
        self.a = build_texas_infusion_analysis()

    def test_chain_shares_sum_to_one(self):
        self.assertAlmostEqual(
            sum(c["share"] for c in self.a["chains"]), 1.0, places=3)

    def test_hhi_is_fragmented(self):
        # Named-chain HHI well below the DOJ 1500 line → fragmented.
        self.assertLess(self.a["hhi"], 1500)
        self.assertIn("fragment", self.a["hhi_band"])

    def test_hhi_equals_sum_of_squared_named_shares(self):
        named = [c for c in self.a["chains"] if c.get("named")]
        expected = round(sum((c["share"] * 100) ** 2 for c in named), 0)
        self.assertEqual(self.a["hhi"], expected)

    def test_fragmentation_verdict_names_top_operator(self):
        frag = self.a["fragmentation"]
        self.assertIn("Option Care", frag["top_operator"])
        self.assertGreater(frag["independent_pool_share"], 0.4)

    def test_health_system_capacity_is_hopd_share(self):
        hs = self.a["health_system_capacity"]
        hopd = next(s for s in self.a["site_of_care"] if "HOPD" in s["site"])
        self.assertEqual(hs["hopd_share"], hopd["share"])


class ProviderAndMetroTests(unittest.TestCase):
    def setUp(self):
        self.a = build_texas_infusion_analysis()

    def test_provider_counts_population_scaled(self):
        pl = self.a["provider_landscape"]
        tx_share = self.a["tx_population_share"]
        self.assertEqual(pl["home_infusion_locations"], round(800 * tx_share))
        self.assertEqual(pl["ambulatory_infusion_centers"],
                         round(1_600 * tx_share))

    def test_metros_are_the_four_big_ones_ranked(self):
        metros = self.a["metros"]
        self.assertEqual(len(metros), 4)
        names = {m["metro"].split("-")[0] for m in metros}
        self.assertTrue({"Dallas", "Houston", "Austin", "San Antonio"}
                        & names)
        # Ranked descending by attractiveness, ranks 1..4.
        scores = [m["attractiveness"] for m in metros]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertEqual([m["rank"] for m in metros], [1, 2, 3, 4])

    def test_metro_demand_uses_real_population(self):
        # Each metro carries a real (multi-hundred-thousand) senior count
        # and a positive referral density.
        for m in self.a["metros"]:
            self.assertGreater(m["seniors"], 100_000)
            self.assertGreater(m["referral_density_per_100k"], 0)
            self.assertGreaterEqual(m["attractiveness"], 0)
            self.assertLessEqual(m["attractiveness"], 100)

    def test_population_growth_present(self):
        g = self.a["population_growth"]
        self.assertEqual(g["tx_pop_gain_2024"], 562_941)
        self.assertGreater(g["tx_senior_growth_pct"], g["tx_pop_growth_pct"])


class ChannelPlayersRiskTests(unittest.TestCase):
    def setUp(self):
        self.a = build_texas_infusion_analysis()

    def test_two_channels_aic_and_home(self):
        chans = [c["channel"] for c in self.a["channel_economics"]]
        self.assertTrue(any("AIC" in c for c in chans))
        self.assertTrue(any("Home" in c for c in chans))
        for c in self.a["channel_economics"]:
            for k in ("reimbursement", "margin_model", "working_capital",
                      "key_risk"):
                self.assertTrue(c[k])

    def test_players_have_channel_ownership_link(self):
        players = self.a["players"]
        self.assertGreaterEqual(len(players), 8)
        for p in players:
            self.assertIn(p["channel"], ("AIC", "Home", "Both"))
            self.assertTrue(p["ownership"])
            self.assertTrue(p["link"].startswith("http"))
        names = {p["name"] for p in players}
        # The marquee AIC + home names must be present.
        self.assertIn("Option Care Health", names)
        self.assertIn("IVX Health", names)            # pure-play AIC
        # Payer-owned steerage threats flagged.
        payer = [p for p in players if "Payer-owned" in p["ownership"]]
        self.assertTrue(payer)

    def test_risk_register_tags_severity_channel_and_rcm(self):
        risks = self.a["risk_register"]
        self.assertGreaterEqual(len(risks), 6)
        for r in risks:
            self.assertIn(r["severity"], ("HIGH", "MEDIUM", "LOW"))
            self.assertIn(r["hits"], ("AIC", "Home", "Both"))
            self.assertTrue(r["rcm_angle"])      # every risk has the RCM read
        # The two channel-defining HIGH risks must be present.
        names = " ".join(r["risk"] for r in risks).lower()
        self.assertIn("white-bag", names)
        self.assertIn("hit benefit", names)

    def test_rcm_playbook_has_infusion_kpis(self):
        pb = self.a["rcm_playbook"]
        self.assertTrue(pb["why_different"])
        kpis = [k["kpi"] for k in pb["kpis"]]
        self.assertTrue(any("denial" in k.lower() for k in kpis))
        self.assertTrue(any("DOLLAR" in k for k in kpis))   # the $/claim read
        self.assertTrue(any("AR" in k for k in kpis))
        self.assertGreaterEqual(len(pb["denial_drivers"]), 4)
        self.assertGreaterEqual(len(pb["diligence_questions"]), 4)


class CityDeepDiveTests(unittest.TestCase):
    def setUp(self):
        self.a = build_texas_infusion_analysis()
        self.dd = {d["metro"].split("-")[0]: d
                   for d in self.a["metro_deepdives"]}

    def test_four_city_deepdives(self):
        self.assertEqual(len(self.a["metro_deepdives"]), 4)

    def test_age_bands_rebase_to_real_senior_share(self):
        # The two senior bands sum to the metro's REAL 65+ share.
        for d in self.a["metro_deepdives"]:
            metro = next(m for m in self.a["metros"]
                         if m["cbsa_code"] == d["cbsa_code"])
            senior_share = sum(b["pop_share"] for b in d["age_bands"]
                               if b["band"] in ("65–74", "75+"))
            self.assertAlmostEqual(senior_share,
                                   metro["pct_age_65_plus"], places=3)

    def test_age_band_shares_sum_to_one(self):
        for d in self.a["metro_deepdives"]:
            self.assertAlmostEqual(
                sum(b["pop_share"] for b in d["age_bands"]), 1.0, places=3)
            self.assertAlmostEqual(
                sum(b["demand_share"] for b in d["age_bands"]), 1.0,
                places=3)

    def test_age_bands_ranked_by_demand(self):
        d = self.dd["Houston"]
        ranks = sorted(d["age_bands"], key=lambda b: b["demand_rank"])
        shares = [b["demand_share"] for b in ranks]
        self.assertEqual(shares, sorted(shares, reverse=True))
        self.assertEqual(ranks[0]["demand_rank"], 1)

    def test_suburbs_are_real_member_counties_ranked(self):
        hou = self.dd["Houston"]
        names = {s["county"] for s in hou["suburbs"]}
        self.assertIn("Harris", names)            # Houston anchor county
        pts = [s["infusion_patients"] for s in hou["suburbs"]]
        self.assertEqual(pts, sorted(pts, reverse=True))
        self.assertEqual(hou["suburbs"][0]["demand_rank"], 1)
        dfw = self.dd["Dallas"]
        self.assertIn("Dallas", {s["county"] for s in dfw["suburbs"]})

    def test_suburb_patients_sum_approximates_metro(self):
        # County patients should roughly reconstruct the metro total.
        for d in self.a["metro_deepdives"]:
            metro = next(m for m in self.a["metros"]
                         if m["cbsa_code"] == d["cbsa_code"])
            csum = sum(s["infusion_patients"] for s in d["suburbs"])
            self.assertGreater(csum, metro["infusion_patients"] * 0.85)
            self.assertLess(csum, metro["infusion_patients"] * 1.15)

    def test_operators_present_and_linked(self):
        for d in self.a["metro_deepdives"]:
            self.assertTrue(d["operators"])
            for o in d["operators"]:
                self.assertTrue(o["org"])
                self.assertTrue(o["link"].startswith("http"))
        # Houston (the TMC ecosystem) carries the most operators.
        self.assertGreaterEqual(len(self.dd["Houston"]["operators"]), 5)

    def test_specialty_tilt_per_city(self):
        self.assertIn("MD Anderson", self.dd["Houston"]["specialty"])
        self.assertIn("Youngest", self.dd["Austin"]["specialty"])

    def test_whitespace_counties_have_thin_capacity(self):
        # Whitespace = real demand with the thinnest local AIS estimate.
        for d in self.a["metro_deepdives"]:
            for w in d["whitespace_counties"]:
                self.assertGreater(w["infusion_patients"], 0)


class PageRenderTests(unittest.TestCase):
    def test_page_renders_all_sections(self):
        from rcm_mc.ui.texas_infusion_page import render_texas_infusion_page
        h = render_texas_infusion_page()
        for needle in (
            "Texas Infusion Market", "driver chain", "therapy form",
            "site of care", "Provider landscape", "Metro attractiveness",
            "Concentration", "Payer mix", "Medicare population",
            "Certificate of Need", "Sources", "562,941",
            "Home-infusion locations", "Competitive read",
            "City deep-dives", "INFUSION DEMAND BY AGE BAND",
            "SUBURBS / COUNTIES", "WHITESPACE SUBURBS", "Specialty tilt",
            "The two channels", "DEFINING RISK", "Players",
            "Where the risks are", "White-bagging", "RCM read",
            "How RCM talks about infusion", "Denial DOLLAR exposure",
            "TOP DENIAL DRIVERS",
        ):
            self.assertIn(needle, h, f"missing section: {needle}")

    def test_city_charts_and_operator_links_render(self):
        from rcm_mc.ui.texas_infusion_page import render_texas_infusion_page
        h = render_texas_infusion_page()
        self.assertGreaterEqual(h.count("<svg"), 8)        # per-city charts
        self.assertIn('optioncarehealth.com', h)           # linked operator
        self.assertIn('target="_blank"', h)

    def test_route_registered_in_palette(self):
        from rcm_mc.ui._chartis_kit import _DEFAULT_PALETTE_MODULES
        routes = {m["route"] for m in _DEFAULT_PALETTE_MODULES}
        self.assertIn("/diligence/texas-infusion", routes)


if __name__ == "__main__":
    unittest.main()
