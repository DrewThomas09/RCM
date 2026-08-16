"""Who operates a facility, when its name tells you nothing.

The problem this exists for
---------------------------
30,092 certified facilities are operating and unmapped, and **27,341 of
them — 90.9% — share their CMS name with no other facility in the
country**::

    SNF 96.6% singleton   dialysis 96.3%   hospital 89.2%
    HHA 88.3%             hospice 84.9%

Every mapping tool in this package groups names. The registry matches
name patterns; :mod:`operator_discovery` clusters normalized names;
the 50-state proposal sweep read names off the register. Against a
facility whose name matches nothing, none of them can fire. Discovery's
entire confident-and-unmapped set is 1,412 groups over 3,349 facilities
— eleven per cent of the gap, and that is its ceiling rather than its
progress.

CMS publishes a ``chain_name`` field, which would solve this outright.
It is populated for dialysis and for **zero** rows of SNF, home health,
hospice or hospital.

What NPPES carries that CMS does not
------------------------------------
Two things, harvested per CCN alongside the NPI::

    CMS name       EASTVIEW REHABILITATION & HEALTHCARE CENTER
    NPPES name     BALL HEALTHCARE EASTVIEW INC        <- the operator
    NPPES mailing  1 SOUTHERN WAY, MOBILE AL 36619     <- corporate HQ
                   (the facility is in Birmingham, 250 miles away)

The **mailing address is the load-bearing one**, because it is the only
signal here that does not depend on the name at all. A chain's back
office receives mail for every building it runs, and those buildings
are frequently named nothing alike::

    4150 INTERNATIONAL PLAZA, FORT WORTH TX
      FANNIN COUNTY HOSPITAL AUTHORITY       -> North Park Health & Rehab
      WEST WHARTON COUNTY HOSPITAL DISTRICT  -> Amarillo Center for Skilled Care
      VAL VERDE COUNTY HOSPITAL DISTRICT     -> La Hacienda De Paz
      GILMER I ENTERPRISES, L.L.C.           -> Gilmer Nursing & Rehabilitation
      REFUGIO II ENTERPRISES, L.L.C.         -> Mission Ridge Rehab & Nursing

Three county hospital districts hundreds of miles apart, with no
geographic relationship to the buildings they license, plus two shell
LLCs — one office suite. Nothing in the CMS file connects those five.

The guard that makes it work
----------------------------
Most facilities mail to themselves. An independent nursing home files
its own street as its mailing address, so joining on mailing address
naively would union every facility in a ZIP that happens to share a
building. :func:`is_remote_mailing` requires the mailing address to be
somewhere *other than* the facility — a different city, or a different
street in the same city. Only a remote back office is evidence.

The second guard is for registered-agent and lockbox addresses. A law
firm or corporate-services provider receives mail for hundreds of
unrelated companies, and joining on that address would fuse an entire
state into one fictional operator.

Counting *legal names* was the obvious way to spot one, and it was
exactly wrong. A chain that incorporates every building separately
files nineteen names from one Utah office, so a name-count guard
refused Farmington, North Olmsted and Beachwood — the three clearest
chains in the first harvest. What separates a back office from a law
firm is not how many entities receive mail there but how many
*signatories* do: Foundations Health Solutions files twenty names and
one Sandy Muir. So the threshold is :data:`MAX_OFFICIALS_PER_ADDRESS`,
and refusals are reported through :func:`service_addresses` rather
than silently dropped.

Four join keys, not one
-----------------------
The harvest showed the address is not always the strongest key.

**The legal name.** Texas runs a supplemental-payment arrangement in
which rural hospital districts hold the licence for nursing homes
hundreds of miles outside their county. Those facilities mail to
themselves, so the address key never fires — but they file under one
legal entity::

    FANNIN COUNTY HOSPITAL AUTHORITY
      -> facilities in Waco, Paris, Palestine and Denison
    WINNIE-STOWELL HOSPITAL DISTRICT
      -> Copperas Cove, Marshall, Groves, Hemphill

This is still a name match, but not the kind that failed: it is the
*registered entity* on the NPI, not the brand on the building. Two
facilities filing the same legal name are the same legal person, which
is a fact rather than an inference. It is also the only key that
reaches roughly a third of the Texas nursing estate.

**The authorized official.** One person, **Soon Burnam**, signs for
four different hospital districts at four different addresses. The
person is the join there, not the building.

**The declared parent.** A minority of records name their parent
outright in ``parent_organization_legal_business_name`` — Saber
Healthcare Holdings does — which is ground truth needing no inference.

Each key is reported on its own, and that is deliberate
-------------------------------------------------------
The first version unioned all four keys with union-find, on the
reasoning that a chain found by two keys is one chain. Run against the
real harvest it produced a **152-facility cluster** spanning Alvin
Health Care Center, Bellville Hospital District, Belmont Care Center
and dozens more — because union-find is transitive. A shares an office
with B, B shares an officer with C, C shares a legal name with D, and
four unrelated operators become one blob. The claim "these 152
facilities are one company" is not something the evidence supports and
not something a reader can check.

So clusters are now grouped **per key**, and a facility appears in as
many clusters as it has evidence for. "These nineteen share a back
office" and "these twelve share a signing officer" are two separate,
checkable statements. Overlap between them is information, not a
problem to resolve — and nothing chains.

What this is not
----------------
It is not applied to ``system_id``. A cluster is evidence that one
company runs several buildings; it is not a claim about what that
company is called on a cap table, and the registry stores brands. The
output is a queue of candidate operators for the same admission gate
in :mod:`registry_proposals` that everything else goes through.
"""

