"""Service-provider interface: a uniform adapter over each connector package.

Every connector under ``connectors/`` (openFDA, CMS Coverage, NPI Registry,
ICD-10) is an independent, self-contained vertical slice, but they were all
built to the *same* contract:

  * ``<pkg>.registry`` exposes a ``RegistryRow`` dataclass with identical
    field names plus ``registry_rows()`` / ``registry_as_dicts()`` /
    ``by_dataset_id()`` / ``dataset_ids()``;
  * ``<pkg>.tables`` defines exactly one ``*Store`` SQLite wrapper;
  * ``<pkg>.query`` exposes ``query()`` / ``aggregate()`` / ``QueryError``
    with the same signatures and the same ``as_dict`` result shapes;
  * ``<pkg>.lookup`` exposes ``v1_handlers(store) -> {route_template: fn}``.

Because that contract is uniform, one thin :class:`Adapter` can drive any
connector, and the top-level registry / HTTP surface / CLI can treat all of
them as one estate — without the individual connectors importing each other
or a shared core. This module is the only place that reaches across
connectors; each connector stays self-contained and independently testable.
"""
from __future__ import annotations

import importlib
import inspect
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

# Registration order = display order everywhere (registry, /v1/connectors, CLI).
CONNECTOR_NAMES: Tuple[str, ...] = (
    "openfda", "cms_coverage", "npi_registry", "icd10",
    "cms_open_data", "provider_data", "open_payments", "medicaid_data",
    "healthcare_gov", "cdc_data", "hrsa_data", "nih_reporter", "census_acs",
)

# Human labels for the estate view. Descriptive only.
CONNECTOR_LABELS: Dict[str, str] = {
    "openfda": "openFDA (drug + device)",
    "cms_coverage": "CMS Medicare Coverage Database",
    "npi_registry": "NPI Registry (NPPES v2.1)",
    "icd10": "ICD-10-CM + ICD-10-PCS (NLM Clinical Tables)",
    "cms_open_data": "CMS Open Data (data.cms.gov data-api)",
    "provider_data": "CMS Provider Data Catalog (Care Compare)",
    "open_payments": "CMS Open Payments (Sunshine Act)",
    "medicaid_data": "Medicaid Open Data (data.medicaid.gov)",
    "healthcare_gov": "Healthcare.gov Marketplace (QHP PUFs)",
    "cdc_data": "CDC Open Data (data.cdc.gov / Socrata)",
    "hrsa_data": "HRSA (HPSA shortage areas + health centers)",
    "nih_reporter": "NIH RePORTER (grants + publications)",
    "census_acs": "US Census ACS 5-year (demographics)",
}

# Query-string key aliases: a lookup handler parameter name that is exposed
# under a different query-string key. Keeps the generic binder honest without
# leaking per-connector routing into the unified server.
_QS_ALIASES: Dict[str, str] = {"code_type": "type"}


def _find_store_class(tables_mod: Any) -> type:
    """The single ``*Store`` class each connector's ``tables`` module owns."""
    candidates = [
        getattr(tables_mod, n) for n in dir(tables_mod)
        if n.endswith("Store") and isinstance(getattr(tables_mod, n), type)
    ]
    if not candidates:
        raise LookupError(f"no *Store class in {tables_mod.__name__}")
    # Prefer the one actually defined in this module (not an imported base).
    local = [c for c in candidates if c.__module__ == tables_mod.__name__]
    return (local or candidates)[0]


@dataclass(frozen=True)
class Adapter:
    """Uniform handle onto one connector package."""

    name: str
    label: str
    registry: Any
    query_mod: Any
    lookup_mod: Any
    tables_mod: Any
    store_cls: type

    # ── construction ──────────────────────────────────────────────────
    @classmethod
    def load(cls, name: str) -> "Adapter":
        reg = importlib.import_module(f"connectors.{name}.registry")
        qm = importlib.import_module(f"connectors.{name}.query")
        lm = importlib.import_module(f"connectors.{name}.lookup")
        tm = importlib.import_module(f"connectors.{name}.tables")
        return cls(
            name=name,
            label=CONNECTOR_LABELS.get(name, name),
            registry=reg, query_mod=qm, lookup_mod=lm, tables_mod=tm,
            store_cls=_find_store_class(tm),
        )

    # ── registry passthroughs ─────────────────────────────────────────
    def registry_as_dicts(self) -> List[Dict[str, Any]]:
        return self.registry.registry_as_dicts()

    def dataset_ids(self) -> List[str]:
        return list(self.registry.dataset_ids())

    def by_dataset_id(self) -> Dict[str, Any]:
        return self.registry.by_dataset_id()

    def base_urls(self) -> List[str]:
        return sorted({r["base_url"] for r in self.registry_as_dicts()})

    # ── store ─────────────────────────────────────────────────────────
    def open_store(self, db_path: str = ":memory:") -> Any:
        return self.store_cls(db_path)

    # ── query engine passthroughs (uniform signatures) ────────────────
    @property
    def QueryError(self) -> type:
        return self.query_mod.QueryError

    def query(self, store: Any, dataset_id: str, **kw: Any) -> Any:
        return self.query_mod.query(store, dataset_id, **kw)

    def aggregate(self, store: Any, dataset_id: str, **kw: Any) -> Any:
        return self.query_mod.aggregate(store, dataset_id, **kw)

    # ── lookups ───────────────────────────────────────────────────────
    def lookup_handlers(self, store: Any) -> Dict[str, Callable[..., Any]]:
        return self.lookup_mod.v1_handlers(store)


def load_all() -> Dict[str, Adapter]:
    """Every connector adapter, keyed by name, in registration order."""
    return {n: Adapter.load(n) for n in CONNECTOR_NAMES}


# ── generic lookup-route binder ───────────────────────────────────────
def match_template(template: str, parts: List[str]) -> Optional[Dict[str, str]]:
    """Match a ``/v1/lookup/code/{code}``-style template to path ``parts``.

    Returns an ordered dict ``{param_name: value}`` for the ``{...}``
    segments when every literal segment matches and the lengths line up,
    else ``None``.
    """
    tsegs = [s for s in template.strip("/").split("/") if s]
    if len(tsegs) != len(parts):
        return None
    params: Dict[str, str] = {}
    for tseg, pseg in zip(tsegs, parts):
        if tseg.startswith("{") and tseg.endswith("}"):
            params[tseg[1:-1]] = pseg
        elif tseg != pseg:
            return None
    return params


def invoke_handler(handler: Callable[..., Any], path_params: Dict[str, str],
                   qs: Dict[str, List[str]]) -> Any:
    """Call a ``v1_handlers`` lambda from parsed path params + query string.

    The connectors' handler lambdas take the template's ``{path}`` params as
    their leading positional arguments; any further parameters carry defaults
    and are optional query-string values (e.g. ICD-10's ``code_type`` /
    ``q`` / ``limit``). We bind path params positionally, then fill remaining
    parameters from the query string by name (honouring :data:`_QS_ALIASES`).
    """
    sig = inspect.signature(handler)
    pnames = list(sig.parameters)
    path_values = list(path_params.values())
    args: List[Any] = list(path_values)
    kwargs: Dict[str, Any] = {}
    for pname in pnames[len(path_values):]:
        qs_key = _QS_ALIASES.get(pname, pname)
        if qs_key in qs and qs[qs_key]:
            kwargs[pname] = qs[qs_key][0]
    return handler(*args, **kwargs)
