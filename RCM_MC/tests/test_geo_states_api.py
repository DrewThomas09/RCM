"""Geo states JSON API (/api/geo/states[/<STATE>]): exposes the shared real
metric layer programmatically. Guards payload shape, real values + null (never
fabricated) for missing, single-state filtering, and the HTTP endpoint.
"""
import json
import os
import socket
import tempfile
import threading
import unittest
import urllib.request

from rcm_mc.ui.data_public.state_compare_page import _METRICS, _VALID, geo_states_payload


def _free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close()
    return p


class GeoStatesPayloadTests(unittest.TestCase):
    def test_full_payload_shape(self):
        p = geo_states_payload()
        self.assertEqual(p["jurisdictions"], len(_VALID))
        self.assertEqual(len(p["metrics"]), len(_METRICS))
        self.assertEqual(set(p["states"]), set(_VALID))
        # every metric meta has a direction tag
        self.assertTrue(all(m["direction"] in ("higher_better", "lower_better", "neutral")
                            for m in p["metrics"]))
        # CA population is a real number; a missing metric is null, not faked
        ca = p["states"]["CA"]
        self.assertGreater(ca["population"], 30_000_000)
        for v in ca.values():
            self.assertTrue(v is None or isinstance(v, (int, float)))

    def test_single_state_filter(self):
        p = geo_states_payload("tx")
        self.assertEqual(set(p["states"]), {"TX"})
        # invalid → full set (never errors, never fabricates)
        self.assertEqual(set(geo_states_payload("ZZ")["states"]), set(_VALID))

    def test_json_serializable(self):
        json.dumps(geo_states_payload("CA"))  # must not raise


class GeoStatesApiHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.port = _free_port()
        from rcm_mc.server import build_server
        cls.server, _ = build_server(port=cls.port, host="127.0.0.1",
                                     db_path=os.path.join(cls.tmp.name, "t.db"), auth=None)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close()
        cls.thread.join(timeout=5); cls.tmp.cleanup()

    def _get(self, path):
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=10) as r:
            return r.status, r.headers.get("Content-Type", ""), json.loads(r.read())

    def test_endpoints(self):
        status, ctype, body = self._get("/api/geo/states")
        self.assertEqual(status, 200)
        self.assertIn("json", ctype)
        self.assertEqual(len(body["states"]), len(_VALID))
        s2, _c2, b2 = self._get("/api/geo/states/CA")
        self.assertEqual(s2, 200)
        self.assertEqual(set(b2["states"]), {"CA"})


if __name__ == "__main__":
    unittest.main()
