# engagement/

**Per-engagement RBAC + comments + draft/publish state machine.** Layers on top of the app-level `auth/rbac.py` — an **engagement** is the diligence project a deal team is executing against, with its own scoped roles and state.

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring — "engagement = the diligence project the deal team is executing against." |
| `store.py` | **Single coherent SQLite store** — engagements, members, comments, deliverables all scoped to an `engagement_id`. Deliberately one file: splitting the aggregate adds import churn without clarity. |

## Why one file

The engagement model is a single coherent aggregate — engagements own members, members own comments, deliverables are scoped to engagements. Splitting across files would require `engagement_id` foreign keys across 4+ modules with more import graph for no clarity gain. Kept as one module with well-bounded dataclasses.

## Relationship to `auth/rbac.py`

- `auth.rbac` = **app-level roles** (ADMIN / PARTNER / VP / ASSOCIATE / ANALYST / VIEWER). Enforces access to features platform-wide.
- `engagement` = **per-engagement roles** (lead / reviewer / viewer on a specific diligence project). Scoped to a single engagement.

An analyst with `ANALYST` app-role can be a **lead reviewer** on one engagement and a **viewer only** on another. The engagement layer encodes that per-project permission.

## Draft / publish state machine

Engagements have a `state`:
- `DRAFT` — work-in-progress, visible to engagement members only
- `PUBLISHED` — finalized, visible per app-role (partner + up see all; associates see own)
- `ARCHIVED` — closed, read-only

Transitions are logged in `auth.audit_log` with engagement_id + actor.

## UI

`ui/engagement_pages.py` — 3 HTTP surfaces:
- `/engagements` — list engagements visible to current user
- `/engagements/<id>` — detail page with members + comments + deliverables
- `/engagements/new` — create engagement form

## Tests

`tests/test_engagement*.py` — covers RBAC transitions + state machine + comment threading.
