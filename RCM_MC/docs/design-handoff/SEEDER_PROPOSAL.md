# SEEDER_PROPOSAL — Demo database seed script

**Status:** Proposal · Pre-Phase-2b infrastructure work
**Authored:** 2026-04-25 (overnight, against a tired-but-disciplined ask)
**Decision required:** Andrew — review with coffee, greenlight or course-correct before implementation

---

## What this is

A scripted, repeatable, idempotent seed for a demo SQLite database that populates every block on `/app?ui=v3` with realistic, partner-readable data. Replaces the current "spin up `/tmp/demo.db` and watch it render empty" failure mode that surfaced during the 2026-04-25 local test.

This proposal is the proposal-first deliverable. **No implementation code is being written tonight.** The morning review decides scope, naming, and any conflicts; commits 1..N follow only after Andrew's nod.

---

## What this is NOT

- Not a fix for the cross-cutting nav gaps (`?ui=v3` propagation, topnav target ports). Those are Phase 2b/2c/2d work — see `UI_REWORK_PLAN.md` "Discovered during local testing 2026-04-25" §1–§2.
- Not a production-DB tool. The seeder lives under a `dev/` subpackage and refuses to run if it detects a production marker (proposed: refuses if `--db` resolves under `/data/` without `--force-prod-path`).
- Not a faker-library wrapper. Realistic enough for a partner demo means *deliberately curated* data (fictional hospital systems, plausible covenant trajectories), not random.

---

## Step 1 — Source-of-truth files read

Confirmed paths (re-verify before implementation, may have drifted):

| File | What it owns |
|---|---|
| `docs/DEMO_CHECKLIST.md` | Per-block data requirements + verification commands (sibling of `UI_REWORK_PLAN.md`, NOT under `design-handoff/`) |
| `rcm_mc/portfolio/portfolio_snapshots.py` | `register_snapshot()` API; `DEAL_STAGES = ('sourced', 'ioi', 'loi', 'spa', 'closed', 'hold', 'exit')` |
| `rcm_mc/portfolio/store.py` | `PortfolioStore`, `upsert_deal`, `add_run` |
| `rcm_mc/exports/export_store.py` | `record_export()` (the API to write to `generated_exports`) |
| `rcm_mc/deals/deal_stages.py` | `set_stage()` for the deal_stage_history table; `VALID_STAGES` includes `pipeline/diligence/ic` for the auth-side stage transitions distinct from the snapshot stages above |
| `rcm_mc/rcm/initiatives.py` + `rcm/initiative_tracking.py` | `get_all_initiatives()` (validates initiative_id at insert time); `record_initiative_actual()` |
| `rcm_mc/alerts/alerts.py` | `evaluate_active()` — alerts are *derived* from deal_snapshots, not seeded directly |
| `rcm_mc/analysis/packet_builder.py` + `analysis_store.py` | `get_or_build_packet()` — caches `DealAnalysisPacket` in `analysis_runs` table |
| `rcm_mc/ui/chartis/_app_*.py` (9 helpers) | What each block actually consumes |
| `rcm_mc/infra/exports.py` | `canonical_deal_export_path()` / `canonical_portfolio_export_path()` — the seeder writes placeholder export files at canonical paths |

**Watch-out:** there are TWO different "stage" namespaces in the codebase that the seeder has to keep straight. The `deal_snapshots.stage` namespace is what the dashboard funnel/filter consumes (`sourced/ioi/loi/spa/closed/hold/exit`). The `deal_stage_history.stage` namespace is the lifecycle workflow (`pipeline/diligence/ic/hold/exit/closed`). These are the same word for different things. The seeder writes BOTH so downstream features stay coherent, but the dashboard funnel only reads from `deal_snapshots`.

---

## Step 2 — Per-block inventory

For each of the 9 dashboard blocks: minimum-to-render vs. interesting-to-demo, plus dependencies.

