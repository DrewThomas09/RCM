"""Connector-estate coverage for the NPI cleaner — offline honesty end to end.

New-file tests (the 239-test contract in test_npi_cleaner.py is untouched)
covering the connectors front:

  * plan() consults real data availability before claiming a screen applies
    (LEIE "needs_data" vs "ready"), recommends reference packs from the
    previously-dead has_dx/has_hcpcs/has_taxonomy signals, and no longer
    advertises the ghost "rxnav" connector no resolver implements.
  * catalog() carries a PECOS entry so the panel matches what actually runs.
  * openFDA NDC lookups are normalized to the FDA native hyphenated forms
    (the digits-only exact match was dead for 11-digit claims NDCs) with a
    product_ndc fallback.
  * Coverage counters (rows_seen / rows_enriched / rows_covered) flow from
    resolve_drugs and nppes_bridge into the scorecard payloads.
  * connector_status()/health(): machine-readable LIVE-PACK / DEGRADED /
    UNAVAILABLE per source, with vintages — never fabricated.
  * refdata_packs installs offline (install_from_bytes / install_from_file /
    bootstrap_icd10cm_from_vendored) and reports pack staleness.
  * vendor_adapter propagates per-screen attrs disclosures and surfaces the
    offline SAD classification + gap inventory that only the networked deep
    pipeline used to reach.
  * bulk reference tables try candidate URLs newest-first; cms_rates never
    caches an empty (poisoned) lookup.
"""
import csv
import io
import json
import os
import tempfile
import time
import unittest
import urllib.parse
from pathlib import Path
from unittest.mock import patch

# Luhn-valid synthetic NPIs (same ones the main suite uses).
GOOD_A = "1679576722"
GOOD_B = "1234567893"


def _fresh_packs(testcase):
    """Patch refdata_packs onto a temp SQLite store for one test."""
    import rcm_mc.npi_cleaner.refdata_packs as packs
    tmp = tempfile.TemporaryDirectory()
    testcase.addCleanup(tmp.cleanup)
    p = patch.object(packs, "_DB_PATH", Path(tmp.name) / "packs.sqlite3")
    p.start()
    testcase.addCleanup(p.stop)
    packs._CACHE.clear()
    testcase.addCleanup(packs._CACHE.clear)
    return packs


def _no_leie_env(testcase):
    env = patch.dict(os.environ, {}, clear=False)
    env.start()
    os.environ.pop("RCM_MC_LEIE_CSV", None)
    testcase.addCleanup(env.stop)


LEIE_CSV = ("NPI,LASTNAME,FIRSTNAME\n"
            f"{GOOD_A},DOE,JANE\n"
            "0000000000,VOID,ROW\n").encode()


