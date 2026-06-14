"""Texas infusion market — Continued (part 2): the granular layer.

The part-2 module's contract: every figure is either a verified
published constant (CMS PFS/OPPS/HIT/ASP/GPCI files, Montana Medicaid,
AMA/KFF/CMS payer data) or pure arithmetic on those constants + the
part-1 demand model — and the channel build must reconcile to the
part-1 TAM EXACTLY so the two tabs can never disagree.
"""
from __future__ import annotations

import unittest

from rcm_mc.diligence.texas_infusion_continued import (
    DRUG_DOSE_ECONOMICS,
    HIT_G_CODES,
    HOME_PERDIEM_CODES,
    PFS_ADMIN_CODES,
    build_texas_infusion_continued_analysis,
    channel_sizing,
    cross_site_visit_comparison,
    drug_mix_economics,
    healthquest_proximity,
    metro_payer_analysis,
    network_access_by_metro,
    overall_reimbursement_rate,
    patient_experience_analysis,
    state_reimbursement_index,
    texas_locality_rates,
    visit_stack_economics,
)


class ChannelSizingTests(unittest.TestCase):
    def setUp(self):
        self.a = build_texas_infusion_continued_analysis()

    def test_channel_build_reconciles_to_part1_tam_exactly(self):
        cs = self.a["channel_sizing"]
        self.assertEqual(cs["tam_check"], round(self.a["sizing"]["tam"]))

    def test_site_shares_sum_to_one(self):
        cs = self.a["channel_sizing"]
        self.assertAlmostEqual(
            sum(r["share"] for r in cs["rows"]), 1.0, places=3)

    def test_hopd_prices_above_aic_home_below(self):
        cs = channel_sizing(100_000)
        by = {r["site"]: r for r in cs["rows"]}
        hopd = next(v for k, v in by.items() if "HOPD" in k)
        home = by["Home infusion"]
        aic = next(v for k, v in by.items() if "AIS" in k)
        self.assertGreater(hopd["revenue_per_infusion"],
                           aic["revenue_per_infusion"])
        self.assertLess(home["revenue_per_infusion"],
                        aic["revenue_per_infusion"])


class PfsCodeTests(unittest.TestCase):
    def test_96413_cy2025_verified_amount(self):
        c = next(c for c in PFS_ADMIN_CODES if c["code"] == "96413")
        self.assertAlmostEqual(c["nonfac"], 119.36, places=2)
        self.assertAlmostEqual(c["nonfac_2026"], 133.27, places=2)

    def test_cy2026_raises_every_admin_code(self):
        # The 2026 CF increase + office-PE change raised all 13 codes.
        for c in PFS_ADMIN_CODES:
            self.assertGreater(c["nonfac_2026"], c["nonfac"], c["code"])

    def test_visit_stacks_recompute_from_code_table(self):
        by_code = {c["code"]: c["nonfac"] for c in PFS_ADMIN_CODES}
        for v in visit_stack_economics():
            self.assertAlmostEqual(
                v["admin_total"],
                round(sum(x["amount"] for x in v["lines"]), 2), places=2)
            for line in v["lines"]:
                self.assertAlmostEqual(
                    line["amount"], by_code[line["code"]], places=2)

    def test_biologic_visit_is_96413_plus_push(self):
        v = next(x for x in visit_stack_economics()
                 if x["visit"].startswith("Biologic infusion, 1 hr"))
        self.assertEqual(v["codes"], "96413 + 96375")
        self.assertAlmostEqual(v["admin_total"], 119.36 + 14.23, places=2)


