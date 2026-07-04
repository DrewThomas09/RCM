import unittest

from ..connector import Icd10Connector
from ..endpoints import get_endpoint
from ..transport import NlmTransport
from .fakes import FakeNlm

_CM = "/icd10cm/v3/search"
_PCS = "/icd10pcs/v3/search"


def _conn(page_limit=2):
    t = NlmTransport(min_interval_s=0.0)
    return Icd10Connector(t, page_limit=page_limit, sleep=lambda s: None)


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
        # Five CM codes under the "E" prefix; page_limit=2 forces 3 offsets.
        recs = [{"code": f"E11.{i}", "name": f"diabetes {i}"} for i in range(5)]
        fake = FakeNlm().add(_CM, recs)
        spec = get_endpoint("cm")
        conn = _conn(page_limit=2)
        got = _drain(conn, spec, fake)
        codes = sorted(r["code"] for r in got)
        self.assertEqual(codes, [f"E11.{i}" for i in range(5)])
        # The "E" seed paged by offset: at least 3 requests hit /icd10cm.
        e_calls = [c for c in fake.calls if "code%3AE%2A" in c or "code:E*" in c]
        self.assertGreaterEqual(len(e_calls), 3)

    def test_variable_df_width_is_handled(self):
        # One record carries long_name, one does not; CM df asks for 3 cols.
        recs = [
            {"code": "E11.9", "name": "T2DM", "long_name": "Type 2 diabetes mellitus"},
            {"code": "E11.65", "name": "T2DM w/ hyperglycemia"},  # no long_name
        ]
        fake = FakeNlm().add(_CM, recs)
        spec = get_endpoint("cm")
        conn = _conn(page_limit=5)
        got = {r["code"]: r for r in _drain(conn, spec, fake)}
        # Wide row keeps long_name; narrow row simply omits it (no crash).
        self.assertEqual(got["E11.9"].get("long_name"), "Type 2 diabetes mellitus")
        self.assertNotIn("long_name", got["E11.65"])
        self.assertEqual(got["E11.65"]["code_type"], "cm")

    def test_pcs_endpoint_drains(self):
        recs = [{"code": f"0DT{i}0ZZ", "name": f"resection {i}"} for i in range(3)]
        fake = FakeNlm().add(_PCS, recs)
        spec = get_endpoint("pcs")
        conn = _conn(page_limit=2)
        got = _drain(conn, spec, fake)
        self.assertEqual(len(got), 3)
        self.assertTrue(all(r["code_type"] == "pcs" for r in got))

    def test_caller_supplied_q_collapses_to_single_pass(self):
        recs = [{"code": "E11.9", "name": "T2DM"},
                {"code": "A00.0", "name": "cholera"}]
        fake = FakeNlm().add(_CM, recs)
        spec = get_endpoint("cm")
        conn = _conn(page_limit=10)
        got = _drain(conn, spec, fake, params={"q": "code:E11*"})
        self.assertEqual([r["code"] for r in got], ["E11.9"])
        # Only the single caller query was issued — no A–Z seed sweep.
        self.assertEqual(len(fake.calls), 1)

    def test_total_count(self):
        recs = [{"code": f"E11.{i}", "name": "x"} for i in range(4)]
        fake = FakeNlm().add(_CM, recs)
        spec = get_endpoint("cm")
        conn = _conn()
        self.assertEqual(conn.total_count(spec, q="code:E*", opener=fake), 4)


if __name__ == "__main__":
    unittest.main()
