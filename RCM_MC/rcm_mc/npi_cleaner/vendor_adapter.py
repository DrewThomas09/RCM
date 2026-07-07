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

# What each v49 coding-edit screen needs in order to run at all —
# rendered as an honest note when a screen is absent from the results
# (clean_all drops non-applicable screens without a trace). PTP is also
# dropped when it ran and found zero pairs, so its wording covers both.
_SCREEN_REQUIREMENTS: Dict[str, str] = {
    "mue_units": ("Screen did not run — needs a HCPCS/procedure column "
                  "and a units column."),
    "icd_dos_validity": ("Screen did not run — needs a diagnosis "
                         "(ICD-10) column."),
    "age_sex_conflict": ("Screen did not run — needs patient age and "
                         "sex columns."),
    "jw_jz_wastage": ("Screen did not run — needs a HCPCS column "
                      "(single-dose drug codes)."),
    "npi_deactivated": ("Screen did not run — needs a billing NPI "
                        "column."),
    "ptp_pairs": ("No PTP conflicts found, or the screen could not run "
                  "(needs a HCPCS column). Reference is a 4,376-pair "
                  "sample of the ~4M-pair NCCI set — absence of "
                  "conflicts is a floor, not a clearance."),
}


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
    # ``screen_details`` carries what the bare counts used to drop: each
    # screen's own frame.attrs disclosure (e.g. "Seed is a sample of the
    # full CMS file") and its reference-data source — without it a
    # "0 rows" line read as a clean pass when coverage was <2%.
    # ``screens`` stays a name → int map for back-compat.
    screens = res.get("screens", {}) or {}
    payload["screens"] = {}
    payload["screen_details"] = {}
    issue_rows: Dict[str, dict] = {}
    for name, frame in screens.items():
        cols = getattr(frame, "columns", [])
        if not hasattr(frame, "columns"):
            continue
        attrs = getattr(frame, "attrs", {}) or {}
        # Per-row screens carry "row"; the PTP screen carries code PAIRS
        # (col1/col2) instead and used to be dropped entirely — its
        # conflicts never reached the page even when it fired.
        if "row" not in cols and not ("col1" in cols and "col2" in cols):
            # A note-only frame is a screen explaining why it could NOT
            # run (missing column / missing reference file) — surface
            # that honestly instead of silently dropping the screen.
            if "note" in cols and len(frame):
                payload.setdefault("screen_notes", {})[name] = str(
                    frame["note"].iloc[0])
            continue
        payload["screens"][name] = int(len(frame))
        payload["screen_details"][name] = {
            "n": int(len(frame)),
            "note": str(attrs.get("note", "") or ""),
            "source": str(attrs.get("source", "") or ""),
        }
        show = [c for c in cols if c not in ("verdict",)][:8]
        sample = []
        for _, r in frame.head(15).iterrows():
            sample.append({c: ("" if pd.isna(r[c]) else str(r[c])) for c in show})
        if sample:
            issue_rows[name] = {"columns": show, "rows": sample}
    payload["issue_rows"] = issue_rows

    # Screens that did NOT run (clean_all silently drops a screen whose
    # required column or reference file is absent). "npi_deactivated: 0"
    # vs "npi_deactivated: did not run" is exactly the honesty gap a
    # compliance-adjacent surface cannot leave open.
    for name, req in _SCREEN_REQUIREMENTS.items():
        if name not in payload["screens"]:
            payload.setdefault("screen_notes", {}).setdefault(name, req)

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

    # Offline recovery views — SAD jurisdiction classification and the
    # dollar-ranked gap inventory. Both are fully offline pandas modules
    # with vendored seeds, but their only call site used to be the
    # networked deep pipeline, so a no-egress deployment could never see
    # them despite everything needed being on disk.
    try:
        payload.update(_offline_recovery(std, mapping, pd))
    except Exception:  # noqa: BLE001 — recovery views never block the run
        pass

    # Machine-readable reference/connector data status, so the scorecard
    # (and everything rendered from it) can say which sources were real,
    # which were samples, and which were absent on THIS run.
    try:
        from . import connectors as _connectors
        payload["reference_status"] = _connectors.connector_status()
    except Exception:  # noqa: BLE001
        pass

    return payload


def _records(frame, pd, cap: int = 50) -> List[dict]:
    """First ``cap`` rows of a frame as plain-JSON records."""
    out: List[dict] = []
    for _, r in frame.head(cap).iterrows():
        rec = {}
        for c in frame.columns:
            v = r[c]
            if pd.isna(v):
                rec[c] = ""
            elif isinstance(v, (int, float)) and not isinstance(v, bool):
                rec[c] = float(v) if isinstance(v, float) else int(v)
            else:
                rec[c] = str(v)
        out.append(rec)
    return out


def _offline_recovery(std, mapping, pd) -> Dict[str, object]:
    """SAD jurisdiction rollup + recoverable-gap inventory from the
    vendored v49 modules — offline, guarded, empty dict on any miss."""
    out: Dict[str, object] = {}
    try:
        from .vendor_v49.npi_recovery.coding_edits import _default_ref
        ref = _default_ref()
    except Exception:  # noqa: BLE001
        return out
    cols = getattr(std, "columns", [])
    allowed_col = (mapping or {}).get("allowed_amt")
    allowed = (pd.to_numeric(std[allowed_col], errors="coerce")
               if allowed_col and allowed_col in cols else None)

    # --- SAD jurisdiction / route classification (needs a HCPCS column) ---
    try:
        hc = (mapping or {}).get("hcpcs")
        if hc and hc in cols:
            from .vendor_v49.npi_recovery import sad_jurisdiction as SAD
            cls = SAD.classify_frame(
                std, ref_dir=ref, allowed=allowed, hcpcs_col=hc,
                state_col=((mapping or {}).get("state") or "state"),
                modifier_col=(mapping or {}).get("modifiers"))
            if (hasattr(cls, "columns") and "verdict" in cls.columns
                    and len(cls)):
                sad: Dict[str, object] = {
                    "rollup": _records(cls, pd),
                    "ambiguous_dollars": float(
                        cls.attrs.get("ambiguous_dollars") or 0.0),
                    "snapshot_codes": int(
                        cls.attrs.get("snapshot_codes") or 0),
                    "note": str(cls.attrs.get("note", "") or ""),
                    "source": "vendored CMS SAD snapshot + MAC roster "
                              "(sad_jurisdiction v39)",
                }
                amb = SAD.ambiguous_lines(std, cls, allowed=allowed,
                                          hcpcs_col=hc, top_n=15)
                if hasattr(amb, "columns") and "hcpcs" in amb.columns:
                    sad["ambiguous"] = _records(amb, pd, cap=15)
                out["sad"] = sad
    except Exception:  # noqa: BLE001
        pass

    # --- Recoverable-gap inventory + executable resolution plan ---
    try:
        from .vendor_v49.npi_recovery import missing_resolver as MR
        inv = MR.gap_inventory(std, allowed=allowed, ref_dir=ref)
        if hasattr(inv, "columns") and "gap" in inv.columns and len(inv):
            gaps: Dict[str, object] = {
                "inventory": _records(inv, pd),
                "total_gap_dollars": float(
                    inv.attrs.get("total_gap_dollars") or 0.0),
                "note": str(inv.attrs.get("note", "") or ""),
            }
            plan = MR.resolution_plan(std, allowed=allowed, ref_dir=ref)
            if hasattr(plan, "columns") and "gap" in plan.columns:
                gaps["plan"] = _records(plan, pd)
            out["gaps"] = gaps
    except Exception:  # noqa: BLE001
        pass
    return out


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
