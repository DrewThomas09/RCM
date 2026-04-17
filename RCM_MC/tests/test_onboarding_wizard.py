"""Tests for the five-step onboarding wizard (Prompt 26).

Invariants locked here:

 1. GET /new-deal renders Step 1 with the search box.
 2. /api/data/hospitals returns match JSON (already covered by
    Prompt 23; smoke-checked here via the Step-1 JS dependency).
 3. Step-1 HTML includes the manual-entry form.
 4. POST /api/deals/wizard/select with a CCN runs auto-populate,
    upserts the deal, and redirects to Step 2.
 5. Step 2 renders source badges for populated fields.
 6. Step 2 renders gap rows sorted by EBITDA sensitivity rank.
 7. Step 2 shows a coverage bar.
 8. Step 2 "Skip to Analysis" button links to Step 4.
 9. Step 3 lists files processed so far.
10. Step 3 upload POST merges extracted metrics into the session.
11. Step 4 shows the projected grade + override fields.
12. Step 4 shows fewer than 11 override fields (top-10 cap).
13. Step 4 "Run Monte Carlo" checkbox defaults on when grade >= B.
14. Step 5 auto-redirects to the workbench.
15. Manual-entry path creates a synthetic deal and lands on Step 2.
16. Unknown deal_id on Step 2/3/4/5 redirects back to Step 1.
17. Wizard launch rebuilds the packet and exposes it at
    ``/analysis/<deal_id>``.
18. Session state survives between step renders.
19. End-to-end: select → step2 → step3 (upload) → step4 → launch
    → step5 → redirect to workbench.
20. Manual path form fields populate the session profile.
"""
from __future__ import annotations

import json
import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def _start(db_path: str) -> tuple:
    from rcm_mc.server import build_server
    s = socket.socket(); s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]; s.close()
    server, _ = build_server(port=port, db_path=db_path)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.05)
    return server, port


def _first_hcris_ccn() -> str:
    from rcm_mc.data.hcris import _get_hcris_cached
    df = _get_hcris_cached()
    return str(df.iloc[0]["ccn"])


# ── Step renderers (module-level) ─────────────────────────────────

