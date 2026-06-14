# Second Agent Build Prompt — RCM-MC / PEDesk

**Purpose:** stand up a *second* Claude Code agent that builds in
parallel with the primary agent without ever editing the same files.
This document is the build prompt you hand that agent. It is grounded
in the **actual** RCM-MC tree (1,789 Python modules, 2,878 passing
tests), not a greenfield `src/` scheme — every path below exists today.

Paired reading (do not duplicate their content, inherit it):
- [`RCM_MC/CLAUDE.md`](RCM_MC/CLAUDE.md) — conventions (authoritative).
- [`RCM_MC/readME/13_Build_Status.md`](RCM_MC/readME/13_Build_Status.md) — the open-gap scorecard.
- [`B11_SWEEP_HANDOFF.md`](B11_SWEEP_HANDOFF.md) — the primary agent's active sweep (do not touch its pages).

---

## 1. The one rule that makes this work

**One file, one owner.** The two agents run in separate git worktrees
and never edit the same file in the same window. Merges happen at branch
integration, never in shared working state. If both agents repeatedly
need the same module, the boundary is wrong — re-cut it before writing
more code.

Two corollaries, taken straight from how this repo already works:

- **The contract is frozen during parallel runs.** The shared interface
  (see §3) is changed only by agreement and only between runs, never
  mid-flight.
- **The prediction path stays statistical/ML — never LLM.** Ridge +
  conformal intervals (`rcm_mc/ml/`), isolation forest / changepoint
  (`rcm_mc/qoe/`, `rcm_mc/analysis/anomaly_detection.py`), two-source
  Monte Carlo (`rcm_mc/mc/`). The second agent must **not** introduce an
  LLM call into the prediction or numeric pipeline. LLM use stays
  confined to `rcm_mc/ai/` and `rcm_mc/assistant/` (narrative/QA only),
  which the second agent does not own.

---

## 2. Directory ownership

The primary agent owns the **analytics / prediction core** and the
**editorial UI sweep**. The second agent owns the **platform spine** —
ingestion freshness, deliverable production, monitoring/alerting, and
CI/observability. The split is by directory, enforced by worktree.

### Primary agent owns (second agent: read-only)

| Area | Paths |
|---|---|
| Prediction & simulation core | `rcm_mc/core/`, `rcm_mc/ml/`, `rcm_mc/mc/`, `rcm_mc/montecarlo_v3/`, `rcm_mc/scenarios/` |
| PE / domain math | `rcm_mc/pe/`, `rcm_mc/finance/`, `rcm_mc/domain/`, `rcm_mc/causal/`, `rcm_mc/vbc/`, `rcm_mc/vbc_contracts/` |
| Editorial UI sweep | `rcm_mc/ui/` (incl. `data_public/`, `chartis/`) — the B11 sweep |
| LLM narrative | `rcm_mc/ai/`, `rcm_mc/assistant/` |

### Second agent owns (primary agent: read-only)

| Layer | Paths | Current state → next action (from `13_Build_Status.md`) |
|---|---|---|
| **1. Ingestion freshness** | `rcm_mc/data/` loaders (`cms_hcris.py`, `hcris_incremental.py`, `cms_pos.py`, `cms_ma_enrollment.py`, `cms_utilization.py`, `cms_care_compare.py`, `nppes_infusion.py`, …), `rcm_mc/data/data_refresh.py`, `pipeline.py` | Loaders **ship**. Gap: *automate HCRIS refresh end-to-end* — watermark-based idempotent incremental loads, MERGE on natural keys, suppression-aware validation. |
| **2. Deliverable production** | `rcm_mc/exports/` (`packet_renderer.py`, `ic_packet.py`, `qoe_memo.py`, `diligence_package.py`, `lp_quarterly_report.py`, `xlsx_*`), `rcm_mc/ic_memo/`, `rcm_mc/ic_binder/`, `rcm_mc/qoe/`, `rcm_mc/reports/` | Packet renderer **ships**. Gap: *real `python-docx`/`python-pptx`* behind a feature flag; provenance-by-construction (every exhibit carries a source line). |
| **3. Monitoring & alerting** | `rcm_mc/portfolio_monitor/` (`dashboard.py`, `snapshot.py`, `variance.py`), `rcm_mc/alerts/`, `rcm_mc/portfolio/` | Ships. Gap: *exception-based alerting* fed by the primary agent's changepoint/anomaly outputs against variance-to-plan thresholds; RAG board-review surface. |
| **4. App shell / roles** | `rcm_mc/server.py`, `rcm_mc/auth/`, route wiring (NOT page bodies) | Ships. Gap: *session persistence across restart*; role-based nav (Chartis EMs vs external PE partners). |
| **5. CI / observability / infra** | `.github/workflows/`, `rcm_mc/infra/`, `tests/`, `AZURE_DEPLOY.md`/`DEPLOYMENT_PLAN.md` | Gap: *structured per-request logging*; golden-file tests for generated docs; idempotency reconciliation tests. |

**Collision points (touch only by agreement):** `rcm_mc/server.py`
route table, `pyproject.toml`, `rcm_mc/cli.py`, any migration that adds a
table. If a task needs one of these, coordinate first.

---

## 3. The frozen contract

The shared interface between the two agents is **not** a new
`src/contracts/` package — it already exists and is load-bearing:

> **`rcm_mc/analysis/packet.py` — `DealAnalysisPacket`.**
> "UI routes, API endpoints, and exports render from *this* object —
> nothing renders independently. If a number shows up on a page, it came
> from here."

- The **analytics core** (primary agent) *produces* the packet via
  `rcm_mc/analysis/packet_builder.py`, cached in the `analysis_runs`
  table.