class TexasLocalityTests(unittest.TestCase):
    def setUp(self):
        self.locs = texas_locality_rates()

    def test_eight_localities(self):
        self.assertEqual(len(self.locs), 8)

    def test_houston_gaf_highest_beaumont_lowest(self):
        self.assertEqual(self.locs[0]["city"], "Houston")
        self.assertEqual(self.locs[-1]["city"], "Beaumont")

    def test_houston_gpcis_match_cms_file(self):
        h = next(r for r in self.locs if r["city"] == "Houston")
        self.assertAlmostEqual(h["work"], 1.014, places=3)
        self.assertAlmostEqual(h["pe"], 1.003, places=3)
        # The famously high Houston malpractice GPCI is real.
        self.assertAlmostEqual(h["mp"], 1.409, places=3)

    def test_gaf_recomputes_from_gpcis_at_published_weights(self):
        from rcm_mc.data.cms_gpci import GPCI_COST_WEIGHTS
        for r in self.locs:
            expect = (r["work"] * GPCI_COST_WEIGHTS["work"]
                      + r["pe"] * GPCI_COST_WEIGHTS["pe"]
                      + r["mp"] * GPCI_COST_WEIGHTS["mp"])
            self.assertAlmostEqual(r["gaf"], expect, places=4)

    def test_locality_rate_is_national_times_gaf(self):
        nonfac = next(c["nonfac"] for c in PFS_ADMIN_CODES
                      if c["code"] == "96413")
        for r in self.locs:
            self.assertAlmostEqual(
                r["rates"]["96413"], round(nonfac * r["gaf"], 2),
                places=2)

    def test_san_antonio_pays_rest_of_texas(self):
        rot = next(r for r in self.locs if r["locality"] == "99")
        self.assertIn("San Antonio", rot["counties"])


class StateGafTests(unittest.TestCase):
    def setUp(self):
        self.sr = state_reimbursement_index()

    def test_fifty_states_plus_dc(self):
        self.assertEqual(len(self.sr["states"]), 51)

    def test_texas_present_with_eight_localities(self):
        tx = self.sr["texas"]
        self.assertTrue(tx["is_tx"])
        self.assertEqual(tx["localities"], 8)
        # TX averages just under national across its localities.
        self.assertGreater(tx["gaf"], 0.95)
        self.assertLess(tx["gaf"], 1.01)

    def test_rates_are_anchor_times_gaf_and_ranked(self):
        anchor = self.sr["anchor_nonfac"]
        gafs = [s["gaf"] for s in self.sr["states"]]
        self.assertEqual(gafs, sorted(gafs, reverse=True))
        for s in self.sr["states"][:5] + self.sr["states"][-5:]:
            self.assertAlmostEqual(
                s["rate"], round(anchor * s["gaf"], 2), places=2)

    def test_alaska_floor_makes_it_the_top(self):
        self.assertEqual(self.sr["states"][0]["state"], "AK")


class HomeChannelCodeTests(unittest.TestCase):
    def test_hit_first_visit_exceeds_subsequent(self):
        for g in HIT_G_CODES:
            self.assertGreater(g["first_visit"], g["subsequent"])

    def test_hit_cy2025_verified_amounts(self):
        by = {g["code"]: g for g in HIT_G_CODES}
        self.assertAlmostEqual(by["G0068"]["subsequent"], 186.16, places=2)
        self.assertAlmostEqual(by["G0070"]["first_visit"], 380.58, places=2)
        self.assertEqual(by["G0068"]["first_code"], "G0088")

    def test_perdiem_published_rates_or_flagged_none(self):
        by = {p["code"]: p for p in HOME_PERDIEM_CODES}
        # Montana Medicaid published values are carried verbatim.
        self.assertAlmostEqual(by["S9365"]["published_rate"], 302.47,
                               places=2)
        self.assertAlmostEqual(by["S9338"]["published_rate"], 99.66,
                               places=2)
        # No public antibiotic per-diem exists — honesty preserved.
        self.assertIsNone(by["S9500"]["published_rate"])

    def test_cross_site_premium(self):
        cs = cross_site_visit_comparison()
        sites = [r["site"] for r in cs["rows"]]
        self.assertEqual(len(sites), 3)
        hopd = next(r for r in cs["rows"] if "HOPD" in r["site"])
        aic = next(r for r in cs["rows"] if "office" in r["site"].lower())
        self.assertAlmostEqual(hopd["amount"], 331.69, places=2)
        self.assertAlmostEqual(
            cs["hopd_premium"], round(331.69 / 119.36, 2), places=2)
        self.assertEqual(aic["vs_aic"], 1.0)


