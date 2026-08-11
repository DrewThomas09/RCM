"""The CCN↔NPI link, harvested from NPPES and keyed on the CCN itself.

The hole this fills
-------------------
The crosswalk carries 48,510 certified facilities. Ninety of them
carried an NPI. That is not a rounding error, it is the join failing
almost completely, and it happened for two compounding reasons.

The bundled NPPES data is an *ambulance/EMS slice* — 20,401
organization NPIs in the 3416/3418/3439 taxonomy family, vendored for
a different workstream (see :mod:`npi_registry`, which says so in its
own docstring). Hospitals, SNFs and home health agencies are almost
entirely absent from it, so there was nothing to match against. And
:func:`provider_crosswalk._npi_for` matches on
``(normalized name, state, ZIP5)``, which is exactly the key that
breaks on the records that *are* present:

    CCN 010039  HUNTSVILLE HOSPITAL
    NPI 1447221056  THE HEALTH CARE AUTHORITY OF THE CITY OF HUNTSVILLE

Same building, same ZIP, same provider. Zero shared words. A hospital
enumerates under the public authority, municipal corporation or
religious order that holds its licence, and the brand on the door
appears in NPPES as a d/b/a at best. Name matching cannot recover
that, and no amount of fuzzing makes it safe to try — the names that
*do* look similar across a metro are usually different hospitals.

What this module is instead
---------------------------
A harvested table keyed on the CCN, so no name matching happens at
read time at all. Each row was resolved against the live NPPES
registry on the evidence that actually identifies a facility:

  **address** — the NPPES practice location is the same street, or at
  minimum the same city and ZIP5, as the certified facility, and

  **taxonomy** — the NPI is enumerated as a hospital (282N general
  acute, 282NC0060X critical access, 283Q psychiatric, 283X rehab,
  and the rest of the hospital family), not as the physician group,
  billing entity or foundation that shares the name.

Both are required. A name match at a different address is the single
most common way to attach the wrong NPI, because health systems
enumerate their medical groups under the flagship hospital's name.

Sometimes the provider just tells you
-------------------------------------
A minority of NPPES records carry a **PTAN** in their ``identifiers``
block — the Medicare provider number, issued by the MAC, which for an
institutional provider *is* the CCN with a hyphen in it::

    NPI 1467547265  PROVIDENCE HEALTH & SERVICES WASHINGTON
                    d/b/a PROVIDENCE ALASKA MEDICAL CENTER
                    identifiers: {issuer: PTAN, identifier: "02-0001"}
                                                             └ CCN 020001

That is not evidence to weigh, it is the provider's own enumeration
naming the CCN, and it is the strongest link this file can carry.
Where a harvested row has one, ``match_basis`` is ``ptan`` and the
loader *enforces* it: a PTAN that normalises to a different CCN than
the row claims drops the row rather than trusting the address, and
the drop is reported through :func:`ptan_contradictions`. A row can
be wrong about an address; it cannot be wrong about this and still be
worth keeping.

Most rows do not have one — Huntsville's does not — which is why
address and taxonomy remain the working rule rather than a fallback.

What the file does not claim
----------------------------
It is a harvest, not a census. A CCN absent from it means "not
resolved", never "has no NPI". Coverage is deliberately uneven —
hospitals first, because they carry the beds and the revenue — and
the rows record ``confidence`` so a caller can hold the medium ones
at arm's length: ``high`` means the street matched, ``medium`` means
only city and ZIP5 did.

Two checks run at load, on every row, every time:

  1. **The check digit.** :func:`npi_identifier.is_valid_npi` runs
     Luhn over ``80840`` + the NPI. A transcription slip in a
     harvested file is silent otherwise, and this is the one error
     class that can be caught with no network and no ambiguity.
  2. **One NPI per CCN.** A second row for a CCN already claimed is
     dropped rather than allowed to overwrite, and surfaced through
     :func:`bridge_conflicts` — a CCN with two candidate NPIs means
     the harvest was wrong about at least one of them, and silently
     keeping whichever sorted last would hide that.

The reverse — one NPI against several CCNs — is *not* an error and is
not dropped. A hospital that operates a distinct-part psychiatric or
rehab unit holds several CCNs under one enumeration, which is exactly
the relationship ``parent_ccn`` already models. It is reported, not
refused.
"""

from __future__ import annotations

import csv
import gzip
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .npi_identifier import is_valid_npi

_PACKAGE_DIR = Path(__file__).resolve().parent

