"""``rcm-lookup`` — browse CMS HCRIS from the command line.

Before an analyst types a 6-digit Medicare CCN into the intake wizard, they
often need to find it: "the Memorial in Dallas", "all Ohio teaching hospitals
with 500-1,200 beds", or just "what's the exact CCN for Cedars-Sinai?".
This command composes :mod:`rcm_mc.hcris` primitives into a fast terminal
browser: no DB, no server, no network — just the shipped public-data bundle.

Typical calls::

    rcm-lookup --ccn 360180              # full record for one hospital
    rcm-lookup --name "Mount Sinai"      # fuzzy name search, ranked
    rcm-lookup --state NY                # all NY hospitals, biggest first
    rcm-lookup --name memorial --state TX --beds 200-800
    rcm-lookup --state CA --limit 50 --json > ca_hospitals.json

Returns a non-zero exit if no hospitals match, so the command composes into
shell pipelines (``rcm-lookup --ccn X || echo "not found"``).
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


# ── Search ──────────────────────────────────────────────────────────────────

def _parse_beds_range(raw: Optional[str]) -> Optional[Tuple[int, int]]:
    """Parse a ``"MIN-MAX"`` or ``"MIN-"`` bed-range string to ``(lo, hi)``.

    Returns None for empty/None input. Raises ``ValueError`` on malformed input
    (argparse catches this into a user-visible message).
    """
    if not raw:
        return None
    s = str(raw).strip()
    if "-" not in s:
        # Single number = exact match (range of just that value)
        n = int(s)
        return (n, n)
    lo_s, _, hi_s = s.partition("-")
    lo = int(lo_s) if lo_s.strip() else 0
    hi = int(hi_s) if hi_s.strip() else 10_000  # open-ended upper
    if lo > hi:
        raise ValueError(f"beds range {lo}-{hi}: min greater than max")
    if lo < 0:
        raise ValueError(f"beds range {lo}-{hi}: negative bed count")
    return (lo, hi)


def search(
    *,
    ccn: Optional[str] = None,
    name: Optional[str] = None,
    state: Optional[str] = None,
    beds_range: Optional[Tuple[int, int]] = None,
    limit: int = 25,
) -> List[Dict[str, Any]]:
    """Unified HCRIS search.

    Resolution order:
    1. ``ccn`` wins (exact, single-result)
    2. ``name`` → fuzzy name search, optionally state-scoped
    3. ``state`` alone → browse by state sorted by bed count (biggest first)

    ``beds_range`` is applied as a post-filter on the candidate list after the
    primary search, then capped at ``limit``.
    """
    # Lazy imports so `rcm-lookup --help` never needs the HCRIS data file.
    from .hcris import browse_by_state, lookup_by_ccn, lookup_by_name

    if ccn:
        row = lookup_by_ccn(ccn)
        return [row] if row else []

    # Over-fetch by 2× so the bed-range post-filter has margin.
    raw_limit = max(int(limit) * 2, int(limit))
    if name:
        rows = lookup_by_name(name, state=state, limit=raw_limit)
    elif state:
        rows = browse_by_state(state, beds_range=beds_range, limit=int(limit))
        # beds_range already applied inside browse_by_state
        return rows
    else:
        return []

    if beds_range is not None:
        lo, hi = beds_range
        rows = [
            r for r in rows
            if isinstance(r.get("beds"), (int, float)) and lo <= r["beds"] <= hi
        ]
    return rows[: int(limit)]


# ── Formatting ──────────────────────────────────────────────────────────────

def _fmt_money(v: Any) -> str:
    """Compact money formatting with proper negative handling (``-$104M`` not ``$-104M``)."""
    if v is None:
        return "—"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "—"
    sign = "-" if f < 0 else ""
    af = abs(f)
    if af >= 1e9:
        return f"{sign}${af/1e9:.2f}B"
    if af >= 1e6:
        return f"{sign}${af/1e6:.0f}M"
    if af >= 1e3:
        return f"{sign}${af/1e3:.0f}K"
    return f"{sign}${af:.0f}"


def _fmt_pct(v: Any) -> str:
    if v is None:
        return "—"
    try:
        return f"{float(v)*100:.1f}%"
    except (TypeError, ValueError):
        return "—"


def _fmt_int(v: Any) -> str:
    if v is None:
        return "—"
    try:
        return f"{int(float(v)):,}"
    except (TypeError, ValueError):
        return "—"


def _fmt_hhi(v: Any) -> str:
    """Herfindahl index: decimal 0.333-1.000, shown to 3 places."""
    if v is None:
        return "—"
    try:
        return f"{float(v):.3f}"
    except (TypeError, ValueError):
        return "—"


def _truncate(s: Any, width: int) -> str:
    text = "" if s is None else str(s)
    if len(text) <= width:
        return text
    return text[: width - 1] + "…"


def format_one_hospital(row: Dict[str, Any]) -> str:
    """Multi-line detail block for a single hospital's full record."""
    name = row.get("name") or "?"
    ccn = row.get("ccn") or "?"
    loc = f"{row.get('city', '?')}, {row.get('state', '?')} {row.get('zip') or ''}".strip()
    fy = row.get("fiscal_year")
    fy_bgn = row.get("fy_bgn_dt") or "?"
    fy_end = row.get("fy_end_dt") or "?"
    rpt_stus = row.get("rpt_stus_cd") or "?"

    lines = [
        f"{name}  (CCN {ccn})",
        "─" * min(80, max(len(name) + 14, 40)),
        f"  Location:          {loc}",
        f"  Beds:              {_fmt_int(row.get('beds'))}",
        f"  Net Patient Rev:   {_fmt_money(row.get('net_patient_revenue'))}",
        f"  Operating expense: {_fmt_money(row.get('operating_expenses'))}",
        f"  Net income:        {_fmt_money(row.get('net_income'))}",
        f"  Medicare day %:    {_fmt_pct(row.get('medicare_day_pct'))}",
        f"  Medicaid day %:    {_fmt_pct(row.get('medicaid_day_pct'))}",
        f"  Total patient days:{_fmt_int(row.get('total_patient_days'))}",
        f"  Fiscal year:       FY{fy}  ({fy_bgn} → {fy_end})" if fy else f"  Fiscal period:     {fy_bgn} → {fy_end}",
        f"  Report status:     {rpt_stus}  (3=Audited, 2=Settled, 1=As-submitted)",
    ]
    return "\n".join(lines)


