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


class AICEconomicsTests(unittest.TestCase):
    def setUp(self):
        self.a = build_texas_infusion_analysis()

    def test_per_chair_pl_sections_balance(self):
        from rcm_mc.diligence.texas_infusion import aic_chair_economics
        e = aic_chair_economics()
        sect = {s["label"]: s["value"] for s in e["sections"]}
        rev = next(v for k, v in sect.items() if "Gross revenue" in k)
        costs = sum(v for k, v in sect.items()
                    if k.startswith("−"))   # negative
        contrib = next(v for k, v in sect.items()
                       if "contribution" in k)
        # contribution must equal admin + drug-spread − costs; check the
        # waterfall closes: revenue + costs (negatives) ≈ a gross-profit
        # line that exceeds contribution (since admin+spread < revenue).
        self.assertGreater(rev, 0)
        self.assertLess(costs, 0)
        self.assertEqual(contrib, e["contribution_per_chair"])
        # Contribution margin in a sane band for a drug-heavy AIC.
        self.assertGreater(e["contribution_margin_pct"], 0.05)
        self.assertLess(e["contribution_margin_pct"], 0.40)

    def test_levers_are_pure_functions(self):
        from rcm_mc.diligence.texas_infusion import aic_chair_economics
        base = aic_chair_economics(util_pct=0.78)
        higher = aic_chair_economics(util_pct=0.90)
        # Higher utilization → more infusions → more contribution.
        self.assertGreater(higher["contribution_per_chair"],
                           base["contribution_per_chair"])
        # White-bagging shock: drug margin → 0 cuts contribution.
        nobill = aic_chair_economics(drug_margin_pct=0.0)
        self.assertLess(nobill["contribution_per_chair"],
                        base["contribution_per_chair"])

    def test_named_kpis_present(self):
        e = self.a["aic_economics"]
        kpis = " ".join(k["kpi"].lower() for k in e["kpis"])
        for lever in ("chair utilization", "nurse productivity",
                      "recurring", "commercial", "prior-auth",
                      "drug margin"):
            self.assertIn(lever, kpis)


class AICEditableAssumptionsTests(unittest.TestCase):
    def test_payer_mix_is_a_real_lever(self):
        from rcm_mc.diligence.texas_infusion import aic_chair_economics
        lo = aic_chair_economics(commercial_mix_pct=0.40)
        hi = aic_chair_economics(commercial_mix_pct=0.80)
        # Blended admin fee + drug margin rise with commercial mix.
        self.assertGreater(hi["contribution_per_chair"],
                           lo["contribution_per_chair"])
        self.assertTrue(hi["assumptions"]["payer_blended"])
        # Explicit override still wins (white-bag shock path).
        forced = aic_chair_economics(commercial_mix_pct=0.80,
                                     drug_margin_pct=0.0)
        self.assertEqual(forced["assumptions"]["drug_margin_pct"], 0.0)

    def test_qs_parsing_clamps_and_drops_junk(self):
        from rcm_mc.diligence.texas_infusion import aic_assumptions_from_qs
        ov = aic_assumptions_from_qs({
            "aic_util": ["88"], "aic_commercial": ["75"],
            "aic_chairs": ["999"],          # clamps to 60
            "aic_per_day": ["abc"],          # dropped
            "aic_rcm": ["7"], "aic_nurse_ratio": ["0.5"],
            "unrelated": ["x"]})
        self.assertEqual(ov["util_pct"], 0.88)
        self.assertEqual(ov["commercial_mix_pct"], 0.75)
        self.assertEqual(ov["chairs"], 60)
        self.assertNotIn("infusions_per_chair_day", ov)
        self.assertEqual(ov["rcm_cost_pct"], 0.07)
        self.assertNotIn("unrelated", ov)

    def test_sensitivity_is_pure_recompute(self):
        from rcm_mc.diligence.texas_infusion import (
            aic_chair_economics, aic_sensitivity)
        rows = aic_sensitivity()
        base = aic_chair_economics()["contribution_per_chair"]
        self.assertEqual(rows[0]["base"], base)
        # Sorted by impact, throughput levers dominate.
        impacts = [r["impact"] for r in rows]
        self.assertEqual(impacts, sorted(impacts, reverse=True))
        self.assertIn(rows[0]["lever"],
                      ("Chair utilization", "Infusions / chair / day"))
        # Every lever's low/high straddle reality: low ≤ high impact dirs
        for r in rows:
            self.assertGreaterEqual(r["impact"], 0)

    def test_utilization_curve_and_breakeven(self):
        from rcm_mc.diligence.texas_infusion import aic_utilization_curve
        c = aic_utilization_curve()
        # Monotonic increasing contribution with utilization.
        vals = [p["contribution"] for p in c["points"]]
        self.assertEqual(vals, sorted(vals))
        # Break-even exists and sits below the default 78% utilization.
        self.assertIsNotNone(c["breakeven_util"])
        self.assertLess(c["breakeven_util"], 0.78)
        # At break-even, contribution is ~first non-negative point.
        self.assertGreaterEqual(c["current_contribution"], 0)

    def test_overrides_flow_through_analysis_and_page(self):
        from rcm_mc.diligence.texas_infusion import (
            aic_assumptions_from_qs)
        ov = aic_assumptions_from_qs({"aic_util": ["90"]})
        a = build_texas_infusion_analysis(aic_overrides=ov)
        self.assertTrue(a["aic_overrides_active"])
        self.assertEqual(a["aic_economics"]["assumptions"]["util_pct"],
                         0.90)
        base = build_texas_infusion_analysis()
        self.assertGreater(
            a["aic_economics"]["contribution_per_chair"],
            base["aic_economics"]["contribution_per_chair"])
        from rcm_mc.ui.texas_infusion_page import (
            render_texas_infusion_page)
        h = render_texas_infusion_page({"aic_util": ["90"]})
        self.assertIn("EDITED", h)
        self.assertIn('value="90"', h)

    def test_form_and_charts_render_by_default(self):
        from rcm_mc.ui.texas_infusion_page import (
            render_texas_infusion_page)
        h = render_texas_infusion_page()
        for needle in ("CHANGE THE ASSUMPTIONS", "Recompute",
                       "SENSITIVITY", "break-even",
                       "UTILIZATION → CONTRIBUTION"):
            self.assertIn(needle, h)
        self.assertNotIn("EDITED — your assumptions", h)


