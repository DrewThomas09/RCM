"""Tests for the NPI cleaner CLI management (CRUD) subcommands.

The cleaner's stores (profiles, mapping templates, run history, wishlist)
were web-UI only; these exercise the flag-based CLI surface that exposes
them to cron/scripts. Every test drives ``cli.main([...])`` with
redirect_stdout/stderr, asserting exit codes and round-tripping a created
record through --list / --show / status / delete. Real store functions
write to the cleaner WORKDIR — same discipline as tests/test_npi_cleaner.py.
"""
from __future__ import annotations

import contextlib
import io
import json
import unittest

from rcm_mc.npi_cleaner.cli import main as cli_main
from rcm_mc.npi_cleaner import (engine, history, mappings, profiles,
                                wishlist)


# NPI that passes the real CMS/NPPES Luhn check (shared with test_npi_cleaner).
GOOD_B = "1679576722"


def _run(argv):
    """Drive cli.main capturing stdout+stderr; return (rc, out, err)."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = cli_main(argv)
    return rc, out.getvalue(), err.getvalue()


class TestListCommands(unittest.TestCase):
    """Every list flag returns 0 and emits a JSON list — including when the
    store is empty (the store's own guards degrade to [])."""

    def test_list_flags_return_zero_and_json_is_a_list(self):
        for flag in ("--list-profiles", "--list-mappings",
                     "--history", "--wishlist"):
            with self.subTest(flag=flag):
                rc, out, _ = _run([flag])
                self.assertEqual(rc, 0)
                rc_j, out_j, _ = _run([flag, "--json"])
                self.assertEqual(rc_j, 0)
                self.assertIsInstance(json.loads(out_j), list)

    def test_history_accepts_explicit_limit(self):
        rc, _, _ = _run(["--history", "5"])
        self.assertEqual(rc, 0)


class TestProfilesCrud(unittest.TestCase):
    NAME = "cli-crud-profile"

    def tearDown(self):
        profiles.delete_profile(self.NAME)

    def test_profile_round_trip(self):
        profiles.save_profile(self.NAME, {"disabled_rules": ["date-stale"]})

        # list (human) surfaces the name
        rc, out, _ = _run(["--list-profiles"])
        self.assertEqual(rc, 0)
        self.assertIn(self.NAME, out)

        # show (JSON) parses and carries the injected name
        rc, out, _ = _run(["--show-profile", self.NAME, "--json"])
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out)["name"], self.NAME)

        # delete via the CLI, then it is gone from the store
        rc, out, _ = _run(["--delete-profile", self.NAME])
        self.assertEqual(rc, 0)
        self.assertIsNone(profiles.get_profile(self.NAME))

        # deleting again is a not-found → exit 2 on stderr
        rc, _, err = _run(["--delete-profile", self.NAME])
        self.assertEqual(rc, 2)
        self.assertIn("no such profile", err)

    def test_show_missing_profile_returns_2(self):
        rc, _, err = _run(["--show-profile", "definitely-not-a-profile"])
        self.assertEqual(rc, 2)
        self.assertIn("no such profile", err)


class TestMappingsCrud(unittest.TestCase):
    NAME = "cli-crud-mapping"

    def tearDown(self):
        mappings.delete_mapping(self.NAME)

    def test_mapping_round_trip(self):
        mappings.save_mapping(self.NAME, {"billing_npi": "Billing_Prov_NPI"})

        rc, out, _ = _run(["--list-mappings"])
        self.assertEqual(rc, 0)
        self.assertIn(self.NAME, out)

        rc, out, _ = _run(["--show-mapping", self.NAME, "--json"])
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out)["billing_npi"], "Billing_Prov_NPI")

        rc, out, _ = _run(["--show-mapping", self.NAME])
        self.assertEqual(rc, 0)
        self.assertIn("Billing_Prov_NPI", out)

        rc, _, _ = _run(["--delete-mapping", self.NAME])
        self.assertEqual(rc, 0)
        self.assertIsNone(mappings.get_mapping(self.NAME))

        rc, _, err = _run(["--delete-mapping", self.NAME])
        self.assertEqual(rc, 2)
        self.assertIn("no such mapping template", err)

    def test_show_missing_mapping_returns_2(self):
        rc, _, err = _run(["--show-mapping", "definitely-not-a-mapping"])
        self.assertEqual(rc, 2)
        self.assertIn("no such mapping template", err)


