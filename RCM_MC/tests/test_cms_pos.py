"""Tests for the CMS Provider of Services (POS) data source.

POS gives us `chain_identifier` — the field that lets the tool say
"this deal is a LifePoint facility" or "part of the HCA chain of 4
hospitals." Huge for PE peer-matching and concentration scanning.
"""
from __future__ import annotations

import os
import tempfile
import unittest


class TestPOSParser(unittest.TestCase):
    def test_parses_sample_csv(self):
        from rcm_mc.data.cms_pos import (
            parse_pos_csv, DEFAULT_POS_SAMPLE_PATH,
        )
        records = parse_pos_csv(DEFAULT_POS_SAMPLE_PATH)
        self.assertGreater(len(records), 20,
                           msg="sample should have ≥20 representative CCNs")

    def test_chain_identifier_populated(self):
        """At least some sample rows have a chain_identifier — that's
        the GOLD field, the whole point of ingesting POS."""
        from rcm_mc.data.cms_pos import (
            parse_pos_csv, DEFAULT_POS_SAMPLE_PATH,
        )
        records = parse_pos_csv(DEFAULT_POS_SAMPLE_PATH)
        chains = {r.chain_identifier for r in records if r.chain_identifier}
        self.assertGreater(len(chains), 5,
                           msg=f"need ≥5 distinct chains, got {len(chains)}")

    def test_lifepoint_has_multiple_ccns_in_sample(self):
        """The LifePoint chain has 3 CCNs in our sample so the
        `count_facilities_in_chain` helper has something real to
        report. Regression guard for the sample file."""
        from rcm_mc.data.cms_pos import (
            parse_pos_csv, DEFAULT_POS_SAMPLE_PATH,
        )
        records = parse_pos_csv(DEFAULT_POS_SAMPLE_PATH)
        lp = [r for r in records if r.chain_identifier == "LIFEPOINT_001"]
        self.assertGreaterEqual(len(lp), 3)

    def test_hca_chain_present(self):
        from rcm_mc.data.cms_pos import (
            parse_pos_csv, DEFAULT_POS_SAMPLE_PATH,
        )
        records = parse_pos_csv(DEFAULT_POS_SAMPLE_PATH)
        hca = [r for r in records if r.chain_identifier == "HCA_001"]
        self.assertGreaterEqual(len(hca), 2)

    def test_independent_hospital_has_empty_chain(self):
        """Not every CCN is in a chain — some are truly independent.
        Those should have chain_identifier = '' (not None), which is
        our "unknown chain" sentinel."""
        from rcm_mc.data.cms_pos import (
            parse_pos_csv, DEFAULT_POS_SAMPLE_PATH,
        )
        records = parse_pos_csv(DEFAULT_POS_SAMPLE_PATH)
        by_ccn = {r.ccn: r for r in records}
        # 240080 = Hennepin County Medical Center — seeded as independent
        self.assertIn("240080", by_ccn)
        self.assertEqual(by_ccn["240080"].chain_identifier, "")


class TestPOSStoreRoundtrip(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "t.db")
        from rcm_mc.portfolio.store import PortfolioStore
        self.store = PortfolioStore(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def test_refresh_roundtrip(self):
        """refresh_pos_source should populate the cms_pos table
        and the read helpers should find what was inserted."""
        from rcm_mc.data.cms_pos import (
            refresh_pos_source, get_facility_by_ccn,
        )
        n = refresh_pos_source(self.store)
        self.assertGreater(n, 20)

        fac = get_facility_by_ccn(self.store, "450022")
        self.assertIsNotNone(fac)
        self.assertEqual(fac["chain_identifier"], "LIFEPOINT_001")
        self.assertEqual(fac["state"], "TX")

    def test_get_chain_members(self):
        from rcm_mc.data.cms_pos import (
            refresh_pos_source, get_chain_members,
        )
        refresh_pos_source(self.store)
        lp = get_chain_members(self.store, "LIFEPOINT_001")
        self.assertGreaterEqual(len(lp), 3)
        # Returned sorted — verify by checking states are in order
        states = [f["state"] for f in lp]
        self.assertEqual(states, sorted(states))

    def test_count_facilities_in_chain(self):
        from rcm_mc.data.cms_pos import (
            refresh_pos_source, count_facilities_in_chain,
        )
        refresh_pos_source(self.store)
        # LifePoint: 3 CCNs in sample
        self.assertGreaterEqual(count_facilities_in_chain(
            self.store, "450022"), 3)
        # Independent hospital → count 1 (itself)
        self.assertEqual(count_facilities_in_chain(
            self.store, "240080"), 1)
        # Unknown CCN → count 0
        self.assertEqual(count_facilities_in_chain(
            self.store, "999999"), 0)

    def test_idempotent_refresh(self):
        """Running refresh twice should produce the same row count —
        not doubles. INSERT OR REPLACE on a PRIMARY KEY."""
        from rcm_mc.data.cms_pos import refresh_pos_source
        n1 = refresh_pos_source(self.store)
        n2 = refresh_pos_source(self.store)
        self.assertEqual(n1, n2)

        with self.store.connect() as con:
            total = con.execute(
                "SELECT COUNT(*) AS c FROM cms_pos"
            ).fetchone()["c"]
        self.assertEqual(total, n1,
                         msg="idempotent refresh should not double rows")


class TestKnownSources(unittest.TestCase):
    def test_cms_pos_in_known_sources(self):
        from rcm_mc.data.data_refresh import KNOWN_SOURCES
        self.assertIn("cms_pos", KNOWN_SOURCES)

    def test_cms_pos_dispatches(self):
        """The refresh_all_sources → _default_refreshers path must
        have a dispatcher for cms_pos."""
        from rcm_mc.data.data_refresh import _default_refreshers
        refs = _default_refreshers()
        self.assertIn("cms_pos", refs)
        # Check it's callable
        self.assertTrue(callable(refs["cms_pos"]))


class TestRiskScanExposesChain(unittest.TestCase):
    """The portfolio risk scanner should surface chain info for
    any deal whose deal_id is a valid CCN."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "t.db")
        from rcm_mc.portfolio.store import PortfolioStore
        self.store = PortfolioStore(self.db)
        # Seed POS first
        from rcm_mc.data.cms_pos import refresh_pos_source
        refresh_pos_source(self.store)
        # Seed a deal whose deal_id is a valid CCN from the sample
        import json
        from datetime import datetime, timezone
        with self.store.connect() as con:
            con.execute(
                "INSERT INTO deals (deal_id, name, created_at, profile_json) "
                "VALUES (?, ?, ?, ?)",
                ("450022", "LifePoint Silsbee",
                 datetime.now(timezone.utc).isoformat(),
                 json.dumps({"sector": "hospital"})),
            )
            con.commit()

    def tearDown(self):
        self.tmp.cleanup()

    def test_gather_includes_chain(self):
        from rcm_mc.ui.portfolio_risk_scan_page import _gather_per_deal
        deals = _gather_per_deal(self.db)
        lp = next((d for d in deals if d["deal_id"] == "450022"), None)
        self.assertIsNotNone(lp)
        self.assertEqual(lp["chain"], "LIFEPOINT_001")
        self.assertGreaterEqual(lp["chain_size"], 3)

    def test_chain_surfaces_in_rendered_html(self):
        from rcm_mc.ui.portfolio_risk_scan_page import render_portfolio_risk_scan
        html = render_portfolio_risk_scan(self.db)
        self.assertIn("LIFEPOINT_001", html)
        # Chain column header
        self.assertIn("Chain", html)


if __name__ == "__main__":
    unittest.main()
