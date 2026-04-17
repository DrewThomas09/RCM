"""Tests for B118 CLI mirrors (alerts / deadlines / owners)."""
from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date, timedelta

from rcm_mc import portfolio_cmd
from rcm_mc.alerts.alert_acks import trigger_key_for
from rcm_mc.alerts.alerts import evaluate_all
from rcm_mc.deals.deal_deadlines import add_deadline
from rcm_mc.deals.deal_owners import assign_owner
from tests.test_alerts import _seed_with_pe_math


def _db(tmp: str) -> str:
    return os.path.join(tmp, "p.db")


def _run(*argv, db_path: str) -> str:
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = portfolio_cmd.main(["--db", db_path, *argv])
    assert rc == 0, f"CLI exited {rc}"
    return buf.getvalue()


class TestAlertsCli(unittest.TestCase):
    def test_alerts_active_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            out = _run("alerts", "active", db_path=_db(tmp))
            data = json.loads(out)
            self.assertTrue(len(data) >= 1)
            kinds = {a["kind"] for a in data}
            self.assertIn("covenant_tripped", kinds)

    def test_alerts_ack_then_active_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            a = next(x for x in evaluate_all(store)
                     if x.kind == "covenant_tripped")
            tk = trigger_key_for(a)
            out = _run(
                "alerts", "ack",
                "--kind", a.kind, "--deal-id", a.deal_id,
                "--trigger-key", tk,
                db_path=_db(tmp),
            )
            ack = json.loads(out)
            self.assertIn("ack_id", ack)
            # After ack, active list should not contain this alert
            out2 = _run("alerts", "active", db_path=_db(tmp))
            active = json.loads(out2)
            self.assertFalse(any(x["kind"] == "covenant_tripped"
                                 for x in active))


class TestDeadlinesCli(unittest.TestCase):
    def test_add_and_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "ccf")
            future = (date.today() + timedelta(days=5)).isoformat()
            out = _run(
                "deadlines", "add",
                "--deal-id", "ccf", "--label", "refi call",
                "--due-date", future, "--owner", "AT",
                db_path=_db(tmp),
            )
            did = json.loads(out)["deadline_id"]

            upcoming_csv = _run(
                "deadlines", "upcoming", "--days", "14",
                db_path=_db(tmp),
            )
            self.assertIn("refi call", upcoming_csv)

            out = _run(
                "deadlines", "complete", "--id", str(did),
                db_path=_db(tmp),
            )
            self.assertTrue(json.loads(out)["completed"])

    def test_owner_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "ccf")
            past = (date.today() - timedelta(days=2)).isoformat()
            # One deadline per owner
            _run("deadlines", "add", "--deal-id", "ccf",
                 "--label", "AT item", "--due-date", past,
                 "--owner", "AT", db_path=_db(tmp))
            _run("deadlines", "add", "--deal-id", "ccf",
                 "--label", "SB item", "--due-date", past,
                 "--owner", "SB", db_path=_db(tmp))
            at_csv = _run("deadlines", "overdue", "--owner", "AT",
                          db_path=_db(tmp))
            self.assertIn("AT item", at_csv)
            self.assertNotIn("SB item", at_csv)


class TestOwnersCli(unittest.TestCase):
    def test_assign_and_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "ccf")
            _run(
                "owners", "assign", "--deal-id", "ccf", "--owner", "AT",
                db_path=_db(tmp),
            )
            out = _run("owners", "list", db_path=_db(tmp))
            self.assertIn("AT\t1", out)
            deals = _run("owners", "deals", "--owner", "AT",
                         db_path=_db(tmp)).strip()
            self.assertEqual(deals, "ccf")


if __name__ == "__main__":
    unittest.main()
