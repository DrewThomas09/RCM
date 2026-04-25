"""Weekly incremental NPPES updates + Type-1↔Type-2 affiliation
linking.

NPPES publishes a full weekly snapshot CSV (~9GB, 6M+ rows) and a
weekly DELTA file. The full snapshot is overkill for a partner
running this on a cron — they only need:

  • New NPIs (NPI not already in pricing_nppes)
  • Updated NPIs (nppes_last_updated > our stored value)
  • Newly retired NPIs (a "deactivation_date" appearing for an
    existing NPI)

This module implements that. Plus the Type-1 ↔ Type-2
affiliation table that downstream systems
(rcm_mc.referral, rcm_mc.pricing.payer_mrf consumers) need to
ask "which organization does this physician bill under?"

The affiliation source: NPPES "Other Provider Identifier" fields
encode (when populated) the parent organization's NPI. For
provider records that don't have it, partners typically join via
Medicare Provider Utilization shared-patient files.

Public API::

    from rcm_mc.pricing.nppes_incremental import (
        incremental_nppes_load,
        list_affiliations_for_npi,
        list_individuals_at_organization,
        NppesIncrementalReport,
    )
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, List, Optional, Set

from .nppes import NppesRecord

logger = logging.getLogger(__name__)


@dataclass
class NppesIncrementalReport:
    """Output of one incremental load."""
    rows_inserted: int = 0
    rows_updated: int = 0
    rows_skipped: int = 0
    rows_deactivated: int = 0
    affiliations_recorded: int = 0
    notes: List[str] = field(default_factory=list)


def _ensure_affiliation_table(con: Any) -> None:
    """Create the Type-1 ↔ Type-2 affiliation table."""
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS pricing_nppes_affiliations (
            individual_npi TEXT NOT NULL,
            organization_npi TEXT NOT NULL,
            relationship_type TEXT,
            recorded_at TEXT NOT NULL,
            source TEXT,
            PRIMARY KEY (individual_npi, organization_npi)
        )
        """
    )
    con.execute(
        "CREATE INDEX IF NOT EXISTS "
        "idx_nppes_affiliation_org "
        "ON pricing_nppes_affiliations(organization_npi)"
    )


def _ensure_deactivation_column(con: Any) -> None:
    """Add the optional deactivation_date column if not yet present."""
    try:
        con.execute(
            "ALTER TABLE pricing_nppes "
            "ADD COLUMN deactivation_date TEXT")
    except Exception:  # noqa: BLE001
        # Already exists or table not present yet — ignore
        pass