class DrugMixTests(unittest.TestCase):
    def setUp(self):
        self.dm = drug_mix_economics()

    def test_dose_payment_recomputes_from_unit_price(self):
        for d in DRUG_DOSE_ECONOMICS:
            self.assertAlmostEqual(
                d["asp_dose"], d["asp_unit"] * d["units_dose"],
                delta=max(0.51, d["asp_dose"] * 0.001), msg=d["hcpcs"])

    def test_annual_revenue_is_dose_times_frequency(self):
        for d in self.dm["drugs"]:
            self.assertEqual(d["annual_drug_rev"],
                             round(d["asp_dose"] * d["doses_yr"]))

    def test_mix_shares_sum_to_one(self):
        self.assertAlmostEqual(
            sum(m["share"] for m in self.dm["mix"]), 1.0, places=3)

    def test_soliris_is_the_top_annual_revenue_line(self):
        self.assertEqual(self.dm["drugs"][0]["hcpcs"], "J1299")

    def test_eculizumab_uses_the_replacement_code(self):
        codes = {d["hcpcs"] for d in DRUG_DOSE_ECONOMICS}
        self.assertIn("J1299", codes)      # J1300 deactivated 3/31/2025
        self.assertNotIn("J1300", codes)

    def test_commercial_spread_exceeds_medicare(self):
        for d in self.dm["drugs"]:
            self.assertGreater(d["commercial_spread_dose"],
                               d["medicare_spread_dose"])


class OverallReimbursementTests(unittest.TestCase):
    def setUp(self):
        self.orr = overall_reimbursement_rate()

    def test_blend_reconciles_to_part1_anchor(self):
        self.assertEqual(self.orr["blended_revenue_per_infusion"],
                         self.orr["anchor"])

    def test_payer_shares_sum_to_one(self):
        self.assertAlmostEqual(
            sum(r["share"] for r in self.orr["rows"]), 1.0, places=3)

    def test_yield_ordering(self):
        by = {r["payer"]: r["revenue_per_infusion"]
              for r in self.orr["rows"]}
        self.assertGreater(by["Commercial / employer"],
                           by["Medicare FFS (Part B)"])
        self.assertGreater(by["Medicare FFS (Part B)"],
                           by["Medicare Advantage"])
        self.assertGreater(by["Medicare Advantage"],
                           by["Medicaid (TX STAR/managed)"])
        self.assertGreater(by["Medicaid (TX STAR/managed)"],
                           by["Self-pay / uninsured"])


class MetroPayerTests(unittest.TestCase):
    def setUp(self):
        self.mp = metro_payer_analysis()

    def test_four_metros_ranked(self):
        self.assertEqual(len(self.mp["metros"]), 4)
        self.assertEqual([m["rank"] for m in self.mp["metros"]],
                         [1, 2, 3, 4])

    def test_austin_is_friendliest_market(self):
        self.assertEqual(self.mp["metros"][0]["metro"], "Austin")

    def test_verified_county_ma_penetration(self):
        by = {m["metro"]: m for m in self.mp["metros"]}
        self.assertAlmostEqual(by["Houston"]["ma_penetration"], 0.613,
                               places=3)
        self.assertAlmostEqual(by["Austin"]["ma_penetration"], 0.475,
                               places=3)

    def test_austin_hcsc_share_is_the_published_floor(self):
        austin = next(m for m in self.mp["metros"]
                      if m["metro"] == "Austin")
        self.assertAlmostEqual(austin["hcsc_share"], 0.37, places=2)

    def test_hmo_exposure_tracks_ma_penetration(self):
        by = {m["metro"]: m for m in self.mp["metros"]}
        self.assertGreater(by["Houston"]["hmo_exposure"],
                           by["Austin"]["hmo_exposure"])
        for m in self.mp["metros"]:
            self.assertGreater(m["hmo_exposure"], 0.0)
            self.assertLess(m["hmo_exposure"], 1.0)