# Default columns for list view. Order matches reading priority: pick target → scale → mix.
_LIST_COLUMNS = [
    ("ccn",                   "CCN",        6,   "left"),
    ("name",                  "Name",       38,  "left"),
    ("city",                  "City",       18,  "left"),
    ("state",                 "ST",         2,   "left"),
    ("beds",                  "Beds",       6,   "right"),
    ("net_patient_revenue",   "NPSR",       8,   "right"),
    ("medicare_day_pct",      "Med %",      6,   "right"),
]


def format_table(rows: List[Dict[str, Any]]) -> str:
    """Fixed-width terminal table for a list of hospitals. No external deps."""
    if not rows:
        return "(no hospitals matched)"

    def _render_cell(row: Dict[str, Any], key: str) -> str:
        v = row.get(key)
        if key == "beds":
            return _fmt_int(v)
        if key in ("net_patient_revenue", "operating_expenses", "net_income"):
            return _fmt_money(v)
        if key in ("medicare_day_pct", "medicaid_day_pct"):
            return _fmt_pct(v)
        return str(v) if v is not None else "—"

    # Build header + separator + data rows with fixed widths.
    parts: List[str] = []
    header = []
    sep = []
    for _, hdr, width, align in _LIST_COLUMNS:
        header.append(hdr.ljust(width) if align == "left" else hdr.rjust(width))
        sep.append("─" * width)
    parts.append("  ".join(header))
    parts.append("  ".join(sep))

    for row in rows:
        cells = []
        for key, _, width, align in _LIST_COLUMNS:
            rendered = _truncate(_render_cell(row, key), width)
            cells.append(rendered.ljust(width) if align == "left" else rendered.rjust(width))
        parts.append("  ".join(cells))
    return "\n".join(parts)


# ── CLI entry ──────────────────────────────────────────────────────────────

def _build_parser(prog: str = "rcm-lookup") -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog=prog,
        description="Search CMS HCRIS (~6,000 US hospitals) from the command line.",
        epilog=(
            "Examples:\n"
            "  rcm-lookup --ccn 360180                       # full record\n"
            "  rcm-lookup --name 'Mount Sinai'               # fuzzy name search\n"
            "  rcm-lookup --state TX --beds 200-600          # browse by size\n"
            "  rcm-lookup --state CA --limit 50 --json       # machine-readable\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--ccn", default=None, help="6-digit Medicare Provider Number (exact match)")
    ap.add_argument("--name", default=None, help="Case-insensitive substring search (fuzzy-ranked)")
    ap.add_argument("--state", default=None, help="Two-letter USPS state code to scope results")
    ap.add_argument(
        "--beds", default=None, metavar="MIN-MAX",
        help="Bed-count filter, e.g. 200-600, 500- (500+), -1000 (≤1000)",
    )
    ap.add_argument("--limit", type=int, default=25, help="Max rows to display (default 25)")
    ap.add_argument("--json", action="store_true", help="Emit JSON instead of a table")
    ap.add_argument(
        "--ein", default=None,
        help=(
            "Optional: analyst-supplied IRS EIN for a non-profit target. When "
            "combined with --ccn, adds an IRS 990 cross-check (ProPublica API)."
        ),
    )
    ap.add_argument(
        "--mrf", default=None,
        help=(
            "Optional: path to a Hospital Price Transparency machine-readable "
            "file (CSV or JSON). Prints payer / rate summary."
        ),
    )
    ap.add_argument(
        "--trend", action="store_true",
        help=(
            "With --ccn, print a multi-year HCRIS trend table (one row per "
            "fiscal year on file)."
        ),
    )
    ap.add_argument(
        "--peers", action="store_true",
        help=(
            "With --ccn, print a peer set ranked by similarity + the target's "
            "percentile on each KPI."
        ),
    )
    ap.add_argument(
        "--peers-n", type=int, default=15,
        help="Number of peers to surface (default 15).",
    )
    ap.add_argument(
        "--peers-all-states", action="store_true",
        help="Disable same-state preference when picking peers.",
    )
    ap.add_argument(
        "--one-liner", action="store_true",
        help=(
            "With --ccn, print a single-line diligence summary suitable for "
            "pasting into Slack or email (instead of the full record)."
        ),
    )
    ap.add_argument(
        "--markdown", action="store_true",
        help=(
            "With --ccn, emit a memo-ready markdown block (identity, "
            "financials, peer table, trend) — paste into Notion/Obsidian/"
            "GitHub."
        ),
    )
    ap.add_argument(
        "--ccns-file", default=None, metavar="PATH",
        help=(
            "Batch mode: read a CSV or TXT file of CCNs (header 'ccn' for CSV, "
            "one CCN per line for TXT) and emit one summary per target. Works "
            "with --one-liner and --json."
        ),
    )
    ap.add_argument(
        "--concerning-only", action="store_true",
        help=(
            "Batch mode only. Emit only targets with ≥1 concerning trend "
            "signal — useful for triaging a pipeline."
        ),
    )
    ap.add_argument(
        "--sort-by", default=None, choices=["concerning", "npsr", "beds"],
        help=(
            "Batch mode only. Sort output by key: concerning = count of "
            "concerning signals (desc), npsr = net patient revenue (desc), "
            "beds = bed count (desc)."
        ),
    )
    ap.add_argument(
        "--out", default=None, metavar="DIR",
        help=(
            "Write artifact files (peer_comparison.csv, trend.csv, "
            "trend_signals.csv, mrf_summary.json, irs_990.json) to DIR for "
            "any --peers / --trend / --mrf / --ein sections requested."
        ),
    )
    return ap