class TestPlanHonesty(unittest.TestCase):
    """plan() checks that data actually exists before claiming a screen
    applies, and recommends packs from the file-shape signals."""

    def setUp(self):
        self.packs = _fresh_packs(self)
        _no_leie_env(self)
        from rcm_mc.npi_cleaner import connectors
        self.C = connectors

    def test_leie_needs_data_when_nothing_installed(self):
        plan = self.C.plan({"has_billing": True, "has_npi": True})
        leie = next(p for p in plan if p["id"] == "oig_leie")
        self.assertTrue(leie["applies"])       # the screen DOES apply…
        self.assertEqual(leie["state"], "needs_data")  # …but has no data
        self.assertIn("not installed", leie["reason"].lower())
        self.assertIn("RCM_MC_LEIE_CSV", leie["reason"])

    def test_leie_ready_with_env_csv(self):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as fh:
            fh.write(LEIE_CSV)
            path = fh.name
        self.addCleanup(os.unlink, path)
        os.environ["RCM_MC_LEIE_CSV"] = path
        plan = self.C.plan({"has_billing": True})
        leie = next(p for p in plan if p["id"] == "oig_leie")
        self.assertEqual(leie["state"], "ready")
        self.assertIn("RCM_MC_LEIE_CSV", leie["reason"])

    def test_leie_ready_with_installed_pack_and_stale_note(self):
        self.packs.install_from_bytes("leie", LEIE_CSV, source="UPDATED.csv")
        plan = self.C.plan({"has_billing": True})
        leie = next(p for p in plan if p["id"] == "oig_leie")
        self.assertEqual(leie["state"], "ready")
        self.assertIn("pack", leie["reason"].lower())
        self.assertNotIn("days old", leie["reason"])
        # Backdate the pack past its 35-day cadence → the reason says so.
        with self.packs._LOCK, self.packs._conn() as con:
            con.execute("UPDATE pack_meta SET fetched=? WHERE pack='leie'",
                        (time.time() - 60 * 86400,))
        plan = self.C.plan({"has_billing": True})
        leie = next(p for p in plan if p["id"] == "oig_leie")
        self.assertEqual(leie["state"], "ready")
        self.assertIn("days old", leie["reason"])

    def test_no_ghost_connector_ids(self):
        plan = self.C.plan({"has_npi": True, "has_billing": True,
                            "has_ndc": True, "has_drug_name": True,
                            "jcode_pct": 50.0, "has_hcpcs": True,
                            "has_dx": True, "has_taxonomy": True})
        ids = {p["id"] for p in plan}
        self.assertNotIn("rxnav", ids)
        # Every network-mode plan id must be one a resolver can emit.
        net = {p["id"] for p in plan if p["mode"] == "network"}
        self.assertTrue(net <= {"nppes", "rxnorm", "openfda"}, net)
        # And rxnav is no longer claimed as cleaning-wired anywhere.
        self.assertNotIn("rxnav", self.C._CLEANING_WIRED)

    def test_pack_rows_follow_signals(self):
        # dx present, pack absent → applicable but needs_data.
        plan = self.C.plan({"has_dx": True})
        icd = next(p for p in plan if p["id"] == "pack_icd10cm")
        self.assertTrue(icd["applies"])
        self.assertEqual(icd["state"], "needs_data")
        self.assertIn("not installed", icd["reason"].lower())
        # no dx → honestly not applicable.
        plan = self.C.plan({})
        icd = next(p for p in plan if p["id"] == "pack_icd10cm")
        self.assertFalse(icd["applies"])
        # hcpcs and taxonomy rows exist and follow their signals.
        plan = self.C.plan({"has_hcpcs": True, "has_taxonomy": True})
        by_id = {p["id"]: p for p in plan}
        self.assertTrue(by_id["pack_hcpcs"]["applies"])
        self.assertTrue(by_id["pack_taxonomy"]["applies"])

    def test_pack_row_ready_after_offline_bootstrap(self):
        self.packs.bootstrap_icd10cm_from_vendored()
        plan = self.C.plan({"has_dx": True})
        icd = next(p for p in plan if p["id"] == "pack_icd10cm")
        self.assertEqual(icd["state"], "ready")
        self.assertIn("Installed", icd["reason"])
        self.assertRegex(icd["reason"], r"[\d,]{5,} rows")

    def test_plan_rows_keep_backward_compatible_keys(self):
        for p in self.C.plan({"has_npi": True, "has_billing": True}):
            for key in ("id", "name", "applies", "mode", "reason", "state"):
                self.assertIn(key, p)


class TestCatalogPecos(unittest.TestCase):
    def test_catalog_contains_pecos_marked_cleaning_wired(self):
        from rcm_mc.npi_cleaner import connectors as C
        cat = C.catalog()
        if not cat:
            self.skipTest("public_api_catalog unavailable")
        pecos = [c for c in cat if c["id"] == "pecos"]
        self.assertEqual(len(pecos), 1)
        self.assertTrue(pecos[0]["cleaning_wired"])
        self.assertEqual(pecos[0]["operator"], "CMS")

    def test_cleaning_wired_ids_match_what_actually_runs(self):
        from rcm_mc.npi_cleaner import connectors as C
        cat = C.catalog()
        if not cat:
            self.skipTest("public_api_catalog unavailable")
        wired = {c["id"] for c in cat if c["cleaning_wired"]}
        self.assertEqual(wired,
                         {"nppes", "rxnorm", "openfda", "oig_leie", "pecos"})