from __future__ import annotations

import csv
import gzip
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .health_systems import normalize_name
from .npi_identifier import is_valid_npi

_PACKAGE_DIR = Path(__file__).resolve().parent

#: Shipped as package data via the ``rcm_mc = ["data/*.csv.gz"]`` glob.
OWNERSHIP_PATH = _PACKAGE_DIR / "facility_ownership.csv.gz"

OWNERSHIP_COLUMNS: Tuple[str, ...] = (
    "ccn", "npi", "legal_name", "dba", "parent_org",
    "mail_street", "mail_city", "mail_state", "mail_zip",
    "official_name", "official_title", "taxonomy_code",
    "match_basis", "confidence",
)

#: How many *different people* may sign at one address before it stops
#: looking like a company and starts looking like a registered agent.
#:
#: Counting legal names here was the obvious first idea and it was
#: wrong: a chain that incorporates every building separately files
#: nineteen legal names from one Utah office, and a name-count guard
#: refused exactly the chains this module exists to find. What
#: separates a back office from a law firm is not how many entities
#: receive mail there — it is how many *signatories* do. Foundations
#: Health Solutions files twenty names and one Sandy Muir; a corporate
#: services provider files hundreds of names and hundreds of officers.
MAX_OFFICIALS_PER_ADDRESS = 8

#: A cluster of one is just a facility. Two is the smallest thing that
#: is evidence of an operator.
MIN_CLUSTER = 2


def _clean(value: object) -> str:
    return str(value or "").strip()


def _norm_street(value: object) -> str:
    """Uppercase and strip punctuation, without the SAINT rule.

    :func:`health_systems.normalize_name` expands ``ST`` to ``SAINT``,
    which is right for SAINT MARYS HOSPITAL and wrong for 101 W LIBERTY
    ST. Clustering survived it because both sides were mangled the same
    way, but the key is displayed on the page and in the CSV export, and
    "101 W LIBERTY SAINT" is not an address anyone can look up or join
    against.
    """
    text = "".join(ch if ch.isalnum() else " " for ch in str(value or "").upper())
    return " ".join(text.split())


def _norm_addr(street: str, city: str, state: str) -> str:
    """An address reduced to a comparison key.

    Suite numbers are deliberately **kept**. Two shells at Ste 200 and
    Ste 600 of one building are the same operator, and dropping the
    suite would be right there and wrong in an office tower shared by
    unrelated companies. The service-address guard handles the tower;
    keeping the suite costs nothing.
    """
    parts = [_norm_street(street), _norm_street(city), _clean(state).upper()]
    return "|".join(p for p in parts if p)


@dataclass(frozen=True)
class OwnershipRow:
    """One facility's operator, as the provider filed it with NPPES."""

    ccn: str
    npi: str
    legal_name: str
    dba: str
    parent_org: str
    mail_street: str
    mail_city: str
    mail_state: str
    mail_zip: str
    official_name: str
    official_title: str
    taxonomy_code: str
    match_basis: str
    confidence: str

    @property
    def mail_key(self) -> str:
        return _norm_addr(self.mail_street, self.mail_city, self.mail_state)

    @property
    def official_key(self) -> str:
        # A person's name, so the SAINT rule is harmless here and the
        # shared normaliser keeps officer keys consistent with the
        # legal-name keys they are compared against.
        return normalize_name(self.official_name)

    @property
    def parent_key(self) -> str:
        return normalize_name(self.parent_org)

    @property
    def legal_key(self) -> str:
        """The registered entity, not the brand.

        Two facilities filing this name are the same legal person. That
        is why it is safe to join on where the CMS facility name is not:
        one is an entity, the other is a sign over a door.
        """
        return normalize_name(self.legal_name)