def main(argv: Optional[List[str]] = None, prog: str = "rcm-lookup") -> int:
    ap = _build_parser(prog=prog)
    args = ap.parse_args(argv)

    # Batch mode short-circuits the normal single-target pipeline
    if args.ccns_file:
        try:
            ccns = _read_ccns_file(args.ccns_file)
        except FileNotFoundError as exc:
            sys.stderr.write(f"{exc}\n")
            return 1
        return _run_batch(ccns, args)

    if not any([args.ccn, args.name, args.state]):
        ap.print_help()
        sys.stderr.write("\nError: provide at least one of --ccn, --name, or --state\n")
        return 2

    try:
        beds_range = _parse_beds_range(args.beds)
    except ValueError as exc:
        sys.stderr.write(f"invalid --beds value: {exc}\n")
        return 2

    try:
        results = search(
            ccn=args.ccn, name=args.name, state=args.state,
            beds_range=beds_range, limit=args.limit,
        )
    except FileNotFoundError as exc:
        sys.stderr.write(f"lookup failed: {exc}\n")
        return 1

    if not results:
        sys.stderr.write("(no hospitals matched)\n")
        return 1

    if args.json:
        payload: Dict[str, Any] = {"results": results}
        # Fold optional sections alongside results so machine consumers
        # (Slack bots, LLM tools, shell pipelines) get structured data.
        if args.ccn and len(results) == 1:
            if args.one_liner:
                payload["one_liner"] = format_one_liner(args.ccn)
            if args.markdown:
                payload["markdown"] = format_markdown_summary(args.ccn)
            if args.trend:
                payload["trend"] = _trend_payload(args.ccn)
            if args.peers:
                payload["peers"] = _peers_payload(
                    args.ccn, n=args.peers_n,
                    same_state_preferred=not args.peers_all_states,
                )
            if args.ein:
                payload["irs_990_cross_check"] = _990_payload(args.ccn, args.ein)
            if args.mrf:
                payload["mrf_summary"] = _mrf_payload(args.mrf)
        # Back-compat: when the only payload is the hospital list, emit bare
        # list so existing shell pipelines (`--json > file; jq '.'`) still work.
        out = results if set(payload.keys()) == {"results"} else payload
        sys.stdout.write(json.dumps(out, indent=2, default=str) + "\n")
    elif args.ccn and len(results) == 1 and args.markdown:
        # Markdown deal-memo block — pastes into Notion / Obsidian / GitHub
        sys.stdout.write(format_markdown_summary(args.ccn) + "\n")
    elif args.ccn and len(results) == 1 and args.one_liner:
        # Just the one-liner — perfect for piping into clipboard / paste tools
        sys.stdout.write(format_one_liner(args.ccn) + "\n")
    elif args.ccn and len(results) == 1:
        # Single-record view — full detail
        sys.stdout.write(format_one_hospital(results[0]) + "\n")
        if args.trend:
            sys.stdout.write("\n" + _render_trend_table(args.ccn))
        if args.peers:
            sys.stdout.write("\n" + _render_peer_set(
                args.ccn, n=args.peers_n,
                same_state_preferred=not args.peers_all_states,
            ))
        if args.ein:
            sys.stdout.write("\n" + _render_990_cross_check(args.ccn, args.ein))
        if args.mrf:
            sys.stdout.write("\n" + _render_mrf_summary(args.mrf))
        # Optional: persist the requested sections to disk
        if args.out and any([args.peers, args.trend, args.mrf, args.ein]):
            written = _write_artifacts(args.ccn, args.out, args)
            for p in written:
                sys.stdout.write(f"  wrote: {p}\n")
    else:
        sys.stdout.write(format_table(results) + "\n")
        if len(results) == args.limit:
            sys.stdout.write(
                f"\n(showing {args.limit}; increase with --limit, or narrow with --state / --beds)\n"
            )
    return 0


