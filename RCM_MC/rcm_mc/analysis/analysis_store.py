"""SQLite-backed cache for :class:`DealAnalysisPacket` runs.

The ``analysis_runs`` table is append-only. Each row is one packet
generation, keyed by ``(deal_id, scenario_id, as_of, hash_inputs)``.
The ``hash_inputs`` column lets the builder skip expensive rebuilds
when the inputs match a recent cached run.

Why append-only and not UPSERT: partners want to go back to a prior
analysis ("what did we think on Feb 3?"). Overwriting destroys that.
Cache hits return the *latest* matching row.

Follows the idiomatic pattern in ``deal_sim_inputs.py``:
``_ensure_table`` is called from every public entry point, so there's
no ordering requirement between modules.
"""
from __future__ import annotations

import json
import zlib
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from .packet import DealAnalysisPacket, PACKET_SCHEMA_VERSION, hash_inputs


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_table(store: Any) -> None:
    """Create ``analysis_runs`` if it doesn't exist. Safe to call on every
    request — ``CREATE TABLE IF NOT EXISTS`` is cheap."""
    store.init_db()
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS analysis_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deal_id TEXT NOT NULL,
                scenario_id TEXT,
                as_of TEXT,
                model_version TEXT NOT NULL,
                created_at TEXT NOT NULL,
                packet_json BLOB NOT NULL,
                hash_inputs TEXT NOT NULL,
                run_id TEXT NOT NULL,
                notes TEXT,
                FOREIGN KEY(deal_id) REFERENCES deals(deal_id)
                    ON DELETE CASCADE
            )"""
        )
        # Index for cache lookup by hash
        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_analysis_runs_hash "
            "ON analysis_runs(deal_id, hash_inputs)"
        )
        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_analysis_runs_deal "
            "ON analysis_runs(deal_id, created_at)"
        )
        con.commit()


def _compress(s: str) -> bytes:
    return zlib.compress(s.encode("utf-8"), level=6)


def _decompress(b: bytes) -> str:
    return zlib.decompress(b).decode("utf-8")


def save_packet(
    store: Any,
    packet: DealAnalysisPacket,
    *,
    inputs_hash: str,
    notes: Optional[str] = None,
) -> int:
    """Persist a packet. Returns the row id."""
    _ensure_table(store)
    # Canonical JSON (indent=None for smallest blob).
    payload = packet.to_json(indent=None)
    blob = _compress(payload)
    with store.connect() as con:
        cur = con.execute(
            """INSERT INTO analysis_runs
               (deal_id, scenario_id, as_of, model_version, created_at,
                packet_json, hash_inputs, run_id, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                packet.deal_id,
                packet.scenario_id,
                packet.as_of.isoformat() if packet.as_of else None,
                packet.model_version,
                _utcnow_iso(),
                blob,
                inputs_hash,
                packet.run_id,
                notes,
            ),
        )
        con.commit()
        return int(cur.lastrowid)


def load_latest_packet(
    store: Any,
    deal_id: str,
    *,
    scenario_id: Optional[str] = None,
    as_of: Optional[date] = None,
) -> Optional[DealAnalysisPacket]:
    """Most-recent packet matching ``(deal_id, scenario_id, as_of)``.

    ``scenario_id=None`` / ``as_of=None`` match strictly (i.e. NULL).
    Callers wanting "any scenario, latest" should use ``list_packets``.
    """
    _ensure_table(store)
    with store.connect() as con:
        row = con.execute(
            """SELECT packet_json FROM analysis_runs
               WHERE deal_id = ?
                 AND (scenario_id IS ? OR scenario_id = ?)
                 AND (as_of IS ? OR as_of = ?)
               ORDER BY created_at DESC
               LIMIT 1""",
            (
                str(deal_id),
                scenario_id, scenario_id,
                as_of.isoformat() if as_of else None,
                as_of.isoformat() if as_of else None,
            ),
        ).fetchone()
    if row is None:
        return None
    try:
        return DealAnalysisPacket.from_json(_decompress(row["packet_json"]))
    except (zlib.error, json.JSONDecodeError, KeyError, ValueError):
        return None


def find_cached_packet(
    store: Any,
    deal_id: str,
    inputs_hash: str,
    *,
    schema_version: Optional[str] = None,
) -> Optional[DealAnalysisPacket]:
    """Return the most recent packet whose ``hash_inputs`` matches.

    Used by :func:`rcm_mc.analysis.packet_builder.build_analysis_packet`
    when ``force_rebuild=False`` — a hash hit means "inputs are
    identical to a prior build; reuse the cached packet".

    When ``schema_version`` is provided (Prompt 21) we also filter by
    ``model_version`` so a packet saved before a packet-shape change
    can't be served against the new code path. Partners that bump
    :data:`PACKET_SCHEMA_VERSION` get a full rebuild automatically.
    """
    _ensure_table(store)
    with store.connect() as con:
        if schema_version is not None:
            row = con.execute(
                """SELECT packet_json FROM analysis_runs
                   WHERE deal_id = ? AND hash_inputs = ?
                     AND model_version = ?
                   ORDER BY created_at DESC LIMIT 1""",
                (str(deal_id), str(inputs_hash), str(schema_version)),
            ).fetchone()
        else:
            row = con.execute(
                """SELECT packet_json FROM analysis_runs
                   WHERE deal_id = ? AND hash_inputs = ?
                   ORDER BY created_at DESC LIMIT 1""",
                (str(deal_id), str(inputs_hash)),
            ).fetchone()
    if row is None:
        return None
    try:
        return DealAnalysisPacket.from_json(_decompress(row["packet_json"]))
    except (zlib.error, json.JSONDecodeError, KeyError, ValueError):
        return None


