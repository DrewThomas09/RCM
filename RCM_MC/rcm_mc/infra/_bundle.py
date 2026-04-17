"""Diligence-grade deliverable bundle.

Replaces a 20-file output folder with:

- ``diligence_workbook.xlsx`` — multi-tab Excel for IC/partner review
- ``data_requests.md`` — management asks, ranked by value-driver salience
- ``outputs/_detail/`` — all the raw CSVs / charts for analysts who dig

Top-level outputs that remain: ``report.html``, ``summary.csv``,
``simulations.csv``, ``provenance.json``, plus the two new files above.
Everything else is swept into ``_detail/``.

The bundle is generated as the last step of a CLI run so it sees the final
state of the output directory.
"""
from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd

from ..data.sources import classify_sources, confidence_grade, path_notes, summarize


# Files that stay at the top of outdir. Anything else gets swept to _detail/.
_TOP_LEVEL_KEEP = frozenset([
    "summary.csv",
    "simulations.csv",
    "provenance.json",
    "report.html",
    "report.md",
    "summary.json",
    "report.pptx",
    "partner_brief.html",
    "diligence_workbook.xlsx",
    "data_requests.md",
    "runs.sqlite",
    # PE math artifacts (Brick 46) — portfolio snapshots read these
    # directly from the run dir, so they must stay top-level.
    "pe_bridge.json",
    "pe_returns.json",
    "pe_covenant.json",
    "pe_hold_grid.csv",
    # Peer + trend CSVs consumed by the portfolio + hold-period layer
    "peer_comparison.csv",
    "peer_target_percentiles.csv",
    "trend.csv",
    "trend_signals.csv",
])


# Plain-English request prompts per path suffix. A partner can copy-paste these
# directly into an email to management.
_REQUEST_PROMPTS: Dict[str, str] = {
    "hospital.annual_revenue": "Audited NPSR for the trailing 12 months (income-statement line or payer-mix roll-up).",
    "hospital.ebitda_margin": "Adjusted EBITDA margin; reconcile to audited financials.",
    "hospital.debt": "Outstanding debt balances and covenant details (if applicable).",
    "hospital.rcm_spend_annual": "All-in RCM cost (in-house FTE + technology + outsourced vendors).",
    "economics.wacc_annual": "Target WACC assumption to sanity-check working-capital carry.",
    "revenue_share": "Net revenue by payer for the trailing 12 months (claims_summary extract).",
    "avg_claim_dollars": "Claim count and total paid by payer (for average claim size calc).",
    "dar_clean_days": "A/R aging detail by payer (include 0-30 / 31-60 / 61-90 / 90+ buckets).",
    "denials.idr": "Denials extract: claim_id, payer, denial_date, denial_amount, denial_reason.",
    "denials.fwr": "Final-status flag on denied claims (paid vs written-off after appeals).",
    "denials.stage_mix": "Appeal stage flag per denial (L1 / L2 / L3 / ALJ, or local equivalents).",
    "underpayments.upr": "Contractual allowance analysis: expected vs paid per claim/payer.",
    "underpayments.severity": "Underpayment dollar magnitudes by payer (same contractual analysis).",
    "underpayments.recovery": "Historical rework recovery rate on flagged underpayments.",
}


def _lookup_prompt(dotted_path: str) -> str:
    """Match a dotted path to the most specific request prompt available."""
    # Exact match first
    if dotted_path in _REQUEST_PROMPTS:
        return _REQUEST_PROMPTS[dotted_path]
    # Suffix match (e.g., payers.Medicare.denials.idr -> denials.idr)
    for suffix, prompt in _REQUEST_PROMPTS.items():
        if dotted_path.endswith(suffix):
            return prompt
    return "Provide source documentation for this parameter."


def _payer_from_path(dotted_path: str) -> Optional[str]:
    """Extract the payer segment, if any, from a dotted path."""
    parts = dotted_path.split(".")
    if len(parts) >= 2 and parts[0] == "payers":
        return parts[1]
    return None


