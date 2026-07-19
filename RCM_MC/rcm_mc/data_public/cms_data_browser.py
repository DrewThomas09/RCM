"""CMS Public Data Browser — real catalog over the connector estate.

Historically this page rendered a hand-written list of CMS datasets with
fabricated record counts and refresh dates. That was actively misleading
on a surface whose whole job is to say "here is the CMS data we actually
have." This module now derives every number from the live connector
estate (``data_public.connector_estate``): the dataset catalog, the
per-connector row counts, and the vintages are all read from the ingested
SQLite files, so a dataset reads as *cached* only when its rows are on
disk and *available* otherwise. Nothing here is illustrative.

Scope is the CMS / CMS-adjacent public-data connectors (``_CMS_CONNECTORS``)
— the broader estate (openFDA, CDC, Census, …) lives on ``/data-hub`` and
``/connector-estate``. Per-dataset counts are only computed for connectors
that are actually warmed, so a cold deployment renders instantly (every
dataset shows "not cached") instead of opening 130 empty databases.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

# The CMS (and CMS-adjacent) connectors this browser scopes to. Order is
# display order in the connector-summary table.
_CMS_CONNECTORS = (
    "cms_open_data",
    "provider_data",
    "cms_coverage",
    "open_payments",
    "medicaid_data",
    "healthcare_gov",
)


@dataclass
class CMSDataset:
    dataset_id: str
    connector: str
    category: str          # human connector label
    endpoint: str
    update_frequency: str
    last_refresh: str      # ISO vintage, or "" when not cached
    record_count: int
    key_fields: str
    ingestion_status: str  # "cached" | "available"


@dataclass
class ConnectorRow:
    connector: str
    label: str
    base_url: str
    n_datasets: int
    rows_cached: int
    vintage: str           # ISO vintage, or "" when not cached
    warmed: bool


@dataclass
class CMSDataResult:
    available: bool
    total_datasets: int
    cached_datasets: int
    total_rows: int
    latest_vintage: str
    connectors: List[ConnectorRow] = field(default_factory=list)
    datasets: List[CMSDataset] = field(default_factory=list)


def _key_fields(row: dict) -> str:
    jk = row.get("join_keys") or []
    if isinstance(jk, (list, tuple)):
        return ", ".join(str(k) for k in jk)
    return str(jk)


def compute_cms_data_browser() -> CMSDataResult:
    """Build the CMS catalog from the live estate. Never raises; degrades
    to ``available=False`` (honest empty state) when the estate is absent.
    """
    from . import connector_estate as ce

    if not ce.estate_available():
        return CMSDataResult(available=False, total_datasets=0,
                             cached_datasets=0, total_rows=0,
                             latest_vintage="")

    summaries = {s.get("connector"): s for s in ce.connectors_summary()}
    ingested = ce.ingested_counts()          # per-connector, one pass
    vintages = ce.connector_vintages()       # per-connector, one pass

    # Connector summary rows (fast — no per-dataset DB work).
    connectors: List[ConnectorRow] = []
    for name in _CMS_CONNECTORS:
        s = summaries.get(name)
        if not s:
            continue
        rows = int(ingested.get(name, 0) or 0)
        base_urls = s.get("base_urls") or []
        connectors.append(ConnectorRow(
            connector=name,
            label=str(s.get("label", name)),
            base_url=str(base_urls[0]) if base_urls else "",
            n_datasets=int(s.get("n_datasets", 0) or 0),
            rows_cached=rows,
            vintage=str(vintages.get(name, "") or ""),
            warmed=rows > 0,
        ))

    # Dataset catalog. Per-dataset counts/vintages are only queried for
    # connectors that are warmed — a cold connector contributes its rows
    # as "not cached" with zero DB opens.
    warmed = {c.connector for c in connectors if c.warmed}
    datasets: List[CMSDataset] = []
    for d in ce.all_datasets():
        conn = d.get("connector")
        if conn not in _CMS_CONNECTORS:
            continue
        label = str(summaries.get(conn, {}).get("label", conn))
        if conn in warmed:
            count = ce.dataset_ingested_count(d["dataset_id"]) or 0
            vint = ce.dataset_vintage(d["dataset_id"]) or vintages.get(conn, "")
        else:
            count, vint = 0, ""
        datasets.append(CMSDataset(
            dataset_id=str(d.get("dataset_id", "")),
            connector=str(conn),
            category=label,
            endpoint=str(d.get("endpoint", "") or ""),
            update_frequency=str(d.get("refresh_cadence", "") or "—"),
            last_refresh=str(vint or ""),
            record_count=int(count),
            key_fields=_key_fields(d),
            ingestion_status="cached" if count > 0 else "available",
        ))

    # Cached datasets first, then by breadth of key fields, then id — so a
    # partner sees what's actually pullable at the top.
    datasets.sort(key=lambda x: (-(x.record_count > 0), -x.record_count,
                                 x.dataset_id))

    total_rows = sum(c.rows_cached for c in connectors)
    cached = sum(1 for d in datasets if d.record_count > 0)
    latest = max((c.vintage for c in connectors if c.vintage), default="")

    return CMSDataResult(
        available=True,
        total_datasets=len(datasets),
        cached_datasets=cached,
        total_rows=total_rows,
        latest_vintage=latest,
        connectors=connectors,
        datasets=datasets,
    )
