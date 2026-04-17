"""Corpus export utilities — CSV, JSON, and Markdown export of the public deals.

Provides partner-ready exports of the 175-deal corpus with optional
filtering, formatting, and portfolio analytics summary headers.

Public API:
    to_csv(deals, path, include_payer_mix)    -> str  (CSV text or writes to path)
    to_json(deals, path, pretty)              -> str  (JSON text or writes to path)
    to_markdown(deals, max_rows, scorecard)   -> str  (markdown table)
    export_full_corpus(db_path, out_dir, fmt) -> dict (paths written)
"""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Canonical export columns
# ---------------------------------------------------------------------------

_CORE_COLS = [
    "source_id", "deal_name", "year", "buyer", "seller",
    "ev_mm", "ebitda_at_entry_mm", "hold_years",
    "realized_moic", "realized_irr",
]
_PAYER_COLS = ["payer_medicare", "payer_medicaid", "payer_commercial", "payer_selfpay"]


def _expand_payer(deal: Dict[str, Any]) -> Dict[str, Any]:
    """Expand payer_mix JSON into flat payer_* columns."""
    pm = deal.get("payer_mix")
    if isinstance(pm, str):
        try:
            pm = json.loads(pm)
        except Exception:
            pm = {}
    if not isinstance(pm, dict):
        pm = {}
    return {
        "payer_medicare": pm.get("medicare"),
        "payer_medicaid": pm.get("medicaid"),
        "payer_commercial": pm.get("commercial"),
        "payer_selfpay": pm.get("selfpay"),
    }


def _flat_row(deal: Dict[str, Any], include_payer: bool) -> Dict[str, Any]:
    row: Dict[str, Any] = {col: deal.get(col) for col in _CORE_COLS}
    if include_payer:
        row.update(_expand_payer(deal))
    row["notes"] = (deal.get("notes") or "")[:200]
    return row


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

def to_csv(
    deals: List[Dict[str, Any]],
    path: Optional[str] = None,
    include_payer_mix: bool = True,
) -> str:
    """Export deals to CSV string (writes to path if given).

    Defangs Excel formula injection by prepending ' to values starting with
    =, +, -, @, |.
    """
    _FORMULA_CHARS = {"=", "+", "-", "@", "|"}

    def _safe(v: Any) -> str:
        s = "" if v is None else str(v)
        if s and s[0] in _FORMULA_CHARS:
            s = "'" + s
        return s

    cols = _CORE_COLS + (_PAYER_COLS if include_payer_mix else []) + ["notes"]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    for deal in deals:
        row = _flat_row(deal, include_payer_mix)
        safe_row = {k: _safe(v) for k, v in row.items()}
        writer.writerow(safe_row)

    text = buf.getvalue()
    if path:
        Path(path).write_text(text, encoding="utf-8")
    return text


# ---------------------------------------------------------------------------
# JSON export
# ---------------------------------------------------------------------------

def to_json(
    deals: List[Dict[str, Any]],
    path: Optional[str] = None,
    pretty: bool = True,
    include_payer_mix: bool = True,
) -> str:
    """Export deals to JSON string (writes to path if given)."""
    rows = []
    for deal in deals:
        row = _flat_row(deal, include_payer_mix)
        if include_payer_mix:
            # Also keep original payer_mix as nested dict
            pm = deal.get("payer_mix")
            if isinstance(pm, str):
                try:
                    pm = json.loads(pm)
                except Exception:
                    pm = {}
            row["payer_mix"] = pm
        rows.append(row)

    indent = 2 if pretty else None
    text = json.dumps(rows, indent=indent, default=str)
    if path:
        Path(path).write_text(text, encoding="utf-8")
    return text


# ---------------------------------------------------------------------------
# Markdown export
# ---------------------------------------------------------------------------

def to_markdown(
    deals: List[Dict[str, Any]],
    max_rows: int = 50,
    include_scorecard: bool = True,
) -> str:
    """Export deals to a markdown table with optional portfolio scorecard header."""
    lines = []

    if include_scorecard:
        try:
            from .portfolio_analytics import corpus_scorecard, scorecard_text
            sc = corpus_scorecard(deals)
            lines.append("## Portfolio Corpus Scorecard")
            lines.append("")
            lines.append(f"| Metric | Value |")
            lines.append(f"|--------|-------|")
            lines.append(f"| Total deals | {sc.get('total_deals', 0)} |")
            lines.append(f"| Realized deals | {sc.get('realized_deals', 0)} |")
            lines.append(f"| Total EV ($M) | ${sc.get('total_ev_mm', 0):,.1f} |")
            lines.append(f"| MOIC P50 | {sc.get('moic_p50', 'N/A'):.2f}x |" if sc.get('moic_p50') else "| MOIC P50 | N/A |")
            lines.append(f"| Loss rate | {sc.get('loss_rate', 0):.1%} |")
            lines.append(f"| Home-run rate | {sc.get('home_run_rate', 0):.1%} |")
            lines.append("")
        except Exception:
            pass

    lines += [
        "## Deal Corpus",
        "",
        "| # | Deal Name | Year | Buyer | EV ($M) | MOIC | IRR |",
        "|---|-----------|------|-------|---------|------|-----|",
    ]

    for i, deal in enumerate(deals[:max_rows], 1):
        name = str(deal.get("deal_name") or "")[:60]
        yr = str(deal.get("year") or "N/A")
        buyer = str(deal.get("buyer") or "N/A")[:30]
        ev = deal.get("ev_mm")
        ev_s = f"${ev:,.0f}" if ev is not None else "N/A"
        moic = deal.get("realized_moic")
        moic_s = f"{moic:.2f}x" if moic is not None else "—"
        irr = deal.get("realized_irr")
        irr_s = f"{irr:.1%}" if irr is not None else "—"
        lines.append(f"| {i} | {name} | {yr} | {buyer} | {ev_s} | {moic_s} | {irr_s} |")

    if len(deals) > max_rows:
        lines.append(f"| ... | *{len(deals) - max_rows} more deals* | | | | | |")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Full export
# ---------------------------------------------------------------------------

def export_full_corpus(
    db_path: str = "corpus.db",
    out_dir: str = ".",
    formats: Optional[List[str]] = None,
) -> Dict[str, str]:
    """Export the full seeded corpus to one or more formats.

    Returns dict of {format: written_path}.
    formats: list of "csv", "json", "markdown" (default: all three)
    """
    from .deals_corpus import DealsCorpus

    formats = formats or ["csv", "json", "markdown"]
    corpus = DealsCorpus(db_path)
    corpus.seed()
    deals = corpus.list()

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    written: Dict[str, str] = {}
    if "csv" in formats:
        p = str(out / "public_deals.csv")
        to_csv(deals, path=p)
        written["csv"] = p
    if "json" in formats:
        p = str(out / "public_deals.json")
        to_json(deals, path=p)
        written["json"] = p
    if "markdown" in formats:
        p = str(out / "public_deals.md")
        Path(p).write_text(to_markdown(deals), encoding="utf-8")
        written["markdown"] = p

    return written