def _metric_from_path(dotted_path: str) -> str:
    """Human-readable metric name from a dotted path."""
    parts = dotted_path.split(".")
    if parts[0] == "payers" and len(parts) >= 3:
        return ".".join(parts[2:])
    return dotted_path


def build_data_requests(
    cfg: Dict[str, Any],
    sensitivity_df: Optional[pd.DataFrame] = None,
    hospital_name: Optional[str] = None,
) -> str:
    """Render data_requests.md content: management asks grouped by payer, ranked
    by value-driver salience when sensitivity data is available.
    """
    classification = classify_sources(cfg)
    notes = path_notes(cfg)
    counts = summarize(classification)
    grade = confidence_grade(classification)
    total = counts.get("total", 0) or 0
    observed = counts.get("observed", 0) or 0

    assumed_paths = [p for p, label in classification.items() if label == "assumed"]
    prior_paths = [p for p, label in classification.items() if label == "prior"]
    observed_paths = [p for p, label in classification.items() if label == "observed"]

    # Rank assumed paths by sensitivity ranking if we have correlation data.
    ranked_assumed = list(assumed_paths)
    if sensitivity_df is not None and not sensitivity_df.empty:
        sens_order = {str(row): i for i, row in enumerate(sensitivity_df.iloc[:, 0].tolist())}

        def _rank(p: str) -> int:
            suffix = _metric_from_path(p).split(".")[-1]
            for k, idx in sens_order.items():
                if suffix in k or k in p:
                    return idx
            return len(sens_order) + 1

        ranked_assumed = sorted(assumed_paths, key=_rank)

    gen = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    hosp = hospital_name or (cfg.get("hospital", {}) or {}).get("name") or "Target"

    lines: List[str] = []
    lines.append(f"# Data Requests — {hosp}")
    lines.append("")
    lines.append(f"Generated {gen}. Based on the most recent RCM Monte Carlo run.")
    lines.append("")
    lines.append(
        f"**Current evidence grade: {grade}** — {observed} of {total} model inputs observed from target data "
        f"({(observed / total * 100.0) if total else 0:.0f}%). "
        f"Closing the gaps below improves defensibility and tightens the EBITDA range."
    )
    lines.append("")

    if ranked_assumed:
        lines.append("## Priority asks — currently analyst assumptions")
        lines.append("")
        lines.append("Grouped by payer. Each row is what to ask management for.")
        lines.append("")
        # Group by payer
        by_payer: Dict[str, List[str]] = {}
        for p in ranked_assumed:
            payer = _payer_from_path(p) or "(hospital-level)"
            by_payer.setdefault(payer, []).append(p)
        for payer, paths in by_payer.items():
            lines.append(f"### {payer}")
            lines.append("")
            lines.append("| Metric | Request |")
            lines.append("|--------|---------|")
            for p in paths:
                metric = _metric_from_path(p)
                prompt = _lookup_prompt(p).replace("|", "\\|")
                lines.append(f"| `{metric}` | {prompt} |")
            lines.append("")

    if prior_paths:
        lines.append("## Currently industry priors (no target data)")
        lines.append("")
        lines.append(
            "These are industry benchmarks from published sources. Actual target data "
            "would let us calibrate specifically to this hospital."
        )
        lines.append("")
        for p in prior_paths:
            note = notes.get(p, "")
            if note:
                lines.append(f"- `{p}` — prior ({note})")
            else:
                lines.append(f"- `{p}` — prior")
        lines.append("")

    if observed_paths:
        lines.append("## Already observed — no action needed")
        lines.append("")
        for p in observed_paths:
            note = notes.get(p, "")
            if note:
                lines.append(f"- `{p}` — {note}")
            else:
                lines.append(f"- `{p}`")
        lines.append("")

    return "\n".join(lines) + "\n"


def _summary_tab(summary_df: pd.DataFrame) -> pd.DataFrame:
    """Summary tab: metric, mean, median, P10, P90, rounded for presentation."""
    out = summary_df.copy()
    out.index.name = "metric"
    out = out.reset_index()
    # Keep only the analyst-relevant columns if present; the summary frame may have
    # other columns from scrub/aggregation — preserve the common subset.
    cols_in_order = [c for c in ("metric", "mean", "median", "p10", "p90") if c in out.columns]
    extras = [c for c in out.columns if c not in cols_in_order]
    return out[cols_in_order + extras]