def list_packets(store: Any, deal_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return lightweight metadata rows for the analysis UI.

    Does NOT deserialize the full packet blob — use ``load_packet_by_id``
    to hydrate a specific row.
    """
    _ensure_table(store)
    with store.connect() as con:
        if deal_id:
            rows = con.execute(
                """SELECT id, deal_id, scenario_id, as_of, model_version,
                          created_at, hash_inputs, run_id, notes
                   FROM analysis_runs WHERE deal_id = ?
                   ORDER BY created_at DESC""",
                (str(deal_id),),
            ).fetchall()
        else:
            rows = con.execute(
                """SELECT id, deal_id, scenario_id, as_of, model_version,
                          created_at, hash_inputs, run_id, notes
                   FROM analysis_runs
                   ORDER BY created_at DESC"""
            ).fetchall()
    return [dict(r) for r in rows]


def load_packet_by_id(store: Any, row_id: int) -> Optional[DealAnalysisPacket]:
    _ensure_table(store)
    with store.connect() as con:
        row = con.execute(
            "SELECT packet_json FROM analysis_runs WHERE id = ?",
            (int(row_id),),
        ).fetchone()
    if row is None:
        return None
    try:
        return DealAnalysisPacket.from_json(_decompress(row["packet_json"]))
    except (zlib.error, json.JSONDecodeError, KeyError, ValueError):
        return None


def get_or_build_packet(
    store: Any,
    deal_id: str,
    *,
    scenario_id: Optional[str] = None,
    as_of: Optional[date] = None,
    force_rebuild: bool = False,
    notes: Optional[str] = None,
    **builder_kwargs: Any,
) -> DealAnalysisPacket:
    """High-level entry point used by server + CLI.

    1. Hash the inputs.
    2. Unless ``force_rebuild``, look for a cached row with that hash.
    3. If no hit, call :func:`build_analysis_packet` and persist.
    """
    from .packet_builder import build_analysis_packet

    # Compute the hash from the inputs that actually go into the builder.
    # Anything that doesn't change the packet shouldn't change the hash.
    observed_override = builder_kwargs.get("observed_override") or {}
    profile_override = builder_kwargs.get("profile_override") or {}
    # Analyst overrides (Prompt 18) — pulled from the store so a
    # newly-written override invalidates the cache on the next build
    # without the caller having to thread anything extra.
    overrides_for_hash: Dict[str, Any] = {}
    try:
        from .deal_overrides import get_overrides as _get_overrides
        overrides_for_hash = _get_overrides(store, deal_id) or {}
    except Exception:  # noqa: BLE001
        overrides_for_hash = {}
    # Report 0148/0162 MR958: include actual.yaml + benchmark.yaml
    # content hashes so editing those files invalidates the cache. The
    # YAMLs are loaded in packet_builder._build_simulation_summary via
    # deal_sim_inputs, so we look them up the same way here. Best-
    # effort: any failure (table missing, file missing, IO error) just
    # leaves the hash as None and falls back to the prior behaviour.
    actual_yaml_hash: Optional[str] = None
    benchmark_yaml_hash: Optional[str] = None
    try:
        from ..deals.deal_sim_inputs import get_inputs as _get_sim_inputs
        _sim_inputs = _get_sim_inputs(store, deal_id) or {}
        import hashlib as _h
        from pathlib import Path as _P
        for _key, _slot in (
            ("actual_path", "actual_yaml_hash"),
            ("benchmark_path", "benchmark_yaml_hash"),
        ):
            _path = _sim_inputs.get(_key)
            if _path and _P(_path).is_file():
                with open(_path, "rb") as _f:
                    _digest = _h.sha256(_f.read()).hexdigest()
                if _slot == "actual_yaml_hash":
                    actual_yaml_hash = _digest
                else:
                    benchmark_yaml_hash = _digest
    except Exception:  # noqa: BLE001 — best-effort; never block build
        pass
    h = hash_inputs(
        deal_id=deal_id,
        observed_metrics=observed_override,
        scenario_id=scenario_id,
        as_of=as_of,
        profile=profile_override if isinstance(profile_override, dict) else None,
        analyst_overrides=overrides_for_hash,
        actual_yaml_hash=actual_yaml_hash,
        benchmark_yaml_hash=benchmark_yaml_hash,
    )

    if not force_rebuild:
        # Prompt 21: gate cache hits on the current
        # ``PACKET_SCHEMA_VERSION`` so a code change that bumps the
        # schema auto-invalidates prior blobs. Prior rows remain on
        # disk for audit but won't be served.
        cached = find_cached_packet(
            store, deal_id, h,
            schema_version=PACKET_SCHEMA_VERSION,
        )
        if cached is not None:
            return cached

    packet = build_analysis_packet(
        store,
        deal_id,
        scenario_id=scenario_id,
        as_of=as_of,
        **builder_kwargs,
    )
    try:
        save_packet(store, packet, inputs_hash=h, notes=notes)
    except Exception:  # noqa: BLE001 — cache write must not break build
        pass
    return packet