class _FdaOpenerMixin:
    """Fake transport for resolve_drugs: records every openFDA search."""

    def _make_opener(self, package_hits=True, product_hits=False):
        searches = []

        def opener(url, headers, timeout_s):
            if "api.fda.gov" in url:
                q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
                search = q.get("search", [""])[0]
                searches.append(search)
                hit = ((package_hits and search.startswith("package_ndc"))
                       or (product_hits and search.startswith("product_ndc")))
                results = ([{"brand_name": "GLUCOPHAGE",
                             "generic_name": "METFORMIN",
                             "labeler_name": "BMS"}] if hit else [])
                return json.dumps({"results": results}).encode()
            return b"{}"  # RxNav lookups resolve to nothing, no error
        return opener, searches


class TestOpenFdaNdcQuery(unittest.TestCase, _FdaOpenerMixin):
    """The 11-digit claims NDC must be queried in FDA native hyphenated
    form — the digits-only exact match matched nothing on real files."""

    def setUp(self):
        from rcm_mc.npi_cleaner import connectors as C
        if not C.available():
            self.skipTest("public_api_clients unavailable")
        self.C = C

    def test_eleven_digit_ndc_queries_native_hyphenated_forms(self):
        opener, searches = self._make_opener()
        res = self.C.resolve_drugs(["00002322730"], [], opener=opener)
        ofda = next(r for r in res if r["id"] == "openfda")
        self.assertEqual(ofda["resolved"], 1)
        fda_search = next(s for s in searches
                          if s.startswith("package_ndc"))
        # 5-4-2 "00002-3227-30" pads the labeler, so the native FDA form
        # is 4-4-2 — both candidates must be in one OR group.
        self.assertIn('"0002-3227-30"', fda_search)
        self.assertIn('"00002-3227-30"', fda_search)

    def test_ten_digit_ndc_zfills_then_normalizes(self):
        opener, searches = self._make_opener()
        self.C.resolve_drugs(["0002322730"], [], opener=opener)
        fda_search = next(s for s in searches
                          if s.startswith("package_ndc"))
        self.assertIn('"0002-3227-30"', fda_search)

    def test_hyphenated_input_passes_through(self):
        opener, searches = self._make_opener()
        self.C.resolve_drugs(["0002-3227-30"], [], opener=opener)
        fda_search = next(s for s in searches
                          if s.startswith("package_ndc"))
        self.assertEqual(fda_search, 'package_ndc:"0002-3227-30"')

    def test_falls_back_to_product_ndc_when_no_package_match(self):
        opener, searches = self._make_opener(package_hits=False,
                                             product_hits=True)
        res = self.C.resolve_drugs(["00002322730"], [], opener=opener)
        ofda = next(r for r in res if r["id"] == "openfda")
        self.assertEqual(ofda["resolved"], 1)
        prod = next(s for s in searches if s.startswith("product_ndc"))
        self.assertIn('"0002-3227"', prod)

    def test_non_ndc_shaped_value_is_unresolved_without_a_call(self):
        opener, searches = self._make_opener()
        res = self.C.resolve_drugs(["not-an-ndc"], [], opener=opener)
        ofda = next(r for r in res if r["id"] == "openfda")
        self.assertEqual(ofda["resolved"], 0)
        self.assertEqual(ofda["unresolved"], 1)
        self.assertFalse([s for s in searches if "ndc" in s])


