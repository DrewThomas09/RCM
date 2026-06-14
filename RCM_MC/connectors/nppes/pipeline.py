"""End-to-end NPPES pipeline orchestrator.

Stages (resumable, idempotent):
  1. NUCC → dim_taxonomy.
  2. Monthly full file → raw landing (parquet/ndjson, partitioned by
     entity_type/state, streamed) → normalize into dim_provider +
     bridge_provider_taxonomy + dim_provider_address. Records the monthly
     version and the source-file row count for reconciliation.
  3. Weekly increments → applied in order as NPI-keyed upserts; already-
     applied weeklies are skipped (tracked in nppes_load_state).
  4. Auxiliary files → other-name, practice-location, endpoint tables.
  5. Derived bridge_provider_affiliation.
  6. DQ suite.
  7. Journal: nppes_load_state + STATE.md + PROGRESS_LOG.md.

State lives in two mirrored places so a hard kill loses nothing: the
``nppes_load_state`` row (authoritative, transactional) and STATE.md (human
readable). Re-running ``run`` converges — landing overwrites, normalize
upserts, weeklies are de-duplicated by id.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import affiliation, dq, landing, normalize, parse
from .parse import ProviderRow, zip5_of
from .store import NppesStore

HERE = Path(__file__).resolve().parent
STATE_MD = HERE / "STATE.md"
PROGRESS_LOG = HERE / "PROGRESS_LOG.md"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _practice_state(row: ProviderRow) -> str:
    for a in row.addresses:
        if a.purpose == "practice" and a.state:
            return a.state
    return "NA"


def _flatten_for_landing(row: ProviderRow) -> Dict[str, Any]:
    """Flat, scalar-only raw row for the landing zone (nested taxonomy /
    address structures are JSON-encoded so parquet and ndjson round-trip
    identically). Includes the partition keys entity_type + state."""
    d = {
        "npi": row.npi, "entity_type": row.entity_type,
        "state": _practice_state(row),
        "replacement_npi": row.replacement_npi,
        "organization_name": row.organization_name,
        "last_name": row.last_name, "first_name": row.first_name,
        "middle_name": row.middle_name, "name_prefix": row.name_prefix,
        "name_suffix": row.name_suffix, "credential": row.credential,
        "authorized_official_last_name": row.authorized_official_last_name,
        "authorized_official_first_name": row.authorized_official_first_name,
        "authorized_official_title": row.authorized_official_title,
        "authorized_official_phone": row.authorized_official_phone,
        "sole_proprietor": row.sole_proprietor,
        "enumeration_date": row.enumeration_date,
        "last_update_date": row.last_update_date,
        "deactivation_date": row.deactivation_date,
        "reactivation_date": row.reactivation_date,
        "taxonomies_json": json.dumps([t.__dict__ for t in row.taxonomies]),
        "addresses_json": json.dumps([a.__dict__ for a in row.addresses]),
    }
    return d


def _landed_to_provider_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(d)
    out["taxonomies"] = json.loads(d.get("taxonomies_json") or "[]")
    out["addresses"] = json.loads(d.get("addresses_json") or "[]")
    return out


def land_and_normalize_main(
    store: NppesStore, path: str, *, source_row: str, monthly_version: str,
    landing_root: str, dataset: str, chunk_log: int = 100_000,
) -> Dict[str, int]:
    """Stream the main file once into the landing zone, then normalize from
    the landing zone. Returns combined counters incl. landed row count."""
    lander = landing.RawLander(landing_root, dataset,
                               partition_keys=("entity_type", "state"))
    landed = 0
    for prow in parse.parse_main_file(path):
        lander.write(_flatten_for_landing(prow))
        landed += 1
    lander.close()

    rows = (_landed_to_provider_dict(d)
            for d in landing.read_partitions(landing_root, dataset))
    counters = normalize.normalize_providers(
        store, rows, source_row=source_row, monthly_version=monthly_version,
        batch_label=f"{source_row}:{dataset}")
    counters["landed"] = landed
    counters["landing_format"] = landing.landing_format()
    return counters


def apply_weekly(store: NppesStore, path: str, *, weekly_id: str,
                 monthly_version: str, landing_root: str) -> Dict[str, int]:
    dataset = f"weekly_{weekly_id}"
    return land_and_normalize_main(
        store, path, source_row="weekly", monthly_version=monthly_version,
        landing_root=landing_root, dataset=dataset)


def _read_state(store: NppesStore) -> Dict[str, Any]:
    with store.connect() as con:
        r = con.execute(
            "SELECT * FROM nppes_load_state WHERE id=1").fetchone()
    if not r:
        return {"monthly_version": None, "monthly_header_count": None,
                "weeklies_applied": [], "last_run_at": None}
    d = dict(r)
    d["weeklies_applied"] = json.loads(d.get("weeklies_applied") or "[]")
    return d


def _write_state(store: NppesStore, *, monthly_version, header_count,
                 weeklies_applied: List[str], notes: str = "") -> None:
    with store.connect() as con:
        con.execute(
            "INSERT INTO nppes_load_state "
            "(id, monthly_version, monthly_header_count, weeklies_applied, "
            " last_run_at, notes) VALUES (1,?,?,?,?,?) "
            "ON CONFLICT(id) DO UPDATE SET "
            "monthly_version=excluded.monthly_version, "
            "monthly_header_count=excluded.monthly_header_count, "
            "weeklies_applied=excluded.weeklies_applied, "
            "last_run_at=excluded.last_run_at, notes=excluded.notes",
            (monthly_version, header_count, json.dumps(weeklies_applied),
             _now(), notes))
        con.commit()


def run(
    store: NppesStore,
    *,
    monthly_path: str,
    nucc_path: str,
    monthly_version: str,
    monthly_header_count: Optional[int] = None,
    weekly_paths: Optional[List[str]] = None,
    othername_path: Optional[str] = None,
    practice_location_path: Optional[str] = None,
    endpoint_path: Optional[str] = None,
    landing_root: Optional[str] = None,
    taxonomy_threshold: float = 0.95,
    write_journal: bool = True,
) -> Dict[str, Any]:
    """Run the full pipeline. Idempotent and resumable."""
    store.init_db()
    landing_root = landing_root or str(HERE / "data" / "landing")
    weekly_paths = weekly_paths or []
    report: Dict[str, Any] = {"stages": {}, "started_at": _now()}

    # 1. NUCC crosswalk
    report["stages"]["nucc"] = normalize.normalize_taxonomy(
        store, parse.parse_nucc_csv(nucc_path), nucc_version=monthly_version)

    # 2. Monthly base
    prior = _read_state(store)
    main_counters = land_and_normalize_main(
        store, monthly_path, source_row="monthly",
        monthly_version=monthly_version, landing_root=landing_root,
        dataset="monthly")
    report["stages"]["monthly"] = main_counters
    header_count = (monthly_header_count
                    if monthly_header_count is not None
                    else main_counters.get("landed"))

    # 3. Weeklies (apply in order, skip already-applied)
    applied = list(prior.get("weeklies_applied") or [])
    weekly_reports = []
    for wp in weekly_paths:
        wid = Path(wp).stem
        if wid in applied:
            weekly_reports.append({"weekly_id": wid, "skipped": True})
            continue
        wr = apply_weekly(store, wp, weekly_id=wid,
                          monthly_version=monthly_version,
                          landing_root=landing_root)
        wr["weekly_id"] = wid
        weekly_reports.append(wr)
        applied.append(wid)
    report["stages"]["weeklies"] = weekly_reports

    # 4. Auxiliary files
    aux = {}
    if othername_path:
        aux["other_names"] = normalize.normalize_other_names(
            store, parse.parse_othername(othername_path))
    if practice_location_path:
        aux["practice_locations"] = normalize.normalize_practice_locations(
            store, parse.parse_practice_location(practice_location_path))
    if endpoint_path:
        aux["endpoints"] = normalize.normalize_endpoints(
            store, parse.parse_endpoint(endpoint_path))
    report["stages"]["aux"] = aux

    # 5. Affiliations (after aux so other-names feed the name signal)
    report["stages"]["affiliation"] = affiliation.build_affiliations(store)

    # 6. Persist state BEFORE DQ so reconciliation can read header_count.
    _write_state(store, monthly_version=monthly_version,
                 header_count=header_count, weeklies_applied=applied,
                 notes=f"landing_format={main_counters.get('landing_format')}")

    # 7. DQ
    dq_report = dq.run_all(store, taxonomy_threshold=taxonomy_threshold)
    report["stages"]["dq"] = dq_report["summary"]
    report["dq_all_passed"] = dq_report["all_passed"]
    report["finished_at"] = _now()

    if write_journal:
        _write_state_md(store, report)
        _append_progress(report)
    return report


# ── journal writers (filesystem-as-memory) ──────────────────────────
def _table_counts(store: NppesStore) -> Dict[str, int]:
    tables = ["dim_provider", "bridge_provider_taxonomy", "dim_taxonomy",
              "dim_provider_address", "bridge_provider_affiliation",
              "dim_provider_endpoint", "nppes_other_name", "nppes_invalid_npi"]
    out = {}
    with store.connect() as con:
        for t in tables:
            out[t] = con.execute(f"SELECT COUNT(*) c FROM {t}").fetchone()["c"]
        out["dim_provider_type1"] = con.execute(
            "SELECT COUNT(*) c FROM dim_provider WHERE entity_type=1").fetchone()["c"]
        out["dim_provider_type2"] = con.execute(
            "SELECT COUNT(*) c FROM dim_provider WHERE entity_type=2").fetchone()["c"]
        out["dim_provider_deactivated"] = con.execute(
            "SELECT COUNT(*) c FROM dim_provider WHERE status='deactivated'").fetchone()["c"]
    return out


def _write_state_md(store: NppesStore, report: Dict[str, Any]) -> None:
    st = _read_state(store)
    counts = _table_counts(store)
    lines = [
        "# NPPES Connector — STATE",
        "",
        f"_Last run: {report.get('finished_at')}_  ",
        f"_Generated by `connectors/nppes/pipeline.py`. Authoritative copy "
        f"lives in the `nppes_load_state` table; this file mirrors it._",
        "",
        "## Load state",
        f"- Monthly version loaded: **{st.get('monthly_version')}**",
        f"- Monthly source row count (header): **{st.get('monthly_header_count')}**",
        f"- Weekly increments applied: **{len(st.get('weeklies_applied') or [])}** "
        f"→ {st.get('weeklies_applied')}",
        f"- Landing format: **{report['stages']['monthly'].get('landing_format')}**",
        "",
        "## Cumulative row counts",
    ]
    for k, v in counts.items():
        lines.append(f"- `{k}`: {v:,}")
    lines += ["", "## DQ status",
              f"- All passed: **{report.get('dq_all_passed')}**"]
    for name, res in report["stages"]["dq"].items():
        flag = "✅" if res["passed"] else "❌"
        lines.append(f"- {flag} `{name}` — metric={res['metric']} — {res['detail']}")
    lines += ["", "## Resume contract",
              "- Re-running `pipeline.run(...)` is idempotent: NUCC + monthly "
              "upsert, weeklies de-duplicated by id, affiliations rebuilt.",
              "- A hard kill mid-run loses at most the in-flight batch; "
              "`nppes_load_state` + committed rows are enough to resume.",
              ""]
    STATE_MD.write_text("\n".join(lines), encoding="utf-8")


def _append_progress(report: Dict[str, Any]) -> None:
    mon = report["stages"]["monthly"]
    dqp = report.get("dq_all_passed")
    line = (f"- {report.get('finished_at')} — monthly landed="
            f"{mon.get('landed')} inserted={mon.get('inserted')} "
            f"quarantined={mon.get('quarantined')} "
            f"weeklies={len(report['stages']['weeklies'])} "
            f"dq_all_passed={dqp}\n")
    header = "# NPPES Connector — Progress Log (append-only)\n\n"
    if not PROGRESS_LOG.exists():
        PROGRESS_LOG.write_text(header, encoding="utf-8")
    with PROGRESS_LOG.open("a", encoding="utf-8") as fh:
        fh.write(line)
