# checklist/

**The diligence orchestration layer a PE analyst uses day-to-day.** 36-item curated DD playbook + stateless status tracker.

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring — "Diligence Checklist + Open Questions Tracker." |
| `items.py` | **Curated 36-item RCM due-diligence checklist.** Organized by phase: screening → benchmarks → predictive → risk → financial → deliverable → manual. Each = partner-readable question + auto-complete metadata. |
| `tracker.py` | **Stateless status computer.** Given a `DealObservations` snapshot (what has/hasn't been run), emits per-item status. No SQLite — observed deal state is source of truth; tracker just derives. |

## Design principle

**Stateless.** No persistence of checklist state — the observed deal state IS the state. If `HCRIS X-Ray` hasn't been run, the item is `OPEN`. Once it runs, the item auto-completes. No "mark as done" button that could drift from reality.

## Phases

1. Screening (pre-LOI, 30-min teaser) — 6 items
2. CCD + benchmarks (Phase 1-2 ingest + KPIs) — 8 items
3. Predictive (Phase 3 — ML + denial prediction + bankruptcy scan) — 6 items
4. Risk (cyber, regulatory, real estate, management) — 8 items
5. Financial (Deal MC + covenant stress + exit timing) — 5 items
6. Deliverable (IC packet, QoE memo, LP update) — 2 items
7. Manual (banker-call notes, reference calls) — 1 item

## Where it plugs in

- **Deal Profile** — checklist status in sidebar
- **Thesis Pipeline** — each step auto-completes its checklist item on success
- **IC Packet** — checklist summary is the opening section of the memo

## Tests

`tests/test_checklist*.py` — stateless-tracker contract + per-phase item coverage.
