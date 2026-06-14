# AGENTS.md — coordination & ownership

Canonical, machine-and-human-readable ownership map for parallel agents
working on this repo. Read this **before** writing code. The detailed
build prompt for the platform-spine agent is
[`SECOND_AGENT_BUILD_PROMPT.md`](SECOND_AGENT_BUILD_PROMPT.md);
conventions are in [`RCM_MC/CLAUDE.md`](RCM_MC/CLAUDE.md).

## The one rule

**One file, one owner.** Agents run in separate git worktrees and never
edit the same file in the same window. Merges happen at branch
integration, never in shared working state.

## Ownership table

| Owner | Directories (own) | Read-only to it |
|---|---|---|
| **Primary agent** — analytics/prediction core + editorial UI sweep | `RCM_MC/rcm_mc/core/`, `ml/`, `mc/`, `montecarlo_v3/`, `scenarios/`, `pe/`, `finance/`, `domain/`, `causal/`, `vbc/`, `vbc_contracts/`, `ui/` (incl. `data_public/`, `chartis/`), `ai/`, `assistant/` | the platform spine below |
| **Platform agent** — ingestion / deliverables / monitoring / app-shell / CI | `RCM_MC/rcm_mc/data/`, `exports/`, `ic_memo/`, `ic_binder/`, `qoe/`, `reports/`, `portfolio_monitor/`, `alerts/`, `portfolio/`, `auth/`, `infra/`, `RCM_MC/tests/`, `.github/workflows/` | the analytics core above |

## Frozen contract

`RCM_MC/rcm_mc/analysis/packet.py` — `DealAnalysisPacket`. The analytics
core **produces** it (`analysis/packet_builder.py`); deliverable /
monitoring / UI layers **consume** it. Neither agent edits the packet
shape or the `MetricSource` ordering mid-run; changing it is a contract
change → pause, agree, then resume.

## Collision points (touch only by agreement)

`RCM_MC/rcm_mc/server.py` route table · `RCM_MC/pyproject.toml` ·
`RCM_MC/rcm_mc/cli.py` · any migration that adds a SQLite table.

## Non-negotiables (from `RCM_MC/CLAUDE.md`)

- Zero new runtime deps without discussion.
- Prediction path stays statistical/ML — **never** an LLM call. LLM use
  is confined to `ai/` + `assistant/` (narrative/QA only).
- Parameterised SQL only; `html.escape()` user strings; timezone-aware
  datetimes; dollars 2dp / pct 1dp / multiples 2dp+`x`.
- Every feature gets `tests/test_<feature>.py`; exercise the real path.
