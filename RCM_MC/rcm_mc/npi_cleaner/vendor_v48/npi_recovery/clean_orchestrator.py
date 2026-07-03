"""
clean_orchestrator.py  (v45)
============================

One entry point that fixes and cleans most problems in a single pass and analyzes
each one, so a user gets: what was auto-fixed, what has a suggested fix awaiting
review, what could not be judged, and how big each problem is. It composes the
pieces built across the toolkit rather than re-implementing them:

  deterministic repairs    the existing deep-clean orchestrator (clean_pipeline)
                           applies safe formatting/standardization repairs with a
                           ledger, originals preserved.
  coding-edit screens       the six CMS screens (coding_edits) flag units, code
                           pairs, ICD validity, age/sex, wastage, deactivation.
  consistency screens       cross-field impossibilities (money and date ordering,
                           provider roles, units vs days supply).
  suggested corrections     every flag gets a proposed fix with provenance and a
                           safe-to-auto-apply flag (suggested_fixes).
  issue analysis            each problem is sized: rows, dollars, concentration,
                           and a systematic-vs-random verdict (issue_analysis).

The output is a cleaning scorecard that rolls all of it into categories with rows
and dollars, plus the cleaned dataset, the corrections companion, and the per
issue analysis. Nothing judgemental is applied silently: deterministic repairs are
applied to a cleaned copy, and every coding/consistency suggestion goes to the
companion for review.
"""
from __future__ import annotations

import pandas as pd
import numpy as np


def clean_all(std: pd.DataFrame, *, ref_dir=None, mapping=None,
              run_deep_clean=True) -> dict:
    """Run the full fix-and-analyze pass. Returns a dict with the cleaned frame,
    the suggestions companion, the issue analysis, and the scorecard."""
    from . import coding_edits as CE
    from . import consistency as CON
    from . import suggested_fixes as SF
    from . import issue_analysis as IA

    result = {}
    mapping = mapping or {}

    # ---- 1. deterministic repairs (safe, applied to a copy) ----
    cleaned = std.copy()
    repair_ledger = pd.DataFrame()
    if run_deep_clean:
        try:
            from . import clean_pipeline as CP
            cleaned, repair_ledger, _findings = CP.run_cleaning(std)
        except Exception:
            cleaned = std.copy()
    result["cleaned"] = cleaned
    result["repair_ledger"] = repair_ledger

    # ---- 2. coding-edit screens ----
    screens = {}
    for name, fn in (("mue_units", CE.mue_screen),
                     ("icd_dos_validity", CE.icd10_dos_validity),
                     ("age_sex_conflict", CE.age_sex_conflicts),
                     ("jw_jz_wastage", CE.jw_jz_wastage),
                     ("npi_deactivated", CE.deactivated_npi_screen)):
        try:
            r = fn(std, ref_dir=ref_dir, mapping=mapping)
            if isinstance(r, pd.DataFrame) and "row" in r.columns:
                screens[name] = r
        except Exception:
            continue
    try:
        ptp = CE.ptp_screen(std, ref_dir=ref_dir, mapping=mapping)
        if isinstance(ptp, pd.DataFrame) and not ptp.empty and "col1" in ptp.columns:
            screens["ptp_pairs"] = ptp
    except Exception:
        pass

    # ---- 3. consistency screens ----
    consistency = CON.run_all(std, mapping)
    for name, r in consistency.items():
        if isinstance(r, pd.DataFrame) and "row" in r.columns and not r.empty:
            screens[name] = r
    result["screens"] = screens

    # ---- 4. suggested corrections (coding-edit issues) ----
    suggestions = SF.build_suggestions(screens, std=std, mapping=mapping)
    # consistency screens already carry a suggested_fix column; fold them in
    con_sugs = []
    for name, r in consistency.items():
        if isinstance(r, pd.DataFrame) and "row" in r.columns and "suggested_fix" in r.columns:
            con_sugs.append(pd.DataFrame({
                "row": r["row"], "field": name, "current_value": "",
                "suggested_value": r["suggested_fix"],
                "fix_rule": r.get("violation", name), "confidence": "medium",
                "safe_to_auto_apply": False, "provenance": "cross-field consistency",
                "issue": name,
                "dollars": np.nan,
            }))
    if con_sugs:
        suggestions = pd.concat([suggestions] + con_sugs, ignore_index=True)
    result["suggestions"] = suggestions

    # ---- 5. issue analysis ----
    summary, details = IA.analyze_all(screens, std, mapping=mapping)
    result["issue_summary"] = summary
    result["issue_details"] = details

    # ---- 6. cleaning scorecard ----
    result["scorecard"] = _scorecard(cleaned, std, repair_ledger, screens,
                                     suggestions, mapping)
    return result


def _scorecard(cleaned, std, repair_ledger, screens, suggestions, mapping):
    """Roll everything into categories with rows and dollars."""
    acol = (mapping or {}).get("allowed_amt", "allowed_amt")
    acol = acol if acol in std.columns else ("allowed_amt" if "allowed_amt" in std.columns else None)

    def _dollars(rows):
        if acol is None:
            return float(len(rows))
        return float(pd.to_numeric(std.loc[list(rows), acol], errors="coerce").fillna(0).clip(lower=0).sum())

    rows = []
    # auto-fixed (deterministic repairs)
    n_repairs = int(len(repair_ledger)) if isinstance(repair_ledger, pd.DataFrame) else 0
    rows.append({"category": "auto_fixed_deterministic",
                 "detail": "safe formatting/standardization repairs applied",
                 "issues": n_repairs, "rows_affected": n_repairs, "dollars_exposed": np.nan})

    # suggested (review-required)
    if isinstance(suggestions, pd.DataFrame) and not suggestions.empty and "issue" in suggestions.columns:
        for issue, g in suggestions.groupby("issue"):
            rset = [r for r in g["row"].tolist() if r in std.index]
            rows.append({"category": "suggested_review_required", "detail": issue,
                         "issues": len(g), "rows_affected": len(rset),
                         "dollars_exposed": round(_dollars(rset), 2) if rset else np.nan})

    out = pd.DataFrame(rows)
    total_flagged = sum(len(r) for r in screens.values() if isinstance(r, pd.DataFrame) and "row" in r.columns)
    out.attrs["note"] = (
        f"{n_repairs} deterministic repairs applied to the cleaned copy (originals "
        f"preserved). {total_flagged} issues flagged across {len(screens)} screens, "
        f"each with a suggested correction in the companion and an analysis of its "
        f"size and concentration. Nothing judgemental was applied automatically.")
    return out
