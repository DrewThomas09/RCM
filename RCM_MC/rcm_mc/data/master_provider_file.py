"""The master NPI file — one row per identifier, every one with a parent.

What this is
------------
A single wide table keyed on NPI, carrying identity, status history,
taxonomy and category, geography, the CCN it bills under where one
exists, and the final parent it resolves to with the evidence for that
parent. It is built to be the spine other crosswalks join to: give it an
NPI from a claim file, a roster or a diligence data room and it answers
who that is, what they do, where they are, and who owns them.

Everything upstream of here already exists — :mod:`nppes_ingest` streams
the register, :mod:`nucc_categories` classifies the taxonomy,
:mod:`provider_crosswalk` carries certified-facility geography,
:mod:`parent_resolution` walks the ownership graph. This module is the
assembly, and it is deliberately thin: a bug here should be a bug in one
join, not in a re-derivation of something already tested elsewhere.

What it will and will not claim
-------------------------------
**An individual NPI gets a parent only from an affiliation source, never
from geography.** NPPES has no employer field for a person: no column
says which system a physician works for, and two physicians sharing a
medical office building are not colleagues. So an individual resolves to
itself, with ``parent_basis`` saying why, unless something outside NPPES
links them.

The one such source in this repository is the derived bridge in
``connectors/nppes/affiliation.py``, which pairs an individual with an
organization at the same practice address *and* sharing a name token —
Dr. Smith billing where Smith Family Medicine bills. Pass it via
``affiliations`` and those individuals resolve, carrying the bridge's own
per-pair confidence and its method in ``parent_basis``. The bridge's
other method, bare co-location, is refused rather than scored down: a low
number on a claim that should not have been made is still the claim.

**Organization NPIs are where the ownership graph does its work**, via
NPPES's own subpart filing, PECOS enrolment groups, the CCN link, chain
names, and last the brand registry.

Scale
-----
The full register is ~8 million rows and does not fit in memory
alongside a graph. :func:`export_master_file` streams: it builds the
ownership graph once from organization NPIs (~1.8 M, the only ones that
can carry an ownership edge), then reads the register in chunks and
writes rows as it goes. :func:`build_master_file` materialises instead,
which is right for the sources that fit — and, today, for everything
available offline.

What is available offline
-------------------------
``download.cms.gov`` is not reachable from this build, so the 9 GB
dissemination file is not here. What is here is real: 20,401 ambulance
and EMS organization NPIs with PECOS enrolment groups, plus the
certified-facility crosswalk. The builder runs on those unchanged, and
runs on the full file the day it is supplied — ``db_path`` points at a
database written by :func:`nppes_ingest.ingest_nppes` and nothing else
about the code changes.
"""
from __future__ import annotations

import csv
import gzip as _gzip
import sqlite3
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

import pandas as pd

from .nppes_ingest import (
    ENTITY_ORGANIZATION, STATUS_ACTIVE, STATUS_DEACTIVATED,
)
from .nucc_categories import classify_taxonomy
from .parent_resolution import (
    NS_NPI, ParentGraph, build_parent_graph, load_affiliations, node_key,
)

MASTER_COLUMNS: Tuple[str, ...] = (
    # Identity
    "npi", "entity_type", "entity_label", "legal_name", "dba_name",
    "credential", "sole_proprietor",
    # Status and history
    "status", "enumeration_date", "deactivation_date", "reactivation_date",
    "last_updated", "certification_date",
    # What they do
    "taxonomy_code", "taxonomy_codes", "taxonomy_category",
    "taxonomy_level_i", "is_organisation",
    # Where they are
    "address", "city", "state", "zip", "county", "county_fips",
    "cbsa_code", "cbsa_title", "cbsa_type",
    # What they are certified as
    "ccn", "provider_class", "facility_type", "facility_status",
    # Who says they own it
    "is_subpart", "parent_org_lbn", "parent_org_tin", "ein", "pecos_group",
    # Who owns them, resolved
    "final_parent", "final_parent_type", "final_parent_id",
    "parent_tier", "parent_confidence", "parent_hops", "parent_basis",
    "parent_contested",
    # Where the row came from
    "source",
)

