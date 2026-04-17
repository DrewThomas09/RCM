"""Tests for the Seller Data Room."""
from __future__ import annotations

import os
import socket
import sqlite3
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request


class TestDataRoomStorage(unittest.TestCase):

    def setUp(self):
        self.tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tf.close()
        self.con = sqlite3.connect(self.tf.name)

    def tearDown(self):
        self.con.close()
        os.unlink(self.tf.name)

    def test_save_entry(self):
        from rcm_mc.data.data_room import save_entry, get_entries
        eid = save_entry(self.con, "010001", "denial_rate", 0.093,
                         sample_size=500, source="Seller Q4", analyst="AT")
        self.con.commit()
        self.assertIsInstance(eid, int)
        entries = get_entries(self.con, "010001")
        self.assertEqual(len(entries), 1)
        self.assertAlmostEqual(entries[0].value, 0.093)

    def test_supersedes_old_entry(self):
        from rcm_mc.data.data_room import save_entry, get_entries
        save_entry(self.con, "010001", "denial_rate", 0.12)
        save_entry(self.con, "010001", "denial_rate", 0.093)
        self.con.commit()
        entries = get_entries(self.con, "010001")
        self.assertEqual(len(entries), 1)
        self.assertAlmostEqual(entries[0].value, 0.093)

    def test_multiple_metrics(self):
        from rcm_mc.data.data_room import save_entry, get_latest_values
        save_entry(self.con, "010001", "denial_rate", 0.093)
        save_entry(self.con, "010001", "days_in_ar", 45)
        save_entry(self.con, "010001", "clean_claim_rate", 0.94)
        self.con.commit()
        latest = get_latest_values(self.con, "010001")
        self.assertEqual(len(latest), 3)
        self.assertIn("denial_rate", latest)
        self.assertIn("days_in_ar", latest)

    def test_calibration(self):
        from rcm_mc.data.data_room import save_entry, calibrate_metrics
        save_entry(self.con, "010001", "denial_rate", 0.093, sample_size=500)
        self.con.commit()
        ml_preds = {"denial_rate": 0.11, "days_in_ar": 45}
        cals = calibrate_metrics(self.con, "010001", ml_preds, beds=200)
        self.con.commit()
        self.assertGreater(len(cals), 0)
        denial_cal = next((c for c in cals if c.metric == "denial_rate"), None)
        self.assertIsNotNone(denial_cal)
        # With strong seller data (n=500), posterior should be close to seller
        self.assertAlmostEqual(denial_cal.bayesian_posterior, 0.093, delta=0.02)
        self.assertEqual(denial_cal.data_quality, "strong")

    def test_calibration_ml_only(self):
        from rcm_mc.data.data_room import calibrate_metrics
        ml_preds = {"denial_rate": 0.11}
        cals = calibrate_metrics(self.con, "010001", ml_preds, beds=200)
        self.con.commit()
        denial_cal = next((c for c in cals if c.metric == "denial_rate"), None)
        self.assertIsNotNone(denial_cal)
        self.assertEqual(denial_cal.data_quality, "ml_only")

    def test_get_calibrated_profile(self):
        from rcm_mc.data.data_room import save_entry, get_calibrated_profile
        save_entry(self.con, "010001", "denial_rate", 0.08, sample_size=200)
        self.con.commit()
        profile = get_calibrated_profile(self.con, "010001",
                                          {"denial_rate": 0.10}, beds=200)
        self.assertIn("denial_rate", profile)
        self.assertIn("_n_seller_metrics", profile)
        self.assertEqual(profile["_n_seller_metrics"], 1)


class TestDataRoomServer(unittest.TestCase):

    def _start(self, db_path):
        from rcm_mc.server import build_server
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        server, _ = build_server(port=port, db_path=db_path)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        time.sleep(0.05)
        return server, port

    def test_data_room_renders(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = self._start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/data-room/010001"
                ) as r:
                    body = r.read().decode()
                self.assertIn("Data Room", body)
                self.assertIn("Enter Seller Data", body)
                self.assertIn("SeekingChartis", body)
            finally:
                server.shutdown()
                server.server_close()
        finally:
            os.unlink(tf.name)

    def test_add_data_point(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = self._start(tf.name)
            try:
                # POST data point
                data = urllib.parse.urlencode({
                    "metric": "denial_rate",
                    "value": "0.093",
                    "sample_size": "500",
                    "source": "Test",
                    "analyst": "AT",
                }).encode()
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/data-room/010001/add",
                    data=data, method="POST",
                )
                try:
                    urllib.request.urlopen(req)
                except urllib.error.HTTPError as e:
                    self.assertEqual(e.code, 302)

                # Verify data shows up
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/data-room/010001"
                ) as r:
                    body = r.read().decode()
                self.assertIn("CONFIRMED", body)
                self.assertIn("Entry History", body)
            finally:
                server.shutdown()
                server.server_close()
        finally:
            os.unlink(tf.name)


if __name__ == "__main__":
    unittest.main()