def _write_artifacts(ccn: str, outdir: str, args: argparse.Namespace) -> List[str]:
    """Persist requested sections for ``ccn`` to ``outdir``. Returns paths written.

    Each section writes only when its flag is set — matches the terminal
    rendering exactly, so an analyst gets the same data on disk as on screen.
    Failures degrade: a section that can't be fetched emits a ``*_error.txt``
    instead of blowing up the whole command.
    """
    import json as _json
    import os as _os

    _os.makedirs(outdir, exist_ok=True)
    written: List[str] = []

    def _save(name: str, writer) -> None:
        path = _os.path.join(outdir, name)
        try:
            writer(path)
            written.append(path)
        except (ValueError, FileNotFoundError, OSError) as exc:
            err_path = _os.path.join(outdir, name.rsplit(".", 1)[0] + "_error.txt")
            with open(err_path, "w", encoding="utf-8") as f:
                f.write(f"{type(exc).__name__}: {exc}\n")
            written.append(err_path)

    if args.peers:
        from .hcris import compute_peer_percentiles, find_peers
        def _peers_writer(path):
            peers = find_peers(
                ccn, n=args.peers_n,
                same_state_preferred=not args.peers_all_states,
            )
            peers.to_csv(path, index=False)
            pcts = compute_peer_percentiles(ccn, peers)
            pcts.to_csv(_os.path.join(outdir, "peer_target_percentiles.csv"), index=False)
        _save("peer_comparison.csv", _peers_writer)
        # peer_target_percentiles.csv was written inside the same call
        if _os.path.isfile(_os.path.join(outdir, "peer_target_percentiles.csv")):
            written.append(_os.path.join(outdir, "peer_target_percentiles.csv"))

    if args.trend:
        from .hcris import get_trend, trend_signals
        _save("trend.csv", lambda p: get_trend(ccn).to_csv(p, index=False))
        _save("trend_signals.csv", lambda p: trend_signals(ccn).to_csv(p, index=False))

    if args.mrf:
        from ..infra.transparency import parse_mrf
        def _mrf_writer(path):
            summary = parse_mrf(args.mrf)
            with open(path, "w", encoding="utf-8") as f:
                _json.dump(summary.to_dict(), f, indent=2, default=str)
        _save("mrf_summary.json", _mrf_writer)

    if args.ein:
        from .irs990 import cross_check_ccn
        def _990_writer(path):
            report = cross_check_ccn(ccn, args.ein)
            with open(path, "w", encoding="utf-8") as f:
                _json.dump(report.to_dict(), f, indent=2, default=str)
        _save("irs_990.json", _990_writer)

    # De-dup in case peers path got appended twice
    seen = set()
    uniq: List[str] = []
    for p in written:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    return uniq


def _run_batch(ccns: List[str], args: argparse.Namespace) -> int:
    """Emit per-CCN summaries. Returns 1 if no CCNs resolved, else 0."""
    from .hcris import lookup_by_ccn, trend_signals

    if not ccns:
        sys.stderr.write("No CCNs found in input file.\n")
        return 1

    # Resolve each CCN once, collecting record + concerning count for
    # downstream filter / sort. Missing CCNs flow through with record=None.
    resolved: List[Dict[str, Any]] = []
    for ccn in ccns:
        row = lookup_by_ccn(ccn)
        n_concerning = 0
        if row is not None and (args.concerning_only or args.sort_by == "concerning"):
            sig = trend_signals(ccn)
            if not sig.empty and "severity" in sig.columns:
                n_concerning = int((sig["severity"] == "concerning").sum())
        resolved.append({"ccn": ccn, "record": row, "n_concerning": n_concerning})

    # Filter: drop targets with no concerning signals (only when flag is set)
    if args.concerning_only:
        resolved = [r for r in resolved if r["n_concerning"] > 0]

    # Sort: applies only to records that were successfully resolved.
    # `None` records sort to the end so "not found" lines stay in input order.
    if args.sort_by == "concerning":
        resolved.sort(key=lambda r: (-r["n_concerning"], r["ccn"]))
    elif args.sort_by == "npsr":
        resolved.sort(
            key=lambda r: -float(((r["record"] or {}).get("net_patient_revenue")) or 0)
        )
    elif args.sort_by == "beds":
        resolved.sort(
            key=lambda r: -float(((r["record"] or {}).get("beds")) or 0)
        )

    # --json: emit a list of per-target payloads
    if args.json:
        payloads: List[Dict[str, Any]] = []
        for r in resolved:
            ccn = r["ccn"]
            row = r["record"]
            entry: Dict[str, Any] = {"ccn": ccn}
            if row is None:
                entry["error"] = "not found"
            else:
                entry["record"] = row
                if args.one_liner:
                    entry["one_liner"] = format_one_liner(ccn)
                if args.trend:
                    entry["trend"] = _trend_payload(ccn)
                if args.peers:
                    entry["peers"] = _peers_payload(
                        ccn, n=args.peers_n,
                        same_state_preferred=not args.peers_all_states,
                    )
            payloads.append(entry)
        sys.stdout.write(json.dumps(payloads, indent=2, default=str) + "\n")
        return 0 if any("record" in p for p in payloads) else 1

    # --one-liner (default batch format): one line per target
    hit_any = False
    for r in resolved:
        ccn = r["ccn"]
        row = r["record"]
        if row is None:
            sys.stdout.write(f"CCN {ccn}: not found\n")
            continue
        hit_any = True
        if args.one_liner:
            sys.stdout.write(format_one_liner(ccn) + "\n")
        else:
            # Without --one-liner, emit a minimal compact table row per CCN
            sys.stdout.write(format_table([row]).splitlines()[-1] + "\n")
    return 0 if hit_any else 1