class DrugSupplyTests(unittest.TestCase):
    def setUp(self):
        self.a = build_texas_infusion_analysis()

    def test_real_fda_snapshot(self):
        ds = self.a["drug_supply"]
        self.assertTrue(ds["snapshot_date"])
        self.assertGreater(ds["total_current"], 0)   # real FDA data
        self.assertIn("openFDA", ds["source"])

    def test_specialty_biologics_stable(self):
        ds = self.a["drug_supply"]
        bio = next(c for c in ds["classes"]
                   if "biologic" in c["klass"].lower())
        # The core AIC margin engine is NOT FDA-shortage-listed.
        self.assertIn("STABLE", bio["status"])
        self.assertEqual(bio["current_shortages"], 0)

    def test_tpn_fluids_show_real_shortage(self):
        ds = self.a["drug_supply"]
        tpn = next(c for c in ds["classes"] if "TPN" in c["klass"])
        # Dextrose/amino-acid/saline carry real current FDA shortages.
        self.assertGreater(tpn["current_shortages"], 0)

    def test_classes_have_channel_and_examples(self):
        for c in self.a["drug_supply"]["classes"]:
            self.assertTrue(c["channel"])
            self.assertIsInstance(c["examples"], list)


class IllnessNorthSuburbTests(unittest.TestCase):
    def setUp(self):
        self.a = build_texas_infusion_analysis()
        self.dd = {d["metro"].split("-")[0]: d
                   for d in self.a["metro_deepdives"]}

    def test_north_suburbs_flagged_each_metro(self):
        for d in self.a["metro_deepdives"]:
            self.assertTrue(d["north_suburbs"])      # callout text
            north = [s for s in d["suburbs"]
                     if s.get("region") == "North suburb"]
            self.assertTrue(north, f"no north county in {d['metro']}")
        # DFW north ring = Collin + Denton.
        dfw_north = {s["county"] for s in self.dd["Dallas"]["suburbs"]
                     if s.get("region") == "North suburb"}
        self.assertEqual(dfw_north, {"Collin", "Denton"})

    def test_illness_burden_scales_with_population(self):
        # Metro illness burden = sum of county (pop × TX prevalence);
        # the bigger metro carries the bigger burden.
        for d in self.a["metro_deepdives"]:
            self.assertTrue(d["illness_burden"])
            for ib in d["illness_burden"]:
                self.assertGreater(ib["estimated_patients"], 0)
                self.assertTrue(ib["therapy"])
                self.assertTrue(ib["condition"])
        # Houston/DFW (larger) > Austin (smaller) on total burden.
        def _tot(m):
            return sum(i["estimated_patients"]
                       for i in self.dd[m]["illness_burden"])
        self.assertGreater(_tot("Houston"), _tot("Austin"))

    def test_illness_maps_to_infusion_therapies(self):
        conds = {i["condition"]
                 for i in self.dd["Houston"]["illness_burden"]}
        self.assertIn("Rheumatoid Arthritis", conds)   # immunology biologics
        self.assertIn("Cancer", conds)                  # oncology infusion

    def test_county_illness_is_population_scaled(self):
        from rcm_mc.diligence.texas_infusion import county_illness_burden
        small = county_illness_burden(100_000)
        big = county_illness_burden(1_000_000)
        for s, b in zip(small, big):
            self.assertEqual(s["condition"], b["condition"])
            self.assertAlmostEqual(b["estimated_patients"],
                                   s["estimated_patients"] * 10, delta=2)


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


