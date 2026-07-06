"""Read-only bridge to the repo-root ``connectors/`` estate.

The public-API connector estate (openFDA, CMS Coverage, NPI Registry,
ICD-10, CMS Open Data, Provider Data Catalog, Open Payments, Medicaid
Open Data, Healthcare.gov, CDC, HRSA, NIH RePORTER, Census ACS — plus
whatever connectors register at the root later; everything here is
count-agnostic) lives at the *repository root*, one level above the
``RCM_MC`` package — it is a sibling estate, not a package dependency. A wheel install of ``rcm_mc``
does not ship it, so every import here is optional and lazy: nothing in
this module touches ``sys.path`` or imports ``connectors`` at module
import time, and every public function degrades to ``[]`` / ``{}`` /
``None`` when the estate is absent. The app must render (with an honest
empty state) either way — that is why this bridge exists instead of a
plain ``import connectors`` in the page renderers.

Queries issued through this bridge are **read-only by design**: the app
is a browser over whatever a separate ingest (``python -m connectors.cli
refresh --db var/connectors`` or a per-connector ``discover``/``fetch``)
has already written. When a connector's SQLite file does not exist we
open ``:memory:`` instead so a sample query can never create stray
``.db`` files inside a deployment.

Root resolution order (re-checked on every call so tests can repoint the
estate via the environment):

1. ``RCM_MC_CONNECTORS_ROOT`` — honored only if it actually contains
   ``connectors/_spi.py``; a bogus value means "estate unavailable",
   which is exactly how the unavailable path is exercised in tests.
2. Walk the parents of this file looking for ``connectors/_spi.py``.

``RCM_MC_CONNECTORS_DB`` overrides the SQLite directory (default
``<repo_root>/var/connectors``). The directory is never created here.

Name collision, and why the import below is deliberately weird: RCM_MC
ships its *own* top-level ``connectors`` package (the NPPES-universe
workstream at ``RCM_MC/connectors/``), and the test suite imports it —
so ``sys.modules["connectors"]`` may already belong to the in-app
package (or get claimed by it later). The estate is therefore imported
inside a save/swap/restore of ``sys.modules``/``sys.path``: the estate
loads eagerly (its registry imports every connector at import time),
this module keeps direct references to the loaded module objects, and
the interpreter state is restored so the in-app package keeps working.
Neither package ever sees the other.
"""
from __future__ import annotations

import contextlib
import importlib
import os
import sys
import threading
from typing import Any

# Lazy singleton: (resolved_root, registry_module, spi_module).
# Cached per resolved root so an env repoint invalidates the handles.
_HANDLES: tuple[str, Any, Any] | None = None
_LOAD_LOCK = threading.RLock()


