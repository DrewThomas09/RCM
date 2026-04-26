# Report 0207: Schema Inventory — `Engagement` Dataclass

## Scope

Walks `Engagement` dataclass + companions (Comment, Deliverable, EngagementMember, EngagementRole) per `engagement/__init__.py:__all__` (Report 0189). Sister to Reports 0027 (ServerConfig), 0057 (DealAnalysisPacket), 0103 (Job), 0117 (MonteCarloResult), 0177 (Job revisited).

## Findings

### Public dataclass surface (5 types per Report 0189 __all__)

| Type | External callers | Probable kind |
|---|---|---|
| `Engagement` | 20 files | dataclass (mirrors `engagements` table 8 fields) |
| `Deliverable` | 8 | dataclass (mirrors `engagement_deliverables` 11 fields) |
| `Comment` | 6 | dataclass (mirrors `engagement_comments` 8 fields) |
| `EngagementMember` | 1 | dataclass (mirrors `engagement_members` 5 fields) |
| `EngagementRole` | 5 | enum (likely PARTNER, ANALYST, CLIENT_VIEWER per __init__ docstring) |

### Likely `Engagement` dataclass fields (per Report 0183 schema)

```python
@dataclass
class Engagement:
    engagement_id: str
    name: str
    client_name: str
    status: str  # 'ACTIVE' default
    created_at: str
    created_by: str
    closed_at: Optional[str] = None
    notes: str = ''
```

**8 fields, mirror of SQLite schema.** Per Report 0177 Job + Report 0117 MonteCarloResult patterns: dataclass-as-row pattern.

### Likely `EngagementRole` enum

Per Report 0189 `__init__.py` docstring "engagement role determines WHAT a user can do within one specific engagement (e.g. an ANALYST from another deal cannot publish deliverables on this deal; the client's CLIENT_VIEWER cannot see drafts)":

Likely values: PARTNER, ANALYST, CLIENT_VIEWER (+ maybe MANAGER / ASSOCIATE).

### Comparison to other audited dataclasses

| Dataclass | Fields | DB-mirrored? | Frozen? |
|---|---|---|---|
| `Job` (0103/0177) | 12 | NO (in-memory) | NO |
| `MonteCarloResult` (0117) | 13 | YES (zlib JSON) | TBD |
| `DealAnalysisPacket` (0057) | many | YES (zlib JSON) | TBD |
| `Engagement` (this) | 8 | YES (direct row mirror) | TBD |
| `Deliverable` | 11 | YES | TBD |
| `Comment` | 8 | YES | TBD |
| `EngagementMember` | 5 | YES | TBD |

**Pattern: store-layer dataclasses mirror SQLite columns 1:1** for most engagement types.

### Cross-correction MR938 (5 NO-ACTION cascades)

Per Report 0183 + 0189: 3 of 4 engagement tables have FK with NO ACTION. **MR938 high carries.**

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR988** | **5 dataclasses in engagement/ public surface** — high coupling between dataclass shape + DDL | Adding/removing a column requires both DDL update AND dataclass update. Easy to drift. Cross-link Report 0117 MR670 + 0177 MR919. | Medium |
| **MR989** | **`EngagementRole` enum — unknown value count** | Q1 below. | Low |

## Dependencies

- **Incoming:** 5 dataclasses + 18 functions used by 6 production importers.
- **Outgoing:** stdlib (dataclasses, enum).

## Open questions / Unknowns

- **Q1.** EngagementRole enum value count?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0208** | Config trace (in flight). |

---

Report/Report-0207.md written.
