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
# runaway export; the count is always reported in full and the cap is
# sized for real large files, not just demos.
_MAX_SUGGESTIONS = 50_000


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
        # Read the SAME sheet the stdlib pipeline picks
        # (engine._xlsx_best_sheet): vendor extracts lead with cover
        # sheets, and pandas' default of sheet 0 made the mapping editor
        # detect a 3-column 'Detail' tab while the real table sat on a
        # later 'DATA' tab.
        from .engine import _xlsx_best_sheet
        sheet = _xlsx_best_sheet(data)
        return pd.read_excel(io.BytesIO(data), dtype=str,
                             sheet_name=sheet if sheet is not None else 0)
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
    out = {
        "headers": [str(c) for c in raw.columns],
        "mapping": {k: (str(v) if v else "") for k, v in mapping.items()},
        "roles": [{"key": k, "label": lbl} for k, lbl in EDITABLE_ROLES],
    }
    if data[:4] == b"PK\x03\x04":
        # Tell the mapping editor which worksheet is being mapped so a
        # multi-sheet workbook is never a silent guess.
        try:
            from .engine import _xlsx_best_sheet
            sheet = _xlsx_best_sheet(data)
            if sheet:
                out["sheet"] = sheet
        except Exception:  # noqa: BLE001
            pass
    return out


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

    # Extended anomaly screens — additional v49 modules not in clean_all's
    # default set (Benford's law, per-unit rate outliers, rounding pathology,
    # modifier economics, provider concentration). Each is guarded.
    payload["extended"] = _extended_screens(std, mapping, pd)

    return payload


def _extended_screens(std, mapping, pd) -> List[dict]:
    """Run additional offline v49 anomaly modules; return a summary list."""
    out: List[dict] = []
    allowed = mapping.get("allowed_amt")
    units = mapping.get("units")
    if not allowed or allowed not in getattr(std, "columns", []):
        return out
    allowed_s = pd.to_numeric(std[allowed], errors="coerce")

    def _add(key, label, value, note):
        out.append({"key": key, "label": label, "value": value, "note": note})

    # Benford's-law first-digit conformance on allowed amounts (fraud signal).
    try:
        from .vendor_v49.npi_recovery import distribution_screens as DS
        bf = DS.benford_first_digit(allowed_s.dropna())
        attrs = getattr(bf, "attrs", {})
        if "chi_square" in attrs:
            chi = float(attrs["chi_square"])
            verdict = str(attrs.get("verdict", "")).split(":")[0].split("(")[0].strip().lower()
            _add("benford", "Benford first-digit (allowed $)",
                 f"χ²={chi:.1f} · {verdict or 'see note'}",
                 str(attrs.get("note", "Leading-digit distribution vs Benford.")))
    except Exception:  # noqa: BLE001
        pass

    # Rounding pathology — an excess of round-dollar amounts by group.
    try:
        from .vendor_v49.npi_recovery import distribution_screens as DS
        grp = mapping.get("payer") or mapping.get("billing_npi")
        if grp and grp in std.columns:
            rp = DS.rounding_pathology(std, allowed=allowed_s, group_col=grp)
            if hasattr(rp, "columns") and "note" not in rp.columns and len(rp):
                _add("rounding", "Rounding pathology",
                     f"{len(rp)} group(s) flagged",
                     "Groups with an implausible share of round-dollar amounts.")
    except Exception:  # noqa: BLE001
        pass

    # Per-unit rate outliers ($/unit far from the code's panel median).
    try:
        if units and units in std.columns:
            from .vendor_v49.npi_recovery import unit_integrity as UI
            ro = UI.rate_outlier_screen(std, allowed=allowed_s,
                                        units=pd.to_numeric(std[units], errors="coerce"))
            if hasattr(ro, "columns") and "row" in ro.columns and len(ro):
                _add("rate_outlier", "Allowed-per-unit rate outliers",
                     f"{len(ro)} lines flagged",
                     "Lines whose $/unit is a large outlier vs the code median.")
    except Exception:  # noqa: BLE001
        pass

    # Provider concentration (HHI, 0–10000 DOJ scale) on allowed dollars.
    try:
        from .vendor_v49.npi_recovery import concentration as CC
        bcol = mapping.get("billing_npi")
        if bcol and bcol in std.columns:
            by = std.assign(_a=allowed_s.fillna(0)).groupby(bcol)["_a"].sum()
            hhi = CC.hhi(by)
            band = ("highly concentrated" if hhi >= 2500 else
                    "moderately concentrated" if hhi >= 1500 else "unconcentrated")
            _add("hhi", "Billing-provider concentration (HHI)",
                 f"{hhi:.0f} · {band}",
                 "Herfindahl index (0–10000) of allowed $ across billing NPIs.")
    except Exception:  # noqa: BLE001
        pass

    return out