class NetworkMatrixTests(unittest.TestCase):
    def setUp(self):
        self.net = network_access_by_metro()

    def test_statuses_are_valid(self):
        valid = {"in", "owned", "rpt", "ltd", "out"}
        for op in self.net["matrix"]:
            for plan in self.net["plans"]:
                self.assertIn(op["status"][plan], valid,
                              f'{op["operator"]} / {plan}')

    def test_payer_owned_assets_flagged(self):
        by = {op["operator"]: op for op in self.net["matrix"]}
        self.assertEqual(
            by["Optum Infusion"]["status"]["UnitedHealthcare"], "owned")
        self.assertEqual(
            by["Coram (CVS Health)"]["status"]["Aetna/CVS"], "owned")

    def test_healthquest_medicaid_wedge(self):
        hq = next(op for op in self.net["matrix"]
                  if "HealthQuest" in op["operator"])
        # Community Health Choice preferred status = Medicaid MCO 'in'.
        self.assertEqual(hq["status"]["TX Medicaid (STAR MCOs)"], "in")
        self.assertIn("Community Health Choice", hq["note"])

    def test_options_counted_per_metro(self):
        rows = {r["metro"]: r["options"] for r in self.net["rows"]}
        self.assertEqual(set(rows), {"Houston", "Dallas", "Austin",
                                     "San Antonio"})
        # Houston has the deepest operator bench in part 1 + extras.
        for plan in self.net["plans"]:
            self.assertGreaterEqual(rows["Houston"][plan],
                                    rows["Austin"][plan], plan)


class ProximityTests(unittest.TestCase):
    def setUp(self):
        self.a = build_texas_infusion_continued_analysis()
        self.px = self.a["proximity"]

    def test_sixteen_counties_ranked_by_minutes(self):
        rows = self.px["counties"]
        self.assertEqual(len(rows), 16)
        mins = [r["avg_minutes"] for r in rows]
        self.assertEqual(mins, sorted(mins))

    def test_urban_cores_closer_than_growth_rings(self):
        by = {r["county"]: r["avg_minutes"] for r in self.px["counties"]}
        self.assertLess(by["Harris"], by["Montgomery"])
        self.assertLess(by["Dallas"], by["Collin"])
        self.assertLess(by["Bexar"], by["Comal"])

    def test_distance_formula_recomputes(self):
        import math
        r = self.px["counties"][0]
        center_density = r["est_centers"] / r["land_sqmi"]
        road = 0.5 / math.sqrt(center_density) * 1.30
        self.assertAlmostEqual(r["avg_miles_to_nearest"], road,
                               delta=0.06)

    def test_verified_census_land_area(self):
        harris = next(r for r in self.px["counties"]
                      if r["county"] == "Harris")
        self.assertAlmostEqual(harris["land_sqmi"], 1_706.96, places=2)


class HealthQuestTests(unittest.TestCase):
    def setUp(self):
        self.hq = healthquest_proximity()

    def test_two_open_chair_sites_only(self):
        open_sites = [s for s in self.hq["sites"]
                      if s["status"] == "open"]
        self.assertEqual(len(open_sites), 2)
        cities = {s["city"].split(" (")[0] for s in open_sites}
        self.assertEqual(cities, {"Houston", "Beaumont"})

    def test_woodlands_is_service_area_not_facility(self):
        tw = next(s for s in self.hq["sites"]
                  if s["city"].startswith("The Woodlands"))
        self.assertEqual(tw["status"], "service")

    def test_drive_times_sorted_and_bounded(self):
        rows = self.hq["centers"]
        mins = [r["drive_minutes"] for r in rows]
        self.assertEqual(mins, sorted(mins))
        self.assertGreater(self.hq["pct_within_30min"], 0.3)
        self.assertLess(self.hq["pct_within_30min"], 1.0)

    def test_within30_population_math(self):
        within = sum(r["pop"] for r in self.hq["centers"]
                     if r["within_30"])
        self.assertEqual(self.hq["pop_within_30min"], within)
        self.assertAlmostEqual(
            self.hq["pct_within_30min"],
            round(within / self.hq["pop_total"], 3), places=3)

    def test_profile_carries_the_verified_payer_facts(self):
        p = self.hq["profile"]
        self.assertIn("Community Health Choice", p["payers"])
        self.assertIn("2008", p["founded"])
        self.assertIn("ACHC", p["accreditation"])

    def test_competitor_sites_present(self):
        ops = {c["operator"] for c in self.hq["competitors"]}
        self.assertIn("IVX Health", ops)
        self.assertIn("KabaFusion", ops)


