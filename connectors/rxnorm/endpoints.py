"""Declarative specs for every RxNav (RxNorm) dataset this connector ingests.

One :class:`EndpointSpec` per registered dataset. The spec is the single
place that knows the RxNav-specific quirks: the URL path template, the
envelope key its payload arrives under, which canonical table the
normalizer writes into, and the roster kind a pull is driven by. The
registry rows (:mod:`connectors.rxnorm.registry`) and the connector both
read these — adding or retuning a dataset is a data edit here, never new
routing logic elsewhere.

RxNorm is the NLM's normalized drug vocabulary and it is the **join
dimension** for the drug money already in this estate: Medicaid NADAC
and State Drug Utilization (``medicaid_data``), Medicare Part B and
Part D spending by drug (``cms_open_data``), and openFDA's NDC
directory. Those files identify products by NDC or by a messy label
name; RxNorm resolves both to a stable ``rxcui``, its ingredient set,
and its ATC / DailyMed pharmacologic class — which is what turns
per-product spend into per-ingredient or per-class spend. It plays the
same role for drugs that ``icd10`` plays for diagnoses and ``hcpcs``
for procedures.

Three roster-driven datasets, all resolving into the same concept
dimension plus their own crosswalk table:

``ndc``
    ``/rxcui.json?idtype=NDC&id={ndc}`` — an NDC (the identifier NADAC,
    SDUD and the Part D files carry) to its RxCUI. Fills
    ``xwalk_ndc_rxcui`` plus the concept row.
``name``
    ``/rxcui.json?name={name}&search=2`` with an
    ``/approximateTerm.json`` fallback — a free-text drug name (what
    claim and chargemaster extracts carry) to its RxCUI. Fills
    ``xwalk_name_rxcui`` plus the concept row.
``concept``
    ``/rxcui/{rxcui}/properties.json`` + ``/related.json?tty=IN`` +
    ``/rxclass/class/byRxcui.json`` — enrich an RxCUI you already have
    into name, ingredients and drug classes. Fills
    ``dim_rxnorm_concept``.

All three are **roster-driven** (per-identifier, like the NPI Registry
and QPP eligibility connectors), so they are manual-ingest: a pull needs
a caller-supplied ``--ndcs`` / ``--names`` / ``--rxcuis`` list. The
natural roster is a distinct-NDC query against the NADAC / SDUD / Part D
tables this estate already ingests.

Response shapes below are the ones this repo's existing RxNav client
(``rcm_mc/npi_cleaner/vendor_v49/npi_recovery/clients.py``) resolves
against in production, so the envelope keys are verified, not inferred.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

_RXNAV_BASE = "https://rxnav.nlm.nih.gov/REST"

# Verified RxNav route templates + the envelope key each answers under.
NDC_PATH = "/rxcui.json"                       # ?idtype=NDC&id={ndc}   → idGroup
NAME_PATH = "/rxcui.json"                      # ?name={name}&search=2 → idGroup
APPROXIMATE_PATH = "/approximateTerm.json"     # ?term=&maxEntries=    → approximateGroup
PROPERTIES_PATH_TEMPLATE = "/rxcui/{rxcui}/properties.json"   # → properties
RELATED_PATH_TEMPLATE = "/rxcui/{rxcui}/related.json"         # ?tty=IN → relatedGroup
CLASS_PATH = "/rxclass/class/byRxcui.json"     # ?rxcui=&relaSource=  → rxclassDrugInfoList

# Class sources tried in order when enriching a concept. ATC is the
# primary pharmacologic classification; many biologics (immune globulin,
# for instance) carry no ATC class but do carry a DailyMed one, so the
# fallback keeps the class column from going blank on exactly the
# high-cost injectables a Part B analysis cares about.
CLASS_SOURCES: Tuple[str, ...] = ("ATC", "DAILYMED")


@dataclass(frozen=True)
class EndpointSpec:
    """One RxNav dataset.

    Attributes
    ----------
    key:
        Short dataset id, also the ``/v1/query/{dataset}`` slug suffix
        and the value written into each row's ``source_endpoint`` column.
    kind:
        ``ndc`` | ``name`` | ``concept`` — drives which resolve path and
        normalizer mapper runs.
    path:
        The URL path this spec's first request hits.
    target_table:
        Canonical table the normalizer upserts the dataset's own grain
        into. Every kind ALSO contributes a ``dim_rxnorm_concept`` row,
        because resolving an identifier always yields its concept.
    roster_param:
        The ``params`` key a pull's identifier roster arrives under.
    join_keys:
        Keys other datasets join to this one on (``ndc`` joins NADAC /
        SDUD / Part D prescriber files; ``rxcui`` joins the concept dim).
    """

    key: str
    kind: str
    path: str
    target_table: str
    roster_param: str
    join_keys: Tuple[str, ...] = ()
    refresh_cadence: str = "monthly"
    date_field: str = ""
    default_params: Dict[str, str] = field(default_factory=dict)

    @property
    def dataset_id(self) -> str:
        return f"rxnorm_{self.key}"

    @property
    def base_url(self) -> str:
        return _RXNAV_BASE


_SPECS: List[EndpointSpec] = [
    EndpointSpec(
        key="ndc",
        kind="ndc",
        path=NDC_PATH,
        target_table="xwalk_ndc_rxcui",
        roster_param="ndcs",
        join_keys=("ndc", "rxcui"),
        default_params={"idtype": "NDC"},
    ),
    EndpointSpec(
        key="name",
        kind="name",
        path=NAME_PATH,
        target_table="xwalk_name_rxcui",
        roster_param="names",
        join_keys=("rxcui",),
        default_params={"search": "2"},
    ),
    EndpointSpec(
        key="concept",
        kind="concept",
        path=PROPERTIES_PATH_TEMPLATE,
        target_table="dim_rxnorm_concept",
        roster_param="rxcuis",
        join_keys=("rxcui",),
    ),
]

ENDPOINTS: Dict[str, EndpointSpec] = {s.key: s for s in _SPECS}


def get_endpoint(key: str) -> EndpointSpec:
    """Look up an endpoint spec by key, raising a clear error if absent."""
    try:
        return ENDPOINTS[key]
    except KeyError as exc:
        raise KeyError(
            f"unknown RxNorm endpoint {key!r}; known: {sorted(ENDPOINTS)}"
        ) from exc
