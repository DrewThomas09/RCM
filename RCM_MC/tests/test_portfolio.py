import os
import tempfile
import unittest
import pandas as pd

from rcm_mc.infra.config import load_and_validate
from rcm_mc.portfolio.store import PortfolioStore


class TestPortfolioStore(unittest.TestCase):
    def test_store_init_add_export(self):
        base_dir = os.path.dirname(os.path.dirname(__file__))
        cfg_path = os.path.join(base_dir, "configs", "actual.yaml")
        cfg = load_and_validate(cfg_path)

        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "portfolio.sqlite")
            store = PortfolioStore(db_path)
            store.init_db()

            summary_df = pd.DataFrame(
                {"mean": [1.0], "median": [1.0], "p10": [0.5], "p90": [1.5]},
                index=["ebitda_drag"],
            )

            run_id = store.add_run(
                deal_id="DEAL_001",
                scenario="actual",
                cfg=cfg,
                summary_df=summary_df,
                notes="unit test",
            )
            self.assertTrue(run_id > 0)

            deals = store.list_deals()
            self.assertIn("DEAL_001", set(deals["deal_id"]))

            priors_out = os.path.join(tmp, "priors.yaml")
            priors = store.export_priors(priors_out)
            self.assertTrue(os.path.exists(priors_out))
            self.assertIn("payers", priors)
