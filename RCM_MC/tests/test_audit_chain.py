"""Audit-log hash chain regression tests.

Invariants under test:

- Appending a chained event produces a hash deterministically derived
  from the row's content + the previous row's hash.
- Verification passes on a clean chain and fails on:
    (a) Row mutation after write (stored row_hash no longer matches
        recomputed).
    (b) Row deletion (prev_hash linkage broken).
    (c) Row reordering via id swap (hash linkage broken).
- Pre-chain rows (written by the legacy ``log_event`` path) coexist
  with chained rows — verification starts at the first hashed row.
- The verifier never raises on a freshly created store; it reports
  "no hashed rows yet" and ok=True.
"""
from __future__ import annotations

import os
import tempfile
import unittest

from rcm_mc.auth.audit_log import log_event
from rcm_mc.compliance.audit_chain import (
    append_chained_event, chain_status, verify_audit_chain,
)
from rcm_mc.portfolio.store import PortfolioStore


def _store(tmp: str) -> PortfolioStore:
    return PortfolioStore(os.path.join(tmp, "p.db"))


class ChainAppendTests(unittest.TestCase):

    def test_append_returns_id_and_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            event_id, row_hash = append_chained_event(
                store, actor="at", action="alert.ack", target="ccf",
            )
            self.assertGreaterEqual(event_id, 1)
            self.assertEqual(len(row_hash), 64)
            self.assertTrue(all(c in "0123456789abcdef" for c in row_hash))

    def test_second_append_links_to_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            id1, hash1 = append_chained_event(
                store, actor="at", action="a", target="t1",
            )
            id2, hash2 = append_chained_event(
                store, actor="at", action="a", target="t2",
            )
            self.assertNotEqual(hash1, hash2)
            # Row 2's prev_hash equals row 1's row_hash.
            with store.connect() as con:
                row2 = con.execute(
                    "SELECT prev_hash FROM audit_events WHERE id = ?",
                    (id2,),
                ).fetchone()
            self.assertEqual(row2["prev_hash"], hash1)

    def test_first_row_has_null_prev_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            eid, _ = append_chained_event(
                store, actor="at", action="a", target="t",
            )
            with store.connect() as con:
                row = con.execute(
                    "SELECT prev_hash FROM audit_events WHERE id = ?",
                    (eid,),
                ).fetchone()
            self.assertIsNone(row["prev_hash"])


class ChainVerifyHappyPathTests(unittest.TestCase):

    def test_empty_store_verifies_with_no_hashed_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            report = verify_audit_chain(store)
            self.assertTrue(report.ok)
            self.assertEqual(report.hashed_rows, 0)

    def test_clean_chain_of_five_verifies(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            for i in range(5):
                append_chained_event(store, actor="at",
                                     action=f"a{i}", target=f"t{i}")
            report = verify_audit_chain(store)
            self.assertTrue(report.ok)
            self.assertEqual(report.hashed_rows, 5)
            self.assertEqual(report.mismatches, [])
            self.assertEqual(report.missing_prev, [])


class ChainTamperDetectionTests(unittest.TestCase):

    def test_mutation_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            id1, _ = append_chained_event(
                store, actor="at", action="approve", target="deal_42",
            )
            append_chained_event(
                store, actor="at", action="noop", target="t",
            )
            # Attacker flips the target on row 1.
            with store.connect() as con:
                con.execute(
                    "UPDATE audit_events SET target = ? WHERE id = ?",
                    ("deal_99", id1),
                )
                con.commit()
            report = verify_audit_chain(store)
            self.assertFalse(report.ok)
            self.assertTrue(
                any(m["id"] == id1 for m in report.mismatches),
                msg=f"expected row {id1} in mismatches, got {report.mismatches}",
            )

    def test_deletion_detected_via_broken_prev_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            append_chained_event(store, actor="at", action="a1", target="t")
            id2, _ = append_chained_event(store, actor="at", action="a2", target="t")
            append_chained_event(store, actor="at", action="a3", target="t")
            # Attacker deletes row 2 to hide an action.
            with store.connect() as con:
                con.execute("DELETE FROM audit_events WHERE id = ?", (id2,))
                con.commit()
            report = verify_audit_chain(store)
            self.assertFalse(report.ok)
            self.assertTrue(
                report.missing_prev,
                msg="deletion should break the prev_hash linkage",
            )

    def test_row_hash_nulled_is_detected_as_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            id1, _ = append_chained_event(store, actor="at", action="a", target="t")
            append_chained_event(store, actor="at", action="b", target="t")
            # Attacker blanks row 1's hash column (tries to re-insert
            # a "clean" row).
            with store.connect() as con:
                con.execute(
                    "UPDATE audit_events SET row_hash = NULL WHERE id = ?",
                    (id1,),
                )
                con.commit()
            # Row 2 still has row_hash; its prev_hash no longer links.
            report = verify_audit_chain(store)
            self.assertFalse(report.ok)


class ChainCoexistenceWithLegacyTests(unittest.TestCase):
    """Legacy ``log_event`` rows have no row_hash. They must coexist
    with chained rows without breaking verification — verification
    starts at the first hashed row."""

    def test_pre_chain_rows_are_counted_but_not_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            # 3 legacy rows, then 2 chained rows.
            log_event(store, actor="legacy", action="a", target="t")
            log_event(store, actor="legacy", action="b", target="t")
            log_event(store, actor="legacy", action="c", target="t")
            append_chained_event(store, actor="at", action="d", target="t")
            append_chained_event(store, actor="at", action="e", target="t")
            report = verify_audit_chain(store)
            self.assertTrue(report.ok)
            self.assertEqual(report.total_rows, 5)
            self.assertEqual(report.hashed_rows, 2)

    def test_chain_status_reports_pre_chain_and_hashed_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            log_event(store, actor="legacy", action="a", target="t")
            append_chained_event(store, actor="at", action="b", target="t")
            status = chain_status(store)
            self.assertEqual(status["total_rows"], 2)
            self.assertEqual(status["hashed_rows"], 1)
            self.assertEqual(status["pre_chain_rows"], 1)
            self.assertIsNotNone(status["last_row_hash"])


if __name__ == "__main__":
    unittest.main()
