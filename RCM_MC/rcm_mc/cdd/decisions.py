"""BOLSTER-06 DECISIONS.md routing pattern.

Wires the uncertainty-routing pattern: any non-default modeling or data choice is
logged in DECISIONS.md with the options considered, the choice made, the
rationale, and how it is validated. This module parses that log, exposes which
features are covered, appends new entries in the canonical format, and flags any
feature that made a non-default choice but lacks a decision entry.

Statistical and deterministic. No LLM on any path.
"""
from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Dict, List, Optional

from .exhibit import Exhibit, Flag, Footnote, Reconciliation, Series
from .registry import CddFeature, register

FEATURE_ID = "BOLSTER-06"

_FEATURE_ID_RE = re.compile(r"\b((?:NEW|BOLSTER)-\d+)\b")
_HEADER_RE = re.compile(r"^##\s+", re.MULTILINE)

# Non-default choices made this session. Each must have a DECISIONS.md entry.
NON_DEFAULT_CHOICES: Dict[str, str] = {
    "NEW-01": "SOM is capacity times win rate, not a flat percentage of TAM",
    "NEW-02": "symmetric Bennet decomposition for additivity and reversal-consistency",
    "NEW-04": "reimbursement bases are labeled separately and never blended",
    "NEW-05": "small-cohort reliability threshold set at 30 members",
    "NEW-11": "default Monte Carlo model is base times one plus the sum of shocks",
    "NEW-13": "FFS correction weight is one over one minus MA penetration",
    "BOLSTER-01": "StandardScaler pipeline and exchangeable design for conformal coverage",
    "BOLSTER-03": "BIC-style default changepoint penalty with robust sigma",
}


def _repo_root() -> str:
    # rcm_mc/cdd/decisions.py -> RCM_MC -> repo root
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(os.path.dirname(os.path.dirname(here)))


def default_decisions_path() -> str:
    return os.path.join(_repo_root(), "DECISIONS.md")


def covered_features(path: Optional[str] = None) -> Dict[str, int]:
    """Return feature ids that appear in a DECISIONS.md header, with a count."""
    path = path or default_decisions_path()
    if not os.path.exists(path):
        return {}
    text = open(path, encoding="utf-8").read()
    counts: Dict[str, int] = {}
    for block in _HEADER_RE.split(text):
        # only inspect the header line of each block (first line)
        header = block.splitlines()[0] if block.splitlines() else ""
        for fid in _FEATURE_ID_RE.findall(header):
            counts[fid] = counts.get(fid, 0) + 1
    return counts


def missing_decisions(path: Optional[str] = None,
                      choices: Optional[Dict[str, str]] = None) -> List[str]:
    """Feature ids that made a non-default choice but have no decision entry."""
    choices = choices if choices is not None else NON_DEFAULT_CHOICES
    covered = covered_features(path)
    return sorted(fid for fid in choices if fid not in covered)


def append_decision(feature_id: str, title: str, *, context: str, options: str,
                    decision: str, rationale: str, validation: str,
                    path: Optional[str] = None, now: Optional[datetime] = None) -> str:
    """Append a canonical decision entry to DECISIONS.md and return the entry."""
    path = path or default_decisions_path()
    ts = (now or datetime.utcnow()).strftime("%Y-%m-%d %H:%M")
    entry = (
        f"\n## [{ts}] {feature_id} {title}\n"
        f"Context: {context}\n"
        f"Options: {options}\n"
        f"Decision: {decision}\n"
        f"Rationale: {rationale}\n"
        f"Reconciliation/Validation: {validation}\n"
    )
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(entry)
    return entry


def _demo() -> Exhibit:
    covered = covered_features()
    missing = missing_decisions()
    flags: List[Flag] = []
    if missing:
        flags.append(Flag(
            code="decisions_missing",
            severity="warn",
            message=f"{len(missing)} non-default choice(s) lack a decision entry: {', '.join(missing)}.",
        ))
    reconciliations = [
        Reconciliation(identity="every non-default choice has a decision entry",
                       lhs=1.0 if not missing else 0.0, rhs=1.0, tolerance=1e-9),
    ]
    series = [
        Series(name="Decisions logged by feature", kind="bar",
               points=[{"label": k, "value": v} for k, v in sorted(covered.items())]),
        Series(name="Missing decision entries", kind="bar", internal_only=True,
               points=[{"label": m, "value": 1} for m in missing]),
    ]
    footnote = Footnote(
        source="DECISIONS.md",
        vintage=datetime.utcnow().strftime("%Y-%m-%d"),
        assumptions=[
            "Coverage is parsed from DECISIONS.md headers.",
            "A non-default choice without a decision entry is flagged.",
        ],
    )
    return Exhibit(
        feature_id=FEATURE_ID,
        title="Decision-log routing coverage",
        audience="internal",
        series=series,
        footnote=footnote,
        flags=flags,
        reconciliations=reconciliations,
        summary=f"{len(covered)} feature(s) with decision entries, {len(missing)} missing.",
        meta={"covered": covered, "missing": missing},
    ).validate()


register(
    CddFeature(
        feature_id=FEATURE_ID,
        title="DECISIONS.md routing pattern",
        audience="internal",
        demo=_demo,
    )
)
