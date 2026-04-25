"""CMS Medicare Physician Referrals loader.

The CMS Office of Enterprise Data and Analytics publishes an
annual shared-patient file recording every NPI-to-NPI Medicare
referral relationship that exceeded an 11-patient threshold.
Public download: https://data.cms.gov/.../shared-patient-patterns

Schema (the columns we care about):

    npi_1                 — referring provider NPI
    npi_2                 — receiving provider NPI
    patient_count         — beneficiaries shared in the period
    transaction_count     — total transactions (optional)

This loader streams the CSV row-by-row, builds a ReferralGraph,
and (when a PricingStore with populated pricing_nppes is
supplied) joins each NPI against the NPPES table to populate
``node_org`` with the organizational name. That tagging is what
the leakage + key-person-risk computations depend on.

For diligence-grade work the file is ~5GB unzipped and 10M+ rows
nationwide; partners typically pre-filter to a state or list of
CCNs of interest. The loader stays bounded in memory regardless
of input size — ReferralGraph is sparse and only adds nodes that
appear as edge endpoints.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, Optional, Set

from .graph import ReferralEdge, ReferralGraph


# Column-name candidates per axis (CMS file headers vary across
# publication years). Loader picks whichever is present.
_REFERRER_COLS = ("npi_1", "from_npi", "referring_npi", "src")
_RECEIVER_COLS = ("npi_2", "to_npi", "receiving_npi", "dst")
_COUNT_COLS = (
    "patient_count", "shared_patient_count",
    "beneficiary_count", "count",
)


def _pick_column(headers, candidates) -> Optional[str]:
    """Return the first candidate column name present in headers,
    or None if no candidate matches."""
    header_set = set(headers or ())
    for c in candidates:
        if c in header_set:
            return c
    return None


@dataclass
class CmsReferralRow:
    """Parsed shared-patient row."""
    referring_npi: str
    receiving_npi: str
    patient_count: float


def parse_cms_referrals_csv(
    path: object,
    *,
    min_patient_count: int = 11,
    state_filter: Optional[Iterable[str]] = None,
    npi_filter: Optional[Iterable[str]] = None,
) -> Iterator[CmsReferralRow]:
    """Stream-parse a CMS shared-patient CSV.

    Args:
      path: filesystem path to the CSV.
      min_patient_count: drop edges below the threshold (CMS
        suppresses anything below 11 already, but we re-enforce).
      state_filter: optional set of state codes; rows are kept
        only if either NPI's state column matches. Requires the
        file to carry state columns (newer files do).
      npi_filter: optional set of NPIs; rows are kept only if
        either endpoint NPI is in the set. Useful for pre-
        filtering to "every NPI within an MSO" before building
        the graph.
    """
    p = Path(str(path))
    if not p.is_file():
        raise FileNotFoundError(f"CMS referrals CSV not found at {p}")

    states_set = ({s.upper() for s in state_filter}
                  if state_filter else None)
    npi_set = ({str(n).strip() for n in npi_filter}
               if npi_filter else None)

    with p.open("r", encoding="utf-8", errors="replace",
                newline="") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames:
            return
        ref_col = _pick_column(reader.fieldnames, _REFERRER_COLS)
        rec_col = _pick_column(reader.fieldnames, _RECEIVER_COLS)
        cnt_col = _pick_column(reader.fieldnames, _COUNT_COLS)
        if not (ref_col and rec_col):
            raise ValueError(
                f"CSV missing referrer/receiver columns; "
                f"saw: {reader.fieldnames}")

        for row in reader:
            ref_npi = (row.get(ref_col) or "").strip()
            rec_npi = (row.get(rec_col) or "").strip()
            if not (ref_npi and rec_npi):
                continue
            if npi_set and not (
                    ref_npi in npi_set or rec_npi in npi_set):
                continue
            try:
                count = float(row[cnt_col]) if cnt_col else 1.0
            except (TypeError, ValueError, KeyError):
                count = 1.0
            if count < min_patient_count:
                continue
            if states_set:
                # If the file has a state column, enforce. We try
                # a few common variants — CMS files differ.
                ref_state = (row.get("state_1") or row.get(
                    "from_state") or "").upper()
                rec_state = (row.get("state_2") or row.get(
                    "to_state") or "").upper()
                if not (ref_state in states_set
                        or rec_state in states_set):
                    continue
            yield CmsReferralRow(
                referring_npi=ref_npi,
                receiving_npi=rec_npi,
                patient_count=count,
            )


def build_graph_from_cms(
    path: object,
    *,
    pricing_store: Any = None,
    min_patient_count: int = 11,
    state_filter: Optional[Iterable[str]] = None,
    npi_filter: Optional[Iterable[str]] = None,
) -> ReferralGraph:
    """End-to-end: parse the CMS shared-patient CSV → build a
    ReferralGraph → tag every node with its NPPES organization
    when a PricingStore is supplied.

    Returns the populated graph. Use the existing centrality /
    leakage / simulate helpers downstream.
    """
    g = ReferralGraph()
    edge_count = 0
    npis_seen: Set[str] = set()

    for r in parse_cms_referrals_csv(
        path,
        min_patient_count=min_patient_count,
        state_filter=state_filter,
        npi_filter=npi_filter,
    ):
        g.add_edge(r.referring_npi, r.receiving_npi,
                   weight=r.patient_count)
        npis_seen.add(r.referring_npi)
        npis_seen.add(r.receiving_npi)
        edge_count += 1

    # NPPES enrichment for org tagging
    if pricing_store and npis_seen:
        try:
            with pricing_store.connect() as con:
                for npi in npis_seen:
                    rec = con.execute(
                        "SELECT organization_name FROM "
                        "pricing_nppes WHERE npi = ?",
                        (npi,),
                    ).fetchone()
                    if rec and rec["organization_name"]:
                        g.set_node_org(npi, rec["organization_name"])
        except Exception:  # noqa: BLE001
            # NPPES table may not exist; leave nodes untagged.
            pass

    return g
