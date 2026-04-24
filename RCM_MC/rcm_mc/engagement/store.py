"""Engagement SQLite store + role / comment / deliverable primitives.

One module on purpose: the engagement model is a single coherent
aggregate (engagements, members, comments, deliverables are all
scoped to an engagement_id) and splitting them across files adds
import churn without adding clarity.

Persistence model — four tables, all keyed on ``engagement_id``:

    engagements               — one row per deal engagement
    engagement_members        — (engagement_id, username, role)
    engagement_comments       — threaded comments on a target
    engagement_deliverables   — draft / published memos + findings

Every write goes through ``BEGIN IMMEDIATE`` to serialise concurrent
writers (the same pattern used elsewhere in the codebase). All
sensitive writes also append to the audit-log chain via
``rcm_mc.compliance.audit_chain.append_chained_event`` — publication
is a HIPAA-logged event because it changes what's visible to client
viewers.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from ..portfolio.store import PortfolioStore


# ── Roles ──────────────────────────────────────────────────────────

class EngagementRole(str, Enum):
    """Engagement-scoped roles. Orthogonal to the app-level Role.

    - PARTNER: signs the QoE memo; can publish any deliverable; can
      add/remove members; sees drafts.
    - LEAD: managing associate; can publish most deliverables (not
      the partner sign-off block); sees drafts; can add analysts.
    - ANALYST: produces draft deliverables; sees drafts; cannot
      publish or add members.
    - CLIENT_VIEWER: read-only on PUBLISHED deliverables only; never
      sees drafts; never sees comments marked internal.
    """
    PARTNER       = "PARTNER"
    LEAD          = "LEAD"
    ANALYST       = "ANALYST"
    CLIENT_VIEWER = "CLIENT_VIEWER"


_PUBLISH_ALLOWED: Dict[EngagementRole, set] = {
    EngagementRole.PARTNER:       {"QOE_MEMO", "BENCHMARKS",
                                   "WATERFALL", "ROOT_CAUSE",
                                   "ADVISORY"},
    EngagementRole.LEAD:          {"BENCHMARKS", "WATERFALL",
                                   "ROOT_CAUSE", "ADVISORY"},
    EngagementRole.ANALYST:       set(),
    EngagementRole.CLIENT_VIEWER: set(),
}


def can_publish(role: EngagementRole, deliverable_kind: str) -> bool:
    """Return True when ``role`` is authorised to publish
    ``deliverable_kind`` on this engagement. Partner-signed
    deliverables (QOE_MEMO) are PARTNER-only by design."""
    return deliverable_kind.upper() in _PUBLISH_ALLOWED.get(role, set())


def can_view_draft(role: EngagementRole) -> bool:
    """Drafts are hidden from client viewers. Everyone else with any
    engagement role sees drafts."""
    return role in (
        EngagementRole.PARTNER,
        EngagementRole.LEAD,
        EngagementRole.ANALYST,
    )


# ── Dataclasses ────────────────────────────────────────────────────

@dataclass
class Engagement:
    engagement_id: str
    name: str
    client_name: str
    status: str = "ACTIVE"        # ACTIVE | ARCHIVED
    created_at: str = ""
    created_by: str = ""
    closed_at: Optional[str] = None
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class EngagementMember:
    engagement_id: str
    username: str
    role: EngagementRole
    added_at: str = ""
    added_by: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "engagement_id": self.engagement_id,
            "username": self.username,
            "role": self.role.value,
            "added_at": self.added_at,
            "added_by": self.added_by,
        }


@dataclass
class Comment:
    comment_id: int
    engagement_id: str
    target: str                    # e.g. "deliverable:42" or "deal:X"
    author: str
    body: str
    posted_at: str = ""
    is_internal: bool = False      # hidden from CLIENT_VIEWER
    parent_comment_id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class Deliverable:
    deliverable_id: int
    engagement_id: str
    kind: str                      # QOE_MEMO | BENCHMARKS | WATERFALL | ...
    title: str
    status: str = "DRAFT"          # DRAFT | PUBLISHED | RETRACTED
    created_by: str = ""
    created_at: str = ""
    published_by: Optional[str] = None
    published_at: Optional[str] = None
    content_ref: str = ""          # e.g. a packet run_id, a file path
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


# ── Helpers ────────────────────────────────────────────────────────

def _iso_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_tables(store: PortfolioStore) -> None:
    store.init_db()
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS engagements (
                engagement_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                client_name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                created_at TEXT NOT NULL,
                created_by TEXT NOT NULL,
                closed_at TEXT,
                notes TEXT NOT NULL DEFAULT ''
            )"""
        )
        con.execute(
            """CREATE TABLE IF NOT EXISTS engagement_members (
                engagement_id TEXT NOT NULL,
                username TEXT NOT NULL,
                role TEXT NOT NULL,
                added_at TEXT NOT NULL,
                added_by TEXT NOT NULL,
                PRIMARY KEY (engagement_id, username),
                FOREIGN KEY (engagement_id) REFERENCES engagements(engagement_id)
            )"""
        )
        con.execute(
            """CREATE TABLE IF NOT EXISTS engagement_comments (
                comment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                engagement_id TEXT NOT NULL,
                target TEXT NOT NULL,
                author TEXT NOT NULL,
                body TEXT NOT NULL,
                posted_at TEXT NOT NULL,
                is_internal INTEGER NOT NULL DEFAULT 0,
                parent_comment_id INTEGER,
                FOREIGN KEY (engagement_id) REFERENCES engagements(engagement_id)
            )"""
        )
        con.execute(
            """CREATE TABLE IF NOT EXISTS engagement_deliverables (
                deliverable_id INTEGER PRIMARY KEY AUTOINCREMENT,
                engagement_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                title TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'DRAFT',
                created_by TEXT NOT NULL,
                created_at TEXT NOT NULL,
                published_by TEXT,
                published_at TEXT,
                content_ref TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                FOREIGN KEY (engagement_id) REFERENCES engagements(engagement_id)
            )"""
        )
        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_comments_engagement "
            "ON engagement_comments(engagement_id, posted_at DESC)"
        )
        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_deliverables_engagement "
            "ON engagement_deliverables(engagement_id, status)"
        )
        con.commit()


