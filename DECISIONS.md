# DECISIONS — CDD Analytics Expansion (session claude/pedesk-cdd-analytics-cvzvgf)

Architectural and routing decisions for the CDD analytics build. Append-only.
The pre-existing app decision log lives at `RCM_MC/DECISIONS.md`; this file
tracks decisions made during this session only.

## [2026-06-14 01:25] SESSION — CDD package location and shared foundation
Context: New CDD analytics features need a home that does not entangle with the
large existing rcm_mc surface, while still being wired into the app.
Options: A) scatter modules across existing analytics/ml dirs; B) one cohesive
`rcm_mc/cdd/` subpackage with a shared Exhibit contract and a registry the
server and CLI consume.
Decision: B. New code lives in `rcm_mc/cdd/`. Each feature is a module exposing
a pure compute function returning an `Exhibit`. A `registry` maps feature ids to
builders so the CLI (`rcm-mc cdd ...`) and server can enumerate and run them.
Rationale: keeps golden tests hermetic, satisfies "no orphan modules" by routing
every feature through one registered surface, and isolates from the 2,878-test
existing suite.
Reconciliation/Validation: `tests/golden/test_registry.py` asserts every
feature id in feature_list.json resolves to a registered builder.

## [2026-06-14 01:25] SESSION — Exhibit metadata + audience separation in code
Context: Part 4 requires sourced footnotes, em-dash-free copy, and audience
separation enforced in code, not convention.
Options: A) rely on existing HTML chart_kit source strings; B) a typed Exhibit
dataclass carrying machine-readable footnotes (source, vintage, assumptions),
audience gating, and a copy linter.
Decision: B. `rcm_mc/cdd/exhibit.py` defines `Exhibit`, `Footnote`,
`AssumptionNode`. `Exhibit.render(internal_mode=False)` strips assumption nodes
and internal-only series for partner output. A `lint_copy` helper rejects
em-dashes and AI filler in any user-facing string.
Rationale: makes Part 4 constraints testable rather than aspirational.
Reconciliation/Validation: `test_two_audience.py` asserts partner render omits
assumption nodes; `test_chartpack_standards.py` asserts footnote metadata and
em-dash-free labels on every exhibit.

## [2026-06-14 01:25] SESSION — Statistical-only inference, seeds pinned
Context: Part 4 hard constraint: no LLM on any prediction path; determinism.
Decision: All CDD estimators use numpy / scipy / scikit-learn / lifelines /
ruptures only. Every stochastic path takes `seed` and uses
`np.random.default_rng(seed)`. No `np.random.*` global state.
Rationale: reproducibility to 1e-9 and auditability.
Reconciliation/Validation: reproducibility assertions in Monte Carlo and
conformal golden tests.
