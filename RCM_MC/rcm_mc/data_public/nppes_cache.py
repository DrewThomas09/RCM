"""NPPES live-cache layer for the diligence platform.

Wraps :mod:`rcm_mc.data_public.nppes_api_client` with a SQLite cache
keyed by (lookup-shape, lookup-key) so that successive partner
navigations on /hospital/<ccn>/providers don't fan out to NPPES on
every render.

Schema lives in the same SQLite file as the rest of the portfolio
store (single-machine deployment per CLAUDE.md). Refresh handler
follows the pattern in `rcm_mc/data/sources.py` — explicit
``refresh()`` call, never an inline render-time hit.

Cache TTL: default 30 days. NPPES updates monthly so daily TTL is
overkill; partners need the data to be ~recent but not real-time.

Public API:
    ensure_table(con)                                 — idempotent migration
    get_cached_org_roster(con, ccn) -> dict | None    — cache read
    refresh_org_roster(con, ccn, hospital_name, state) — pulls + stores
    list_providers(con, ccn) -> List[NppesProvider]   — read decoded
    cache_age_days(con, ccn) -> Optional[int]         — staleness check
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .nppes_api_client import (
    NppesProvider,
    search_by_organization,
    search_by_address,
)


_CACHE_TTL_DAYS = 30


def ensure_table(con: sqlite3.Connection) -> None:
    """Idempotent migration for the NPPES live-cache table.

    One row per (CCN, NPI) pair so the same provider showing up under
    multiple hospitals doesn't conflict. ``fetched_at`` drives the
    staleness check.
    """
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS nppes_live_cache (
            ccn TEXT NOT NULL,
            npi TEXT NOT NULL,
            entity_type INTEGER,
            name TEXT,
            first_name TEXT,
            last_name TEXT,
            organization_name TEXT,
            taxonomy_code TEXT,
            taxonomy_label TEXT,
            primary_specialty TEXT,
            address_line TEXT,
            city TEXT,
            state TEXT,
            postal_code TEXT,
            phone TEXT,
            enumeration_date TEXT,
            last_updated TEXT,
            raw_record TEXT,
            fetched_at TEXT NOT NULL,
            PRIMARY KEY (ccn, npi)
        )
        """
    )
    con.execute(
        "CREATE INDEX IF NOT EXISTS idx_nppes_live_ccn "
        "ON nppes_live_cache(ccn)"
    )
    con.execute(
        "CREATE INDEX IF NOT EXISTS idx_nppes_live_taxo "
        "ON nppes_live_cache(taxonomy_code)"
    )
    con.commit()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def cache_age_days(con: sqlite3.Connection, ccn: str) -> Optional[int]:
    """Return age in days of the freshest cached row for this CCN, or
    None if there are no cached rows."""
    row = con.execute(
        "SELECT fetched_at FROM nppes_live_cache WHERE ccn = ? "
        "ORDER BY fetched_at DESC LIMIT 1",
        (str(ccn),),
    ).fetchone()
    if not row:
        return None
    try:
        fetched = datetime.fromisoformat(row[0])
        if fetched.tzinfo is None:
            fetched = fetched.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None
    return max(0, (datetime.now(timezone.utc) - fetched).days)


def is_stale(con: sqlite3.Connection, ccn: str, *,
             ttl_days: int = _CACHE_TTL_DAYS) -> bool:
    """True if cache is missing or older than TTL."""
    age = cache_age_days(con, ccn)
    return age is None or age > ttl_days


def list_providers(con: sqlite3.Connection, ccn: str) -> List[NppesProvider]:
    """Return cached providers for a CCN as NppesProvider records."""
    rows = con.execute(
        "SELECT npi, entity_type, name, first_name, last_name, "
        "organization_name, taxonomy_code, taxonomy_label, "
        "primary_specialty, address_line, city, state, postal_code, "
        "phone, enumeration_date, last_updated, raw_record "
        "FROM nppes_live_cache WHERE ccn = ? ORDER BY name",
        (str(ccn),),
    ).fetchall()
    out: List[NppesProvider] = []
    for r in rows:
        raw: Dict[str, Any] = {}
        if r[16]:
            try:
                raw = json.loads(r[16])
            except json.JSONDecodeError:
                raw = {}
        out.append(NppesProvider(
            npi=r[0] or "",
            entity_type=int(r[1] or 0),
            name=r[2] or "",
            first_name=r[3] or "",
            last_name=r[4] or "",
            organization_name=r[5] or "",
            taxonomy_code=r[6] or "",
            taxonomy_label=r[7] or "",
            primary_specialty=r[8] or "",
            address_line=r[9] or "",
            city=r[10] or "",
            state=r[11] or "",
            postal_code=r[12] or "",
            phone=r[13] or "",
            enumeration_date=r[14] or "",
            last_updated=r[15] or "",
            raw_record=raw,
        ))
    return out


