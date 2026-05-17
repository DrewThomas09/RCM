# SESSION_STATE.md — cold-start brief for the methodology / chip-propagation workstream

**Last updated:** 2026-05-17, mid-day during B.1 design-doc work
**Last deployed commit on main:** `d974cc6b` (post A.10 PR B merge, deploy run `25997215168`)
**Purpose:** Durable snapshot of session-level decisions, operating principles, in-flight design work, and Tier-B queue. A fresh session reading only this document + the live codebase should be able to continue B.1 design-doc construction without losing context.

This document is insurance against context rot in long sessions. It does NOT replace reading the actual code or the PR descriptions of shipped work — both are authoritative. This document is the **map** to find them.

---

## 1. PRs shipped in this workstream (chronological)

| # | PR | Title (short) | What it did |
|---|---|---|---|
| 1 | [#137](https://github.com/DrewThomas09/RCM/pull/137) | A.1 — failure_reason channel + diagnostic chip for ridge predictions | Added `FailureReason` enum + `failure_reason` field on `ridge_predictor.PredictedMetric` and packet `PredictedMetric`. Added `ck_prediction_chip()` helper in `_chartis_kit.py` + CSS for 3 chip variants (gray/amber/red). Detection logic in `_predict_ridge` for `PINV_FALLBACK` / `CI_UNSTABLE` / `R2_NEGATIVE`. Audit framing was "remove silent zero-fill" but actual bug was sentinel conflation. |
| 2 | [#138](https://github.com/DrewThomas09/RCM/pull/138) | Pattern 1 — `ck_action_button` primitive, kill third-color regression | Four pages (`compare`, `counterfactual`, `denial-prediction`, `deal-autopsy`) emitted `<button>` with background `#155752` — a *third* color matching neither marketing CTA (near-black-navy) nor workbench primary (`#1F7A75` teal). Introduced `ck_action_button(text, *, type, form_target, variant="primary")` primitive routing through existing `.cad-btn .cad-btn-primary` CSS. |
| 3 | [#139](https://github.com/DrewThomas09/RCM/pull/139) | Pattern 2 — sub-nav letter-spacing 0.04em → 0.08em | One-character CSS change in `_chartis_kit.py:3326`. The sub-nav was the only nav element using both the tightest tracking in the system AND Title Case (no `text-transform`). All 9 sub-nav routes benefit uniformly. |
| 4 | [#140](https://github.com/DrewThomas09/RCM/pull/140) | A.3 — clamp `benchmark_percentile` to [0, 1] in `_merge_rcm_profile` | Defensive clamp on `_percentile` closure inside `packet_builder.py:314-320`. Audit said "n==0 + clamp"; n==0 case was already guarded at line 316. Only the clamp half was needed. |
| 5 | [#141](https://github.com/DrewThomas09/RCM/pull/141) | A.10 PR A — propagate `failure_reason` through `ProfileMetric` + add `ck_aggregate` | Foundation only: added `failure_reason: Optional[str]` field on `packet.ProfileMetric` + `to_dict`/`from_dict` back-compat. Propagated in `_merge_rcm_profile` PREDICTED branch (one line). Added `AggregatedFailure` dataclass + `ck_aggregate(*sources, labels=None)` composition primitive. Extended `ck_prediction_chip` tooltip for `contributing_sources`. Partner-visible impact: none — surfaces wired in PR B. |
| 6 | [#142](https://github.com/DrewThomas09/RCM/pull/142) | A.10 PR B — surface rollout: chip render across consumers | Wired chip into `analysis_workbench.py` (metric cell + risk-flag source + diligence-question source + JSON export), `portfolio_heatmap.py` (cell chip), `exports/packet_renderer.py` + `xlsx_renderer.py` (CSV/XLSX `failure_reason` column), `provenance/graph.py` (node metadata). Risk-flag and diligence-question chips wrap source through `ck_aggregate` with trigger-metric label so tooltip names source. |

**Also today (2026-05-17):**
- **A.7 route-normalization investigation** — closed as "no real bypass." 46 probe paths tested; Python's `http.server` normalizes leading `//x` → `/x` benignly; B152 fix at `server.py:2141` already guards exact-match comparison after `urlparse`. Auth gate is structurally sound. No PR shipped.

---

## 2. Operating principles established this workstream

These are durable across sessions. Most have been demonstrated multiple times.

### 2.1 Discipline gate — verify the named target actually behaves as claimed

When an audit / earlier PR claims `X is broken at file:line`, **verify with grep + DOM/runtime evidence before accepting the framing**. Audit findings are starting points for investigation, not file:line specs. This pattern has now caught framing errors 5+ times: silent zero-fill → sentinel conflation; `_phi_banner_html` → already-shipping editorial copy; three-mechanism PHI inventory → only one working; "remove silent zero-fill" → unreached defaults; "in-sample R²" → already LOO.

### 2.2 Surface inventories cover BOTH UI rendering AND API JSON paths

A.10 PR B's grep focused on `ui/*.py` files and missed `/api/predict/backtest` (a partner-facing JSON endpoint). Future inventories for chip / failure_reason propagation work must include both surface types — grep for UI handlers returning HTML AND API handlers returning JSON.

### 2.3 Chip belongs to the SOURCE, not the conclusion

For risk flags and diligence questions: the flag/question text stays unmodified ("HIGH denial risk", "What is causing X?"). The chip surfaces NEXT TO the source metric (the ProfileMetric the flag triggered on), wrapped through `ck_aggregate` with the trigger-metric name as the label, so the tooltip explicitly names the source ("Sources: denial_rate (pinv_fallback)") rather than ambiguous default ("Fit unstable").

### 2.4 Option-1 vs Option-2 PR review

- **Option 1** (push directly): mechanical change, no framing correction, no architectural pattern, no knowingly-left gap. CSS value tweaks, defensive guards, contract updates.
- **Option 2** (surface diff + PR description for review BEFORE push): introduces architectural pattern, corrects previously-stated framing, knowingly leaves a follow-up gap, or touches shared infrastructure. ANY of the three triggers option-2.

### 2.5 Forward-fix protocol on deploy regressions

**Clean revert** (`git revert <sha>`, push, ping with revert PR link): authorized to execute without review. Mechanical, zero design content, restores known-good state. **Any non-revert forward-fix** (re-applying with adjusted markup, swapping classes, trying a different approach): STOPS for normal draft-review even on fast paths. Stacking two review-skips (auto-merge + agent-pushes-fix-without-review) compounds risk neither does alone.

### 2.6 Investigate → propose → code (for non-mechanical PRs)

For any architectural / design-decision PR: investigation phase first (grep, DOM probes, code reads), then proposal (design doc or PR draft surfaced for review), then code only after user approval. Skip the proposal step only for option-1-mechanical work.

### 2.7 Real-time surfacing of design-doc decisions

In design-doc work, surface intermediate decisions AS THEY EMERGE, not batched at the end. Each major design choice goes to user for pushback or wave-through before the next decision crystallizes. Lead with the primary recommendation; edge cases at the end of each decision, not first.

### 2.8 Pre-merge CI gate (agent owns)

Push branch → background-poll `gh pr checks <#> --watch` → ping user when all 3 Python versions green ("safe to merge"). Never say "standing by for merge" before CI completes — user auto-merges on link drop, so implicit transfer of CI-watching to user is wrong.

### 2.9 Post-merge deploy gate (agent owns)

When user merges, poll for new `Deploy to Azure VM` workflow run (filter by databaseId != last known). Watch to completion with `--exit-status`. Report green or red within 5 min. For partner-visible PRs, DOM-verify on production after deploy green.

### 2.10 Polling design — restart-on-exit pattern

Bash tool has hard 10-min timeout. For long-window unattended polling, the agent should re-arm a fresh 10-min poll each time the previous exits without finding a target. Functionally equivalent to a continuous long poll. Logged from the dark-window incident.

### 2.11 Recurring failure mode — "incomplete migration leaves multiple primitives in parallel"

Observed in three places: shell trio (chartis_shell / editorial_chartis_shell alias / actual editorial shell), button trio (`.cta-btn` / `.cad-btn-primary` / four-page invented third color), nav visual register (topnav / sub-nav / breadcrumbs all different tracking values). When a future investigation lands in shared infrastructure, check first whether the symptom is "one broken thing" vs "multiple competing things, none canonical." If the latter, the unit-of-work is unification, not the symptom fix.

### 2.12 Premier-ML rigor vs practical-engineering rigor

Two modes for design docs. Premier-ML: every choice justified with reasoning + literature reference where applicable; bikeshed-marked sub-choices called out explicitly. Practical-engineering: defensible defaults with 2-3 sentences each. B.1 ML methodology work is premier-ML mode.

---

## 3. Chip taxonomy — current state

### Tiers (in `_FAILURE_REASON_TIER` at `_chartis_kit.py`)

| Tier | Chip variant | Visual | Meaning | Reasons (post A.10 PR B) |
|---|---|---|---|---|
| 3 | `FIT_ERROR` | red `✕ prediction failed` | "math broke, don't use this number" — chip should suppress downstream calculations (Tier B item) | `fit_exception` |
| 2 | `UNSTABLE_FIT` | amber `⚠ fit unstable` | "math ran but solver/output wobbled — treat with care" | `pinv_fallback`, `ci_unstable`, `r2_negative` |
| 1 | `INSUFFICIENT_DATA` | gray `— insufficient comparables` | "data doesn't support a prediction" | `insufficient_comparables`, `target_features_missing`, `no_benchmark` |
| 0 | (no chip) | — | clean | `None` |

**Current failure_reason count: 7.** (User's "9" in the most recent prompt is a small miscount — verified by reading `_FAILURE_REASON_TIER` directly. Worth flagging because it's exactly the kind of drift this document is designed to surface.)

### Production-rendering note (carry into every B.* PR description)

**Only Tier 2 fires from real predictor paths today.** Tier 1 and Tier 3 are wired throughout the pipeline (failure_reason field, aggregator, chip helper, surface rollout) but require the orchestrator-emit refactor to emit them on fallback / hard-failure paths. Partners see only amber chips on pedesk.app until that lands. This is a known gap, not a propagation bug.

### Coming in B.1 (per D1 + D3 locks)

- New chip variant: `DIAGNOSTIC_SUSPECT` (amber tier — same severity as `UNSTABLE_FIT`, distinct chip face). Visually: dashed amber border, flag icon (final glyph TBD via visual test — leaning `⚑`).
- New failure_reasons (6, all routing to DIAGNOSTIC_SUSPECT):
  - `small_cohort_tuned` — α tuned via CV but N < 10
  - `alpha_at_boundary` — chosen α at grid edge
  - `vif_high` — multicollinearity
  - `cook_d_high` — outlier-driven fit
  - `bp_heteroscedastic` — non-constant variance
  - `leverage_high` — observation with leverage > 2p/N
- Total post-B.1: 13 failure_reasons across 4 chip variants.

### AggregatedFailure + ck_aggregate (shipped in A.10 PR A)

```python
@dataclass
class AggregatedFailure:
    failure_reason: Optional[str] = None    # string value of worst-tier reason
    tier: int = 0                           # 0-3, max across inputs
    contributing_sources: List[str] = field(default_factory=list)  # "label (reason_key)" per non-clean input

def ck_aggregate(*sources, labels=None) -> AggregatedFailure:
    """Compose worst-tier failure_reason across N PMs. Unknown reasons
    defensively map to tier 3 (loud, not silent)."""
```

`ck_prediction_chip` accepts any object with `.failure_reason` (ridge PM / packet PM / ProfileMetric / AggregatedFailure). Tooltip is enhanced when `contributing_sources` is non-empty. Backward-compat: single-PM calls render the A.1 default tooltip unchanged.

---

## 4. BENCHMARKS.md classification — status

**Step 1 (T1/T2/T3 categorization of 39 hardcoded benchmark constants):** done in chat conversation, not yet committed as a file.

- **T1 historical anchors** (frozen on purpose, do not refresh): the entire v1 EBITDA bridge coefficient set in `pe/rcm_ebitda_bridge.py`; the sanity-range tuples in `constants.py`
- **T2 live benchmarks** (date-stamp + refresh quarterly/annually): hospital EV/EBITDA card text, covenant peer medians, blended rate peer median, rent/revenue + EBITDAR coverage industry medians, OBBBA Medicaid mix threshold (`risk_flags.py:259`), MA denial rate threshold (`risk_flags.py:357`)
- **T3 partner defaults / priors** (label as priors, not data): all ML hyperparameters (`_RIDGE_ALPHA`, `_DEFAULT_COVERAGE`, `_MIN_FOR_RIDGE`), calibration prior strengths, MC execution beta priors, all risk-flag actionability thresholds (denial > 10%, AR > 20%, etc.), MOIC/IRR tone thresholds, banker-convention covenant breach probability bars

**Step 2 (batch user-confirmation of classifications):** Batch 1 (rows 1-10) surfaced; user confirmed 9 of 10 (Row 5 `_BREACH_PROB_*` reclassified T3 with explicit "partner-asserted underwriting convention" sourcing note). Batches 2+ still queued — approximately 3 more batches of ~10 rows each.

**BENCHMARKS.md file:** NOT YET WRITTEN as a committed file. Planned to be the output of Step 2 — the locked classifications + provenance + refresh-cadence get committed when Step 2 batches all confirm.

**Tier C (refresh of T2 constants to 2026 sources):** gated on BENCHMARKS.md lock.

---

## 5. B.1 in-flight state — ridge predictor defensibility upgrade

**Scope:** `rcm_mc/ml/ridge_predictor.py` only. `rcm_predictor.py` retains hardcoded α (Tier-B follow-up if anyone wants better backtester accuracy — see filings).

### D1 — Alpha search strategy — **LOCKED**

Replace `_RIDGE_ALPHA = 1.0` (hardcoded at `ridge_predictor.py:53`) with per-fit LOO-CV α selection.

- **Grid**: `np.logspace(-3, 3, 25)` (25 log-spaced α values from 10⁻³ to 10³)
- **CV method**: leave-one-out via the closed-form hat-matrix shortcut (`e_i / (1 - H_ii)`). Cost is O(N·p²) per α — same as one ridge fit. Reference: Hastie/Tibshirani/Friedman ESL §7.10, eq 7.65; Allen 1974 for the original derivation.
- **Granularity**: per-fit (per metric per deal), not per-deal or global
- **Edge cases**:
  - N < 3 → skip CV, use α = 1.0 default, set `failure_reason = INSUFFICIENT_COMPARABLES` (existing Tier 1)
  - N ∈ [3, 10) → **Option A** (CV-chosen α, flag as `SMALL_COHORT_TUNED`, NO smoothing toward conservative α). Same principle as A.10's clip-flag-vs-silent-clamp: surface noisy answer with flag, don't silently smooth what partners can't undo
  - α at grid boundary → `ALPHA_AT_BOUNDARY` (new failure_reason, routing to DIAGNOSTIC_SUSPECT per D3)
  - Non-finite LOO scores → skip that α from candidates; if all skipped → α = 1.0 + `FIT_EXCEPTION`. **Guardrail**: only fire `ALPHA_AT_BOUNDARY` when chosen α is at boundary of the EVALUATED set AND the boundary candidate was successfully evaluated (not skipped — the boundary would be artificial if the higher-α candidate was skipped due to non-finite LOO)

### D3 — Chip taxonomy for diagnostic-suspect — **LOCKED**

Introduce new chip variant `DIAGNOSTIC_SUSPECT` (amber tier, distinct from UNSTABLE_FIT).

- Same aggregator tier (2) as UNSTABLE_FIT (both "treat with care")
- Different chip face: `.ck-pred-chip-diag` CSS class, dashed amber border, flag icon (final glyph TBD: leaning `⚑`)
- Routes the 6 new B.1 failure_reasons (`small_cohort_tuned`, `alpha_at_boundary`, `vif_high`, `cook_d_high`, `bp_heteroscedastic`, `leverage_high`)
- AggregatedFailure when both UNSTABLE_FIT and DIAGNOSTIC_SUSPECT reasons fire on same source: first-seen wins for chip face; tooltip lists both via contributing_sources (existing behavior, no new logic)

### D2 — Diagnostics method — **PENDING** (next to surface)

Will define exactly which diagnostics fire which failure_reason, with thresholds and edge cases:
- max leverage (h_ii > 2p/N)
- Cook's D top-3 (D_i > 4/N)
- Breusch-Pagan p-value (p < 0.05)
- max VIF (VIF > 10)
- residuals-vs-fitted summary stat
- multi-diagnostic state composition rule

### D4 — R² rendering — **PENDING**

Notable: R² is **already LOO** in both `ridge_predictor.py:304` and `rcm_predictor.py:342` (confirmed by reading, contradicting the yesterday-audit's "almost certainly in-sample" claim). The migration question of "in-sample → LOO partner perception shift" does NOT apply.

Real D4 question: with tuned α (per D1), the LOO R² distribution will shift (likely improve). Should the UI surface a "previous α=1.0 baseline" alongside the new tuned value for the first few deploys, or is that too noisy?

### D5 — Test plan — **PENDING**

Unit tests for: alpha-grid search on synthetic data with known optimal α; each diagnostic with synthetic data of known VIF / Cook's D / BP; chip variant routing per failure_reason; aggregator behavior with multi-diagnostic firing.

Integration: synthetic deal with known characteristics that should fire each diagnostic; render workbench HTML; grep DOM for correct chip variants.

### D6 — Migration plan — **PENDING**

15 production readers of `PredictedMetric.r_squared / ci_low / ci_high`. Specifically: `packet_builder.py:357-359` quality categorization (`"high" if pm.r_squared >= 0.5 else "medium" if >= 0.2 else "low"`) may need recalibration once tuned-α LOO R² distribution shifts upward.

---

## 6. Tier-B queue — DO NOT LOSE

Each item below is a future PR or investigation, filed during this session with explicit rationale. All deferred from in-flight work, not "nice to have" inventions.

| # | Item | Source | Scope |
|---|---|---|---|
| 1 | **B.1.5** — rcm_predictor CI methodology | Discovered during B.1 scope-narrowing (rcm_predictor uses in-sample residual stddev × 1.28σ at line 344-347, explicitly admitted in comment as "not LOO; cheaper") | Decide between conformal vs LOO bootstrap vs jackknife+ vs parametric; own design doc |
| 2 | **Predictor-contract-cleanup** — `r_squared` semantic mismatch | Discovered during B.1 verification (rcm_predictor.py:311 stores `1 - sd/abs(val)` under field name `r_squared` for weighted_median path — different metric, same name) | Either rename to `cv_proxy` / `dispersion_score` OR compute real LOO R² for weighted_median path. Either is non-trivial; silent fix would shift partner perception |
| 3 | **A.10 PR C-1** — MarginPrediction failure_reason retrofit + 2 surfaces | Discovered during A.10 PR B scope correction | `MarginPrediction` class retrofit (field + propagation) + chip wire-up on `ml_insights_page.py` + `thesis_card.py`. Same pattern as A.1 + A.10 PR A |
| 4 | **A.10 PR C-2** — CalibrationResult failure_reason retrofit + 1 surface | Same source as C-1 | Bayesian `CalibrationResult` class retrofit + chip wire-up on `data_room_page.py`. Separate PR from C-1 because different prediction class with different predictor |
| 5 | **A.10 PR D** — `/api/predict/backtest` JSON response failure_reason wire-up | Discovered during γ investigation today (server.py:10794 endpoint missed by PR B grep) | Add `failure_reason` to the JSON response so any client consuming the API can render chips. Same shape as analysis_workbench JSON export wire-up |
| 6 | **Orchestrator-emit refactor** — wire Tier 1 + Tier 3 chips to fire | Deferred from A.1 | The chip pipeline supports all 3 tiers but only Tier 2 fires from real predictor paths. Tier 1 needs orchestrator to emit `INSUFFICIENT_COMPARABLES` on fallback paths; Tier 3 needs orchestrator to emit `FIT_EXCEPTION` on hard-failure paths + downstream-suppression of dependent calculations |
| 7 | **Numeric defaults refactor** — `0.0 → Optional[float]` | Deferred from A.1 | `PredictedMetric.r_squared / ci_low / ci_high` defaults are `0.0` — used as "method N/A" sentinel by weighted_median + benchmark_fallback. Sentinel resolved by failure_reason channel; numeric default cleanup is a separate logical change with ~15-file blast radius |
| 8 | **Principled CI-stability metric** — replace `_CI_UNSTABLE_REL_WIDTH = 2.0` rule of thumb | Deferred from A.1 | The 200%-relative-CI-width threshold over-fires when point estimate is near zero. Replace with normalized stability metric (CV against per-metric baseline, or CI half-width / pooled residual SE) |
| 9 | **Q4.2 escape-hatch fix** | Discovered during A.2 investigation | `UI_V2_ENABLED = True` hardcoded in `_chartis_kit.py:38` bypasses the `?ui=v2` redirect-opt-out. Negative-test `test_q4_2_legacy_dashboard_does_not_redirect` would fail. Escape hatch was load-bearing per UI_REWORK_PLAN.md |
| 10 | **`editorial_chartis_shell` alias fix** | Discovered during A.2 | Alias at `_chartis_kit.py:4558` points at unified shell, not the actual editorial shell. Pages calling `editorial_chartis_shell()` expecting editorial-only features (PHI banner, sidebar, etc.) get no-op behavior |
| 11 | **Orphan `_phi_banner_html` tests** | Discovered during A.2 | `test_web_production_readiness.py` + `test_security_hardening.py` assert behavior of `_phi_banner_html` function with copy ("no PHI permitted") that doesn't exist in active codebase. These are part of the 120 pre-existing test failures |
| 12 | **Design unification sweep — meta-ticket** | Logged from Pattern 1 reasoning + reinforced through A.2 / A.10 work | Three "incomplete migration zones" exist: shell trio (chartis_shell / editorial_chartis_shell alias / actual editorial) / button trio (`.cta-btn` / `.cad-btn-primary` / retired four-page invented color) / nav visual register (topnav / sub-nav / breadcrumbs all different tracking). A coordinated design pass resolves all three together more efficiently than chasing each separately. Scoped post-methodology work |
| 13 | **A.2 PHI footer on authenticated pages** | Discovered during A.2 investigation, parked by user | DOM verification proved partners on authenticated pages see NO PHI compliance signal at all. F2 copy/visibility/position decisions already locked. Parked until methodology stack is sound |
| 14 | **A.4 cost-of-capital %/decimal toggle** | From original audit | Real footgun (silent coercion of `0.5` → `0.5%`) but bounded blast radius (one input field). Deferred for higher-leverage methodology work |

---

## 7. Frozen by design — DO NOT TOUCH

| Item | Why frozen |
|---|---|
| **v1 EBITDA bridge** (`pe/rcm_ebitda_bridge.py`) | 29 regression tests lock every lever coefficient to the published research bands. Module docstring lines 12-18 explicitly state retention. Use `value_bridge_v2` for new work |
| **Four gold-standard reference pages**: `/qoe-memo`, `/provider-economics`, `/ingest`, `/lp-update` | Reference patterns for `chartis_shell + ck_page_title` everywhere else. Compare other pages against these; never modify these |
| **T1 historical anchors in BENCHMARKS.md** | Dated on purpose. Updating to "current market" would corrupt the analytical model |
| **`rcm_predictor.py`** | NOT frozen but intentionally retained as Phase-1 reference predictor for backtester. Per `ridge_predictor.py:25-28`: "stays the default inside `ml/` for legacy callers." Has zero partner-facing UI consumers; the analysis packet uses `ridge_predictor.py` instead. γ investigation today verified this. Document the rationale on /methodology when convenient; no deprecation |

---

## 8. Pending merges

**None.** All today's PRs (#137 through #142) deployed clean. Last deploy `25997215168` to commit `d974cc6b`. pedesk.app/healthz → 200.

---

## 9. Fresh-session pickup instructions

If you're an agent reading this cold:

1. **Read this file first.** Then `git log --oneline -15` to verify the PR list above matches actual main.
2. **Verify the chip taxonomy state** by grepping `_FAILURE_REASON_TIER` in `rcm_mc/ui/_chartis_kit.py`. If the count there differs from section 3's "7 failure_reasons today," update this doc.
3. **B.1 design doc** is mid-construction. D1 and D3 are locked (see section 5). D2 (diagnostics method) is the next decision to surface. Write D2 in the same shape as D1's re-surface: primary recommendation, defense, detailed reasoning, edge cases, bikesheds.
4. **Operating principles** in section 2 apply to every PR. Surface inventories cover UI + API. Discipline gate before accepting any audit framing.
5. **Tier-B queue** (section 6) is the backlog. Do not silently fix any T-B item without filing it; do not silently DROP any item by forgetting it.
6. **Frozen items** (section 7) are explicit no-touch zones.

For B.1 specifically: the design doc lives in this chat conversation (not yet committed to repo as a doc file). When D2-D6 are locked and code is drafted, the design doc could be committed to `docs/design/b1_ridge_defensibility.md` as a permanent companion to the PR description.

---

*This document is insurance. If you find a section inaccurate, update it in the same commit as whatever made it inaccurate, so the next reader gets the current state.*
