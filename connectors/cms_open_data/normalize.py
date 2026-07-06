"""Map raw CMS Open Data payloads → canonical rows.

Three mappers, one per endpoint kind:

  * :func:`normalize_catalog`  — the DCAT ``data.json`` document → one row
    per published dataset (keyed by the title slug).
  * :func:`normalize_curated`  — data-api row objects → snake_cased rows
    for the dataset's own canonical table, keyed by a composed
    ``{key}:{v1}:{v2}…`` natural key.
  * :func:`normalize_generic`  — data-api row objects → the on-demand
    ``cms_open_data_rows`` store (``row_json`` blobs keyed by
    ``{dataset_key}:{row_idx}`` for unfiltered crawls, or
    ``{dataset_key}:{slice_sig}:{row_idx}`` when the fetch was scoped by
    filters — see :func:`slice_signature`) so *any* catalog dataset stays
    queryable through the uniform engine without a bespoke table.

The one deterministic name normalizer
--------------------------------------
:func:`_snake` is THE mapping between the API's original column names
(``"Provider CCN"``, ``"ROLE CODE - OWNER"``, ``"Rndrng_NPI"``) and our
SQLite columns (``provider_ccn``, ``role_code_owner``, ``rndrng_npi``).
The column tuples snapshotted in endpoints.py were generated with this
exact function, so runtime rows always land in the snapshotted columns:
lowercase; every non-alphanumeric run becomes one underscore; edges are
stripped; a leading digit gains a ``c_`` prefix. No camelCase splitting —
that would be ambiguous for the API's acronym-heavy names (``CBSA``,
``RUCA``, ``WorkDate``).

Every mapper is defensive: fields are looked up with ``.get`` and never
assumed present, and a record whose natural-key values are all empty is
skipped rather than upserted under a degenerate key.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .endpoints import EndpointSpec

_RESERVED = {"row_key", "dataset_key", "source_endpoint", "ingested_at"}
_UUID_RE = re.compile(r"/dataset/([0-9a-fA-F-]{36})/")


def _snake(name: Any) -> str:
    """Deterministically snake_case an API column name (see module doc).

    MUST stay byte-identical with the generator that snapshotted the
    column tuples in endpoints.py — it is the schema contract.
    """
    out = re.sub(r"[^0-9A-Za-z]+", "_", str(name)).strip("_").lower()
    if not out:
        out = "col"
    if out[0].isdigit():
        out = "c_" + out
    return out


def slugify(title: Any) -> str:
    """A catalog dataset's stable key: its title, snake_cased."""
    return _snake(title)