class TestCoverageCounters(unittest.TestCase, _FdaOpenerMixin):
    """rows_seen / rows_enriched / rows_covered — how much of THIS file
    each connector actually earned, for the scorecard."""

    def test_resolve_drugs_row_coverage(self):
        from rcm_mc.npi_cleaner import connectors as C
        if not C.available():
            self.skipTest("public_api_clients unavailable")

        def opener(url, headers, timeout_s):
            if "rxcui.json" in url:
                return json.dumps(
                    {"idGroup": {"rxnormId": ["860975"]}}).encode()
            if "/properties.json" in url:
                return json.dumps({"properties": {"name": "metformin",
                                                  "tty": "IN"}}).encode()
            if "/ndcs.json" in url:
                return json.dumps({"ndcGroup": {"ndcList": {}}}).encode()
            if "api.fda.gov" in url:
                return json.dumps({"results": [{"brand_name": "G"}]}).encode()
            return b"{}"

        # 3 non-empty NDC cells (2 distinct) + 1 name cell; all resolve.
        res = C.resolve_drugs(
            ["0093-1049-01", "0093-1049-01", "", "0002-3227-30"],
            ["metformin"], opener=opener)
        rx = next(r for r in res if r["id"] == "rxnorm")
        self.assertEqual(rx["rows_seen"], 4)       # 3 NDC + 1 name cells
        self.assertEqual(rx["rows_enriched"], 4)
        ofda = next(r for r in res if r["id"] == "openfda")
        self.assertEqual(ofda["rows_seen"], 3)
        self.assertEqual(ofda["rows_enriched"], 3)

    def test_verify_npis_row_coverage(self):
        from rcm_mc.npi_cleaner import nppes_bridge as NB
        if not NB.available():
            self.skipTest("nppes client unavailable")
        with patch("rcm_mc.data_public.nppes_api_client.fetch_by_npi",
                   lambda npi, **kw: None):
            out = NB.verify_npis([GOOD_A, GOOD_A, GOOD_B, "12345"])
        self.assertEqual(out["rows_seen"], 3)       # the malformed one is out
        self.assertEqual(out["rows_covered"], 3)    # both distinct checked
        self.assertEqual(out["checked"], 2)

    def test_verify_npis_cap_limits_row_coverage_honestly(self):
        from rcm_mc.npi_cleaner import nppes_bridge as NB
        if not NB.available():
            self.skipTest("nppes client unavailable")
        with patch("rcm_mc.data_public.nppes_api_client.fetch_by_npi",
                   lambda npi, **kw: None):
            out = NB.verify_npis([GOOD_A, GOOD_B, GOOD_B], cap=1)
        self.assertTrue(out["capped"])
        self.assertEqual(out["rows_seen"], 3)
        self.assertEqual(out["rows_covered"], 1)    # only GOOD_A checked


class TestVerifyRankedByDollars(unittest.TestCase):
    """The verify cap spends its lookups on the top-dollar NPIs when
    weights are supplied, not on whichever appeared first."""

    def _fetch_recorder(self, seen):
        def fetch(npi, **kw):
            seen.append(npi)
            return None
        return fetch

    def test_high_dollar_npi_wins_the_cap(self):
        from rcm_mc.npi_cleaner import nppes_bridge as NB
        if not NB.available():
            self.skipTest("nppes client unavailable")
        looked = []
        with patch("rcm_mc.data_public.nppes_api_client.fetch_by_npi",
                   self._fetch_recorder(looked)):
            out = NB.verify_npis([GOOD_A, GOOD_B], cap=1,
                                 weights={GOOD_A: 10.0, GOOD_B: 5000.0})
        self.assertEqual(looked, [GOOD_B])
        self.assertTrue(out["ranked_by_dollars"])
        self.assertIn("top 1 distinct NPIs by dollars", out["note"])

    def test_no_weights_keeps_first_seen_order(self):
        from rcm_mc.npi_cleaner import nppes_bridge as NB
        if not NB.available():
            self.skipTest("nppes client unavailable")
        looked = []
        with patch("rcm_mc.data_public.nppes_api_client.fetch_by_npi",
                   self._fetch_recorder(looked)):
            out = NB.verify_npis([GOOD_A, GOOD_B], cap=1)
        self.assertEqual(looked, [GOOD_A])
        self.assertFalse(out["ranked_by_dollars"])
        self.assertIn("first 1", out["note"])

    def test_garbage_weights_never_raise(self):
        from rcm_mc.npi_cleaner import nppes_bridge as NB
        if not NB.available():
            self.skipTest("nppes client unavailable")
        with patch("rcm_mc.data_public.nppes_api_client.fetch_by_npi",
                   lambda npi, **kw: None):
            out = NB.verify_npis([GOOD_A],
                                 weights={"junk": "NaN?", GOOD_A: None})
        self.assertEqual(out["checked"], 1)


