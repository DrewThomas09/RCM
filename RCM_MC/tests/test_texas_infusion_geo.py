"""Texas infusion county-proximity model — the referral-convenience
geography (rcm_mc/diligence/texas_infusion_geo.py + the
/diligence/texas-infusion/counties workbench).

Guards the evidence chain: all 254 counties from the real ACS file, the
real geocoded facility supply, model properties that must hold for the
distance read to be trustworthy, and the page/CSV routes.
"""
from __future__ import annotations

import unittest


class UniverseTests(unittest.TestCase):
    def test_all_254_counties_with_real_population(self):
        from rcm_mc.diligence.texas_infusion_geo import tx_county_universe
        rows = tx_county_universe()
        self.assertEqual(len(rows), 254)
        # Census 2023-vintage TX population ≈ 30.0M — the vendored ACS
        # aggregate must reconcile to it (guards a broken join).
        pop = sum(r["population"] for r in rows)
        self.assertTrue(29_000_000 < pop < 32_000_000, pop)
        fips = {r["county_fips"] for r in rows}
        self.assertEqual(len(fips), 254)
        self.assertTrue(all(f.startswith("48") for f in fips))

    def test_access_points_are_geocoded_general_acute(self):
        from rcm_mc.diligence.texas_infusion_geo import tx_access_points
        pts = tx_access_points()
        self.assertGreater(len(pts), 250)
        for p in pts:
            self.assertIn(p["kind"], ("STAC", "CAH"))
            # Texas bounding box — a coordinate outside it means the
            # geocode join grabbed the wrong row.
            self.assertTrue(25.5 < p["lat"] < 36.6, p)
            self.assertTrue(-107.0 < p["lon"] < -93.4, p)

    def test_county_name_matching_bridges_legacy_spellings(self):
        # CMS coords say 'MC LENNAN'; ACS says 'McLennan County'. The
        # original join missed these and misclassified Waco as having
        # no hospital.
        from rcm_mc.diligence.texas_infusion_geo import tx_county_universe
        by_name = {r["county"]: r for r in tx_county_universe()}
        self.assertGreater(by_name["McLennan"]["access_points"], 0)
        self.assertGreater(by_name["El Paso"]["access_points"], 0)


class DistanceModelTests(unittest.TestCase):
    def test_every_county_classified_and_positive_distance(self):
        from rcm_mc.diligence.texas_infusion_geo import tx_county_universe
        for r in tx_county_universe():
            self.assertIn(r["access_tier"],
                          ("MULTI_SITE", "SINGLE_SITE", "NO_IN_COUNTY"))
            self.assertGreater(r["expected_distance_mi"], 0.0, r["county"])
            self.assertIn(r["distance_evidence"], ("REAL", "MODELED"))
            self.assertIn(r["land_evidence"], ("REAL", "DEFAULT"))

    def test_access_monotonicity(self):
        # The property the whole read rests on: patients in counties
        # with no in-county site travel farther (weighted) than
        # single-site counties, which travel farther than multi-site.
        from rcm_mc.diligence.texas_infusion_geo import proximity_summary
        t = proximity_summary()["tiers"]
        self.assertGreater(t["NO_IN_COUNTY"]["weighted_distance_mi"],
                           t["SINGLE_SITE"]["weighted_distance_mi"])
        self.assertGreater(t["SINGLE_SITE"]["weighted_distance_mi"],
                           t["MULTI_SITE"]["weighted_distance_mi"])

    def test_metro_spillover_shortens_no_access_counties(self):
        # Randall County (Amarillo's CBSA, hospitals across the Potter
        # line) must read materially closer than an isolated
        # no-hospital county of similar size.
        from rcm_mc.diligence.texas_infusion_geo import tx_county_universe
        by_name = {r["county"]: r for r in tx_county_universe()}
        randall, king = by_name["Randall"], by_name["King"]
        self.assertEqual(randall["access_tier"], "NO_IN_COUNTY")
        self.assertTrue(randall["metro_spillover"])
        self.assertFalse(king["metro_spillover"])
        self.assertLess(randall["expected_distance_mi"],
                        king["expected_distance_mi"])

    def test_rollups_reconcile_to_total(self):
        from rcm_mc.diligence.texas_infusion_geo import (
            proximity_by_group,
            proximity_summary,
        )
        s = proximity_summary()
        for key in ("metro_class", "access_tier", "cbsa_title"):
            groups = proximity_by_group(key)
            self.assertEqual(sum(g["counties"] for g in groups), 254, key)
            self.assertEqual(sum(g["infusion_patients"] for g in groups),
                             s["infusion_patients"], key)

    def test_whitespace_is_demand_times_distance(self):
        from rcm_mc.diligence.texas_infusion_geo import aic_whitespace
        ws = aic_whitespace(10)
        self.assertEqual(len(ws), 10)
        for w in ws:
            self.assertEqual(
                w["patient_miles"],
                round(w["infusion_patients"] * w["expected_distance_mi"]))
        miles = [w["patient_miles"] for w in ws]
        self.assertEqual(miles, sorted(miles, reverse=True))