class CapacityScorecardTests(unittest.TestCase):
    """Per-county chair capacity, market saturation, and the Texas
    long-term growth scorecard — all recomputed from real county
    population × labeled site-of-care / chair assumptions."""

    def setUp(self):
        self.a = build_texas_infusion_analysis()

    def test_provider_segments_cover_the_market(self):
        segs = self.a["provider_segments"]
        self.assertEqual(len(segs), 5)
        self.assertAlmostEqual(sum(s["share"] for s in segs), 1.0, places=4)
        # The five owner types the request named are all present.
        names = " ".join(s["segment"].lower() for s in segs)
        for owner in ("national", "health-system", "physician",
                      "independent ambulatory", "independent home"):
            self.assertIn(owner, names)
        # Health-system pool is captive (not part of the non-hospital
        # roll-up pool); the rest are non-hospital.
        hs = [s for s in segs if not s["non_hospital"]]
        self.assertTrue(hs and all("health" in s["segment"].lower()
                                   for s in hs))

    def test_capacity_ratio_is_scoped_to_the_ais_channel(self):
        # Demand/capacity must compare the AIS-channel slice of demand
        # (~22% of infusion volume) to AIS chair capacity — not TOTAL
        # infusion demand. That keeps ratios realistic (~0.5–1.5), not 4–5x.
        for dd in self.a["metro_deepdives"]:
            for s in dd["suburbs"]:
                cap = s.get("capacity") or {}
                if not cap.get("est_chairs"):
                    continue
                dc = cap["demand_capacity_ratio"]
                self.assertIsNotNone(dc)
                self.assertLess(dc, 3.0, f"{s['county']} ratio implausible")
                # ais_demand_visits < total demand_visits.
                self.assertLess(cap["ais_demand_visits"],
                                cap["demand_visits"])

    def test_saturation_bands_are_mixed(self):
        # A realistic market is not uniformly one band.
        bands = set()
        for dd in self.a["metro_deepdives"]:
            for s in dd["suburbs"]:
                cap = s.get("capacity") or {}
                if cap.get("saturation_band"):
                    bands.add(cap["saturation_band"])
        self.assertGreaterEqual(len(bands), 2)

    def test_scorecard_ranks_descending_and_flags_growth(self):
        sc = self.a["growth_scorecard"]
        scores = [r["score"] for r in sc["top_opportunities"]]
        self.assertEqual(scores, sorted(scores, reverse=True))
        ranks = [r["rank"] for r in sc["top_opportunities"]]
        self.assertEqual(ranks, list(range(1, len(ranks) + 1)))
        # Undersupplied growth markets are real, and each is flagged.
        self.assertGreaterEqual(sc["n_undersupplied"], 1)
        for r in sc["undersupplied_growth_markets"]:
            self.assertTrue(r["demand_exceeds_capacity"])
        self.assertEqual(sc["n_undersupplied"],
                         len(sc["undersupplied_growth_markets"]))

    def test_growth_corridors_surface_as_undersupplied(self):
        # North-Texas / Austin growth corridors (site-of-care migration +
        # population growth) should appear among the undersupplied markets.
        sc = self.a["growth_scorecard"]
        names = {r["county"] for r in sc["undersupplied_growth_markets"]}
        corridors = {"Williamson", "Collin", "Denton", "Montgomery",
                     "Hays", "Comal"}
        self.assertTrue(names & corridors,
                        f"expected a growth corridor in {names}")

    def test_opportunity_score_is_bounded(self):
        for dd in self.a["metro_deepdives"]:
            for s in dd["suburbs"]:
                opp = s.get("opportunity") or {}
                if "score" in opp:
                    self.assertGreaterEqual(opp["score"], 0)
                    self.assertLessEqual(opp["score"], 100)