def _render_trend_table(ccn: str) -> str:
    """Multi-year HCRIS trend table + diligence signals for one CCN."""
    from .hcris import get_trend, trend_signals

    df = get_trend(ccn)
    if df.empty:
        return f"No trend data for CCN {ccn}.\n"
    if len(df) < 2:
        return f"Only one fiscal year on file for CCN {ccn}; no trend to show.\n"

    # Compact columns for terminal readability
    def _fmt_money(v):
        if v is None or (isinstance(v, float) and v != v):
            return "—"
        try:
            f = float(v)
        except (TypeError, ValueError):
            return "—"
        sign = "-" if f < 0 else ""
        af = abs(f)
        if af >= 1e9:
            return f"{sign}${af/1e9:.2f}B"
        if af >= 1e6:
            return f"{sign}${af/1e6:.0f}M"
        return f"{sign}${af:,.0f}"

    def _fmt_int(v):
        if v is None or (isinstance(v, float) and v != v):
            return "—"
        try:
            return f"{int(float(v)):,}"
        except (TypeError, ValueError):
            return "—"

    def _fmt_pct(v):
        if v is None or (isinstance(v, float) and v != v):
            return "—"
        try:
            return f"{float(v)*100:.1f}%"
        except (TypeError, ValueError):
            return "—"

    lines = [
        f"Multi-year trend — CCN {ccn}",
        "─" * 60,
        f"  {'Year':>6s} {'Beds':>6s} {'NPSR':>8s} {'OpEx':>8s} {'NetInc':>8s} {'Med%':>6s}",
    ]
    for _, row in df.iterrows():
        lines.append(
            f"  {int(row.get('fiscal_year', 0)):>6d} "
            f"{_fmt_int(row.get('beds')):>6s} "
            f"{_fmt_money(row.get('net_patient_revenue')):>8s} "
            f"{_fmt_money(row.get('operating_expenses')):>8s} "
            f"{_fmt_money(row.get('net_income')):>8s} "
            f"{_fmt_pct(row.get('medicare_day_pct')):>6s}"
        )

    # Year-over-year diligence signals — first fiscal year on file → last.
    signals = trend_signals(ccn)
    if not signals.empty:
        from ..infra._terminal import paint
        first_year = int(signals.iloc[0]["start_year"])
        last_year = int(signals.iloc[0]["end_year"])
        lines.append("")
        lines.append(f"  Diligence signals ({first_year}→{last_year}):")
        arrow = {"up": "↑", "down": "↓", "flat": "→"}
        severity_color = {"concerning": "red", "favorable": "green", "neutral": None}
        for _, s in signals.iterrows():
            metric = str(s["metric"])
            label = metric.replace("_", " ")
            start_v = s["start_value"]
            end_v = s["end_value"]
            direction = arrow.get(str(s["direction"]), "·")
            if pd.notna(s["pts_change"]):
                delta = f"{s['pts_change']:+.1f} pts"
                start_f = _fmt_pct(start_v)
                end_f = _fmt_pct(end_v)
            else:
                pct = s.get("pct_change")
                delta = f"{pct*100:+.1f}%" if pd.notna(pct) else "—"
                if metric in ("total_patient_days", "beds"):
                    start_f = _fmt_int(start_v)
                    end_f = _fmt_int(end_v)
                else:
                    start_f = _fmt_money(start_v)
                    end_f = _fmt_money(end_v)
            row_text = f"    {direction} {label:<24s} {delta:>10s}   ({start_f} → {end_f})"
            color = severity_color.get(str(s.get("severity") or "neutral"))
            if color:
                row_text = paint(row_text, color=color)
            lines.append(row_text)

        # Watchlist count — tells a partner in one line whether to dig in
        severities = signals["severity"].tolist() if "severity" in signals.columns else []
        n_concerning = sum(1 for x in severities if x == "concerning")
        n_favorable = sum(1 for x in severities if x == "favorable")
        summary_parts: List[str] = []
        if n_concerning:
            txt = f"{n_concerning} concerning"
            summary_parts.append(paint(txt, color="red") if n_concerning else txt)
        if n_favorable:
            txt = f"{n_favorable} favorable"
            summary_parts.append(paint(txt, color="green") if n_favorable else txt)
        if summary_parts:
            lines.append(f"    Watchlist: {', '.join(summary_parts)}")
        else:
            lines.append("    Watchlist: no directional signals flagged")
    return "\n".join(lines) + "\n"


