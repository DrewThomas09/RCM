# Report 0184: Incoming Dep Graph — `engagement/`

## Scope

Maps importers of `engagement/`. Sister to Report 0182 (engagement inventory), 0183 (4 schema tables).

## Findings

### Importers (6 total)

| File | Likely use |
|---|---|
| `tests/test_engagement.py` | direct unit tests |
| `tests/test_engagement_pages.py` | UI render tests |
| `tests/test_qoe_memo.py` | QoE memo references engagement |
| `server.py` | `/engagements/*` routes (per Report 0127) |
| `ui/engagement_pages.py` | UI rendering (NEW unmapped module) |
| `diligence/_pages.py` | cross-package — diligence pages reference engagements |

**6 importers.** Per Report 0094 heuristic ">5 = tight"; **borderline tight.** Healthy fanin for a mid-size workflow subsystem.

### NEW unmapped modules in importer list

- `ui/engagement_pages.py` — never reported
- `diligence/_pages.py` — never reported (and `diligence/` is on Report 0091/0151 unmapped #4)

### Cross-link to Report 0127 + 0157 (feat/ui-rework-v3)

Per Report 0127: branch added `/engagements/...` routes. Per this iteration: 4 SQLite tables + 6 importers. **Engagement is a mid-tier production feature.**

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR940** | **`ui/engagement_pages.py` and `diligence/_pages.py` discovered, never reported** | Add to backlog. Cross-link Report 0181 ~17 never-mentioned subpackages. | Medium |
| **MR941** | **6 importers — borderline tight coupling for a 4-table CRUD layer** | Manageable. Renaming engagement_id PK ripples through 6 callers. | Low |

## Dependencies

- **Incoming:** 6 files (4 production + 3 tests; some overlap counts).
- **Outgoing:** PortfolioStore.

## Open questions / Unknowns

- **Q1.** What does `ui/engagement_pages.py` render?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0185** | Outgoing dep graph (in flight). |

---

Report/Report-0184.md written.