def _audit(
    store: PortfolioStore,
    *,
    actor: str,
    action: str,
    target: str,
    detail: Optional[Dict[str, Any]] = None,
) -> None:
    """Best-effort audit-chain append. Never fails the caller; audit
    log is a detective control, not a pre-condition."""
    try:
        from ..compliance.audit_chain import append_chained_event
        append_chained_event(
            store, actor=actor, action=action, target=target,
            detail=detail,
        )
    except Exception:  # noqa: BLE001
        pass


# ── Engagement CRUD ────────────────────────────────────────────────

def create_engagement(
    store: PortfolioStore,
    *,
    engagement_id: str,
    name: str,
    client_name: str,
    created_by: str,
    notes: str = "",
) -> Engagement:
    _ensure_tables(store)
    now = _iso_utc()
    with store.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        existing = con.execute(
            "SELECT 1 FROM engagements WHERE engagement_id = ?",
            (engagement_id,),
        ).fetchone()
        if existing:
            raise ValueError(
                f"engagement {engagement_id!r} already exists"
            )
        con.execute(
            "INSERT INTO engagements "
            "(engagement_id, name, client_name, status, created_at, "
            " created_by, notes) "
            "VALUES (?, ?, ?, 'ACTIVE', ?, ?, ?)",
            (engagement_id, name, client_name, now, created_by, notes),
        )
        con.commit()
    eng = Engagement(
        engagement_id=engagement_id, name=name, client_name=client_name,
        status="ACTIVE", created_at=now, created_by=created_by, notes=notes,
    )
    _audit(
        store, actor=created_by, action="engagement.create",
        target=engagement_id,
        detail={"name": name, "client_name": client_name},
    )
    return eng


def get_engagement(
    store: PortfolioStore, engagement_id: str,
) -> Optional[Engagement]:
    _ensure_tables(store)
    with store.connect() as con:
        row = con.execute(
            "SELECT engagement_id, name, client_name, status, "
            "created_at, created_by, closed_at, notes "
            "FROM engagements WHERE engagement_id = ?",
            (engagement_id,),
        ).fetchone()
    if row is None:
        return None
    return Engagement(
        engagement_id=row["engagement_id"], name=row["name"],
        client_name=row["client_name"], status=row["status"],
        created_at=row["created_at"], created_by=row["created_by"],
        closed_at=row["closed_at"], notes=row["notes"] or "",
    )


