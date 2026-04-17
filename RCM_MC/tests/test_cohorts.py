"""Tests for cohort analytics (Brick 106)."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
import urllib.request as _u

from rcm_mc.analysis.cohorts import cohort_detail, cohort_rollup
from rcm_mc.deals.deal_tags import add_tag
from tests.test_alerts import _seed_with_pe_math


class TestCohortRollup(unittest.TestCase):
    def test_empty_store_returns_empty_df(self):
        with tempfile.TemporaryDirectory() as tmp:
            from rcm_mc.portfolio.store import PortfolioStore
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            df = cohort_rollup(store)
            self.assertTrue(df.empty)
            # Still has the right columns
            self.assertIn("tag", df.columns)
            self.assertIn("deal_count", df.columns)

    def test_single_tag_single_deal(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=2.0)
            add_tag(store, deal_id="ccf", tag="growth")
            df = cohort_rollup(store)
            self.assertEqual(len(df), 1)
            row = df.iloc[0]
            self.assertEqual(row["tag"], "growth")
            self.assertEqual(row["deal_count"], 1)
            self.assertAlmostEqual(row["weighted_moic"], 2.5, places=2)
            self.assertEqual(row["n_priced"], 1)
            self.assertEqual(row["covenant_trips"], 0)

    def test_deal_with_multiple_tags_appears_in_each_cohort(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=2.0)
            add_tag(store, deal_id="ccf", tag="growth")
            add_tag(store, deal_id="ccf", tag="fund_3")
            df = cohort_rollup(store)
            self.assertEqual(len(df), 2)
            tags = set(df["tag"])
            self.assertEqual(tags, {"growth", "fund_3"})

    def test_weighted_moic_by_ev(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "big", headroom=2.0)
            store2 = _seed_with_pe_math(tmp, "small", headroom=2.0)
            # Both have entry_ev=450e6 in seed — weighted MOIC should = 2.5
            add_tag(store, deal_id="big", tag="cohort_a")
            add_tag(store, deal_id="small", tag="cohort_a")
            df = cohort_rollup(store)
            row = df[df["tag"] == "cohort_a"].iloc[0]
            self.assertEqual(row["deal_count"], 2)
            self.assertAlmostEqual(row["weighted_moic"], 2.5, places=2)

    def test_covenant_trips_counted_per_cohort(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "d1", headroom=-0.5)  # TRIPPED
            _seed_with_pe_math(tmp, "d2", headroom=2.0)            # SAFE
            add_tag(store, deal_id="d1", tag="risky")
            add_tag(store, deal_id="d2", tag="risky")
            df = cohort_rollup(store)
            row = df[df["tag"] == "risky"].iloc[0]
            self.assertEqual(row["covenant_trips"], 1)


class TestCohortDetail(unittest.TestCase):
    def test_unknown_tag_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=2.0)
            self.assertTrue(cohort_detail(store, "nonexistent").empty)

    def test_cohort_detail_returns_deals(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=2.0)
            _seed_with_pe_math(tmp, "other", headroom=2.0)
            add_tag(store, deal_id="ccf", tag="growth")
            df = cohort_detail(store, "growth")
            self.assertEqual(len(df), 1)
            self.assertEqual(df.iloc[0]["deal_id"], "ccf")


class TestCohortsHttp(unittest.TestCase):
    def _start(self, tmp):
        import socket as _socket, threading, time as _time
        from rcm_mc.server import build_server
        s = _socket.socket(); s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]; s.close()
        server, _ = build_server(port=port,
                                 db_path=os.path.join(tmp, "p.db"))
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start(); _time.sleep(0.05)
        return server, port

    def test_cohorts_page_empty_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/cohorts") as r:
                    body = r.read().decode()
                    self.assertIn("No cohorts yet", body)
            finally:
                server.shutdown(); server.server_close()

    def test_cohorts_page_shows_tagged_deal(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=2.0)
            add_tag(store, deal_id="ccf", tag="growth")
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/cohorts") as r:
                    body = r.read().decode()
                    self.assertIn("growth", body)
                    self.assertTrue(
                        'href="/cohort/growth"' in body
                        or "href='/cohort/growth'" in body
                    )
            finally:
                server.shutdown(); server.server_close()

    def test_cohort_detail_page_lists_deal(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=2.0)
            add_tag(store, deal_id="ccf", tag="growth")
            server, port = self._start(tmp)
            try:
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/cohort/growth"
                ) as r:
                    body = r.read().decode()
                    self.assertIn("ccf", body)
                    # Accept either quote style in href
                    self.assertTrue(
                        'href="/deal/ccf"' in body or "href='/deal/ccf'" in body
                    )
            finally:
                server.shutdown(); server.server_close()

    def test_api_cohorts_returns_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=2.0)
            add_tag(store, deal_id="ccf", tag="growth")
            server, port = self._start(tmp)
            try:
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/api/cohorts"
                ) as r:
                    data = json.loads(r.read().decode())
                    self.assertEqual(len(data), 1)
                    self.assertEqual(data[0]["tag"], "growth")
                    self.assertEqual(data[0]["deal_count"], 1)
            finally:
                server.shutdown(); server.server_close()

    def test_dashboard_has_cohorts_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/") as r:
                    body = r.read().decode()
                    self.assertIn('href="/cohorts"', body)
            finally:
                server.shutdown(); server.server_close()


if __name__ == "__main__":
    unittest.main()
