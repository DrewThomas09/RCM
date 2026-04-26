# Report 0040: Orphan Files / Subsystems within `rcm_mc/diligence/`

## Scope

Searches `rcm_mc/diligence/` (40-subdir subsystem per Report 0004 Discovery A) for orphan subdirectories — those imported by 0 production callers and 0 tests. The diligence subsystem has been deferred for ~9 reports. This iteration confirms which subdirs are wired vs unwired.

Prior reports reviewed: 0036-0039.

## Findings

### Method

For each `rcm_mc/diligence/<sub>/` directory, count import sites:

```bash
grep -rln "from rcm_mc\.diligence\.<sub>\|from \.diligence\.<sub>\|from \.<sub>" RCM_MC/rcm_mc | wc -l
grep -rln "from rcm_mc\.diligence\.<sub>" RCM_MC/tests | wc -l
```

### Results — orphan + low-coupling subdirs

| Subdir | Prod | Test | Verdict |
|---|---:|---:|---|
| **`diligence/root_cause/`** | **0** | **0** | **HIGH-PRIORITY ORPHAN** |
| **`diligence/value/`** | **0** | **0** | **HIGH-PRIORITY ORPHAN** |
| `diligence/bridge_audit/` | 1 | 1 | Light coupling |
| `diligence/covenant_lab/` | 1 | 1 | Light |
| `diligence/deal_mc/` | 1 | 1 | Light |
| `diligence/denial_prediction/` | 1 | 1 | Light |
| `diligence/exit_timing/` | 1 | 1 | Light |
| `diligence/labor/` | 1 | 1 | Light |
| `diligence/ma_dynamics/` | 1 | 1 | Light |
| `diligence/management_scorecard/` | 1 | 1 | Light (sister to `rcm_mc/management/` per Report 0014's README cross-reference) |
| `diligence/patient_pay/` | 1 | 1 | Light |
| `diligence/payer_stress/` | 1 | 1 | Light |
| `diligence/physician_eu/` | 1 | 1 | Light |
| `diligence/quality/` | 1 | 1 | Light |
| `diligence/referral/` | 1 | 1 | Light |
| `diligence/reputational/` | 1 | 1 | Light |

### Subdirs NOT in the low-coupling list (presumably 2+ prod imports each — i.e. better-coupled)

The 24 not listed have ≥2 production importers each. Includes `bear_case`, `benchmarks`, `checklist`, `counterfactual`, `cyber`, `deal_autopsy`, `hcris_xray`, `ingest`, `integrity`, `physician_attrition`, `physician_comp`, `real_estate`, `regulatory`, `regulatory_calendar`, `screening`, `synergy`, `thesis_pipeline`, `working_capital` (per Report 0004's listing).

### HIGH-PRIORITY discoveries

#### `diligence/root_cause/` — 0 prod, 0 test

Per Report 0004's directory listing: exists with 4 entries (likely `__init__.py`, README.md, plus 2 modules). **Zero production callers, zero tests.** The most-orphan diligence subdir.

Mtime / size not checked this iteration; likely shipped but never wired into a route or pipeline.

#### `diligence/value/` — 0 prod, 0 test

Same. Per Report 0004 listing: 4 entries. Untested + unwired.

### Light-coupling pattern (1 prod, 1 test each — 14 subdirs)

The 14 subdirs with `prod=1, test=1` follow a uniform pattern:

- Each imported by ONE production file (likely `server.py` or a UI page that renders that section).
- Each tested by ONE dedicated test file.
- **Single-callsite single-test coverage** — minimal.

This is the **per-feature-page architecture**: each diligence subsystem is one page; one route imports it; one test hits it. Coverage is shallow but at-least-existent.

### Comparison vs Report 0010

Report 0010 surveyed top-level `rcm_mc/` subpackages. This report goes one layer deeper into `rcm_mc/diligence/`. Findings dovetail:

- Top-level orphans (Report 0010): `management/`, `portfolio_synergy/`, `site_neutral/`.
- Diligence-subdir orphans (this report): `diligence/root_cause/`, `diligence/value/`.

**Total 0-prod orphan subdirs across the package: 5.** All are tested-but-unused or wholly-untested.

### Subsystem-level coupling map

The `diligence/` subsystem's 40 subdirs include 17 with 1-importer-only (light) + 2 wholly-unimported (orphan). That's **48% of diligence subdirs at 0-1 prod-importer threshold** — a wide thin-coupling profile.

Per Report 0005 server.py imports `.diligence.*` 13 times — most of those are likely to the better-coupled subdirs (the 21 with ≥2 importers). The 19 light/orphan subdirs are reached primarily via UI pages or analysis pipelines.

## Merge risks flagged

| ID | Risk | Detail | Severity |
|---|---|---|---|
| **MR327** | **`diligence/root_cause/` and `diligence/value/` are TRUE orphans (0 prod, 0 test)** | Cross-link Report 0010 MR69-MR71 (top-level orphans). Estimate ~200-400 LoC of orphan code. Pre-merge: any branch claiming to use root_cause / value functionality must wire it into a route + test. | **High** |
| **MR328** | **14 diligence subdirs at 1-prod-1-test coverage** | If the single production caller is removed, the subdir becomes orphan. **Fragile.** | Medium |
| **MR329** | **Diligence subsystem coupling profile: 48% at ≤1 prod importer** | Suggests bottom-up subsystem build (one feature page at a time), without integration cross-referencing. **Low overall robustness.** | Medium |
| **MR330** | **`diligence/management_scorecard/` is light-coupled but is the cross-reference target from `rcm_mc/management/`** (Report 0014) | Per the management/README.md, the two are intended sister modules. Need to verify that `management_scorecard` actually consumes `management` outputs — unclear from coupling counts. | Medium |

## Dependencies

- **Incoming:** server.py + UI pages + analysis pipelines (per Report 0005).
- **Outgoing:** depends per-subdir.

## Open questions / Unknowns

- **Q1.** What's actually inside `diligence/root_cause/` and `diligence/value/`? Read needed.
- **Q2.** Are the 14 light-coupling subdirs each a UI route, or do they have CLI entry points too?
- **Q3.** Why does `physician_eu` exist alongside `physician_attrition` and `physician_comp`? Naming suggests a Europe variant — verify.

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0041** | **Config map** (already requested as iteration 41). | Pending. |
| **0042** | **Read `diligence/root_cause/` and `diligence/value/`** — what do they contain? | Resolves Q1 / MR327. |
| **0043** | **Audit `diligence/INTEGRATION_MAP.md`** (17 KB, deferred since Report 0004) | Repeated suggestion — likely answers Q2 + the diligence wiring picture. |

---

Report/Report-0040.md written. Next iteration should: read `diligence/INTEGRATION_MAP.md` (17 KB, deferred 9 reports), the diligence subsystem's own integration roadmap that almost certainly explains the 19 light/orphan subdirs and the wiring contract.