def _payers_tab(cfg: Dict[str, Any]) -> pd.DataFrame:
    """Payer mix + key KPIs flattened for Excel."""
    classification = classify_sources(cfg)
    rows = []
    for name, pconf in (cfg.get("payers") or {}).items():
        row: Dict[str, Any] = {"payer": name}
        row["revenue_share"] = pconf.get("revenue_share")
        row["avg_claim_dollars"] = pconf.get("avg_claim_dollars")
        dar = pconf.get("dar_clean_days") or {}
        row["dar_clean_days_mean"] = dar.get("mean") if isinstance(dar, dict) else None
        den = pconf.get("denials") or {}
        idr = (den.get("idr") or {}) if isinstance(den, dict) else {}
        fwr = (den.get("fwr") or {}) if isinstance(den, dict) else {}
        row["idr_mean"] = idr.get("mean") if isinstance(idr, dict) else None
        row["fwr_mean"] = fwr.get("mean") if isinstance(fwr, dict) else None
        # Source tag for the three big payer KPIs (which drive IC conversation)
        row["idr_source"] = classification.get(f"payers.{name}.denials.idr", "—")
        row["fwr_source"] = classification.get(f"payers.{name}.denials.fwr", "—")
        row["dar_source"] = classification.get(f"payers.{name}.dar_clean_days", "—")
        rows.append(row)
    return pd.DataFrame(rows)


def _assumptions_tab(cfg: Dict[str, Any]) -> pd.DataFrame:
    """Source-map tab: every meaningful input with its source label and note."""
    classification = classify_sources(cfg)
    notes = path_notes(cfg)
    rows = [
        {
            "path": p,
            "source": label,
            "note": notes.get(p, ""),
        }
        for p, label in sorted(classification.items())
    ]
    return pd.DataFrame(rows)


def _value_drivers_tab(outdir: str) -> Optional[pd.DataFrame]:
    """Prefer OAT attribution output; fall back to correlation sensitivity."""
    attr_path = os.path.join(outdir, "attribution_oat.csv")
    if os.path.isfile(attr_path):
        df = pd.read_csv(attr_path)
        return df
    sens_path = os.path.join(outdir, "sensitivity.csv")
    if os.path.isfile(sens_path):
        df = pd.read_csv(sens_path)
        return df
    return None


def _stress_tab(outdir: str) -> Optional[pd.DataFrame]:
    p = os.path.join(outdir, "stress_tests.csv")
    if os.path.isfile(p):
        return pd.read_csv(p)
    return None


def _plan_tab(outdir: str) -> Optional[pd.DataFrame]:
    p = os.path.join(outdir, "hundred_day_plan.csv")
    if os.path.isfile(p):
        return pd.read_csv(p)
    return None


def _pressure_test_tabs(outdir: str) -> Dict[str, pd.DataFrame]:
    """Return pressure-test dataframes keyed by desired sheet name (if present)."""
    out: Dict[str, pd.DataFrame] = {}
    assess = os.path.join(outdir, "pressure_test_assessments.csv")
    miss = os.path.join(outdir, "pressure_test_miss_scenarios.csv")
    if os.path.isfile(assess):
        out["Plan Pressure Test"] = pd.read_csv(assess)
    if os.path.isfile(miss):
        out["Plan Miss Scenarios"] = pd.read_csv(miss)
    return out


