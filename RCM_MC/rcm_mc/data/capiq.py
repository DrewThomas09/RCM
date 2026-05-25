"""Capital IQ export ingestion + entity resolution to CMS facilities.

This module consumes Capital IQ / NetAdvantage **exports the user produced
under their own S&P Global license** — it reads files you provide (CSV/Excel
saved from the Screening tool or the Office plug-in). It deliberately does
**not** extract data from S&P, circumvent export caps, or drive the plug-in:
bulk/automated extraction and any redistribution entitlement are a licensing
question that lives outside this code (e.g. an Xpressfeed data-feed license).

What it *does* do is the load-bearing, license-clean part of the data
architecture:

  1. Parse a CapIQ target/transaction export with flexible column mapping
     (CapIQ column headers vary by template).
  2. Resolve each company to a CMS Medicare **CCN** by fuzzy name match against
     HCRIS, with an explicit **confidence** and a status of
     ``RESOLVED`` / ``AMBIGUOUS`` / ``UNMATCHED``. Ambiguity is *surfaced,
     never silently guessed* — a diligence tool must not pick the wrong
     "Memorial Hospital" (mirrors ``intake._resolve_name_to_ccn``).
  3. **Fill operational gaps with CMS public data**: a resolved CCN is enriched
     from the HCRIS facility profile (beds, operating margin, payer-day mix,
     net patient revenue) that the financial export does not carry.

The CapIQ-derived fields stay tagged with their source so downstream surfaces
(and the Guide) can honestly say which numbers are licensed-commercial vs CMS
-public — consistent with the Diligence honesty reform.
"""
from __future__ import annotations

import csv
import difflib
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


# ── Flexible column mapping ──────────────────────────────────────────────
# CapIQ export headers vary by template; accept the common variants. First
# present wins. All matching is case-insensitive on the stripped header.
_COL_ID = ("iq_company_id", "company id", "capiq id", "ciq id", "id")
_COL_NAME = ("company name", "target name", "company", "target", "name",
             "issuer name")
_COL_STATE = ("state", "state/province", "hq state", "geography")
_COL_SECTOR = ("industry", "gics sub-industry", "sector",
               "capital iq industry", "primary industry")
_COL_EV = ("total enterprise value", "tev", "enterprise value", "ev")
_COL_EBITDA = ("ebitda", "ltm ebitda", "ebitda ($mm)")
_COL_EV_EBITDA = ("tev/ebitda", "ev/ebitda", "tev/ltm ebitda")
_COL_DEAL_DATE = ("closed date", "announced date", "transaction date", "date")


class ResolutionStatus(str, Enum):
    """Outcome of matching a CapIQ company to a CMS CCN."""
    RESOLVED = "resolved"      # one clean, confident match
    AMBIGUOUS = "ambiguous"    # several plausible — needs a human pick
    UNMATCHED = "unmatched"    # no CMS facility (e.g. non-hospital target)


@dataclass
class CapIQRecord:
    """One row of a CapIQ export. ``raw`` keeps every original column so no
    licensed field is silently dropped during downstream use."""
    capiq_id: str
    company_name: str
    state: Optional[str] = None
    sector: Optional[str] = None
    ev_mm: Optional[float] = None
    ebitda_mm: Optional[float] = None
    ev_ebitda: Optional[float] = None
    deal_date: Optional[str] = None
    raw: Dict[str, str] = field(default_factory=dict)


@dataclass
class CcnCandidate:
    ccn: str
    name: str
    state: Optional[str]
    score: float            # 0..1 SequenceMatcher ratio vs the query name


@dataclass
class EntityResolution:
    """A CapIQ company mapped (or not) to a CMS CCN. ``source='capiq+cms'``
    once enriched; ``candidates`` is populated only when AMBIGUOUS so a
    reviewer can pick without re-querying."""
    capiq_id: str
    company_name: str
    status: ResolutionStatus
    ccn: Optional[str] = None
    confidence: float = 0.0
    candidates: List[CcnCandidate] = field(default_factory=list)


