"""SQLite schema + idempotent upserts for the RxNorm vertical slice.

Tables owned by this connector (and nothing else):
  * ``xwalk_ndc_rxcui``     — the NDC→RxCUI crosswalk (the spine other sources
                              join to). Keyed by canonical ``ndc_11``.
  * ``dim_rxnorm_concept``  — the concept universe with status + remap target.
  * ``bridge_rxcui_related``— ingredient/brand/clinical/branded relationships.
  * ``dim_drug_class``      — ATC / therapeutic / mechanism-of-action grouping.
  * ``dim_ndc_properties``  — optional packaging / labeler detail.

Idempotency is the rule, never a blind append: every write is an
``INSERT OR REPLACE`` (upsert) keyed by ``ndc_11`` or ``rxcui`` (+ the natural
secondary key on the bridge/class tables) so re-running a batch — or resuming
after a hard kill — converges to the same state instead of duplicating rows.

Mirrors the repo's loader convention: ``_ensure_*`` for CREATE-IF-NOT-EXISTS,
a ``store`` with ``init_db()`` / ``connect()``, ``BEGIN IMMEDIATE`` around the
check-then-write, parameterised SQL only.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from .normalize import ConceptRow, DrugClassRow


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Schema ─────────────────────────────────────────────────────────────────

def ensure_tables(con: Any) -> None:
    """Idempotent CREATE for all five RxNorm tables + their indexes."""
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS xwalk_ndc_rxcui (
            ndc_11   TEXT NOT NULL,
            ndc_raw  TEXT NOT NULL,
            rxcui    TEXT NOT NULL,
            status   TEXT NOT NULL DEFAULT 'active',
            loaded_at TEXT NOT NULL,
            PRIMARY KEY (ndc_11)
        )
        """
    )
    con.execute("CREATE INDEX IF NOT EXISTS idx_xwalk_rxcui "
                "ON xwalk_ndc_rxcui(rxcui)")

    con.execute(
        """
        CREATE TABLE IF NOT EXISTS dim_rxnorm_concept (
            rxcui            TEXT NOT NULL,
            name             TEXT,
            tty              TEXT,
            status           TEXT NOT NULL DEFAULT 'active',
            remapped_to_rxcui TEXT DEFAULT '',
            loaded_at        TEXT NOT NULL,
            PRIMARY KEY (rxcui)
        )
        """
    )
    con.execute("CREATE INDEX IF NOT EXISTS idx_concept_status "
                "ON dim_rxnorm_concept(status)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_concept_tty "
                "ON dim_rxnorm_concept(tty)")

    con.execute(
        """
        CREATE TABLE IF NOT EXISTS bridge_rxcui_related (
            rxcui         TEXT NOT NULL,
            related_rxcui TEXT NOT NULL,
            relationship  TEXT NOT NULL,
            loaded_at     TEXT NOT NULL,
            PRIMARY KEY (rxcui, related_rxcui, relationship)
        )
        """
    )
    con.execute("CREATE INDEX IF NOT EXISTS idx_bridge_related "
                "ON bridge_rxcui_related(related_rxcui)")

    con.execute(
        """
        CREATE TABLE IF NOT EXISTS dim_drug_class (
            rxcui      TEXT NOT NULL,
            class_id   TEXT NOT NULL,
            class_name TEXT,
            class_type TEXT NOT NULL,
            loaded_at  TEXT NOT NULL,
            PRIMARY KEY (rxcui, class_id)
        )
        """
    )
    con.execute("CREATE INDEX IF NOT EXISTS idx_class_type "
                "ON dim_drug_class(class_type)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_class_id "
                "ON dim_drug_class(class_id)")

    con.execute(
        """
        CREATE TABLE IF NOT EXISTS dim_ndc_properties (
            ndc_11      TEXT NOT NULL,
            ndc_raw     TEXT,
            rxcui       TEXT,
            labeler     TEXT,
            packaging   TEXT,
            status      TEXT,
            loaded_at   TEXT NOT NULL,
            PRIMARY KEY (ndc_11)
        )
        """
    )


