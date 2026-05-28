# Editorial style-sweep · migration inventory

**Spec**: 2026-05-28 editorial handoff — strict Tier-1 5-block head + spec-forbidden trope removal.

**Status (as of batch 21, 2026-05-28)**: 21 PRs shipped (#1057–#1077 pending); ~56 routes effectively swept; ~275 page renderers still to migrate.

**Wave-1 (batch 19) shipped**: `my_dashboard_page`, `portfolio_monitor_page`, `deal_mc_page`
**Wave-2 (batch 20) shipped**: `portfolio_bridge_page`, `risk_workbench_page`, `scenario_modeler_page`, `market_intel_page`, `escalations_page`
**Wave-3 (batch 21) shipped**: `bridge_audit_page`, `data_room_page`, `denial_prediction_page`, `diligence_checklist_page`, `exit_timing_page`
**Wave-4 (batch 22) shipped**: `hcris_xray_page` (2 paths), `hospital_providers_page`, `ic_memo_page`, `ic_packet_page` (2 paths), `management_scorecard_page`
**Wave-5 (batch 23) shipped**: `methodology_page`, `model_validation_page`, `physician_eu_page`, `quant_lab_page`, `questions_aggregator_page`
**Wave-6 (batch 24) shipped**: `advanced_tools_page` (2 paths), `market_data_page` (2 paths), `regulatory_calendar_page`, `sector_intelligence_page`, `seeking_alpha_page`, `thesis_pipeline_page` (2 paths)

## 🎉 Group B fully cleared

All 30 originally-flagged Group B files are now in Group A. The strict 5-block head + `ck_editorial_head()` cascade is the universal standard across every page that previously emitted a `ck_section_intro` at its masthead.

This doc is the **single source of truth** for what remains. Every batch updates it.

---

## The universal head helper

The kit now exposes one universal builder that ALL remaining pages should adopt:

```python
from ._chartis_kit import ck_editorial_head

head = ck_editorial_head(
    eyebrow="DEAL MONTE CARLO",
    title=f"Monte Carlo — {html.escape(deal_name)}",
    meta=f"{n_runs:,} RUNS · DEAL {deal_id.upper()}",
    lede_italic_phrase="Range of outcomes for this thesis.",
    lede_body="N-trial Monte Carlo …",
    source_note="Computed from packet inputs",   # optional
    actions_html=ck_copy_share_link_button(),    # optional
)
```

Output:
- Single `<h1>` (no dual-h1 trap)
- Eyebrow with 24×1px `--green-deep` dash
- Mono uppercase meta-line
- Italic-first-phrase serif lede in `--green-deep`
- Optional source-note
- 4-bucket status-dot legend
- Optional right-side actions block (share-link / cross-links / etc.)

Pages should call this and **drop their `ck_section_intro` or local `_xx_head_css`** in favor of the unified helper.

---

## Groups (304 pages total)

### GROUP A · Already swept (16 / 304 · 5.3%) — ✅ compliant

| File | Helper used | PR |
|---|---|---|
| `pipeline_page.py` | local `_pp_head_css` | #1058 |
| `library_page.py` | local `_lib_head_css` | #1059 |
| `home_v2.py` | local `_home_head_css` | #1061 + #1073 |
| 6× sector vertical pages (dialysis, home-health, hospice, irf, ltch, snf) | shared `render_sector_screener` (`_ss_head_css`) | #1062 |
| `diligence_index_page.py` + `section_catalog_page.py` | shared `render_grouped_catalog` (`_HEAD_CSS`) | #1060 |
| `section_best_page.py` | local `sb-head` styles | #1064 |
| `bear_case_page.py` | local `_bc_head` | #1071 |
| `covenant_lab_page.py` | local `_cv_head` | #1072 |
| `payer_stress_page.py` | local `_ps_head` | #1072 |
| `day_one_page.py` | local `_do_head_css` | #1070 |
| `deal_profile_page.py` | local `_dp_head_css` | #1067 |
| Plus `portfolio_overview.py`, `analytics_pages.py` (4 renderers), `hospital_profile.py`, `sector_provider_profile.py` | various local helpers | #1057, #1063, #1066, #1069 |

### GROUP B · Legacy `ck_section_intro` at head (30 / 304 · 9.9%) — ⚠ dual-h1 risk

Pages calling `ck_section_intro()` in the top half of their render function. Each carries a risk of the shell auto-injecting a second `<h1>` above it (was fixed for several pages in earlier batches; remaining ones still emit duplicate title blocks).

**High-traffic targets** (priority sweep next):

| File | Approximate route | Notes |
|---|---|---|
| `deal_mc_page.py` | `/models/mc/<id>` | Monte Carlo per-deal |
| `my_dashboard_page.py` | `/my/<owner>` | Personal portfolio view |
| `portfolio_monitor_page.py` | `/portfolio/monitor` | Daily monitor |
| `portfolio_bridge_page.py` | `/portfolio/bridge` | Cross-deal EBITDA bridge |
| `risk_workbench_page.py` | `/risk/workbench` | Risk analysis bench |
| `scenario_modeler_page.py` | `/scenarios/design` | Scenario builder |
| `market_intel_page.py` | `/market-intel` | Market intelligence |
| `escalations_page.py` | `/alerts/escalated` | Escalation queue |

**Remaining 22 mid-priority**: `advanced_tools_page`, `bridge_audit_page`, `data_room_page`, `denial_prediction_page`, `diligence_checklist_page`, `exit_timing_page`, `hcris_xray_page`, `hospital_providers_page`, `ic_memo_page`, `ic_packet_page`, `management_scorecard_page`, `market_data_page`, `methodology_page`, `model_validation_page`, `physician_eu_page`, `quant_lab_page`, `questions_aggregator_page`, `regression_page` (in-body intros only — main masthead already swept #1055), `regulatory_calendar_page`, `sector_intelligence_page`, `seeking_alpha_page`, `thesis_pipeline_page`.

**Migration recipe per file**:
1. Replace the `ck_section_intro(...)` call at the top with `ck_editorial_head(...)`.
2. If the page already had a `ck_page_title` AND an `editorial_intro=` shell kwarg, drop both (the new helper produces the h1 itself).
3. Add an h1-count test to `tests/test_<page>_editorial_head.py` (use `tests/test_bear_case_editorial_head.py` as a template).

### GROUP C · Legacy CAD chrome (~180 / 304 · 59.2%) — ⚠ spec-forbidden tropes

Pages using `cad-card`, `cad-table`, `cad-btn`, plus `border-left:[1-9]px solid` accent stripes, oversized `border-radius`, or content-card `box-shadow`. These violate the Tier-4 don'ts.

**Highest-density trope violators** (priority sweep):

| File | border-left | box-shadow | border-radius | Approx LOC | Notes |
|---|---|---|---|---|---|
| `dashboard_page.py` | 2 | 3 | 17 | 2,623 | Biggest single file |
| `models_page.py` | 3 | 1 | 0 | 1,130 | Core analytics drill-in |
| `target_screener_page.py` | 1 | 1 | 3 | 1,544 | Pipeline screener |
| `physician_attrition_page.py` | 4 | 1 | 8 | 1,209 | Highest border-left density |
| `counterfactual_page.py` | 3 | 0 | 6 | 916 | Already partially swept (#1069) |
| `ml_insights_page.py` | 3 | 0 | 6 | 958 | ML model surface |
| `deal_autopsy_page.py` | 2 | 1 | 4 | 892 | Deal postmortem |
| `alerts_page.py` | 3 | 0 | 0 | 520 | Daily alerts |
| `compare_page.py` | 2 | 0 | 0 | 454 | Compare deals |
| `ebitda_bridge_page.py` | 0 | 0 | 2 | 1,675 | EBITDA bridge surface |
| `competitive_intel_page.py` | 1 | 0 | 0 | 575 | Competitive intel |
| `deal_library_page.py` | 2 | 0 | 0 | 444 | Deal library |

**Migration recipe**: PR-level CSS sweep. For each page:
1. Convert `cad-card` content cards to `.ck-panel` (hairline, no shadow, no left-border)
2. Strip every `border-left:[1-9]px solid` accent UNLESS it's semantic (severity color on `.ck-severity-panel`-shaped surfaces)
3. Cap `border-radius` at 2px
4. Replace `box-shadow` on content cards with `--paper-hi` background hover

### GROUP D · No clear page head (~78 / 304 · 25.7%) — ⚠ relies on shell auto-inject or has no h1

Pages with no `ck_page_title`, `ck_section_intro`, `editorial_intro=`, or local head helper. Either the shell adds an h1 from the `title` kwarg, or the page has no h1 at all (a11y failure).

**Confirmed-existing high-priority candidates** (verify each before sweep):
- `calibration_page.py` (`/calibration`)
- Other Group D files need individual verification — many appear in `data_public/` analyzer surfaces and may already be swept indirectly via the `chartis_shell` auto-inject path.

**Migration recipe per file**:
1. Call `ck_editorial_head(...)` at the top of the render function.
2. Drop any `editorial_intro=` kwarg on the `chartis_shell()` call (the helper produces the h1 directly).
3. Add an h1-count test.

---

## Migration timeline (best-of-best plan)

Each batch caps at 2–3 page renderers + tests so review stays manageable.

### Batch 19 (this PR) — Phase 1 foundations
- Ship `ck_editorial_head()` kit helper
- Ship this inventory doc
- Sweep first 3 high-traffic Group B: `deal_mc_page`, `my_dashboard_page`, `portfolio_monitor_page`
- Pin: each route renders exactly one `<h1>` + `ck-eh` head wrapper

### Batches 20–24 — finish Group B (8 high-traffic + 22 mid-priority over 5 PRs of ~6 pages each)

### Batches 25–30 — sweep Group D + verify the remaining 78 files render exactly one h1

### Batches 31–45+ — Group C trope removal (3-4 pages per PR; ~50 PRs to clear 180 files, but each PR ships visible cleanup)

**Honest pace estimate**: at the autonomous-loop's current cadence (~3 PRs/hour green-to-green), the remaining ~288 pages can be cleared in roughly 65-80 more PRs. Each batch is small, atomic, and reversible.

---

## Honesty rules carried across every batch

1. **Real counts only** in meta-lines — never hard-code. Pull from the data layer.
2. **One `<h1>` per page** (#1036 a11y invariant).
3. **No fabricated numbers** anywhere — empty states render `—` or honest "Awaiting data".
4. **No forbidden tropes**: no shadows on content cards (Tier-4), no card radius > 2px, no left-border-accent strips (except semantic severity).
5. **Italic-first-phrase preserves existing partner copy** — visual treatment changes, wording doesn't (unless the wording itself is broken).
6. **Tests pin the contract** — every sweep adds a per-page `_editorial_head` test (use `tests/test_bear_case_editorial_head.py` as the template).

---

## How to claim a batch

When a future loop iteration picks a batch:
1. Pick 2-3 files from the priority lists above (in order).
2. Branch off latest `main`.
3. Apply the migration recipe per file.
4. Update this doc — move swept files from B/C/D into the A list with the PR number.
5. Run the broad-sweep test suite (`pytest -q -k "...affected files..."`).
6. Open PR with the standard cumulative summary at the bottom.
7. Auto-merge on green CI; watcher confirms deploy + healthz.

This loop continues until all 304 pages are in Group A.
