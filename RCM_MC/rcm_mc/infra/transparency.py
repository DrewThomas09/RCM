"""Hospital Price Transparency machine-readable file parser.

Since July 2024 CMS requires hospitals to publish negotiated rates in a
standardized CSV or JSON format (the "v2.0 standard charges template").
This module takes an analyst-supplied MRF file and produces a partner-
readable summary: payer count, unique services, rate distribution per
payer, concentration metrics.

Scope boundary: we do **not** crawl hospital websites to discover MRF URLs.
That's an adversarial problem (compliance is uneven, URLs move, schemas
vary). The analyst points this tool at a downloaded file; we produce the
summary. Pre-2024 file formats with non-standard columns are handled
best-effort via alias mapping, but will fall back to "non-compliant"
warnings when required columns are absent.
"""
from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple



# ── CMS v2.0 canonical column names + aliases ──────────────────────────────

# Required columns per the CMS final rule (simplified subset — the full
# schema has ~30 optional fields; these are the ones diligence cares about).
_REQUIRED_COLUMNS = ("code", "description", "payer_name", "standard_charge_dollar_amount")

_COLUMN_ALIASES: Dict[str, List[str]] = {
    "code":        ["code", "billing_code", "hcpcs", "cpt", "drg", "cpt_hcpcs"],
    "code_type":   ["code_type", "billing_code_type"],
    "description": ["description", "service_description", "procedure_description"],
    "payer_name":  ["payer_name", "payer", "payor_name", "payor", "insurer"],
    "plan_name":   ["plan_name", "plan"],
    "standard_charge_dollar_amount": [
        "standard_charge_dollar_amount",
        "negotiated_rate",
        "standard_charge",
        "negotiated_dollar_amount",
        "charge_amount",
    ],
    "standard_charge_methodology": [
        "standard_charge_methodology", "methodology",
    ],
}


# ── Data classes ──────────────────────────────────────────────────────────

@dataclass
class PayerRateSummary:
    payer: str
    rate_count: int
    min_rate: float
    median_rate: float
    mean_rate: float
    max_rate: float
    unique_codes: int


@dataclass
class MRFSummary:
    source_path: str
    format: str                              # "csv" | "json"
    compliant: bool                          # all _REQUIRED_COLUMNS present?
    missing_required: List[str] = field(default_factory=list)
    column_map: Dict[str, str] = field(default_factory=dict)  # canonical → actual
    total_rows: int = 0
    unique_codes: int = 0
    unique_payers: int = 0
    payer_summaries: List[PayerRateSummary] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_path": self.source_path,
            "format": self.format,
            "compliant": self.compliant,
            "missing_required": self.missing_required,
            "column_map": self.column_map,
            "total_rows": self.total_rows,
            "unique_codes": self.unique_codes,
            "unique_payers": self.unique_payers,
            "payer_summaries": [
                {
                    "payer": p.payer,
                    "rate_count": p.rate_count,
                    "unique_codes": p.unique_codes,
                    "min_rate": p.min_rate,
                    "median_rate": p.median_rate,
                    "mean_rate": p.mean_rate,
                    "max_rate": p.max_rate,
                }
                for p in self.payer_summaries
            ],
            "warnings": self.warnings,
        }


# ── Loaders ────────────────────────────────────────────────────────────────

def _read_csv(path: Path) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Read a CSV, return ``(rows_as_dicts, headers)``. Encoding-robust."""
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            with open(path, encoding=enc, newline="") as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames or []
                rows = list(reader)
            return rows, headers
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Could not decode CSV at {path}")


def _read_json(path: Path) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Read a CMS MRF JSON file.

    Per the v2.0 spec, the top-level is an object with a ``standard_charge_information``
    array of items; each item has ``payer_specific_negotiated_charges``. We
    flatten that structure into a list of ``{code, description, payer_name,
    standard_charge_dollar_amount, ...}`` rows so the same summarization path
    works for CSV and JSON.
    """
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)

    if isinstance(payload, list):
        # Already flat — some vendors produce a flat list
        return payload, sorted({k for row in payload if isinstance(row, dict) for k in row.keys()})

    rows: List[Dict[str, Any]] = []
    items = payload.get("standard_charge_information") or []
    for item in items:
        code = item.get("code") or item.get("billing_code")
        description = item.get("description")
        for charge in item.get("payer_specific_negotiated_charges") or []:
            rows.append({
                "code": code,
                "description": description,
                "payer_name": charge.get("payer_name") or charge.get("payer"),
                "plan_name": charge.get("plan_name"),
                "standard_charge_dollar_amount": (
                    charge.get("standard_charge_dollar_amount")
                    or charge.get("negotiated_rate")
                    or charge.get("standard_charge")
                ),
                "standard_charge_methodology": charge.get("standard_charge_methodology"),
            })
    headers = ["code", "description", "payer_name", "plan_name",
               "standard_charge_dollar_amount", "standard_charge_methodology"]
    return rows, headers


def _norm_header(s: str) -> str:
    """Alnum-only lowercase so "Standard Charge: Dollar Amount" normalizes to
    ``standardchargedollaramount``."""
    return "".join(ch for ch in str(s).strip().lower() if ch.isalnum())