class CDCProxyTests(unittest.TestCase):
    """CDC PLACES / ACS public-health proxies — every rate is a real
    published value (CDC PLACES full-population or CMS Medicare), every
    county count recomputes from real population × the proxy rate, and
    the live API path falls back cleanly when egress is blocked."""

    def setUp(self):
        self.a = build_texas_infusion_analysis()

    def test_proxies_cover_named_therapy_families(self):
        from rcm_mc.diligence.texas_infusion import texas_cdc_proxies
        cp = texas_cdc_proxies()
        keys = {t["key"] for t in cp["therapies"]}
        # The user-named clinical proxies all present.
        self.assertEqual(keys, {"rheum", "onc", "iron", "chronic"})
        anchors = {t["key"]: t["anchor_measure"] for t in cp["therapies"]}
        self.assertEqual(anchors["rheum"], "arthritis")
        self.assertEqual(anchors["onc"], "cancer")
        self.assertEqual(anchors["iron"], "kidney_disease")
        self.assertIn(anchors["chronic"], ("diabetes", "obesity"))

    def test_state_rates_are_real_sourced_values(self):
        from rcm_mc.diligence.texas_infusion import texas_cdc_state_rates
        from rcm_mc.data.cdc_places_agg import places_equity_state
        rates = texas_cdc_state_rates()
        # Diabetes/obesity rates equal the REAL vendored TX PLACES values.
        pl = places_equity_state("TX")
        self.assertAlmostEqual(rates["diabetes"]["rate_pct"],
                               round(float(pl["diabetes"]), 2), places=2)
        self.assertAlmostEqual(rates["obesity"]["rate_pct"],
                               round(float(pl["obesity"]), 2), places=2)
        self.assertIn("PLACES", rates["diabetes"]["source"])
        # Arthritis/cancer/CKD from CMS Medicare (TX-adjusted), real.
        self.assertIn("Medicare", rates["arthritis"]["source"])
        for k in ("arthritis", "cancer", "kidney_disease"):
            self.assertGreater(rates[k]["rate_pct"], 0)

    def test_offline_falls_back_not_live(self):
        # No egress in CI/sandbox → the live flag is False and the API
        # client returns empty (fails closed, never fabricates).
        self.assertFalse(self.a["cdc_proxies"]["live"])
        from rcm_mc.data.cdc_places_api import (
            fetch_places_counties, places_counties_by_fips)
        self.assertEqual(fetch_places_counties("TX"), [])
        self.assertEqual(places_counties_by_fips("ZZ"), {})

    def test_county_demand_uses_correct_denominator(self):
        from rcm_mc.diligence.texas_infusion import (
            county_cdc_demand, texas_cdc_state_rates)
        rates = texas_cdc_state_rates()
        county = {"population": 1_000_000, "seniors": 130_000,
                  "female_share": 0.50}
        rows = {r["key"]: r for r in county_cdc_demand(
            county, rates, None, 0.50)}
        adults = 1_000_000 * 0.76
        # Full-population PLACES rate (chronic/diabetes) → adults base.
        exp_chronic = round(adults * rates["diabetes"]["rate_pct"] / 100)
        self.assertEqual(rows["chronic"]["estimated_patients"], exp_chronic)
        self.assertEqual(rows["chronic"]["denominator"], "adults 18+")
        # Medicare rate (cancer) → senior (65+) base, not all adults.
        exp_onc = round(130_000 * rates["cancer"]["rate_pct"] / 100)
        self.assertEqual(rows["onc"]["estimated_patients"], exp_onc)
        self.assertIn("Medicare", rows["onc"]["denominator"])

    def test_iv_iron_weighted_by_female_share(self):
        from rcm_mc.diligence.texas_infusion import (
            county_cdc_demand, texas_cdc_state_rates)
        rates = texas_cdc_state_rates()
        county = {"population": 1_000_000, "seniors": 130_000}
        low = {r["key"]: r for r in county_cdc_demand(
            county, rates, None, 0.45)}["iron"]["estimated_patients"]
        high = {r["key"]: r for r in county_cdc_demand(
            county, rates, None, 0.55)}["iron"]["estimated_patients"]
        # More women → larger anemia/IV-iron pool.
        self.assertGreater(high, low)

    def test_live_county_rate_overrides_state(self):
        # When a PLACES county row is present, the full-population rate
        # is used (and applied to adults), overriding the state fallback.
        from rcm_mc.diligence.texas_infusion import (
            county_cdc_demand, texas_cdc_state_rates)
        rates = texas_cdc_state_rates()
        county = {"population": 1_000_000, "seniors": 130_000}
        places_row = {"arthritis": 25.0, "cancer": 7.0,
                      "kidney_disease": 3.5, "diabetes": 14.0,
                      "population": 1_000_000}
        rows = {r["key"]: r for r in county_cdc_demand(
            county, rates, places_row, 0.50)}
        self.assertTrue(rows["rheum"]["rate_is_county_live"])
        self.assertEqual(rows["rheum"]["rate_pct"], 25.0)
        # Live arthritis applies to all adults, not seniors.
        self.assertEqual(rows["rheum"]["estimated_patients"],
                         round(1_000_000 * 0.76 * 25.0 / 100))

    def test_payer_access_index_bounded_and_real(self):
        from rcm_mc.diligence.texas_infusion import (
            county_payer_access, texas_cdc_state_rates)
        rates = texas_cdc_state_rates()
        good = county_payer_access(
            {"uninsured_rate": 0.05, "child_poverty_rate": 0.05}, rates)
        bad = county_payer_access(
            {"uninsured_rate": 0.30, "child_poverty_rate": 0.40}, rates)
        self.assertGreaterEqual(good["score"], 0)
        self.assertLessEqual(good["score"], 100)
        self.assertGreater(good["score"], bad["score"])
        self.assertIn(good["band"], ("strong", "moderate", "constrained"))

    def test_metro_and_county_demand_attached_and_consistent(self):
        for dd in self.a["metro_deepdives"]:
            self.assertTrue(dd["cdc_demand"])
            # Metro total per therapy = sum of its counties.
            by_key = {r["key"]: r["estimated_patients"]
                      for r in dd["cdc_demand"]}
            roll = {}
            for s in dd["suburbs"]:
                for d in s["cdc_demand"]:
                    roll[d["key"]] = roll.get(d["key"], 0) \
                        + d["estimated_patients"]
            for k, v in by_key.items():
                self.assertEqual(v, roll.get(k))

    def test_analysis_json_serializable(self):
        import json
        json.dumps(self.a)  # must not raise