class RouteTests(unittest.TestCase):
    def test_page_and_csv_render_live(self):
        import os
        import socket
        import tempfile
        import threading
        import time
        import urllib.request

        from rcm_mc.server import build_server
        sk = socket.socket()
        sk.bind(("127.0.0.1", 0))
        port = sk.getsockname()[1]
        sk.close()
        server, _ = build_server(
            port=port, db_path=os.path.join(tempfile.mkdtemp(), "p.db"))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        time.sleep(0.3)
        try:
            base = f"http://127.0.0.1:{port}"
            html = urllib.request.urlopen(
                base + "/diligence/texas-infusion/counties",
                timeout=30).read().decode()
            for marker in ("Demand-weighted distance", "AIC whitespace",
                           "County universe", "Methodology",
                           "counties.csv"):
                self.assertIn(marker, html)
            csv = urllib.request.urlopen(
                base + "/diligence/texas-infusion/counties.csv",
                timeout=30).read().decode()
            self.assertEqual(len(csv.strip().splitlines()), 255)
            self.assertTrue(csv.startswith("county_fips,county,"))
            # The main TX page links the workbench.
            main = urllib.request.urlopen(
                base + "/diligence/texas-infusion",
                timeout=60).read().decode()
            self.assertIn("/diligence/texas-infusion/counties", main)
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()


class MetroDeepdiveTests(unittest.TestCase):
    def test_four_metros_with_member_counties(self):
        from rcm_mc.diligence.texas_infusion_geo import (
            metro_county_deepdive,
        )
        metros = metro_county_deepdive()
        self.assertEqual(len(metros), 4)
        names = {m["metro"] for m in metros}
        self.assertEqual(names, {"Dallas-Fort Worth", "Houston",
                                 "San Antonio", "Austin"})
        for m in metros:
            self.assertGreaterEqual(m["member_counties"], 5, m["metro"])
            self.assertGreater(m["access_points"], 10, m["metro"])
            self.assertIsNotNone(m["facility_nn_mi"], m["metro"])
            # Member-county patients sum to the metro figure.
            self.assertEqual(
                sum(c["infusion_patients"] for c in m["counties"]),
                m["infusion_patients"], m["metro"])

    def test_rosters_carry_real_facility_names(self):
        from rcm_mc.diligence.texas_infusion_geo import (
            metro_county_deepdive,
        )
        dfw = next(m for m in metro_county_deepdive()
                   if m["metro"] == "Dallas-Fort Worth")
        dallas = next(c for c in dfw["counties"]
                      if c["county"] == "Dallas")
        self.assertGreaterEqual(len(dallas["facility_roster"]), 10)
        for f in dallas["facility_roster"]:
            self.assertTrue(f["name"])
            self.assertIn(f["kind"], ("STAC", "CAH"))

    def test_age_split_and_drive_time_consistent(self):
        from rcm_mc.diligence.texas_infusion_geo import (
            metro_county_deepdive,
        )
        for m in metro_county_deepdive():
            for c in m["counties"]:
                self.assertAlmostEqual(
                    c["patients_65_plus"] + c["patients_under_65"],
                    c["infusion_patients"], delta=1)
                # Drive proxy: 25-45 mph band → minutes within
                # [dist/45*60, dist/25*60].
                lo = c["expected_distance_mi"] / 45.0 * 60.0
                hi = c["expected_distance_mi"] / 25.0 * 60.0
                self.assertTrue(
                    lo - 0.11 <= c["drive_minutes"] <= hi + 0.11,
                    f'{m["metro"]}/{c["county"]}: {c["drive_minutes"]}')
                self.assertTrue(c["siting_verdict"])

    def test_state_context_reads_vendored_files(self):
        from rcm_mc.diligence.texas_infusion_geo import (
            metro_state_context,
        )
        ctx = metro_state_context()
        self.assertIn("ma", ctx)
        self.assertGreater(ctx["ma"]["ma_enrollment"], 1_000_000)
        self.assertIn("places", ctx)
        self.assertIn("hpsa", ctx)

    def test_metros_csv_route(self):
        import os
        import socket
        import tempfile
        import threading
        import time
        import urllib.request

        from rcm_mc.server import build_server
        sk = socket.socket()
        sk.bind(("127.0.0.1", 0))
        port = sk.getsockname()[1]
        sk.close()
        server, _ = build_server(
            port=port, db_path=os.path.join(tempfile.mkdtemp(), "p.db"))
        threading.Thread(target=server.serve_forever,
                         daemon=True).start()
        time.sleep(0.3)
        try:
            csv = urllib.request.urlopen(
                f"http://127.0.0.1:{port}"
                "/diligence/texas-infusion/metros.csv",
                timeout=30).read().decode()
            lines = csv.strip().splitlines()
            self.assertGreater(len(lines), 30)
            self.assertIn("siting_verdict", lines[0])
            self.assertIn("facility_names", lines[0])
        finally:
            server.shutdown()
            server.server_close()
