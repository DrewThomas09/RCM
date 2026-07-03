"""
suggested_fixes.py  (v45)
=========================

Turns every coding-edit flag into a suggested correction, with the rule, the
provenance, and a flag for whether it is safe to auto-apply. This is how the tool
fixes problems rather than only naming them, done in the one defensible way for a
diligence tool: nothing is silently rewritten. Each suggestion is a proposed value
plus the reason and the source, written to a corrections companion the analyst
reviews before anything is applied. Deterministic repairs (formatting,
standardization) are marked auto-applicable; judgment calls (recode a diagnosis,
cap units) are marked review-required.

For each issue the suggestion carries:
  field                which column the fix touches
  current_value        what is there now
  suggested_value      the proposed corrected value
  fix_rule             the deterministic rule that produced the suggestion
  confidence           how sure the suggestion is (high for mechanical, lower for
                       judgment calls)
  safe_to_auto_apply   whether it can be applied without human review
  provenance           the reference source and vintage behind the rule
  dollars              the exposure on the row, for triage

The suggestions are generated from the screen outputs in coding_edits.py, so this
module adds the fix layer on top of the flag layer without re-running the screens.
"""
from __future__ import annotations

import pandas as pd
import numpy as np


def _dollars_for(std, rows, mapping):
    if std is None:
        return pd.Series([np.nan] * len(rows))
    acol = (mapping or {}).get("allowed_amt", "allowed_amt")
    acol = acol if acol in std.columns else ("allowed_amt" if "allowed_amt" in std.columns else None)
    if acol is None:
        return pd.Series([np.nan] * len(rows), index=rows)
    return pd.to_numeric(std.loc[rows, acol], errors="coerce")


def from_mue(flagged: pd.DataFrame, std=None, mapping=None) -> pd.DataFrame:
    """MUE over-cap: suggest capping units to the MUE value. Review-required,
    because the excess may be legitimately split across dates or reflect a real
    high-dose regimen; the cap is a proposal, not a correction."""
    if flagged is None or flagged.empty or "units_over_mue" not in flagged.columns and "mue_value" not in flagged.columns:
        return pd.DataFrame()
    rows = flagged["row"] if "row" in flagged.columns else flagged.index
    d = _dollars_for(std, rows, mapping)
    out = pd.DataFrame({
        "row": list(rows),
        "field": "units",
        "current_value": flagged.get("units"),
        "suggested_value": flagged.get("mue_value"),
        "fix_rule": "cap units to the Medicare MUE value for the code",
        "confidence": "medium",
        "safe_to_auto_apply": False,
        "provenance": flagged.attrs.get("source", "CMS NCCI MUE"),
        "issue": "units_exceed_mue",
        "dollars": d.to_numpy(),
    })
    return out


def from_icd_dos(flagged: pd.DataFrame, std=None, mapping=None) -> pd.DataFrame:
    """ICD invalid for the service-date fiscal year: suggest recode. There is no
    deterministic single correct replacement, so the suggestion is to recode with
    the valid-code set for that year, flagged review-required."""
    if flagged is None or flagged.empty or "diagnosis" not in flagged.columns:
        return pd.DataFrame()
    rows = flagged["row"] if "row" in flagged.columns else flagged.index
    d = _dollars_for(std, rows, mapping)
    out = pd.DataFrame({
        "row": list(rows),
        "field": "diagnosis",
        "current_value": flagged.get("diagnosis"),
        "suggested_value": "(recode: not valid in FY " + flagged.get("fiscal_year").astype(str) + ")",
        "fix_rule": "recode to a diagnosis valid in the fiscal year of service",
        "confidence": "low",
        "safe_to_auto_apply": False,
        "provenance": flagged.attrs.get("source", "CMS ICD-10-CM order files"),
        "issue": "diagnosis_invalid_for_dos",
        "dollars": d.to_numpy(),
    })
    return out


def from_jw_jz(flagged: pd.DataFrame, std=None, mapping=None) -> pd.DataFrame:
    """Single-dose line missing JW/JZ: suggest adding JZ (the zero-waste default
    that CMS requires when there is no discarded amount). Auto-applicable only in
    the sense that the modifier is mechanically required; still marked review so a
    real discarded amount (which needs JW plus a wastage line) is not masked."""
    if flagged is None or flagged.empty:
        return pd.DataFrame()
    # only the true missing-modifier flags, not the unjudged-missing-field rows
    if "verdict" in flagged.columns:
        flagged = flagged[flagged["verdict"] == "flag"]
    if flagged.empty:
        return pd.DataFrame()
    rows = flagged["row"] if "row" in flagged.columns else flagged.index
    d = _dollars_for(std, rows, mapping)
    out = pd.DataFrame({
        "row": list(rows),
        "field": "modifiers",
        "current_value": "(no JW/JZ)",
        "suggested_value": "add JZ (zero discarded) or JW + wastage line if discarded",
        "fix_rule": "single-dose drug requires JZ when no waste, JW when waste",
        "confidence": "high",
        "safe_to_auto_apply": False,
        "provenance": flagged.attrs.get("source", "CMS JW/JZ policy"),
        "issue": "missing_wastage_modifier",
        "dollars": d.to_numpy(),
    })
    return out


