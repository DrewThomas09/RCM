# Phase 3 Proposal — Demo-Ready /app

**Branch:** `feat/ui-rework-v3` @ `757a649` · **Status:** PROPOSAL — no implementation yet
**Baseline:** Phase 2 contract tests `18/18 PASS` in both legacy + editorial modes (re-confirmed)
**Optimization target:** demo-ready `/app` for the scheduled partner walkthrough; do NOT optimize for "most pages reskinned." Phase 2b/2c/2d wait.

---

## TL;DR

Phase 3 fills in the dashboard's stub returns with real data so the partner walkthrough doesn't surface "structure-without-data" cells. Sequencing per Q3.5-first decision: canonical exports path FIRST (one-meeting product decision, unblocks filesystem work), then EBITDA decomposition + covenant grid + cross-portfolio playbook signals + PHI banner polish.

**Estimated commit count: 11.** Mirrors Phase 2's footprint. No sub-split — each commit is small and atomic; cluster boundaries are obvious from the work-class (Q3.5 takes 4 of the 11; the rest are 1 commit each).

**Honest scope-cut surfaced during inventory:** `deal_snapshots` schema only carries 1 of the 6 spec covenants (Net Leverage). Q3.2 wires that 1 row with real data; the other 5 stay as `—` with "data not collected yet" footnote. The alternative — synthesizing fake covenant numbers from related metrics — is rejected as worse than honest emptiness during a demo.

---

## Step 0 — Baseline

```
branch: feat/ui-rework-v3
commit: 757a649

Contract tests (legacy):    18/18 PASS in 2.11s
Contract tests (editorial): 18/18 PASS in 1.67s
```

---

## Step 1 — Source-of-truth re-read

Re-confirmed the 5 helpers Phase 3 modifies, their stub-return shapes, the data sources required, the registered Q3.* questions in `UI_REWORK_PLAN.md`, and the spec sections (§6.7 covenant heatmap / §6.8 EBITDA drag / §6.9 initiative tracker / §6.11 deliverables). Specific reads behind the gap analysis below.

---

## Step 2 — Inventory + gap analysis

### 2a. Q3.5 — Export-writer inventory + canonical path migration

**Existing exporters (12 found by grep on file-write patterns + `to_excel` / `wb.save` calls):**

| File | Writer | Path API |
|---|---|---|
| `rcm_mc/exports/packet_renderer.py:158` | `render_diligence_memo_html` | `out_dir` kwarg (default = `tempfile.mkdtemp`) |
| `rcm_mc/exports/packet_renderer.py:191` | `render_diligence_memo_pptx` | same |
| `rcm_mc/exports/packet_renderer.py:365` | inline CSV write | uses `out_dir` |
| `rcm_mc/exports/packet_renderer.py:576` | inline `path.write_text` | uses `out_dir` |
| `rcm_mc/exports/diligence_package.py:153` | zip+packet bundler | `out_dir` kwarg, no default |
| `rcm_mc/exports/exit_package.py:233` | zip bundler | `out_dir` kwarg, default = `Path(".")` |
| `rcm_mc/exports/xlsx_renderer.py:497` | `wb.save(out_dir / f"{stem}.xlsx")` | `out_dir` kwarg |
| `rcm_mc/exports/bridge_export.py:220` | `wb.save(buf)` | BytesIO (no path) |
| `rcm_mc/exports/ic_packet.py:1257` | `render_ic_packet_html` | returns string, no write |
| `rcm_mc/exports/qoe_memo.py:67` | `render_qoe_memo_html` | returns string, no write |
| `rcm_mc/reports/full_report.py:217` | `with open(out_path, "w")` | `out_path` arg |
| `rcm_mc/reports/markdown_report.py:122` | `with open(md_path, "w")` | `md_path` arg |
| `rcm_mc/reports/exit_memo.py:363` | `with open(out_path, "w")` | `out_path` arg |
| `rcm_mc/reports/_partner_brief.py:578` | `with open(out_path, "w")` | `out_path` arg |
| `rcm_mc/reports/html_report.py:1289` | `with open(out_path, "w")` | `out_path` arg |
| `rcm_mc/infra/_bundle.py:460` | `xls.to_excel(...)` × 8 sheets | uses an `xls` ExcelWriter context |

