import tempfile
import unittest
from pathlib import Path

from .. import dq as dq_mod
from ..connector import OpenFdaConnector
from ..crosswalk import resolve_ndc_rxcui
from ..endpoints import get_endpoint
from ..pipeline import OpenFdaPipeline, PipelineConfig
from ..query import query
from ..raw_store import RawStore
from ..state import StateStore
from ..tables import OpenFdaStore
from ..transport import OpenFdaTransport
from .fakes import FakeFda


def _fake_world():
    """A small but cross-cutting FakeFda covering several endpoints."""
    fake = FakeFda()
    fake.add("/drug/ndc.json", [
        {"product_ndc": "0002-1200", "brand_name": "FOO", "generic_name": "foo",
         "labeler_name": "Acme Inc", "dosage_form": "TABLET", "route": ["ORAL"]},
        {"product_ndc": "0003-1300", "brand_name": "BAR", "generic_name": "bar",
         "labeler_name": "Acme LLC", "dosage_form": "CREAM", "route": ["TOPICAL"]},
    ])
    fake.add("/drug/event.json", [
        {"safetyreportid": str(i), "receivedate": f"200401{i:02d}",
         "patient": {"drug": [{"medicinalproduct": "FOO",
                               "openfda": {"product_ndc": ["0002-1200"]}}],
                     "reaction": [{"reactionmeddrapt": "Nausea"}]}}
        for i in range(1, 6)])
    fake.add("/device/510k.json", [
        {"k_number": "K1", "product_code": "ABC", "device_name": "Widget",
         "applicant": "DeviceCo", "decision_date": "2019-05-01",
         "openfda": {"device_class": ["2"]}},
    ])
    return fake


class DqTests(unittest.TestCase):
    def setUp(self):
        self.store = OpenFdaStore(":memory:")

    def tearDown(self):
        self.store.close()

    def test_null_key_check_flags_empty_pk(self):
        # Insert directly to simulate a bad ingest (normalizer normally guards).
        self.store.conn.execute(
            "INSERT INTO dim_drug_product (ndc) VALUES ('')")
        self.store.conn.commit()
        results = dq_mod.null_key_check(self.store)
        ddp = next(r for r in results if r.name == "null_key:dim_drug_product")
        self.assertFalse(ddp.passed)

    def test_rxcui_coverage_reported(self):
        self.store.upsert("dim_drug_product", [
            {"ndc": "a", "source_endpoint": "drug_ndc"},
            {"ndc": "b", "rxcui": "55", "source_endpoint": "drug_ndc"}])
        r = dq_mod.ndc_rxcui_coverage(self.store)
        self.assertEqual(r.metrics["coverage_pct"], 50.0)

    def test_reconcile_against_live_count(self):
        self.store.upsert("dim_device", [
            {"device_key": "K:1", "product_code": "ABC",
             "source_endpoint": "device_510k"}])
        fake = FakeFda().add("/device/510k.json", [{"k_number": "K1"}])
        conn = OpenFdaConnector(OpenFdaTransport(min_interval_s=0.0))
        spec = get_endpoint("device_510k")
        r = dq_mod.reconcile_counts(conn, self.store, spec, opener=fake)
        self.assertTrue(r.passed)  # 1 ingested vs 1 live

    def test_deferred_rxcui_when_no_rxnorm(self):
        self.store.upsert("dim_drug_product", [
            {"ndc": "0002-1200", "source_endpoint": "drug_ndc"}])
        stats = resolve_ndc_rxcui(self.store, ["0002-1200"])
        self.assertEqual(stats["resolved"], 0)
        self.assertEqual(stats["deferred"], 1)
        row = self.store.fetchall("SELECT * FROM xwalk_ndc_rxcui")[0]
        self.assertEqual(row["resolution_status"], "deferred_no_rxnorm")