class TestConnectorStatusHealth(unittest.TestCase):
    """connector_status()/health(): machine-readable, offline, honest."""

    def setUp(self):
        self.packs = _fresh_packs(self)
        _no_leie_env(self)
        from rcm_mc.npi_cleaner import connectors
        self.C = connectors

    def test_statuses_are_honest_on_a_bare_deployment(self):
        by_id = {s["id"]: s for s in self.C.connector_status()}
        # Uninstalled packs: UNAVAILABLE, with the install route named.
        for pid in ("pack_leie", "pack_icd10cm", "pack_hcpcs",
                    "pack_taxonomy"):
            self.assertEqual(by_id[pid]["status"], self.C.STATUS_UNAVAILABLE)
            self.assertIn("Not installed", by_id[pid]["note"])
        # Sample-sized vendored seeds: DEGRADED, and they say why.
        for sid, frag in (("vendored_ncci_ptp", "sample"),
                          ("vendored_nppes_deactivated", "sample"),
                          ("vendored_sad_snapshot", "slice")):
            self.assertEqual(by_id[sid]["status"], self.C.STATUS_DEGRADED)
            self.assertIn(frag, by_id[sid]["note"].lower())
        # Full vendored tables: LIVE-PACK with rows and a vintage.
        for sid in ("vendored_ncci_mue", "vendored_icd10cm_validity",
                    "vendored_jw_jz_policy"):
            self.assertEqual(by_id[sid]["status"], self.C.STATUS_LIVE)
            self.assertGreater(by_id[sid]["rows"], 0)
            self.assertTrue(by_id[sid]["vintage"])
        # Live connectors offline: UNAVAILABLE, never fabricated.
        for cid in ("nppes", "rxnorm", "openfda", "pecos"):
            self.assertEqual(by_id[cid]["status"], self.C.STATUS_UNAVAILABLE)
            self.assertIn("opt-in", by_id[cid]["note"].lower())

    def test_installed_pack_reports_live_then_degraded_when_stale(self):
        self.packs.install_from_bytes("leie", LEIE_CSV, source="UPDATED.csv")
        by_id = {s["id"]: s for s in self.C.connector_status()}
        self.assertEqual(by_id["pack_leie"]["status"], self.C.STATUS_LIVE)
        self.assertTrue(by_id["pack_leie"]["vintage"])  # vintage date set
        with self.packs._LOCK, self.packs._conn() as con:
            con.execute("UPDATE pack_meta SET fetched=? WHERE pack='leie'",
                        (time.time() - 60 * 86400,))
        by_id = {s["id"]: s for s in self.C.connector_status()}
        self.assertEqual(by_id["pack_leie"]["status"],
                         self.C.STATUS_DEGRADED)
        self.assertIn("days old", by_id["pack_leie"]["note"])

    def test_health_rollup_counts_match(self):
        h = self.C.health()
        self.assertIn("generated", h)
        self.assertEqual(sum(h["counts"].values()), len(h["sources"]))
        for s in h["sources"]:
            self.assertIn(s["status"], (self.C.STATUS_LIVE,
                                        self.C.STATUS_DEGRADED,
                                        self.C.STATUS_UNAVAILABLE))


