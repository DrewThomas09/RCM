"""
Tests for diligence requests mapping.
"""
from __future__ import annotations

import unittest

import pandas as pd

from rcm_mc.infra.diligence_requests import build_diligence_requests


class TestDiligenceRequests(unittest.TestCase):
    def test_build_diligence_requests(self):
        sens = pd.DataFrame([
            {"driver": "fwr_Commercial", "driver_label": "Final write-off rate (Commercial)", "corr": 0.72},
            {"driver": "idr_Medicare", "driver_label": "Initial denial rate (Medicare)", "corr": 0.45},
            {"driver": "upr_Commercial", "driver_label": "Underpayment rate (Commercial)", "corr": 0.38},
        ])
        rows = build_diligence_requests(sens, top_n=3)
        self.assertEqual(len(rows), 3)
        self.assertIn("diligence_request", rows[0])
        self.assertIn("835", rows[0]["diligence_request"])

    def test_empty_sensitivity(self):
        rows = build_diligence_requests(None, top_n=3)
        self.assertEqual(rows, [])
        rows = build_diligence_requests(pd.DataFrame(), top_n=3)
        self.assertEqual(rows, [])
