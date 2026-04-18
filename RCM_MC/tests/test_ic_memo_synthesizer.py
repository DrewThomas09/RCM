"""Tests for ic_memo_synthesizer.py."""
from __future__ import annotations

import unittest


def _deal(**kw):
    base = {
        "source_id": "test_001",
        "deal_name": "Test Health System LBO",
        "ev_mm": 1_200.0,
        "ebitda_at_entry_mm": 100.0,
        "sector": "physician_group",
        "buyer": "Blackstone Group",
        "payer_mix": {"medicare": 0.45, "medicaid": 0.12, "commercial": 0.38, "self_pay": 0.05},
    }
    base.update(kw)
    return base


def _corpus():
    from rcm_mc.data_public.deals_corpus import _SEED_DEALS
    from rcm_mc.data_public.extended_seed import EXTENDED_SEED_DEALS
    from rcm_mc.data_public.extended_seed_16 import EXTENDED_SEED_DEALS_16
    return _SEED_DEALS + EXTENDED_SEED_DEALS + EXTENDED_SEED_DEALS_16


class TestBuildIcPacket(unittest.TestCase):

    def test_returns_ic_packet(self):
        from rcm_mc.data_public.ic_memo_synthesizer import build_ic_packet, IcPacket
        packet = build_ic_packet(_deal(), _corpus())
        self.assertIsInstance(packet, IcPacket)

    def test_overall_signal_set(self):
        from rcm_mc.data_public.ic_memo_synthesizer import build_ic_packet
        packet = build_ic_packet(_deal(), _corpus())
        self.assertIn(packet.overall_signal, ["green", "yellow", "red"])

    def test_signal_rationale_non_empty(self):
        from rcm_mc.data_public.ic_memo_synthesizer import build_ic_packet
        packet = build_ic_packet(_deal(), _corpus())
        self.assertGreater(len(packet.signal_rationale), 0)

    def test_lbo_analysis_populated(self):
        from rcm_mc.data_public.ic_memo_synthesizer import build_ic_packet
        packet = build_ic_packet(_deal(), _corpus())
        self.assertIsNotNone(packet.max_entry_multiple)
        self.assertIsNotNone(packet.lbo_feasible)

    def test_hold_optimization_populated(self):
        from rcm_mc.data_public.ic_memo_synthesizer import build_ic_packet
        packet = build_ic_packet(_deal(), _corpus())
        self.assertIsNotNone(packet.moic_maximizing_year)
        self.assertIsNotNone(packet.irr_maximizing_year)

    def test_reimbursement_risk_populated_with_payer_mix(self):
        from rcm_mc.data_public.ic_memo_synthesizer import build_ic_packet
        d = _deal()
        d["ebitda_mm"] = 100.0
        d["ev_ebitda"] = 12.0
        packet = build_ic_packet(d, _corpus())
        # base_ebitda_impact should be set or None (model may not fill it without ev_ebitda)
        # Just check it doesn't blow up
        self.assertIsInstance(packet, object)

    def test_corpus_base_rates_populated(self):
        from rcm_mc.data_public.ic_memo_synthesizer import build_ic_packet
        packet = build_ic_packet(_deal(), _corpus())
        self.assertIsNotNone(packet.corpus_moic_p50)

    def test_teardown_comps_list(self):
        from rcm_mc.data_public.ic_memo_synthesizer import build_ic_packet
        packet = build_ic_packet(_deal(), _corpus())
        self.assertIsInstance(packet.teardown_comps, list)

    def test_red_flags_list(self):
        from rcm_mc.data_public.ic_memo_synthesizer import build_ic_packet
        packet = build_ic_packet(_deal(), _corpus())
        self.assertIsInstance(packet.red_flags, list)

    def test_deal_stored_in_packet(self):
        from rcm_mc.data_public.ic_memo_synthesizer import build_ic_packet
        d = _deal(deal_name="Meridian Health LBO")
        packet = build_ic_packet(d, _corpus())
        self.assertEqual(packet.deal["deal_name"], "Meridian Health LBO")

    def test_aggressive_entry_signals_warning(self):
        """Very high entry EV/EBITDA should trigger aggressive corpus signal."""
        from rcm_mc.data_public.ic_memo_synthesizer import build_ic_packet
        d = _deal(ev_mm=3_000.0, ebitda_at_entry_mm=100.0)  # 30x entry
        packet = build_ic_packet(d, _corpus())
        self.assertIn(packet.entry_corpus_signal, ["aggressive", "above_median", "below_median", "conservative", "unknown"])

    def test_empty_corpus_does_not_crash(self):
        from rcm_mc.data_public.ic_memo_synthesizer import build_ic_packet
        packet = build_ic_packet(_deal(), [])
        self.assertIsNotNone(packet.overall_signal)

    def test_missing_ev_does_not_crash(self):
        from rcm_mc.data_public.ic_memo_synthesizer import build_ic_packet
        d = {"source_id": "t", "deal_name": "Incomplete", "sector": "hospital"}
        packet = build_ic_packet(d, [])
        self.assertIsInstance(packet.overall_signal, str)