# ── Upserts (idempotent; keyed, never blind-append) ─────────────────────────

def upsert_concepts(store: Any, rows: Iterable[ConceptRow]) -> int:
    store.init_db()
    now = _utcnow()
    n = 0
    with store.connect() as con:
        ensure_tables(con)
        con.execute("BEGIN IMMEDIATE")
        try:
            for r in rows:
                con.execute(
                    "INSERT OR REPLACE INTO dim_rxnorm_concept "
                    "(rxcui, name, tty, status, remapped_to_rxcui, loaded_at) "
                    "VALUES (?,?,?,?,?,?)",
                    (r.rxcui, r.name, r.tty, r.status,
                     r.remapped_to_rxcui, now),
                )
                n += 1
            con.commit()
        except Exception:
            con.rollback()
            raise
    return n


def upsert_crosswalk(store: Any, rows: Iterable[Dict[str, str]]) -> int:
    """Upsert NDC→RxCUI rows. Each row: {ndc_11, ndc_raw, rxcui, status}.

    Keyed by ``ndc_11`` so the many-to-one (many NDCs → one current RxCUI)
    relationship is enforced and re-resolving an NDC overwrites in place.
    """
    store.init_db()
    now = _utcnow()
    n = 0
    with store.connect() as con:
        ensure_tables(con)
        con.execute("BEGIN IMMEDIATE")
        try:
            for r in rows:
                ndc_11 = str(r.get("ndc_11", "")).strip()
                rxcui = str(r.get("rxcui", "")).strip()
                if not ndc_11 or not rxcui:
                    continue
                con.execute(
                    "INSERT OR REPLACE INTO xwalk_ndc_rxcui "
                    "(ndc_11, ndc_raw, rxcui, status, loaded_at) "
                    "VALUES (?,?,?,?,?)",
                    (ndc_11, str(r.get("ndc_raw", "")), rxcui,
                     str(r.get("status", "active")), now),
                )
                n += 1
            con.commit()
        except Exception:
            con.rollback()
            raise
    return n


def upsert_related(store: Any, rxcui: str,
                   triples: Iterable) -> int:
    """Upsert relationship edges for one source rxcui.

    ``triples`` are ``(related_rxcui, tty, relationship)`` from
    :func:`normalize.parse_related`.
    """
    store.init_db()
    now = _utcnow()
    n = 0
    with store.connect() as con:
        ensure_tables(con)
        con.execute("BEGIN IMMEDIATE")
        try:
            for related_rxcui, _tty, relationship in triples:
                if not related_rxcui or related_rxcui == rxcui:
                    continue
                con.execute(
                    "INSERT OR REPLACE INTO bridge_rxcui_related "
                    "(rxcui, related_rxcui, relationship, loaded_at) "
                    "VALUES (?,?,?,?)",
                    (str(rxcui), str(related_rxcui), str(relationship), now),
                )
                n += 1
            con.commit()
        except Exception:
            con.rollback()
            raise
    return n


def upsert_drug_classes(store: Any, rows: Iterable[DrugClassRow]) -> int:
    store.init_db()
    now = _utcnow()
    n = 0
    with store.connect() as con:
        ensure_tables(con)
        con.execute("BEGIN IMMEDIATE")
        try:
            for r in rows:
                con.execute(
                    "INSERT OR REPLACE INTO dim_drug_class "
                    "(rxcui, class_id, class_name, class_type, loaded_at) "
                    "VALUES (?,?,?,?,?)",
                    (r.rxcui, r.class_id, r.class_name, r.class_type, now),
                )
                n += 1
            con.commit()
        except Exception:
            con.rollback()
            raise
    return n


