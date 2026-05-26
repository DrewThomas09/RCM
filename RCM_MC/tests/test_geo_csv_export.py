"""CSV export for the Geographic Intelligence trio. Guards that each export
builds a real, non-empty DataFrame with the expected columns, that values are
raw (computable) numbers or blank (never fabricated), and that the .csv routes
stream a real download over HTTP.
"""
import os
import socket
import tempfile
import threading
import unittest
import urllib.request

from rcm_mc.ui.data_public.state_compare_page import compare_dataframe
from rcm_mc.ui.data_public.state_peers_page import peers_dataframe
from rcm_mc.ui.data_public.state_profile_page import profile_dataframe
from rcm_mc.ui.data_public.state_rankings_page import rankings_dataframe


def _free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close()
    return p


class GeoCsvDataFrameTests(unittest.TestCase):
    def test_compare_dataframe_shape(self):
        df = compare_dataframe(["CA", "TX"])
        self.assertEqual(list(df.columns)[:2], ["Metric", "Source"])
        self.assertIn("CA", df.columns)
        self.assertIn("TX", df.columns)
        self.assertEqual(len(df), 19)  # 19 metrics
        # CA population cell is a real number, not a formatted string
        pop = df.loc[df["Metric"] == "Population", "CA"].iloc[0]
        self.assertIsInstance(pop, (int, float))

    def test_rankings_dataframe_sorted_and_real(self):
        df = rankings_dataframe("population")
        self.assertEqual(list(df.columns), ["Rank", "State", "Population", "Source"])
        self.assertEqual(df.iloc[0]["State"], "CA")  # most populous
        self.assertEqual(df.iloc[0]["Rank"], 1)

    def test_peers_dataframe_sorted(self):
        df = peers_dataframe("OH")
        self.assertEqual(list(df.columns), ["Rank", "State", "Name", "Distance", "SharedMetrics"])
        self.assertNotIn("OH", list(df["State"]))  # target excluded
        dists = list(df["Distance"])
        self.assertEqual(dists, sorted(dists))  # closest-first

    def test_profile_dataframe_has_rank(self):
        df = profile_dataframe("CA")
        self.assertEqual(list(df.columns),
                         ["Metric", "Value", "VsUSMedianPct", "NationalRank", "Of", "Source"])
        self.assertEqual(len(df), 19)
        pop_rank = df.loc[df["Metric"] == "Population", "NationalRank"].iloc[0]
        self.assertEqual(pop_rank, 1)


class GeoCsvRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = os.path.join(cls.tmp.name, "t.db")
        cls.port = _free_port()
        from rcm_mc.server import build_server
        cls.server, _ = build_server(port=cls.port, host="127.0.0.1",
                                     db_path=cls.db, auth=None)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close()
        cls.thread.join(timeout=5); cls.tmp.cleanup()

    def _get(self, path):
        with urllib.request.urlopen(
            f"http://127.0.0.1:{self.port}{path}", timeout=10) as r:
            return r.status, r.headers.get("Content-Type", ""), r.read().decode()

    def test_csv_routes_stream_download(self):
        for path, needle in (
            ("/state-compare.csv?states=CA,TX", "Metric,Source,CA,TX"),
            ("/state-rankings.csv?metric=population", "Rank,State,Population,Source"),
            ("/state-profile.csv?state=CA", "Metric,Value,VsUSMedianPct,NationalRank,Of,Source"),
            ("/state-peers.csv?state=OH", "Rank,State,Name,Distance,SharedMetrics"),
        ):
            status, ctype, body = self._get(path)
            self.assertEqual(status, 200, path)
            self.assertIn("text/csv", ctype, path)
            self.assertIn(needle, body.splitlines()[0], path)
            self.assertGreater(len(body.splitlines()), 2, path)


if __name__ == "__main__":
    unittest.main()