class PipelineEndToEndTests(unittest.TestCase):
    def _pipe(self, root, mode="backfill"):
        store = OpenFdaStore(str(Path(root) / "openfda.db"))
        state = StateStore(root)
        raw = RawStore(str(Path(root) / "raw"))
        conn = OpenFdaConnector(OpenFdaTransport(min_interval_s=0.0),
                                page_limit=2, backfill_start="20040101",
                                sleep=lambda s: None)
        pipe = OpenFdaPipeline(store, state, raw, conn,
                               config=PipelineConfig(mode=mode,
                                                     backfill_start="20040101"))
        return pipe, store, state

    def test_backfill_populates_and_is_resumable(self):
        with tempfile.TemporaryDirectory() as root:
            fake = _fake_world()
            pipe, store, state = self._pipe(root)
            states = pipe.run(endpoints=["drug_ndc", "drug_event", "device_510k"],
                              opener=fake)
            self.assertEqual(states["drug_ndc"].status, "complete")
            self.assertEqual(states["drug_event"].status, "complete")
            self.assertEqual(store.count("dim_drug_product"), 2)
            self.assertEqual(store.count("fact_drug_adverse_event"), 5)
            self.assertEqual(store.count("dim_device"), 1)

            # STATE.md persisted and reloadable.
            reloaded = state.load()
            self.assertEqual(reloaded["drug_event"].rows_ingested, 5)
            # DECISIONS.md notes the deferred RxCUI resolution.
            decisions = (Path(root) / "DECISIONS.md").read_text()
            self.assertIn("NDC", decisions)

            # Re-run = idempotent (no duplicate rows).
            pipe2, store2, _ = self._pipe(root)
            pipe2.run(endpoints=["drug_ndc", "drug_event", "device_510k"],
                      opener=_fake_world())
            self.assertEqual(store2.count("fact_drug_adverse_event"), 5)

    def test_one_failing_endpoint_does_not_block_others(self):
        with tempfile.TemporaryDirectory() as root:
            fake = _fake_world()
            # device/event has no records and we script a hard 400 for it so it fails.
            fake.add("/device/event.json", [])
            pipe, store, state = self._pipe(root)

            # Wrap the connector so device_event raises, others proceed.
            real_fetch = pipe.connector.fetch

            def flaky_fetch(spec, params, cursor, *, opener=None):
                if spec.key == "device_event":
                    raise RuntimeError("boom")
                return real_fetch(spec, params, cursor, opener=opener)

            pipe.connector.fetch = flaky_fetch
            states = pipe.run(endpoints=["drug_ndc", "device_event"], opener=fake)
            self.assertEqual(states["drug_ndc"].status, "complete")
            self.assertEqual(states["device_event"].status, "failed")
            self.assertEqual(store.count("dim_drug_product"), 2)

    def test_incremental_resumes_from_watermark(self):
        with tempfile.TemporaryDirectory() as root:
            # Backfill establishes a high-watermark from the FAERS dates.
            fake = _fake_world()  # drug_event dates 20040101..20040105
            pipe, store, state = self._pipe(root)
            pipe.run(endpoints=["drug_event"], opener=fake)
            wm = state.load()["drug_event"].high_watermark
            self.assertEqual(wm, "20040105")

            # Incremental seeds the connector start from watermark - overlap.
            pipe2, _, state2 = self._pipe(root, mode="incremental")
            pipe2.config.incremental_overlap_days = 2
            seeded = {}
            real = pipe2.connector.fetch

            def spy(spec, params, cursor, *, opener=None):
                # Capture the seeded start on the first (fresh-cursor) call.
                if spec.key == "drug_event" and cursor is None:
                    seeded["start"] = pipe2.connector.backfill_start
                return real(spec, params, cursor, opener=opener)

            pipe2.connector.fetch = spy
            pipe2.run(endpoints=["drug_event"], opener=_fake_world())
            # 20040105 - 2 days = 20040103, not a fixed today-lookback window.
            self.assertEqual(seeded["start"], "20040103")

    def test_query_after_pipeline(self):
        with tempfile.TemporaryDirectory() as root:
            pipe, store, _ = self._pipe(root)
            pipe.run(endpoints=["drug_ndc"], opener=_fake_world())
            res = query(store, "openfda_drug_ndc",
                        filters={"dosage_form": "TABLET"})
            self.assertEqual(res.total, 1)
            self.assertEqual(res.rows[0]["ndc"], "0002-1200")


if __name__ == "__main__":
    unittest.main()