class TestWishlistCrud(unittest.TestCase):
    TITLE = "CLI CRUD wishlist round-trip probe"

    def test_wishlist_add_list_status_delete(self):
        # add via the CLI
        rc, out, _ = _run(["--wishlist-add", "rule", self.TITLE])
        self.assertEqual(rc, 0)
        self.assertIn("added wishlist request", out)

        # find the created id via JSON list
        rc, out, _ = _run(["--wishlist", "--json"])
        self.assertEqual(rc, 0)
        rows = json.loads(out)
        mine = [r for r in rows if r["title"] == self.TITLE]
        self.assertEqual(len(mine), 1)
        rid = mine[0]["id"]
        self.assertEqual(mine[0]["status"], "open")
        self.assertEqual(mine[0]["category"], "rule")

        try:
            # move it to planned, then confirm via the filtered JSON list
            rc, _, _ = _run(["--wishlist-status", str(rid), "planned"])
            self.assertEqual(rc, 0)
            rc, out, _ = _run(["--wishlist", "planned", "--json"])
            self.assertEqual(rc, 0)
            self.assertTrue(any(r["id"] == rid for r in json.loads(out)))

            # an invalid status is rejected with exit 2
            rc, _, err = _run(["--wishlist-status", str(rid), "bogus"])
            self.assertEqual(rc, 2)
            self.assertIn("valid:", err)

            # a non-numeric id is rejected with exit 2
            rc, _, err = _run(["--wishlist-status", "not-an-int", "open"])
            self.assertEqual(rc, 2)
            self.assertIn("invalid request id", err)
        finally:
            rc, _, _ = _run(["--wishlist-delete", str(rid)])
            self.assertEqual(rc, 0)

        # already deleted → not found → exit 2
        rc, _, err = _run(["--wishlist-delete", str(rid)])
        self.assertEqual(rc, 2)
        self.assertIn("no such wishlist request", err)

    def test_wishlist_add_blank_title_returns_2(self):
        rc, _, err = _run(["--wishlist-add", "rule", "   "])
        self.assertEqual(rc, 2)
        self.assertTrue(err.strip())


class TestHistoryCommands(unittest.TestCase):
    def test_show_missing_run_returns_2(self):
        rc, _, err = _run(["--show-run", "deadbeefcafe"])
        self.assertEqual(rc, 2)
        self.assertIn("no such run", err)

    def test_compare_missing_runs_returns_2(self):
        rc, _, err = _run(["--compare-runs", "nope-a", "nope-b"])
        self.assertEqual(rc, 2)
        self.assertIn("could not compare", err)

    def test_compare_two_real_runs(self):
        # Two real cleaner runs are auto-recorded in history; a good file
        # scores higher than a malformed one → negative score delta.
        engine.clean_bytes(
            ("ClaimID,BillingNPI\n" f"1,{GOOD_B}\n").encode(),
            "cli_crud_hist_good.csv")
        engine.clean_bytes(
            "ClaimID,BillingNPI,HCPCS\n1,123,BAD!!\n".encode(),
            "cli_crud_hist_bad.csv")
        runs = history.list_runs(50)
        good = next(r for r in runs
                    if r["file_name"] == "cli_crud_hist_good.csv")
        bad = next(r for r in runs
                   if r["file_name"] == "cli_crud_hist_bad.csv")

        # show-run round-trips one of them
        rc, out, _ = _run(["--show-run", good["run_id"], "--json"])
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out)["run_id"], good["run_id"])

        # compare via JSON
        rc, out, _ = _run(
            ["--compare-runs", good["run_id"], bad["run_id"], "--json"])
        self.assertEqual(rc, 0)
        cmp_ = json.loads(out)
        self.assertLess(cmp_["score_delta"], 0)

        # compare in human mode also succeeds
        rc, out, _ = _run(
            ["--compare-runs", good["run_id"], bad["run_id"]])
        self.assertEqual(rc, 0)
        self.assertIn("score delta", out)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