def _peer_tabs(outdir: str) -> Dict[str, pd.DataFrame]:
    """Return peer-comparison + trend dataframes keyed by sheet name (if present).

    "Peer Percentiles" leads because a partner should read target's rank-on-KPI
    first; the full peer roster ("Peer Set") is supporting detail. "Trend
    Signals" captures first→last fiscal-year deltas for the target, answering
    the "how is this hospital trending?" question that pairs with peer ranks.
    """
    out: Dict[str, pd.DataFrame] = {}
    pcts = os.path.join(outdir, "peer_target_percentiles.csv")
    peers = os.path.join(outdir, "peer_comparison.csv")
    signals = os.path.join(outdir, "trend_signals.csv")
    if os.path.isfile(pcts):
        out["Peer Percentiles"] = pd.read_csv(pcts)
    if os.path.isfile(peers):
        out["Peer Set"] = pd.read_csv(peers)
    if os.path.isfile(signals):
        out["Trend Signals"] = pd.read_csv(signals)
    return out


def _pe_tabs(outdir: str) -> Dict[str, pd.DataFrame]:
    """Return PE deal-math dataframes keyed by sheet name (Brick 47).

    Four tabs surface the pe_integration artifacts in the workbook:

    - PE Bridge     — waterfall rows (Entry EV → components → Exit EV)
    - PE Returns    — base-case MOIC/IRR single-row snapshot
    - PE Hold Grid  — hold-years × exit-multiple sensitivity (IC sensitivity)
    - PE Covenant   — leverage + covenant headroom single-row snapshot

    All four tabs are optional — present only when the matching artifacts
    exist (i.e., the actual.yaml had a `deal` section).
    """
    import json as _json
    out: Dict[str, pd.DataFrame] = {}

    bridge_path = os.path.join(outdir, "pe_bridge.json")
    if os.path.isfile(bridge_path):
        with open(bridge_path, encoding="utf-8") as f:
            payload = _json.load(f)
        out["PE Bridge"] = pd.DataFrame(payload.get("components") or [])

    returns_path = os.path.join(outdir, "pe_returns.json")
    if os.path.isfile(returns_path):
        with open(returns_path, encoding="utf-8") as f:
            payload = _json.load(f)
        out["PE Returns"] = pd.DataFrame([{
            "entry_equity":        payload.get("entry_equity"),
            "exit_proceeds":       payload.get("exit_proceeds"),
            "hold_years":          payload.get("hold_years"),
            "moic":                payload.get("moic"),
            "irr":                 payload.get("irr"),
            "total_distributions": payload.get("total_distributions"),
        }])

    grid_path = os.path.join(outdir, "pe_hold_grid.csv")
    if os.path.isfile(grid_path):
        out["PE Hold Grid"] = pd.read_csv(grid_path)

    covenant_path = os.path.join(outdir, "pe_covenant.json")
    if os.path.isfile(covenant_path):
        with open(covenant_path, encoding="utf-8") as f:
            payload = _json.load(f)
        out["PE Covenant"] = pd.DataFrame([payload])

    return out


def _lineage_tab(outdir: str) -> Optional[pd.DataFrame]:
    """Read ``provenance.json`` and flatten per-metric lineage into a tab.

    For each metric, we show:

    - ``metric`` — name as it appears in summary.csv
    - ``formula`` — human-readable definition from METRIC_REGISTRY
    - ``config_keys`` — comma-joined input paths that drive this metric
    - ``source_summary`` — rollup like "12 observed / 3 prior / 1 assumed"
      computed by globbing the metric's config_keys against the classification
      map (so ``payers.*.denials.idr`` expands to the four payer-level paths)
    - ``caveats`` — analyst-facing warnings attached in the registry

    A partner opening the Lineage tab sees, in one place, what drives each
    headline number AND how well-evidenced its inputs are. Returns None if
    provenance.json is missing or malformed.
    """
    import fnmatch
    import json
    from collections import Counter

    prov_path = os.path.join(outdir, "provenance.json")
    if not os.path.isfile(prov_path):
        return None
    try:
        with open(prov_path, "r", encoding="utf-8") as f:
            doc = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None

    metrics = doc.get("metrics") or []
    if not metrics:
        return None
    classification = ((doc.get("sources") or {}).get("classification") or {})

    rows: List[Dict[str, Any]] = []
    for m in metrics:
        name = str(m.get("metric") or "").strip()
        if not name:
            continue
        formula = str(m.get("formula") or "")
        config_keys = [str(k) for k in (m.get("config_keys") or [])]
        caveats = [str(c) for c in (m.get("caveats") or [])]

        # Expand each glob-like config_keys entry against the classification map.
        matched_labels: List[str] = []
        for pattern in config_keys:
            matches = fnmatch.filter(classification.keys(), pattern)
            matched_labels.extend(classification[p] for p in matches)

        if matched_labels:
            counts = Counter(matched_labels)
            parts = [
                f"{counts[k]} {k}"
                for k in ("observed", "prior", "assumed")
                if counts.get(k, 0) > 0
            ]
            source_summary = " / ".join(parts) if parts else "—"
        else:
            source_summary = "—"

        rows.append({
            "metric": name,
            "source_summary": source_summary,
            "config_keys": ", ".join(config_keys)[:300],
            "formula": formula[:500],
            "caveats": "; ".join(caveats)[:300],
        })
    return pd.DataFrame(rows) if rows else None


