#!/usr/bin/env python3
"""verify_rework.py — post-landing checks for the Chartis UI rework.

Run from the repo root AFTER copying CHARTIS_KIT_REWORK.py into
rcm_mc/ui/_chartis_kit.py and chartis_tokens.css into rcm_mc/ui/static/.

Usage:
    python handoff/verify_rework.py
    python handoff/verify_rework.py --server http://localhost:8080

Exits non-zero on any failure. Intended to be CI-friendly.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
UI_DIR = REPO_ROOT / "rcm_mc" / "ui"

# Hex codes that belonged to the old dark palette. Any survivor is a bug.
FORBIDDEN_HEX = [
    r"#0a0a0a",
    r"#111(?![0-9a-f])",
    r"#1a1a1a",
    r"#202020",
    r"#2a2a2a",
    r"#00ff9c",
    r"#33ffff",
    r"#ff6b6b",
    r"#ffab00",
]

# Pages that are expected to be fully migrated. Expand as you work.
TIER_1 = [
    "home_page.py",
    "pipeline_page.py",
    "analysis_workbench.py",
    "ic_memo_page.py",
    "ebitda_bridge_page.py",
    "portfolio_analytics_page.py",
    "payer_intelligence_page.py",
    "pe_intelligence_hub_page.py",
    "corpus_backtest_page.py",
]


def check_kit_signatures() -> list[str]:
    """Confirm the new _chartis_kit.py exposes the symbols pages import."""
    required = [
        "chartis_shell",
        "ck_panel",
        "ck_table",
        "ck_kpi_block",
        "ck_signal_badge",
        "ck_section_header",
        "ck_fmt_currency",
        "ck_fmt_percent",
        "ck_fmt_number",
        "_CORPUS_NAV",
    ]
    kit = UI_DIR / "_chartis_kit.py"
    if not kit.exists():
        return [f"MISSING: {kit}"]
    src = kit.read_text(encoding="utf-8")
    return [f"MISSING symbol in _chartis_kit.py: {sym}" for sym in required if sym not in src]


def check_tokens_present() -> list[str]:
    tokens = UI_DIR / "static" / "chartis_tokens.css"
    if not tokens.exists():
        return [f"MISSING: {tokens} — copy from handoff/chartis_tokens.css"]
    required = ["--sc-navy", "--sc-teal", "--sc-parchment", "--sc-serif"]
    src = tokens.read_text(encoding="utf-8")
    return [f"MISSING token in chartis_tokens.css: {t}" for t in required if t not in src]


def grep_forbidden_hex() -> list[str]:
    """Find hardcoded old-palette hex codes in any page file."""
    fails: list[str] = []
    pattern = re.compile("|".join(FORBIDDEN_HEX), re.IGNORECASE)
    for py in UI_DIR.rglob("*.py"):
        if py.name == "_chartis_kit_legacy.py":
            continue
        try:
            text = py.read_text(encoding="utf-8")
        except Exception:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if pattern.search(line):
                rel = py.relative_to(REPO_ROOT)
                fails.append(f"{rel}:{i}: {line.strip()[:100]}")
    return fails


def check_tier_1_migrated() -> list[str]:
    """Tier-1 pages must import from the new kit, not the legacy module."""
    fails: list[str] = []
    for name in TIER_1:
        p = UI_DIR / name
        if "/" in name:
            p = UI_DIR / name
        if not p.exists():
            p = UI_DIR / "chartis" / name  # some live in the chartis subdir
        if not p.exists():
            fails.append(f"TIER-1 page not found: {name}")
            continue
        src = p.read_text(encoding="utf-8")
        if "_chartis_kit_legacy" in src:
            fails.append(f"{name} still imports from _chartis_kit_legacy")
    return fails


def smoke_boot(server_url: str | None) -> list[str]:
    """Optional: hit the home route and confirm the new tokens file is linked."""
    if not server_url:
        return []
    try:
        import urllib.request
        with urllib.request.urlopen(f"{server_url}/home", timeout=4) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
    except Exception as exc:
        return [f"smoke boot failed: {exc}"]
    fails = []
    if "chartis_tokens.css" not in body:
        fails.append("smoke boot: /home did not link chartis_tokens.css")
    if "Source+Serif+4" not in body and "Source Serif 4" not in body:
        fails.append("smoke boot: Source Serif 4 font not linked")
    return fails


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", default=None, help="e.g. http://localhost:8080")
    ap.add_argument("--fail-on-hex", action="store_true",
                    help="Exit non-zero if forbidden hex codes are still found (strict mode)")
    args = ap.parse_args()

    all_fails: dict[str, list[str]] = {
        "kit signatures": check_kit_signatures(),
        "tokens file":    check_tokens_present(),
        "tier-1 pages":   check_tier_1_migrated(),
        "forbidden hex":  grep_forbidden_hex(),
        "smoke boot":     smoke_boot(args.server),
    }

    total = sum(len(v) for v in all_fails.values())
    for bucket, fails in all_fails.items():
        tag = "✓" if not fails else "✗"
        print(f"\n[{tag}] {bucket}: {len(fails)} issue(s)")
        for f in fails[:50]:
            print(f"    {f}")
        if len(fails) > 50:
            print(f"    ... and {len(fails) - 50} more")

    # Forbidden hex is a soft warning by default — expected during migration.
    hard_fail = (
        bool(all_fails["kit signatures"])
        or bool(all_fails["tokens file"])
        or bool(all_fails["tier-1 pages"])
        or bool(all_fails["smoke boot"])
        or (args.fail_on_hex and bool(all_fails["forbidden hex"]))
    )
    print(f"\n{'FAIL' if hard_fail else 'PASS'} — {total} total issue(s) found")
    return 1 if hard_fail else 0


if __name__ == "__main__":
    sys.exit(main())