@dataclass(frozen=True)
class OwnershipCluster:
    """Facilities sharing one piece of ownership evidence.

    ``joined_by`` is a single key type, not a set: a cluster is exactly
    one claim, so that a reader can check it. A facility appearing in
    three clusters has three separate pieces of evidence, which is more
    useful than one merged blob asserting more than can be verified.
    """

    joined_by: str = ""
    key: str = ""
    members: Tuple[str, ...] = ()
    legal_names: Tuple[str, ...] = ()
    mail_addresses: Tuple[str, ...] = ()
    officials: Tuple[str, ...] = ()
    parents: Tuple[str, ...] = ()

    @property
    def size(self) -> int:
        return len(self.members)

    @property
    def states(self) -> Tuple[str, ...]:
        """The CMS state codes the members' CCNs carry.

        These are CMS codes and not postal ones — 45 is Texas, 36 is
        Ohio — so they are safe to compare against each other and wrong
        to show a reader as a state. Available without a join, which is
        why the comparison uses them; anything user-facing should map
        the CCN through the crosswalk instead.
        """
        return tuple(sorted({c[:2] for c in self.members}))

    @property
    def names_differ(self) -> bool:
        """True when even the members' *legal* names do not group.

        The strongest form of the finding. A cluster held together only
        by a back office or a signing officer, whose members do not
        agree on a legal name either, is one no name-based method could
        have reached from any field in any file.

        A cluster joined on the legal name reads False here and is still
        invisible to everything else in this package, because the field
        that matches is the registered entity on the NPI and the field
        the registry reads is the sign over the door.
        """
        return len({normalize_name(n) for n in self.legal_names}) > 1


def _read_rows(path: Path) -> List[Dict[str, str]]:
    """Rows from the shipped file, or none if it is not there.

    A missing file is normal: the harvest is incremental and every
    caller treats an unresolved facility as ordinary.
    """
    if not path.exists():
        return []
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def is_remote_mailing(row: OwnershipRow, facility_city: str = "",
                      facility_street: str = "") -> bool:
    """Is the mailing address somewhere other than the facility?

    Independent facilities mail to themselves, so a mailing address that
    *is* the facility carries no information about ownership. Only a
    back office elsewhere does.

    Without a facility address to compare against, this can still refuse
    the empty case, which is the one that would otherwise fuse every
    unfiled row into a single cluster.
    """
    if not row.mail_key:
        return False
    if facility_city and normalize_name(facility_city) != normalize_name(row.mail_city):
        return True
    if facility_street:
        return normalize_name(facility_street) != normalize_name(row.mail_street)
    # Either the mailing city matches and there is no street to separate
    # them, or there is no facility address at all. Both are "cannot be
    # shown to be remote", and unproven is not evidence: a cluster built
    # on an address nobody checked would be indistinguishable from one
    # built on a real back office.
    return False


@lru_cache(maxsize=2)
def _cached(path_str: str) -> Tuple[Dict[str, OwnershipRow], ...]:
    rows: Dict[str, OwnershipRow] = {}
    for raw in _read_rows(Path(path_str)):
        ccn = _clean(raw.get("ccn")).upper()
        npi = _clean(raw.get("npi"))
        if not ccn or not is_valid_npi(npi) or ccn in rows:
            continue
        rows[ccn] = OwnershipRow(
            ccn=ccn, npi=npi,
            legal_name=_clean(raw.get("legal_name")),
            dba=_clean(raw.get("dba")),
            parent_org=_clean(raw.get("parent_org")),
            mail_street=_clean(raw.get("mail_street")),
            mail_city=_clean(raw.get("mail_city")),
            mail_state=_clean(raw.get("mail_state")).upper(),
            mail_zip=_clean(raw.get("mail_zip")),
            official_name=_clean(raw.get("official_name")),
            official_title=_clean(raw.get("official_title")),
            taxonomy_code=_clean(raw.get("taxonomy_code")),
            match_basis=_clean(raw.get("match_basis")),
            confidence=_clean(raw.get("confidence")).lower() or "medium",
        )
    return (rows,)


def load_ownership(path: Optional[Path] = None) -> Dict[str, OwnershipRow]:
    """CCN -> :class:`OwnershipRow` for every harvested facility."""
    return _cached(str(path or OWNERSHIP_PATH))[0]


def service_addresses(path: Optional[Path] = None) -> Dict[str, int]:
    """Mailing addresses signed for by too many different people.

    Registered agents, law firms and lockboxes. Counting *signatories*
    rather than entity names is the whole trick: a chain that
    incorporates each building separately files many names and one
    officer, which is the shape this module is looking for, while a
    corporate-services provider files many names and many officers.

    Reported rather than quietly skipped, because the line between a
    very large operator and a services provider is a judgement the
    count should let a reader make for themselves.
    """
    officials: Dict[str, set] = defaultdict(set)
    for row in load_ownership(path).values():
        if row.mail_key and row.official_key:
            officials[row.mail_key].add(row.official_key)
    return {addr: len(seen) for addr, seen in sorted(officials.items())
            if len(seen) > MAX_OFFICIALS_PER_ADDRESS}