class TestRefdataOfflineInstall(unittest.TestCase):
    """No-egress installs: from bytes, from file, and the vendored
    ICD-10-CM bootstrap — then the pack-gated checks actually fire."""

    def setUp(self):
        self.packs = _fresh_packs(self)
        _no_leie_env(self)

    def test_install_from_bytes_lights_the_leie_screen(self):
        info = self.packs.install_from_bytes("leie", LEIE_CSV,
                                             source="UPDATED.csv")
        self.assertEqual(info["rows"], 1)   # the all-zero NPI is dropped
        self.assertTrue(info["source"].startswith("file:"))
        self.assertEqual(self.packs.leie_npis(), frozenset({GOOD_A}))
        # The real compliance screen reads the pack with no env var set.
        from rcm_mc.npi_cleaner import compliance
        out = compliance.screen_leie([GOOD_A, GOOD_B])
        self.assertTrue(out["available"])
        self.assertEqual(out["excluded"], 1)
        self.assertEqual(out["matches"], [{"npi": GOOD_A}])

    def test_install_from_file(self):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as fh:
            fh.write(LEIE_CSV)
            path = fh.name
        self.addCleanup(os.unlink, path)
        info = self.packs.install_from_file("leie", path)
        self.assertEqual(info["rows"], 1)
        st = {d["id"]: d for d in self.packs.status()}
        self.assertTrue(st["leie"]["installed"])

    def test_install_rejects_garbage(self):
        with self.assertRaises(ValueError):
            self.packs.install_from_bytes("leie", b"not,a,leie\n1,2,3\n")
        with self.assertRaises(ValueError):
            self.packs.install_from_bytes("nope", LEIE_CSV)
        with self.assertRaises(ValueError):
            self.packs.install_from_file("leie", "/no/such/file.csv")

    def test_bootstrap_icd10cm_from_vendored_fires_unknown_code_flag(self):
        info = self.packs.bootstrap_icd10cm_from_vendored()
        self.assertGreater(info["rows"], 60_000)
        self.assertIn("vendored", info["source"])
        codes = self.packs.icd10_codes()
        self.assertIn("A000", codes)
        # A shaped-but-nonexistent diagnosis now flags in the stdlib grade.
        fake = next(c for c in ("E119999", "A0099Z", "Z999X9")
                    if c not in codes)
        real = "E1165" if "E1165" in codes else "A000"
        from rcm_mc.npi_cleaner import engine
        data = (f"BillingNPI,Diagnosis\n{GOOD_A},{real}\n"
                f"{GOOD_B},{fake}\n").encode()
        res = engine.clean_bytes(data, "dx.csv")
        self.assertEqual(res.sanity.get("icd10-unknown-code"), 1)

    def test_status_reports_age_and_cadence(self):
        self.packs.install_from_bytes("leie", LEIE_CSV)
        self.packs.bootstrap_icd10cm_from_vendored()
        with self.packs._LOCK, self.packs._conn() as con:
            con.execute("UPDATE pack_meta SET fetched=?",
                        (time.time() - 40 * 86400,))
        st = {d["id"]: d for d in self.packs.status()}
        self.assertTrue(st["leie"]["stale"])            # 40d > 35d cadence
        self.assertAlmostEqual(st["leie"]["age_days"], 40.0, delta=0.2)
        self.assertFalse(st["icd10cm"]["stale"])        # 40d < 400d cadence
        self.assertEqual(st["leie"]["cadence_days"], 35)
        self.assertTrue(st["leie"]["fetched_iso"])