#: Shipped as package data via the ``rcm_mc = ["data/*.csv.gz"]`` glob
#: in pyproject, alongside ``hcris.csv.gz``.
BRIDGE_PATH = _PACKAGE_DIR / "ccn_npi_bridge.csv.gz"

#: Written onto every crosswalk row this table fills, so a partner
#: reading the export can tell a harvested link from one the bundled
#: roster produced by name matching.
BRIDGE_SOURCE = "nppes ccn bridge"

BRIDGE_COLUMNS: Tuple[str, ...] = (
    "ccn", "npi", "npi_name", "npi_dba",
    "npi_taxonomy_code", "npi_taxonomy_desc",
    "npi_street", "npi_city", "npi_state", "npi_zip",
    "ptan", "match_basis", "confidence",
)

#: The street had to match, not merely the city and ZIP5. Callers that
#: want only the strongest links filter on this.
CONFIDENCE_HIGH = "high"
CONFIDENCE_MEDIUM = "medium"

#: ``match_basis`` for a row the provider's own PTAN confirms.
BASIS_PTAN = "ptan"


def normalise_ptan(value: object) -> str:
    """A PTAN reduced to the CCN it encodes, or "" if it encodes none.

    MACs write the institutional provider number several ways —
    ``02-0001``, ``020001``, ``02 0001`` — so strip the separators and
    compare the six characters that remain. Anything that is not a
    six-character alphanumeric after stripping is some other flavour
    of PTAN (a practitioner's, a legacy number) and is not a CCN;
    returning "" says so rather than guessing.
    """
    text = "".join(ch for ch in str(value or "") if ch.isalnum()).upper()
    return text if len(text) == 6 and text[:2].isdigit() else ""


@dataclass(frozen=True)
class BridgeRow:
    """One resolved CCN↔NPI link and the evidence behind it."""

    ccn: str
    npi: str
    npi_name: str
    npi_dba: str
    taxonomy_code: str
    taxonomy_desc: str
    street: str
    city: str
    state: str
    zip_code: str
    ptan: str
    match_basis: str
    confidence: str

    @property
    def is_high_confidence(self) -> bool:
        return self.confidence == CONFIDENCE_HIGH

    @property
    def is_ptan_confirmed(self) -> bool:
        """The provider's own Medicare number names this CCN."""
        return normalise_ptan(self.ptan) == self.ccn


@dataclass(frozen=True)
class PtanContradiction:
    """A row whose PTAN named a different CCN than the row claimed.

    Always a harvest error, never a judgement call: the provider filed
    the number themselves. Dropped at load and reported here so the
    count is visible rather than absorbed.
    """

    ccn: str
    npi: str
    ptan_ccn: str


@dataclass(frozen=True)
class BridgeConflict:
    """A CCN the harvest resolved to more than one NPI.

    Kept as a first-class result rather than logged and forgotten:
    every conflict is a place the harvest contradicted itself, and the
    count belongs in the same report as the coverage number so the two
    are read together.
    """

    ccn: str
    kept: str
    rejected: Tuple[str, ...]


def _clean(value: object) -> str:
    return str(value or "").strip()


def _read_rows(path: Path) -> List[Dict[str, str]]:
    """Rows from the shipped .csv.gz, or none if it is not there.

    A missing file is a normal state, not a failure: the harvest is
    incremental, and every caller already treats an unresolved CCN as
    ordinary. Raising here would take the whole crosswalk down over
    an absent optional enrichment.
    """
    if not path.exists():
        return []
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _load(path: Path) -> Tuple[Dict[str, BridgeRow],
                               List[BridgeConflict],
                               List[PtanContradiction]]:
    rows: Dict[str, BridgeRow] = {}
    contested: Dict[str, List[str]] = {}
    contradicted: List[PtanContradiction] = []

    for raw in _read_rows(path):
        ccn = _clean(raw.get("ccn")).upper()
        npi = _clean(raw.get("npi"))
        if not ccn or not is_valid_npi(npi):
            continue
        # A PTAN that names a different CCN is the provider's own
        # filing contradicting the harvest. Drop before the row can
        # claim the CCN and shut out a correct row behind it.
        ptan = _clean(raw.get("ptan"))
        ptan_ccn = normalise_ptan(ptan)
        if ptan_ccn and ptan_ccn != ccn:
            contradicted.append(
                PtanContradiction(ccn=ccn, npi=npi, ptan_ccn=ptan_ccn))
            continue
        seen = rows.get(ccn)
        if seen is not None:
            if seen.npi != npi:
                # A PTAN-confirmed row outranks whatever an address
                # match got there first; anything else loses the race
                # and is reported.
                if normalise_ptan(ptan) == ccn and not seen.is_ptan_confirmed:
                    contested.setdefault(ccn, []).append(seen.npi)
                else:
                    contested.setdefault(ccn, []).append(npi)
                    continue
            else:
                continue
        rows[ccn] = BridgeRow(
            ccn=ccn,
            npi=npi,
            npi_name=_clean(raw.get("npi_name")),
            npi_dba=_clean(raw.get("npi_dba")),
            taxonomy_code=_clean(raw.get("npi_taxonomy_code")),
            taxonomy_desc=_clean(raw.get("npi_taxonomy_desc")),
            street=_clean(raw.get("npi_street")),
            city=_clean(raw.get("npi_city")),
            state=_clean(raw.get("npi_state")).upper(),
            zip_code=_clean(raw.get("npi_zip")),
            ptan=ptan,
            match_basis=_clean(raw.get("match_basis")),
            confidence=_clean(raw.get("confidence")).lower() or CONFIDENCE_MEDIUM,
        )

    conflicts = [
        BridgeConflict(ccn=ccn, kept=rows[ccn].npi, rejected=tuple(sorted(set(others))))
        for ccn, others in sorted(contested.items())
    ]
    return rows, conflicts, contradicted


