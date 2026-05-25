"""CapIQ export ingestion + entity resolution to CMS facilities.

Exercises the real path against the shipped HCRIS data: parse a Capital IQ
export (flexible columns), resolve company names to CMS CCNs with surfaced
ambiguity, fill gaps with CMS facility data, and persist the name↔CCN
crosswalk. No real CapIQ files needed — a synthetic export fixture drives it.
"""
import os
import tempfile
import unittest

from rcm_mc.data import capiq
from rcm_mc.data.capiq import ResolutionStatus
from rcm_mc.data.hcris import lookup_by_name


def _write_csv(path: str, headers, rows) -> None:
    import csv
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(headers)
        for r in rows:
            w.writerow(r)


class TestParse(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "export.csv")

    def tearDown(self):
        self.tmp.cleanup()

    def test_flexible_columns_and_numeric_parsing(self):
        # Header variants + messy numerics ($ , parens x NA).
        _write_csv(
            self.path,
            ["IQ_COMPANY_ID", "Company Name", "State", "TEV", "LTM EBITDA",
             "TEV/EBITDA", "Closed Date"],
            [["IQ123", "Acme Surgical Holdings", "TX", "$1,250.0", "(20.5)",
              "12.5x", "2025-03-01"]],
        )
        recs = capiq.parse_capiq_export(self.path)
        self.assertEqual(len(recs), 1)
        r = recs[0]
        self.assertEqual(r.capiq_id, "IQ123")
        self.assertEqual(r.company_name, "Acme Surgical Holdings")
        self.assertEqual(r.state, "TX")
        self.assertAlmostEqual(r.ev_mm, 1250.0)
        self.assertAlmostEqual(r.ebitda_mm, -20.5)   # parens → negative
        self.assertAlmostEqual(r.ev_ebitda, 12.5)    # 'x' stripped
        self.assertIn("Closed Date", r.raw)          # nothing dropped

    def test_missing_id_falls_back_to_name_and_skips_nameless(self):
        _write_csv(self.path, ["Company", "TEV"],
                   [["Beacon Health", "100"], ["", "50"]])
        recs = capiq.parse_capiq_export(self.path)
        self.assertEqual(len(recs), 1)              # nameless row skipped
        self.assertEqual(recs[0].capiq_id, "Beacon Health")


class TestResolution(unittest.TestCase):
    def _rec(self, name, state=None):
        return capiq.CapIQRecord(capiq_id=name, company_name=name, state=state)

    def test_exact_name_resolves_cleanly(self):
        # Use a real HCRIS facility's exact name → should be RESOLVED.
        seed = lookup_by_name("Cleveland Clinic Avon", limit=1)
        self.assertTrue(seed, "fixture precondition: HCRIS data present")
        exact = seed[0]["name"]
        res = capiq.resolve_record(self._rec(exact))
        self.assertEqual(res.status, ResolutionStatus.RESOLVED)
        self.assertEqual(res.ccn, str(seed[0]["ccn"]))
        self.assertGreaterEqual(res.confidence, 0.90)

    def test_generic_name_is_ambiguous_not_guessed(self):
        # "Cleveland Clinic" matches several facilities — must NOT auto-pick.
        res = capiq.resolve_record(self._rec("Cleveland Clinic"))
        self.assertEqual(res.status, ResolutionStatus.AMBIGUOUS)
        self.assertIsNone(res.ccn)
        self.assertGreater(len(res.candidates), 1)
        # candidates are score-sorted descending
        scores = [c.score for c in res.candidates]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_non_hospital_target_is_unmatched(self):
        res = capiq.resolve_record(self._rec("Zzqx Software Holdings LLC"))
        self.assertEqual(res.status, ResolutionStatus.UNMATCHED)
        self.assertIsNone(res.ccn)


class TestEnrichmentAndPersistence(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "t.db")
        from rcm_mc.portfolio.store import PortfolioStore
        self.store = PortfolioStore(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def test_cms_enrichment_only_for_resolved(self):
        seed = lookup_by_name("Cleveland Clinic Avon", limit=1)
        resolved = capiq.resolve_record(
            capiq.CapIQRecord(capiq_id="x", company_name=seed[0]["name"]))
        gap = capiq.enrich_with_cms(resolved)
        self.assertTrue(gap)                          # CMS fields present
        self.assertIn("state", gap)

        ambiguous = capiq.resolve_record(
            capiq.CapIQRecord(capiq_id="y", company_name="Cleveland Clinic"))
        self.assertEqual(capiq.enrich_with_cms(ambiguous), {})  # never enrich a guess

    def test_store_crosswalk_roundtrip(self):
        recs = [
            capiq.CapIQRecord(capiq_id="A", company_name=lookup_by_name(
                "Cleveland Clinic Avon", limit=1)[0]["name"]),
            capiq.CapIQRecord(capiq_id="B", company_name="Cleveland Clinic"),
            capiq.CapIQRecord(capiq_id="C", company_name="Zzqx Software LLC"),
        ]
        resolutions = capiq.resolve_export(recs)
        n = capiq.load_resolutions_to_store(self.store, resolutions)
        self.assertEqual(n, 3)
        # idempotent upsert
        self.assertEqual(capiq.load_resolutions_to_store(self.store, resolutions), 3)
        with self.store.connect() as con:
            rows = con.execute(
                "SELECT capiq_id, status, ccn FROM capiq_entity_map ORDER BY capiq_id"
            ).fetchall()
        self.assertEqual(len(rows), 3)
        summary = capiq.resolution_summary(resolutions)
        self.assertEqual(summary["resolved"] + summary["ambiguous"]
                         + summary["unmatched"], 3)


if __name__ == "__main__":
    unittest.main()