class TestVendorAdapterDisclosures(unittest.TestCase):
    """vendor_adapter propagates seed disclosures and surfaces the
    offline SAD + gap-inventory views."""

    @classmethod
    def setUpClass(cls):
        from rcm_mc.npi_cleaner import vendor_adapter
        if not vendor_adapter.available():
            raise unittest.SkipTest("pandas / v49 modules unavailable")
        cls.VA = vendor_adapter
        rows = ["ClaimID,BillingProviderNPI,ProviderState,HCPCS,"
                "AllowedAmt,Units,DateOfService,Diagnosis"]
        for i in range(40):
            npi = GOOD_A if i % 4 else ""
            code = ("C9399", "J1745", "99213", "J3357")[i % 4]
            st = ("TX", "NY", "", "CA")[i % 4]
            rows.append(f"{1000 + i},{npi},{st},{code},"
                        f"{100 + i}.50,2,2026-03-0{i % 9 + 1},E1165")
        cls.payload = cls.VA.run(("\n".join(rows) + "\n").encode())
        assert cls.payload is not None

    def test_screens_stay_ints_for_back_compat(self):
        for v in self.payload["screens"].values():
            self.assertIsInstance(v, int)

    def test_screen_details_carry_sample_disclosure(self):
        det = self.payload.get("screen_details") or {}
        self.assertTrue(det)
        deact = det.get("npi_deactivated")
        self.assertIsNotNone(deact)
        self.assertIn("sample", deact["note"].lower())
        self.assertIn("CMS NPPES", deact["source"])
        for d in det.values():
            self.assertEqual(set(d) >= {"n", "note", "source"}, True)
            self.assertEqual(d["n"],
                             self.payload["screens"][
                                 next(k for k, v in det.items() if v is d)])

    def test_sad_classification_surfaces_offline(self):
        sad = self.payload.get("sad")
        self.assertIsNotNone(sad, "SAD view missing from payload")
        verdicts = {r["verdict"] for r in sad["rollup"]}
        self.assertIn("SAD_EXCLUDED", verdicts)
        for r in sad["rollup"]:
            self.assertEqual(round(float(r["dollars"]), 2),
                             float(r["dollars"]))
        # The 15-code snapshot must disclose it is a slice, not the list.
        self.assertIn("slice", sad["note"].lower())
        self.assertGreater(sad["snapshot_codes"], 0)
        self.assertLess(sad["snapshot_codes"], 1000)

    def test_gap_inventory_surfaces_offline(self):
        gaps = self.payload.get("gaps")
        self.assertIsNotNone(gaps, "gap inventory missing from payload")
        names = {g["gap"] for g in gaps["inventory"]}
        self.assertIn("billing NPI blank", names)
        self.assertIn("state blank", names)
        self.assertGreater(float(gaps["total_gap_dollars"]), 0.0)
        self.assertTrue(gaps.get("plan"))

    def test_reference_status_snapshot_included(self):
        ref = self.payload.get("reference_status")
        self.assertTrue(ref and len(ref) >= 10)
        for s in ref:
            self.assertIn(s["status"],
                          ("LIVE-PACK", "DEGRADED", "UNAVAILABLE"))

    def test_note_only_screens_surface_as_screen_notes(self):
        # No NPI column at all → the deactivated screen cannot run and
        # says so, instead of silently vanishing.
        rows = ["HCPCS,AllowedAmt,DateOfService"]
        rows += [f"J1745,{100 + i}.00,2026-03-01" for i in range(10)]
        payload = self.VA.run(("\n".join(rows) + "\n").encode())
        self.assertIsNotNone(payload)
        notes = payload.get("screen_notes") or {}
        self.assertTrue(any("NPI" in v for v in notes.values()), notes)


class TestBulkCandidateUrls(unittest.TestCase):
    """Bulk tables try candidate URLs newest-first instead of a pinned
    dated filename that rots."""

    class _Resp:
        def __init__(self, content):
            self.content = content

        def raise_for_status(self):
            return None

    class _Sess:
        def __init__(self, by_url):
            self.by_url = by_url
            self.calls = []

        def get(self, url, timeout=0):
            self.calls.append(url)
            if url not in self.by_url:
                raise OSError(f"404: {url}")
            return TestBulkCandidateUrls._Resp(self.by_url[url])

    def test_second_candidate_wins_and_meta_records_it(self):
        from rcm_mc.npi_cleaner.vendor_v49.npi_recovery import bulk
        csv_bytes = (b"Code,Grouping,Classification,Specialization\n"
                     b"207X00000X,Allopathic,Orthopaedic Surgery,\n")
        with tempfile.TemporaryDirectory() as tmp:
            table = bulk.BulkTable(
                name="t", url=["https://x/one.csv", "https://x/two.csv"],
                key_col="taxonomy_code", loader=bulk.load_nucc_taxonomy,
                cache_dir=tmp)
            sess = self._Sess({"https://x/two.csv": csv_bytes})
            df = table.ensure(session=sess)
            self.assertIsNotNone(df)
            self.assertEqual(sess.calls,
                             ["https://x/one.csv", "https://x/two.csv"])
            meta = json.loads(table._meta.read_text())
            self.assertEqual(meta["url"], "https://x/two.csv")

    def test_all_candidates_fail_returns_none_not_raise(self):
        from rcm_mc.npi_cleaner.vendor_v49.npi_recovery import bulk
        with tempfile.TemporaryDirectory() as tmp:
            table = bulk.BulkTable(
                name="t", url=["https://x/a", "https://x/b"],
                key_col="taxonomy_code", loader=bulk.load_nucc_taxonomy,
                cache_dir=tmp)
            self.assertIsNone(table.ensure(session=self._Sess({})))

    def test_registry_generates_rolling_candidates(self):
        from rcm_mc.npi_cleaner.vendor_v49.npi_recovery import bulk
        de = bulk.deactivated_npi_urls()
        self.assertGreaterEqual(len(de), 9)
        self.assertTrue(all("NPPES_Deactivated_NPI_Report_" in u
                            for u in de))
        self.assertEqual(de[-1].rsplit("_", 1)[-1], "060925.zip")  # fallback
        nucc = bulk.nucc_taxonomy_urls()
        self.assertGreaterEqual(len(nucc), 4)
        # Newest-first: the current NUCC major version leads.
        import datetime
        major = datetime.datetime.now(datetime.timezone.utc).year - 2000
        self.assertIn(f"nucc_taxonomy_{major}1.csv", nucc[0])
        # The registry now wires the generators, not pinned names.
        self.assertTrue(callable(bulk.REGISTRY["nucc_taxonomy"]["url"]))
        self.assertTrue(callable(bulk.REGISTRY["deactivated_npi"]["url"]))


