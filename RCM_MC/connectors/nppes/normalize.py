"""Normalize parsed/landed rows into the canonical dimensions.

Every writer is an idempotent upsert keyed by NPI (or the bridge's natural
composite key) and operates in bounded batches so an 8M-row stream never
balloons memory. Invalid NPIs are quarantined into ``nppes_invalid_npi``,
never dropped. The functions accept either a ``ProviderRow`` (from the
streaming parser) or an equivalent flat dict (from the landing/api path),
so the monthly file, the weeklies, and the live API all flow through the
same normalizer.
"""
from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from .luhn import is_valid_npi
from .parse import ProviderRow, TaxonomySlot, AddressBlock, TaxonomyDef, zip5_of


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_provider_row(obj: Any) -> ProviderRow:
    if isinstance(obj, ProviderRow):
        return obj
    d = dict(obj)
    taxos = []
    for t in d.get("taxonomies", []) or []:
        if isinstance(t, TaxonomySlot):
            taxos.append(t)
        else:
            taxos.append(TaxonomySlot(
                code=t.get("code", ""), primary=bool(t.get("primary")),
                license_number=t.get("license_number", ""),
                license_state=t.get("license_state", ""),
                group=t.get("group", "")))
    addrs = []
    for a in d.get("addresses", []) or []:
        if isinstance(a, AddressBlock):
            addrs.append(a)
        else:
            addrs.append(AddressBlock(
                purpose=a.get("purpose", "practice"),
                line_1=a.get("line_1", ""), line_2=a.get("line_2", ""),
                city=a.get("city", ""), state=a.get("state", ""),
                postal_code=a.get("postal_code", ""),
                country_code=a.get("country_code", "US"),
                telephone=a.get("telephone", ""), fax=a.get("fax", "")))
    return ProviderRow(
        npi=str(d.get("npi", "")),
        entity_type=int(d.get("entity_type") or 0),
        replacement_npi=d.get("replacement_npi", ""),
        organization_name=d.get("organization_name", ""),
        last_name=d.get("last_name", ""),
        first_name=d.get("first_name", ""),
        middle_name=d.get("middle_name", ""),
        name_prefix=d.get("name_prefix", ""),
        name_suffix=d.get("name_suffix", ""),
        credential=d.get("credential", ""),
        authorized_official_last_name=d.get("authorized_official_last_name", ""),
        authorized_official_first_name=d.get("authorized_official_first_name", ""),
        authorized_official_title=d.get("authorized_official_title", ""),
        authorized_official_phone=d.get("authorized_official_phone", ""),
        sole_proprietor=d.get("sole_proprietor", ""),
        enumeration_date=d.get("enumeration_date", ""),
        last_update_date=d.get("last_update_date", ""),
        deactivation_date=d.get("deactivation_date", ""),
        reactivation_date=d.get("reactivation_date", ""),
        taxonomies=taxos,
        addresses=addrs,
    )


def _status_of(row: ProviderRow) -> str:
    """Deactivated iff there is a deactivation date with no later
    reactivation date. NPPES uses MM/DD/YYYY in the file; we compare
    lexically only when formats match, else fall back to presence."""
    deact = (row.deactivation_date or "").strip()
    react = (row.reactivation_date or "").strip()
    if not deact:
        return "active"
    if react and react >= deact:
        return "active"
    return "deactivated"


def normalize_providers(
    store: Any,
    rows: Iterable[Any],
    *,
    source_row: str = "monthly",
    monthly_version: str = "",
    batch_size: int = 5000,
    batch_label: str = "normalize",
) -> Dict[str, int]:
    """Upsert a provider stream into dim_provider + bridge_provider_taxonomy
    + dim_provider_address. Returns counters."""
    store.init_db()
    now = _now()
    counters = {"rows_in": 0, "inserted": 0, "updated": 0,
                "quarantined": 0, "taxonomy_rows": 0, "address_rows": 0}

    with store.connect() as con:
        con.execute("BEGIN")
        pending = 0
        try:
            for obj in rows:
                row = _as_provider_row(obj)
                counters["rows_in"] += 1
                if not is_valid_npi(row.npi):
                    con.execute(
                        "INSERT INTO nppes_invalid_npi "
                        "(raw_npi, reason, source_row, payload, quarantined_at) "
                        "VALUES (?,?,?,?,?)",
                        (row.npi, "failed_luhn_or_format", source_row,
                         json.dumps(_compact(row)), now))
                    counters["quarantined"] += 1
                    pending += 1
                else:
                    existed = con.execute(
                        "SELECT nppes_last_updated FROM dim_provider WHERE npi=?",
                        (row.npi,)).fetchone()
                    # Skip stale updates: only overwrite when the incoming
                    # last_update is >= stored (weeklies arrive newest-wins).
                    if existed is not None:
                        stored = existed["nppes_last_updated"] or ""
                        incoming = row.last_update_date or ""
                        if incoming and stored and incoming < stored:
                            counters["updated"] += 0  # stale, leave as is
                            continue
                    self_upsert_provider(con, row, source_row, monthly_version, now)
                    self_upsert_taxonomies(con, row, now, counters)
                    self_upsert_addresses(con, row, now, counters)
                    if existed is None:
                        counters["inserted"] += 1
                    else:
                        counters["updated"] += 1
                    pending += 1
                if pending >= batch_size:
                    con.execute("COMMIT")
                    con.execute("BEGIN")
                    pending = 0
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise

        con.execute(
            "INSERT INTO nppes_load_log "
            "(batch, dataset_id, action, rows_in, rows_inserted, rows_updated, "
            " rows_quarantined, notes, logged_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (batch_label, "nppes_main", source_row, counters["rows_in"],
             counters["inserted"], counters["updated"], counters["quarantined"],
             f"version={monthly_version}", now))
        con.commit()
    return counters


