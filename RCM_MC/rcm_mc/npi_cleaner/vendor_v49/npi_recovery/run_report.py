"""
run_report.py  (v36)
====================

The output layer. The workbook now carries seventy-plus tabs whose verdicts live
in DataFrame attrs that a reader never sees, and error notes scattered one per
tab. This module turns the finished tab dictionary into a readable deliverable:

  findings_digest     harvests every tab's verdict and note, classifies each
                      into CRITICAL / WARN / INFO / PASS by a transparent
                      keyword model, and ranks them
  errors_log          every stage that degraded (skipped-with-exception notes),
                      one table, so partial failure is visible instead of quiet
  executive_summary   the one-page read: severity counts, the critical and warn
                      lines in full, and where to look next
  run_manifest        version, row and tab counts, error count, and an OK or
                      DEGRADED status for reproducibility and audit
  table_of_contents   every tab with size and a has-findings marker

Pure post-processing over the tab dict; nothing recomputes, nothing mutates.
Deterministic and offline.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

_CRITICAL = ("UPSTREAM DEFICIT", "NOT REPRODUCED", "DIVERGENT", "NOT idempotent",
             "do not chart", "UNDECODABLE", "NO HEADER-LIKE ROW")
_WARN = ("DEVIATES", "DIVERGES", "RESTATED (", "LOW stability", "stability LOW",
         "inflates growth", "INCOMPLETE_TAIL", "bends", "hazard", "AMBIGUOUS",
         "UNMAPPED", "overstatement", "NEAR MISS", "casualties", "flagged",
         "QUARANTINE", "leakage", "artifact")
_PASS = ("CONFORMS", "REPRODUCED", "MATCHES", "CONVERGENT", "clean", "idempotent",
         "no material", "does not move", "pass", "safe", "STABLE", "consistent",
         "no decimal-magnitude", "no cross-field", "no text-hygiene")


def classify_severity(text: str) -> str:
    t = str(text)
    for k in _CRITICAL:
        if k.lower() in t.lower():
            return "CRITICAL"
    for k in _WARN:
        if k.lower() in t.lower():
            return "WARN"
    for k in _PASS:
        if k.lower() in t.lower():
            return "PASS"
    return "INFO"


def _is_error_note(text: str) -> bool:
    t = str(text).lower()
    return ("skipped:" in t and ("error" in t or "exception" in t)) \
        or "error:" in t or ": traceback" in t \
        or (("skipped:" in t) and any(x in t for x in
                                      ("typeerror", "valueerror", "keyerror",
                                       "attributeerror", "indexerror", "zerodivision")))


def findings_digest(tabs: dict) -> pd.DataFrame:
    """One row per verdict-bearing tab: the finding text, its severity, and the
    tab to open. attrs verdicts win; note-only tabs contribute their note."""
    rows = []
    for name, df in tabs.items():
        if df is None or not isinstance(df, pd.DataFrame):
            continue
        texts = []
        at = getattr(df, "attrs", {}) or {}
        for key in ("verdict", "note"):
            if at.get(key):
                texts.append(str(at[key]))
        if list(df.columns) == ["note"] and len(df):
            texts.append(str(df["note"].iloc[0]))
        if not texts:
            continue
        full = " | ".join(dict.fromkeys(t for t in texts if t))
        sev = classify_severity(full)
        if _is_error_note(full):
            sev = "ERROR"
        rows.append({"severity": sev, "tab": name, "rows": int(len(df)),
                     "finding": full[:400]})
    if not rows:
        return pd.DataFrame({"note": ["no verdict-bearing tabs found"]})
    order = {"ERROR": 0, "CRITICAL": 1, "WARN": 2, "INFO": 3, "PASS": 4}
    out = (pd.DataFrame(rows)
           .assign(_o=lambda d: d["severity"].map(order))
           .sort_values(["_o", "tab"]).drop(columns="_o").reset_index(drop=True))
    counts = out["severity"].value_counts().to_dict()
    out.attrs["severity_counts"] = counts
    out.attrs["note"] = ("Every verdict the workbook renders, ranked. Severity is a "
                         "transparent keyword model (see run_report), not a judgment "
                         "call hidden in code.")
    return out


def errors_log(tabs: dict) -> pd.DataFrame:
    """Every stage that degraded to an exception note; empty means no stage
    failed anywhere in the run."""
    rows = []
    for name, df in tabs.items():
        if df is None or not isinstance(df, pd.DataFrame):
            continue
        texts = []
        if list(df.columns) == ["note"] and len(df):
            texts.append(str(df["note"].iloc[0]))
        at = getattr(df, "attrs", {}) or {}
        if at.get("note"):
            texts.append(str(at["note"]))
        for t in texts:
            if _is_error_note(t):
                rows.append({"stage": name, "message": t[:300]})
                break
    if not rows:
        out = pd.DataFrame({"note": ["no stage errors; every block ran clean"]})
        out.attrs["n_errors"] = 0
        return out
    out = pd.DataFrame(rows).sort_values("stage").reset_index(drop=True)
    out.attrs["n_errors"] = len(out)
    out.attrs["note"] = ("{} stage(s) degraded but the run completed; each block "
                         "isolates its own failure by design.".format(len(out)))
    return out


def run_manifest(tabs: dict, *, version: str = "", input_name: str = "",
                 n_rows: int | None = None, flags: str = "") -> pd.DataFrame:
    err = errors_log(tabs)
    n_err = err.attrs.get("n_errors", 0)
    dig = findings_digest(tabs)
    counts = dig.attrs.get("severity_counts", {}) if hasattr(dig, "attrs") else {}
    status = "DEGRADED ({} stage errors)".format(n_err) if n_err else "OK"
    rows = [
        {"field": "toolkit_version", "value": version},
        {"field": "input", "value": input_name},
        {"field": "panel_rows", "value": (n_rows if n_rows is not None else "")},
        {"field": "tabs_built", "value": len(tabs)},
        {"field": "run_status", "value": status},
        {"field": "stage_errors", "value": n_err},
        {"field": "critical_findings", "value": counts.get("CRITICAL", 0)},
        {"field": "warn_findings", "value": counts.get("WARN", 0)},
        {"field": "pass_findings", "value": counts.get("PASS", 0)},
        {"field": "flags", "value": flags},
        {"field": "guarantees", "value": "offline no-ops; rows conserved outside "
         "explicit opt-ins; nothing invented above ceilings; hand-rolled numpy/pandas "
         "only"},
    ]
    out = pd.DataFrame(rows)
    out.attrs["status"] = status
    out.attrs["note"] = "Reproducibility header; cite version and flags with any number."
    return out


def executive_summary(tabs: dict, *, version: str = "") -> pd.DataFrame:
    """The one-page read: severity counts, then every ERROR, CRITICAL, and WARN
    line in full, then the three strongest PASS proofs."""
    dig = findings_digest(tabs)
    if "severity" not in getattr(dig, "columns", []):
        return dig
    counts = dig.attrs.get("severity_counts", {})
    rows = [{"line": "RUN SUMMARY {}".format(version).strip(),
             "detail": " | ".join("{} {}".format(k, counts.get(k, 0))
                                  for k in ("ERROR", "CRITICAL", "WARN", "INFO", "PASS"))}]
    for sev in ("ERROR", "CRITICAL", "WARN"):
        for _, r in dig[dig["severity"] == sev].iterrows():
            rows.append({"line": "{} [{}]".format(sev, r["tab"]), "detail": r["finding"]})
    for _, r in dig[dig["severity"] == "PASS"].head(3).iterrows():
        rows.append({"line": "PASS [{}]".format(r["tab"]), "detail": r["finding"]})
    out = pd.DataFrame(rows)
    out.attrs["note"] = "Read this tab first; everything below it is the evidence."
    return out


def table_of_contents(tabs: dict) -> pd.DataFrame:
    dig = findings_digest(tabs)
    sev_of = {}
    if "tab" in getattr(dig, "columns", []):
        sev_of = dict(zip(dig["tab"], dig["severity"]))
    rows = []
    for name, df in tabs.items():
        if df is None or not isinstance(df, pd.DataFrame):
            continue
        rows.append({"tab": name, "rows": int(len(df)),
                     "cols": int(len(df.columns)),
                     "finding_severity": sev_of.get(name, "")})
    out = pd.DataFrame(rows).reset_index(drop=True)
    out.attrs["note"] = "Every tab in the workbook with its finding severity."
    return out


def attach_run_report(tabs: dict, *, version: str = "", input_name: str = "",
                      n_rows: int | None = None, flags: str = "") -> dict:
    """Mutating convenience for the pipeline: append the five report tabs in
    reading order. Safe to call on any tab dict."""
    tabs["Errors_Log"] = errors_log(tabs)
    tabs["Findings_Digest"] = findings_digest(tabs)
    tabs["Run_Manifest"] = run_manifest(tabs, version=version, input_name=input_name,
                                        n_rows=n_rows, flags=flags)
    tabs["Executive_Summary"] = executive_summary(tabs, version=version)
    tabs["Table_of_Contents"] = table_of_contents(tabs)
    return tabs
