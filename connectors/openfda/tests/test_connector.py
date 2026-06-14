import unittest

from .. import connector as C
from ..connector import OpenFdaConnector
from ..endpoints import get_endpoint
from ..transport import OpenFdaTransport
from .fakes import FakeFda


def _conn(page_limit=2):
    t = OpenFdaTransport(min_interval_s=0.0)
    return OpenFdaConnector(t, page_limit=page_limit,
                            backfill_start="20040101", sleep=lambda s: None)


def _drain(conn, spec, opener, params=None):
    rows, cursor = [], None
    for _ in range(2000):
        res = conn.fetch(spec, params or {}, cursor, opener=opener)
        rows.extend(res.rows)
        if res.next_cursor is None:
            return rows
        cursor = res.next_cursor
    raise AssertionError("did not terminate")


class WindowPagingTests(unittest.TestCase):
    def test_windowed_endpoint_drains_all_rows(self):
        recs = [{"safetyreportid": str(i), "receivedate": f"200401{i:02d}",
                 "patient": {"reaction": [{"reactionmeddrapt": "nausea"}]}}
                for i in range(1, 21)]
        fake = FakeFda().add("/drug/event.json", recs)
        spec = get_endpoint("drug_event")
        conn = _conn(page_limit=5)
        got = _drain(conn, spec, fake)
        ids = sorted(int(r["safetyreportid"]) for r in got)
        self.assertEqual(ids, list(range(1, 21)))

    def test_adaptive_window_shrink_under_skip_cap(self):
        # Force a tiny cap so a default 30-day window overflows and must halve.
        orig = C.SAFE_SKIP_CAP
        C.SAFE_SKIP_CAP = 3
        try:
            recs = [{"safetyreportid": str(i), "receivedate": f"200401{i:02d}"}
                    for i in range(1, 11)]  # 10 across 10 distinct days
            fake = FakeFda().add("/drug/event.json", recs)
            spec = get_endpoint("drug_event")
            conn = _conn(page_limit=2)
            got = _drain(conn, spec, fake)
            self.assertEqual(sorted(int(r["safetyreportid"]) for r in got),
                             list(range(1, 11)))
        finally:
            C.SAFE_SKIP_CAP = orig


class SkipPagingTests(unittest.TestCase):
    def test_skip_mode_drains_non_dated_endpoint(self):
        recs = [{"product_ndc": f"000{i}-1200", "dosage_form": "TABLET"}
                for i in range(7)]
        fake = FakeFda().add("/drug/ndc.json", recs)
        spec = get_endpoint("drug_ndc")
        conn = _conn(page_limit=3)
        got = _drain(conn, spec, fake)
        self.assertEqual(len(got), 7)

    def test_skip_cap_falls_back_to_partition(self):
        orig = C.SAFE_SKIP_CAP
        C.SAFE_SKIP_CAP = 4
        try:
            recs = ([{"product_ndc": f"a{i}", "dosage_form": "TABLET"} for i in range(6)]
                    + [{"product_ndc": f"b{i}", "dosage_form": "CAPSULE"} for i in range(3)])
            fake = FakeFda().add("/drug/ndc.json", recs)
            spec = get_endpoint("drug_ndc")
            conn = _conn(page_limit=2)
            got = _drain(conn, spec, fake)
            # Partition by dosage_form drains both buckets despite the cap.
            self.assertGreaterEqual(len(got), 6)
            forms = {r["dosage_form"] for r in got}
            self.assertEqual(forms, {"TABLET", "CAPSULE"})
        finally:
            C.SAFE_SKIP_CAP = orig


class AggregateTests(unittest.TestCase):
    def test_count_aggregate_and_total(self):
        recs = ([{"product_ndc": str(i), "dosage_form": "TABLET"} for i in range(4)]
                + [{"product_ndc": str(i), "dosage_form": "CREAM"} for i in range(2)])
        fake = FakeFda().add("/drug/ndc.json", recs)
        spec = get_endpoint("drug_ndc")
        conn = _conn()
        agg = conn.count_aggregate(spec, "dosage_form", opener=fake)
        terms = {r["term"]: r["count"] for r in agg}
        self.assertEqual(terms["TABLET"], 4)
        self.assertEqual(conn.total_count(spec, opener=fake), 6)


if __name__ == "__main__":
    unittest.main()