def list_engagements(
    store: PortfolioStore, *, status: Optional[str] = None,
) -> List[Engagement]:
    _ensure_tables(store)
    where, params = "", []
    if status:
        where = "WHERE status = ?"
        params.append(status)
    with store.connect() as con:
        rows = con.execute(
            f"SELECT engagement_id, name, client_name, status, "
            f"created_at, created_by, closed_at, notes "
            f"FROM engagements {where} ORDER BY created_at DESC",
            params,
        ).fetchall()
    return [
        Engagement(
            engagement_id=r["engagement_id"], name=r["name"],
            client_name=r["client_name"], status=r["status"],
            created_at=r["created_at"], created_by=r["created_by"],
            closed_at=r["closed_at"], notes=r["notes"] or "",
        )
        for r in rows
    ]


# ── Members ────────────────────────────────────────────────────────

def add_member(
    store: PortfolioStore,
    *,
    engagement_id: str,
    username: str,
    role: EngagementRole,
    added_by: str,
) -> EngagementMember:
    _ensure_tables(store)
    now = _iso_utc()
    with store.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        # Replace if exists (role update is legitimate).
        con.execute(
            "DELETE FROM engagement_members "
            "WHERE engagement_id = ? AND username = ?",
            (engagement_id, username),
        )
        con.execute(
            "INSERT INTO engagement_members "
            "(engagement_id, username, role, added_at, added_by) "
            "VALUES (?, ?, ?, ?, ?)",
            (engagement_id, username, role.value, now, added_by),
        )
        con.commit()
    _audit(
        store, actor=added_by, action="engagement.member.add",
        target=f"{engagement_id}/{username}",
        detail={"role": role.value},
    )
    return EngagementMember(
        engagement_id=engagement_id, username=username, role=role,
        added_at=now, added_by=added_by,
    )


def remove_member(
    store: PortfolioStore, *,
    engagement_id: str, username: str, removed_by: str,
) -> bool:
    _ensure_tables(store)
    with store.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        cur = con.execute(
            "DELETE FROM engagement_members "
            "WHERE engagement_id = ? AND username = ?",
            (engagement_id, username),
        )
        con.commit()
        removed = cur.rowcount > 0
    if removed:
        _audit(
            store, actor=removed_by, action="engagement.member.remove",
            target=f"{engagement_id}/{username}",
        )
    return removed


def list_members(
    store: PortfolioStore, engagement_id: str,
) -> List[EngagementMember]:
    _ensure_tables(store)
    with store.connect() as con:
        rows = con.execute(
            "SELECT engagement_id, username, role, added_at, added_by "
            "FROM engagement_members WHERE engagement_id = ? "
            "ORDER BY username ASC",
            (engagement_id,),
        ).fetchall()
    return [
        EngagementMember(
            engagement_id=r["engagement_id"], username=r["username"],
            role=EngagementRole(r["role"]),
            added_at=r["added_at"], added_by=r["added_by"],
        )
        for r in rows
    ]


def get_member_role(
    store: PortfolioStore, *,
    engagement_id: str, username: str,
) -> Optional[EngagementRole]:
    _ensure_tables(store)
    with store.connect() as con:
        row = con.execute(
            "SELECT role FROM engagement_members "
            "WHERE engagement_id = ? AND username = ?",
            (engagement_id, username),
        ).fetchone()
    if row is None:
        return None
    return EngagementRole(row["role"])


# ── Comments ───────────────────────────────────────────────────────