#: The one honest answer for a person. NPPES carries no employer field,
#: and inventing one here would be the single easiest way to make the
#: whole crosswalk untrustworthy.
INDIVIDUAL_NO_PARENT = (
    "individual NPI — NPPES carries no employer; needs a facility-"
    "affiliation source")
ROOT_BASIS = "top of its own ownership tree"

_TABLE = "npi_crosswalk"

_DB_COLUMNS: Tuple[str, ...] = (
    "npi", "entity_type", "legal_name", "dba_name", "credential",
    "sole_proprietor", "status", "enumeration_date", "deactivation_date",
    "reactivation_date", "last_updated", "certification_date",
    "taxonomy_code", "taxonomy_codes", "taxonomy_category",
    "taxonomy_level_i", "is_organisation", "address", "city", "state", "zip",
    "ccn", "is_subpart", "parent_org_lbn", "parent_org_tin", "ein",
    "system_id",
)


# ── reading whatever NPI source is available ───────────────────────

def _read_db_chunks(db_path: Any, chunk_size: int,
                    where: str = "", params: Tuple[Any, ...] = ()
                    ) -> Iterator[pd.DataFrame]:
    """Stream ``npi_crosswalk`` without materialising it.

    Keyset pagination on the primary key rather than OFFSET: at 8 M rows
    an OFFSET scan re-walks the whole prefix on every page and turns a
    linear read into a quadratic one.
    """
    con = sqlite3.connect(str(db_path))
    try:
        available = {r[1] for r in con.execute(f"PRAGMA table_info({_TABLE})")}
        cols = [c for c in _DB_COLUMNS if c in available]
        if "npi" not in cols:
            raise ValueError(f"{db_path} has no {_TABLE} table to read")
        clause = f" AND ({where})" if where else ""
        sql = (f"SELECT {', '.join(cols)} FROM {_TABLE} "
               f"WHERE npi > ?{clause} ORDER BY npi LIMIT ?")
        cursor_npi = ""
        while True:
            rows = con.execute(sql, (cursor_npi, *params, chunk_size)).fetchall()
            if not rows:
                return
            frame = pd.DataFrame(rows, columns=cols).fillna("")
            for missing in (c for c in _DB_COLUMNS if c not in cols):
                frame[missing] = ""
            yield frame
            cursor_npi = str(rows[-1][cols.index("npi")])
    finally:
        con.close()


def _bundled_npi_frame() -> pd.DataFrame:
    """The only real NPPES data on disk: the ambulance/EMS org roster.

    A slice, not the register — 20,401 organization NPIs in the 3416 /
    3418 / 3439 taxonomy family. Every count derived from it is scoped
    to that slice and the ``source`` column says so on every row.
    """
    from .npi_registry import assign_npi_registry

    frame = assign_npi_registry()
    if frame.empty:
        return pd.DataFrame(columns=list(_DB_COLUMNS))
    # The roster spells status as NPPES's raw A/D code; the master file
    # speaks one vocabulary or its status column cannot be grouped on.
    status = (frame.get("status", pd.Series([""] * len(frame)))
              .astype(str).str.strip().str.upper()
              .map({"A": STATUS_ACTIVE, "D": STATUS_DEACTIVATED})
              .fillna(STATUS_ACTIVE))
    out = pd.DataFrame({
        "npi": frame["npi"].astype(str),
        "entity_type": ENTITY_ORGANIZATION,
        "legal_name": frame["legal_name"].astype(str),
        "dba_name": frame["dba"].astype(str),
        "status": status,
        "enumeration_date": frame["enumeration_date"].astype(str),
        "taxonomy_code": frame["taxonomy_code"].astype(str),
        "city": frame["city"].astype(str),
        "state": frame["state"].astype(str),
        "zip": frame["zip5"].astype(str),
        "county_fips": frame["county_fips"].astype(str),
        "cbsa_code": frame["cbsa_code"].astype(str),
        "cbsa_title": frame["cbsa_title"].astype(str),
        "cbsa_type": frame["cbsa_type"].astype(str),
        "pecos_group": frame["pecos_group"].astype(str),
        "system_id": frame["system_id"].astype(str),
        # Carried for the ownership graph, not for the master file's
        # columns: the authorised official is how an unbranded
        # subsidiary reaches the parent its sibling is branded with.
        "auth_official": frame.get(
            "auth_official", pd.Series([""] * len(frame))).astype(str),
    })
    for missing in (c for c in _DB_COLUMNS if c not in out.columns):
        out[missing] = ""
    out["source"] = "nppes ambulance/EMS extract"
    return out