def repo_root() -> str | None:
    """The directory containing ``connectors/_spi.py``, or ``None``.

    Re-resolved on every call (cheap stat) so an ``RCM_MC_CONNECTORS_ROOT``
    change between requests — the tests' unavailable-estate path — takes
    effect without a process restart.
    """
    env = os.environ.get("RCM_MC_CONNECTORS_ROOT")
    if env:
        root = os.path.abspath(env)
        if os.path.isfile(os.path.join(root, "connectors", "_spi.py")):
            return root
        return None  # explicit-but-bogus root == estate unavailable
    here = os.path.abspath(os.path.dirname(__file__))
    cur = here
    for _ in range(8):
        if os.path.isfile(os.path.join(cur, "connectors", "_spi.py")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return None


def _owns_name(mod: Any, root: str) -> bool:
    """True when the ``connectors`` module in sys.modules IS the estate."""
    mod_file = getattr(mod, "__file__", "") or ""
    expected = os.path.join(root, "connectors") + os.sep
    return os.path.abspath(mod_file).startswith(expected)


def _load() -> tuple[str, Any, Any] | None:
    """(root, connectors.registry, connectors._spi) or None. Cached.

    See the module docstring for why this swaps ``sys.modules`` instead
    of doing a plain import: the top-level name ``connectors`` is also
    used by an in-app RCM_MC package, and the two must coexist.
    """
    global _HANDLES
    root = repo_root()
    if root is None:
        return None
    with _LOAD_LOCK:
        if _HANDLES is not None and _HANDLES[0] == root:
            return _HANDLES
        existing = sys.modules.get("connectors")
        if existing is not None and _owns_name(existing, root):
            # The estate already owns the name (e.g. a process started
            # from the repo root) — import submodules in place.
            try:
                registry = importlib.import_module("connectors.registry")
                spi = importlib.import_module("connectors._spi")
            except Exception:
                return None
            _HANDLES = (root, registry, spi)
            return _HANDLES
        # The name is free, or taken by the in-app package: load the
        # estate under a scratch swap and restore the interpreter after.
        saved = {k: v for k, v in sys.modules.items()
                 if k == "connectors" or k.startswith("connectors.")}
        for k in saved:
            del sys.modules[k]
        sys.path.insert(0, root)
        try:
            registry = importlib.import_module("connectors.registry")
            spi = importlib.import_module("connectors._spi")
            _HANDLES = (root, registry, spi)
            return _HANDLES
        except Exception:
            return None
        finally:
            # Drop every estate name and put back whatever was there so
            # the in-app ``connectors`` package (NPPES universe) keeps
            # importing normally. The estate stays alive through the
            # direct module references captured above.
            for k in [k for k in sys.modules
                      if k == "connectors" or k.startswith("connectors.")]:
                del sys.modules[k]
            sys.modules.update(saved)
            with contextlib.suppress(ValueError):
                sys.path.remove(root)


def estate_available() -> bool:
    """True when the repo-root connector estate is importable."""
    return _load() is not None


def estate_catalog() -> dict[str, Any]:
    """``connectors.registry.catalog()`` or ``{}`` when absent."""
    h = _load()
    if h is None:
        return {}
    try:
        return h[1].catalog()
    except Exception:
        return {}


def connectors_summary() -> list[dict[str, Any]]:
    """One row per connector (label, base URLs, dataset count) or ``[]``."""
    h = _load()
    if h is None:
        return []
    try:
        return h[1].connectors_summary()
    except Exception:
        return []


def all_datasets() -> list[dict[str, Any]]:
    """Every registry row across every connector, or ``[]``."""
    h = _load()
    if h is None:
        return []
    try:
        return h[1].all_registry_rows()
    except Exception:
        return []


def dataset_owner(dataset_id: str) -> str | None:
    """Which connector owns ``dataset_id`` (``None`` if unknown/absent)."""
    h = _load()
    if h is None:
        return None
    try:
        return h[1].dataset_owner(dataset_id)
    except Exception:
        return None


def adapter_for(connector_name: str) -> Any | None:
    """The estate ``Adapter`` for one connector, or ``None``.

    Exposed so callers (and tests) can reach a connector's real store
    class without importing ``connectors.*`` themselves — the top-level
    name may belong to the in-app package (see module docstring).
    """
    h = _load()
    if h is None:
        return None
    try:
        return h[1].adapters().get(connector_name)
    except Exception:
        return None


def connector_label(name: str) -> str:
    """Human label for a connector name (falls back to the name)."""
    h = _load()
    if h is None:
        return name
    try:
        return h[2].CONNECTOR_LABELS.get(name, name)
    except Exception:
        return name


def db_dir() -> str:
    """Directory holding the per-connector SQLite files (never created).

    ``RCM_MC_CONNECTORS_DB`` wins; default is ``<repo_root>/var/connectors``.
    Empty string when the estate itself cannot be located and no override
    is set — callers treat a missing file the same way either way.
    """
    env = os.environ.get("RCM_MC_CONNECTORS_DB")
    if env:
        return env
    root = repo_root()
    if root is None:
        return ""
    return os.path.join(root, "var", "connectors")


def _db_path(connector_name: str) -> str | None:
    """Existing SQLite file for a connector, or ``None``."""
    d = db_dir()
    if not d:
        return None
    path = os.path.join(d, f"{connector_name}.db")
    return path if os.path.isfile(path) else None


def open_store(connector_name: str) -> tuple[Any, Any] | None:
    """(adapter, store) for one connector, or ``None`` when unavailable.

    Opens the ingested ``{db_dir}/{name}.db`` when it exists, else an
    in-memory store — sample queries must never create stray files.
    Callers own closing the returned store.
    """
    h = _load()
    if h is None:
        return None
    try:
        adapter = h[1].adapters().get(connector_name)
        if adapter is None:
            return None
        path = _db_path(connector_name) or ":memory:"
        return adapter, adapter.open_store(path)
    except Exception:
        return None


def _clamp(value: Any, default: int, lo: int, hi: int) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    return max(lo, min(n, hi))


def dataset_row(dataset_id: str) -> dict[str, Any] | None:
    """The registry row (declarative dict) for one dataset, or ``None``."""
    for row in all_datasets():
        if row.get("dataset_id") == dataset_id:
            return row
    return None


def dataset_columns(dataset_id: str) -> list[str]:
    """Column whitelist of the dataset's target table, or ``[]``."""
    h = _load()
    if h is None:
        return []
    owner = dataset_owner(dataset_id)
    if owner is None:
        return []
    try:
        adapter = h[1].adapters()[owner]
        row = adapter.by_dataset_id().get(dataset_id)
        if row is None:
            return []
        tdef = adapter.tables_mod.TABLES.get(row.target_table)
        return list(tdef.columns) if tdef is not None else []
    except Exception:
        return []


def sample_rows(dataset_id: str, limit: int = 10,
                filters: dict[str, Any] | None = None) -> dict[str, Any]:
    """Up to ``limit`` (clamped 1..100) rows as ``QueryResult.as_dict()``.

    ``{}`` on any absence or ``QueryError`` — the page renders an empty
    state instead of a 500 when a dataset id is bogus or the estate is
    missing. Runs against the ingested db when present, else ``:memory:``
    (which yields an empty-but-valid result, not an error).
    """
    owner = dataset_owner(dataset_id)
    if owner is None:
        return {}
    handle = open_store(owner)
    if handle is None:
        return {}
    adapter, store = handle
    try:
        result = adapter.query(store, dataset_id, filters=filters or {},
                               limit=_clamp(limit, 10, 1, 100))
        return result.as_dict()
    except Exception:
        return {}
    finally:
        with contextlib.suppress(Exception):
            store.close()


def aggregate(dataset_id: str, group_by: Any,
              filters: dict[str, Any] | None = None,
              limit: int = 20) -> dict[str, Any]:
    """Group-by/count aggregate as ``AggregateResult.as_dict()``, or ``{}``.

    ``group_by`` may be a single column name or a list. Same degrade
    contract as :func:`sample_rows`.
    """
    if isinstance(group_by, str):
        group_by = [group_by]
    if not group_by:
        return {}
    owner = dataset_owner(dataset_id)
    if owner is None:
        return {}
    handle = open_store(owner)
    if handle is None:
        return {}
    adapter, store = handle
    try:
        result = adapter.aggregate(store, dataset_id,
                                   group_by=list(group_by),
                                   filters=filters or {},
                                   limit=_clamp(limit, 20, 1, 100))
        return result.as_dict()
    except Exception:
        return {}
    finally:
        with contextlib.suppress(Exception):
            store.close()


def _connector_tables(adapter: Any) -> list[str]:
    """Canonical table names for one connector (TABLES-driven)."""
    try:
        return list(adapter.tables_mod.TABLES)
    except Exception:
        return sorted({r["target_table"] for r in adapter.registry_as_dicts()})


def ingested_counts() -> dict[str, int]:
    """Total rows ingested per connector, for connectors with a db file.

    Sums ``store.count`` over each connector's canonical tables. Never
    raises; a connector that errors is simply omitted (treated as not
    ingested) so one corrupt file can't take the estate page down.
    """
    h = _load()
    if h is None:
        return {}
    out: dict[str, int] = {}
    try:
        adapters = h[1].adapters()
    except Exception:
        return {}
    for name, adapter in adapters.items():
        path = _db_path(name)
        if path is None:
            continue
        try:
            store = adapter.open_store(path)
        except Exception:
            continue
        try:
            out[name] = sum(int(store.count(t))
                            for t in _connector_tables(adapter))
        except Exception:
            continue
        finally:
            with contextlib.suppress(Exception):
                store.close()
    return out


def dataset_ingested_count(dataset_id: str) -> int | None:
    """Rows in the dataset's target table, or ``None`` when not ingested."""
    h = _load()
    if h is None:
        return None
    owner = dataset_owner(dataset_id)
    if owner is None or _db_path(owner) is None:
        return None
    try:
        adapter = h[1].adapters()[owner]
        row = adapter.by_dataset_id().get(dataset_id)
        if row is None:
            return None
        store = adapter.open_store(_db_path(owner))
        try:
            return int(store.count(row.target_table))
        finally:
            store.close()
    except Exception:
        return None


def catalog_dataset_counts() -> dict[str, int]:
    """Rows in each connector's synced ``*_catalog`` table (when ingested).

    Six connectors mirror their platform's full open-data catalog as a
    first-class ``<name>_catalog`` dataset; the sum of these counts is the
    "datasets discoverable" figure — far larger than the registered
    (curated) dataset count. ``{}`` when nothing is synced yet.
    """
    out: dict[str, int] = {}
    for row in all_datasets():
        did = row.get("dataset_id", "")
        if not did.endswith("_catalog"):
            continue
        n = dataset_ingested_count(did)
        if n:
            out[row["connector"]] = n
    return out