def format_markdown_summary(ccn: str) -> str:
    """A memo-ready markdown block for one hospital.

    Composed of four sections, each optional: identity, headline financials,
    peer position, multi-year trend. Sections drop gracefully when data is
    missing (e.g., target without peer-matchable beds → no peer table).

    Output is Commonmark-compatible so it renders in Notion, Obsidian,
    GitHub, and most markdown tooling. Severity is encoded via emoji (🔴 /
    🟢 / 🟡) since markdown has no color primitive.
    """
    from .hcris import (
        compute_peer_percentiles, find_peers, lookup_by_ccn, trend_signals,
    )

    row = lookup_by_ccn(ccn)
    if row is None:
        return f"# CCN {ccn}\n\n*Not found in HCRIS.*\n"

    lines: List[str] = []

    # ── Identity header ──
    name = str(row.get("name") or "?").strip()
    lines.append(f"# {name}")
    lines.append("")
    meta_bits = [f"**CCN**: {row.get('ccn')}"]
    if row.get("city") or row.get("state"):
        loc = f"{row.get('city') or '?'}, {row.get('state') or '?'}"
        meta_bits.append(f"**Location**: {loc}")
    if pd.notna(row.get("beds")):
        meta_bits.append(f"**Beds**: {int(float(row['beds'])):,}")
    fy = row.get("fiscal_year")
    if pd.notna(fy):
        meta_bits.append(f"**Fiscal year**: FY{int(fy)}")
    lines.append(" · ".join(meta_bits))
    lines.append("")

    # ── Headline financials ──
    fin_rows = [
        ("Net Patient Revenue", _fmt_money(row.get("net_patient_revenue"))),
        ("Operating Expenses",  _fmt_money(row.get("operating_expenses"))),
        ("Net Income",          _fmt_money(row.get("net_income"))),
    ]
    ni = row.get("net_income")
    npsr = row.get("net_patient_revenue")
    if pd.notna(ni) and pd.notna(npsr) and float(npsr) != 0:
        margin = float(ni) / float(npsr)
        fin_rows.append(("Operating Margin", f"{margin*100:.1f}%"))
    if pd.notna(row.get("medicare_day_pct")):
        fin_rows.append(("Medicare Day %", _fmt_pct(row["medicare_day_pct"])))
    if pd.notna(row.get("medicaid_day_pct")):
        fin_rows.append(("Medicaid Day %", _fmt_pct(row["medicaid_day_pct"])))

    lines.append("## Headline Financials")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    for label, val in fin_rows:
        lines.append(f"| {label} | {val} |")
    lines.append("")

    # ── Peer position (best-effort; skip if not matchable) ──
    try:
        peers = find_peers(ccn, n=15)
        if not peers.empty:
            pcts = compute_peer_percentiles(ccn, peers)
            lines.append(f"## Peer Position (n={len(peers)} matched hospitals)")
            lines.append("")
            lines.append("| KPI | Target | P10 | Median | P90 | Rank |")
            lines.append("|-----|--------|-----|--------|-----|------|")
            for _, r in pcts.iterrows():
                kpi_name = str(r["kpi"])
                if kpi_name.endswith("_pct") or kpi_name == "operating_margin":
                    fmt = _fmt_pct
                elif kpi_name in ("beds", "total_patient_days"):
                    fmt = _fmt_int
                elif kpi_name == "payer_mix_hhi":
                    fmt = _fmt_hhi
                else:
                    fmt = _fmt_money
                tp = r.get("target_percentile")
                rank = "—" if tp is None or (isinstance(tp, float) and tp != tp) else f"{tp:.0f}th"
                lines.append(
                    f"| {kpi_name.replace('_', ' ')} | "
                    f"{fmt(r.get('target'))} | "
                    f"{fmt(r.get('peer_p10'))} | "
                    f"{fmt(r.get('peer_median'))} | "
                    f"{fmt(r.get('peer_p90'))} | "
                    f"{rank} |"
                )
            lines.append("")
    except ValueError:
        pass  # target not peer-matchable

    # ── Multi-year trend signals ──
    sig = trend_signals(ccn)
    if not sig.empty and "severity" in sig.columns:
        sy = int(sig.iloc[0]["start_year"])
        ey = int(sig.iloc[0]["end_year"])
        lines.append(f"## Multi-year Trend ({sy}→{ey})")
        lines.append("")
        n_c = int((sig["severity"] == "concerning").sum())
        n_f = int((sig["severity"] == "favorable").sum())
        watchlist_bits = []
        if n_c:
            watchlist_bits.append(f"🔴 {n_c} concerning")
        if n_f:
            watchlist_bits.append(f"🟢 {n_f} favorable")
        if watchlist_bits:
            lines.append(f"**Watchlist**: {' · '.join(watchlist_bits)}")
            lines.append("")
        emoji = {"concerning": "🔴", "favorable": "🟢", "neutral": "🟡"}
        arrow = {"up": "↑", "down": "↓", "flat": "→"}
        for _, s in sig.iterrows():
            metric = str(s["metric"]).replace("_", " ")
            direction = arrow.get(str(s["direction"]), "·")
            tag = emoji.get(str(s.get("severity") or "neutral"), "")
            if pd.notna(s["pts_change"]):
                delta = f"{s['pts_change']:+.1f} pts"
            else:
                pct = s.get("pct_change")
                delta = f"{pct*100:+.1f}%" if pd.notna(pct) else "—"
            lines.append(f"- {tag} {direction} **{metric}** {delta}")
        lines.append("")

    return "\n".join(lines)


