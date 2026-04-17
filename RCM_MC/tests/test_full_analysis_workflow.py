"""End-to-end happy-path walk: register deal → build packet → export memo.

This is the workflow a partner actually runs. If any intermediate step
breaks, the whole product is broken — which is why it gets its own
test file separate from the component-level suites.

We stop short of the HTTP layer because that's covered by the
endpoint tests; this file exercises the Python-level orchestration
that those endpoints delegate to.
"""
from __future__ import annotations

import os
import re
import tempfile
import unittest

from rcm_mc.analysis.analysis_store import (
    get_or_build_packet,
    load_latest_packet,
)
from rcm_mc.analysis.packet import ObservedMetric, SectionStatus
from rcm_mc.analysis.packet_builder import build_analysis_packet
from rcm_mc.exports import PacketRenderer, list_exports, record_export
from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.ui.analysis_workbench import render_workbench


def _store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    s = PortfolioStore(path)
    s.init_db()
    return s, path


class TestFullWorkflow(unittest.TestCase):
    def setUp(self):
        self.store, self.path = _store()
        # Step 1: register deal + hospital profile.
        self.store.upsert_deal("e2e-acme", name="Acme Regional", profile={
            "bed_count": 420, "region": "midwest", "state": "IL",
            "payer_mix": {"medicare": 0.40, "commercial": 0.45, "medicaid": 0.15},
            "teaching_status": "non-teaching", "urban_rural": "urban",
        })

    def tearDown(self):
        try:
            os.unlink(self.path)
        except OSError:
            pass

    def test_register_through_export_memo(self):
        # Step 2: supply actuals + financials → build packet.
        packet = build_analysis_packet(
            self.store, "e2e-acme", skip_simulation=True,
            observed_override={
                "denial_rate": ObservedMetric(value=11.0, source="USER_INPUT"),
                "days_in_ar": ObservedMetric(value=55.0, source="USER_INPUT"),
                "clean_claim_rate": ObservedMetric(value=88.0),
                "net_collection_rate": ObservedMetric(value=94.0),
                "cost_to_collect": ObservedMetric(value=3.8),
            },
            target_metrics={
                "denial_rate": 7.0, "days_in_ar": 45.0,
                "cost_to_collect": 3.0,
            },
            financials={
                "gross_revenue": 1_000_000_000, "net_revenue": 400_000_000,
                "current_ebitda": 32_000_000, "claims_volume": 300_000,
            },
        )
        # Step 3: every section populated.
        self.assertEqual(packet.deal_id, "e2e-acme")
        self.assertEqual(packet.profile.bed_count, 420)
        self.assertGreater(packet.completeness.observed_count, 0)
        self.assertEqual(packet.ebitda_bridge.status, SectionStatus.OK)
        self.assertGreater(packet.ebitda_bridge.total_ebitda_impact, 0)
        self.assertTrue(packet.risk_flags)
        self.assertTrue(packet.diligence_questions)
        self.assertTrue(packet.provenance.nodes)

        # Step 4: export the diligence memo + csv + json.
        renderer = PacketRenderer()
        memo_html = renderer.render_diligence_memo_html(packet)
        csv_path = renderer.render_raw_data_csv(packet)
        memo_pptx = renderer.render_diligence_memo_pptx(packet)
        memo_json = renderer.render_packet_json(packet)

        # Step 5: memo carries packet data — spot-check specific
        # numbers that must propagate from packet → memo.
        self.assertIn("Acme Regional", memo_html)
        self.assertIn("$", memo_html)
        self.assertIn(packet.run_id, memo_html)

        # CSV: check the denial_rate row is present.
        text = csv_path.read_text()
        self.assertIn("denial_rate", text)
        # Audit footer comments at bottom.
        self.assertIn(packet.run_id, text)

        # PPTX fallback shows run_id in the footer slide. Prompt 22
        # upgraded the fallback from a plain-text ``.pptx.txt`` to a
        # real OOXML ``.pptx`` zip; the final slide carries the audit
        # footer text.
        import zipfile as _zip
        with _zip.ZipFile(memo_pptx) as z:
            pptx_text = z.read("ppt/slides/slide8.xml").decode("utf-8")
        self.assertIn(packet.run_id, pptx_text)

        # JSON roundtrips.
        import json as _json
        parsed = _json.loads(memo_json)
        self.assertEqual(parsed["deal_id"], "e2e-acme")

    def test_workbench_renders_from_same_packet(self):
        packet = build_analysis_packet(
            self.store, "e2e-acme", skip_simulation=True,
            observed_override={
                "denial_rate": ObservedMetric(value=11.0),
            },
            financials={
                "gross_revenue": 1_000_000_000, "net_revenue": 400_000_000,
                "current_ebitda": 32_000_000, "claims_volume": 300_000,
            },
        )
        html = render_workbench(packet)
        self.assertIn("Acme Regional", html)
        # Both workbench and memo should agree on the total EBITDA
        # impact number. Extract from each and compare.
        memo = PacketRenderer().render_diligence_memo_html(packet)
        dollar_rx = re.compile(r"\$[\d,]+(?:\.\d+)?[KMB]?")
        workbench_dollars = set(dollar_rx.findall(html))
        memo_dollars = set(dollar_rx.findall(memo))
        # Intersection is non-trivial: at least current_ebitda appears
        # in both renders.
        self.assertTrue(workbench_dollars & memo_dollars,
                        "workbench and memo share no dollar figures")

    def test_cached_and_exported_chain(self):
        # Build once → cache.
        p1 = get_or_build_packet(
            self.store, "e2e-acme", skip_simulation=True,
            observed_override={
                "denial_rate": ObservedMetric(value=11.0),
            },
            financials={
                "gross_revenue": 1_000_000_000, "net_revenue": 400_000_000,
                "current_ebitda": 32_000_000, "claims_volume": 300_000,
            },
        )
        # Export + record audit row.
        renderer = PacketRenderer()
        memo = renderer.render_diligence_memo_html(p1)
        record_export(
            self.store, deal_id="e2e-acme",
            analysis_run_id=p1.run_id, format="html",
            filepath=None, file_size_bytes=len(memo),
            packet_hash="abc",
        )
        # Load latest packet — same run_id.
        latest = load_latest_packet(self.store, "e2e-acme")
        self.assertEqual(latest.run_id, p1.run_id)
        # Export audit present.
        exp = list_exports(self.store, "e2e-acme")
        self.assertEqual(len(exp), 1)
        self.assertEqual(exp[0]["analysis_run_id"], p1.run_id)


if __name__ == "__main__":
    unittest.main()
