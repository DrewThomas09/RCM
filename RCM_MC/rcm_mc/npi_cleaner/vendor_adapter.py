"""Drive the *real* v49 deterministic engine from the NPI cleaner.

v49 is the complete package (unlike the v48 upload, which was missing its
core). Its offline orchestrator — ``schema.standardize_any`` +
``clean_orchestrator.clean_all`` — runs with no third-party deps beyond
pandas/numpy and no network, and now finds the vendored CMS reference tables
(NCCI MUE, ICD-10-CM validity, PTP pairs, deactivated-NPI, JW/JZ single-dose),
so every coding-edit + consistency screen lights up for real.

``clean_all`` returns the genuine v49 outputs:
  * ``repair_ledger`` — safe deterministic repairs applied to a cleaned copy
  * ``screens``       — MUE / PTP / ICD-DOS / age-sex / JW-JZ wastage /
                        deactivated-NPI / cross-field consistency
  * ``suggestions``   — a corrections companion (row, current→suggested, rule,
                        confidence, safe-to-auto-apply, provenance, $)
  * ``issue_summary`` — each issue sized: rows, % rows, $ exposure, % $,
                        drug/provider HHI, and a systematic-vs-random verdict

Everything is guarded: if pandas or the vendored modules are unavailable,
``run(...)`` returns ``None`` and the caller falls back to the stdlib cleaner.

The full networked ``run_pipeline`` (live NPPES/CMS recovery, Steps 0–8) is a
batch/CLI job — it constructs live clients and can run for minutes — so it is
deliberately not invoked from the web request. The interactive page uses this
deterministic path plus the bounded live NPPES cross-check in ``nppes_bridge``.
"""
from __future__ import annotations

import io
import math
from typing import Dict, List, Optional

# Cap the corrections companion so a pathological file can't produce a
# multi-hundred-MB export; the count is always reported in full.
_MAX_SUGGESTIONS = 5000


def available() -> bool:
    """True when pandas and the vendored v49 offline engine import."""
    try:
        import pandas  # noqa: F401
        from .vendor_v49.npi_recovery import schema, clean_orchestrator  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False


def _read_df(data: bytes):
    import pandas as pd
    if data[:4] == b"PK\x03\x04":  # xlsx
        return pd.read_excel(io.BytesIO(data), dtype=str)
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("latin-1", errors="replace")
    return pd.read_csv(io.StringIO(text), sep=None, engine="python",
                       dtype=str, keep_default_na=False)


def _num(v) -> Optional[float]:
    try:
        f = float(v)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


# The column roles the mapping editor exposes, in display order — a curated
# subset of the v49 canonical schema that the cleaner/connectors act on.
EDITABLE_ROLES: List[tuple] = [
    ("billing_npi", "Billing NPI"),
    ("rendering_npi", "Rendering NPI"),
    ("referring_npi", "Referring NPI"),
    ("billing_name", "Billing / org name"),
    ("state", "State"),
    ("hcpcs", "Procedure (HCPCS/CPT)"),
    ("ndc", "Drug NDC"),
    ("drug_name", "Drug name"),
    ("date_of_service", "Service date"),
    ("allowed_amt", "Allowed $"),
    ("billed_amt", "Billed $"),
    ("paid_amt", "Paid $"),
    ("units", "Units"),
    ("days_supply", "Days supply"),
    ("diagnosis", "Diagnosis (ICD-10)"),
    ("modifiers", "Modifiers"),
    ("payer", "Payer"),
]


def detect(data: bytes) -> Optional[dict]:
    """Detect the column → canonical-role mapping for the mapping editor.

    Returns ``{headers, mapping}`` (mapping = role→header or None) or ``None``
    when the v49 detector is unavailable.
    """
    try:
        from .vendor_v49.npi_recovery import schema
    except Exception:  # noqa: BLE001
        return None
    try:
        raw = _read_df(data)
    except Exception:  # noqa: BLE001
        return None
    if raw is None or raw.shape[1] == 0:
        return None
    try:
        mapping, _report = schema.detect_columns(raw)
    except Exception:  # noqa: BLE001
        return None
    return {
        "headers": [str(c) for c in raw.columns],
        "mapping": {k: (str(v) if v else "") for k, v in mapping.items()},
        "roles": [{"key": k, "label": lbl} for k, lbl in EDITABLE_ROLES],
    }