def _first_present(row: Dict[str, str], candidates) -> Optional[str]:
    """Return the first non-empty value whose (lowercased) header matches a
    candidate. Headers are matched case-insensitively and whitespace-trimmed."""
    lowered = {str(k).strip().lower(): v for k, v in row.items()}
    for cand in candidates:
        v = lowered.get(cand)
        if v is not None and str(v).strip():
            return str(v).strip()
    return None


def _to_float(v: Optional[str]) -> Optional[float]:
    """Parse a CapIQ numeric cell. Tolerates $, commas, parens (negatives),
    'x' multiple suffixes, and 'NA'/'-' placeholders → None."""
    if v is None:
        return None
    s = str(v).strip()
    if not s or s.upper() in ("NA", "N/A", "-", "NM", "NULL"):
        return None
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()").replace("$", "").replace(",", "").replace("x", "").replace("X", "")
    s = s.strip()
    try:
        f = float(s)
        return -f if neg else f
    except ValueError:
        return None


def parse_capiq_export(path: str | Path) -> List[CapIQRecord]:
    """Parse a CapIQ CSV export into ``CapIQRecord``s.

    Skips rows with no resolvable company name. A missing ``IQ_COMPANY_ID``
    falls back to the company name as the key (the export still loads; the
    caller just won't have CapIQ's internal id for that row). Reads CSV only —
    save Excel exports as CSV first (keeps this dependency-free).
    """
    p = Path(path)
    records: List[CapIQRecord] = []
    with p.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            name = _first_present(row, _COL_NAME)
            if not name:
                continue
            cid = _first_present(row, _COL_ID) or name
            records.append(CapIQRecord(
                capiq_id=cid,
                company_name=name,
                state=_first_present(row, _COL_STATE),
                sector=_first_present(row, _COL_SECTOR),
                ev_mm=_to_float(_first_present(row, _COL_EV)),
                ebitda_mm=_to_float(_first_present(row, _COL_EBITDA)),
                ev_ebitda=_to_float(_first_present(row, _COL_EV_EBITDA)),
                deal_date=_first_present(row, _COL_DEAL_DATE),
                raw={str(k): str(v) for k, v in row.items()},
            ))
    return records


def _score(query: str, name: str) -> float:
    return difflib.SequenceMatcher(None, query.upper(), str(name).upper()).ratio()


def resolve_record(
    rec: CapIQRecord,
    *,
    accept_threshold: float = 0.90,
    ambiguity_margin: float = 0.05,
    limit: int = 5,
) -> EntityResolution:
    """Resolve one CapIQ company to a CMS CCN against HCRIS.

    Decision rule (conservative on purpose — a wrong CCN corrupts the whole
    pipeline):

      * 0 candidates                       → UNMATCHED (likely non-hospital).
      * top score ≥ ``accept_threshold`` AND it clears the runner-up by
        ``ambiguity_margin`` (or is the only candidate) → RESOLVED.
      * otherwise                          → AMBIGUOUS (candidates returned for
        a human pick; we never auto-select).

    ``rec.state`` (if present) scopes the HCRIS search, which sharply reduces
    false positives across same-named facilities in different states.
    """
    from .hcris import lookup_by_name

    matches = lookup_by_name(rec.company_name, state=rec.state, limit=limit)
    if not matches:
        # Retry without the state scope — the export's geography column may be
        # an HQ that differs from the facility's HCRIS state.
        if rec.state:
            matches = lookup_by_name(rec.company_name, limit=limit)
        if not matches:
            return EntityResolution(
                capiq_id=rec.capiq_id, company_name=rec.company_name,
                status=ResolutionStatus.UNMATCHED,
            )

    cands = [
        CcnCandidate(
            ccn=str(m.get("ccn") or ""),
            name=str(m.get("name") or ""),
            state=(str(m.get("state")) if m.get("state") else None),
            score=_score(rec.company_name, m.get("name") or ""),
        )
        for m in matches if m.get("ccn")
    ]
    cands.sort(key=lambda c: c.score, reverse=True)
    if not cands:
        return EntityResolution(
            capiq_id=rec.capiq_id, company_name=rec.company_name,
            status=ResolutionStatus.UNMATCHED,
        )

    top = cands[0]
    runner = cands[1].score if len(cands) > 1 else 0.0
    clean = top.score >= accept_threshold and (top.score - runner) >= ambiguity_margin
    if clean:
        return EntityResolution(
            capiq_id=rec.capiq_id, company_name=rec.company_name,
            status=ResolutionStatus.RESOLVED, ccn=top.ccn,
            confidence=round(top.score, 4),
        )
    return EntityResolution(
        capiq_id=rec.capiq_id, company_name=rec.company_name,
        status=ResolutionStatus.AMBIGUOUS, confidence=round(top.score, 4),
        candidates=cands,
    )


