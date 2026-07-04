import unittest

from ..connector import CmsCoverageConnector
from ..endpoints import get_endpoint
from ..transport import CmsCoverageTransport
from .fakes import FakeCmsCoverage

_NCD_PATH = "/v1/reports/national-coverage-ncd"
_CONTRACTORS_PATH = "/v1/metadata/contractors"


def _connector(**kw):
    kw.setdefault("page_limit", 2)
    return CmsCoverageConnector(
        CmsCoverageTransport(min_interval_s=0.0), **kw)


def _national(n):
    return [{"document_id": 100 + i, "document_version": 1,
             "document_type": "NCD", "title": f"Doc {i}",
             "chapter": "240", "last_updated_sort": f"2024010{i}"}
            for i in range(n)]


class ConnectorTests(unittest.TestCase):
    def test_discover_lists_endpoints(self):
        keys = {s.key for s in _connector().discover()}
        self.assertIn("national_ncd", keys)
        self.assertIn("local_lcd", keys)
        self.assertIn("contractors", keys)

    def test_fetch_pages_through_next_page_token_and_stops(self):
        fake = FakeCmsCoverage(page_size=2).add(_NCD_PATH, _national(5))
        conn = _connector()
        spec = get_endpoint("national_ncd")

        rows, cursor, steps = [], None, 0
        while True:
            step = conn.fetch(spec, cursor=cursor, opener=fake)
            rows.extend(step.rows)
            steps += 1
            if step.next_cursor is None:
                break
            cursor = step.next_cursor
            self.assertIn("page_token", cursor)

        self.assertEqual(len(rows), 5)          # every record, no duplicates
        self.assertEqual(steps, 3)              # 2 + 2 + 1 pages
        self.assertEqual({r["document_id"] for r in rows},
                         {100, 101, 102, 103, 104})

    def test_fetch_all_convenience_drains_endpoint(self):
        fake = FakeCmsCoverage(page_size=2).add(_NCD_PATH, _national(3))
        conn = _connector()
        rows = conn.fetch_all(get_endpoint("national_ncd"), opener=fake)
        self.assertEqual(len(rows), 3)

    def test_contractors_single_fetch(self):
        contractors = [
            {"contractor_id": 236, "contractor_version": 2,
             "contractor_name": "CGS Administrators, LLC",
             "contract_number": "15004"},
            {"contractor_id": 240, "contractor_version": 1,
             "contractor_name": "Noridian", "contract_number": "01111"},
        ]
        fake = FakeCmsCoverage().add(_CONTRACTORS_PATH, contractors)
        conn = _connector()
        step = conn.fetch(get_endpoint("contractors"), opener=fake)
        self.assertIsNone(step.next_cursor)     # single-shot, no paging
        self.assertEqual(len(step.rows), 2)
        self.assertEqual(step.total, 2)
        self.assertEqual(len(fake.calls), 1)    # exactly one request


if __name__ == "__main__":
    unittest.main()
