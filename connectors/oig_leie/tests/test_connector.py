import datetime
import unittest

from ..connector import OigLeieConnector, SUPPLEMENT_LOOKBACK_MONTHS
from ..endpoints import get_endpoint
from ..tables import OigLeieStore
from ..transport import OigLeieApiError, OigLeieTransport, RawResponse
from .fakes import (FakeOig, SUPPL_2605_EXCL, SUPPL_2605_REIN, UPDATED_PATH,
                    _to_csv, supplement_excl_csv, supplement_rein_csv,
                    updated_csv, updated_rows)

# The fixed "today" every walk-back test pins: 2026-07-06, matching the
# live probe date — so "latest published" resolves 2026-07 → 2026-06 →
# 2026-05 exactly as it did against the real site.
_TODAY = datetime.date(2026, 7, 6)


def _connector():
    return OigLeieConnector(OigLeieTransport(min_interval_s=0.0),
                            sleep=lambda s: None, today=lambda: _TODAY)


class ConnectorTests(unittest.TestCase):
    def test_discover_lists_all_three_datasets(self):
        keys = {s.key for s in _connector().discover()}
        self.assertEqual(keys, {"exclusions", "supplement", "reinstatements"})

    def test_fetch_full_is_single_step_no_cursor(self):
        fake = FakeOig().add(UPDATED_PATH, updated_csv())
        step = _connector().fetch(get_endpoint("exclusions"), opener=fake)
        self.assertIsNone(step.next_cursor)     # one file = one step
        self.assertTrue(step.done)
        self.assertEqual(len(step.rows), 4)
        self.assertFalse(step.truncated)
        self.assertEqual(step.endpoint, "exclusions")
        self.assertEqual(step.requests, 1)      # exactly one download
        self.assertIsNone(step.month_tag)       # full file has no month
        self.assertEqual(len(fake.calls), 1)
        self.assertIn("UPDATED.csv", fake.calls[0])

    def test_fetch_accepts_key_string(self):
        fake = FakeOig().add(UPDATED_PATH, updated_csv())
        step = _connector().fetch("exclusions", opener=fake)
        self.assertEqual(len(step.rows), 4)

    def test_fetch_max_rows_caps_ingest(self):
        fake = FakeOig().add(UPDATED_PATH, updated_csv())
        step = _connector().fetch("exclusions", max_rows=1, opener=fake)
        self.assertEqual(len(step.rows), 1)
        self.assertTrue(step.truncated)

    def test_fetch_all_is_uncapped(self):
        fake = FakeOig().add(UPDATED_PATH, updated_csv())
        rows = _connector().fetch_all("exclusions", opener=fake)
        self.assertEqual(len(rows), 4)

    def test_fetch_supplement_explicit_month_builds_live_url(self):
        fake = FakeOig().add(SUPPL_2605_EXCL, supplement_excl_csv())
        step = _connector().fetch("supplement", year=2026, month=5,
                                  opener=fake)
        self.assertEqual(len(step.rows), 2)
        self.assertEqual(step.month_tag, "2026-05")
        # The exact live URL pattern: /{yyyy}/{yy}{mm}excl.csv
        self.assertTrue(fake.calls[0].endswith(
            "/exclusions/downloadables/2026/2605excl.csv"))

    def test_fetch_supplement_month_via_params_dict(self):
        # Estate parity: paging connectors pass knobs via params.
        fake = FakeOig().add(SUPPL_2605_EXCL, supplement_excl_csv())
        step = _connector().fetch("supplement",
                                  {"year": "2026", "month": "5"}, opener=fake)
        self.assertEqual(step.month_tag, "2026-05")

    def test_fetch_supplement_walks_back_over_unpublished_months(self):
        # 2026-07 and 2026-06 return 404 (not published — matches the
        # live index on the probe date); 2026-05 exists.
        fake = FakeOig().add(SUPPL_2605_EXCL, supplement_excl_csv())
        step = _connector().fetch("supplement", opener=fake)
        self.assertEqual(step.month_tag, "2026-05")
        self.assertEqual(len(step.rows), 2)
        self.assertEqual([u.rsplit("/", 1)[-1] for u in fake.calls],
                         ["2607excl.csv", "2606excl.csv", "2605excl.csv"])

    def test_fetch_reinstatements_walks_back_too(self):
        fake = FakeOig().add(SUPPL_2605_REIN, supplement_rein_csv())
        step = _connector().fetch("reinstatements", opener=fake)
        self.assertEqual(step.month_tag, "2026-05")
        self.assertTrue(fake.calls[-1].endswith("2605rein.csv"))

    def test_walk_back_exhaustion_raises_naming_tried_months(self):
        fake = FakeOig()  # nothing published at all
        with self.assertRaises(OigLeieApiError) as ctx:
            _connector().fetch("supplement", opener=fake)
        msg = str(ctx.exception)
        self.assertIn("2026-07", msg)
        self.assertIn("2026-02", msg)   # 6 months back from 2026-07
        self.assertEqual(len(fake.calls), SUPPLEMENT_LOOKBACK_MONTHS)

    def test_walk_back_does_not_swallow_non_404_failures(self):
        fake = FakeOig().add(SUPPL_2605_EXCL, supplement_excl_csv())
        fake.transients[0] = (403, {})   # first probe hard-fails
        with self.assertRaises(OigLeieApiError) as ctx:
            _connector().fetch("supplement", opener=fake)
        self.assertEqual(ctx.exception.status, 403)

    def test_year_without_month_raises(self):
        with self.assertRaises(ValueError):
            _connector().fetch("supplement", year=2026, opener=FakeOig())

    def test_refresh_ingests_end_to_end_and_reports_counts(self):
        fake = FakeOig().add(UPDATED_PATH, updated_csv())
        store = OigLeieStore(":memory:")
        try:
            counts = _connector().refresh(store, "exclusions", opener=fake)
            self.assertEqual(counts["dataset_id"], "oig_leie_exclusions")
            self.assertEqual(counts["fetched"], 4)
            self.assertEqual(counts["upserted"], {"oig_exclusions": 4})
            self.assertFalse(counts["truncated"])
            self.assertEqual(counts["unmapped_fields"], {})
            self.assertIsNone(counts["year"])
            self.assertEqual(store.count("oig_exclusions"), 4)
        finally:
            store.close()

    def test_refresh_collapses_duplicate_source_lines(self):
        # The live full file contains a couple dozen byte-identical
        # duplicate lines; the composed key + upsert must collapse them.
        fake = FakeOig().add(UPDATED_PATH, updated_csv(duplicate_last_row=True))
        store = OigLeieStore(":memory:")
        try:
            counts = _connector().refresh(store, "exclusions", opener=fake)
            self.assertEqual(counts["fetched"], 5)              # raw lines
            self.assertEqual(store.count("oig_exclusions"), 4)  # unique rows
        finally:
            store.close()

    def test_refresh_supplement_merges_into_cumulative_table(self):
        # Full pull, then a monthly supplement containing one known row
        # and one new row: the table must grow by exactly one, and the
        # supplement rows must carry the month-tagged provenance.
        fake = (FakeOig()
                .add(UPDATED_PATH, updated_csv())
                .add(SUPPL_2605_EXCL, supplement_excl_csv()))
        store = OigLeieStore(":memory:")
        try:
            conn = _connector()
            conn.refresh(store, "exclusions", opener=fake)
            self.assertEqual(store.count("oig_exclusions"), 4)
            counts = conn.refresh(store, "supplement", opener=fake)
            self.assertEqual(counts["month"], 5)
            self.assertEqual(store.count("oig_exclusions"), 5)  # +1 new
            self.assertEqual(
                store.count("oig_exclusions",
                            "source_endpoint = ?", ("supplement:2026-05",)),
                2)  # both supplement rows re-tagged by the later write
        finally:
            store.close()

    def test_refresh_reinstatements_lands_in_own_table(self):
        fake = FakeOig().add(SUPPL_2605_REIN, supplement_rein_csv())
        store = OigLeieStore(":memory:")
        try:
            counts = _connector().refresh(store, "reinstatements", opener=fake)
            self.assertEqual(counts["dataset_id"], "oig_leie_reinstatements")
            self.assertEqual(counts["upserted"], {"oig_reinstatements": 2})
            self.assertEqual(store.count("oig_reinstatements"), 2)
            self.assertEqual(store.count("oig_exclusions"), 0)
        finally:
            store.close()

    def test_unknown_dataset_key_raises(self):
        with self.assertRaises(KeyError):
            _connector().fetch("nope", opener=FakeOig())


