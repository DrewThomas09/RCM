"""Derived organization-affiliation bridge (heuristic).

We reconstruct individual→organization affiliation the way a diligence
analyst would when NPPES gives no explicit parent link: providers that
*operate from the same place* and *share a name* are probably affiliated.
This approximates referral and captive-volume relationships (the spine of
market-structure / TAM work), and it is explicitly heuristic — every row
carries a ``method`` and a ``confidence`` in [0,1].

Matching method (documented; mirrored in DECISIONS.md)
------------------------------------------------------
Signals, per (Type-1 individual NPI ``i``, Type-2 organization NPI ``o``):

  S1  shared practice address — ``i`` and ``o`` share a normalized practice
      address key (upper(line_1) stripped of punctuation + zip5). Base
      evidence of co-location.
  S2  name overlap — a significant token of ``i``'s last name appears in
      ``o``'s legal business name or in one of ``o``'s other organization
      names (captures "Smith" billing under "Smith Family Medicine LLC").

Confidence:
  • S1 alone:  0.45, divided down by how many distinct orgs share the
    address (co-location is weaker evidence when many orgs share a suite):
    ``0.45 / sqrt(n_orgs_at_address)``, floored at 0.20.
  • S1 + S2:   boosted to ``min(0.92, conf_S1 + 0.30)``.
A pair with only S2 and no co-location is *not* emitted (too weak alone).

The bridge is rebuilt from scratch on each run (idempotent) and is purely
derived — it never writes back into dim_provider.
"""
from __future__ import annotations

import math
import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Set, Tuple

_PUNCT = re.compile(r"[^A-Z0-9 ]+")
_STOP = {"LLC", "INC", "PC", "PA", "PLLC", "LLP", "LTD", "CORP", "CO",
         "THE", "OF", "AND", "GROUP", "HEALTH", "MEDICAL", "CENTER",
         "CLINIC", "ASSOCIATES", "PARTNERS", "SERVICES", "CARE"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm_addr(line_1: str, zip5: str) -> str:
    base = _PUNCT.sub("", (line_1 or "").upper()).strip()
    base = re.sub(r"\s+", " ", base)
    return f"{base}|{(zip5 or '').strip()}" if base else ""


def _name_tokens(name: str) -> Set[str]:
    up = _PUNCT.sub(" ", (name or "").upper())
    toks = {t for t in up.split() if len(t) >= 3 and t not in _STOP}
    return toks


def build_affiliations(
    store: Any, *, min_confidence: float = 0.20, max_orgs_per_address: int = 50
) -> Dict[str, int]:
    """Rebuild bridge_provider_affiliation. Returns counters."""
    store.init_db()
    now = _now()

    # Pull practice addresses joined to provider entity/name. Bounded read:
    # only practice/secondary_practice purposes, only the columns needed.
    addr_to_individuals: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
    addr_to_orgs: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
    org_other_names: Dict[str, Set[str]] = defaultdict(set)

    with store.connect() as con:
        for r in con.execute(
            "SELECT npi, other_name FROM nppes_other_name"):
            org_other_names[r["npi"]] |= _name_tokens(r["other_name"])

        q = (
            "SELECT a.npi AS npi, a.address_line_1 AS line1, a.zip5 AS zip5, "
            "       p.entity_type AS et, p.last_name AS last_name, "
            "       p.organization_name AS org_name "
            "FROM dim_provider_address a "
            "JOIN dim_provider p ON p.npi = a.npi "
            "WHERE a.address_purpose IN ('practice','secondary_practice')"
        )
        for r in con.execute(q):
            key = _norm_addr(r["line1"], r["zip5"])
            if not key:
                continue
            if r["et"] == 1:
                addr_to_individuals[key].append((r["npi"], r["last_name"] or ""))
            elif r["et"] == 2:
                addr_to_orgs[key].append((r["npi"], r["org_name"] or ""))

        counters = {"pairs": 0, "addresses_matched": 0}
        con.execute("BEGIN")
        try:
            con.execute("DELETE FROM bridge_provider_affiliation")
            for key, individuals in addr_to_individuals.items():
                orgs = addr_to_orgs.get(key)
                if not orgs or len(orgs) > max_orgs_per_address:
                    continue
                n_orgs = len(orgs)
                base = max(0.20, 0.45 / math.sqrt(n_orgs))
                counters["addresses_matched"] += 1
                for ind_npi, ind_last in individuals:
                    ind_tokens = _name_tokens(ind_last)
                    for org_npi, org_name in orgs:
                        org_tokens = _name_tokens(org_name) | org_other_names.get(org_npi, set())
                        name_hit = bool(ind_tokens & org_tokens)
                        if name_hit:
                            conf = min(0.92, base + 0.30)
                            method = "shared_address+name"
                            ev = (f"co-located @ {key}; name token overlap "
                                  f"{sorted(ind_tokens & org_tokens)}")
                        else:
                            conf = round(base, 4)
                            method = "shared_practice_address"
                            ev = f"co-located @ {key}; {n_orgs} org(s) at address"
                        if conf < min_confidence:
                            continue
                        con.execute(
                            "INSERT OR REPLACE INTO bridge_provider_affiliation "
                            "(individual_npi, organization_npi, method, confidence, "
                            " evidence, loaded_at) VALUES (?,?,?,?,?,?)",
                            (ind_npi, org_npi, method, round(conf, 4), ev, now))
                        counters["pairs"] += 1
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK"); raise

        con.execute(
            "INSERT INTO nppes_load_log (batch, dataset_id, action, rows_inserted, "
            "notes, logged_at) VALUES (?,?,?,?,?,?)",
            ("affiliation", "bridge_provider_affiliation", "derive",
             counters["pairs"],
             f"addresses_matched={counters['addresses_matched']}", now))
        con.commit()
    return counters