def post_comment(
    store: PortfolioStore,
    *,
    engagement_id: str,
    target: str,
    author: str,
    body: str,
    is_internal: bool = False,
    parent_comment_id: Optional[int] = None,
) -> Comment:
    """Authorisation: caller must be an engagement member. Internal
    comments are rejected from CLIENT_VIEWERs (who can never post
    an internal-flagged comment)."""
    _ensure_tables(store)
    role = get_member_role(store, engagement_id=engagement_id,
                           username=author)
    if role is None:
        raise PermissionError(
            f"{author!r} is not a member of {engagement_id!r}"
        )
    if is_internal and role == EngagementRole.CLIENT_VIEWER:
        raise PermissionError(
            "client viewers cannot post internal-flagged comments"
        )
    if not body.strip():
        raise ValueError("comment body cannot be empty")

    now = _iso_utc()
    with store.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        cur = con.execute(
            "INSERT INTO engagement_comments "
            "(engagement_id, target, author, body, posted_at, "
            " is_internal, parent_comment_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (engagement_id, target, author, body, now,
             1 if is_internal else 0, parent_comment_id),
        )
        con.commit()
        cid = int(cur.lastrowid)
    _audit(
        store, actor=author, action="engagement.comment.post",
        target=f"{engagement_id}/{target}",
        detail={"comment_id": cid, "is_internal": is_internal},
    )
    return Comment(
        comment_id=cid, engagement_id=engagement_id, target=target,
        author=author, body=body, posted_at=now,
        is_internal=is_internal, parent_comment_id=parent_comment_id,
    )


def list_comments(
    store: PortfolioStore,
    *,
    engagement_id: str,
    target: Optional[str] = None,
    viewer: Optional[str] = None,
) -> List[Comment]:
    """List comments. When ``viewer`` is provided, filters out
    internal comments for CLIENT_VIEWERs (matches the view-from-the-
    client-portal behaviour)."""
    _ensure_tables(store)
    where, params = ["engagement_id = ?"], [engagement_id]
    if target is not None:
        where.append("target = ?")
        params.append(target)
    with store.connect() as con:
        rows = con.execute(
            f"SELECT comment_id, engagement_id, target, author, body, "
            f"posted_at, is_internal, parent_comment_id "
            f"FROM engagement_comments WHERE {' AND '.join(where)} "
            f"ORDER BY comment_id ASC",
            params,
        ).fetchall()

    viewer_role: Optional[EngagementRole] = None
    if viewer is not None:
        viewer_role = get_member_role(
            store, engagement_id=engagement_id, username=viewer,
        )
    out: List[Comment] = []
    for r in rows:
        c = Comment(
            comment_id=r["comment_id"],
            engagement_id=r["engagement_id"],
            target=r["target"], author=r["author"],
            body=r["body"], posted_at=r["posted_at"],
            is_internal=bool(r["is_internal"]),
            parent_comment_id=r["parent_comment_id"],
        )
        if viewer_role == EngagementRole.CLIENT_VIEWER and c.is_internal:
            continue
        out.append(c)
    return out


# ── Deliverables (draft → published flow) ──────────────────────────

def create_deliverable(
    store: PortfolioStore,
    *,
    engagement_id: str,
    kind: str,
    title: str,
    created_by: str,
    content_ref: str = "",
    notes: str = "",
) -> Deliverable:
    _ensure_tables(store)
    role = get_member_role(store, engagement_id=engagement_id,
                           username=created_by)
    if role is None:
        raise PermissionError(
            f"{created_by!r} is not a member of {engagement_id!r}"
        )
    if role == EngagementRole.CLIENT_VIEWER:
        raise PermissionError(
            "client viewers cannot create deliverables"
        )
    now = _iso_utc()
    with store.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        cur = con.execute(
            "INSERT INTO engagement_deliverables "
            "(engagement_id, kind, title, status, created_by, "
            " created_at, content_ref, notes) "
            "VALUES (?, ?, ?, 'DRAFT', ?, ?, ?, ?)",
            (engagement_id, kind.upper(), title, created_by, now,
             content_ref, notes),
        )
        con.commit()
        did = int(cur.lastrowid)
    _audit(
        store, actor=created_by, action="engagement.deliverable.create",
        target=f"{engagement_id}/{did}",
        detail={"kind": kind.upper(), "title": title},
    )
    return Deliverable(
        deliverable_id=did, engagement_id=engagement_id, kind=kind.upper(),
        title=title, status="DRAFT", created_by=created_by,
        created_at=now, content_ref=content_ref, notes=notes,
    )


