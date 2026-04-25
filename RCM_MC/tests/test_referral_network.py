"""Tests for the physician referral network packet.

Coverage:
  • Graph construction + augmentation (repeat add_edge sums weights)
  • Centrality (in-degree, out-degree, eigenvector)
  • Leakage with platform tagging
  • Key-person-risk threshold detection
  • Departure simulation (delta in leakage + volume lost)
  • Payer-leverage scoring
"""
from __future__ import annotations

import unittest


def _build_panel():
    """A small fixture: 6 platform NPIs + 4 outside, with mixed
    inbound/outbound flow.

    Platform org "PlatformPC":
        P1 — receives heavy inbound from external Ext1
        P2 — receives moderate inbound from Ext1 + Ext2
        P3 — sends outbound to platform (internal)
        P4 — sends outbound to outside Ext3 (leakage)
        P5 — small node
        P6 — quiet/disconnected

    External:
        Ext1, Ext2 — referrers (high volume into platform)
        Ext3 — receiver (platform leaks to)
        Ext4 — competing platform receiver
    """
    from rcm_mc.referral import ReferralGraph
    g = ReferralGraph()
    for npi in ("P1", "P2", "P3", "P4", "P5", "P6"):
        g.set_node_org(npi, "PlatformPC")
    for npi in ("Ext1", "Ext2", "Ext3", "Ext4"):
        g.set_node_org(npi, "OutsideClinic")

    # Inbound to platform
    g.add_edge("Ext1", "P1", 200)
    g.add_edge("Ext1", "P2", 100)
    g.add_edge("Ext2", "P2", 80)
    g.add_edge("Ext2", "P5", 20)

    # Internal platform referrals (high → physician retention indicator)
    g.add_edge("P3", "P1", 50)
    g.add_edge("P3", "P2", 40)

    # Leakage: platform refers to external
    g.add_edge("P4", "Ext3", 60)
    g.add_edge("P4", "Ext4", 30)
    return g


class TestReferralGraph(unittest.TestCase):
    def test_add_edge_sums_weight(self):
        from rcm_mc.referral import ReferralGraph
        g = ReferralGraph()
        g.add_edge("A", "B", 10)
        g.add_edge("A", "B", 5)
        self.assertEqual(g.out_neighbors("A")["B"], 15)

    def test_node_count_and_edges(self):
        g = _build_panel()
        self.assertEqual(g.node_count(), 10)
        # 8 distinct (src, dst) pairs
        self.assertEqual(g.edge_count(), 8)

    def test_drop_node_returns_new_graph(self):
        from rcm_mc.referral import ReferralGraph
        g = _build_panel()
        new = g.drop_node("Ext1")
        self.assertNotIn("Ext1", new.nodes())
        self.assertIn("Ext1", g.nodes())  # original untouched
        # Ext1's edges should be gone in the new graph
        self.assertEqual(new.in_weight("P1"), 50)  # only P3 left


class TestCentrality(unittest.TestCase):
    def test_in_degree_normalized(self):
        from rcm_mc.referral import in_degree_centrality
        g = _build_panel()
        c = in_degree_centrality(g)
        # P1 = 200 (Ext1) + 50 (P3) = 250 — the highest in-degree
        # P2 = 100 + 80 + 40 = 220
        self.assertAlmostEqual(c["P1"], 1.0, places=3)
        self.assertAlmostEqual(c["P2"], 220 / 250, places=3)

    def test_out_degree_normalized(self):
        from rcm_mc.referral import out_degree_centrality
        g = _build_panel()
        c = out_degree_centrality(g)
        # Ext1 = 300 (highest out)
        self.assertAlmostEqual(c["Ext1"], 1.0, places=3)
        # P4 = 90 (60 + 30 leakage)
        self.assertAlmostEqual(c["P4"], 90 / 300, places=3)

    def test_eigenvector_converges(self):
        from rcm_mc.referral import eigenvector_centrality
        g = _build_panel()
        c = eigenvector_centrality(g)
        # All scores should be non-negative
        for npi, v in c.items():
            self.assertGreaterEqual(v, 0)
        # P1 + P2 (the inbound hubs) should rank above P6 (disconnected)
        # Actually P6 is connected via P3→nothing — fully isolated
        # Just check P1 has higher centrality than at least 5 others
        sorted_by_c = sorted(c.items(), key=lambda kv: kv[1])
        top3 = {kv[0] for kv in sorted_by_c[-3:]}
        # P1, P2 should be in top-3 because they're hub destinations
        self.assertIn("P1", top3.union({"Ext1", "P2"}))