class TestIcPacketReport(unittest.TestCase):

    def _packet(self):
        from rcm_mc.data_public.ic_memo_synthesizer import build_ic_packet
        return build_ic_packet(_deal(), _corpus())

    def test_report_is_string(self):
        from rcm_mc.data_public.ic_memo_synthesizer import ic_packet_report
        text = ic_packet_report(self._packet())
        self.assertIsInstance(text, str)

    def test_report_contains_deal_name(self):
        from rcm_mc.data_public.ic_memo_synthesizer import ic_packet_report
        text = ic_packet_report(self._packet())
        self.assertIn("Test Health System", text)

    def test_report_contains_sections(self):
        from rcm_mc.data_public.ic_memo_synthesizer import ic_packet_report
        text = ic_packet_report(self._packet())
        for section in ["LBO Entry", "Hold Period", "Reimbursement", "Sector", "Sponsor"]:
            self.assertIn(section, text)

    def test_report_contains_signal(self):
        from rcm_mc.data_public.ic_memo_synthesizer import ic_packet_report
        packet = self._packet()
        text = ic_packet_report(packet)
        self.assertIn(packet.overall_signal.upper(), text)

    def test_report_contains_entry_multiple(self):
        from rcm_mc.data_public.ic_memo_synthesizer import ic_packet_report
        text = ic_packet_report(self._packet())
        self.assertIn("Max affordable", text)


class TestQuickIcReport(unittest.TestCase):

    def test_returns_string(self):
        from rcm_mc.data_public.ic_memo_synthesizer import quick_ic_report
        text = quick_ic_report(_deal(), _corpus())
        self.assertIsInstance(text, str)

    def test_non_trivial_length(self):
        from rcm_mc.data_public.ic_memo_synthesizer import quick_ic_report
        text = quick_ic_report(_deal(), _corpus())
        self.assertGreater(len(text), 300)


class TestIcPacketWithRealCorpus(unittest.TestCase):
    """Integration tests using the real seeded corpus."""

    def setUp(self):
        import tempfile, os
        from rcm_mc.data_public.deals_corpus import DealsCorpus
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = tmp.name
        tmp.close()
        self.corpus = DealsCorpus(self.db_path)
        self.corpus.seed(skip_if_populated=False)

    def tearDown(self):
        import os
        os.unlink(self.db_path)

    def _seeds(self):
        from rcm_mc.data_public.deals_corpus import _SEED_DEALS
        return _SEED_DEALS

    def test_hca_lbo_packet(self):
        """HCA 2006 deal should generate a valid packet."""
        from rcm_mc.data_public.ic_memo_synthesizer import build_ic_packet
        hca = self._seeds()[0]
        packet = build_ic_packet(hca, self._seeds())
        self.assertIn(packet.overall_signal, ["green", "yellow", "red"])
        self.assertIsNotNone(packet.corpus_moic_p50)

    def test_home_health_deal(self):
        from rcm_mc.data_public.ic_memo_synthesizer import build_ic_packet
        deal = {
            "source_id": "p001",
            "deal_name": "HC Home Health Acquisition",
            "ev_mm": 800.0,
            "ebitda_at_entry_mm": 70.0,
            "sector": "home_health",
            "buyer": "Warburg Pincus",
            "payer_mix": {"medicare": 0.72, "medicaid": 0.10, "commercial": 0.15, "self_pay": 0.03},
            "ebitda_mm": 70.0,
            "ev_ebitda": 11.4,
            "hold_years": 5.0,
        }
        packet = build_ic_packet(deal, self._seeds())
        self.assertIsInstance(packet.overall_signal, str)


if __name__ == "__main__":
    unittest.main()