def from_deactivated(flagged: pd.DataFrame, std=None, mapping=None) -> pd.DataFrame:
    """Deactivated billing NPI: suggest re-recovery of a valid biller (the tool's
    own recovery, routed through the review queue). No mechanical replacement."""
    if flagged is None or flagged.empty or "billing_npi" not in flagged.columns:
        return pd.DataFrame()
    rows = flagged["row"] if "row" in flagged.columns else flagged.index
    d = _dollars_for(std, rows, mapping)
    out = pd.DataFrame({
        "row": list(rows),
        "field": "billing_npi",
        "current_value": flagged.get("billing_npi"),
        "suggested_value": "(re-recover: NPI deactivated as of service date)",
        "fix_rule": "billing NPI was deactivated on/before the service date",
        "confidence": "low",
        "safe_to_auto_apply": False,
        "provenance": flagged.attrs.get("source", "CMS NPPES deactivation"),
        "issue": "deactivated_billing_npi",
        "dollars": d.to_numpy(),
    })
    return out


def from_age_sex(flagged: pd.DataFrame, std=None, mapping=None) -> pd.DataFrame:
    """Age/sex conflict: suggest review of the diagnosis or the demographic. No
    deterministic correction; the error could be in either field."""
    if flagged is None or flagged.empty or "diagnosis" not in flagged.columns:
        return pd.DataFrame()
    rows = flagged["row"] if "row" in flagged.columns else flagged.index
    d = _dollars_for(std, rows, mapping)
    out = pd.DataFrame({
        "row": list(rows),
        "field": "diagnosis|patient_age|patient_sex",
        "current_value": flagged.get("diagnosis"),
        "suggested_value": "(review: " + flagged.get("conflict").astype(str) + ")",
        "fix_rule": "diagnosis conflicts with patient age or sex",
        "confidence": "low",
        "safe_to_auto_apply": False,
        "provenance": "MCE/IOCE structure",
        "issue": "age_sex_conflict",
        "dollars": d.to_numpy(),
    })
    return out


# map an issue key to its suggestion builder
_BUILDERS = {
    "mue_units": from_mue,
    "icd_dos_validity": from_icd_dos,
    "jw_jz_wastage": from_jw_jz,
    "npi_deactivated": from_deactivated,
    "age_sex_conflict": from_age_sex,
}


def build_suggestions(screen_results: dict, std=None, mapping=None) -> pd.DataFrame:
    """Assemble a single corrections companion from a dict of screen outputs
    keyed by fix key (as run_selected returns). Every suggestion carries its rule,
    confidence, provenance, and whether it is safe to auto-apply."""
    frames = []
    for key, builder in _BUILDERS.items():
        res = screen_results.get(key)
        if res is None or not isinstance(res, pd.DataFrame) or res.empty:
            continue
        try:
            sug = builder(res, std=std, mapping=mapping)
            if not sug.empty:
                frames.append(sug)
        except Exception:
            continue
    if not frames:
        out = pd.DataFrame(columns=["row", "field", "current_value", "suggested_value",
                                    "fix_rule", "confidence", "safe_to_auto_apply",
                                    "provenance", "issue", "dollars"])
        out.attrs["note"] = "No coding-edit issues found, so no corrections suggested."
        return out
    out = pd.concat(frames, ignore_index=True)
    n_auto = int(out["safe_to_auto_apply"].sum())
    d = pd.to_numeric(out["dollars"], errors="coerce").fillna(0)
    out.attrs["note"] = (
        f"{len(out)} suggested corrections across {out['issue'].nunique()} issue types, "
        f"${d.sum():,.0f} exposure. {n_auto} are safe to auto-apply; the rest are "
        f"review-required. Nothing is applied to the data automatically: this is the "
        f"corrections companion, reviewed before any fix is committed.")
    return out


def apply_safe_suggestions(std: pd.DataFrame, suggestions: pd.DataFrame,
                           mapping=None) -> tuple:
    """Apply ONLY the suggestions marked safe_to_auto_apply to a copy of std,
    preserving originals in a shadow column. Returns (cleaned, applied_log).
    Everything else is left for review. In practice most coding-edit suggestions
    are review-required, so this is conservative by design."""
    if suggestions is None or suggestions.empty:
        return std.copy(), pd.DataFrame()
    safe = suggestions[suggestions["safe_to_auto_apply"] == True]  # noqa: E712
    if safe.empty:
        return std.copy(), pd.DataFrame()
    cleaned = std.copy()
    applied = []
    for _, s in safe.iterrows():
        field = s["field"]
        if field not in cleaned.columns:
            continue
        r = s["row"]
        orig_col = f"{field}__original"
        if orig_col not in cleaned.columns:
            cleaned[orig_col] = cleaned[field]
        cleaned.at[r, field] = s["suggested_value"]
        applied.append({"row": r, "field": field, "from": s["current_value"],
                        "to": s["suggested_value"], "rule": s["fix_rule"]})
    return cleaned, pd.DataFrame(applied)