def _read_ccns_file(path: str) -> List[str]:
    """Read a list of CCNs from CSV (column 'ccn') or plain text (one per line).

    Lines starting with ``#`` are treated as comments. Blank lines are skipped.
    Values are stripped but NOT zero-padded here — ``lookup_by_ccn`` handles
    that downstream so the caller sees exactly what they wrote in the file.
    """
    import csv as _csv
    import os as _os

    if not _os.path.isfile(path):
        raise FileNotFoundError(f"CCNs file not found: {path}")

    # CSV if it has a .csv extension or the first non-comment line contains commas
    ext = _os.path.splitext(path)[1].lower()
    with open(path, encoding="utf-8") as f:
        text = f.read()

    if ext == ".csv" or (text and "," in text.splitlines()[0]):
        ccns: List[str] = []
        reader = _csv.DictReader(text.splitlines())
        if reader.fieldnames and "ccn" in reader.fieldnames:
            for row in reader:
                v = (row.get("ccn") or "").strip()
                if v and not v.startswith("#"):
                    ccns.append(v)
            return ccns
        # Fall through: no 'ccn' column — treat as one-per-line

    return [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def format_one_liner(ccn: str) -> str:
    """A single-line diligence summary — meant for pasting into Slack / email.

    Example:
        CLEVELAND CLINIC HOSPITAL (CCN 360180, OH, 1,326 beds). FY2022 NPSR
        $6.38B, op margin -17.7%, 22.5% Medicare. Peer rank: NPSR 100th, margin
        20th of 15 Ohio AMC peers. Trend 2020→2022: 2 concerning, 1 favorable.

    Gracefully degrades — each clause is independent, so missing peer data or
    single-year data just drops the corresponding clause rather than blanking
    the whole line.
    """
    from .hcris import (
        compute_peer_percentiles, find_peers, lookup_by_ccn, trend_signals,
    )

    row = lookup_by_ccn(ccn)
    if row is None:
        return f"CCN {ccn}: not found in HCRIS."

    clauses: List[str] = []
    name = str(row.get("name") or "?").strip()
    state = str(row.get("state") or "?").strip()
    beds = row.get("beds")
    fy = row.get("fiscal_year")
    head = f"{name} (CCN {row.get('ccn')}, {state}"
    if beds is not None and pd.notna(beds):
        head += f", {int(float(beds)):,} beds"
    head += ")"
    clauses.append(head)

    # Headline financials clause
    fin_parts: List[str] = []
    if fy is not None and pd.notna(fy):
        fin_parts.append(f"FY{int(fy)}")
    if pd.notna(row.get("net_patient_revenue")):
        fin_parts.append(f"NPSR {_fmt_money(row['net_patient_revenue'])}")
    # Margin: derive on the fly (hcris._add_derived_kpis expects DataFrame)
    ni = row.get("net_income")
    npsr = row.get("net_patient_revenue")
    if (pd.notna(ni) and pd.notna(npsr) and float(npsr) != 0):
        margin = float(ni) / float(npsr)
        fin_parts.append(f"op margin {margin*100:.1f}%")
    if pd.notna(row.get("medicare_day_pct")):
        fin_parts.append(f"{float(row['medicare_day_pct'])*100:.1f}% Medicare")
    if fin_parts:
        clauses.append(", ".join(fin_parts))

    # Peer rank clause — rank on the two diligence-critical KPIs
    try:
        peers = find_peers(ccn, n=15)
        if not peers.empty:
            pcts = compute_peer_percentiles(ccn, peers)
            npsr_rank = pcts[pcts["kpi"] == "net_patient_revenue"]
            margin_rank = pcts[pcts["kpi"] == "operating_margin"]
            peer_bits: List[str] = []
            if not npsr_rank.empty and pd.notna(npsr_rank.iloc[0]["target_percentile"]):
                peer_bits.append(f"NPSR {int(npsr_rank.iloc[0]['target_percentile'])}th")
            if not margin_rank.empty and pd.notna(margin_rank.iloc[0]["target_percentile"]):
                peer_bits.append(f"margin {int(margin_rank.iloc[0]['target_percentile'])}th")
            if peer_bits:
                clauses.append(f"Peer rank: {', '.join(peer_bits)} (n={len(peers)})")
    except ValueError:
        pass  # target not peer-matchable (e.g., no beds) — just drop the clause

    # Trend watchlist clause
    sig = trend_signals(ccn)
    if not sig.empty and "severity" in sig.columns:
        n_c = int((sig["severity"] == "concerning").sum())
        n_f = int((sig["severity"] == "favorable").sum())
        sy = int(sig.iloc[0]["start_year"])
        ey = int(sig.iloc[0]["end_year"])
        parts = []
        if n_c:
            parts.append(f"{n_c} concerning")
        if n_f:
            parts.append(f"{n_f} favorable")
        if parts:
            clauses.append(f"Trend {sy}→{ey}: {', '.join(parts)}")

    return ". ".join(clauses) + "."


def _df_to_records(df: "pd.DataFrame") -> List[Dict[str, Any]]:
    """DataFrame → list of dicts with NaN → None for JSON safety."""
    if df is None or df.empty:
        return []
    return [{k: (None if (isinstance(v, float) and pd.isna(v)) else v)
             for k, v in row.items()}
            for row in df.to_dict(orient="records")]


def _trend_payload(ccn: str) -> Dict[str, Any]:
    """Structured trend data: raw year-by-year table + computed signals."""
    from .hcris import get_trend, trend_signals
    df = get_trend(ccn)
    signals = trend_signals(ccn)
    return {
        "fiscal_years": _df_to_records(df),
        "signals": _df_to_records(signals),
    }


def _peers_payload(ccn: str, n: int, same_state_preferred: bool) -> Dict[str, Any]:
    """Structured peer set + percentile table; matches the CLI text output."""
    from .hcris import compute_peer_percentiles, find_peers
    try:
        peers = find_peers(ccn, n=n, same_state_preferred=same_state_preferred)
    except ValueError as exc:
        return {"error": str(exc)}
    pcts = compute_peer_percentiles(ccn, peers) if not peers.empty else None
    return {
        "peers": _df_to_records(peers),
        "percentiles": _df_to_records(pcts),
    }


def _990_payload(ccn: str, ein: str) -> Dict[str, Any]:
    from .irs990 import IRS990FetchError, cross_check_ccn
    try:
        return cross_check_ccn(ccn, ein).to_dict()
    except (ValueError, IRS990FetchError) as exc:
        return {"error": str(exc)}


def _mrf_payload(path: str) -> Dict[str, Any]:
    from ..infra.transparency import parse_mrf
    try:
        return parse_mrf(path).to_dict()
    except (FileNotFoundError, ValueError) as exc:
        return {"error": str(exc)}


def _render_peer_set(ccn: str, n: int = 15, same_state_preferred: bool = True) -> str:
    """Peer set + per-KPI percentile block for one CCN."""
    from .hcris import compute_peer_percentiles, find_peers

    try:
        peers = find_peers(ccn, n=n, same_state_preferred=same_state_preferred)
    except ValueError as exc:
        return f"Peer lookup unavailable: {exc}\n"
    if peers.empty:
        return f"No peers found for CCN {ccn}.\n"

    lines = [
        f"Peer set — CCN {ccn}  ({len(peers)} hospitals)",
        "─" * 72,
        f"  {'CCN':>6s}  {'Name':<38s}  {'ST':<2s}  {'Beds':>6s}  {'NPSR':>8s}  {'Med%':>6s}",
    ]
    for _, row in peers.iterrows():
        lines.append(
            f"  {str(row.get('ccn') or '?'):>6s}  "
            f"{_truncate(row.get('name'), 38):<38s}  "
            f"{str(row.get('state') or '??'):<2s}  "
            f"{_fmt_int(row.get('beds')):>6s}  "
            f"{_fmt_money(row.get('net_patient_revenue')):>8s}  "
            f"{_fmt_pct(row.get('medicare_day_pct')):>6s}"
        )

    # Percentile block — target vs peer distribution
    pcts = compute_peer_percentiles(ccn, peers)
    if not pcts.empty:
        from ..infra._terminal import paint
        lines.append("")
        lines.append("  Target vs peers:")
        lines.append(
            f"    {'KPI':<22s} {'Target':>12s}  {'P10':>10s}  {'Median':>10s}  "
            f"{'P90':>10s}  {'Rank':>5s}"
        )
        for _, row in pcts.iterrows():
            kpi = str(row["kpi"])
            if kpi.endswith("_pct") or kpi == "operating_margin":
                fmt = _fmt_pct
            elif kpi in ("beds", "total_patient_days"):
                fmt = _fmt_int
            elif kpi == "payer_mix_hhi":
                fmt = _fmt_hhi
            elif kpi in ("cost_per_patient_day", "npsr_per_bed"):
                fmt = _fmt_money
            else:
                fmt = _fmt_money
            tp = row.get("target_percentile")
            if tp is None or (isinstance(tp, float) and tp != tp):
                rank_text = "—"
            else:
                rank_text = f"{tp:>3.0f}%"
                # Percentile coloring is neutral across KPIs — the analyst
                # reads meaning from KPI context (high NPSR: big hospital;
                # high Medicare %: different mix), so we just mark extremes.
                if tp >= 75:
                    rank_text = paint(rank_text, color="green")
                elif tp <= 25:
                    rank_text = paint(rank_text, color="red")
            lines.append(
                f"    {kpi:<22s} {fmt(row.get('target')):>12s}  "
                f"{fmt(row.get('peer_p10')):>10s}  "
                f"{fmt(row.get('peer_median')):>10s}  "
                f"{fmt(row.get('peer_p90')):>10s}  "
                f"{rank_text:>5s}"
            )
    return "\n".join(lines) + "\n"


def _render_mrf_summary(path: str) -> str:
    """Parse the analyst-supplied MRF file and return a terminal-friendly block."""
    from ..infra.transparency import format_mrf_summary, parse_mrf
    try:
        summary = parse_mrf(path)
    except (FileNotFoundError, ValueError) as exc:
        return f"MRF summary unavailable: {exc}\n"
    return format_mrf_summary(summary) + "\n"


def _render_990_cross_check(ccn: str, ein: str) -> str:
    """Call the IRS 990 cross-check and render it as a short terminal block."""
    from .irs990 import IRS990FetchError, cross_check_ccn

    try:
        report = cross_check_ccn(ccn, ein)
    except (ValueError, IRS990FetchError) as exc:
        return f"990 cross-check unavailable: {exc}\n"

    lines = [
        "IRS 990 Cross-Check",
        "─" * 40,
        f"  EIN:              {report.ein}",
        f"  HCRIS fiscal year:{report.hcris_fiscal_year}",
        f"  IRS tax year:     {report.irs_tax_year}",
    ]
    if not report.matched:
        lines.append("  (no 990 filings available)")
        return "\n".join(lines) + "\n"

    def _fmt(v):
        if v is None:
            return "—"
        return f"${v/1e6:.1f}M" if abs(v) >= 1e6 else f"${v:,.0f}"

    def _fmt_pct(v):
        if v is None:
            return "—"
        return f"{v*100:+.0f}%"

    for metric in ("total_revenue", "total_expenses", "net_income"):
        h = report.hcris.get(metric)
        i = report.irs.get(metric)
        v = report.variance_pct.get(metric)
        lines.append(f"  {metric:17s}{_fmt(h):>12s} (HCRIS)  {_fmt(i):>12s} (990)  Δ {_fmt_pct(v)}")

    if report.flags:
        lines.append("  Flags:")
        for f in report.flags:
            lines.append(f"    ⚠ {f}")
    return "\n".join(lines) + "\n"



if __name__ == "__main__":
    sys.exit(main())