@lru_cache(maxsize=2)
def _cached(path_str: str) -> Tuple[Dict[str, BridgeRow],
                                    Tuple[BridgeConflict, ...],
                                    Tuple[PtanContradiction, ...]]:
    rows, conflicts, contradictions = _load(Path(path_str))
    return rows, tuple(conflicts), tuple(contradictions)


def load_bridge(path: Optional[Path] = None) -> Dict[str, BridgeRow]:
    """CCN → :class:`BridgeRow` for every row that survives validation."""
    return _cached(str(path or BRIDGE_PATH))[0]


def bridge_conflicts(path: Optional[Path] = None) -> Tuple[BridgeConflict, ...]:
    """CCNs the harvest resolved to more than one NPI."""
    return _cached(str(path or BRIDGE_PATH))[1]


def ptan_contradictions(path: Optional[Path] = None) -> Tuple[PtanContradiction, ...]:
    """Rows dropped because their PTAN named a different CCN."""
    return _cached(str(path or BRIDGE_PATH))[2]


def shared_npis(path: Optional[Path] = None) -> Dict[str, Tuple[str, ...]]:
    """NPIs that cover several CCNs, each with the CCNs it covers.

    Expected rather than suspect — a hospital with a distinct-part
    rehab or psychiatric unit holds several CCNs under one enumeration
    — but worth being able to see, because an NPI stretched across
    facilities in different *states* is a harvest error rather than a
    distinct-part unit.
    """
    grouped: Dict[str, List[str]] = {}
    for row in load_bridge(path).values():
        grouped.setdefault(row.npi, []).append(row.ccn)
    return {npi: tuple(sorted(ccns))
            for npi, ccns in sorted(grouped.items()) if len(ccns) > 1}


def cross_state_npis(path: Optional[Path] = None) -> Dict[str, Tuple[str, ...]]:
    """The subset of :func:`shared_npis` whose CCNs span states.

    A CCN's first two digits are its state code, so this needs no join.
    One NPI certified in two states is not a distinct-part unit; it is
    the harvest having attached a chain's corporate NPI to a local
    facility, and it should be reviewed before the row is trusted.
    """
    return {npi: ccns for npi, ccns in shared_npis(path).items()
            if len({c[:2] for c in ccns}) > 1}


def bridge_summary(path: Optional[Path] = None) -> Dict[str, object]:
    """Coverage and its caveats in one dict, for the page and the tests."""
    rows = load_bridge(path)
    high = sum(1 for r in rows.values() if r.is_high_confidence)
    return {
        "ccns_resolved": len(rows),
        "distinct_npis": len({r.npi for r in rows.values()}),
        "ptan_confirmed": sum(1 for r in rows.values() if r.is_ptan_confirmed),
        "high_confidence": high,
        "medium_confidence": len(rows) - high,
        "states": len({ccn[:2] for ccn in rows}),
        "conflicting_ccns": len(bridge_conflicts(path)),
        "ptan_contradictions": len(ptan_contradictions(path)),
        "npis_covering_several_ccns": len(shared_npis(path)),
        "npis_spanning_states": len(cross_state_npis(path)),
    }


def _clear_cache() -> None:
    """Drop the memoized load. Tests writing a fixture file need this."""
    _cached.cache_clear()
