import unittest

from ..connector import HcpcsConnector
from ..endpoints import get_endpoint
from ..transport import NlmTransport
from .fakes import FakeNlm

_HCPCS = "/hcpcs/v3/search"


def _conn(page_limit=2):
    t = NlmTransport(min_interval_s=0.0)
    return HcpcsConnector(t, page_limit=page_limit, sleep=lambda s: None)


def _drain(conn, spec, opener, params=None):
    rows, cursor = [], None
    for _ in range(5000):
        res = conn.fetch(spec, params or {}, cursor, opener=opener)
        rows.extend(res.rows)
        if res.next_cursor is None:
            return rows
        cursor = res.next_cursor
    raise AssertionError("did not terminate")


class SeedPagingTests(unittest.TestCase):
    def test_seed_prefixes_page_by_offset_and_stop_at_total(self):
        # Five J-codes under the "J" prefix; page_limit=2 forces 3 offsets.
        recs = [{"code": f"J927{i}", "display": f"drug {i}"} for i in range(5)]
        fake = FakeNlm().add(_HCPCS, recs)
        spec = get_endpoint("lvl2")
        conn = _conn(page_limit=2)
        got = _drain(conn, spec, fake)
        codes = sorted(r["code"] for r in got)
        self.assertEqual(codes, [f"J927{i}" for i in range(5)])
        # The "J" seed paged by offset: at least 3 requests hit /hcpcs.
        j_calls = [c for c in fake.calls if "code%3AJ%2A" in c or "code:J*" in c]
        self.assertGreaterEqual(len(j_calls), 3)

    def test_variable_df_width_is_handled(self):
        # One record carries long_desc, one does not; df asks for 5 cols.
        recs = [
            {"code": "E0601", "display": "CPAP device",
             "short_desc": "CPAP device",
             "long_desc": "Continuous positive airway pressure device"},
            {"code": "E0470", "display": "RAD w/o backup"},  # narrow row
        ]
        fake = FakeNlm().add(_HCPCS, recs)
        spec = get_endpoint("lvl2")
        conn = _conn(page_limit=5)
        got = {r["code"]: r for r in _drain(conn, spec, fake)}
        # Wide row keeps long_desc; narrow row simply omits it (no crash).
        self.assertTrue(got["E0601"]["long_desc"].startswith("Continuous"))
        self.assertNotIn("long_desc", got["E0470"])
        self.assertEqual(got["E0470"]["code_type"], "lvl2")

    def test_caller_supplied_q_collapses_to_single_pass(self):
        recs = [{"code": "J9271", "display": "pembrolizumab"},
                {"code": "A0428", "display": "ambulance service"}]
        fake = FakeNlm().add(_HCPCS, recs)
        spec = get_endpoint("lvl2")
        conn = _conn(page_limit=10)
        got = _drain(conn, spec, fake, params={"q": "code:J92*"})
        self.assertEqual([r["code"] for r in got], ["J9271"])
        # Only the single caller query was issued — no A–V seed sweep.
        self.assertEqual(len(fake.calls), 1)

    def test_total_count(self):
        recs = [{"code": f"L300{i}", "display": "orthotic"} for i in range(4)]
        fake = FakeNlm().add(_HCPCS, recs)
        spec = get_endpoint("lvl2")
        conn = _conn()
        self.assertEqual(conn.total_count(spec, q="code:L*", opener=fake), 4)


if __name__ == "__main__":
    unittest.main()
