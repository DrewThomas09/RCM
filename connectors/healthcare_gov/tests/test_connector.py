import unittest

from ..connector import HealthcareGovConnector
from ..endpoints import get_endpoint
from ..tables import HealthcareGovStore
from ..transport import HealthcareGovTransport
from .fakes import (
    CATALOG_ITEMS,
    FakeHealthcareGov,
    PLAN_ATTRIBUTES_ROWS,
    RATES_ROWS,
)

_PLAN_ATTRS_ID = get_endpoint("plan_attributes_py2026").identifier
_RATES_ID = get_endpoint("rate_puf_py2026").identifier


def _connector(**kw):
    return HealthcareGovConnector(
        HealthcareGovTransport(min_interval_s=0.0), **kw)


def _rates(n):
    """n distinct rate cells (distinct age bands) in the live shape."""
    out = []
    for i in range(n):
        row = dict(RATES_ROWS[0])
        row["age"] = str(15 + i)
        row["individualrate"] = str(65.0 + i)
        out.append(row)
    return out


class ConnectorTests(unittest.TestCase):
    def test_endpoints_enumerates_specs(self):
        keys = {s.key for s in _connector().endpoints()}
        self.assertIn("catalog", keys)
        self.assertIn("plan_attributes_py2026", keys)
        self.assertIn("rate_puf_py2026", keys)
        self.assertIn("fetched_rows", keys)

    def test_discover_returns_normalized_catalog_rows(self):
        fake = FakeHealthcareGov().add_catalog(CATALOG_ITEMS)
        rows = _connector().discover(opener=fake)
        # 3 items, 1 without identifier → skipped by the normalizer.
        self.assertEqual(len(rows), 2)
        ids = {r["identifier"] for r in rows}
        self.assertIn("ca253298-c4ef-4a77-9c44-0de0bbe91941", ids)
        self.assertTrue(all(r["source_endpoint"] == "catalog" for r in rows))

    def test_fetch_absorbs_limit_offset_paging_and_stops(self):
        fake = FakeHealthcareGov().add_datastore(_RATES_ID, _rates(5))
        conn = _connector()
        step = conn.fetch("rate_puf_py2026", opener=fake, page_size=2)
        self.assertEqual(len(step.rows), 5)          # every record, no dupes
        self.assertEqual(step.pages, 3)              # 2 + 2 + 1 (short page)
        self.assertTrue(step.exhausted)
        self.assertEqual(step.total, 5)
        self.assertEqual({r["age"] for r in step.rows},
                         {"15", "16", "17", "18", "19"})

    def test_fetch_max_pages_caps_and_resume_drains(self):
        fake = FakeHealthcareGov().add_datastore(_RATES_ID, _rates(5))
        conn = _connector()
        step = conn.fetch("rate_puf_py2026", opener=fake, page_size=2,
                          max_pages=2)
        self.assertEqual(len(step.rows), 4)          # capped at 2 pages
        self.assertFalse(step.exhausted)
        self.assertEqual(step.next_offset, 4)
        # Resume where the capped call stopped.
        rest = conn.fetch("rate_puf_py2026", opener=fake, page_size=2,
                          start_offset=step.next_offset)
        self.assertEqual(len(rest.rows), 1)
        self.assertTrue(rest.exhausted)

    def test_fetch_filters_compile_to_dkan_conditions(self):
        fake = FakeHealthcareGov().add_datastore(
            _PLAN_ATTRS_ID, PLAN_ATTRIBUTES_ROWS)
        conn = _connector()
        step = conn.fetch("plan_attributes_py2026", {"statecode": "TX"},
                          opener=fake)
        self.assertEqual(len(step.rows), 1)          # fake filtered like live
        self.assertEqual(step.rows[0]["planid"], "33602TX0450002-04")
        self.assertIn("conditions%5B0%5D%5Bproperty%5D=statecode",
                      fake.calls[0])

    def test_fetch_requests_row_ids(self):
        fake = FakeHealthcareGov().add_datastore(_RATES_ID, _rates(1))
        step = _connector().fetch("rate_puf_py2026", opener=fake)
        self.assertIn("record_number", step.rows[0])

    def test_fetch_generic_placeholder_key_raises(self):
        with self.assertRaises(ValueError):
            _connector().fetch("fetched_rows", opener=FakeHealthcareGov())

    def test_fetch_dataset_pulls_arbitrary_identifier(self):
        fake = FakeHealthcareGov().add_datastore("e4rr-zk4i", _rates(3))
        step = _connector().fetch_dataset("e4rr-zk4i", opener=fake,
                                          page_size=2)
        self.assertEqual(len(step.rows), 3)
        self.assertEqual(step.endpoint, "e4rr-zk4i")

    def test_refresh_ingests_curated_endpoint(self):
        fake = FakeHealthcareGov().add_datastore(
            _PLAN_ATTRS_ID, PLAN_ATTRIBUTES_ROWS)
        store = HealthcareGovStore(":memory:")
        summary = _connector().refresh(store, "plan_attributes_py2026",
                                       opener=fake)
        self.assertEqual(summary["rows_upserted"], 3)
        self.assertEqual(summary["table"], "healthcare_gov_plan_attributes")
        self.assertEqual(store.count("healthcare_gov_plan_attributes"), 3)
        store.close()

    def test_refresh_catalog_syncs_catalog_table(self):
        fake = FakeHealthcareGov().add_catalog(CATALOG_ITEMS)
        store = HealthcareGovStore(":memory:")
        summary = _connector().refresh(store, "catalog", opener=fake)
        self.assertEqual(summary["rows_upserted"], 2)
        self.assertEqual(store.count("healthcare_gov_catalog"), 2)
        store.close()

    def test_refresh_dataset_lands_generic_rows_keyed_by_record_number(self):
        fake = FakeHealthcareGov().add_datastore("e4rr-zk4i", _rates(3))
        store = HealthcareGovStore(":memory:")
        summary = _connector().refresh_dataset(store, "e4rr-zk4i",
                                               opener=fake)
        self.assertEqual(summary["rows_upserted"], 3)
        rows = store.fetchall(
            "SELECT row_key, dataset_key, row_idx FROM healthcare_gov_rows "
            "ORDER BY CAST(row_idx AS INTEGER)")
        self.assertEqual(rows[0]["row_key"], "e4rr-zk4i:00000001")
        self.assertEqual(rows[0]["dataset_key"], "e4rr-zk4i")
        # Re-run is idempotent (same record_numbers → same keys).
        _connector().refresh_dataset(store, "e4rr-zk4i", opener=fake)
        self.assertEqual(store.count("healthcare_gov_rows"), 3)
        store.close()

    def test_refresh_dataset_signs_keys_with_the_filter_slice(self):
        # Two refreshes of one dataset under different conditions must
        # coexist — the params are forwarded to generic_rows as the
        # slice signature (same contract as the other DKAN connectors).
        # The fake datastore applies equality conditions like live DKAN, so
        # filter on age bands that actually exist in the fixture rows.
        fake = FakeHealthcareGov().add_datastore("e4rr-zk4i", _rates(2))
        store = HealthcareGovStore(":memory:")
        conn = _connector()
        conn.refresh_dataset(store, "e4rr-zk4i", opener=fake)
        conn.refresh_dataset(store, "e4rr-zk4i", {"age": "15"}, opener=fake)
        conn.refresh_dataset(store, "e4rr-zk4i", {"age": "16"}, opener=fake)
        self.assertEqual(store.count("healthcare_gov_rows"), 4)
        keys = [r["row_key"] for r in store.fetchall(
            "SELECT row_key FROM healthcare_gov_rows ORDER BY row_key")]
        # One unfiltered slice (no signature segment) + two signed slices.
        unsigned = [k for k in keys if k.count(":") == 1]
        signed = [k for k in keys if k.count(":") == 2]
        self.assertEqual(len(unsigned), 2)
        self.assertEqual(len(signed), 2)
        self.assertEqual(len({k.split(":")[1] for k in signed}), 2)
        # Re-running a filtered slice stays idempotent.
        conn.refresh_dataset(store, "e4rr-zk4i", {"age": "16"}, opener=fake)
        self.assertEqual(store.count("healthcare_gov_rows"), 4)
        store.close()


if __name__ == "__main__":
    unittest.main()