def run(data: bytes, overrides: Optional[Dict[str, str]] = None) -> Optional[dict]:
    """Run the real v49 deterministic engine. Returns a display payload plus a
    capped ``suggestions_records`` companion, or ``None`` when unavailable.

    ``overrides`` maps canonical role → the header to use, letting the user
    correct auto-detection from the mapping editor.
    """
    try:
        import pandas as pd
        from .vendor_v49.npi_recovery import schema, clean_orchestrator as CO
    except Exception:  # noqa: BLE001
        return None

    try:
        raw = _read_df(data)
    except Exception:  # noqa: BLE001
        return None
    if raw is None or raw.shape[1] == 0 or len(raw) == 0:
        return None

    # Only pass overrides whose target column actually exists.
    ov = {k: v for k, v in (overrides or {}).items()
          if v and v in raw.columns} or None
    try:
        out = schema.standardize_any(raw, ov)
        std = out[0] if isinstance(out, tuple) else out
        mapping = out[1] if isinstance(out, tuple) and len(out) > 1 else {}
    except Exception:  # noqa: BLE001
        return None

    try:
        res = CO.clean_all(std, mapping=mapping)
    except Exception:  # noqa: BLE001
        return None

    payload: Dict[str, object] = {
        "engine": "npi_recovery v49 · schema.standardize_any + clean_all",
        "mapping": {k: str(v) for k, v in (mapping or {}).items()},
    }

    ledger = res.get("repair_ledger")
    payload["repairs"] = int(len(ledger)) if ledger is not None and hasattr(
        ledger, "__len__") else 0

    # Screen flag counts (frames that carry a per-row "row" column), plus a
    # capped sample of the actual offending rows per screen for drill-down.
    screens = res.get("screens", {}) or {}
    payload["screens"] = {}
    issue_rows: Dict[str, dict] = {}
    for name, frame in screens.items():
        cols = getattr(frame, "columns", [])
        if not (hasattr(frame, "columns") and "row" in cols):
            continue
        payload["screens"][name] = int(len(frame))
        show = [c for c in cols if c not in ("verdict",)][:8]
        sample = []
        for _, r in frame.head(15).iterrows():
            sample.append({c: ("" if pd.isna(r[c]) else str(r[c])) for c in show})
        if sample:
            issue_rows[name] = {"columns": show, "rows": sample}
    payload["issue_rows"] = issue_rows

    # Sized issues (the headline: rows, $ exposure, systematic verdict).
    issues: List[dict] = []
    isum = res.get("issue_summary")
    if isum is not None and hasattr(isum, "iterrows"):
        for _, r in isum.iterrows():
            issues.append({
                "issue": str(r.get("issue", "")),
                "rows": int(r.get("rows_flagged", 0) or 0),
                "pct_rows": _num(r.get("pct_rows")),
                "dollars": _num(r.get("dollar_exposure")),
                "pct_dollars": _num(r.get("pct_dollars")),
                "systematic": str(r.get("systematic_signal", "")),
            })
        issues.sort(key=lambda d: (d["dollars"] or 0), reverse=True)
    payload["issues"] = issues

    # Corrections companion.
    sug = res.get("suggestions")
    records: List[dict] = []
    if sug is not None and hasattr(sug, "iterrows") and len(sug):
        cols = [c for c in ("row", "field", "current_value", "suggested_value",
                            "fix_rule", "confidence", "safe_to_auto_apply",
                            "provenance", "issue", "dollars")
                if c in sug.columns]
        for _, r in sug.head(_MAX_SUGGESTIONS).iterrows():
            records.append({c: ("" if pd.isna(r[c]) else str(r[c])) for c in cols})
    payload["suggestions_n"] = int(len(sug)) if sug is not None else 0
    payload["suggestions_records"] = records
    payload["suggestions_cols"] = (
        list(records[0].keys()) if records else [])

    cleaned = res.get("cleaned")
    if cleaned is not None and hasattr(cleaned, "shape"):
        payload["cleaned_rows"] = int(cleaned.shape[0])
        payload["cleaned_cols"] = int(cleaned.shape[1])

    return payload