- The **deliverable / monitoring / UI** layers (second agent) *consume*
  the packet — they read its sections, never recompute numbers.
- The packet is fully `to_json`/`from_json` round-trippable; every
  metric carries a `MetricSource` provenance enum
  (`OBSERVED > CCD > EXTRACTED > AUTO_POPULATED > PREDICTED > BENCHMARK`).

**Freeze rule:** the `DealAnalysisPacket` dataclass shape and the
`MetricSource` ordering are the API boundary. The second agent does not
edit `packet.py` or `packet_builder.py`. If a deliverable needs a field
the packet doesn't expose, that is a **contract change** → pause, raise
it, let the primary agent add the field, then resume.

---

## 4. Coordination mechanics

- **Worktrees.** Run the second agent in its own worktree
  (`claude --worktree platform`, or `git worktree add`). Add
  `.claude/worktrees/` to `.gitignore` if not already. Use a
  `.worktreeinclude` to copy untracked `.env`/db files into the
  worktree.
- **Branch.** All second-agent work lands on
  `claude/pedesk-rcm-second-agent-9o7ud7` (this branch). Never push to
  the primary agent's branch.
- **One-PR-per-fix.** This repo's workflow is one focused change per PR
  with an in-depth description (see any B11 PR). Keep
  `git diff --stat` to the owned files only.
- **Status checkpoint.** Update the relevant `13_Build_Status.md` row's
  "next action" as each gap closes, so the scorecard reflects live
  state.

---

## 5. Conventions inherited from `CLAUDE.md` (non-negotiable)

These already govern the codebase; the second agent does not get to
relax them:

- **Zero new runtime dependencies** without explicit discussion. `pandas`
  + `numpy` + `matplotlib` are the only runtime deps beyond stdlib. The
  `python-docx`/`python-pptx` deliverable upgrade is the one place this
  may need a conversation — gate it behind a feature flag and a graceful
  fallback to the current HTML/string renderer, so the default install
  stays dependency-free.
- **Parameterised SQL only**; `BEGIN IMMEDIATE` around check-then-write;
  pick a delete behavior deliberately from the delete-policy matrix.
- **`html.escape()` every user-supplied string**; respect the documented
  `ck_kpi_block` exemption.
- **Number formatting:** dollars 2dp, percentages 1dp, multiples 2dp+`x`,
  dates ISO-like, times UTC ISO.
- **Datetimes timezone-aware** (`datetime.now(timezone.utc)`).
- **Tests:** every feature gets `tests/test_<feature>.py`; exercise the
  real path (no mocks for our own code); order-independent; multi-step
  workflows tested end-to-end over a real HTTP server on a free port.
- **UI (if a route surface is needed):** render through `chartis_shell`
  + `ck_page_title`; never bespoke HTML; add palette/nav entries.

---

## 6. Staged plan

**Stage 0 — Set up isolation.** Create the worktree, confirm the branch,
read `CLAUDE.md` + `13_Build_Status.md` + this doc. Verify no file
overlap with the primary agent's active sweep (`B11_SWEEP_HANDOFF.md`
lists its in-flight pages — all under `ui/data_public/`).

**Stage 1 — Ingestion freshness (unblocks everything).** Automate the
HCRIS refresh end-to-end in `rcm_mc/data/`: poll the CMS quarterly
release, compare file hash/last-modified against a stored watermark,
join NMRC/ALPHA → RPT on `RPT_REC_NUM`, MERGE on
`(CCN, fiscal_year_end, report_status)` keeping the highest-status
report, chunked reads + Parquet intermediates for the >2GB files,
suppression-aware validation (cells ≤10/11). **Done = re-running a
loader produces zero row changes and passes record-count
reconciliation.** Golden-test each loader.

**Stage 2 — Deliverable production against the frozen packet.**
Template-driven `.docx`/`.pptx` behind a feature flag in
`rcm_mc/exports/`; provenance enforced by construction (single
`add_exhibit()` helper renders chart **and** its source line every time;
matplotlib → `BytesIO` → `add_picture` with `buffer.seek(0)`).
Encapsulate the library limitations once (pptx has no native small-caps;
docx has no native footnotes) so they are not re-derived per deliverable.
Red-flag interim deliverable = condensed risk-quantification template.

**Stage 3 — Monitoring & alerting.** Exception-based alerts in
`rcm_mc/portfolio_monitor/` + `rcm_mc/alerts/` fed by the primary agent's
changepoint/anomaly outputs against variance-to-plan thresholds (RCM KPI
benchmarks are directional — Days-in-AR <40, clean-claim ~95–98%, denial
5–10% with <5% optimal; treat as configurable thresholds, not
universals). RAG board-review surface.

**Stage 4 — App shell + CI/observability.** Role-based nav, session
persistence across restart, structured per-request logging in
`rcm_mc/infra/`. GitHub Actions with least-privilege per-job permissions,
token caps, secret scrubbing; golden-file tests for generated documents.

**Stage 5 — Integrate.** Merge the worktree branch; resolve conflicts by
each side's intent; only now unfreeze the contract if a field was
genuinely missing.

---

## 7. Caveats (carried from the research)

- CMS dataset cadences/formats change (NPPES V.1 retired March 2026; PDC
  distribution IDs change every refresh; HCRIS quarterly full overwrite).
  The pipeline must **detect** format/version changes, not assume
  stability.
- KPI/RCM benchmarks (HFMA MAP Keys, MGMA DataDive) vary by specialty and
  payer mix — directional thresholds, configurable per deal.
- `python-pptx`/`python-docx` limitations are real (no native small-caps
  in pptx; no native footnotes in docx) — design around them in helpers.
- IC-memo format varies by firm (Word vs PPT vs hybrid; page counts) —
  keep the template configurable, not fixed.
