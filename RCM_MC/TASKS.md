# TASKS — Three-Agent Coordination Ledger

Shared, git-tracked work-allocation ledger for the three PEDesk (RCM-MC)
Claude Code agents. Filesystem isolation (git worktrees) handles *where* each
agent edits; this ledger handles *who is doing what* so work isn't duplicated
and cross-agent requests have a single home.

See [`docs/PEDESK_AGENT3_ARCHITECTURE.md`](docs/PEDESK_AGENT3_ARCHITECTURE.md)
for the full ownership map, frozen-contract surface, and merge sequencing.

## How to use this file

- Before starting work, claim it here (move a row to **In progress** with your
  agent tag).
- Mark **Done** when merged to `main`.
- Need something another agent owns (a dependency, a CI change, a frozen-contract
  change)? File it under **Cross-agent requests** — do not edit another agent's
  directory or a frozen contract silently.
- **Config owner = Agent 2.** All `pyproject.toml`, `.github/workflows/`, and
  root `CLAUDE.md` edits route through Agent 2. No new runtime dependency lands
  without explicit discussion (per `CLAUDE.md`).

## Ownership map (summary)

| Agent | Owns |
|---|---|
| **A1 — analytics/prediction** | `core/ mc/ pe/ rcm/ finance/ scenarios/ analysis/ ml/ causal/` + analytic diligence modules |
| **A2 — ingestion/deliverables/app-shell** *(config owner)* | `data/ data_public/` ingestion, `reports/ exports/ ic_memo/ ic_binder/ portfolio_monitor/ ui/ server.py`, `tests/` + CI |
| **A3 — cross-cutting platform** | `auth/ compliance/ engagement/ integrations/` + new `connectors/ primary_research/ contracts/`, VDR/data-room, deal-pipeline state machine, `infra/secrets.py` |

## In progress

| Owner | Task | Notes |
|---|---|---|
| A3 | Agent-3 architecture + coordination model | This doc + `docs/PEDESK_AGENT3_ARCHITECTURE.md` (Stage 0) |

## Backlog (Agent 3, by stage — see architecture §6)

| Stage | Task | Status |
|---|---|---|
| 1 | Freeze `contracts/` (TenantContext, authorize, audit emit, entitlement, canonical records, classification) | todo |
| 2 | Pool-model tenant scoping + CI lint + ABAC evaluator + ethical-wall ABAC + `infra/secrets.py`; SSO/SCIM seams | todo |
| 3 | 4-tier classification → ABAC/retention; audit trigger + chain-head anchor + verify job; MNPI registers; SOC 2 map update | todo |
| 4 | Connector ACL (adapter/translator/facade) for vendor set; resilience primitives; entitlement enforcement | todo |
| 5 | Expert-call compliance lifecycle + thematic-analysis tracker (non-generative); VDR; deal-stage machine; engagement extensions | todo |

## Cross-agent requests

| From → To | Request | Status |
|---|---|---|
| — | (none yet) | — |