def _crosswalk_npi_frame(crosswalk: pd.DataFrame) -> pd.DataFrame:
    """Organization NPIs that the certified-facility crosswalk resolved.

    Ninety of them today — matched to a CCN on name, state and ZIP.
    Small, and the only NPIs in this build that arrive already tied to a
    cost-report filer, which makes them the ones worth keeping.
    """
    linked = crosswalk[crosswalk["npi"].astype(str).str.strip().ne("")]
    if linked.empty:
        return pd.DataFrame(columns=list(_DB_COLUMNS) + ["source"])
    out = pd.DataFrame({
        "npi": linked["npi"].astype(str),
        "entity_type": ENTITY_ORGANIZATION,
        "legal_name": linked["name"].astype(str),
        "taxonomy_code": linked["taxonomy_code"].astype(str),
        "address": linked["street"].astype(str),
        "city": linked["city"].astype(str),
        "state": linked["state"].astype(str),
        "zip": linked["zip"].astype(str).str[:5],
        "ccn": linked["ccn"].astype(str),
        "system_id": linked["system_id"].astype(str),
    })
    for missing in (c for c in _DB_COLUMNS if c not in out.columns):
        out[missing] = ""
    out["source"] = "provider crosswalk (CCN-linked)"
    return out


def _facility_index(crosswalk: pd.DataFrame) -> Dict[str, Dict[str, str]]:
    """CCN -> the facility attributes an NPI inherits from its CCN.

    Geography lives on the certified facility, not on the NPI: NPPES
    gives a practice address but no county and no CBSA, and the
    crosswalk has already done that work — including the Connecticut
    planning-region vintage break that a naive ZIP join gets wrong.
    """
    wanted = ("county", "county_fips", "cbsa_code", "cbsa_title", "cbsa_type",
              "provider_class", "facility_type", "facility_status",
              "certification_date")
    index: Dict[str, Dict[str, str]] = {}
    for rec in crosswalk.to_dict("records"):
        ccn = str(rec.get("ccn") or "").strip()
        if ccn:
            index[ccn] = {k: str(rec.get(k) or "") for k in wanted}
    return index


# ── assembling one row ─────────────────────────────────────────────

def _entity_label(entity_type: Any, is_org: bool) -> str:
    text = str(entity_type or "").strip()
    if text == ENTITY_ORGANIZATION:
        return "organization"
    if text:
        return "individual"
    # An entity type is missing on tombstone rows, where the taxonomy
    # is missing too. Say "unknown" rather than defaulting to a guess
    # that would put a dead NPI on the wrong side of the graph.
    return "organization" if is_org else "unknown"