def write_diligence_workbook(
    outdir: str,
    summary_df: pd.DataFrame,
    cfg: Dict[str, Any],
) -> str:
    """Build ``diligence_workbook.xlsx`` with Summary / Payers / Assumptions /
    Value Drivers tabs, plus optional Stress / Action Plan / Plan Pressure Test
    / Peer tabs when data exists. Returns the absolute path.

    After data is written, polish is applied: styled headers, frozen panes,
    currency / percent / integer number formats per column, source-tag
    coloring in the Assumptions tab, percentile coloring in Peer Percentiles,
    and a cover sheet as the first tab with target metadata + TOC.
    """
    from ..ui._workbook_style import (
        _TAB_DESCRIPTIONS,
        add_tab_note,
        apply_color_scale,
        apply_data_bar,
        apply_peer_percentile_row_formats,
        apply_percentile_coloring,
        apply_sheet_polish,
        apply_source_coloring,
        build_cover_sheet,
    )

    path = os.path.join(outdir, "diligence_workbook.xlsx")
    with pd.ExcelWriter(path, engine="openpyxl") as xls:
        _summary_tab(summary_df).to_excel(xls, sheet_name="Summary", index=False)
        _payers_tab(cfg).to_excel(xls, sheet_name="Payers", index=False)
        _assumptions_tab(cfg).to_excel(xls, sheet_name="Assumptions", index=False)
        vd = _value_drivers_tab(outdir)
        if vd is not None:
            vd.to_excel(xls, sheet_name="Value Drivers", index=False)
        stress = _stress_tab(outdir)
        if stress is not None:
            stress.to_excel(xls, sheet_name="Stress Tests", index=False)
        plan = _plan_tab(outdir)
        if plan is not None:
            plan.to_excel(xls, sheet_name="Action Plan", index=False)
        for sheet_name, df in _pressure_test_tabs(outdir).items():
            df.to_excel(xls, sheet_name=sheet_name, index=False)
        for sheet_name, df in _peer_tabs(outdir).items():
            df.to_excel(xls, sheet_name=sheet_name, index=False)
        for sheet_name, df in _pe_tabs(outdir).items():
            df.to_excel(xls, sheet_name=sheet_name, index=False)

        lineage = _lineage_tab(outdir)
        if lineage is not None:
            lineage.to_excel(xls, sheet_name="Lineage", index=False)

        challenge_path = os.path.join(outdir, "challenge_analysis.csv")
        if os.path.isfile(challenge_path):
            pd.read_csv(challenge_path).to_excel(xls, sheet_name="Challenge", index=False)

        wb = xls.book

        # Per-sheet polish: header, freeze, number formats, column widths.
        # Skip nothing — every data sheet gets the same treatment.
        for sheet in wb.worksheets:
            apply_sheet_polish(sheet)

        # Sheet-specific conditional fills (safe no-ops if sheet missing).
        if "Assumptions" in wb.sheetnames:
            apply_source_coloring(wb["Assumptions"])
        if "Peer Percentiles" in wb.sheetnames:
            apply_peer_percentile_row_formats(wb["Peer Percentiles"])
            apply_percentile_coloring(wb["Peer Percentiles"])

        # UI-5: data bars + color scales on columns an analyst skims.
        # Each call is a safe no-op when the sheet or column is missing.
        if "PE Hold Grid" in wb.sheetnames:
            apply_color_scale(wb["PE Hold Grid"], "moic", higher_is_better=True)
            apply_color_scale(wb["PE Hold Grid"], "irr", higher_is_better=True)
        if "Plan Miss Scenarios" in wb.sheetnames:
            apply_data_bar(wb["Plan Miss Scenarios"], "ebitda_drag_mean")
        if "Value Drivers" in wb.sheetnames:
            apply_data_bar(wb["Value Drivers"], "uplift_oat")
        if "Trend Signals" in wb.sheetnames:
            apply_color_scale(wb["Trend Signals"], "pct_change", higher_is_better=True)
            apply_color_scale(wb["Trend Signals"], "pts_change", higher_is_better=True)
        if "PE Bridge" in wb.sheetnames:
            apply_data_bar(wb["PE Bridge"], "value")

        # UI-5: prepend a descriptive note row to each tab. MUST run
        # AFTER data-bar / color-scale rules because it inserts a row.
        for sheet in wb.worksheets:
            note = _TAB_DESCRIPTIONS.get(sheet.title)
            if note:
                add_tab_note(sheet, note)

        # Cover sheet last — reads the final set of tab titles for the TOC.
        hospital = cfg.get("hospital") or {}
        build_cover_sheet(
            wb,
            hospital_name=hospital.get("name"),
            ccn=hospital.get("ccn"),
            outdir=outdir,
            tab_order=[ws.title for ws in wb.worksheets if ws.title != "Cover"],
        )
    return path