class FullReplacementTests(unittest.TestCase):
    """UPDATED.csv is a full-replacement publication: a complete refresh
    must REPLACE the exclusions slice so reinstated providers (absent
    from the new file) stop being flagged; anything less than a complete
    download must never delete."""

    def setUp(self):
        self.store = OigLeieStore(":memory:")
        self.conn = _connector()

    def tearDown(self):
        self.store.close()

    def _seed_full_and_supplement(self, fake):
        """Full pull (4 rows incl. SMITH) + supplement (adds OKAFOR)."""
        r = self.conn.refresh(self.store, "exclusions", opener=fake)
        self.assertEqual(r["mode"], "replace")
        self.assertIsNone(r["warning"])
        r = self.conn.refresh(self.store, "supplement", opener=fake)
        self.assertEqual(r["mode"], "merge")   # supplements never replace
        self.assertIsNone(r["warning"])
        self.assertEqual(self.store.count("oig_exclusions"), 5)

    def test_reinstated_provider_disappears_after_full_refresh(self):
        fake = (FakeOig()
                .add(UPDATED_PATH, updated_csv())
                .add(SUPPL_2605_EXCL, supplement_excl_csv()))
        self._seed_full_and_supplement(fake)
        # Next month's full file: SMITH was reinstated → absent. The
        # cumulative full file also supersedes the merged supplement
        # rows (OKAFOR is not in it).
        without_smith = [r for r in updated_rows()
                         if r.get("LASTNAME") != "SMITH"]
        fake.add(UPDATED_PATH, _to_csv(without_smith))
        report = self.conn.refresh(self.store, "exclusions", opener=fake)
        self.assertEqual(report["mode"], "replace")
        self.assertIsNone(report["warning"])
        self.assertEqual(self.store.count("oig_exclusions"), 3)
        self.assertEqual(
            self.store.count("oig_exclusions", "lastname = ?", ("SMITH",)),
            0)  # reinstated → no longer flagged
        self.assertEqual(
            self.store.count("oig_exclusions", "lastname = ?", ("OKAFOR",)),
            0)  # superseded supplement row gone too

    def test_capped_full_refresh_merges_only_and_warns(self):
        fake = FakeOig().add(UPDATED_PATH, updated_csv())
        self.conn.refresh(self.store, "exclusions", opener=fake)
        self.assertEqual(self.store.count("oig_exclusions"), 4)
        # New (smaller) live file, but the pull is row-capped: the
        # partial snapshot must merge, never delete.
        without_smith = [r for r in updated_rows()
                         if r.get("LASTNAME") != "SMITH"]
        fake.add(UPDATED_PATH, _to_csv(without_smith))
        report = self.conn.refresh(self.store, "exclusions", max_rows=2,
                                   opener=fake)
        self.assertEqual(report["mode"], "merge")
        self.assertTrue(report["truncated"])
        self.assertIn("partial merge", report["warning"])
        self.assertEqual(self.store.count("oig_exclusions"), 4)
        self.assertEqual(
            self.store.count("oig_exclusions", "lastname = ?", ("SMITH",)),
            1)  # untouched — a capped pull is not a snapshot

    def test_failed_truncated_download_never_deletes(self):
        fake = FakeOig().add(UPDATED_PATH, updated_csv())
        self.conn.refresh(self.store, "exclusions", opener=fake)
        self.assertEqual(self.store.count("oig_exclusions"), 4)

        body = updated_csv().encode("utf-8")

        def dropping_opener(url, headers, timeout):
            # Mid-body connection drop: short body vs Content-Length.
            return RawResponse(
                status=200,
                headers={"content-length": str(len(body))},
                body=body[: len(body) // 3])

        conn = OigLeieConnector(
            OigLeieTransport(min_interval_s=0.0, max_retries=1),
            sleep=lambda s: None, today=lambda: _TODAY)
        with self.assertRaises(OigLeieApiError):
            conn.refresh(self.store, "exclusions", opener=dropping_opener)
        self.assertEqual(self.store.count("oig_exclusions"), 4)  # intact

    def test_zero_row_full_file_refuses_to_wipe(self):
        fake = FakeOig().add(UPDATED_PATH, updated_csv())
        self.conn.refresh(self.store, "exclusions", opener=fake)
        header_only = updated_csv().splitlines()[0] + "\r\n"
        fake.add(UPDATED_PATH, header_only)
        report = self.conn.refresh(self.store, "exclusions", opener=fake)
        self.assertEqual(report["mode"], "merge")
        self.assertIn("0 usable rows", report["warning"])
        self.assertEqual(self.store.count("oig_exclusions"), 4)  # intact

    def test_store_without_replace_all_degrades_to_merge_with_warning(self):
        class MergeOnlyStore:
            def __init__(self, inner):
                self.inner = inner

            def upsert(self, table, rows):
                return self.inner.upsert(table, rows)

        fake = FakeOig().add(UPDATED_PATH, updated_csv())
        report = self.conn.refresh(MergeOnlyStore(self.store), "exclusions",
                                   opener=fake)
        self.assertEqual(report["mode"], "merge")
        self.assertIn("replace_all", report["warning"])
        self.assertEqual(self.store.count("oig_exclusions"), 4)

    def test_replace_all_is_atomic_in_one_transaction(self):
        # A failure mid-replacement must roll back the DELETE too: the
        # store never exposes an empty/half-written table.
        import sqlite3
        self.store.upsert("oig_exclusions", [
            {"exclusion_key": "k1", "lastname": "OLD"}])
        self.store.conn.execute(
            "CREATE TRIGGER boom BEFORE INSERT ON oig_exclusions "
            "WHEN NEW.lastname = 'BROKEN' "
            "BEGIN SELECT RAISE(ABORT, 'boom'); END")
        bad_rows = [{"exclusion_key": "k2", "lastname": "NEW"},
                    {"exclusion_key": "k3", "lastname": "BROKEN"}]
        with self.assertRaises(sqlite3.DatabaseError):
            self.store.replace_all("oig_exclusions", bad_rows)
        # DELETE and the first INSERT were rolled back with the failure.
        self.assertEqual(self.store.count("oig_exclusions"), 1)
        self.assertEqual(
            self.store.count("oig_exclusions", "lastname = ?", ("OLD",)), 1)


if __name__ == "__main__":
    unittest.main()