def _enrich_chunk(chunk: pd.DataFrame, graph: ParentGraph,
                  facilities: Dict[str, Dict[str, str]],
                  contested: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for rec in chunk.to_dict("records"):
        npi = str(rec.get("npi") or "").strip()
        if not npi:
            continue

        code = str(rec.get("taxonomy_code") or "").strip()
        klass = classify_taxonomy(code)
        category = str(rec.get("taxonomy_category") or "") or klass.category
        level_i = str(rec.get("taxonomy_level_i") or "") or klass.level_i
        is_org_flag = str(rec.get("is_organisation") or "").strip()
        is_org = (is_org_flag in {"1", "True", "true"}
                  or (not is_org_flag and klass.is_organisation)
                  or str(rec.get("entity_type") or "") == ENTITY_ORGANIZATION)

        ccn = str(rec.get("ccn") or "").strip()
        facility = facilities.get(ccn, {})

        node = node_key(NS_NPI, npi)
        res = graph.resolve(node) if node else None
        individual = _entity_label(rec.get("entity_type"), is_org) == "individual"
        if individual and (res is None or res.is_root):
            # NPPES carries no employer field, so a person only gets a
            # parent when an affiliation source supplies one. Absent
            # that, the blank is the answer and the basis says why.
            final_parent, tier, confidence, hops = "", "", "", 0
            basis = INDIVIDUAL_NO_PARENT
        elif res is None or res.is_root:
            final_parent, tier, confidence, hops = "", "", "", 0
            basis = ROOT_BASIS
        else:
            final_parent = res.final_parent
            tier = res.weakest_tier
            confidence = res.confidence
            hops = res.hops
            basis = res.provenance
        parent_ns, _, parent_id = final_parent.partition(":")

        rows.append({
            "npi": npi,
            "entity_type": str(rec.get("entity_type") or ""),
            "entity_label": _entity_label(rec.get("entity_type"), is_org),
            "legal_name": str(rec.get("legal_name") or ""),
            "dba_name": str(rec.get("dba_name") or ""),
            "credential": str(rec.get("credential") or ""),
            "sole_proprietor": str(rec.get("sole_proprietor") or ""),
            "status": str(rec.get("status") or "") or STATUS_ACTIVE,
            "enumeration_date": str(rec.get("enumeration_date") or ""),
            "deactivation_date": str(rec.get("deactivation_date") or ""),
            "reactivation_date": str(rec.get("reactivation_date") or ""),
            "last_updated": str(rec.get("last_updated") or ""),
            "certification_date": (str(rec.get("certification_date") or "")
                                   or facility.get("certification_date", "")),
            "taxonomy_code": code,
            "taxonomy_codes": str(rec.get("taxonomy_codes") or "") or code,
            "taxonomy_category": category,
            "taxonomy_level_i": level_i,
            "is_organisation": 1 if is_org else 0,
            "address": str(rec.get("address") or ""),
            "city": str(rec.get("city") or ""),
            "state": str(rec.get("state") or "").upper(),
            "zip": str(rec.get("zip") or "")[:5],
            "county": str(rec.get("county") or "") or facility.get("county", ""),
            "county_fips": (str(rec.get("county_fips") or "")
                            or facility.get("county_fips", "")),
            "cbsa_code": (str(rec.get("cbsa_code") or "")
                          or facility.get("cbsa_code", "")),
            "cbsa_title": (str(rec.get("cbsa_title") or "")
                           or facility.get("cbsa_title", "")),
            "cbsa_type": (str(rec.get("cbsa_type") or "")
                          or facility.get("cbsa_type", "")),
            "ccn": ccn,
            "provider_class": facility.get("provider_class", ""),
            "facility_type": facility.get("facility_type", ""),
            "facility_status": facility.get("facility_status", ""),
            "is_subpart": str(rec.get("is_subpart") or ""),
            "parent_org_lbn": str(rec.get("parent_org_lbn") or ""),
            "parent_org_tin": str(rec.get("parent_org_tin") or ""),
            "ein": str(rec.get("ein") or ""),
            "pecos_group": str(rec.get("pecos_group") or ""),
            "final_parent": final_parent,
            "final_parent_type": parent_ns,
            "final_parent_id": parent_id,
            "parent_tier": tier,
            "parent_confidence": confidence,
            "parent_hops": hops,
            "parent_basis": basis,
            "parent_contested": 1 if node in contested else 0,
            "source": str(rec.get("source") or "NPPES dissemination file"),
        })
    return rows


# ── the two entry points ───────────────────────────────────────────

def _sources(db_path: Optional[Any], crosswalk: pd.DataFrame,
             npi_frame: Optional[pd.DataFrame]) -> pd.DataFrame:
    """Union the available NPI sources, richest row winning per NPI."""
    frames: List[pd.DataFrame] = []
    if npi_frame is not None:
        frames.append(npi_frame)
    elif db_path is not None:
        frames.extend(_read_db_chunks(db_path, 250_000))
    else:
        frames.append(_bundled_npi_frame())
        frames.append(_crosswalk_npi_frame(crosswalk))

    frames = [f for f in frames if f is not None and not f.empty]
    if not frames:
        return pd.DataFrame(columns=list(_DB_COLUMNS) + ["source"])
    merged = pd.concat(frames, ignore_index=True).fillna("")
    # A CCN-linked row knows more than a roster row about the same NPI,
    # and the roster rows come first, so the LAST duplicate wins.
    return merged.drop_duplicates(subset=["npi"], keep="last")


def build_master_file(
    *,
    db_path: Optional[Any] = None,
    crosswalk: Optional[pd.DataFrame] = None,
    npi_frame: Optional[pd.DataFrame] = None,
    affiliations: Optional[pd.DataFrame] = None,
    affiliation_db: Optional[Any] = None,
    graph: Optional[ParentGraph] = None,
) -> pd.DataFrame:
    """One row per NPI, every organization walked to a final parent.

    With no arguments this builds from what is bundled: the ambulance /
    EMS organization roster and the certified-facility crosswalk. Point
    ``db_path`` at a database written by
    :func:`nppes_ingest.ingest_nppes` and the same code produces the
    national file.
    """
    from .provider_crosswalk import SCOPE_ALL, get_crosswalk

    xw = get_crosswalk(scope=SCOPE_ALL) if crosswalk is None else crosswalk
    frame = _sources(db_path, xw, npi_frame)
    if affiliations is None and affiliation_db is not None:
        affiliations = load_affiliations(affiliation_db)
    if graph is None:
        graph = build_parent_graph(crosswalk=xw, npi_frame=frame,
                                   affiliations=affiliations)
    rows = _enrich_chunk(frame, graph, _facility_index(xw),
                         graph.contested())
    if not rows:
        return pd.DataFrame(columns=list(MASTER_COLUMNS))
    return pd.DataFrame(rows, columns=list(MASTER_COLUMNS))


def export_master_file(
    path: Any,
    *,
    db_path: Optional[Any] = None,
    crosswalk: Optional[pd.DataFrame] = None,
    npi_frame: Optional[pd.DataFrame] = None,
    affiliations: Optional[pd.DataFrame] = None,
    affiliation_db: Optional[Any] = None,
    chunk_size: int = 250_000,
    compress: bool = False,
    progress: Optional[Any] = None,
) -> Dict[str, Any]:
    """Write the master file to CSV without holding it in memory.

    The ownership graph is built once, from organization NPIs only —
    individuals contribute no ownership edge, so excluding them keeps
    the graph to roughly a fifth of the register while losing nothing.
    Rows then stream through it a chunk at a time.

    Returns the counts the run actually produced: rows written,
    organizations, individuals, how many reached a parent, and the mix
    by status and category.
    """
    from .provider_crosswalk import SCOPE_ALL, get_crosswalk

    xw = get_crosswalk(scope=SCOPE_ALL) if crosswalk is None else crosswalk
    facilities = _facility_index(xw)

    if db_path is None:
        graph_source = _sources(None, xw, npi_frame)
        chunks: Iterator[pd.DataFrame] = iter([graph_source])
    else:
        graph_source = pd.concat(
            list(_read_db_chunks(db_path, chunk_size,
                                 where="entity_type = ?",
                                 params=(ENTITY_ORGANIZATION,))) or
            [pd.DataFrame(columns=list(_DB_COLUMNS))],
            ignore_index=True)
        chunks = _read_db_chunks(db_path, chunk_size)

    if affiliations is None and affiliation_db is not None:
        affiliations = load_affiliations(affiliation_db)
    graph = build_parent_graph(crosswalk=xw, npi_frame=graph_source,
                               affiliations=affiliations)
    contested = graph.contested()

    path = Path(path)
    opener = (_gzip.open(path, "wt", newline="", encoding="utf-8")
              if compress else path.open("w", newline="", encoding="utf-8"))
    stats: Dict[str, Any] = {
        "rows": 0, "organizations": 0, "individuals": 0,
        "with_parent": 0, "contested": 0, "with_ccn": 0,
        "by_status": {}, "by_category": {},
    }
    with opener as handle:
        writer = csv.DictWriter(handle, fieldnames=list(MASTER_COLUMNS))
        writer.writeheader()
        for chunk in chunks:
            rows = _enrich_chunk(chunk, graph, facilities, contested)
            writer.writerows(rows)
            for row in rows:
                stats["rows"] += 1
                if row["entity_label"] == "organization":
                    stats["organizations"] += 1
                elif row["entity_label"] == "individual":
                    stats["individuals"] += 1
                if row["final_parent"]:
                    stats["with_parent"] += 1
                if row["parent_contested"]:
                    stats["contested"] += 1
                if row["ccn"]:
                    stats["with_ccn"] += 1
                status = row["status"] or STATUS_ACTIVE
                stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
                cat = row["taxonomy_category"] or "unclassified"
                stats["by_category"][cat] = stats["by_category"].get(cat, 0) + 1
            if progress is not None:
                progress(stats)
    stats["by_category"] = dict(sorted(stats["by_category"].items(),
                                       key=lambda kv: (-kv[1], kv[0])))
    stats["path"] = str(path)
    return stats


@lru_cache(maxsize=1)
def master_graph() -> ParentGraph:
    """The ownership graph over every identifier this build can see.

    Wider than :func:`parent_resolution.crosswalk_graph`, which stops at
    the certified universe. This one adds the NPI sources, so PECOS
    enrolment groups and NPPES subparts are in the graph too — which is
    what makes an ownership disagreement visible on the NPI side rather
    than only between a CCN's chain and its system.
    """
    from .provider_crosswalk import SCOPE_ALL, get_crosswalk

    xw = get_crosswalk(scope=SCOPE_ALL)
    return build_parent_graph(crosswalk=xw, npi_frame=_sources(None, xw, None))


@lru_cache(maxsize=1)
def _cached_master_file() -> pd.DataFrame:
    return build_master_file()


def cached_master_file() -> pd.DataFrame:
    """The bundled-source master file, built once per process.

    A copy on every call. The frame is expensive to build (~9 s, most of
    it the ownership graph) and a route handler that filters it in place
    would corrupt the cache for the next request — which is exactly the
    bug the crosswalk's own cache-copy test was written for.
    """
    return _cached_master_file().copy()


def find_npis(query: Any, *, limit: int = 40,
              frame: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Resolve a query to master-file rows — the direction people ask in.

    A partner holding a claims extract has a ten-digit number, not a
    system. A partner holding a CIM has a name. Both are accepted, and
    an exact NPI is answered exactly rather than being buried in a
    substring sweep that also matches every NPI containing those digits.
    """
    text = str(query or "").strip()
    if not text:
        return pd.DataFrame(columns=list(MASTER_COLUMNS))
    rows = cached_master_file() if frame is None else frame
    if rows.empty:
        return rows

    digits = "".join(c for c in text if c.isdigit())
    if len(digits) == 10:
        exact = rows[rows["npi"].astype(str) == digits]
        if not exact.empty:
            return exact.head(max(1, int(limit)))

    needle = text.upper()
    names = (rows["legal_name"].astype(str).str.upper()
             + " " + rows["dba_name"].astype(str).str.upper())
    hits = rows[names.str.contains(needle, regex=False, na=False)]
    if hits.empty and digits:
        hits = rows[rows["npi"].astype(str).str.contains(digits, regex=False,
                                                         na=False)]
    return hits.head(max(1, int(limit)))


def master_file_coverage(frame: pd.DataFrame) -> Dict[str, Any]:
    """What the built file actually covers — measured, never estimated."""
    if frame.empty:
        return {"npis": 0}
    orgs = frame[frame["entity_label"] == "organization"]
    with_parent = orgs[orgs["final_parent"].astype(str).ne("")]
    people = frame[frame["entity_label"] == "individual"]
    return {
        "npis": len(frame),
        "organizations": len(orgs),
        "individuals": len(people),
        # Counted separately, never folded into the organization rate.
        # An individual only has a parent when an affiliation source
        # supplied one, so mixing the two would make the file look
        # better or worse depending on which sources happened to load.
        "individuals_with_a_parent": int(
            people["final_parent"].astype(str).ne("").sum()) if len(people) else 0,
        "organizations_with_a_parent": len(with_parent),
        "organization_parent_pct": (len(with_parent) / len(orgs) * 100.0
                                    if len(orgs) else 0.0),
        "linked_to_ccn": int(frame["ccn"].astype(str).ne("").sum()),
        "with_a_category": int(frame["taxonomy_category"].astype(str).ne("").sum()),
        "with_a_cbsa": int(frame["cbsa_code"].astype(str).ne("").sum()),
        "contested": int(pd.to_numeric(frame["parent_contested"],
                                       errors="coerce").fillna(0).sum()),
        "by_status": frame["status"].value_counts().to_dict(),
        "by_category": frame["taxonomy_category"].value_counts().head(15).to_dict(),
        "by_parent_tier": frame["parent_tier"].value_counts().to_dict(),
    }


def _clear_cache() -> None:
    """Test hook."""
    _cached_master_file.cache_clear()
    master_graph.cache_clear()