def upsert_ndc_properties(store: Any, rows: Iterable[Dict[str, str]]) -> int:
    store.init_db()
    now = _utcnow()
    n = 0
    with store.connect() as con:
        ensure_tables(con)
        con.execute("BEGIN IMMEDIATE")
        try:
            for r in rows:
                ndc_11 = str(r.get("ndc_11", "")).strip()
                if not ndc_11:
                    continue
                con.execute(
                    "INSERT OR REPLACE INTO dim_ndc_properties "
                    "(ndc_11, ndc_raw, rxcui, labeler, packaging, status, loaded_at) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (ndc_11, str(r.get("ndc_raw", "")), str(r.get("rxcui", "")),
                     str(r.get("labeler", "")), str(r.get("packaging", "")),
                     str(r.get("status", "")), now),
                )
                n += 1
            con.commit()
        except Exception:
            con.rollback()
            raise
    return n


# ── Read helpers ────────────────────────────────────────────────────────────

def resolve_rxcui(store: Any, rxcui: str, *, _depth: int = 0) -> Optional[Dict[str, Any]]:
    """Resolve a (possibly retired/remapped) rxcui to its current concept.

    Joins must resolve *through* remaps so a stale code does not drop a record.
    Follows ``remapped_to_rxcui`` until it reaches an active concept (or a
    remap chain dead-end), with a depth guard against pathological cycles.
    """
    if not rxcui or _depth > 8:
        return None
    with store.connect() as con:
        ensure_tables(con)
        row = con.execute(
            "SELECT * FROM dim_rxnorm_concept WHERE rxcui = ?", (str(rxcui),)
        ).fetchone()
    if row is None:
        return None
    rec = dict(row)
    if rec.get("status") == "remapped" and rec.get("remapped_to_rxcui"):
        nxt = resolve_rxcui(store, rec["remapped_to_rxcui"], _depth=_depth + 1)
        if nxt is not None:
            return nxt
    return rec


def lookup_ndc(store: Any, ndc_11: str) -> Optional[Dict[str, Any]]:
    """Crosswalk lookup by canonical NDC, resolved through remaps."""
    with store.connect() as con:
        ensure_tables(con)
        row = con.execute(
            "SELECT * FROM xwalk_ndc_rxcui WHERE ndc_11 = ?", (str(ndc_11),)
        ).fetchone()
    if row is None:
        return None
    rec = dict(row)
    current = resolve_rxcui(store, rec["rxcui"])
    if current is not None:
        rec["current_rxcui"] = current["rxcui"]
        rec["current_name"] = current.get("name", "")
    else:
        rec["current_rxcui"] = rec["rxcui"]
        rec["current_name"] = ""
    return rec


def counts(store: Any) -> Dict[str, int]:
    """Cumulative row counts per table (for STATE.md / coverage reporting)."""
    out: Dict[str, int] = {}
    tables = ["xwalk_ndc_rxcui", "dim_rxnorm_concept", "bridge_rxcui_related",
              "dim_drug_class", "dim_ndc_properties"]
    with store.connect() as con:
        ensure_tables(con)
        for t in tables:
            out[t] = con.execute(f"SELECT COUNT(*) AS n FROM {t}").fetchone()["n"]
    return out


def class_coverage(store: Any) -> Dict[str, Any]:
    """Drug-class coverage: share of concepts with ≥1 class, by class_type."""
    with store.connect() as con:
        ensure_tables(con)
        total = con.execute(
            "SELECT COUNT(*) AS n FROM dim_rxnorm_concept"
        ).fetchone()["n"]
        classified = con.execute(
            "SELECT COUNT(DISTINCT rxcui) AS n FROM dim_drug_class"
        ).fetchone()["n"]
        by_type = con.execute(
            "SELECT class_type, COUNT(DISTINCT rxcui) AS n "
            "FROM dim_drug_class GROUP BY class_type"
        ).fetchall()
    pct = round(100.0 * classified / total, 2) if total else 0.0
    return {
        "concepts": total,
        "classified_rxcui": classified,
        "coverage_pct": pct,
        "by_class_type": {r["class_type"]: r["n"] for r in by_type},
    }
