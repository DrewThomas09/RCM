"""Final consistency sweep — checks rendered HTML against the
canonical Phase 1-7 contract.

PROMPTS.md Phase 7 / Prompt 100. The acceptance bar from the spec:

    A compliance-scan test walks every route, applies every check,
    prints a per-route compliance score. Target: median ≥ 95%.

This module ships the rule registry and the per-render scorer.
The actual whole-route walk is in ``test_compliance_sweep.py`` —
it spins up a server and grades a sampled set of routes. As pages
migrate (Phase 3 sweeps), per-route scores will rise; for now the
test enforces a ≥ 60% per-route bar to detect catastrophic
regressions without blocking incremental migrations.
"""
from __future__ import annotations

from typing import Callable


# Each rule is (key, predicate). Predicate takes the rendered HTML
# string and returns True if the page complies.
ComplianceRule = tuple[str, str, Callable[[str], bool]]

RULES: list[ComplianceRule] = [
    (
        "has-cmd-k-palette",
        "Page exposes the cmd-K command palette (P46).",
        lambda h: 'id="ck-palette"' in h,
    ),
    (
        "has-focus-visible-rule",
        "Page CSS declares a :focus-visible outline (P96).",
        lambda h: ":focus-visible" in h,
    ),
    (
        "has-print-stylesheet",
        "Page CSS declares a @media print block (P25).",
        lambda h: "@media print" in h,
    ),
    (
        "has-motion-tokens",
        "Shared motion tokens are declared (P19).",
        lambda h: "--motion-fast" in h and "--ease-standard" in h,
    ),
    (
        "has-accent-2-token",
        "Third-accent token (--accent-2) is declared (P23).",
        lambda h: "--accent-2" in h,
    ),
    (
        "has-page-title-typography",
        "Page-title typography rule is declared (P21).",
        lambda h: ".page-title" in h or ".ck-main h1" in h,
    ),
    (
        "form-persist-js-injected",
        "Form-persist localStorage layer is injected (P10).",
        lambda h: "formPersist:" in h,
    ),
    (
        "has-data-table-css",
        "data_table() styling is shipped (P15).",
        lambda h: ".data-table" in h,
    ),
    (
        "has-kpi-strip-css",
        "kpi_strip() styling is shipped (P11).",
        lambda h: ".kpi-strip" in h,
    ),
    (
        "has-recommendation-block-css",
        "recommendation_block() styling is shipped (P16).",
        lambda h: ".recommendation-block" in h,
    ),
    (
        "has-keyboard-help",
        "Keyboard-shortcut help overlay markup present (P89).",
        lambda h: 'id="kbd-help"' in h,
    ),
    (
        "has-tour-overlay-shell",
        "Tour-overlay JS is injected (P77).",
        lambda h: "data-tour" in h,
    ),
]


def compliance_check(html: str) -> dict:
    """Run every compliance rule against ``html``. Returns a dict::

        {
          "pass":   12,
          "total":  12,
          "score":  1.0,
          "results": [{"key": ..., "label": ..., "passed": True}, ...],
        }
    """
    results = []
    n_pass = 0
    for key, label, predicate in RULES:
        try:
            ok = bool(predicate(html))
        except Exception:  # noqa: BLE001 — defensive
            ok = False
        if ok:
            n_pass += 1
        results.append({"key": key, "label": label, "passed": ok})
    return {
        "pass": n_pass,
        "total": len(RULES),
        "score": n_pass / len(RULES) if RULES else 0.0,
        "results": results,
    }