**Critical existing infrastructure** (huge accelerator for Phase 3):

- `rcm_mc/exports/export_store.py` already has `record_export(store, deal_id, analysis_run_id, format, filepath, ...)` and `list_exports(store, deal_id)`. The `generated_exports` table is the manifest the deliverables block needs. **4 of the 12 writers already call `record_export` (in server.py at lines 8819, 8837, 8863, 8903)**; the other 8 don't.

- `_app_deliverables.py` Phase 2 reads from `analysis_runs` (one row per run). Switching it to read from `generated_exports` (one row per artifact, scoped by deal_id, with format pill data already populated) is a strict upgrade.

**Migration plan — incremental, NOT big-bang:**

1. New file `rcm_mc/infra/exports.py` (location defended below) with one function:
   ```python
   def canonical_export_path(
       deal_id: Optional[str],
       filename: str,
       *,
       timestamp: Optional[str] = None,
   ) -> Path
   ```
   Resolves to `/data/exports/<deal_id>/<timestamp>_<filename>` for deal-scoped artifacts, `/data/exports/_portfolio/<timestamp>_<filename>` for cross-portfolio (when `deal_id is None`). Creates parent dirs idempotently. Defaults timestamp to UTC `now`.

2. Update writers ONE FAMILY AT A TIME:
   - **Commit 2**: 5 reports (`full_report.py`, `markdown_report.py`, `exit_memo.py`, `_partner_brief.py`, `html_report.py`) all take `out_path` and write text. Add a fallback: when caller passes `out_path` it wins (back-compat); when caller passes `(deal_id, filename)` instead, route through `canonical_export_path`.
   - **Commit 3**: 3 packet/zip exporters (`packet_renderer.py`, `diligence_package.py`, `exit_package.py`) — same fallback pattern.
   - **Commit 4**: `xlsx_renderer.py` + `bridge_export.py` + `infra/_bundle.py`. Same pattern.
   - Each migration commit also adds `record_export()` to writers that aren't already calling it (so `generated_exports` becomes the comprehensive manifest by end of Phase 3).

3. Server.py callsites that already call `record_export` continue to work (back-compat preserved).

**Non-deal-scoped artifact handling:**

The `infra/_bundle.py` exporter writes a multi-sheet Excel summarizing a corpus (no single deal_id). The `_portfolio` subdirectory is the right home: `/data/exports/_portfolio/<timestamp>_corpus_summary.xlsx`. Underscore prefix is intentional — sorts above any real `deal_id` in directory listings, so `_portfolio` always appears first when a partner browses `/data/exports/`.

### 2b. Q3.3 — EBITDA decomposition mapping

**Actual `DealAnalysisPacket.ebitda_bridge` shape:**

```python
class EBITDABridgeResult:
    current_ebitda: float
    target_ebitda: float
    total_ebitda_impact: float
    new_ebitda_margin: float
    ebitda_delta_pct: float
    per_metric_impacts: List[MetricImpact]    # ← real data lives here
    waterfall_data: List[Tuple[str, float]]
    sensitivity_tornado: List[Dict[str, Any]]
    working_capital_released: float
    margin_improvement_bps: int
    ev_impact_at_multiple: Dict[str, float]
    status: SectionStatus
    reason: str

class MetricImpact:
    metric_key: str        # e.g. "denial_rate_overall"
    ebitda_impact: float   # dollars
    revenue_impact: float
    cost_impact: float
    # ... etc
```

**Mapping per_metric_impacts → 5 spec components:**

The bridge can have any number of per-metric impacts (varies by deal — typically 5–8). The spec wants 5 fixed buckets. Mapping table:

| metric_key prefix | Spec component | Color (matches Phase 2 placeholder) |
|---|---|---|
| `denial_*` | Denial workflow gap | `var(--red)` |
| `coding_*`, `cdi_*` | Coding / CDI miss | `var(--amber)` |
| `days_in_ar`, `ar_*` | A/R aging | `var(--blue)` |
| `self_pay_*`, `bad_debt_*`, `charity_*` | Self-pay leakage | `var(--teal-deep)` |
| *anything else* | Other (residual) | `var(--muted)` |

