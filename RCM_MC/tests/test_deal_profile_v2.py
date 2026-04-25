"""Tests for the narrative-flow deal profile v2."""
from __future__ import annotations

import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def _free_port() -> int:
    with socket.socket(socket.AF_INET,
                       socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# ── Synthetic packet shapes ──────────────────────────────────

@dataclass
class _Profile:
    name: str = "Test Hospital"
    state: str = "GA"
    ccn: str = "111111"
    beds: int = 250
    hospital_type: str = "Acute Care"
    ownership_type: str = "Investor-owned"
    fiscal_year: int = 2023


@dataclass
class _Comp:
    ccn: str
    name: str
    similarity_score: float
    beds: int


@dataclass
class _CompSet:
    members: List[_Comp] = field(default_factory=list)


@dataclass
class _ObsMetric:
    value: float
    unit: str = ""


@dataclass
class _Pred:
    value: float
    ci_low: float
    ci_high: float
    method: str


@dataclass
class _Impact:
    metric_key: str
    ebitda_impact: float


@dataclass
class _Bridge:
    current_ebitda: float
    target_ebitda: float
    total_ebitda_impact: float
    per_metric_impacts: List[_Impact]


@dataclass
class _RiskFlag:
    severity: str
    message: str


@dataclass
class _DiligenceQ:
    priority: str
    question: str


@dataclass
class _Packet:
    deal_id: str
    deal_name: str
    profile: _Profile = field(default_factory=_Profile)
    market_context: Optional[Dict[str, Any]] = None
    comparables: _CompSet = field(default_factory=_CompSet)
    observed_metrics: Dict[str, _ObsMetric] = field(
        default_factory=dict)
    predicted_metrics: Dict[str, _Pred] = field(
        default_factory=dict)
    ebitda_bridge: Optional[_Bridge] = None
    simulation: Any = None
    v2_simulation: Any = None
    risk_flags: List[_RiskFlag] = field(
        default_factory=list)
    diligence_questions: List[_DiligenceQ] = field(
        default_factory=list)


def _full_packet():
    return _Packet(
        deal_id="aurora",
        deal_name="Project Aurora",
        market_context={
            "cbsa": "Atlanta-Sandy Springs",
            "population": 6_300_000,
            "population_growth_5yr": 0.04,
            "median_household_income": 78_000,
            "pct_uninsured": 0.12,
            "attractiveness_score": 0.72,
        },
        comparables=_CompSet(members=[
            _Comp("220001", "Peer A", 0.92, 240),
            _Comp("220002", "Peer B", 0.88, 260),
        ]),
        observed_metrics={
            "denial_rate": _ObsMetric(0.12, ""),
            "days_in_ar": _ObsMetric(52.0, "days"),
        },
        predicted_metrics={
            "denial_rate": _Pred(
                0.10, 0.08, 0.13, "ridge"),
        },
        ebitda_bridge=_Bridge(
            current_ebitda=30_000_000,
            target_ebitda=42_000_000,
            total_ebitda_impact=12_000_000,
            per_metric_impacts=[
                _Impact("denial_rate", 5_000_000),
                _Impact("days_in_ar", 4_000_000),
                _Impact("net_collection_rate",
                        3_000_000),
            ]),
        risk_flags=[
            _RiskFlag(
                "high",
                "Material commercial concentration."),
            _RiskFlag(
                "medium",
                "Stale HCRIS — last filing FY2022."),
        ],
        diligence_questions=[
            _DiligenceQ(
                "high",
                "Verify CY2025 commercial contract terms."),
            _DiligenceQ(
                "medium",
                "Confirm HCRIS filing status."),
        ],
    )


# ── Tests ────────────────────────────────────────────────────

class TestEmptyState(unittest.TestCase):
    def test_no_packet_renders(self):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.ui.deal_profile_v2 import (
            render_deal_profile_v2,
        )
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PortfolioStore(db)
            store.init_db()
            html = render_deal_profile_v2(store, "ghost")
            self.assertIn("ghost", html)
            self.assertIn("No analysis packet found", html)
        finally:
            tmp.cleanup()


class TestEntitySection(unittest.TestCase):
    def test_renders_profile(self):
        from rcm_mc.ui.deal_profile_v2 import (
            _entity_section,
        )
        html = _entity_section(_full_packet())
        self.assertIn("Entity", html)
        self.assertIn("Test Hospital", html)
        self.assertIn("GA", html)
        self.assertIn("250", html)


class TestMarketSection(unittest.TestCase):
    def test_top_tier_market_narrative(self):
        from rcm_mc.ui.deal_profile_v2 import (
            _market_section,
        )
        html = _market_section(_full_packet())
        self.assertIn("Atlanta-Sandy Springs", html)
        self.assertIn("top-tier market", html)
        self.assertIn("0.72", html)

    def test_no_market_context_empty_state(self):
        from rcm_mc.ui.deal_profile_v2 import (
            _market_section,
        )
        p = _Packet(deal_id="x", deal_name="x")
        html = _market_section(p)
        self.assertIn("Run the market-context loader", html)


class TestCompsSection(unittest.TestCase):
    def test_lists_comps(self):
        from rcm_mc.ui.deal_profile_v2 import (
            _comps_section,
        )
        html = _comps_section(_full_packet())
        self.assertIn("Peer A", html)
        self.assertIn("Peer B", html)
        self.assertIn("0.92", html)

    def test_no_comps_empty_state(self):
        from rcm_mc.ui.deal_profile_v2 import (
            _comps_section,
        )
        p = _Packet(deal_id="x", deal_name="x")
        html = _comps_section(p)
        self.assertIn(
            "No comparable set built yet", html)


class TestMetricsSection(unittest.TestCase):
    def test_renders_metrics(self):
        from rcm_mc.ui.deal_profile_v2 import (
            _metrics_section,
        )
        html = _metrics_section(_full_packet())
        self.assertIn("Denial Rate", html)
        self.assertIn("Days In Ar", html)


class TestPredictionsSection(unittest.TestCase):
    def test_renders_with_intervals(self):
        from rcm_mc.ui.deal_profile_v2 import (
            _predictions_section,
        )
        html = _predictions_section(_full_packet())
        self.assertIn("Denial Rate", html)
        # CI shown
        self.assertIn("0.080", html)
        self.assertIn("0.130", html)
        self.assertIn("ridge", html)


class TestBridgeSection(unittest.TestCase):
    def test_renders_bridge(self):
        from rcm_mc.ui.deal_profile_v2 import (
            _bridge_section,
        )
        html = _bridge_section(_full_packet())
        # Total uplift in prose
        self.assertIn("$12.0M", html)
        # Per-lever impacts
        self.assertIn("Denial Rate", html)
        self.assertIn("Days In Ar", html)

    def test_no_bridge_empty_state(self):
        from rcm_mc.ui.deal_profile_v2 import (
            _bridge_section,
        )
        p = _Packet(deal_id="x", deal_name="x")
        html = _bridge_section(p)
        self.assertIn("No bridge built yet", html)


class TestRisksSection(unittest.TestCase):
    def test_renders_flags_with_severity(self):
        from rcm_mc.ui.deal_profile_v2 import (
            _risks_section,
        )
        html = _risks_section(_full_packet())
        self.assertIn("commercial concentration", html)
        self.assertIn("Stale HCRIS", html)
        # high-severity count in prose
        self.assertIn("high-severity", html)

    def test_no_risks_empty_state(self):
        from rcm_mc.ui.deal_profile_v2 import (
            _risks_section,
        )
        p = _Packet(deal_id="x", deal_name="x")
        html = _risks_section(p)
        self.assertIn("No risk flags raised", html)


class TestActionsSection(unittest.TestCase):
    def test_renders_diligence_questions(self):
        from rcm_mc.ui.deal_profile_v2 import (
            _actions_section,
        )
        html = _actions_section(_full_packet())
        self.assertIn("CY2025 commercial contract", html)
        self.assertIn("HCRIS filing", html)


class TestFullRender(unittest.TestCase):
    def test_all_9_sections_render(self):
        from rcm_mc.ui.deal_profile_v2 import (
            render_deal_profile_v2,
        )
        # Simulate a store-less render via monkey-patch _load_packet
        import rcm_mc.ui.deal_profile_v2 as mod
        orig = mod._load_packet
        try:
            mod._load_packet = (
                lambda store, deal_id: _full_packet())
            html = render_deal_profile_v2(
                None, "aurora")
            for label in [
                "Entity", "Market", "Comparables",
                "Observed metrics", "Predictions",
                "EBITDA bridge", "Scenarios", "Risks",
                "Actions",
            ]:
                self.assertIn(label, html)
            # Section numbers 01..09
            for n in range(1, 10):
                self.assertIn(f"{n:02d}", html)
        finally:
            mod._load_packet = orig


class TestHTTPRoute(unittest.TestCase):
    def test_route_registered(self):
        from rcm_mc.server import build_server
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            port = _free_port()
            srv, _h = build_server(
                port=port, db_path=db,
                host="127.0.0.1")
            t = threading.Thread(
                target=srv.serve_forever, daemon=True)
            t.start()
            try:
                time.sleep(0.2)
                with urllib.request.urlopen(
                        f"http://127.0.0.1:{port}"
                        "/deal/ghost/profile",
                        timeout=10) as resp:
                    self.assertEqual(resp.status, 200)
                    body = resp.read().decode()
                    self.assertIn("ghost", body)
                    self.assertIn(
                        "No analysis packet found", body)
            finally:
                srv.shutdown()
                srv.server_close()
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
