import os
import tempfile
import unittest

import pandas as pd

from rcm_mc.core.calibration import calibrate_config
from rcm_mc.infra.config import load_and_validate, validate_config


class TestCalibration(unittest.TestCase):
    def test_calibration_updates_key_parameters_and_keeps_schema_valid(self):
        base_dir = os.path.dirname(os.path.dirname(__file__))
        actual = os.path.join(base_dir, "configs", "actual.yaml")
        cfg = load_and_validate(actual)

        prior_idr_medicare = float(cfg["payers"]["Medicare"]["denials"]["idr"]["mean"])
        prior_fwr_commercial = float(cfg["payers"]["Commercial"]["denials"]["fwr"]["mean"])

        with tempfile.TemporaryDirectory() as td:
            # claims_summary.csv
            claims = pd.DataFrame(
                {
                    "payer": ["Medicare", "Medicaid", "Commercial", "SelfPay"],
                    "net_revenue": [3_500_000, 2_000_000, 4_000_000, 500_000],
                    "claim_count": [200, 200, 200, 100],
                }
            )
            claims.to_csv(os.path.join(td, "claims_summary.csv"), index=False)

            # denials.csv (synthetic)
            rows = []
            claim_id = 1

            def add_rows(payer: str, n: int, denial_amt: float, wo_amt: float, stages, cats):
                nonlocal claim_id
                for i in range(n):
                    rows.append(
                        {
                            "payer": payer,
                            "claim_id": f"C{claim_id}",
                            "denial_amount": denial_amt,
                            "writeoff_amount": wo_amt,
                            "appeal_level": stages[i % len(stages)],
                            "denial_category": cats[i % len(cats)],
                            "days_to_resolve": 10 + (i % 20),
                        }
                    )
                    claim_id += 1

            # Medicare: IDR 0.15, FWR 0.20
            add_rows(
                payer="Medicare",
                n=30,
                denial_amt=17_500,
                wo_amt=3_500,
                stages=["L1"] * 20 + ["L2"] * 8 + ["L3"] * 2,
                cats=["clinical", "coding", "admin"],
            )

            # Medicaid: IDR 0.14, FWR 0.25
            add_rows(
                payer="Medicaid",
                n=28,
                denial_amt=10_000,
                wo_amt=2_500,
                stages=["L1"] * 20 + ["L2"] * 6 + ["L3"] * 2,
                cats=["eligibility", "coding", "clinical"],
            )

            # Commercial: IDR 0.20, FWR 0.10
            add_rows(
                payer="Commercial",
                n=40,
                denial_amt=20_000,
                wo_amt=2_000,
                stages=["L1"] * 25 + ["L2"] * 12 + ["L3"] * 3,
                cats=["auth_admin", "coding", "clinical"],
            )

            denials = pd.DataFrame(rows)
            denials.to_csv(os.path.join(td, "denials.csv"), index=False)

            # Run calibration
            new_cfg, report, _quality = calibrate_config(cfg, td)
            self.assertFalse(report.empty)

            # Medicare IDR should move upward (toward 0.15)
            new_idr_medicare = float(new_cfg["payers"]["Medicare"]["denials"]["idr"]["mean"])
            self.assertGreater(new_idr_medicare, prior_idr_medicare)

            # Commercial FWR should move downward (toward 0.10)
            new_fwr_commercial = float(new_cfg["payers"]["Commercial"]["denials"]["fwr"]["mean"])
            self.assertLess(new_fwr_commercial, prior_fwr_commercial)

            # Config should still validate
            validate_config(new_cfg)