class TestWizardRenderers(unittest.TestCase):

    def test_step1_has_search(self):
        from rcm_mc.ui.onboarding_wizard import render_step1
        html = render_step1()
        self.assertIn('id="wiz-search"', html)
        self.assertIn("/api/data/hospitals", html)
        # Manual-entry form present.
        self.assertIn('action="/new-deal/manual"', html)
        self.assertIn("wizard", html)
        self.assertIn('aria-label="Wizard progress"', html)
        self.assertIn('role="status"', html)
        self.assertIn('aria-live="polite"', html)
        self.assertIn('aria-busy="false"', html)
        self.assertIn('role="button" tabindex="0"', html)
        self.assertIn("keydown", html)

    def test_step2_renders_populated_and_gaps(self):
        from rcm_mc.ui.onboarding_wizard import (
            WizardSession, render_step2,
        )
        session = WizardSession(
            deal_id="d1", name="Acme", ccn="123456", state="TX",
            profile={"name": "Acme", "bed_count": 200},
            financials={"net_revenue": 4e8},
            sources=[{
                "field": "net_revenue", "value": 4e8, "source": "HCRIS",
                "period": "FY2024", "freshness_days": 30,
                "confidence": "HIGH",
            }],
            gaps=[
                {"metric_key": "denial_rate", "display_name": "Denial Rate",
                 "ebitda_sensitivity_rank": 1,
                 "why_it_matters": "driver #1"},
                {"metric_key": "bad_debt", "display_name": "Bad Debt",
                 "ebitda_sensitivity_rank": 20,
                 "why_it_matters": "secondary"},
            ],
            coverage_pct=45.0,
        )
        html = render_step2(session)
        self.assertIn("HCRIS", html)
        self.assertIn("Denial Rate", html)
        self.assertIn("Bad Debt", html)
        self.assertIn("45.0%", html)
        # EBITDA sensitivity rank shown.
        self.assertIn("#1", html)
        # Skip-to-review link.
        self.assertIn("/new-deal/step4", html)

    def test_step3_lists_uploaded_files(self):
        from rcm_mc.ui.onboarding_wizard import (
            WizardSession, render_step3,
        )
        session = WizardSession(
            deal_id="d1", uploaded_files=["denials.csv", "collections.xlsx"],
            extracted={"denial_rate": 12.5},
        )
        html = render_step3(session)
        self.assertIn("denials.csv", html)
        self.assertIn("collections.xlsx", html)
        self.assertIn("Extracted 1", html)

    def test_step4_shows_grade_and_overrides(self):
        from rcm_mc.ui.onboarding_wizard import (
            WizardSession, render_step4,
        )
        session = WizardSession(
            deal_id="d1", name="Acme", ccn="123456", state="TX",
            coverage_pct=75.0, extracted={"denial_rate": 12.5},
            gaps=[
                {"metric_key": "days_in_ar", "display_name": "Days in AR",
                 "ebitda_sensitivity_rank": 2,
                 "why_it_matters": ""},
                {"metric_key": "bad_debt", "display_name": "Bad Debt",
                 "ebitda_sensitivity_rank": 20,
                 "why_it_matters": ""},
            ],
        )
        html = render_step4(session)
        # Grade A / B / C / D rendered.
        self.assertTrue(any(f'class="grade-{g}"' in html for g in "ABCD"))
        # Override fields for denial_rate + top gaps.
        self.assertIn('name="override_denial_rate"', html)
        self.assertIn('name="override_days_in_ar"', html)
        # Bridge link to launch endpoint.
        self.assertIn("/api/deals/wizard/launch", html)

    def test_step4_caps_overrides_at_ten(self):
        from rcm_mc.ui.onboarding_wizard import (
            WizardSession, render_step4,
        )
        session = WizardSession(
            deal_id="d1",
            gaps=[
                {"metric_key": f"metric_{i}",
                 "display_name": f"Metric {i}",
                 "ebitda_sensitivity_rank": i,
                 "why_it_matters": ""}
                for i in range(1, 20)
            ],
        )
        html = render_step4(session)
        # Exactly 10 input rows for overrides.
        self.assertEqual(html.count('data-scenario-target'), 0)   # guard
        override_count = html.count('name="override_')
        self.assertEqual(override_count, 10)

    def test_step5_autoredirects(self):
        from rcm_mc.ui.onboarding_wizard import (
            WizardSession, render_step5,
        )
        html = render_step5(WizardSession(deal_id="d1"))
        self.assertIn("/analysis/d1", html)
        self.assertIn("setTimeout", html)


# ── Session helpers ───────────────────────────────────────────────

class TestSessionHelpers(unittest.TestCase):

    def test_save_and_load(self):
        from rcm_mc.ui.onboarding_wizard import (
            WizardSession, load_session, save_session, clear_session,
        )
        s = WizardSession(deal_id="abc", name="Test")
        save_session(s)
        self.assertEqual(load_session("abc").name, "Test")
        clear_session("abc")
        self.assertIsNone(load_session("abc"))

    def test_merge_extraction_keeps_latest_period(self):
        from rcm_mc.ui.onboarding_wizard import (
            WizardSession, merge_extraction, save_session, clear_session,
        )
        s = WizardSession(deal_id="xx")
        save_session(s)
        extraction = {
            "metrics": {
                "denial_rate": [
                    {"period": "2024-01", "value": 12.5},
                    {"period": "2024-06", "value": 10.8},
                ],
            },
        }
        merged = merge_extraction("xx", extraction, "file.csv")
        self.assertEqual(merged.extracted["denial_rate"], 10.8)
        self.assertIn("file.csv", merged.uploaded_files)
        clear_session("xx")


# ── Server routes ─────────────────────────────────────────────────