| # | Block | Min to render | Interesting-to-demo | Depends on |
|---|---|---|---|---|
| 1 | KPI strip | `latest_per_deal()` non-empty | 5+ deals across stages with non-zero `entry_ev`/`exit_ev`/`moic`/`irr` so weighted aggregate moves visibly | `deal_snapshots` |
| 2 | Pipeline funnel | ≥1 deal at any stage | ≥1 deal in each of ~5 stages with realistic distribution (3 hold, 1 spa, 1 loi, 1 ioi, 1 sourced) | `deal_snapshots` |
| 3 | Deals table | `latest_per_deal()` non-empty | 7 distinct deals with names, stages, EV, MOIC variance | `deal_snapshots` |
| 4 | Focused-deal context bar | ≥1 deal in `hold` ∪ `exit` | ≥3 deals in `hold` ∪ `exit` so prev/next switcher has options | `deal_snapshots`; URL `?deal=<id>` |
| 5 | Covenant heatmap | ≥1 snapshot for focused deal w/ `covenant_leverage` | 8 snapshots over 8 quarters w/ varied trajectory (some deals safe, some watch, some trip) | per-deal `deal_snapshots` history |
| 6 | EBITDA drag bar | Focused deal has a buildable `DealAnalysisPacket` w/ `ebitda_bridge.per_metric_impacts` | `per_metric_impacts` populated with non-uniform `metric_key` mix so bucketing isn't all "Other" — needs `denial_rate` / `case_mix_index` / `days_in_ar` etc. | `analysis_runs` cache OR run the packet builder for the focused deal |
| 7 | Initiative tracker (focused) | ≥1 `initiative_actuals` row for focused deal | 2-3 initiatives per deal w/ varied variance vs. plan | `initiative_actuals` |
| 7 | Initiative tracker (cross-portfolio) | ≥1 actual in trailing 4Q across held deals | ≥1 initiative w/ mean ≤ −10% across ≥2 deals (fires PLAYBOOK GAP pill); ≥1 single-deal-behind; ≥1 ahead | `initiative_actuals` + `latest_per_deal.stage IN (hold, exit)` |
| 8 | Alerts | `evaluate_active(store)` returns at least one Alert | Mix of severity (red/amber/info) — derived from snapshots that trip rules (e.g. covenant headroom < 0.25 turns triggers red) | `deal_snapshots` data shape, NOT direct seed |
| 9 | Deliverables | ≥1 `generated_exports` row OR `analysis_runs` w/ deal | 2-3 exports across formats (HTML/PDF/XLS) per held deal at canonical paths | `generated_exports` + real placeholder files on disk |

**Cross-block dependencies:**

- Block 4 (focused-deal bar) is a no-op unless a deal is focused. Demo flow assumes the user clicks a deal in block 3 to focus it — the seeder doesn't pre-focus, but it MUST produce at least 3 hold deals so the prev/next switcher has options when one is focused.
- Block 6 (EBITDA drag) requires a `DealAnalysisPacket`. Two options: (a) the seeder runs `get_or_build_packet()` synchronously for the focused-candidate deals, populating `analysis_runs` so block 6 hits cache; or (b) the seeder writes a hand-crafted bridge directly to `analysis_runs` JSON. Option (a) is more honest (uses the real builder pipeline) but slower; option (b) is faster but smuggles in a fake bridge. **Recommend (a)** — slowness is a one-time cost paid by the operator, not by the demo.
- Block 7 cross-portfolio mode requires the same initiative_id appearing across ≥2 deals at ≤ −10% variance. The seeder's curation MUST include this — single-deal-only initiatives would hide the playbook-gap pill, which is a marquee feature.
- Block 8 (alerts) is downstream of snapshots. The seeder cannot directly write alerts; it has to write the snapshot data shapes that `evaluate_active()` rules trigger on. This is the right design (alerts are derived, not stored), but means the seeder needs to know which rules fire on which inputs.

---

## Step 3 — Architecture proposal

### 3.1 File location

**Recommend:** `rcm_mc/dev/seed.py` with a thin CLI wrapper at module level (`python -m rcm_mc.dev.seed`).

Defended over alternatives:

| Option | Pro | Con |
|---|---|---|
| `scripts/seed_demo_db.py` | Matches existing `scripts/run_all.sh` convention | Bash scripts are the existing scripts/ residents; a Python file there breaks the implied convention. Also harder to import from tests. |
| `rcm_mc/dev/seed.py` ✅ | Importable as a package; supports `python -m rcm_mc.dev.seed`; easy to gate against production paths; can grow siblings (`rcm_mc/dev/reset.py`, etc.) | Introduces a new `dev/` package — must add `__init__.py` |
| `rcm_mc/cli.py` extension (a `seed` subcommand) | Single CLI surface | Pollutes the production CLI with dev tooling; partners running `rcm-mc --help` shouldn't see "seed" |