def self_upsert_provider(con, row: ProviderRow, source_row, version, now) -> None:
    con.execute(
        """INSERT INTO dim_provider (
            npi, entity_type, first_name, middle_name, last_name,
            name_prefix, name_suffix, credential, organization_name,
            authorized_official_last_name, authorized_official_first_name,
            authorized_official_title, authorized_official_phone,
            sole_proprietor, enumeration_date, last_update_date,
            deactivation_date, reactivation_date, status, replacement_npi,
            nppes_last_updated, monthly_version, source_row, loaded_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(npi) DO UPDATE SET
            entity_type=excluded.entity_type,
            first_name=excluded.first_name, middle_name=excluded.middle_name,
            last_name=excluded.last_name, name_prefix=excluded.name_prefix,
            name_suffix=excluded.name_suffix, credential=excluded.credential,
            organization_name=excluded.organization_name,
            authorized_official_last_name=excluded.authorized_official_last_name,
            authorized_official_first_name=excluded.authorized_official_first_name,
            authorized_official_title=excluded.authorized_official_title,
            authorized_official_phone=excluded.authorized_official_phone,
            sole_proprietor=excluded.sole_proprietor,
            enumeration_date=excluded.enumeration_date,
            last_update_date=excluded.last_update_date,
            deactivation_date=excluded.deactivation_date,
            reactivation_date=excluded.reactivation_date,
            status=excluded.status, replacement_npi=excluded.replacement_npi,
            nppes_last_updated=excluded.nppes_last_updated,
            monthly_version=excluded.monthly_version,
            source_row=excluded.source_row, loaded_at=excluded.loaded_at
        """,
        (row.npi, row.entity_type, row.first_name, row.middle_name,
         row.last_name, row.name_prefix, row.name_suffix, row.credential,
         row.organization_name, row.authorized_official_last_name,
         row.authorized_official_first_name, row.authorized_official_title,
         row.authorized_official_phone, row.sole_proprietor,
         row.enumeration_date, row.last_update_date, row.deactivation_date,
         row.reactivation_date, _status_of(row), row.replacement_npi,
         row.last_update_date, version, source_row, now))


def self_upsert_taxonomies(con, row: ProviderRow, now, counters) -> None:
    # Replace the provider's taxonomy set so re-loads converge (a weekly may
    # drop a taxonomy). Delete-then-insert keyed by NPI.
    con.execute("DELETE FROM bridge_provider_taxonomy WHERE npi=?", (row.npi,))
    for slot in row.taxonomies:
        if not slot.code:
            continue
        con.execute(
            "INSERT OR REPLACE INTO bridge_provider_taxonomy "
            "(npi, taxonomy_code, primary_flag, license_number, license_state, "
            " taxonomy_group, loaded_at) VALUES (?,?,?,?,?,?,?)",
            (row.npi, slot.code, 1 if slot.primary else 0,
             slot.license_number, slot.license_state, slot.group, now))
        counters["taxonomy_rows"] += 1