def resolve_export(records: List[CapIQRecord], **kw: Any) -> List[EntityResolution]:
    """Resolve every parsed record. ``**kw`` forwards thresholds to
    :func:`resolve_record`."""
    return [resolve_record(r, **kw) for r in records]


# Fields HCRIS (CMS public) contributes that a financial export typically
# lacks — this is the "fill the gaps with CMS data" payload.
_CMS_GAP_FIELDS = (
    "name", "state", "city", "beds", "operating_margin", "net_patient_revenue",
    "medicare_day_pct", "medicaid_day_pct", "other_day_pct",
)


def enrich_with_cms(res: EntityResolution) -> Dict[str, Any]:
    """For a RESOLVED entity, return the CMS/HCRIS facility profile that fills
    the operational gaps a CapIQ financial export doesn't carry. Returns an
    empty dict for unmatched/ambiguous entities (we never enrich a guess).

    Every returned value is tagged ``source='cms_hcris'`` at the call site by
    convention; the dict itself is the raw CMS facts so the caller decides how
    to label/merge them.
    """
    if res.status is not ResolutionStatus.RESOLVED or not res.ccn:
        return {}
    from .hcris import lookup_by_ccn

    rec = lookup_by_ccn(res.ccn)
    if not rec:
        return {}
    return {k: rec.get(k) for k in _CMS_GAP_FIELDS if rec.get(k) is not None}


# ── Persistence (additive table; follows the load_*_to_store pattern) ─────
def _ensure_table(store: Any) -> None:
    with store.connect() as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS capiq_entity_map (
                capiq_id      TEXT PRIMARY KEY,
                company_name  TEXT NOT NULL,
                status        TEXT NOT NULL,
                ccn           TEXT,
                confidence    REAL NOT NULL DEFAULT 0,
                resolved_at   TEXT NOT NULL
            )
            """
        )
        con.commit()


def load_resolutions_to_store(store: Any, resolutions: List[EntityResolution]) -> int:
    """Upsert resolutions into ``capiq_entity_map``. Returns rows written.

    Stores only the CapIQ id, name, resolution status, the chosen CCN (NULL
    unless RESOLVED) and confidence — NOT the licensed financial values, so the
    persisted artifact is a name↔CCN crosswalk, not a copy of the S&P dataset.
    """
    from datetime import datetime, timezone

    _ensure_table(store)
    now = datetime.now(timezone.utc).isoformat()
    n = 0
    with store.connect() as con:
        for r in resolutions:
            con.execute(
                """
                INSERT INTO capiq_entity_map
                    (capiq_id, company_name, status, ccn, confidence, resolved_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(capiq_id) DO UPDATE SET
                    company_name=excluded.company_name,
                    status=excluded.status,
                    ccn=excluded.ccn,
                    confidence=excluded.confidence,
                    resolved_at=excluded.resolved_at
                """,
                (r.capiq_id, r.company_name, r.status.value, r.ccn,
                 r.confidence, now),
            )
            n += 1
        con.commit()
    return n


def resolution_summary(resolutions: List[EntityResolution]) -> Dict[str, int]:
    """Counts by status — for an honest ingestion report (how much of the
    licensed export actually mapped to CMS facilities vs. needs review)."""
    out = {s.value: 0 for s in ResolutionStatus}
    for r in resolutions:
        out[r.status.value] += 1
    return out