**Implementation in `_app_ebitda_drag._decompose_drag(packet)`:**

1. Iterate `packet.ebitda_bridge.per_metric_impacts`
2. Bucket each by `metric_key` prefix (case-insensitive starts-with; fall through to "Other" if no match)
3. Sum `ebitda_impact` per bucket
4. Compute pct = bucket_total / total_ebitda_impact (or per-component pct of an overall "drag" basis — ABSOLUTE values, not signed; the bar shows where impact concentrates)
5. Return list of 5 tuples: `(key, label, color, pct, dollars_M)`

**Edge cases:**

- **Bridge with 0 per_metric_impacts** (no analysis run): existing "Run the analysis pipeline" empty state from Phase 2 still applies. No change.
- **Bridge with all impacts in 1 bucket** (e.g. all denial-related): the OTHER 4 buckets render at 0% with their swatches still visible (preserves the 5-segment chrome). The data table reads `0%` for the empty buckets. No fake distribution.
- **Bridge with negative `ebitda_impact`** (lever underperformed): take `abs()` for the pct calculation but render the dollar value with sign preserved + tone (red).
- **`total_ebitda_impact == 0`** (defensive zero): all 5 buckets render 0% / `—`. Empty-state-as-data; not a placeholder.

### 2c. Q3.2 — Covenant grid wiring (PARTIAL — see scope-cut)

**The data model gap surfaced during inventory:**

`deal_snapshots` table schema (created at `portfolio_snapshots.py:94`):
```sql
CREATE TABLE deal_snapshots (
    snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id TEXT NOT NULL,
    stage TEXT NOT NULL,
    created_at TEXT NOT NULL,
    ...
    covenant_leverage REAL,         -- ONE covenant
    covenant_headroom_turns REAL,
    covenant_status TEXT,           -- band string for that ONE covenant
    ...
)
```

Spec §6.7 wants 6 covenants × 8 quarters. The schema only stores 1 covenant per snapshot.

**Three options:**

| Option | What | Verdict |
|---|---|---|
| A. Schema migration — add 5 covenant columns to `deal_snapshots` | invasive; columns empty for old snapshots; backfill problem | rejected for Phase 3 — schema work not in scope |
| B. Synthesize from related metrics — derive Denial Rate / A/R Days from `observed_metrics`, fabricate the rest | fabricates data the system doesn't track. Demo is the wrong place to invent numbers | **rejected** |
| C. Honest partial wiring — Net Leverage row from real `covenant_leverage` data, other 5 rows render `—` with "data not collected yet" footnote | preserves chrome; doesn't fabricate; sets up Phase 3+ to wire the rest as the data model evolves | **recommended** |

**Implementation under Option C:**

1. New helper in `_app_covenant_heatmap.py`: `_fetch_leverage_history(store, deal_id) → list[(quarter, ratio)]` — `SELECT created_at, covenant_leverage FROM deal_snapshots WHERE deal_id=? ORDER BY created_at DESC LIMIT 8`
2. Real band derivation for Net Leverage: ratio ≤ 6.0x → safe, 6.0–6.5x → watch, > 6.5x → trip. Threshold defaults from spec §6.7's `≤ 6.5x` covenant.
3. Per-deal threshold override: new accessor `covenant_thresholds(store, deal_id)` returns `{covenant_key: (warn_at, trip_at)}`. Default values from spec; per-deal overrides via a future `deal_covenant_overrides` table (not Phase 3 scope; the accessor exists but reads spec defaults today, swap to per-deal as it lands). Comment marks it.
4. Other 5 rows: stay as `—` cells but get a foot-note `"5 of 6 covenants not yet tracked. See [Q3.2 wiring backlog](docs/UI_REWORK_PLAN.md#q3.2)."` rendered below the grid.

### 2d. Q3.4 — Cross-portfolio playbook aggregation

**Existing infrastructure:**