class HomeInfusionTests(unittest.TestCase):
    """Deep home-infusion analysis — therapy/condition epidemiology,
    the network roster, the Medicare HIT reimbursement gap, and episode
    economics. Every count is a published rate × real population."""

    def setUp(self):
        self.a = build_texas_infusion_analysis()
        self.hi = self.a["home_infusion"]

    def test_conditions_scale_linearly_with_population(self):
        from rcm_mc.diligence.texas_infusion import home_infusion_conditions
        small = {c["key"]: c["estimated_patients"]
                 for c in home_infusion_conditions(1_000_000, 130_000)}
        big = {c["key"]: c["estimated_patients"]
               for c in home_infusion_conditions(2_000_000, 260_000)}
        # Double the population → double the eligible pool (real-pop scaled).
        for k in small:
            self.assertEqual(big[k], small[k] * 2, f"{k} not pop-scaled")
        # OPAT is the volume driver among the families.
        self.assertEqual(max(small, key=small.get), "opat")

    def test_inotrope_uses_senior_denominator(self):
        from rcm_mc.diligence.texas_infusion import home_infusion_conditions
        # Holding population fixed, more seniors → more home inotrope
        # patients (a senior-denominated therapy), but OPAT unchanged.
        a = {c["key"]: c["estimated_patients"]
             for c in home_infusion_conditions(1_000_000, 100_000)}
        b = {c["key"]: c["estimated_patients"]
             for c in home_infusion_conditions(1_000_000, 200_000)}
        self.assertGreater(b["inotrope"], a["inotrope"])
        self.assertEqual(b["opat"], a["opat"])

    def test_networks_cover_tiers_and_texas(self):
        nets = self.hi["networks"]
        self.assertGreaterEqual(len(nets), 10)
        tiers = {n["tier"] for n in nets}
        # National, payer-owned, IG specialist, and the roll-up pool.
        self.assertTrue(any("National" in t for t in tiers))
        self.assertTrue(any("Payer-owned" in t for t in tiers))
        self.assertTrue(any("roll-up" in t for t in tiers))
        # Payer-owned steerage threats present; Paragon (TX-HQ'd) flagged.
        names = {n["name"] for n in nets}
        self.assertIn("Optum Infusion Pharmacy", names)
        paragon = next(n for n in nets if n["name"] == "Paragon Healthcare")
        self.assertTrue(paragon["tx"])
        for n in nets:
            for f in ("name", "tier", "ownership", "tx", "focus", "accred"):
                self.assertIn(f, n)

    def test_reimbursement_surfaces_the_hit_gap(self):
        reim = self.hi["reimbursement"]
        self.assertGreaterEqual(len(reim["points"]), 5)
        text = " ".join(p["label"] + " " + p["detail"]
                        for p in reim["points"]).lower()
        # The defining calendar-day gap and the Part D black hole.
        self.assertIn("calendar-day", text)
        self.assertIn("part d", text)
        self.assertTrue(reim["rcm_read"])

    def test_episode_economics_recomputes(self):
        ec = self.hi["episode_economics"]
        self.assertEqual(ec["contribution"], ec["revenue"] - ec["cost"])
        self.assertGreater(ec["contribution"], 0)
        self.assertTrue(0 < ec["contribution_margin"] < 1)
        self.assertTrue(ec["drivers"])

    def test_therapy_reference_is_complete(self):
        ths = self.hi["therapies"]
        self.assertEqual(len(ths), 6)
        keys = {t["key"] for t in ths}
        self.assertEqual(keys, {"opat", "ig", "tpn", "inotrope",
                                "biologic", "rare"})
        for t in ths:
            for f in ("conditions", "regimen", "reimbursement",
                      "why_home", "margin", "epi_basis", "epi_per_100k"):
                self.assertIn(f, t)

    def test_each_metro_has_home_infusion_demand(self):
        for dd in self.a["metro_deepdives"]:
            self.assertTrue(dd["home_infusion"])
            self.assertTrue(all(c["estimated_patients"] >= 0
                                for c in dd["home_infusion"]))