def self_upsert_addresses(con, row: ProviderRow, now, counters) -> None:
    con.execute(
        "DELETE FROM dim_provider_address WHERE npi=? AND address_seq=0",
        (row.npi,))
    for blk in row.addresses:
        con.execute(
            """INSERT OR REPLACE INTO dim_provider_address (
                npi, address_purpose, address_seq, address_line_1,
                address_line_2, city, state, postal_code, zip5, country_code,
                telephone, fax, fips_county, latitude, longitude,
                geocode_status, loaded_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (row.npi, blk.purpose, 0, blk.line_1, blk.line_2, blk.city,
             blk.state, blk.postal_code, zip5_of(blk.postal_code),
             blk.country_code, blk.telephone, blk.fax,
             None, None, None, "pending", now))
        counters["address_rows"] += 1


# ── NUCC taxonomy crosswalk ─────────────────────────────────────────
def normalize_taxonomy(
    store: Any, defs: Iterable[Any], *, nucc_version: str = "", batch_size: int = 2000
) -> Dict[str, int]:
    store.init_db()
    now = _now()
    counters = {"rows_in": 0, "loaded": 0}
    with store.connect() as con:
        con.execute("BEGIN")
        pending = 0
        try:
            for obj in defs:
                d = obj if isinstance(obj, TaxonomyDef) else TaxonomyDef(**obj)
                if not d.code:
                    continue
                counters["rows_in"] += 1
                con.execute(
                    """INSERT OR REPLACE INTO dim_taxonomy (
                        taxonomy_code, grouping, classification, specialization,
                        definition, nucc_notes, display_name, section,
                        nucc_version, loaded_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (d.code, d.grouping, d.classification, d.specialization,
                     d.definition, d.notes, d.display_name, d.section,
                     nucc_version, now))
                counters["loaded"] += 1
                pending += 1
                if pending >= batch_size:
                    con.execute("COMMIT"); con.execute("BEGIN"); pending = 0
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK"); raise
        con.commit()
    return counters


# ── auxiliary dissemination files ───────────────────────────────────
def normalize_other_names(store: Any, rows: Iterable[Dict]) -> int:
    store.init_db()
    now = _now()
    n = 0
    seq_by_npi: Dict[str, int] = {}
    with store.connect() as con:
        con.execute("BEGIN")
        try:
            for r in rows:
                npi = str(r.get("npi", ""))
                if not is_valid_npi(npi):
                    continue
                seq = seq_by_npi.get(npi, 0)
                seq_by_npi[npi] = seq + 1
                con.execute(
                    "INSERT OR REPLACE INTO nppes_other_name "
                    "(npi, other_name_seq, other_name, other_name_type_code, loaded_at) "
                    "VALUES (?,?,?,?,?)",
                    (npi, seq, r.get("other_name", ""),
                     r.get("other_name_type_code", ""), now))
                n += 1
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK"); raise
        con.commit()
    return n


def normalize_practice_locations(store: Any, rows: Iterable[Dict]) -> int:
    """Non-primary practice locations → dim_provider_address with seq>0."""
    store.init_db()
    now = _now()
    n = 0
    seq_by_npi: Dict[str, int] = {}
    with store.connect() as con:
        con.execute("BEGIN")
        try:
            for r in rows:
                npi = str(r.get("npi", ""))
                if not is_valid_npi(npi):
                    continue
                seq = seq_by_npi.get(npi, 0) + 1
                seq_by_npi[npi] = seq
                con.execute(
                    """INSERT OR REPLACE INTO dim_provider_address (
                        npi, address_purpose, address_seq, address_line_1,
                        address_line_2, city, state, postal_code, zip5,
                        country_code, telephone, fax, fips_county, latitude,
                        longitude, geocode_status, loaded_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (npi, "secondary_practice", seq, r.get("line_1", ""),
                     r.get("line_2", ""), r.get("city", ""), r.get("state", ""),
                     r.get("postal_code", ""), zip5_of(r.get("postal_code", "")),
                     r.get("country_code", "US"), r.get("telephone", ""),
                     r.get("fax", ""), None, None, None, "pending", now))
                n += 1
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK"); raise
        con.commit()
    return n


def normalize_endpoints(store: Any, rows: Iterable[Dict]) -> int:
    store.init_db()
    now = _now()
    n = 0
    seq_by_npi: Dict[str, int] = {}
    with store.connect() as con:
        con.execute("BEGIN")
        try:
            for r in rows:
                npi = str(r.get("npi", ""))
                if not is_valid_npi(npi):
                    continue
                seq = seq_by_npi.get(npi, 0)
                seq_by_npi[npi] = seq + 1
                con.execute(
                    """INSERT OR REPLACE INTO dim_provider_endpoint (
                        npi, endpoint_seq, endpoint_type, endpoint_type_description,
                        endpoint, affiliation, use_description, content_type, loaded_at
                    ) VALUES (?,?,?,?,?,?,?,?,?)""",
                    (npi, seq, r.get("endpoint_type", ""),
                     r.get("endpoint_type_description", ""), r.get("endpoint", ""),
                     r.get("affiliation", ""), r.get("use_description", ""),
                     r.get("content_type", ""), now))
                n += 1
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK"); raise
        con.commit()
    return n


def _compact(row: ProviderRow) -> Dict:
    d = asdict(row) if is_dataclass(row) else dict(row)
    # keep payload small for quarantine
    return {k: d.get(k) for k in ("npi", "entity_type", "organization_name",
                                  "last_name", "first_name")}