def write_data_requests(
    outdir: str,
    cfg: Dict[str, Any],
    hospital_name: Optional[str] = None,
) -> str:
    """Write ``data_requests.md`` and return its path."""
    sens_path = os.path.join(outdir, "sensitivity.csv")
    sens_df: Optional[pd.DataFrame] = None
    if os.path.isfile(sens_path):
        try:
            sens_df = pd.read_csv(sens_path)
        except (OSError, pd.errors.ParserError):
            sens_df = None
    content = build_data_requests(cfg, sensitivity_df=sens_df, hospital_name=hospital_name)
    path = os.path.join(outdir, "data_requests.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def organize_detail(outdir: str) -> List[str]:
    """Move every non-top-level file in ``outdir`` into ``outdir/_detail/``.

    Returns the list of absolute paths that were moved. Idempotent: re-running
    on an already-organized directory is a no-op.
    """
    if not os.path.isdir(outdir):
        return []
    detail_dir = os.path.join(outdir, "_detail")
    os.makedirs(detail_dir, exist_ok=True)
    moved: List[str] = []
    for name in os.listdir(outdir):
        if name == "_detail":
            continue
        src = os.path.join(outdir, name)
        if not os.path.isfile(src):
            continue  # subdirectories (e.g., prior "_detail", deal subfolders) untouched
        if name in _TOP_LEVEL_KEEP:
            continue
        dst = os.path.join(detail_dir, name)
        # Overwrite-on-move: re-runs should end up with a single authoritative copy
        if os.path.exists(dst):
            os.remove(dst)
        shutil.move(src, dst)
        moved.append(dst)
    return moved


def finalize_bundle(
    outdir: str,
    summary_df: pd.DataFrame,
    cfg: Dict[str, Any],
    hospital_name: Optional[str] = None,
) -> Dict[str, Any]:
    """One-call orchestrator: workbook + data_requests + organize detail.

    Returns ``{"workbook": path, "data_requests": path, "detail_moved": [...]}``.
    Safe to call multiple times against the same outdir.
    """
    workbook_path = write_diligence_workbook(outdir, summary_df, cfg)
    requests_path = write_data_requests(outdir, cfg, hospital_name=hospital_name)
    moved = organize_detail(outdir)
    return {
        "workbook": workbook_path,
        "data_requests": requests_path,
        "detail_moved": moved,
    }