class TestCmsRatesHonesty(unittest.TestCase):
    """OPPS/ASP rate clients degrade honestly and never cache an empty
    lookup (which poisoned every later run)."""

    class _Cache:
        def __init__(self, preload=None):
            self.store = dict(preload or {})
            self.sets = []

        def get(self, ns, key):
            return self.store.get((ns, key))

        def set(self, ns, key, value):
            self.sets.append((ns, key, value))
            self.store[(ns, key)] = value

    def setUp(self):
        try:
            from rcm_mc.npi_cleaner.vendor_v49.npi_recovery import cms_rates
        except Exception as exc:  # pragma: no cover - requests missing
            self.skipTest(f"cms_rates unavailable: {exc}")
        self.cms_rates = cms_rates

    def test_opps_stub_never_caches_empty(self):
        cache = self._Cache()
        c = self.cms_rates.OPPSClient(cache)
        with patch.object(self.cms_rates.OPPSClient, "_current_zip_url",
                          lambda self: None):
            self.assertIsNone(c.rate("J1745"))
            self.assertEqual(c.available(), 0)
        self.assertEqual(cache.sets, [])          # no poisoned entry
        self.assertIn("not implemented", c.note())

    def test_opps_ignores_previously_poisoned_cache(self):
        cache = self._Cache(preload={("opps", "current"): {}})
        c = self.cms_rates.OPPSClient(cache)
        self.assertEqual(c.available(), 0)
        self.assertEqual(cache.sets, [])

    def test_asp_failure_not_cached(self):
        cache = self._Cache()
        c = self.cms_rates.ASPClient(cache)
        with patch.object(self.cms_rates.ASPClient, "_current_zip_url",
                          lambda self: None):
            self.assertIsNone(c.rate("J1745"))
        self.assertEqual(cache.sets, [])

    def test_no_phantom_pfs_client(self):
        self.assertFalse(hasattr(self.cms_rates, "PFSClient"))
        self.assertIn("no PFSClient", self.cms_rates.__doc__)


class TestSadSnapshotDisclosure(unittest.TestCase):
    """classify_frame's note discloses slice coverage so a rollup can
    never read as authoritative off a 15-code seed."""

    def test_note_carries_snapshot_size(self):
        try:
            import pandas as pd
            from rcm_mc.npi_cleaner.vendor_v49.npi_recovery import (
                sad_jurisdiction as SAD)
            from rcm_mc.npi_cleaner.vendor_v49.npi_recovery.coding_edits \
                import _default_ref
        except Exception as exc:
            self.skipTest(f"pandas / v49 unavailable: {exc}")
        std = pd.DataFrame({"hcpcs": ["C9399", "99213"],
                            "state": ["TX", "TX"],
                            "allowed_amt": ["100.00", "50.00"]})
        cls = SAD.classify_frame(std, ref_dir=_default_ref())
        self.assertIn("Snapshot covers", cls.attrs["note"])
        self.assertEqual(cls.attrs["snapshot_codes"], 15)


if __name__ == "__main__":
    unittest.main()
