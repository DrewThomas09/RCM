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
    "oig_leie", "bls_qcew", "healthdata_gov", "hcpcs", "qpp", "rxnorm",
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
    "oig_leie": "HHS OIG LEIE (exclusion list)",
    "bls_qcew": "BLS QCEW (healthcare employment + wages)",
    "healthdata_gov": "healthdata.gov (HHS-wide meta-catalog)",
    "hcpcs": "HCPCS Level II (NLM Clinical Tables)",
    "qpp": "CMS Quality Payment Program (MIPS/APM)",
    "rxnorm": "RxNorm drug identity (NLM RxNav)",
}

# Query-string key aliases: a lookup handler parameter name that is exposed
# under a different query-string key. Keeps the generic binder honest without
# leaking per-connector routing into the unified server.
_QS_ALIASES: Dict[str, str] = {"code_type": "type"}

# ── storage-flag styles per connector CLI ─────────────────────────────
# The earlier root-style slices take a top-level ``--root DIR`` (their db
# lives at ``{root}/{name}.db``); everything else takes ``--db FILE``. Two
# catalog connectors declare ``--db`` per subcommand, so the flag must
# FOLLOW the verb or argparse rejects the invocation. Declared here (the
# one module that already reaches across connectors) so the refresh
# driver, the RCM-MC estate page's copy-ready hints, and tests all agree
# on the same mapping instead of re-deriving it.
ROOT_STYLE_CLIS: Tuple[str, ...] = (
    "openfda", "cms_coverage", "npi_registry", "icd10", "hrsa_data", "hcpcs",
    "qpp", "rxnorm")
SUBCMD_DB_STYLE_CLIS: Tuple[str, ...] = ("cms_open_data", "open_payments")

# Connectors the estate-level ``refresh`` sweep cannot ingest unattended:
# their ingest verbs need domain arguments (openFDA search windows, NPI
# lists, ICD-10 code seeds). Surfaces that tell a user how to populate a
# connector must not point these at ``refresh`` — it skips them entirely.
MANUAL_INGEST_CLIS: Tuple[str, ...] = ("openfda", "npi_registry", "icd10",
                                       "rxnorm")

# ── open-data catalog columns per catalog-syncing connector ───────────
# Seven connectors sync a whole upstream open-data catalog into a table
# (data.cms.gov 158 datasets, Provider Data Catalog 234, Open Payments 74,
# data.medicaid.gov 541, Healthcare.gov 337, data.cdc.gov ~1,500,
# healthdata.gov 23,080). Every one of those is pullable on demand through
# its connector's generic fetched-rows slot — but only if you already know
# its identifier, which made "everything CMS publishes" reachable in
# principle and undiscoverable in practice.
#
# The catalogs are the same IDEA with different column names (DKAN says
# ``title``/``identifier``, Socrata says ``name``/``dataset_uid``), so the
# mapping is declared here — the one module that already reaches across
# connectors and already carries this kind of cross-connector metadata —
# rather than reimplemented seven times. A connector absent from this map
# simply has no catalog (openFDA, ICD-10, HCPCS, QPP, RxNorm, NPI Registry,
# …) and is skipped by every catalog-search surface.
#
# Field meanings: (table, id column, title column, description column,
# last-modified column, resource-URL column). Every value is a real column
# of that table — pinned by connectors/tests/test_catalog_search.py, so a
# renamed column fails loudly instead of silently returning nothing.
CATALOG_SPECS: Dict[str, Dict[str, str]] = {
    "cms_open_data": {
        "table": "cms_open_data_catalog", "id": "dataset_key",
        "title": "title", "description": "description",
        "modified": "modified", "url": "api_url"},
    "provider_data": {
        "table": "provider_data_catalog", "id": "identifier",
        "title": "title", "description": "description",
        "modified": "modified", "url": "csv_url"},
    "open_payments": {
        "table": "open_payments_catalog", "id": "identifier",
        "title": "title", "description": "description",
        "modified": "modified", "url": "api_url"},
    "medicaid_data": {
        "table": "medicaid_data_catalog", "id": "identifier",
        "title": "title", "description": "description",
        "modified": "modified", "url": "api_url"},
    "healthcare_gov": {
        "table": "healthcare_gov_catalog", "id": "identifier",
        "title": "title", "description": "description",
        "modified": "modified", "url": "download_url"},
    "cdc_data": {
        "table": "cdc_data_catalog", "id": "dataset_uid",
        "title": "name", "description": "description",
        "modified": "data_updated_at", "url": "data_uri"},
    "healthdata_gov": {
        "table": "healthdata_gov_catalog", "id": "dataset_uid",
        "title": "name", "description": "description",
        "modified": "data_updated_at", "url": "data_uri"},
}