def get_cached_org_roster(
    con: sqlite3.Connection, ccn: str,
) -> Optional[Dict[str, Any]]:
    """Return summary dict for the CCN's cached roster, or None if empty.

    Summary shape:
        {
          "ccn": "123456",
          "n_providers": int,
          "n_organizations": int,
          "n_individuals": int,
          "specialty_mix": {taxonomy_label: count, ...},
          "fetched_at_iso": str,
          "age_days": int,
        }
    """
    providers = list_providers(con, ccn)
    if not providers:
        return None
    age = cache_age_days(con, ccn) or 0
    # Pull freshest fetched_at for display
    row = con.execute(
        "SELECT fetched_at FROM nppes_live_cache WHERE ccn = ? "
        "ORDER BY fetched_at DESC LIMIT 1",
        (str(ccn),),
    ).fetchone()
    fetched_iso = row[0] if row else ""

    n_orgs = sum(1 for p in providers if p.is_organization)
    n_indiv = sum(1 for p in providers if p.is_individual)
    specialty_mix: Dict[str, int] = {}
    for p in providers:
        if not p.taxonomy_label:
            continue
        specialty_mix[p.taxonomy_label] = (
            specialty_mix.get(p.taxonomy_label, 0) + 1
        )

    return {
        "ccn": str(ccn),
        "n_providers": len(providers),
        "n_organizations": n_orgs,
        "n_individuals": n_indiv,
        "specialty_mix": specialty_mix,
        "fetched_at_iso": fetched_iso,
        "age_days": age,
    }


def refresh_org_roster(
    con: sqlite3.Connection,
    ccn: str,
    *,
    hospital_name: str = "",
    state: str = "",
    city: str = "",
    postal_code: str = "",
    individual_limit: int = 200,
) -> int:
    """Pull fresh NPPES data for this CCN and write to cache.

    Two-step lookup:
        1. Resolve the hospital's Type-2 organization NPI from name +
           state (if hospital_name provided).
        2. Enumerate Type-1 individual NPIs at the practice address.

    Returns the number of providers written to the cache.

    Existing rows for this CCN are DELETED before write so each
    refresh is a full replace, not a merge. Avoids stale-NPI residue.
    """
    ensure_table(con)
    providers: List[NppesProvider] = []

    # Step 1: organization NPIs (Type-2)
    if hospital_name:
        try:
            org_results = search_by_organization(
                organization_name=hospital_name,
                state=state,
                limit=20,
            )
            providers.extend(org_results)
        except Exception:
            # NPPES occasionally returns errors on edge names; skip
            # rather than abort the whole refresh.
            org_results = []
    else:
        org_results = []

    # Step 2: individuals at the resolved practice address(es)
    addresses = []
    if city and state:
        addresses.append((city, state, postal_code))
    for org in org_results[:5]:
        if org.city and org.state:
            key = (org.city.upper(), org.state.upper(), org.postal_code)
            if key not in {(c.upper(), s.upper(), p) for c, s, p in addresses}:
                addresses.append((org.city, org.state, org.postal_code))

    for (city_q, state_q, postal_q) in addresses:
        try:
            individuals = search_by_address(
                city=city_q, state=state_q,
                postal_code=postal_q,
                limit=individual_limit,
            )
            providers.extend(individuals)
        except Exception:
            continue

    # Dedupe by NPI
    by_npi: Dict[str, NppesProvider] = {}
    for p in providers:
        if p.npi and p.npi not in by_npi:
            by_npi[p.npi] = p

    fetched = _now_iso()
    con.execute("DELETE FROM nppes_live_cache WHERE ccn = ?", (str(ccn),))
    for p in by_npi.values():
        con.execute(
            "INSERT INTO nppes_live_cache (ccn, npi, entity_type, name, "
            "first_name, last_name, organization_name, taxonomy_code, "
            "taxonomy_label, primary_specialty, address_line, city, "
            "state, postal_code, phone, enumeration_date, "
            "last_updated, raw_record, fetched_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                str(ccn), p.npi, p.entity_type, p.name,
                p.first_name, p.last_name, p.organization_name,
                p.taxonomy_code, p.taxonomy_label, p.primary_specialty,
                p.address_line, p.city, p.state, p.postal_code,
                p.phone, p.enumeration_date, p.last_updated,
                json.dumps(p.raw_record), fetched,
            ),
        )
    con.commit()
    return len(by_npi)
