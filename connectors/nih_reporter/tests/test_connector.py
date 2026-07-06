import unittest

from ..connector import NihReporterConnector
from ..endpoints import OFFSET_CAP, get_endpoint
from ..tables import NihReporterStore
from ..transport import NihReporterTransport
from .fakes import (FakeNihReporter, PROJECTS_PATH, PUBLICATIONS_PATH,
                    project_record, publication_record)


def _connector(**kw):
    kw.setdefault("page_limit", 2)
    return NihReporterConnector(
        NihReporterTransport(min_interval_s=0.0), **kw)


def _projects(n, start=100):
    return [project_record(appl_id=start + i,
                           project_num=f"5R01GM{start + i:06d}-01",
                           core_project_num=f"R01GM{start + i:06d}")
            for i in range(n)]


class ConnectorTests(unittest.TestCase):
    def test_discover_lists_endpoints(self):
        keys = {s.key for s in _connector().discover()}
        self.assertEqual(keys, {"projects", "publications"})

    def test_fetch_pages_by_offset_and_stops(self):
        fake = FakeNihReporter().add(PROJECTS_PATH, _projects(5))
        conn = _connector()
        spec = get_endpoint("projects")

        rows, cursor, steps = [], None, 0
        while True:
            step = conn.fetch(spec, {"fiscal_years": [2025]}, cursor,
                              opener=fake)
            rows.extend(step.rows)
            steps += 1
            if step.next_cursor is None:
                break
            cursor = step.next_cursor
            self.assertIn("offset", cursor)

        self.assertEqual(len(rows), 5)          # every record, no duplicates
        self.assertEqual(steps, 3)              # 2 + 2 + 1 pages
        self.assertEqual({r["appl_id"] for r in rows},
                         {100, 101, 102, 103, 104})
        # Native paging stayed in the POST body, absorbed from callers.
        offsets = [body["offset"] for _, body in fake.calls]
        self.assertEqual(offsets, [0, 2, 4])
        self.assertTrue(all(body["criteria"] == {"fiscal_years": [2025]}
                            for _, body in fake.calls))

    def test_fetch_all_caps_pages(self):
        # 10 records at page size 2 → max_pages=2 stops after 4 rows.
        fake = FakeNihReporter().add(PROJECTS_PATH, _projects(10))
        conn = _connector()
        rows = conn.fetch_all(get_endpoint("projects"), opener=fake,
                              max_pages=2)
        self.assertEqual(len(rows), 4)
        self.assertEqual(len(fake.calls), 2)

    def test_fetch_all_drains_when_under_cap(self):
        fake = FakeNihReporter().add(PROJECTS_PATH, _projects(3))
        conn = _connector()
        rows = conn.fetch_all(get_endpoint("projects"), opener=fake)
        self.assertEqual(len(rows), 3)

    def test_offset_ceiling_marks_truncated(self):
        # Simulate a result set deeper than the API's reachable window:
        # cursor at the cap boundary, full page returned, more remaining.
        fake = FakeNihReporter().add(PROJECTS_PATH, _projects(10))
        conn = _connector()
        spec = get_endpoint("projects")
        step = conn.fetch(spec, None, {"offset": 4}, opener=fake)
        self.assertIsNotNone(step.next_cursor)   # normal continuation
        self.assertFalse(step.truncated)

        # Force the boundary: page ends exactly past the cap.
        big = FakeNihReporter()
        big.records[PROJECTS_PATH] = _projects(10)

        def opener(url, data, headers, timeout):
            import json as _json
            from ..transport import RawResponse
            body = _json.loads(data)
            page = [project_record(appl_id=1)] * body["limit"]
            return RawResponse(status=200, body=_json.dumps({
                "meta": {"total": 50_000, "offset": body["offset"],
                         "limit": body["limit"]},
                "results": page,
            }).encode())

        step = conn.fetch(spec, None, {"offset": OFFSET_CAP - 1},
                          opener=opener)
        # next offset would be 15,000 > cap → stop + truncated.
        self.assertIsNone(step.next_cursor)
        self.assertTrue(step.truncated)
        self.assertEqual(step.total, 50_000)

    def test_publications_fetch(self):
        pubs = [publication_record(pmid=1000 + i) for i in range(3)]
        fake = FakeNihReporter().add(PUBLICATIONS_PATH, pubs)
        conn = _connector(page_limit=500)
        step = conn.fetch(get_endpoint("publications"),
                          {"core_project_nums": ["R37GM070977"]}, opener=fake)
        self.assertIsNone(step.next_cursor)
        self.assertEqual(len(step.rows), 3)
        self.assertEqual(step.total, 3)
        self.assertEqual(len(fake.calls), 1)

    def test_page_limit_clamped_to_api_max(self):
        conn = NihReporterConnector(
            NihReporterTransport(min_interval_s=0.0), page_limit=9999)
        self.assertEqual(conn.page_limit, 500)

    def test_refresh_fetches_normalizes_and_upserts(self):
        fake = FakeNihReporter().add(PROJECTS_PATH, _projects(5))
        conn = _connector()
        store = NihReporterStore(":memory:")
        result = conn.refresh(store, "projects",
                              {"fiscal_years": [2025]}, opener=fake)
        self.assertEqual(result["fetched"], 5)
        self.assertEqual(result["upserted"], {"nih_projects": 5})
        self.assertEqual(result["dataset_id"], "nih_reporter_projects")
        self.assertFalse(result["truncated"])
        self.assertEqual(store.count("nih_projects"), 5)
        # Idempotent: refreshing the same slice never double-counts.
        conn.refresh(store, "projects", {"fiscal_years": [2025]},
                     opener=FakeNihReporter().add(PROJECTS_PATH, _projects(5)))
        self.assertEqual(store.count("nih_projects"), 5)
        store.close()

    def test_project_criteria_builder_shapes(self):
        crit = NihReporterConnector.project_criteria(
            fiscal_years=2025, org_states="tx", org_names="MD ANDERSON",
            pi_names="Aballay", activity_codes=["r01", "R37"],
            advanced_text_search="oncology")
        self.assertEqual(crit["fiscal_years"], [2025])
        self.assertEqual(crit["org_states"], ["TX"])
        self.assertEqual(crit["org_names"], ["MD ANDERSON"])
        self.assertEqual(crit["pi_names"], [{"any_name": "Aballay"}])
        self.assertEqual(crit["activity_codes"], ["R01", "R37"])
        self.assertEqual(crit["advanced_text_search"]["search_text"],
                         "oncology")
        self.assertEqual(crit["advanced_text_search"]["operator"], "and")

    def test_publication_criteria_builder_shapes(self):
        crit = NihReporterConnector.publication_criteria(
            core_project_nums="R37GM070977", appl_ids="11184227",
            pmids=[23959030])
        self.assertEqual(crit["core_project_nums"], ["R37GM070977"])
        self.assertEqual(crit["appl_ids"], [11184227])
        self.assertEqual(crit["pmids"], [23959030])


if __name__ == "__main__":
    unittest.main()