def publish_deliverable(
    store: PortfolioStore,
    *,
    engagement_id: str,
    deliverable_id: int,
    published_by: str,
) -> Deliverable:
    """Draft → Published. Caller role must allow publishing the
    specific ``kind`` per :data:`_PUBLISH_ALLOWED`. Audit-logged."""
    _ensure_tables(store)
    role = get_member_role(
        store, engagement_id=engagement_id, username=published_by,
    )
    if role is None:
        raise PermissionError(
            f"{published_by!r} is not a member of {engagement_id!r}"
        )
    now = _iso_utc()
    with store.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        row = con.execute(
            "SELECT kind, status FROM engagement_deliverables "
            "WHERE engagement_id = ? AND deliverable_id = ?",
            (engagement_id, deliverable_id),
        ).fetchone()
        if row is None:
            con.rollback()
            raise LookupError(
                f"deliverable {deliverable_id} not found on "
                f"engagement {engagement_id!r}"
            )
        kind = row["kind"]
        if row["status"] != "DRAFT":
            con.rollback()
            raise ValueError(
                f"only DRAFT deliverables can be published; "
                f"deliverable {deliverable_id} is {row['status']}"
            )
        if not can_publish(role, kind):
            con.rollback()
            raise PermissionError(
                f"role {role.value!r} cannot publish a {kind!r} "
                f"deliverable on {engagement_id!r}"
            )
        con.execute(
            "UPDATE engagement_deliverables "
            "SET status = 'PUBLISHED', published_by = ?, "
            "    published_at = ? "
            "WHERE engagement_id = ? AND deliverable_id = ?",
            (published_by, now, engagement_id, deliverable_id),
        )
        con.commit()
    _audit(
        store, actor=published_by,
        action="engagement.deliverable.publish",
        target=f"{engagement_id}/{deliverable_id}",
        detail={"kind": kind},
    )
    d = _fetch_deliverable(store, engagement_id, deliverable_id)
    assert d is not None
    return d


def list_deliverables(
    store: PortfolioStore,
    *,
    engagement_id: str,
    viewer: Optional[str] = None,
) -> List[Deliverable]:
    """List deliverables. When ``viewer`` is a CLIENT_VIEWER, filters
    out DRAFT deliverables — that's the client-portal view."""
    _ensure_tables(store)
    with store.connect() as con:
        rows = con.execute(
            "SELECT deliverable_id, engagement_id, kind, title, "
            " status, created_by, created_at, published_by, "
            " published_at, content_ref, notes "
            "FROM engagement_deliverables WHERE engagement_id = ? "
            "ORDER BY deliverable_id ASC",
            (engagement_id,),
        ).fetchall()

    viewer_role: Optional[EngagementRole] = None
    if viewer is not None:
        viewer_role = get_member_role(
            store, engagement_id=engagement_id, username=viewer,
        )
    out: List[Deliverable] = []
    for r in rows:
        d = Deliverable(
            deliverable_id=r["deliverable_id"],
            engagement_id=r["engagement_id"], kind=r["kind"],
            title=r["title"], status=r["status"],
            created_by=r["created_by"], created_at=r["created_at"],
            published_by=r["published_by"],
            published_at=r["published_at"],
            content_ref=r["content_ref"] or "",
            notes=r["notes"] or "",
        )
        if (viewer_role == EngagementRole.CLIENT_VIEWER
                and d.status != "PUBLISHED"):
            continue
        out.append(d)
    return out


def _fetch_deliverable(
    store: PortfolioStore,
    engagement_id: str,
    deliverable_id: int,
) -> Optional[Deliverable]:
    _ensure_tables(store)
    with store.connect() as con:
        r = con.execute(
            "SELECT deliverable_id, engagement_id, kind, title, "
            " status, created_by, created_at, published_by, "
            " published_at, content_ref, notes "
            "FROM engagement_deliverables "
            "WHERE engagement_id = ? AND deliverable_id = ?",
            (engagement_id, deliverable_id),
        ).fetchone()
    if r is None:
        return None
    return Deliverable(
        deliverable_id=r["deliverable_id"],
        engagement_id=r["engagement_id"], kind=r["kind"],
        title=r["title"], status=r["status"],
        created_by=r["created_by"], created_at=r["created_at"],
        published_by=r["published_by"],
        published_at=r["published_at"],
        content_ref=r["content_ref"] or "",
        notes=r["notes"] or "",
    )