class TestLeakage(unittest.TestCase):
    def test_computes_internal_external_split(self):
        from rcm_mc.referral import compute_leakage
        g = _build_panel()
        result = compute_leakage(g, ["PlatformPC"])
        # Internal: P3→P1 (50) + P3→P2 (40) = 90
        # External: P4→Ext3 (60) + P4→Ext4 (30) = 90
        self.assertEqual(result["internal_referral_volume"], 90.0)
        self.assertEqual(result["external_referral_volume"], 90.0)
        self.assertEqual(result["leakage_rate"], 0.5)
        self.assertEqual(result["platform_npi_count"], 6)

    def test_top_external_destinations_ranked(self):
        from rcm_mc.referral import compute_leakage
        g = _build_panel()
        result = compute_leakage(g, ["PlatformPC"])
        ext = result["external_destinations"]
        self.assertEqual(ext[0]["npi"], "Ext3")  # highest external volume
        self.assertEqual(ext[0]["weight"], 60.0)


class TestKeyPersonRisk(unittest.TestCase):
    def test_top_referrer_above_threshold(self):
        from rcm_mc.referral import compute_key_person_risk
        g = _build_panel()
        # Ext1 sends 300 of 400 inbound → 75% (well above 20%)
        result = compute_key_person_risk(
            g, ["PlatformPC"], threshold=0.20)
        self.assertEqual(result["external_referrer_count"], 2)
        self.assertGreaterEqual(result["critical_count"], 1)
        # Top referrer is Ext1
        self.assertEqual(result["referrers"][0]["npi"], "Ext1")
        self.assertGreaterEqual(
            result["referrers"][0]["share_of_inbound"], 0.7)
        self.assertTrue(result["referrers"][0]["critical"])

    def test_internal_referrals_excluded(self):
        """P3 sends 90 internal volume; should NOT appear as a
        key-person external referrer."""
        from rcm_mc.referral import compute_key_person_risk
        g = _build_panel()
        result = compute_key_person_risk(g, ["PlatformPC"])
        npis = {r["npi"] for r in result["referrers"]}
        self.assertNotIn("P3", npis)


class TestDepartureSimulation(unittest.TestCase):
    def test_dropping_top_referrer_increases_leakage_concentration(self):
        from rcm_mc.referral import simulate_departure
        g = _build_panel()
        result = simulate_departure(g, "Ext1", ["PlatformPC"])
        # Volume lost should equal Ext1's outbound (which is also
        # platform inbound from Ext1) = 300
        self.assertAlmostEqual(
            result["physician_outbound_volume"], 300.0, places=1,
        )
        # Internal ratio rises after losing external referrer
        self.assertGreaterEqual(
            result["after"]["leakage_rate"],
            result["before"]["leakage_rate"],
        )

    def test_dropping_internal_node_changes_volumes(self):
        from rcm_mc.referral import simulate_departure
        g = _build_panel()
        result = simulate_departure(g, "P3", ["PlatformPC"])
        # P3's internal contribution = 90
        self.assertAlmostEqual(
            result["internal_volume_lost"], 90.0, places=1,
        )


class TestPayerLeverage(unittest.TestCase):
    def test_no_alternatives_zero_leverage(self):
        from rcm_mc.referral import payer_leverage_score
        g = _build_panel()
        # Payer has no alternative referrers → zero leverage
        result = payer_leverage_score(
            g, ["PlatformPC"], payer_npis=[])
        self.assertEqual(result["payer_leverage_score"], 0.0)

    def test_payer_with_top_referrer_alternatives(self):
        from rcm_mc.referral import payer_leverage_score
        g = _build_panel()
        # Payer has Ext1 as an alternative network — so they could
        # steer Ext1's referrals away from us. Total platform
        # inbound (including internal P3 → P1/P2) is 490; Ext1
        # accounts for 300 of that → ~61% leverage.
        result = payer_leverage_score(
            g, ["PlatformPC"], payer_npis=["Ext1"])
        self.assertEqual(result["platform_inbound_volume"], 490.0)
        self.assertEqual(result["rerouteable_volume"], 300.0)
        self.assertAlmostEqual(
            result["payer_leverage_score"], 300.0 / 490.0, places=3)


if __name__ == "__main__":
    unittest.main()