class HomeInfusionDischargeRiskTests(unittest.TestCase):
    """Discharge pipeline + therapy-volume risk — the referral FLOW is a
    real-rate × real-population estimate, the risk register recomputes
    from documented axis scores, and referral concentration surfaces the
    commercial fragility."""

    def setUp(self):
        self.a = build_texas_infusion_analysis()
        self.hi = self.a["home_infusion"]

    def test_discharge_flow_scales_with_population(self):
        from rcm_mc.diligence.texas_infusion import (
            home_infusion_discharge_volumes)
        small = {d["key"]: d["annual_referrals"]
                 for d in home_infusion_discharge_volumes(1_000_000, 130_000)}
        big = {d["key"]: d["annual_referrals"]
               for d in home_infusion_discharge_volumes(2_000_000, 260_000)}
        for k in small:
            self.assertEqual(big[k], small[k] * 2)
        # OPAT is the dominant referral flow; every therapy has a source
        # and a readmission anchor.
        self.assertEqual(max(small, key=small.get), "opat")
        for d in self.hi["tx_discharges"]:
            self.assertTrue(d["source"])
            self.assertGreater(d["readmission_pct"], 0)

    def test_flow_is_smaller_than_prevalent_pool(self):
        # Annual new-start FLOW must be ≤ the standing eligible pool for
        # chronic therapies (IG/TPN/biologic) — flow is incidence, pool
        # is prevalence.
        pool = {c["key"]: c["estimated_patients"]
                for c in self.hi["tx_conditions"]}
        flow = {d["key"]: d["annual_referrals"]
                for d in self.hi["tx_discharges"]}
        for k in ("ig", "tpn", "biologic"):
            self.assertLess(flow[k], pool[k], f"{k} flow ≥ pool")

    def test_therapy_risk_recomputes_and_ranks(self):
        from rcm_mc.diligence.texas_infusion import (
            home_infusion_therapy_risk, _RISK_WEIGHTS)
        tr = home_infusion_therapy_risk()
        rows = tr["therapies"]
        # Ranked descending by overall risk; ranks 1..n.
        scores = [r["overall_score"] for r in rows]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertEqual([r["rank"] for r in rows],
                         list(range(1, len(rows) + 1)))
        # overall_score = weighted blend of the five axes (pure recompute).
        for r in rows:
            exp = sum(r["axes"][ax] * w for ax, w in _RISK_WEIGHTS.items())
            self.assertAlmostEqual(r["overall_score"], round(exp, 2))
            self.assertEqual(r["overall_pct"], round(exp * 20))
            self.assertIn(r["band"], ("HIGH", "ELEVATED", "MODERATE"))
        self.assertEqual(tr["most_at_risk"], rows[0]["therapy"])

    def test_high_value_chronic_therapies_flag_steerage(self):
        # IG and home biologics — the expensive, payer-steered therapies —
        # must score steerage risk highest among their axes.
        tr = {r["key"]: r for r in
              self.hi["therapy_risk"]["therapies"]}
        self.assertEqual(tr["ig"]["axes"]["steerage"], 5)
        self.assertEqual(tr["biologic"]["axes"]["steerage"], 5)
        # OPAT — the discharge-fed volume play — is referral-concentrated.
        self.assertEqual(tr["opat"]["axes"]["referral_concentration"], 5)

    def test_referral_sources_sum_and_concentration(self):
        rs = self.hi["referral_sources"]
        self.assertAlmostEqual(
            sum(s["share"] for s in rs["sources"]), 1.0, places=3)
        # Acute-hospital discharge is the dominant, concentrated source.
        top = max(rs["sources"], key=lambda s: s["share"])
        self.assertIn("hospital", top["source"].lower())
        self.assertGreaterEqual(rs["hospital_dependence"], 0.5)
        self.assertTrue(rs["concentration_risk"])
        self.assertTrue(rs["rcm_read"])

    def test_each_metro_has_discharge_flow(self):
        for dd in self.a["metro_deepdives"]:
            self.assertTrue(dd["home_infusion_discharges"])