def snake_row(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Re-key one raw API row with :func:`_snake`, deterministically.

    Collisions (two originals snake-casing identically, or an original
    colliding with a reserved column) are resolved in iteration order the
    same way the endpoints.py generator did, so drifted payloads still
    map onto the snapshotted schema.
    """
    seen: Dict[str, int] = {}
    out: Dict[str, Any] = {}
    for k, v in raw.items():
        s = _snake(k)
        if s in _RESERVED:
            s = "src_" + s
        n = seen.get(s, 0)
        seen[s] = n + 1
        out[s if n == 0 else f"{s}_{n + 1}"] = v
    return out


def compose_row_key(spec: EndpointSpec, raw: Dict[str, Any]) -> Optional[str]:
    """Compose the idempotent upsert key from the spec's natural key.

    Values are taken from ORIGINAL column names (pre-snake) so the key is
    independent of our renaming. Returns ``None`` when every component is
    empty — the caller skips such rows.
    """
    parts = [str(raw.get(col, "") or "").strip() for col in spec.natural_key]
    if not any(parts):
        return None
    return ":".join([spec.key, *parts])


# ── catalog ───────────────────────────────────────────────────────────
def _latest_api_url(entry: Dict[str, Any]) -> str:
    """The data-api accessURL of the dataset's LATEST version.

    data.json lists one API distribution per published version; the
    current one is flagged ``description == "latest"``. Fall back to the
    first API distribution, then to nothing (some datasets are ZIP-only —
    e.g. Geographic Variation by HRR — and cannot be served by the API).
    """
    dists = entry.get("distribution") or []
    if not isinstance(dists, list):
        return ""
    for d in dists:
        if isinstance(d, dict) and d.get("format") == "API" \
                and d.get("description") == "latest" and d.get("accessURL"):
            return str(d["accessURL"])
    for d in dists:
        if isinstance(d, dict) and d.get("format") == "API" and d.get("accessURL"):
            return str(d["accessURL"])
    return ""


def _uuid_from_url(url: str) -> str:
    m = _UUID_RE.search(url or "")
    return m.group(1) if m else ""


def _contact(entry: Dict[str, Any]) -> str:
    cp = entry.get("contactPoint")
    if not isinstance(cp, dict):
        return ""
    fn = str(cp.get("fn") or "").strip()
    email = str(cp.get("hasEmail") or "").replace("mailto:", "").strip()
    return f"{fn} <{email}>" if fn and email else fn or email


def normalize_catalog(doc: Any, *, source_endpoint: str = "catalog"
                      ) -> List[Dict[str, Any]]:
    """DCAT ``data.json`` document → catalog rows (one per dataset).

    ``uuid`` is the latest-version data-api UUID (from the API
    distribution, falling back to the ``identifier`` URL) — the value the
    connector's UUID re-resolution consults at fetch time.
    """
    datasets = doc.get("dataset") if isinstance(doc, dict) else None
    if not isinstance(datasets, list):
        return []
    rows: List[Dict[str, Any]] = []
    for entry in datasets:
        if not isinstance(entry, dict):
            continue
        title = str(entry.get("title") or "").strip()
        if not title:
            continue
        api_url = _latest_api_url(entry)
        uuid = _uuid_from_url(api_url) or _uuid_from_url(str(entry.get("identifier") or ""))
        themes = entry.get("theme")
        rows.append({
            "dataset_key": slugify(title),
            "uuid": uuid,
            "title": title,
            "description": entry.get("description"),
            "themes": "|".join(str(t) for t in themes) if isinstance(themes, list)
                      else (themes or ""),
            "periodicity": entry.get("accrualPeriodicity"),
            "modified": entry.get("modified"),
            "temporal": entry.get("temporal"),
            "api_url": api_url,
            "landing_page": entry.get("landingPage"),
            "described_by": entry.get("describedBy"),
            "contact": _contact(entry),
            "source_endpoint": source_endpoint,
        })
    return rows


# ── curated datasets ──────────────────────────────────────────────────
def normalize_curated(spec: EndpointSpec, raw_rows: List[Dict[str, Any]]
                      ) -> List[Dict[str, Any]]:
    """Data-api rows → canonical rows for the spec's own table.

    Every original field is carried over under its snake_cased name;
    fields the snapshotted schema doesn't know are silently dropped by
    the store's column-driven upsert (schema drift never breaks ingest).
    """
    if spec.kind != "curated":
        raise ValueError(f"normalize_curated needs a curated spec, got {spec.key!r}")
    rows: List[Dict[str, Any]] = []
    for raw in raw_rows:
        if not isinstance(raw, dict):
            continue
        key = compose_row_key(spec, raw)
        if key is None:
            continue
        row = snake_row(raw)
        row["row_key"] = key
        row["source_endpoint"] = spec.key
        rows.append(row)
    return rows


# ── generic on-demand rows ────────────────────────────────────────────
# First N hex chars of the sha1 over the canonicalized slice params —
# short enough to keep keys readable, long enough to never collide for
# the handful of filter combinations a dataset realistically sees.
_SLICE_SIG_LEN = 10


def _canonical_slice_params(slice_params: Optional[Dict[str, Any]]
                            ) -> Optional[Dict[str, Any]]:
    """A JSON-safe, deterministically ordered copy of the slice params.

    Returns ``None`` when there is no *effective* filter: an absent/empty
    dict, or one whose values are all empty (``None``/``""``/``{}``/
    ``[]``), degrades to the unfiltered key shape so the common
    full-crawl case keeps its historical keys byte-identical.
    """
    if not slice_params:
        return None
    kept = {str(k): v for k, v in slice_params.items()
            if v is not None and v != "" and v != {} and v != []}
    if not kept:
        return None
    return json.loads(
        json.dumps(kept, ensure_ascii=False, sort_keys=True, default=str))


def slice_signature(slice_params: Optional[Dict[str, Any]] = None) -> str:
    """Short stable signature of the filter params that scoped a fetch.

    ``""`` for an unfiltered fetch (the historical, common case — keys
    stay ``{dataset_key}:{row_idx}``, byte-identical with what earlier
    versions wrote). Otherwise the first :data:`_SLICE_SIG_LEN` hex chars
    of the sha1 over the canonicalized (sorted-keys JSON, values coerced
    via ``str``) params. The signature becomes a key segment
    (``{dataset_key}:{sig}:{row_idx}``) so two fetches of the same
    dataset with different filters can never overwrite each other's rows
    in the shared table — ``row_idx`` is only meaningful *within* one
    filter slice.
    """
    canon = _canonical_slice_params(slice_params)
    if canon is None:
        return ""
    blob = json.dumps(canon, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:_SLICE_SIG_LEN]


def normalize_generic(dataset_key: str, raw_rows: List[Dict[str, Any]],
                      *, start_idx: int = 0, fetched_at: Optional[str] = None,
                      slice_params: Optional[Dict[str, Any]] = None
                      ) -> List[Dict[str, Any]]:
    """Data-api rows for an arbitrary catalog dataset → row_json records.

    Keyed ``{dataset_key}:{row_idx}`` so a re-fetch of the same window is
    idempotent, with ``dataset_key`` mirrored into ``source_endpoint`` so
    the uniform query engine's slice pinning works on the shared table.
    ``start_idx`` is the fetch's ABSOLUTE start offset in the dataset
    (page offset + position), so a fetch resumed mid-dataset never
    re-keys its rows as 0..N over rows an earlier window already wrote.

    ``slice_params`` are the filter params that scoped the fetch, if any:
    they add a :func:`slice_signature` segment to the key
    (``{dataset_key}:{sig}:{row_idx}``) so differently-filtered fetches
    of one dataset coexist, and the human-readable params are carried in
    the row's JSON under the reserved ``_slice_params`` key. Unfiltered
    fetches produce byte-identical output to earlier versions.
    """
    stamp = fetched_at or datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%S+00:00")
    sig = slice_signature(slice_params)
    canon = _canonical_slice_params(slice_params)
    rows: List[Dict[str, Any]] = []
    for i, raw in enumerate(raw_rows):
        if not isinstance(raw, dict):
            continue
        idx = start_idx + i
        if sig:
            body: Dict[str, Any] = dict(raw)
            body["_slice_params"] = canon
            key = f"{dataset_key}:{sig}:{idx}"
        else:
            body = raw
            key = f"{dataset_key}:{idx}"
        rows.append({
            "row_key": key,
            "dataset_key": dataset_key,
            "row_idx": idx,
            "row_json": json.dumps(body, ensure_ascii=False, sort_keys=True),
            "fetched_at": stamp,
            "source_endpoint": dataset_key,
        })
    return rows