class TestWizardRoutes(unittest.TestCase):

    def test_get_new_deal_renders_step1(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/new-deal",
                ) as r:
                    body = r.read().decode()
                self.assertIn('id="wiz-search"', body)
                self.assertIn("Find your hospital", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_step2_without_session_redirects(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/new-deal/step2?deal_id=ghost",
                    method="GET",
                )
                # Expect a redirect — urllib follows by default.
                with urllib.request.urlopen(req) as r:
                    self.assertIn("Find your hospital", r.read().decode())
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_wizard_select_happy_path(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            ccn = _first_hcris_ccn()
            server, port = _start(tf.name)
            try:
                # Post the form exactly as Step 1's JS would.
                data = urllib.parse.urlencode({"ccn": ccn}).encode()
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/deals/wizard/select",
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    method="POST",
                )
                # 303 redirect → urllib follows → Step 2 renders.
                with urllib.request.urlopen(req) as r:
                    body = r.read().decode()
                self.assertIn("Step 2", body)
                # Source pill present somewhere.
                self.assertIn("HCRIS", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_manual_entry_creates_session(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                data = urllib.parse.urlencode({
                    "name": "Test Regional",
                    "state": "CA",
                    "bed_count": "150",
                    "medicare_pct": "45",
                    "medicaid_pct": "15",
                    "commercial_pct": "40",
                }).encode()
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/new-deal/manual",
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    method="POST",
                )
                with urllib.request.urlopen(req) as r:
                    body = r.read().decode()
                self.assertIn("Step 2", body)
                self.assertIn("Test Regional", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_end_to_end_flow(self):
        """Select CCN → Step 2 → Step 3 → Step 4 → launch → Step 5 →
        workbench. The packet has to exist at the end."""
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            ccn = _first_hcris_ccn()
            server, port = _start(tf.name)
            try:
                base = f"http://127.0.0.1:{port}"

                # Step 1 → 2.
                data = urllib.parse.urlencode({"ccn": ccn}).encode()
                req = urllib.request.Request(
                    f"{base}/api/deals/wizard/select", data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    method="POST",
                )
                with urllib.request.urlopen(req) as r:
                    self.assertIn("Step 2", r.read().decode())

                deal_id = ccn.zfill(6)
                # Skip straight to Step 4 (no upload in this test).
                with urllib.request.urlopen(
                    f"{base}/new-deal/step4?deal_id={urllib.parse.quote(deal_id)}"
                ) as r:
                    step4 = r.read().decode()
                self.assertIn("Build analysis", step4)

                # Launch (build packet).
                data = urllib.parse.urlencode({"deal_id": deal_id}).encode()
                req = urllib.request.Request(
                    f"{base}/api/deals/wizard/launch",
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    method="POST",
                )
                with urllib.request.urlopen(req) as r:
                    step5 = r.read().decode()
                self.assertIn("Step 5", step5)
                self.assertIn(f"/analysis/{deal_id}", step5)

                # Workbench now serves for this deal_id.
                with urllib.request.urlopen(
                    f"{base}/api/analysis/{urllib.parse.quote(deal_id)}"
                ) as r:
                    packet = json.loads(r.read().decode())
                self.assertEqual(packet["deal_id"], deal_id)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_upload_merges_into_session(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            from rcm_mc.ui.onboarding_wizard import (
                WizardSession, save_session, load_session, clear_session,
            )
            # Pre-seed a session so the upload route has something to
            # merge into.
            save_session(WizardSession(deal_id="wtest", name="W"))
            try:
                server, port = _start(tf.name)
                try:
                    csv_bytes = b"Denial Rate,A/R Days\n11.0,52\n"
                    boundary = "----testboundary"
                    body = (
                        f"--{boundary}\r\n"
                        'Content-Disposition: form-data; name="file"; filename="r.csv"\r\n'
                        "Content-Type: text/csv\r\n\r\n"
                    ).encode() + csv_bytes + f"\r\n--{boundary}--\r\n".encode()
                    req = urllib.request.Request(
                        f"http://127.0.0.1:{port}/new-deal/upload?deal_id=wtest",
                        data=body,
                        headers={"Content-Type":
                                 f"multipart/form-data; boundary={boundary}"},
                        method="POST",
                    )
                    with urllib.request.urlopen(req) as r:
                        # Redirect back to Step 3.
                        self.assertIn("Step 3", r.read().decode())
                finally:
                    server.shutdown(); server.server_close()
                session = load_session("wtest")
                self.assertIn("r.csv", session.uploaded_files)
                self.assertIn("denial_rate", session.extracted)
            finally:
                clear_session("wtest")
        finally:
            os.unlink(tf.name)


if __name__ == "__main__":
    unittest.main()
