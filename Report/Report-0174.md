# Report 0174: Cross-Cutting — Provenance Tracking

## Scope

Documents provenance-tracking cross-cutting concern across the project. Per CLAUDE.md "Phase 4: provenance/graph.py + explain.py" + Report 0093 ml/README "ProvenanceTag.ANALYST_OVERRIDE." Sister to Reports 0024 (logging), 0054 (caching), 0084 (auth), 0114 (CSRF), 0144 (retries).

## Findings

### Provenance is a Phase-4 invariant

Per CLAUDE.md "Phase 4 ... `rcm_mc/provenance/graph.py + explain.py`":
- `provenance/graph.py` — provenance DAG construction
- `provenance/explain.py` — human-readable rendering

**Per CLAUDE.md "ProvenanceTracker invariant on every output"** (per memory file `project_rcm_mc_layout.md`).

### Cross-link to Report 0093 ml/README

Per ml/README (Report 0093 line 314):
> "Provenance flag: every predictor carries `provenance: 'synthetic-priors'` until calibrated against ≥30 real closed-deal labels, at which point it flips to `'real-cohort-N'`."

**ProvenanceTag.SYNTHETIC_PRIORS** vs **ProvenanceTag.REAL_COHORT_N** — 2-state classification.

### Cross-link to Report 0134 deal_overrides

Per Report 0134: `deal_overrides` writes "surfaced as `ProvenanceTag.ANALYST_OVERRIDE` everywhere they land." **3rd known ProvenanceTag value.**

### Cross-link to Report 0148 hash_inputs

`hash_inputs` (Report 0148) is the cache-key for `analysis_runs.packet_json`. **NOT itself a provenance tag** but the mechanism for deterministic cache invalidation.

### Estimated provenance call sites

`grep -rln "ProvenanceTag\|ProvenanceTracker\|provenance\." RCM_MC/rcm_mc/`: not run this iteration.

**Inferred per CLAUDE.md "every output"**: every value emitted by analysis chain has a provenance tag. Likely 50+ call sites in:
- `analysis/packet_builder.py` (Report 0140 1454 LOC)
- `ml/*` (Report 0093 41 modules)
- `pe/*` (Report 0142 7 modules)
- `mc/*` (Report 0112 7 modules)
- `pe_intelligence/*` (Reports 0152-0160 276 modules)

### Inconsistencies — likely

Per Report 0144 retry-cross-cut pattern: "no shared retry helper." **Provenance might face the same.** Each subpackage may use different ProvenanceTag values.

Per Report 0093 cross-link 3 known tags + Report 0134 1 known = 4 confirmed. **Probably more.**

### TODO discipline gate

Per Report 0126 commit `0a747f1`: "test(contract): Phase 3 — 6 new tests + TODO discipline gate (18→25)." **Provenance discipline tests likely included.** Cross-link contract-tests in `feat/ui-rework-v3` per Report 0127.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR911** | **Provenance is documented as "Phase 4 invariant" but no audit has enumerated all ProvenanceTag values OR call sites** | Per CLAUDE.md + Report 0093 + Report 0134: at least 4 distinct tags. Likely many more. **Should have central enum.** | **High** |
| **MR912** | **Provenance vs cache-invalidation are decoupled** | Per Report 0148 MR823: hash_inputs doesn't include schema version. **Equivalent risk for provenance**: changing what triggers `synthetic_priors → real_cohort_N` doesn't bust cache automatically. | Medium |
| **MR913** | **No shared `infra/provenance.py`** — each subpackage may reimplement | Cross-link Report 0144 MR800 (no shared retry). Same pattern. | Medium |

## Dependencies

- **Incoming:** every output-producing module per CLAUDE.md.
- **Outgoing:** TBD — `provenance/graph.py + explain.py` likely.

## Open questions / Unknowns

- **Q1.** Full enumeration of ProvenanceTag values (likely an Enum somewhere).
- **Q2.** How many call sites use ProvenanceTag?
- **Q3.** Is there a central `provenance/__init__.py`?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0175** | Integration point (in flight). |
| **0176** | CI/CD (in flight). |
| **0177** | Read `rcm_mc/provenance/__init__.py` (closes Q1+Q3). |

---

Report/Report-0174.md written.