### 3.2 Public interface

```python
def seed_demo_db(
    db_path: str | Path,
    *,
    deal_count: int = 7,
    snapshot_quarters: int = 8,
    seed_random: int = 20260425,
    overwrite: bool = False,
    write_export_files: bool = True,
    base_dir: str | Path | None = None,
) -> SeedResult: ...
```

`SeedResult` is a small dataclass with counts (`deals_inserted`, `snapshots_inserted`, `actuals_inserted`, `exports_inserted`, `packet_runs_built`) so callers (and the verification step) can sanity-check the result.

### 3.3 Idempotency model

**Recommend:** **drop-and-recreate-on-overwrite**, default to **refuse-if-non-empty**.

- Default behavior: if `db_path` exists AND has any row in `deals`, raise `SeederRefuseError` with a hint about `--overwrite`.
- `--overwrite` flag: drops and recreates the seeded tables (`deals`, `deal_snapshots`, `deal_stage_history`, `initiative_actuals`, `generated_exports`, `analysis_runs`). Other tables (e.g. `auth.users`, `audit_log`) untouched — operator-installed data survives.
- **Not** an upsert model. Upsert-on-reseed creates ambiguous state ("did I get the new seed or the old data?") that's the wrong shape for a demo prep workflow.

### 3.4 Determinism