def incremental_nppes_load(
    store: Any,
    records: Iterable[NppesRecord],
    *,
    affiliations: Optional[Iterable[tuple]] = None,
    deactivations: Optional[Iterable[tuple]] = None,
) -> NppesIncrementalReport:
    """Run a weekly incremental NPPES update.

    Args:
      store: PricingStore instance.
      records: iterable of NppesRecord — new + updated NPIs from
        the weekly delta file (or full snapshot).
      affiliations: iterable of (individual_npi, organization_npi,
        relationship_type) tuples — the Type-1 ↔ Type-2 links.
      deactivations: iterable of (npi, deactivation_date) tuples
        — NPIs CMS marked deactivated this week.

    Returns NppesIncrementalReport with per-action counts.
    """
    store.init_db()
    now = datetime.now(timezone.utc).isoformat()
    report = NppesIncrementalReport()

    with store.connect() as con:
        _ensure_affiliation_table(con)
        _ensure_deactivation_column(con)

        con.execute("BEGIN IMMEDIATE")
        try:
            # ── Insert/update NPI rows ────────────────────────
            for r in records:
                existing = con.execute(
                    "SELECT nppes_last_updated FROM pricing_nppes "
                    "WHERE npi = ?", (r.npi,),
                ).fetchone()

                if existing is None:
                    con.execute(
                        "INSERT INTO pricing_nppes (npi, "
                        "entity_type, organization_name, "
                        "last_name, first_name, taxonomy_code, "
                        "taxonomy_label, address_line, city, "
                        "state, zip5, cbsa, "
                        "nppes_last_updated, loaded_at) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (r.npi, r.entity_type, r.organization_name,
                         r.last_name, r.first_name,
                         r.taxonomy_code, r.taxonomy_label,
                         r.address_line, r.city, r.state, r.zip5,
                         r.cbsa, r.nppes_last_updated, now),
                    )
                    report.rows_inserted += 1
                else:
                    stored_ts = (
                        existing["nppes_last_updated"] or "")
                    new_ts = r.nppes_last_updated or ""
                    # Only update when the CMS-published last-
                    # update timestamp is strictly newer. String
                    # comparison works because NPPES uses ISO
                    # YYYY-MM-DD.
                    if new_ts > stored_ts:
                        con.execute(
                            "UPDATE pricing_nppes SET "
                            "entity_type = ?, "
                            "organization_name = ?, "
                            "last_name = ?, first_name = ?, "
                            "taxonomy_code = ?, "
                            "taxonomy_label = ?, "
                            "address_line = ?, city = ?, "
                            "state = ?, zip5 = ?, cbsa = ?, "
                            "nppes_last_updated = ?, "
                            "loaded_at = ? "
                            "WHERE npi = ?",
                            (r.entity_type,
                             r.organization_name,
                             r.last_name, r.first_name,
                             r.taxonomy_code, r.taxonomy_label,
                             r.address_line, r.city, r.state,
                             r.zip5, r.cbsa,
                             r.nppes_last_updated, now,
                             r.npi),
                        )
                        report.rows_updated += 1
                    else:
                        report.rows_skipped += 1

            # ── Affiliations ─────────────────────────────────
            if affiliations:
                for tup in affiliations:
                    if len(tup) >= 2:
                        ind_npi, org_npi = tup[0], tup[1]
                        rel = tup[2] if len(tup) > 2 else "billing"
                        if not (ind_npi and org_npi):
                            continue
                        con.execute(
                            "INSERT OR REPLACE INTO "
                            "pricing_nppes_affiliations "
                            "(individual_npi, organization_npi, "
                            " relationship_type, "
                            " recorded_at, source) "
                            "VALUES (?, ?, ?, ?, ?)",
                            (str(ind_npi), str(org_npi), rel,
                             now, "weekly_delta"),
                        )
                        report.affiliations_recorded += 1

            # ── Deactivations ────────────────────────────────
            if deactivations:
                for npi, deact_date in deactivations:
                    if not npi:
                        continue
                    cur = con.execute(
                        "UPDATE pricing_nppes SET "
                        "deactivation_date = ? "
                        "WHERE npi = ?",
                        (str(deact_date or now), str(npi)),
                    )
                    if cur.rowcount > 0:
                        report.rows_deactivated += 1

            con.commit()
        except Exception:
            con.rollback()
            raise

    return report


def list_affiliations_for_npi(
    store: Any,
    npi: str,
) -> List[dict]:
    """Return all affiliation rows for an NPI (whether
    individual or organizational endpoint).

    For an individual NPI: returns the organizations they bill
    under. For an organizational NPI: returns the individual
    providers affiliated with the org.
    """
    if not npi:
        return []
    npi = str(npi).strip()
    with store.connect() as con:
        _ensure_affiliation_table(con)
        rows = con.execute(
            "SELECT * FROM pricing_nppes_affiliations "
            "WHERE individual_npi = ? "
            "   OR organization_npi = ?",
            (npi, npi),
        ).fetchall()
    return [dict(r) for r in rows]


def list_individuals_at_organization(
    store: Any,
    org_npi: str,
) -> List[dict]:
    """Return the Type-1 NPIs affiliated with an org NPI."""
    if not org_npi:
        return []
    with store.connect() as con:
        _ensure_affiliation_table(con)
        rows = con.execute(
            "SELECT * FROM pricing_nppes_affiliations "
            "WHERE organization_npi = ?",
            (str(org_npi).strip(),),
        ).fetchall()
    return [dict(r) for r in rows]


def list_organizations_for_individual(
    store: Any,
    individual_npi: str,
) -> List[dict]:
    """Return the Type-2 organizations a Type-1 NPI bills under."""
    if not individual_npi:
        return []
    with store.connect() as con:
        _ensure_affiliation_table(con)
        rows = con.execute(
            "SELECT * FROM pricing_nppes_affiliations "
            "WHERE individual_npi = ?",
            (str(individual_npi).strip(),),
        ).fetchall()
    return [dict(r) for r in rows]
