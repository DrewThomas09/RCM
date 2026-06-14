"""Universe profiling — the data-room coverage view.

DQ answers "is the data correct?"; this answers "what do we actually have?"
— the coverage/completeness picture a diligence team reviews before relying
on the universe: entity-type mix, taxonomy and address completeness, key-
field null rates, the specialty and geographic distributions, and the
affiliation/endpoint coverage. Read-only; returns a structured dict and a
markdown summary.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List


def _pct(num: int, den: int) -> float:
    return round(100 * num / den, 2) if den else 0.0


def profile_universe(store: Any) -> Dict[str, Any]:
    with store.connect() as con:
        def scalar(sql, args=()):
            return con.execute(sql, args).fetchone()["c"]

        total = scalar("SELECT COUNT(*) c FROM dim_provider")
        t1 = scalar("SELECT COUNT(*) c FROM dim_provider WHERE entity_type=1")
        t2 = scalar("SELECT COUNT(*) c FROM dim_provider WHERE entity_type=2")
        active = scalar("SELECT COUNT(*) c FROM dim_provider WHERE status='active'")
        deact = scalar("SELECT COUNT(*) c FROM dim_provider WHERE status='deactivated'")

        with_taxo = scalar(
            "SELECT COUNT(DISTINCT npi) c FROM bridge_provider_taxonomy")
        with_primary = scalar(
            "SELECT COUNT(DISTINCT npi) c FROM bridge_provider_taxonomy WHERE primary_flag=1")
        with_practice = scalar(
            "SELECT COUNT(DISTINCT npi) c FROM dim_provider_address "
            "WHERE address_purpose='practice'")
        with_mailing = scalar(
            "SELECT COUNT(DISTINCT npi) c FROM dim_provider_address "
            "WHERE address_purpose='mailing'")
        with_affil = scalar(
            "SELECT COUNT(DISTINCT individual_npi) c FROM bridge_provider_affiliation")
        with_endpoint = scalar(
            "SELECT COUNT(DISTINCT npi) c FROM dim_provider_endpoint")
        quarantined = scalar("SELECT COUNT(*) c FROM nppes_invalid_npi")

        # null/blank rates on key fields
        null_org_t2 = scalar(
            "SELECT COUNT(*) c FROM dim_provider WHERE entity_type=2 "
            "AND (organization_name IS NULL OR organization_name='')")
        null_enum = scalar(
            "SELECT COUNT(*) c FROM dim_provider "
            "WHERE enumeration_date IS NULL OR enumeration_date=''")
        # geocode coverage (expected 0 until Census geocoder lands)
        addr_total = scalar("SELECT COUNT(*) c FROM dim_provider_address")
        geocoded = scalar(
            "SELECT COUNT(*) c FROM dim_provider_address "
            "WHERE fips_county IS NOT NULL AND fips_county<>''")

        top_specialties = [dict(r) for r in con.execute(
            "SELECT COALESCE(t.classification,'(unclassified)') classification, "
            "COUNT(*) c FROM bridge_provider_taxonomy b "
            "LEFT JOIN dim_taxonomy t ON t.taxonomy_code=b.taxonomy_code "
            "WHERE b.primary_flag=1 GROUP BY classification "
            "ORDER BY c DESC LIMIT 10").fetchall()]
        top_states = [dict(r) for r in con.execute(
            "SELECT state, COUNT(DISTINCT npi) c FROM dim_provider_address "
            "WHERE address_purpose='practice' AND state<>'' "
            "GROUP BY state ORDER BY c DESC LIMIT 10").fetchall()]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "totals": {
            "providers": total, "type1_individual": t1, "type2_organization": t2,
            "active": active, "deactivated": deact, "quarantined_invalid": quarantined,
        },
        "completeness_pct": {
            "has_taxonomy": _pct(with_taxo, total),
            "has_primary_taxonomy": _pct(with_primary, total),
            "has_practice_address": _pct(with_practice, total),
            "has_mailing_address": _pct(with_mailing, total),
            "individuals_with_affiliation": _pct(with_affil, t1),
            "has_fhir_endpoint": _pct(with_endpoint, total),
            "addresses_geocoded": _pct(geocoded, addr_total),
        },
        "null_rates_pct": {
            "type2_missing_org_name": _pct(null_org_t2, t2),
            "missing_enumeration_date": _pct(null_enum, total),
        },
        "top_specialties": top_specialties,
        "top_states": top_states,
    }


def profile_markdown(store: Any) -> str:
    p = profile_universe(store)
    t = p["totals"]
    L = [
        "# NPPES Universe — Data-Room Profile",
        "",
        f"_Generated {p['generated_at']}._",
        "",
        "## Totals",
        f"- Providers: **{t['providers']:,}** "
        f"(Type-1 individual {t['type1_individual']:,} · "
        f"Type-2 organization {t['type2_organization']:,})",
        f"- Active **{t['active']:,}** · deactivated **{t['deactivated']:,}** · "
        f"quarantined-invalid **{t['quarantined_invalid']:,}**",
        "",
        "## Completeness",
        "| Field | Coverage |",
        "|---|---:|",
    ]
    for k, v in p["completeness_pct"].items():
        L.append(f"| {k} | {v:.1f}% |")
    L += ["", "## Key-field null rates", "| Field | Null rate |", "|---|---:|"]
    for k, v in p["null_rates_pct"].items():
        L.append(f"| {k} | {v:.1f}% |")
    L += ["", "## Top specialties (primary taxonomy)", "| Specialty | Providers |",
          "|---|---:|"]
    for r in p["top_specialties"]:
        L.append(f"| {r['classification']} | {r['c']:,} |")
    L += ["", "## Top states (practice location)", "| State | Providers |", "|---|---:|"]
    for r in p["top_states"]:
        L.append(f"| {r['state']} | {r['c']:,} |")
    L += ["", "_`addresses_geocoded` is expected at 0% until the Census "
          "geocoder (separate session) populates `fips_county` / lat-long._", ""]
    return "\n".join(L)
