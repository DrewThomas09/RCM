"""Tests for the rcm-lookup CLI and its underlying search + formatters."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from rcm_mc.data.hcris import _clear_cache, browse_by_state
from rcm_mc.data.lookup import (
    _parse_beds_range,
    format_markdown_summary,
    format_one_hospital,
    format_one_liner,
    format_table,
    main as lookup_main,
    search,
)


BASE_DIR = Path(__file__).resolve().parents[1]


class TestBrowseByState(unittest.TestCase):
    def setUp(self):
        _clear_cache()

    def test_state_filter_returns_only_that_state(self):
        rows = browse_by_state("OH", limit=20)
        self.assertTrue(rows)
        self.assertTrue(all(r["state"] == "OH" for r in rows))

    def test_sorted_by_beds_descending_default(self):
        rows = browse_by_state("OH", limit=10)
        beds = [r["beds"] for r in rows if r.get("beds") is not None]
        self.assertEqual(beds, sorted(beds, reverse=True))

    def test_bed_range_filters_inclusive(self):
        rows = browse_by_state("OH", beds_range=(400, 700), limit=50)
        self.assertTrue(rows)
        for r in rows:
            self.assertGreaterEqual(r["beds"], 400)
            self.assertLessEqual(r["beds"], 700)

    def test_unknown_state_returns_empty(self):
        self.assertEqual(browse_by_state("ZZ", limit=10), [])

    def test_empty_or_none_state_returns_empty(self):
        self.assertEqual(browse_by_state("", limit=10), [])
        self.assertEqual(browse_by_state(None, limit=10), [])  # type: ignore[arg-type]


class TestParseBedsRange(unittest.TestCase):
    def test_range_parses(self):
        self.assertEqual(_parse_beds_range("200-600"), (200, 600))

    def test_open_ended_upper(self):
        self.assertEqual(_parse_beds_range("500-"), (500, 10_000))

    def test_open_ended_lower(self):
        self.assertEqual(_parse_beds_range("-1000"), (0, 1000))

    def test_single_number_exact_match(self):
        self.assertEqual(_parse_beds_range("500"), (500, 500))

    def test_none_and_empty(self):
        self.assertIsNone(_parse_beds_range(None))
        self.assertIsNone(_parse_beds_range(""))

    def test_min_greater_than_max_raises(self):
        with self.assertRaises(ValueError):
            _parse_beds_range("900-300")

    def test_negative_raises(self):
        with self.assertRaises(ValueError):
            _parse_beds_range("-500-600")


class TestSearch(unittest.TestCase):
    def setUp(self):
        _clear_cache()

    def test_ccn_returns_single_match(self):
        rows = search(ccn="360180")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["ccn"], "360180")

    def test_ccn_missing_returns_empty(self):
        self.assertEqual(search(ccn="999999"), [])

    def test_name_returns_ranked_matches(self):
        rows = search(name="cleveland clinic", limit=5)
        self.assertTrue(rows)
        # Top match should have "CLEVELAND CLINIC" in its name
        self.assertIn("CLEVELAND CLINIC", rows[0]["name"])

    def test_state_only_browses_by_state(self):
        rows = search(state="OH", limit=15)
        self.assertTrue(rows)
        self.assertTrue(all(r["state"] == "OH" for r in rows))

    def test_name_plus_state_scopes(self):
        rows = search(name="Memorial", state="TX", limit=20)
        self.assertTrue(all(r["state"] == "TX" for r in rows))

    def test_beds_range_narrows_results(self):
        broad = search(state="OH", limit=100)
        narrow = search(state="OH", beds_range=(600, 1500), limit=100)
        self.assertLessEqual(len(narrow), len(broad))
        for r in narrow:
            self.assertGreaterEqual(r["beds"], 600)
            self.assertLessEqual(r["beds"], 1500)

    def test_no_criteria_returns_empty(self):
        self.assertEqual(search(), [])

    def test_limit_caps_results(self):
        rows = search(state="CA", limit=5)
        self.assertLessEqual(len(rows), 5)


class TestFormatters(unittest.TestCase):
    def test_format_one_hospital_has_all_sections(self):
        row = search(ccn="360180")[0]
        text = format_one_hospital(row)
        self.assertIn("CLEVELAND CLINIC", text)
        self.assertIn("CCN 360180", text)
        self.assertIn("Beds:", text)
        self.assertIn("Net Patient Rev:", text)
        self.assertIn("Medicare day %:", text)

    def test_format_table_has_headers_and_rows(self):
        rows = search(state="OH", limit=5)
        out = format_table(rows)
        # Header row + separator row + 5 data rows = 7 lines minimum
        self.assertGreaterEqual(len(out.splitlines()), 7)
        self.assertIn("CCN", out)
        self.assertIn("Name", out)
        self.assertIn("NPSR", out)

    def test_format_table_with_empty_rows(self):
        self.assertIn("no hospitals matched", format_table([]))

    def test_one_liner_includes_name_ccn_state_and_beds(self):
        s = format_one_liner("360180")
        self.assertIn("CLEVELAND CLINIC", s)
        self.assertIn("CCN 360180", s)
        self.assertIn("OH", s)
        self.assertIn("beds", s)

    def test_one_liner_includes_npsr_margin_medicare_pct(self):
        s = format_one_liner("360180")
        self.assertIn("NPSR", s)
        self.assertIn("op margin", s)
        self.assertIn("Medicare", s)

    def test_one_liner_includes_peer_rank_clause(self):
        s = format_one_liner("360180")
        self.assertIn("Peer rank", s)
        self.assertIn("th", s)  # percentile suffix
        # Brick 34 polish: peer-count clause uses "n=" not ambiguous "of N"
        self.assertIn("n=", s)

    def test_one_liner_includes_trend_watchlist_when_multi_year(self):
        s = format_one_liner("360180")
        self.assertIn("Trend", s)
        # Severity tag must appear
        self.assertTrue("concerning" in s or "favorable" in s)

    def test_one_liner_returns_not_found_for_bad_ccn(self):
        s = format_one_liner("999999")
        self.assertIn("not found", s.lower())

    def test_one_liner_is_single_line(self):
        s = format_one_liner("360180")
        # No embedded newlines — must paste as one line
        self.assertNotIn("\n", s)

    def test_markdown_summary_has_all_sections(self):
        md = format_markdown_summary("360180")
        self.assertIn("# CLEVELAND CLINIC", md)
        self.assertIn("## Headline Financials", md)
        self.assertIn("## Peer Position", md)
        self.assertIn("## Multi-year Trend", md)
        # Table pipes present
        self.assertIn("| Metric | Value |", md)
        self.assertIn("|--------|", md)
        # Severity emoji for concerning/favorable lines
        self.assertTrue("🔴" in md or "🟢" in md)

    def test_markdown_summary_returns_not_found_msg_for_bad_ccn(self):
        md = format_markdown_summary("999999")
        self.assertIn("Not found", md)
        self.assertIn("# CCN 999999", md)

    def test_markdown_summary_watchlist_counts(self):
        md = format_markdown_summary("360180")
        self.assertIn("**Watchlist**", md)
        self.assertIn("concerning", md)

    def test_format_table_truncates_long_names(self):
        # Name column width is 38; anything longer should end with "…"
        rows = [{"ccn": "999999", "name": "X" * 100, "city": "Y", "state": "ZZ",
                 "beds": 100, "net_patient_revenue": 1e8, "medicare_day_pct": 0.2}]
        out = format_table(rows)
        self.assertIn("…", out)


class TestCLIMain(unittest.TestCase):
    """In-process CLI smoke tests using main(argv). (No-args behavior is
    covered by the subprocess test TestCLISubprocess.test_no_args_returns_2.)"""

    def test_ccn_returns_zero_and_prints_record(self):
        rc = lookup_main(["--ccn", "360180"])
        self.assertEqual(rc, 0)

    def test_missing_ccn_returns_nonzero(self):
        rc = lookup_main(["--ccn", "999999"])
        self.assertEqual(rc, 1)

    def test_json_output_is_valid_json(self):
        # Capture stdout
        import io
        buf = io.StringIO()
        saved = sys.stdout
        sys.stdout = buf
        try:
            rc = lookup_main(["--state", "OH", "--limit", "3", "--json"])
        finally:
            sys.stdout = saved
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertIsInstance(parsed, list)
        self.assertLessEqual(len(parsed), 3)

    def test_json_with_peers_returns_nested_structure(self):
        import io
        buf = io.StringIO()
        saved = sys.stdout
        sys.stdout = buf
        try:
            rc = lookup_main(["--ccn", "360180", "--peers", "--peers-n", "3", "--json"])
        finally:
            sys.stdout = saved
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertIsInstance(parsed, dict)
        self.assertIn("results", parsed)
        self.assertIn("peers", parsed)
        self.assertIn("peers", parsed["peers"])
        self.assertIn("percentiles", parsed["peers"])
        self.assertEqual(len(parsed["peers"]["peers"]), 3)

    def test_json_with_trend_returns_fiscal_years_and_signals(self):
        import io
        buf = io.StringIO()
        saved = sys.stdout
        sys.stdout = buf
        try:
            rc = lookup_main(["--ccn", "360180", "--trend", "--json"])
        finally:
            sys.stdout = saved
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertIn("trend", parsed)
        self.assertIn("fiscal_years", parsed["trend"])
        self.assertIn("signals", parsed["trend"])
        self.assertGreaterEqual(len(parsed["trend"]["fiscal_years"]), 2)
        self.assertGreater(len(parsed["trend"]["signals"]), 0)

    def test_plain_json_remains_bare_list_for_backcompat(self):
        """Existing shell pipelines (`--json | jq '.[0]'`) must still work."""
        import io
        buf = io.StringIO()
        saved = sys.stdout
        sys.stdout = buf
        try:
            rc = lookup_main(["--ccn", "360180", "--json"])
        finally:
            sys.stdout = saved
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertIsInstance(parsed, list)

    def test_invalid_beds_returns_nonzero(self):
        rc = lookup_main(["--state", "OH", "--beds", "not-a-range"])
        self.assertEqual(rc, 2)

    def test_trend_flag_prints_multi_year_block(self):
        import io
        buf = io.StringIO()
        saved = sys.stdout
        sys.stdout = buf
        try:
            rc = lookup_main(["--ccn", "360180", "--trend"])
        finally:
            sys.stdout = saved
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("Multi-year trend", out)
        # Shipped dataset carries 2020–2022; each year should show
        for y in ("2020", "2021", "2022"):
            self.assertIn(y, out)

    def test_one_liner_flag_emits_compact_summary(self):
        import io
        buf = io.StringIO()
        saved = sys.stdout
        sys.stdout = buf
        try:
            rc = lookup_main(["--ccn", "360180", "--one-liner"])
        finally:
            sys.stdout = saved
        self.assertEqual(rc, 0)
        out = buf.getvalue().rstrip("\n")
        # Single line, no newlines inside
        self.assertEqual(out.count("\n"), 0)
        self.assertIn("CLEVELAND CLINIC", out)
        # Full record block is suppressed when --one-liner is set
        self.assertNotIn("Location:", out)

    def test_ccns_file_csv_emits_one_liner_per_ccn(self):
        import io
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
            f.write("ccn\n360180\n220071\n")
            path = f.name
        buf = io.StringIO()
        saved = sys.stdout
        sys.stdout = buf
        try:
            rc = lookup_main(["--ccns-file", path, "--one-liner"])
        finally:
            sys.stdout = saved
        self.assertEqual(rc, 0)
        lines = [l for l in buf.getvalue().splitlines() if l.strip()]
        self.assertEqual(len(lines), 2)
        self.assertIn("CLEVELAND CLINIC", lines[0])
        self.assertIn("MASSACHUSETTS GENERAL", lines[1])

    def test_ccns_file_txt_skips_comments_and_blank_lines(self):
        import io
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
            f.write("# shortlist\n360180\n\n# another comment\n220071\n")
            path = f.name
        buf = io.StringIO()
        saved = sys.stdout
        sys.stdout = buf
        try:
            rc = lookup_main(["--ccns-file", path, "--one-liner"])
        finally:
            sys.stdout = saved
        self.assertEqual(rc, 0)
        lines = [l for l in buf.getvalue().splitlines() if l.strip()]
        self.assertEqual(len(lines), 2)

    def test_ccns_file_json_emits_list_of_payloads(self):
        import io
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
            f.write("ccn\n360180\n999999\n")
            path = f.name
        buf = io.StringIO()
        saved = sys.stdout
        sys.stdout = buf
        try:
            rc = lookup_main(["--ccns-file", path, "--one-liner", "--json"])
        finally:
            sys.stdout = saved
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertIsInstance(parsed, list)
        self.assertEqual(len(parsed), 2)
        # Found CCN has record + one_liner; missing CCN has error
        hit = next(p for p in parsed if p.get("ccn") == "360180")
        miss = next(p for p in parsed if p.get("ccn") == "999999")
        self.assertIn("record", hit)
        self.assertIn("one_liner", hit)
        self.assertIn("error", miss)

    def test_out_flag_writes_peers_and_trend_artifacts(self):
        import io
        import tempfile
        with tempfile.TemporaryDirectory() as outdir:
            buf = io.StringIO()
            saved = sys.stdout
            sys.stdout = buf
            try:
                rc = lookup_main([
                    "--ccn", "360180", "--peers", "--trend",
                    "--out", outdir,
                ])
            finally:
                sys.stdout = saved
            self.assertEqual(rc, 0)
            expected = [
                "peer_comparison.csv",
                "peer_target_percentiles.csv",
                "trend.csv",
                "trend_signals.csv",
            ]
            for name in expected:
                path = os.path.join(outdir, name)
                self.assertTrue(os.path.isfile(path), f"{name} not written")
            # Peers CSV must contain the matched peer CCNs (not just headers)
            import pandas as _pd
            peers = _pd.read_csv(os.path.join(outdir, "peer_comparison.csv"))
            self.assertGreater(len(peers), 0)
            self.assertIn("ccn", peers.columns)
            # Trend signals CSV must carry the severity column from Brick 30
            signals = _pd.read_csv(os.path.join(outdir, "trend_signals.csv"))
            self.assertIn("severity", signals.columns)

    def test_out_flag_ignored_without_section_flags(self):
        """--out alone (no --peers/--trend/etc.) shouldn't write any files."""
        import io
        import tempfile
        with tempfile.TemporaryDirectory() as outdir:
            buf = io.StringIO()
            saved = sys.stdout
            sys.stdout = buf
            try:
                rc = lookup_main(["--ccn", "360180", "--out", outdir])
            finally:
                sys.stdout = saved
            self.assertEqual(rc, 0)
            # Directory should be empty (no section flags → nothing to persist)
            self.assertEqual(os.listdir(outdir), [])

    def test_ccns_file_sort_by_npsr(self):
        """--sort-by npsr must put largest NPSR first."""
        import io
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
            # NYP > CCF > MGH in NPSR; write in reverse order
            f.write("ccn\n220071\n360180\n330101\n")
            path = f.name
        buf = io.StringIO()
        saved = sys.stdout
        sys.stdout = buf
        try:
            rc = lookup_main(["--ccns-file", path, "--one-liner", "--sort-by", "npsr"])
        finally:
            sys.stdout = saved
        self.assertEqual(rc, 0)
        lines = [l for l in buf.getvalue().splitlines() if l.strip()]
        # NYP should be first, MGH should be last
        self.assertIn("NEW YORK PRESBYTERIAN", lines[0])
        self.assertIn("MASSACHUSETTS GENERAL", lines[-1])

    def test_ccns_file_sort_by_beds(self):
        import io
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
            f.write("ccn\n220071\n360180\n330101\n")
            path = f.name
        buf = io.StringIO()
        saved = sys.stdout
        sys.stdout = buf
        try:
            rc = lookup_main(["--ccns-file", path, "--one-liner", "--sort-by", "beds"])
        finally:
            sys.stdout = saved
        self.assertEqual(rc, 0)
        lines = [l for l in buf.getvalue().splitlines() if l.strip()]
        # NYP ~2850 beds, CCF ~1326, MGH ~997
        self.assertIn("NEW YORK PRESBYTERIAN", lines[0])
        self.assertIn("MASSACHUSETTS GENERAL", lines[-1])

    def test_ccns_file_concerning_only_filters_out_missing(self):
        """--concerning-only drops not-found entries and anything with 0 concerning."""
        import io
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
            f.write("ccn\n360180\n999999\n")
            path = f.name
        buf = io.StringIO()
        saved = sys.stdout
        sys.stdout = buf
        try:
            rc = lookup_main(["--ccns-file", path, "--one-liner", "--concerning-only"])
        finally:
            sys.stdout = saved
        self.assertEqual(rc, 0)
        lines = [l for l in buf.getvalue().splitlines() if l.strip()]
        # CCF has concerning signals; 999999 was not found → dropped
        self.assertEqual(len(lines), 1)
        self.assertIn("CLEVELAND CLINIC", lines[0])
        self.assertNotIn("999999", buf.getvalue())

    def test_ccns_file_missing_returns_error(self):
        import io
        err = io.StringIO()
        saved_err = sys.stderr
        sys.stderr = err
        try:
            rc = lookup_main(["--ccns-file", "/nonexistent.csv", "--one-liner"])
        finally:
            sys.stderr = saved_err
        self.assertEqual(rc, 1)
        self.assertIn("not found", err.getvalue())

    def test_markdown_flag_emits_markdown_block(self):
        import io
        buf = io.StringIO()
        saved = sys.stdout
        sys.stdout = buf
        try:
            rc = lookup_main(["--ccn", "360180", "--markdown"])
        finally:
            sys.stdout = saved
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("# CLEVELAND CLINIC", out)
        # Full-record block is suppressed when --markdown is set
        self.assertNotIn("Report status:", out)

    def test_markdown_in_json_output(self):
        import io
        buf = io.StringIO()
        saved = sys.stdout
        sys.stdout = buf
        try:
            rc = lookup_main(["--ccn", "360180", "--markdown", "--json"])
        finally:
            sys.stdout = saved
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertIn("markdown", parsed)
        self.assertIn("# CLEVELAND CLINIC", parsed["markdown"])

    def test_one_liner_in_json_output(self):
        import io
        buf = io.StringIO()
        saved = sys.stdout
        sys.stdout = buf
        try:
            rc = lookup_main(["--ccn", "360180", "--one-liner", "--json"])
        finally:
            sys.stdout = saved
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertIn("one_liner", parsed)
        self.assertIn("CLEVELAND CLINIC", parsed["one_liner"])

    def test_trend_watchlist_summary_counts_severities(self):
        import io
        buf = io.StringIO()
        saved = sys.stdout
        sys.stdout = buf
        try:
            rc = lookup_main(["--ccn", "360180", "--trend"])
        finally:
            sys.stdout = saved
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("Watchlist:", out)
        # CCF 2020→2022: NPSR up (favorable), OpEx up (concerning), NI down (concerning)
        self.assertIn("concerning", out)
        self.assertIn("favorable", out)

    def test_trend_signals_colored_by_severity_when_forced(self):
        """FORCE_COLOR=1 → favorable rows carry green (32), concerning carry red (31)."""
        import io
        import os as _os
        buf = io.StringIO()
        saved = sys.stdout
        sys.stdout = buf
        prior_force = _os.environ.get("FORCE_COLOR")
        _os.environ["FORCE_COLOR"] = "1"
        try:
            rc = lookup_main(["--ccn", "360180", "--trend"])
        finally:
            sys.stdout = saved
            if prior_force is None:
                _os.environ.pop("FORCE_COLOR", None)
            else:
                _os.environ["FORCE_COLOR"] = prior_force
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        # Favorable NPSR growth should be green; concerning net income should be red
        self.assertIn("\033[32m", out)
        self.assertIn("\033[31m", out)

    def test_trend_signals_no_color_when_piped(self):
        """Piped stdout (captured buf, not TTY) → no ANSI codes by default."""
        import io
        buf = io.StringIO()
        saved = sys.stdout
        sys.stdout = buf
        try:
            rc = lookup_main(["--ccn", "360180", "--trend"])
        finally:
            sys.stdout = saved
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertNotIn("\033[", out)

    def test_trend_flag_includes_diligence_signals_block(self):
        import io
        buf = io.StringIO()
        saved = sys.stdout
        sys.stdout = buf
        try:
            rc = lookup_main(["--ccn", "360180", "--trend"])
        finally:
            sys.stdout = saved
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("Diligence signals", out)
        # At least one directional arrow must appear
        self.assertTrue(any(a in out for a in ("↑", "↓", "→")),
                        msg="Expected a direction arrow in trend signals")

    def test_peers_flag_prints_peer_set_and_percentiles(self):
        import io
        buf = io.StringIO()
        saved = sys.stdout
        sys.stdout = buf
        try:
            rc = lookup_main(["--ccn", "360180", "--peers", "--peers-n", "5"])
        finally:
            sys.stdout = saved
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("Peer set", out)
        self.assertIn("Target vs peers", out)
        # Brick 20 filter: no children's (CCN last4 3300-3399) in CCF peer set
        for line in out.splitlines():
            stripped = line.strip()
            if stripped[:6].isdigit() and stripped[:6] != "360180":
                last4 = int(stripped[2:6])
                self.assertFalse(3300 <= last4 <= 3399,
                                 msg=f"Children's CCN leaked into peer set: {stripped[:6]}")

    def test_peers_flag_unknown_ccn_is_not_a_crash(self):
        import io
        buf = io.StringIO()
        err = io.StringIO()
        saved_out, saved_err = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = buf, err
        try:
            rc = lookup_main(["--ccn", "999999", "--peers"])
        finally:
            sys.stdout, sys.stderr = saved_out, saved_err
        # --ccn 999999 returns 1 from the main lookup (no match) — peers
        # rendering shouldn't even fire. We're just confirming no exception.
        self.assertEqual(rc, 1)


class TestCLISubprocess(unittest.TestCase):
    """End-to-end subprocess tests for `rcm-lookup`."""

    @staticmethod
    def _run(args, timeout=30):
        return subprocess.run(
            [sys.executable, "-m", "rcm_mc.lookup"] + args,
            capture_output=True, text=True, timeout=timeout,
        )

    def test_help_exits_zero(self):
        result = self._run(["--help"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("rcm-lookup", result.stdout)

    def test_ccn_command(self):
        result = self._run(["--ccn", "360180"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("CLEVELAND CLINIC", result.stdout)
        self.assertIn("CCN 360180", result.stdout)

    def test_name_command_returns_table(self):
        result = self._run(["--name", "mount sinai", "--limit", "5"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("CCN", result.stdout)

    def test_no_args_returns_2(self):
        result = self._run([])
        self.assertEqual(result.returncode, 2)