CATALOG_CONNECTORS: Tuple[str, ...] = tuple(
    n for n in CONNECTOR_NAMES if n in CATALOG_SPECS)

# The uniform result row every catalog search returns, whichever connector
# answered. Callers join/merge on these names and nothing else.
CATALOG_ROW_FIELDS: Tuple[str, ...] = (
    "connector", "dataset_id", "title", "description", "modified", "url")


def storage_argv(name: str, db_dir: str) -> List[str]:
    """The argv fragment pointing *name*'s CLI at ``{db_dir}/{name}.db``.

    Root-style connectors write ``{root}/{name}.db`` themselves, so their
    ``--root`` IS the db dir — the exact layout the unified server's
    ``open_stores()`` expects.
    """
    if name in ROOT_STYLE_CLIS:
        return ["--root", db_dir.rstrip("/")]
    return ["--db", f"{db_dir.rstrip('/')}/{name}.db"]


def cli_query_argv(name: str, dataset_id: str, db_dir: str = "var/connectors",
                   limit: int = 10) -> List[str]:
    """A correct, copy-ready ``query`` argv for one connector CLI.

    The storage flag is the part callers kept getting wrong: without it
    the per-connector CLIs query an empty default store and print 0 rows
    even after a full ingest. Subcommand-``--db`` CLIs need the flag after
    the verb; everyone else takes it before.
    """
    verb = ["query", dataset_id, "--limit", str(int(limit))]
    storage = storage_argv(name, db_dir)
    if name in SUBCMD_DB_STYLE_CLIS:
        return [*verb, *storage]
    return [*storage, *verb]


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

    # ── open-data catalog search ──────────────────────────────────────
    @property
    def has_catalog(self) -> bool:
        """Whether this connector syncs a searchable upstream catalog."""
        return self.name in CATALOG_SPECS

    def catalog_search(self, store: Any, q: str, *, limit: int = 50
                       ) -> List[Dict[str, Any]]:
        """Keyword search over this connector's synced catalog.

        Returns uniform :data:`CATALOG_ROW_FIELDS` rows (``[]`` for a
        connector with no catalog, so a caller can fan out over the whole
        estate without special-casing). Matching is a case-insensitive
        substring over the catalog's title OR description — the two fields
        every upstream catalog carries under one name or another.

        Safety: the only interpolated identifiers are the table and column
        names from :data:`CATALOG_SPECS`, which are module constants; the
        search term and limit are bound parameters. ``limit`` is clamped
        the same way the per-connector query engines clamp theirs.
        """
        spec = CATALOG_SPECS.get(self.name)
        if spec is None:
            return []
        term = str(q or "").strip()
        if not term:
            return []
        n = _clamp_limit(limit)
        # SQLite's LIKE is already case-insensitive for ASCII; the explicit
        # LOWER() pair keeps that true regardless of the connection's
        # case_sensitive_like pragma.
        sql = (
            f"SELECT {spec['id']} AS dataset_id, {spec['title']} AS title, "
            f"{spec['description']} AS description, "
            f"{spec['modified']} AS modified, {spec['url']} AS url "
            f"FROM {spec['table']} "
            f"WHERE LOWER({spec['title']}) LIKE ? "
            f"OR LOWER({spec['description']}) LIKE ? "
            f"ORDER BY {spec['title']} LIMIT ?"
        )
        like = f"%{term.lower()}%"
        rows = store.fetchall(sql, (like, like, n))
        return [self._catalog_row(r) for r in rows]

    def _catalog_row(self, row: Any) -> Dict[str, Any]:
        """One raw catalog hit → the uniform row (absent values become '')."""
        d = dict(row)
        out: Dict[str, Any] = {"connector": self.name}
        for field in CATALOG_ROW_FIELDS:
            if field == "connector":
                continue
            value = d.get(field)
            out[field] = "" if value is None else str(value)
        return out


_CATALOG_LIMIT_DEFAULT = 50
_CATALOG_LIMIT_MAX = 1000


def _clamp_limit(limit: Any, default: int = _CATALOG_LIMIT_DEFAULT,
                 lo: int = 1, hi: int = _CATALOG_LIMIT_MAX) -> int:
    """Clamp a caller-supplied limit; junk falls back to the default."""
    try:
        n = int(limit)
    except (TypeError, ValueError):
        return default
    return max(lo, min(n, hi))


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