- `rcm_mc/rcm/initiative_tracking.py:161` has `initiative_variance_report(store, deal_id) -> pd.DataFrame` — per-deal variance vs plan.
- No existing cross-deal aggregator.

**Phase 3 implementation:**

New helper, `cross_portfolio_initiative_variance(store, *, top_n=10, held_only=True)` in `rcm_mc/rcm/initiative_tracking.py`:

1. List all deals (or only `stage in (hold, exit)` if `held_only=True`)
2. Call `initiative_variance_report(store, deal_id)` for each
3. Concatenate all rows into one DataFrame
4. Compute summary stats per `initiative_name`:
   - count of deals where this initiative appears
   - mean variance %
   - sign — if mean variance < -10% AND count ≥ 2, classify as "playbook gap" (recurring miss)
5. Sort by absolute mean variance descending, take top N
6. Return DataFrame with columns: `initiative_name`, `n_deals`, `mean_variance_pct`, `total_actual_M`, `is_playbook_gap` (bool), `affected_deals` (comma-separated ids)

**Aggregation thresholds** (spec is vague — these are defensible defaults):

- "Top variances" = top 10 by absolute mean variance %
- "Playbook gap" = mean variance < -10% AND ≥ 2 affected deals (matches the spec's "when the same initiative repeats across deals with the same sign, it's a playbook gap")
- Time window = current cumulative state (no time-window filter; Phase 4+ can add a "last 4 quarters" view)
- Empty portfolio (zero held deals) → existing empty-state copy; aggregator returns empty DataFrame

**Wiring into `_app_initiative_tracker`:**

When `deal_id is None`, helper now calls the new aggregator instead of rendering empty-state copy. Cards render variance + n_deals + the playbook-gap flag (a small `(playbook gap)` indicator in tone-amber when the bool is true). The variance dot-plot pivots to show one dot per initiative (not per deal-initiative pair).

Helper signature stays unchanged; behavior switches based on `deal_id is None or deal_id`. Empty fund still hits the existing empty-state.

### 2e. Q3.7 — PHI banner CSS-only change

**Current CSS:**

```css
.phi-banner {
  background: var(--green-soft);    /* #DCE6D9 */
  border: 1px solid var(--green);   /* #3F7D4D */
  color: var(--green);              /* #3F7D4D */
  padding: .75rem 1.5rem;           /* ~50px tall with line-height */
  font-family: "Inter", sans-serif;
  font-size: .82rem;
  text-align: center;
  margin: 1rem 2rem;
}
```

**Proposed CSS** (per ticket Q3.7):

```css
:root {
  ...
  --green-muted: #4A7A52;   /* new — between --green and visually quieter */
}

.phi-banner {
  background: var(--green-soft);
  border: 1px solid var(--green-muted);
  color: var(--green-muted);
  padding: .35rem 1.5rem;          /* halved → ~28px tall */
  font-family: "Inter", sans-serif;
  font-size: .75rem;                /* 12px */
  font-weight: 500;
  letter-spacing: .02em;
  text-align: center;
  margin: .5rem 2rem;               /* tighter outer margin */
}
```

**Copy change** in `_chartis_kit_editorial.phi_banner()`:

```diff
-  '🛡 Public data only — no PHI permitted on this instance.'
+  '🛡 Public data only — no PHI'
```

(One-line Python edit — the helper is already pure of mode + reads no env, so this is a pure copy/visual change.)

**WCAG AA contrast check** for `#4A7A52` text on `#DCE6D9` background:

- L1 (foreground) ≈ 0.155
- L2 (background) ≈ 0.737
- contrast ratio ≈ (0.737 + 0.05) / (0.155 + 0.05) ≈ **3.84:1**

That's **below WCAG AA's 4.5:1 floor for body text**. Need to darken `--green-muted` further. Trying `#3D6F45` (slightly deeper):

- L1 ≈ 0.115; ratio ≈ 4.86:1 ✓ — passes AA

**Recommended `--green-muted: #3D6F45`** instead of `#4A7A52`. Same visual intent (muted, less alarm-bell saturated than `--green`), but contrast-compliant. Verify with a real contrast checker before commit ships.

---

## Step 3 — Architecture proposal

### 3a. New module: `rcm_mc/infra/exports.py`

**Why `infra/`:** the canonical-path helper is infrastructure (filesystem layout policy), not a renderer. Putting it in `exports/` would couple it to the existing exporters; `infra/` is the right home for cross-cutting policy. Pattern matches `infra/migrations.py`, `infra/cache.py`, `infra/logger.py` — all things every module depends on but no one owns.

**Contract:**

```python
# rcm_mc/infra/exports.py

def canonical_export_path(
    deal_id: Optional[str],
    filename: str,
    *,
    timestamp: Optional[str] = None,
    base: Optional[Path] = None,
) -> Path:
    """Return the canonical path for an export artifact.

    Layout:
      /data/exports/<deal_id>/<timestamp>_<filename>          (deal-scoped)
      /data/exports/_portfolio/<timestamp>_<filename>          (cross-portfolio)

    Args:
        deal_id: Deal identifier. None routes to the _portfolio subdir.
        filename: Bare filename (e.g. "diligence_packet.html").
        timestamp: ISO-8601 UTC timestamp (default: now). Format
                   YYYY-MM-DDTHH-MM-SS — colons in HH:MM:SS replaced with
                   dashes for filesystem safety on case-insensitive
                   filesystems (macOS).
        base: Override the /data/exports/ root. Defaults to the
              EXPORTS_BASE env var if set, else /data/exports.
              Used by tests; production callers pass nothing.

    Returns:
        Absolute Path with parent directories created.

    # TODO(phase 4): cleanup policy. Per Q3.5 product decision, no
    # auto-cleanup is wired in Phase 3. Phase 4 adds a retention policy
    # (e.g. 90-day TTL or LRU eviction).
    """
```

The `EXPORTS_BASE` env override is the test-isolation hook — pytest `tmpdir` becomes the base for unit tests so they don't write to `/data/exports/` under CI.

### 3b. Helper signatures (new, per Q-question)

```python
# rcm_mc/rcm/initiative_tracking.py (new function alongside existing)
def cross_portfolio_initiative_variance(
    store: PortfolioStore,
    *,
    top_n: int = 10,
    held_only: bool = True,
) -> pd.DataFrame: ...

# rcm_mc/portfolio/portfolio_snapshots.py (new helper alongside existing rollup)
def covenant_thresholds(
    store: PortfolioStore,
    deal_id: str,
) -> Dict[str, Tuple[float, float]]:
    """Returns {covenant_key: (warn_at, trip_at)}.

    Phase 3: returns spec defaults. Per-deal overrides via
    deal_covenant_overrides table land in Phase 3+.
    """

# rcm_mc/ui/chartis/_app_covenant_heatmap.py (new private helper)
def _fetch_leverage_history(
    store: PortfolioStore,
    deal_id: str,
) -> List[Tuple[str, Optional[float]]]:
    """Last 8 quarterly leverage ratios for the focused deal.

    Returns: [(quarter_label, ratio_or_None), ...] in chronological order.
    """

# rcm_mc/ui/chartis/_app_ebitda_drag.py (rewrite of existing private helper)
def _decompose_drag(
    packet: Optional[Any],
) -> Optional[List[Tuple[str, str, str, float, float]]]:
    """Real implementation: bucket per_metric_impacts into 5 spec
    components by metric_key prefix. Returns None on no packet OR
    no bridge OR total_ebitda_impact == 0 (existing empty-state
    behavior preserved)."""
```

### 3c. Migration plan — incremental, not big-bang

Phase 3 commits 2–4 migrate the 12 export writers in 3 batches (5 + 3 + 4 writers each). Each commit:

1. Edits one batch of writers to call `canonical_export_path(deal_id, filename)` when no `out_path`/`out_dir` is passed (back-compat preserved — existing callers continue to pass paths)
2. Adds `record_export()` to writers in that batch that aren't already recording
3. Smoke-tests the writers in isolation

The "back-compat preserved" rule is what makes this incremental. After commits 2–4, every writer KNOWS the canonical path but only writes to it when asked. Phase 4 (or later) can flip the default to "use canonical unless overridden."

### 3d. Test plan — new contract tests

| Test | Asserts |
|---|---|
| `test_canonical_export_path_layout` | `/data/exports/<deal_id>/<ts>_<file>` for deal-scoped; `/_portfolio/<ts>_<file>` for None deal_id; parent dirs created idempotently |
| `test_v3_app_ebitda_drag_renders_real_decomposition` | When focused deal has bridge with per_metric_impacts, the rendered `/app?ui=v3&deal=<id>` shows non-uniform bar segments AND non-zero $ values in at least one bucket |
| `test_v3_app_covenant_heat_real_leverage_row` | When focused deal has `deal_snapshots` with `covenant_leverage`, the Net Leverage row of the heatmap renders cells with real values + appropriate band classes (safe/watch/trip), NOT all `—` |
| `test_v3_app_initiatives_cross_portfolio_when_no_focus` | When NO deal is focused, the initiative tracker calls `cross_portfolio_initiative_variance` and renders aggregated rows (not the Phase 2 empty-state copy) |
| `test_v3_app_deliverables_reads_generated_exports` | `_app_deliverables.render_deliverables` shows artifacts from `generated_exports`, including artifact files at canonical paths |
| `test_phi_banner_contrast_meets_wcag_aa` | Programmatic check: parse `--green-muted` from chartis.css, compute contrast vs `--green-soft`, assert ≥ 4.5:1 |
| `test_phase_3_todos_resolved` | `grep -rn 'TODO(phase 3)' rcm_mc/` returns zero matches after Phase 3 ships |

**Total tests after Phase 3: 18 → 25.** The `test_phase_3_todos_resolved` discipline gate goes in late (last commit's test file edit).

### 3e. Demo readiness — the optimization target

**The walkthrough scenario:** partner clicks `/app?ui=v3`, sees the dashboard, focuses a deal in the held cohort, scrolls.

| Section | Pre-Phase-3 (Phase 2 ship) | Post-Phase-3 (this proposal) |
|---|---|---|
| KPI strip | Real fund-level numbers | unchanged |
| Pipeline funnel | Real stage counts | unchanged |
| Deals table | Real deal list | unchanged |
| Focused-deal bar | Real focused-deal metadata | unchanged |
| Covenant heatmap | All 6 rows × 8 cols `—` | **Net Leverage row real + 5 footnoted "data not yet tracked"** |
| EBITDA drag | 5 segments at uniform 20% | **Real per-component decomposition from packet** |
| Initiative tracker | Empty state when no focus | **Cross-portfolio playbook signals (top variances, gap classification)** |
| Alerts | Real "all clear" or active list | unchanged |
| Deliverables | HTML-only from analysis_runs | **Multi-format artifacts from generated_exports + canonical paths** |
| PHI banner | Loud bar | **Quieter, ~28px, more muted green** |

5 of 9 blocks change behavior. The other 4 already shipped real data in Phase 2.

---

## Step 4 — Conflicts and open questions

### 4a. Conflicts that need user decision

| # | Conflict | My recommendation |
|---|---|---|
| **C1** | `deal_snapshots` schema only carries 1 of 6 covenants. Wiring all 6 requires schema migration | **Honest partial: wire Net Leverage from real data; foot-note the other 5 as "data not yet tracked".** Don't synthesize covenants from related metrics during a demo. Schema migration is a Phase 4+ task. Confirm? |
| **C2** | `--green-muted: #4A7A52` from the Q3.7 ticket is below WCAG AA (3.84:1 vs 4.5:1 floor). Need to darken | **Use `#3D6F45` (4.86:1).** Same visual intent (less saturated than `--green`), contrast-compliant. Re-verify with a contrast checker on first commit; happy to land a different hex if the visual eyeball fails. Confirm scope of "verify with checker"? |
| **C3** | Q3.4 cross-portfolio aggregation has no spec for time-window or playbook-gap threshold | **Defaults: top-10 by absolute mean variance, "playbook gap" = mean ≤−10% AND ≥2 deals affected, no time-window filter.** All defensible; document them in the helper docstring so a future tweak is one-line. Confirm? |
| **C4** | EBITDA bucketing uses `metric_key` prefix matching. The actual prefixes in production data may not match my mapping table (e.g. the codebase uses `payer_denial` not `denial_*`). Risk: wrong-bucket bucketing on real packet | **Run the helper against a real `/api/analysis/<id>` packet pre-flight in commit 6; if metric_keys don't match expected prefixes, expand the mapping table at that commit.** Don't ship the placeholder mapping if it disagrees with reality. Confirm "test against real packet at commit 6" approach? |
| **C5** | `infra/_bundle.py` writes a multi-sheet Excel through `pd.ExcelWriter` — its `to_excel` calls don't use `out_path`/`out_dir` directly. Migration is more invasive than the others | **Defer `_bundle.py` migration to a Phase 3 sub-commit or to Phase 4.** It's a low-traffic exporter (corpus summaries) and the migration touches `pd.ExcelWriter` lifecycle which has its own gotchas. Phase 3 commits 2–4 cover the 11 high-traffic writers. Confirm scope-cut? |

### 4b. Sub-split — Phase 3 commit count

**11 commits** for Phase 3-as-proposed:

```
1.  feat(infra): canonical_export_path + new infra/exports.py
2.  refactor(reports): migrate full_report + markdown_report + exit_memo + _partner_brief + html_report writers (5)
3.  refactor(exports): migrate packet_renderer + diligence_package + exit_package writers (3)
4.  refactor(exports): migrate xlsx_renderer + bridge_export + ic_packet writers (3) [_bundle deferred per C5]
5.  feat(deliverables): wire _app_deliverables to generated_exports + canonical filesystem paths
6.  feat(ebitda-drag): real per_metric_impacts → 5-component bucketing in _app_ebitda_drag
7.  feat(covenant-heat): wire Net Leverage row from deal_snapshots; document the 5 unwired
8.  feat(initiatives): cross_portfolio_initiative_variance + wire into _app_initiative_tracker
9.  feat(phi-banner): Q3.7 visual weight reduction (CSS + 1-line Python copy edit)
10. test(contract): 6 new tests + test_phase_3_todos_resolved discipline gate (18→25)
11. docs(ui-rework): Phase 3 close — IA + plan + Phase 4 question prep
```

No sub-split needed; 11 fits the Phase 1/Phase 2 cluster size. If commits 2–4 (the export migrations) feel like a single conceptual unit and you'd prefer one squashed commit, they collapse cleanly.

### 4c. Pause points during implementation

Per Phase 1/2 pattern:

- **Before commit 2** — paste `canonical_export_path` API surface for review. Locks the path layout + back-compat semantics.
- **Before commit 6** — paste the EBITDA bucketing mapping table after running it against a real packet (per C4); confirm the prefix list matches real data.
- **Before commit 11** — paste the IA / plan diffs.

---

## Step 5 — Decisions needed before commit 1

Five items in 4a (C1–C5) plus structural confirmation:

1. **C1** — Honest partial covenant wiring (1 of 6 rows real, 5 footnoted)? (yes/no)
2. **C2** — `--green-muted: #3D6F45` for WCAG AA compliance? (yes/no)
3. **C3** — Cross-portfolio defaults (top-10, ≥2 deals + ≤−10% = gap, no time window)? (yes/no)
4. **C4** — Test EBITDA mapping against real packet at commit 6, expand if mismatch? (yes/no)
5. **C5** — Defer `infra/_bundle.py` migration to Phase 4? (yes/no)
6. **Sub-split** — keep 11 commits as-is, or squash export migrations (commits 2–4) into one? (as-is / squash)

Confirm those six and I proceed to commit 1 (`canonical_export_path`) → pause for API review → commits 2–9 → pause before commit 10 (orchestrator-equivalent for tests) → commit 10 → pause before commit 11 (docs) → commit 11 → push.

**Hard rules respected throughout:**
- All work stays on `feat/ui-rework-v3`. Never push to `main`.
- Contract tests stay green at every commit (18 minimum, climbing to 25 by commit 10).
- Data model wins — every gap in 2a–2e has a "do less, ask user" recommendation, not a fabrication.
- No implementation written until you approve.