class ExperienceTests(unittest.TestCase):
    def setUp(self):
        self.ex = patient_experience_analysis()

    def test_driver_weights_sum_to_one(self):
        self.assertAlmostEqual(
            sum(d["weight"] for d in self.ex["drivers"]), 1.0, places=3)

    def test_scores_recompute_and_rank(self):
        for m in self.ex["models"]:
            expect = sum(m["scores"][d["driver"]] * d["weight"]
                         for d in self.ex["drivers"])
            self.assertAlmostEqual(m["weighted_score"], expect, places=2)
        ranks = [m["rank"] for m in self.ex["models"]]
        self.assertEqual(ranks, [1, 2, 3, 4])

    def test_hospital_bay_ranks_last(self):
        self.assertIn("Hospital", self.ex["models"][-1]["model"])

    def test_all_scores_one_to_five(self):
        for m in self.ex["models"]:
            for v in m["scores"].values():
                self.assertGreaterEqual(v, 1)
                self.assertLessEqual(v, 5)


class GpciDataModuleTests(unittest.TestCase):
    def test_vendored_file_parses_all_localities(self):
        from rcm_mc.data.cms_gpci import gpci_localities
        locs = gpci_localities()
        self.assertGreaterEqual(len(locs), 100)
        tx = [r for r in locs if r["state"] == "TX"]
        self.assertEqual(len(tx), 8)

    def test_state_rollup_excludes_territories(self):
        from rcm_mc.data.cms_gpci import state_gaf
        st = state_gaf()
        self.assertNotIn("PR", st)
        self.assertNotIn("VI", st)
        self.assertEqual(st["CA"]["localities"], 29)
        self.assertEqual(st["TX"]["localities"], 8)


class PageRenderTests(unittest.TestCase):
    def test_page_renders_all_sections(self):
        from rcm_mc.ui.texas_infusion_continued_page import (
            render_texas_infusion_continued_page,
        )
        h = render_texas_infusion_continued_page({})
        for probe in (
            "Texas Infusion Market · Continued",
            "Channel sizing — AIC and home, reconciled",
            "CPT per office / AIC visit",
            "CPT per home visit",
            "Reimbursement by state",
            "the eight Texas localities",
            "Drug mix — dose economics by J-code",
            "PPO / HMO concentration",
            "Who is in network, per plan",
            "Proximity &amp; population density",
            "HealthQuest — the referral-for-convenience operator",
            "Patient experience — the demand-side moat",
            "96413", "G0088", "S9365", "J1299",
            "Community Health Choice",
        ):
            self.assertIn(probe, h, probe)

    def test_tab_strip_links_both_pages(self):
        from rcm_mc.ui.texas_infusion_continued_page import (
            render_texas_infusion_continued_page,
        )
        h = render_texas_infusion_continued_page({})
        self.assertIn('href="/diligence/texas-infusion"', h)

    def test_part1_links_to_part2(self):
        from rcm_mc.ui.texas_infusion_page import (
            render_texas_infusion_page,
        )
        h = render_texas_infusion_page({})
        self.assertIn("/diligence/texas-infusion-continued", h)


if __name__ == "__main__":
    unittest.main()
