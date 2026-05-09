"""Partner-voice + button-label linter.

PROMPTS.md Phase 7 / Prompts 92 + 93. Two layers:

* ``audit_string(s)`` — flags generic SaaS-speak phrases that
  violate the partner voice (e.g. "Loading…", "Click here",
  "Pick a fixture").
* ``audit_button_label(s)`` — flags labels that don't follow the
  verb-noun pattern (e.g. "RUN", "GENERATE" by themselves).

Returns a list of ``Issue`` dicts with ``rule`` and ``message``
keys. An empty list means the string is clean.

This is a forward-looking lint, not a 100% accurate parser. The
test suite uses it as a *spot-check*; final voice is judged by
humans. The acceptance bar from PROMPTS.md says "sample 30 random
strings post-change; >25 read in the partner voice" — this linter
catches the obvious failures cheaply.
"""
from __future__ import annotations

import re


# Phrases that consistently read as generic SaaS-speak. A match is
# a flag, not a hard error — caller decides.
_SAAS_PHRASES: list[tuple[str, str]] = [
    (r"\bclick here\b",
     'replace "click here" with a labelled link target'),
    (r"\bawesome\b|\bamazing\b",
     'avoid generic intensifiers'),
    (r"\bloading(?:\.{2,}|…)",
     'replace "Loading…" with a specific action ("Running Monte Carlo…")'),
    (r"\bpick a fixture\b",
     'fixture is internal vocab; say "pick a deal"'),
    (r"\bccd fixture\b",
     'CCD is internal vocab; say "claims dataset"'),
    (r"\bphase\s+[0-9]+\b",
     'Phase N is internal vocab; use the user-facing module name'),
    (r"\btrain fraction\b",
     'Train Fraction is internal vocab; say "training split"'),
    (r"\bsimulation paths\b",
     'Simulation Paths is internal vocab; say "Number of simulations"'),
    (r"\b13-step orchestrator\b",
     '13-step orchestrator is internal vocab; say "Diligence pipeline"'),
]


# Known-good verb-noun button-label fragments. A label that matches
# these (case-insensitive) at the start passes the verb-noun rule.
_VERB_NOUN_PREFIXES = [
    "run", "render", "assemble", "generate", "find",
    "audit", "compute", "compare", "open", "save",
    "browse", "screen", "review", "share",
    # Compound verbs are fine too.
    "add a", "add an", "go to", "read",
]


# P94: number-format compliance patterns. CLAUDE.md says:
#   money       → 2dp ($450.25M, never 1 or 3)
#   percent     → 1dp (15.3%)
#   multiples   → 2dp (2.50x)
#
# Below: regex patterns that flag rendered output violating those
# rules. The audit consumes already-rendered HTML/text strings, not
# Python source — so it's safe to run on a server response.

_NUMBER_VIOLATIONS: list[tuple[str, str]] = [
    # $X (no decimals) and $X.X (one decimal) — money should be 2dp.
    # Match a $-prefixed integer or one-decimal value followed by
    # M/B/k/no suffix or whitespace, NOT followed by another digit.
    (r"\$\d+(?:\.\d)?(?=[MBk\s,]|$)",
     'money values should render with 2 decimal places (e.g. $450.25M)'),
    # Percent without a decimal — except for "0%" which is fine.
    (r"\b\d+%(?:[^.\d])",
     'percent values should render with 1 decimal place (e.g. 15.3%)'),
    # Multiples like "2.5x" / "2x" — should be 2dp. The negative
    # lookbehinds prevent matching inside a longer number ("2.80x"
    # contains "80x" starting at a word-boundary).
    (r"(?<!\d)(?<!\.)\d+(?:\.\d)?x\b",
     'multiples should render with 2 decimal places (e.g. 2.80x)'),
]


def audit_number_format(s: str) -> list[dict]:
    """Flag rendered numbers that violate the format-compliance rules.

    Caller passes the output of a render function; the audit
    catches rendered "$450M" / "9%" / "2.8x" — none of which the
    kit's ``format_value`` would produce.

    Returns a list of issues. Empty list = clean.
    """
    if not s:
        return []
    issues = []
    import re
    for pattern, message in _NUMBER_VIOLATIONS:
        for m in re.finditer(pattern, s):
            issues.append({
                "rule": "number-format",
                "message": message,
                "match": m.group(0),
            })
    return issues


def audit_string(s: str) -> list[dict]:
    """Run the voice audit on a single user-facing string."""
    issues: list[dict] = []
    if not s:
        return issues
    lower = s.lower()
    for pattern, message in _SAAS_PHRASES:
        if re.search(pattern, lower):
            issues.append({"rule": "saas-phrase", "message": message})
    return issues


def audit_button_label(label: str) -> list[dict]:
    """Flag button labels that don't follow verb-noun (e.g. "RUN"
    by itself or "Submit" without an object)."""
    issues: list[dict] = []
    if not label:
        return [{"rule": "empty-label",
                 "message": "button label must not be empty"}]
    # Strip leading/trailing decoration like "↗", arrows, ellipsis.
    stripped = re.sub(
        r"[^A-Za-z0-9 ]+", "",
        label,
    ).strip().lower()
    if not stripped:
        return [{"rule": "decoration-only",
                 "message": "label is decoration-only (no verb-noun)"}]
    # One-word labels are usually a verb without an object.
    if " " not in stripped:
        # Allow "Submit" / "Save" only when ambiguous-target; flag
        # the common one-word offenders.
        if stripped in (
            "run", "compute", "generate", "render",
            "audit", "go", "load", "submit",
        ):
            issues.append({
                "rule": "one-word-verb",
                "message": (
                    f'"{label}" is a bare verb; use verb-noun '
                    f'("Run Monte Carlo", "Render memo")'
                ),
            })
        return issues
    # Check the first word is a recognised verb prefix.
    for prefix in _VERB_NOUN_PREFIXES:
        if stripped.startswith(prefix):
            return issues
    # Otherwise fall through with a soft flag.
    issues.append({
        "rule": "non-verb-prefix",
        "message": (
            f'"{label}" does not start with a recognised verb '
            f'(run/render/assemble/generate/find/audit/...)'
        ),
    })
    return issues