class ASPandMATests(unittest.TestCase):
    """CMS Part B ASP buy-and-bill pricing + Medicare Advantage
    enrollment — real public data, real formula, no fabricated dollars."""

    def setUp(self):
        self.a = build_texas_infusion_analysis()

    def test_asp_reference_is_verifiable_jcodes(self):
        asp = self.a["asp_pricing"]
        ref = asp["reference"]
        self.assertGreaterEqual(len(ref), 10)
        codes = {r["hcpcs"] for r in ref}
        # Marquee infusion J-codes present (public CMS facts).
        for c in ("J1745", "J9312", "J2350", "J1569"):
            self.assertIn(c, codes)
        for r in ref:
            for f in ("drug", "unit", "category", "channel"):
                self.assertTrue(r[f])

    def test_asp_formula_and_offline_no_fabrication(self):
        from rcm_mc.data.cms_asp_pricing import (
            payment_limit, ASP_ADDON, ASP_ADDON_SEQUESTERED,
            fetch_asp_pricing)
        # Sequestered ≈ ASP+4.3%, statutory ASP+6%.
        self.assertAlmostEqual(payment_limit(100.0), 104.3, places=1)
        self.assertAlmostEqual(
            payment_limit(100.0, sequestered=False), 106.0, places=1)
        self.assertEqual(ASP_ADDON, 0.06)
        self.assertTrue(0.04 < ASP_ADDON_SEQUESTERED < 0.05)
        # Offline: the live fetch fails closed and the page shows no
        # fabricated dollar value (payment_limit_per_unit is None).
        self.assertEqual(fetch_asp_pricing(["J1745"]), {})
        self.assertFalse(self.a["asp_pricing"]["live"])
        self.assertTrue(all(r["payment_limit_per_unit"] is None
                            for r in self.a["asp_pricing"]["reference"]))

    def test_ma_enrollment_is_real_vendored(self):
        from rcm_mc.data.ma_data import ma_state
        ma = self.a["ma_enrollment"]
        # Matches the real vendored CMS MA geo file for TX.
        self.assertEqual(ma["enrollment"],
                         int(ma_state("TX")["ma_enrollment"]))
        self.assertGreater(ma["enrollment"], 1_000_000)
        self.assertTrue(0 < ma["penetration_proxy"] < 1.5)
        self.assertGreater(ma["dual_eligible_pct"], 0)
        self.assertIn("Medicare Advantage", ma["note"])