`seed_random=20260425` (today's date as int) drives all randomness. Same seed produces same data byte-for-byte: same deal names, same EBITDA values, same covenant trajectories, same initiative variance signs.

Timestamps: `created_at` fields anchor to a fixed reference time (proposed: `datetime(2026, 4, 25, 0, 0, tzinfo=UTC)`) with deterministic offsets per record. Quarterly snapshots count backwards from the reference quarter.

### 3.5 Production safety

```python
def _guard_against_production(db_path: Path, *, force: bool) -> None:
    if force:
        return
    resolved = db_path.resolve()
    if "/data/" in str(resolved) or str(resolved).endswith("seekingchartis.db"):
        raise SeederRefuseError(
            f"db_path {resolved} looks like a production target. "
            f"Pass force=True (or --force-prod-path) to override."
        )
```

The `seekingchartis.db` filename match is a soft heuristic — operator can override, but the default refuses. Eliminates the "I meant to seed `/tmp/demo.db` but typed `seekingchartis.db`" failure mode.

### 3.6 CLI invocation

```bash
.venv/bin/python -m rcm_mc.dev.seed --db /tmp/demo.db
.venv/bin/python -m rcm_mc.dev.seed --db /tmp/demo.db --overwrite --deal-count 10
.venv/bin/python -m rcm_mc.dev.seed --db /tmp/demo.db --no-export-files  # skip filesystem writes
```

Exits 0 on success with a one-line summary; exits 2 on `SeederRefuseError`.

---

## Step 4 — Data realism strategy

### 4.1 Deal names

7 fictional hospital systems with plausible PE-portfolio shapes:

| Deal id | Name | Stage | Notes |
|---|---|---|---|
| `ccf_2026` | Cypress Crossing Health | hold | Flagship; 8 quarters of snapshots; bridge populated; primary demo focus |
| `arr_2025` | Arrowhead Regional | hold | Covenant trajectory lands in "watch" band; useful counterexample |
| `pma_2024` | Peninsula Medical Associates | hold | Strong hold-period story; ahead on initiatives |
| `tlc_2023` | Tidewater Long-term Care | exit | Sold position; closed packet; appears in historicals |
| `nbh_2026` | Northbay Heart | spa | In closing; minimal snapshots |
| `mvm_2026` | Mountainview Medical | loi | Diligence stage; pre-IOI signal only |
| `evh_2026` | Evergreen Health | ioi | Earliest stage; light data |

**Watch-out:** these names are deliberately fictional and non-trademarked. If any conflict with a real US hospital system surfaces in review, swap.

### 4.2 Stage distribution

3 hold + 1 exit + 1 spa + 1 loi + 1 ioi. No `sourced` or `closed` deals in the default seed (operator can re-run with `--deal-count 10` to get a fuller funnel). Justified: "real PE portfolio" shape per spec.

### 4.3 Covenant trajectories

Per-deal `covenant_leverage` time series:

- `ccf_2026`: 5.2 → 5.4 → 5.6 → 5.8 → 5.9 → 6.0 → 6.1 → 6.2 (drifts from safe into watch — "the thesis is intact but warrants attention" demo line)
- `arr_2025`: 5.8 → 5.9 → 6.0 → 6.2 → 6.4 → 6.6 → 6.8 → 7.0 (trips covenant in latest quarter — useful for the alerts block)
- `pma_2024`: 5.0 → 4.9 → 4.8 → 4.7 → 4.6 → 4.5 → 4.4 → 4.3 (deleveraging — strong story)
- `tlc_2023` (exit): flat 4.5 across 4 quarters then closed (held for 4 quarters before exit)

### 4.4 EBITDA bridges

Block 6 is the place where Q3.3's bucketing pays off. Seeded `per_metric_impacts` for `ccf_2026`:

| metric_key | impact_dollars | Routes to bucket |
|---|---|---|
| `denial_rate` | -$420,000 | denial |
| `first_pass_resolution_rate` | -$180,000 | denial |
| `case_mix_index` | +$240,000 | coding |
| `days_in_ar` | -$310,000 | ar_aging |
| `cost_to_collect` | -$95,000 | other |
| `net_collection_rate` | -$220,000 | other (Q4.6 — composite) |

Result: the drag bar shows non-uniform buckets, "Other" is non-zero (so the Q4.6 talking point lands), Self-pay bucket renders at 0% (Decision C from Phase 3), and the dollar totals are realistic for a $50M+ EBITDA hospital system.

### 4.5 Initiatives

3 initiatives across the held deals, deliberately curated to fire the playbook-gap pill:

- `prior_auth_improvement` recorded on `ccf_2026` AND `arr_2025` AND `pma_2024`, all behind plan ≥−15% → **fires PLAYBOOK GAP**
- `coding_cdi_improvement` recorded on `ccf_2026` only, behind plan −20% → single-deal-behind (does NOT fire pill — demonstrates the n_deals ≥ 2 rule honestly)
- `ar_aging_initiative` recorded on `pma_2024`, ahead of plan +12% → ahead

Initiative ids must validate against `get_all_initiatives()` — the seeder reads the library at runtime to pick valid ids, falling back to whatever's actually shipped.

### 4.6 Generated exports

Per held deal: 2-3 placeholder export files written to `canonical_deal_export_path(deal_id, "<filename>", base=base_dir or DEFAULT_DEMO_BASE)`. Files are minimal HTML/CSV/JSON stubs with a header noting "Demo seed file — not a real export." Sizes recorded honestly via `os.stat()`. The deliverables block then lists these as real cards with real download links.

If `write_export_files=False`: still write the `generated_exports` rows but skip the filesystem writes. The deliverables block will show cards but the file-open will 404 — acceptable for "I just want the dashboard to render" smoke runs.

---

## Step 5 — Conflicts and questions list

Same format as PHASE_3_PROPOSAL. Each must be resolved before implementation.

### C1 — Where do the seeded export files actually live?

**Conflict:** `canonical_deal_export_path()` defaults to `/data/exports/` which the seeder must avoid touching by default. Options:

- **C1.a (recommended):** seeder defaults `base_dir` to `tempfile.gettempdir() / "rcm_mc_demo_exports"`. Files survive the demo session, get cleaned up by OS tempdir hygiene. Operator can override.
- **C1.b:** require operator to pass `--export-base /some/path`. No default. More explicit but more friction.

**Question for Andrew:** C1.a or C1.b? Or — if you want the seed-generated files reachable from the demo session at the same paths the dashboard expects, perhaps a `~/.rcm_mc_demo/exports/` default?

### C2 — Should the seeder run `get_or_build_packet()` synchronously?

**Conflict:** Block 6 (EBITDA drag) needs a `DealAnalysisPacket` for the focused-candidate deals. Building one runs the full 12-step packet builder, which can take several seconds per deal.

- **C2.a (recommended):** seeder runs the real builder for the 3 hold deals + the 1 exit deal. Slower (~10-30 sec total) but uses the real pipeline, so block 6 renders against honest data.
- **C2.b:** seeder writes a hand-crafted bridge directly to `analysis_runs` JSON. Faster but the bridge is fake — and we just spent 2 phases enforcing "honest partial wiring." This one violates that principle.

**Recommend C2.a.** Document the slowness; one-time cost.

### C3 — What does "deal_count" actually control?

**Conflict:** the proposed default `deal_count=7` doesn't cleanly map to the 7 named deals in §4.1. If the operator passes `--deal-count 3`, do we keep the first 3 (which would be all `hold`)? The first 3 across stages? Random?

**Recommend:** `deal_count` controls how many of the 7 curated deals are seeded, in order. `deal_count=3` produces `ccf_2026 + arr_2025 + pma_2024` (the 3 hold deals). `deal_count=10` extends the curated list with 3 additional auto-named deals (`extra_001`..`extra_003`) at `sourced` stage. Documented in the docstring.

**Question for Andrew:** OK with this, or prefer `--deal-count` to be removed entirely (always seed all 7 + a constant tail)?

### C4 — Verification commands re-run after seeding

`UI_REWORK_PLAN.md` "Discovered during local testing 2026-04-25" §4 flagged that the `DEMO_CHECKLIST` verification commands were never validated. The seeder should include a `--verify` flag that, post-seed, runs the four verification commands programmatically and prints their output.

**Recommend:** `--verify` is a separate code path that runs after the seed and returns non-zero if any block's expected counts don't match. Becomes the "did the seed work?" sanity check the operator runs the night before a demo.

**Question for Andrew:** include `--verify` in the seeder's first commit, or land it separately as a follow-up?

### C5 — Tests for the seeder itself

**Conflict:** the seeder writes to a SQLite DB; the test should verify the seeded shape produces the expected dashboard render. Two layers:

- **C5.a:** unit test of `seed_demo_db()` that asserts row counts match `SeedResult` (~5 mins to write).
- **C5.b:** integration test that spins up an HTTP server against the seeded DB, fetches `/app?ui=v3`, and asserts the marquee elements (PLAYBOOK GAP pill, Net Leverage row, deliverables card) all render. Closes the loop the contract suite was missing tonight.

**Recommend both, in that order.** C5.a in the seeder commit; C5.b as the next commit so it's separately revertable.

### C6 — Naming: `seed_demo_db` vs `seed` vs `populate_demo_db`?

Bikeshed but worth resolving once:

- `seed_demo_db()` is most explicit about scope.
- `seed()` is shortest but ambiguous (seed what? randomness? a tree?).
- `populate_demo_db()` reads more naturally as a verb-object phrase but is longer.

**Recommend `seed_demo_db()`** to match the file name `rcm_mc/dev/seed.py` — function name is `seed.seed_demo_db()` from import shape.

---

## Step 6 — Estimated commit plan

If C1-C6 are resolved, implementation is roughly:

| Commit | Subject | Approx LOC |
|---|---|---|
| 1 | `feat(dev): seed_demo_db skeleton — guard, signature, SeedResult dataclass` | ~80 |
| 2 | `feat(dev): seed deals + stage history + snapshots (blocks 1-5, 8)` | ~150 |
| 3 | `feat(dev): seed initiative_actuals (block 7)` | ~80 |
| 4 | `feat(dev): seed analysis_runs via get_or_build_packet (block 6)` | ~60 |
| 5 | `feat(dev): seed generated_exports + placeholder files (block 9)` | ~100 |
| 6 | `feat(dev): --verify flag — re-run DEMO_CHECKLIST commands` | ~100 |
| 7 | `test(dev): unit + integration coverage for seed_demo_db` | ~150 |
| 8 | `docs(ui-rework): close out SEEDER_PROPOSAL questions; update DEMO_CHECKLIST` | docs only |

Estimated total: 1-2 working days. Each commit is independently revertable; the contract suite remains 25/25 throughout.

---

## What to read first in the morning

If you only have 5 minutes with coffee, read in this order:

1. **§5 (C1–C6) — the questions.** These are the only places I need a decision; everything else flows from them.
2. **§4.1 (deal names) and §4.5 (initiatives).** These are the curation choices that shape the partner-walkthrough story.
3. **§3.5 (production safety).** Confirm the guard is paranoid enough.

If C1–C6 land in 1-2 quick decisions, implementation can start immediately and the seeder can be in your hands by end-of-day tomorrow.

Sleep well.