def _resolve_columns(headers: List[str]) -> Tuple[Dict[str, str], List[str]]:
    """Map canonical column names to actual headers via alias lookup.

    Returns ``(column_map, missing_required)``. Header matching is case- and
    punctuation-insensitive; first alias that matches wins.
    """
    norm_to_actual = {_norm_header(h): h for h in headers}
    column_map: Dict[str, str] = {}
    for canonical, aliases in _COLUMN_ALIASES.items():
        for alias in aliases:
            key = _norm_header(alias)
            if key in norm_to_actual:
                column_map[canonical] = norm_to_actual[key]
                break
    missing = [c for c in _REQUIRED_COLUMNS if c not in column_map]
    return column_map, missing


def _safe_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    s = str(v).strip().replace("$", "").replace(",", "")
    if not s or s.lower() in ("n/a", "na", "null"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _summarize_rows(
    rows: List[Dict[str, Any]],
    column_map: Dict[str, str],
) -> Tuple[int, int, List[PayerRateSummary]]:
    """Reduce row-level data to per-payer summaries + overall counts."""
    code_col = column_map.get("code")
    payer_col = column_map.get("payer_name")
    rate_col = column_map.get("standard_charge_dollar_amount")

    if not (code_col and payer_col and rate_col):
        return 0, 0, []

    # payer -> list[(code, rate)]
    per_payer: Dict[str, List[Tuple[str, float]]] = {}
    unique_codes: set = set()

    for row in rows:
        code = str(row.get(code_col, "")).strip()
        payer = str(row.get(payer_col, "")).strip()
        rate = _safe_float(row.get(rate_col))
        if not payer or rate is None or rate <= 0:
            continue
        unique_codes.add(code)
        per_payer.setdefault(payer, []).append((code, rate))

    summaries: List[PayerRateSummary] = []
    for payer, entries in per_payer.items():
        rates = [r for _, r in entries]
        codes = {c for c, _ in entries}
        rates_sorted = sorted(rates)
        n = len(rates_sorted)
        median = rates_sorted[n // 2] if n % 2 == 1 else (rates_sorted[n // 2 - 1] + rates_sorted[n // 2]) / 2
        summaries.append(PayerRateSummary(
            payer=payer,
            rate_count=n,
            unique_codes=len(codes),
            min_rate=rates_sorted[0],
            median_rate=median,
            mean_rate=sum(rates) / n,
            max_rate=rates_sorted[-1],
        ))
    # Order by rate_count desc so the biggest payer surfaces first
    summaries.sort(key=lambda p: -p.rate_count)
    return len(unique_codes), len(per_payer), summaries


# ── Public API ─────────────────────────────────────────────────────────────

def parse_mrf(path: str) -> MRFSummary:
    """Parse a Hospital Price Transparency MRF file (CSV or JSON) and summarize.

    Works on CMS v2.0 schema (July 2024+) and earlier formats that follow
    similar column names. Non-compliant files still produce a partial summary
    with ``compliant=False`` and ``missing_required`` listed.
    """
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"MRF file not found: {path}")

    ext = p.suffix.lower()
    if ext in (".csv", ".tsv", ".txt"):
        rows, headers = _read_csv(p)
        fmt = "csv"
    elif ext in (".json",):
        rows, headers = _read_json(p)
        fmt = "json"
    else:
        raise ValueError(f"Unsupported MRF format: {ext} (expected .csv or .json)")

    column_map, missing = _resolve_columns(headers)
    summary = MRFSummary(
        source_path=os.path.abspath(path),
        format=fmt,
        compliant=(not missing),
        missing_required=missing,
        column_map=column_map,
        total_rows=len(rows),
    )
    if missing:
        summary.warnings.append(
            f"Non-compliant with CMS v2.0 schema: missing {', '.join(missing)}. "
            "Rate summary limited to fields we can recognize."
        )

    summary.unique_codes, summary.unique_payers, summary.payer_summaries = (
        _summarize_rows(rows, column_map)
    )
    return summary


def format_mrf_summary(summary: MRFSummary, top_n: int = 10) -> str:
    """Terminal-friendly block (plain text; no ANSI)."""
    lines = [
        f"MRF Summary — {summary.source_path}",
        "─" * 60,
        f"  Format:            {summary.format.upper()}",
        f"  CMS v2.0 compliant:{('  yes' if summary.compliant else '  no')}",
        f"  Total rows:        {summary.total_rows:,}",
        f"  Unique codes:      {summary.unique_codes:,}",
        f"  Unique payers:     {summary.unique_payers:,}",
    ]
    if summary.missing_required:
        lines.append(f"  Missing required:  {', '.join(summary.missing_required)}")

    if summary.payer_summaries:
        lines.append("")
        lines.append(f"  Top {min(top_n, len(summary.payer_summaries))} payers by rate count:")
        lines.append(
            f"    {'Payer':38s} {'Rates':>7s} {'Codes':>7s} "
            f"{'Median':>10s} {'Range':>24s}"
        )
        for p in summary.payer_summaries[:top_n]:
            name = (p.payer if len(p.payer) <= 36 else p.payer[:35] + "…")
            span = f"${p.min_rate:,.0f} – ${p.max_rate:,.0f}"
            lines.append(
                f"    {name:38s} {p.rate_count:>7,d} {p.unique_codes:>7,d} "
                f"${p.median_rate:>9,.0f} {span:>24s}"
            )

    if summary.warnings:
        lines.append("")
        lines.append("  Warnings:")
        for w in summary.warnings:
            lines.append(f"    ⚠ {w}")
    return "\n".join(lines)
