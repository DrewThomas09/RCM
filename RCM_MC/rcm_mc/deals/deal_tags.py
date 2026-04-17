"""Deal tags (Brick 86).

Stage + covenant are authoritative but narrow. PE firms also slice the
portfolio by analyst-defined cohorts:

- **Investment thesis**: "growth", "roll-up", "core", "turnaround"
- **Ownership chunk**: "fund_3", "co_invest"
- **Watchlist**: "watch", "board_flag"
- **Geography**: "region:tx", "market:chicago"
- **Lead analyst**: "owner:AT"

Tags are freeform strings — no taxonomy enforcement. A deal can carry
multiple tags; tags are shared across deals. Analysts add/remove at the
deal-detail page or via REST.

Deliberate scope:
- **Unique constraint** on (deal_id, tag) — adding an existing tag no-ops.
- **Case-insensitive** storage (lowercased on insert) so "Growth" and
  "growth" collapse to one value.
- **No hierarchy / color scheme**. Tags are pure labels. UI may choose
  to color "watch*" tags amber but that's a view decision.

Public API:
    add_tag(store, deal_id, tag) -> bool       (False if already tagged)
    remove_tag(store, deal_id, tag) -> bool    (False if wasn't tagged)
    tags_for(store, deal_id) -> list[str]
    deals_by_tag(store, tag) -> list[str]
    all_tags(store) -> list[(tag, count)]
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import List, Tuple

from ..portfolio.store import PortfolioStore


# Rules for a "valid" tag string. Keeping them narrow so tags stay readable:
# lowercase letters, digits, dash, underscore, colon. Up to 40 chars.
# Rejects spaces → forces analyst to pick a canonical form (``watch_list`` not
# ``watch list``).
_TAG_RE = re.compile(r"^[a-z0-9][a-z0-9_:.-]{0,39}$")


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize(tag: str) -> str:
    """Lowercased + trimmed. Raises ValueError on empty / invalid tags."""
    if tag is None:
        raise ValueError("tag cannot be None")
    t = str(tag).strip().lower()
    if not t:
        raise ValueError("tag cannot be empty")
    if not _TAG_RE.match(t):
        raise ValueError(
            f"invalid tag {tag!r}: use lowercase letters, digits, dash, "
            "underscore, colon, period (no spaces, max 40 chars, must start alnum)"
        )
    return t


def _ensure_tags_table(store: PortfolioStore) -> None:
    """Create deal_tags table if absent. Idempotent."""
    store.init_db()
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS deal_tags (
                tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
                deal_id TEXT NOT NULL,
                tag TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(deal_id) REFERENCES deals(deal_id)
            )"""
        )
        con.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_deal_tags_unique "
            "ON deal_tags(deal_id, tag)"
        )
        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_deal_tags_tag ON deal_tags(tag)"
        )
        con.commit()


def add_tag(store: PortfolioStore, deal_id: str, tag: str) -> bool:
    """Add a tag to a deal. Returns True if newly added, False if already there."""
    t = _normalize(tag)
    _ensure_tags_table(store)
    store.upsert_deal(deal_id)
    with store.connect() as con:
        # Idempotent: INSERT OR IGNORE on the unique (deal_id, tag) index
        cur = con.execute(
            "INSERT OR IGNORE INTO deal_tags (deal_id, tag, created_at) "
            "VALUES (?, ?, ?)",
            (deal_id, t, _utcnow()),
        )
        con.commit()
        return cur.rowcount > 0


def remove_tag(store: PortfolioStore, deal_id: str, tag: str) -> bool:
    """Remove a tag from a deal. Returns True if a row was deleted."""
    t = _normalize(tag)
    _ensure_tags_table(store)
    with store.connect() as con:
        cur = con.execute(
            "DELETE FROM deal_tags WHERE deal_id = ? AND tag = ?",
            (deal_id, t),
        )
        con.commit()
        return cur.rowcount > 0


def tags_for(store: PortfolioStore, deal_id: str) -> List[str]:
    """Tags on one deal, alpha-sorted."""
    _ensure_tags_table(store)
    with store.connect() as con:
        rows = con.execute(
            "SELECT tag FROM deal_tags WHERE deal_id = ? ORDER BY tag",
            (deal_id,),
        ).fetchall()
    return [r["tag"] for r in rows]


def deals_by_tag(store: PortfolioStore, tag: str) -> List[str]:
    """Deal IDs carrying ``tag``, alpha-sorted."""
    t = _normalize(tag)
    _ensure_tags_table(store)
    with store.connect() as con:
        rows = con.execute(
            "SELECT DISTINCT deal_id FROM deal_tags WHERE tag = ? ORDER BY deal_id",
            (t,),
        ).fetchall()
    return [r["deal_id"] for r in rows]


def all_tags(store: PortfolioStore) -> List[Tuple[str, int]]:
    """Portfolio-wide tag usage counts, most-used-first."""
    _ensure_tags_table(store)
    with store.connect() as con:
        rows = con.execute(
            "SELECT tag, COUNT(*) AS c FROM deal_tags GROUP BY tag "
            "ORDER BY c DESC, tag ASC"
        ).fetchall()
    return [(r["tag"], int(r["c"])) for r in rows]