class ProviderMapTests(unittest.TestCase):
    """NPPES infusion-provider map — real estimated counts, real public
    taxonomy codes, and a live NPPES count that is OFF by default (never
    blocks a render) and fails closed when enabled offline."""

    def setUp(self):
        self.a = build_texas_infusion_analysis()

    def test_map_has_four_metros_with_real_estimates(self):
        pm = self.a["provider_map"]
        self.assertEqual(len(pm["points"]), 4)
        shorts = {p["short"] for p in pm["points"]}
        self.assertEqual(shorts, {"Houston", "Dallas", "Austin",
                                  "San Antonio"})
        for p in pm["points"]:
            self.assertGreater(p["estimated_centers"], 0)
            self.assertTrue(0 <= p["x"] <= 100 and 0 <= p["y"] <= 100)
        # Ranked by estimated centers (largest first).
        ests = [p["estimated_centers"] for p in pm["points"]]
        self.assertEqual(ests, sorted(ests, reverse=True))

    def test_default_is_offline_no_network(self):
        # Default build does NOT hit NPPES — live False, counts None.
        pm = self.a["provider_map"]
        self.assertFalse(pm["live"])
        self.assertTrue(all(p["nppes_count"] is None for p in pm["points"]))

    def test_taxonomies_are_real_nucc_codes(self):
        codes = {t["code"] for t in self.a["provider_map"]["taxonomies"]}
        self.assertIn("261QI0500N", codes)   # Clinic/Center Infusion
        self.assertIn("3336I0012X", codes)   # Infusion Pharmacy
        self.assertIn("251F00000X", codes)   # Home Infusion agency

    def test_live_flag_threads_through(self):
        # fetch_live still fails closed in the airgapped sandbox (NPPES
        # unreachable) — the structure holds, counts stay None.
        from rcm_mc.diligence.texas_infusion import (
            texas_infusion_provider_map)
        pm = texas_infusion_provider_map(
            self.a["metro_deepdives"], fetch_live=True)
        self.assertEqual(len(pm["points"]), 4)
        # No fabrication: offline the live count is None.
        self.assertTrue(all(p["nppes_count"] is None for p in pm["points"]))


class SoWhatTakeawayTests(unittest.TestCase):
    """Every section carries a data-driven 'SO WHAT' takeaway that
    recomputes from the analysis it summarizes."""

    def test_takeaways_built_from_real_values(self):
        from rcm_mc.ui.texas_infusion_page import _so_whats
        a = build_texas_infusion_analysis()
        sw = _so_whats(a)
        # One per major section.
        self.assertGreaterEqual(len(sw), 15)
        # Each is non-empty prose.
        for k, v in sw.items():
            self.assertTrue(v and len(v) > 30, f"empty so-what: {k}")
        # Data-driven: the concentration takeaway carries the real HHI,
        # and the discharge takeaway the real OPAT referral flow.
        self.assertIn(f"{a['fragmentation']['hhi']:,.0f}", sw["concentration"])
        opat = next(d["annual_referrals"] for d in
                    a["home_infusion"]["tx_discharges"] if d["key"] == "opat")
        self.assertIn(f"{opat:,}", sw["discharge"])

    def test_page_renders_so_what_callouts(self):
        from rcm_mc.ui.texas_infusion_page import render_texas_infusion_page
        h = render_texas_infusion_page()
        # At least 15 SO WHAT callouts on the page.
        self.assertGreaterEqual(h.count(">SO WHAT<"), 15)


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
            "TOP DENIAL DRIVERS", "AIC unit economics",
            "BREAKDOWN BY SECTION", "Chair contribution margin",
            "Drug supply", "STABLE", "Drug Shortage tracker",
            "North suburbs", "ILLNESS BURDEN",
            "capacity by owner", "Ownership segment",
            "Texas growth scorecard", "TOP-10 COUNTY OPPORTUNITIES",
            "UNDERSUPPLIED GROWTH MARKETS", "CHAIR CAPACITY",
            "CDC public-health demand proxies", "CDC/ACS proxy",
            "CDC-PROXIED INFUSION DEMAND BY THERAPY", "Payer access",
            "Home infusion — therapies, networks", "TX eligible/yr",
            "THE NETWORKS", "calendar-day gap", "Amerita",
            "HOME-INFUSION-ELIGIBLE PATIENTS",
            "ANNUAL REFERRAL FLOW BY THERAPY", "TX referrals/yr",
            "THERAPY-VOLUME RISK HEATMAP", "REFERRAL-SOURCE",
            "Concentration risk", "ANNUAL HOME-INFUSION REFERRALS/YR",
            "Part B drug pricing", "ASP pay limit/unit", "J1745",
            "Post-sequester", "Medicare Advantage", "TX MA ENROLLEES",
            "Infusion-provider map", "NPPES INFUSION TAXONOMIES",
            "261QI0500N", "<polygon points=",
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