def ownership_clusters(
        path: Optional[Path] = None,
        facilities: Optional[Dict[str, Tuple[str, str]]] = None,
) -> List[OwnershipCluster]:
    """Facilities grouped by the company that appears to run them.

    ``facilities`` maps CCN -> (city, street) for the facility itself,
    so :func:`is_remote_mailing` can tell a back office from a building
    mailing to itself. Omit it and every mailing address is treated as
    local, which returns only the officer- and parent-joined clusters —
    correct, and much smaller.
    """
    rows = load_ownership(path)
    if not rows:
        return []
    facilities = facilities or {}
    skip = set(service_addresses(path))

    keyed: Dict[Tuple[str, str], List[str]] = defaultdict(list)
    for ccn, row in rows.items():
        city, street = facilities.get(ccn, ("", ""))
        if (row.mail_key and row.mail_key not in skip
                and is_remote_mailing(row, city, street)):
            keyed[("mail", row.mail_key)].append(ccn)
        if row.official_key:
            keyed[("official", row.official_key)].append(ccn)
        if row.parent_key:
            keyed[("parent", row.parent_key)].append(ccn)
        if row.legal_key:
            keyed[("legal", row.legal_key)].append(ccn)

    out: List[OwnershipCluster] = []
    for (kind, key), members in keyed.items():
        if len(members) < MIN_CLUSTER:
            continue
        members = sorted(members)
        picked = [rows[c] for c in members]
        out.append(OwnershipCluster(
            joined_by=kind, key=key, members=tuple(members),
            legal_names=tuple(sorted({r.legal_name for r in picked if r.legal_name})),
            mail_addresses=tuple(sorted({r.mail_key for r in picked if r.mail_key})),
            officials=tuple(sorted({r.official_name for r in picked if r.official_name})),
            parents=tuple(sorted({r.parent_org for r in picked if r.parent_org})),
        ))
    out.sort(key=lambda c: (-c.size, c.joined_by, c.key))
    return out


def ownership_summary(path: Optional[Path] = None,
                      facilities: Optional[Dict[str, Tuple[str, str]]] = None
                      ) -> Dict[str, object]:
    """Coverage and its caveats, for the page and the tests."""
    rows = load_ownership(path)
    clusters = ownership_clusters(path, facilities)
    hidden = [c for c in clusters if c.names_differ]
    covered = {m for c in clusters for m in c.members}
    by_key = Counter(c.joined_by for c in clusters)
    return {
        "facilities_harvested": len(rows),
        "facilities_in_some_cluster": len(covered),
        "clusters": len(clusters),
        "clusters_by_key": dict(sorted(by_key.items())),
        "largest_cluster": max((c.size for c in clusters), default=0),
        "clusters_whose_legal_names_differ": len(hidden),
        "facilities_no_name_could_group": len({m for c in hidden for m in c.members}),
        "service_addresses_refused": len(service_addresses(path)),
    }


def ownership_cluster_frame(
        path: Optional[Path] = None,
        facilities: Optional[Dict[str, Tuple[str, str]]] = None,
        min_size: int = MIN_CLUSTER,
) -> "pd.DataFrame":
    """The clusters as a downloadable table, one row per cluster.

    Exists because the strongest findings here are the ones the
    registry cannot hold. A cluster joined on a back office or a signing
    officer is better evidence of common ownership than a shared
    licence, and it supplies no name — so it cannot become a SystemDef,
    and a partner can only act on it if they can see it.
    """
    import pandas as pd

    rows = []
    for c in ownership_clusters(path, facilities):
        if c.size < min_size:
            continue
        rows.append({
            "joined_by": c.joined_by,
            "key": c.key,
            "facilities": c.size,
            "ccn_state_codes": "|".join(c.states),
            "legal_names_differ": c.names_differ,
            "ccns": "|".join(c.members),
            "legal_names": " | ".join(c.legal_names[:8]),
            "officials": " | ".join(c.officials[:4]),
            "parents": " | ".join(c.parents[:4]),
            "mail_addresses": " | ".join(c.mail_addresses[:4]),
        })
    columns = ["joined_by", "key", "facilities", "ccn_state_codes",
               "legal_names_differ", "ccns", "legal_names", "officials",
               "parents", "mail_addresses"]
    if not rows:
        return pd.DataFrame(columns=columns)
    frame = pd.DataFrame(rows, columns=columns)
    return frame.sort_values(["facilities", "joined_by", "key"],
                             ascending=[False, True, True])


def _clear_cache() -> None:
    """Drop the memoized load. Tests writing a fixture need this."""
    _cached.cache_clear()
