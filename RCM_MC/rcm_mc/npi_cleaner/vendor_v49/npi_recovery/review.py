"""
review.py  (v46)
================

Closes the loop the v45 suggested corrections opened. v45 produced a companion of
proposed fixes, each with its rule and provenance, deliberately not applied. This
module lets an analyst accept or reject each and commit the accepted ones to a
final cleaned output, with every applied change written to a decision ledger so the
result is fully traceable.

The workflow is decision-driven, not automatic. A decisions table (one row per
suggestion, with an accept/reject/hold flag) drives what gets applied. Decisions
can come from a reviewer editing the companion, or from a rule (for example,
accept every suggestion whose confidence is high and whose issue is a specific
type). Accepted changes are applied to a copy, originals preserved in shadow
columns, and the decision ledger records who decided what and why.

Nothing here weakens the defensibility posture. Applying a fix is always an
explicit decision, the original is always kept, and the ledger always shows the
before, the after, the rule, and the decision.
"""
from __future__ import annotations

import pandas as pd
import numpy as np


ACCEPT = "accept"
REJECT = "reject"
HOLD = "hold"


def blank_decisions(suggestions: pd.DataFrame) -> pd.DataFrame:
    """Start a decisions table from a suggestions companion: every suggestion set
    to HOLD, ready for a reviewer or a rule to set accept/reject."""
    if suggestions is None or suggestions.empty:
        return pd.DataFrame(columns=["suggestion_id", "row", "field", "issue",
                                     "suggested_value", "decision", "decided_by", "note"])
    d = suggestions.reset_index(drop=True).copy()
    d["suggestion_id"] = d.index
    return pd.DataFrame({
        "suggestion_id": d["suggestion_id"],
        "row": d.get("row"), "field": d.get("field"), "issue": d.get("issue"),
        "suggested_value": d.get("suggested_value"),
        "decision": HOLD, "decided_by": "", "note": "",
    })


def decide_by_rule(decisions: pd.DataFrame, suggestions: pd.DataFrame, *,
                   accept_issues=None, accept_confidence=None,
                   reject_issues=None, decided_by="rule") -> pd.DataFrame:
    """Set decisions from a rule instead of by hand. Accept suggestions whose
    issue is in accept_issues or whose confidence is in accept_confidence; reject
    those whose issue is in reject_issues. Everything else stays as it was.
    Conservative: a rule can only move a HOLD, never overturn a human decision."""
    d = decisions.copy()
    s = suggestions.reset_index(drop=True)
    accept_issues = set(accept_issues or [])
    accept_confidence = set(accept_confidence or [])
    reject_issues = set(reject_issues or [])
    for i in d.index:
        if d.at[i, "decision"] != HOLD:
            continue
        sid = d.at[i, "suggestion_id"]
        issue = s.at[sid, "issue"] if sid in s.index else d.at[i, "issue"]
        conf = s.at[sid, "confidence"] if (sid in s.index and "confidence" in s.columns) else ""
        if issue in reject_issues:
            d.at[i, "decision"], d.at[i, "decided_by"] = REJECT, decided_by
        elif issue in accept_issues or conf in accept_confidence:
            d.at[i, "decision"], d.at[i, "decided_by"] = ACCEPT, decided_by
    return d


def apply_decisions(std: pd.DataFrame, suggestions: pd.DataFrame,
                    decisions: pd.DataFrame) -> tuple:
    """Apply the accepted suggestions to a copy of std, preserving originals in
    shadow columns. Returns (final_cleaned, decision_ledger). Only single-field
    suggestions with a concrete suggested value are applied; multi-field or
    descriptive suggestions (recode, review) are recorded as accepted-but-manual."""
    cleaned = std.copy()
    s = suggestions.reset_index(drop=True)
    ledger = []
    accepted = decisions[decisions["decision"] == ACCEPT]
    for _, dec in accepted.iterrows():
        sid = dec["suggestion_id"]
        if sid not in s.index:
            continue
        row = s.at[sid, "row"]
        field = s.at[sid, "field"]
        val = s.at[sid, "suggested_value"]
        applied = False
        # apply only when the field is a real single column and the value is a
        # concrete replacement (not a descriptive "recode: ..." instruction)
        concrete = (field in cleaned.columns and row in cleaned.index
                    and isinstance(val, (str, int, float, np.integer, np.floating))
                    and not (isinstance(val, str) and (val.startswith("(") or "|" in field
                                                       or "recode" in val or "review" in val
                                                       or "verify" in val or "add " in val)))
        before = cleaned.at[row, field] if (field in cleaned.columns and row in cleaned.index) else None
        if concrete:
            shadow = f"{field}__original"
            if shadow not in cleaned.columns:
                cleaned[shadow] = cleaned[field]
            cleaned.at[row, field] = val
            applied = True
        ledger.append({
            "suggestion_id": sid, "row": row, "field": field,
            "issue": s.at[sid, "issue"] if "issue" in s.columns else "",
            "before": before, "after": val if applied else before,
            "rule": s.at[sid, "fix_rule"] if "fix_rule" in s.columns else "",
            "applied": applied,
            "status": "applied" if applied else "accepted_manual_action_required",
            "decided_by": dec.get("decided_by", ""),
        })
    led = pd.DataFrame(ledger)
    n_applied = int(led["applied"].sum()) if not led.empty else 0
    led.attrs["note"] = (
        f"{len(accepted)} suggestions accepted; {n_applied} applied automatically "
        f"(concrete single-field replacements), the rest flagged as accepted but "
        f"needing manual action (recodes, multi-field, or additive fixes). Originals "
        f"preserved in shadow columns.")
    return cleaned, led


def decision_summary(decisions: pd.DataFrame) -> pd.DataFrame:
    """Counts by decision and issue, the reviewer's progress view."""
    if decisions is None or decisions.empty:
        return pd.DataFrame(columns=["issue", "accept", "reject", "hold"])
    g = (decisions.groupby(["issue", "decision"]).size().unstack(fill_value=0)
         .reset_index())
    for c in (ACCEPT, REJECT, HOLD):
        if c not in g.columns:
            g[c] = 0
    return g[["issue", ACCEPT, REJECT, HOLD]]
