"""HRSA Primary-Care HPSA state index — loader (public, no runtime network)."""
import inspect, unittest
from rcm_mc.data import hrsa_data as h


class TestHrsa(unittest.TestCase):
    def test_loads(self):
        df = h.load_hpsa_by_state()
        self.assertGreaterEqual(len(df), 50)
        for c in ("state", "designated_pc_hpsas", "median_hpsa_score"):
            self.assertIn(c, df.columns)

    def test_summary_and_state(self):
        s = h.hpsa_summary()
        self.assertGreater(s["total_designated"], 1000)
        self.assertTrue(s["snapshot_date"])
        ca = h.hpsa_state("CA")
        self.assertGreater(ca.get("designated_pc_hpsas", 0), 0)

    def test_top_states_ranked(self):
        top = h.top_shortage_states(5)
        vals = [t["designated_pc_hpsas"] for t in top]
        self.assertEqual(vals, sorted(vals, reverse=True))

    def test_no_runtime_network(self):
        src = inspect.getsource(h)
        self.assertNotIn("urllib", src); self.assertNotIn("requests", src)

    def test_registry(self):
        self.assertTrue(h.hpsa_sources())


if __name__ == "__main__":
    unittest.main()
