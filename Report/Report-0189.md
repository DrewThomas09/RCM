# Report 0189: Dead Code — `engagement/__init__.py` (closes Report 0182 Q2)

## Scope

Dead-code audit on `engagement/` public surface (18 names per `__init__.py:__all__`). **Closes Report 0182 Q2.** Sister to Reports 0099, 0129, 0159 (dead-code audits).

## Findings

### Public API surface — 18 names

Per `__all__`:

| Symbol | External callers |
|---|---|
| `Engagement` (dataclass) | **20 files** |
| `Deliverable` (dataclass) | 8 files |
| `Comment` (dataclass) | 6 files |
| `EngagementRole` (enum) | 5 files |
| `list_deliverables` | 5 files |
| `list_comments` | 6 files |
| `add_member` | 4 files |
| `create_engagement` | 4 files |
| `publish_deliverable` | 3 files |
| `post_comment` | 3 files |
| `list_members` | 3 files |
| `list_engagements` | 3 files |
| `get_engagement` | 3 files |
| `create_deliverable` | 3 files |
| `can_publish` | 2 files |
| `EngagementMember` | 1 file |
| `can_view_draft` | 1 file |
| `remove_member` | 1 file |

**18 of 18 names externally used. ZERO dead code.**

### Hot symbols

- **`Engagement` (20 files)** — dataclass; the highest-fanout symbol in engagement/.
- `Deliverable` (8) and `Comment` (6) — also widely used.

These match Report 0184 finding (6 importers — but each importer uses MULTIPLE engagement symbols, so per-symbol counts are higher).

### Cold symbols (1 file each)

- `EngagementMember` — 1 file
- `can_view_draft` — 1 file
- `remove_member` — 1 file

**3 symbols with single external caller.** Borderline candidates for "deprecated soon" or specialized helpers. **Not dead** but worth monitoring.

### Architectural observation

Per `__init__.py` docstring lines 1-22 (extracted earlier in batch):
> "Engagement model — RBAC, comments, draft/publish flow."
> "engagement role determines WHAT a user can do within one specific engagement (e.g. an ANALYST from another deal cannot publish deliverables on this deal; the client's CLIENT_VIEWER cannot see drafts)"
> "The two layers multiply — both must permit an action."

**Cross-link Report 0073 + 0074 (auth/rbac.py + external_users.py placeholders).** Engagement-level RBAC is implemented while app-level RBAC is placeholder per Report 0073. **Architectural inversion**: feature-layer RBAC built before foundation-layer RBAC.

### Cross-link to Report 0084

Per Report 0084: 13 auth surfaces. Plus engagement-RBAC layer (`can_publish`, `can_view_draft`) — 2 more. **15+ auth-related surfaces total.**

### Comparison vs other dead-code audits

| Module | Dead found |
|---|---|
| `domain/custom_metrics.py` (Report 0099) | 5 unused imports + 1 dead branch |
| `core/distributions.py` (Report 0129) | 0 dead (3 public-named-internal) |
| `extra_red_flags.py` (Report 0159) | 0 dead (10 private rules) |
| **`engagement/__init__.py`** | **0 dead** |

**Engagement is clean.** Cross-link Report 0134 deal_overrides exemplary discipline pattern.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR949** | **0 dead code in engagement/** — 18 of 18 public symbols externally used | (clean) | (clean) |
| **MR950** | **Engagement-RBAC built BEFORE app-level RBAC** (per Report 0073 placeholder) | Architectural inversion. Feature-layer security exists while foundation layer is placeholder. **Should app-level RBAC be prioritized?** | Medium |
| **MR951** | **3 cold symbols (single-importer)**: EngagementMember, can_view_draft, remove_member | Worth monitoring — borderline candidates for "specialized helpers." Not dead. | Low |

## Dependencies

- **Incoming:** 6 importers per Report 0184; 18 public symbols.
- **Outgoing:** stdlib (Report 0185).

## Open questions / Unknowns

None — closes Report 0182 Q2 cleanly.

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0190** | Continue subpackage backlog. |

---

Report/Report-0189.md written.
