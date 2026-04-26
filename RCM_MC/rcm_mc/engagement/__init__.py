"""Engagement model — RBAC, comments, draft/publish flow.

Layers on top of the app-level RBAC in ``rcm_mc.auth.rbac``. An
engagement is the diligence project the deal team is executing
against; it has its own scoped roles (who can publish, who can only
view), comment thread, and draft → published state machine for
deliverables.

Design:
    app role (from auth.rbac) determines WHO can act on the platform
      at all (e.g. VIEWER cannot upload claims)
    engagement role determines WHAT a user can do within one specific
      engagement (e.g. an ANALYST from another deal cannot publish
      deliverables on this deal; the client's CLIENT_VIEWER cannot
      see drafts)

The two layers multiply — both must permit an action. This keeps the
existing app-level RBAC untouched while adding a second dimension
the partner actually cares about (cross-engagement isolation).

Public API::

    from rcm_mc.engagement import (
        Engagement, EngagementMember, EngagementRole,
        create_engagement, add_member, list_members,
        post_comment, list_comments,
        create_deliverable, publish_deliverable,
        can_publish, can_view_draft,
    )

Persists into the existing SQLite ``PortfolioStore``. Tables are
created with ``CREATE TABLE IF NOT EXISTS`` — idempotent.
"""
from __future__ import annotations

from .store import (  # noqa: F401
    Comment,
    Deliverable,
    Engagement,
    EngagementMember,
    EngagementRole,
    add_member,
    can_publish,
    can_view_draft,
    create_deliverable,
    create_engagement,
    get_engagement,
    get_member_role,
    list_comments,
    list_deliverables,
    list_engagements,
    list_members,
    post_comment,
    publish_deliverable,
    remove_member,
)

__all__ = [
    "Comment",
    "Deliverable",
    "Engagement",
    "EngagementMember",
    "EngagementRole",
    "add_member",
    "can_publish",
    "can_view_draft",
    "create_deliverable",
    "create_engagement",
    "get_engagement",
    "get_member_role",
    "list_comments",
    "list_deliverables",
    "list_engagements",
    "list_members",
    "post_comment",
    "publish_deliverable",
    "remove_member",
]
