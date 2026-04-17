"""Per-deal analyst overrides persisted in SQLite.

The platform already accepts many overrides at call-time — the
reimbursement engine takes ``optional_contract_inputs``,
:class:`~rcm_mc.pe.value_bridge_v2.BridgeAssumptions` exposes every
bridge knob. But until now there was no way for an analyst to
persist a per-deal tweak so subsequent packet builds, API calls, and
CLI runs all pick it up. This module adds that surface:

- SQLite table ``deal_overrides`` keyed by ``(deal_id, override_key)``.
- Validated keyspace: five dotted namespaces (``payer_mix``,
  ``method_distribution``, ``bridge``, ``ramp``, ``metric_target``).
- Values stored as JSON-encoded text so numbers, strings, and small
  objects all round-trip.
- Each write records ``set_by`` (analyst username) and an optional
  ``reason`` so the audit trail can answer "why did this deal's
  exit_multiple get bumped to 11?".

Overrides are applied at packet-build time (see
:mod:`rcm_mc.analysis.packet_builder`), folded into
``hash_inputs`` so the cache correctly misses on change, and surfaced
as ``ProvenanceTag.ANALYST_OVERRIDE`` everywhere they land.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Schema ─────────────────────────────────────────────────────────

# Supported override prefixes. Each validator is responsible for
# accepting the subkey pattern that follows its prefix.
#
# The prefix design is dotted so analysts can use shell tab-completion
# and sort overrides naturally. Keys are case-sensitive — we rely on
# downstream consumers knowing the canonical name (``commercial`` not
# ``Commercial``).
_PREFIXES = ("payer_mix", "method_distribution", "bridge", "ramp",
             "metric_target")

# Payer class values — kept in-module so this file doesn't drag
# :mod:`rcm_mc.finance.reimbursement_engine` into import cycles.
# Validation only needs the names.
_VALID_PAYERS = frozenset({
    "commercial", "medicare_ffs", "medicare_advantage", "medicaid",
    "self_pay", "managed_government",
})

# Reimbursement method values — match the ``ReimbursementMethod``
# enum's ``.value`` strings exactly; the engine calls
# ``ReimbursementMethod(k)`` on each key so anything off-roster blows
# up late rather than at the override-write boundary.
_VALID_METHODS = frozenset({
    "fee_for_service", "drg_prospective_payment", "outpatient_apc_like",
    "per_diem", "capitation", "case_rate_or_bundle",
    "value_based_quality_linked", "cost_based_reimbursement",
})

# BridgeAssumptions field whitelist. Kept explicit rather than
# introspected so an accidental dataclass rename doesn't silently
# open the override surface.
_VALID_BRIDGE_FIELDS = frozenset({
    "exit_multiple", "cost_of_capital", "collection_realization",
    "denial_overturn_rate", "rework_cost_per_claim",
    "cost_per_follow_up_fte", "claims_per_follow_up_fte",
    "implementation_ramp", "confidence_inference_penalty",
    "claims_volume", "net_revenue", "evaluation_month",
})

# Ramp families recognized by the override keyspace. Mirrors
# :data:`rcm_mc.pe.ramp_curves.DEFAULT_RAMP_CURVES`.
_VALID_RAMP_FAMILIES = frozenset({
    "denial_management", "ar_collections", "cdi_coding",
    "payer_renegotiation", "cost_optimization", "default",
})
_VALID_RAMP_FIELDS = frozenset({
    "months_to_25_pct", "months_to_75_pct", "months_to_full",
})

# Metric-target keys are free-form — any registry metric is a
# candidate. We validate the outer shape only.
_METRIC_KEY_RE = re.compile(r"^[a-z][a-z0-9_]{1,64}$")


# ── Validation ─────────────────────────────────────────────────────

def validate_override_key(key: str) -> None:
    """Raise :class:`ValueError` with a helpful message on bad keys.

    Shape rules by prefix:

    - ``payer_mix.<payer>_share`` — payer in :data:`_VALID_PAYERS`.
    - ``method_distribution.<payer>.<method>`` — both validated.
    - ``bridge.<field>`` — field in :data:`_VALID_BRIDGE_FIELDS`.
    - ``ramp.<family>.<field>`` — family + field validated.
    - ``metric_target.<metric>`` — metric matches :data:`_METRIC_KEY_RE`.
    """
    if not key or not isinstance(key, str):
        raise ValueError(f"override key must be a non-empty string, got {key!r}")
    prefix, _, rest = key.partition(".")
    if prefix not in _PREFIXES:
        raise ValueError(
            f"unknown override prefix {prefix!r}; "
            f"expected one of {sorted(_PREFIXES)}"
        )
    if not rest:
        raise ValueError(f"override key {key!r} is missing its subkey")

    if prefix == "payer_mix":
        # Expect ``<payer>_share`` — e.g., ``commercial_share``.
        if not rest.endswith("_share"):
            raise ValueError(
                f"payer_mix key must end in '_share', got {key!r}"
            )
        payer = rest[: -len("_share")]
        if payer not in _VALID_PAYERS:
            raise ValueError(
                f"unknown payer {payer!r} in {key!r}; "
                f"expected one of {sorted(_VALID_PAYERS)}"
            )
        return

    if prefix == "method_distribution":
        parts = rest.split(".")
        if len(parts) != 2:
            raise ValueError(
                f"method_distribution key must be "
                f"'method_distribution.<payer>.<method>', got {key!r}"
            )
        payer, method = parts
        if payer not in _VALID_PAYERS:
            raise ValueError(
                f"unknown payer {payer!r} in {key!r}"
            )
        if method not in _VALID_METHODS:
            raise ValueError(
                f"unknown method {method!r} in {key!r}; "
                f"expected one of {sorted(_VALID_METHODS)}"
            )
        return

    if prefix == "bridge":
        if rest not in _VALID_BRIDGE_FIELDS:
            raise ValueError(
                f"unknown bridge field {rest!r}; "
                f"expected one of {sorted(_VALID_BRIDGE_FIELDS)}"
            )
        return

    if prefix == "ramp":
        parts = rest.split(".")
        if len(parts) != 2:
            raise ValueError(
                f"ramp key must be 'ramp.<family>.<field>', got {key!r}"
            )
        family, fld = parts
        if family not in _VALID_RAMP_FAMILIES:
            raise ValueError(
                f"unknown ramp family {family!r}; "
                f"expected one of {sorted(_VALID_RAMP_FAMILIES)}"
            )
        if fld not in _VALID_RAMP_FIELDS:
            raise ValueError(
                f"unknown ramp field {fld!r}; "
                f"expected one of {sorted(_VALID_RAMP_FIELDS)}"
            )
        return

    if prefix == "metric_target":
        if not _METRIC_KEY_RE.match(rest):
            raise ValueError(
                f"metric key {rest!r} must match {_METRIC_KEY_RE.pattern}"
            )
        return


def _coerce_for_json(value: Any) -> Any:
    """Narrow the accepted value types so we don't round-trip surprises.

    Persisted values must be ``json.dumps``-safe — numbers, strings,
    bools, lists, or shallow dicts of same. Rejecting everything else
    at write time keeps the getter's decoder simple.
    """
    if isinstance(value, (int, float, bool, str)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [_coerce_for_json(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _coerce_for_json(v) for k, v in value.items()}
    raise ValueError(
        f"override value must be JSON-encodable primitive, "
        f"got {type(value).__name__}"
    )


# ── SQLite plumbing ────────────────────────────────────────────────

def _ensure_table(store: Any) -> None:
    """Create ``deal_overrides`` if missing. Idempotent."""
    store.init_db()
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS deal_overrides (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deal_id TEXT NOT NULL,
                override_key TEXT NOT NULL,
                override_value TEXT NOT NULL,
                set_by TEXT NOT NULL,
                set_at TEXT NOT NULL,
                reason TEXT,
                UNIQUE(deal_id, override_key),
                FOREIGN KEY(deal_id) REFERENCES deals(deal_id)
                    ON DELETE CASCADE
            )"""
        )
        con.execute(
            "CREATE INDEX IF NOT EXISTS ix_deal_overrides_deal "
            "ON deal_overrides(deal_id)"
        )
        con.commit()


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Public API ─────────────────────────────────────────────────────

def set_override(
    store: Any,
    deal_id: str,
    key: str,
    value: Any,
    *,
    set_by: str,
    reason: Optional[str] = None,
) -> int:
    """Upsert one override. Returns the row ID.

    ``value`` is JSON-encoded before storage so number/string/bool
    all round-trip. Invalid keys raise :class:`ValueError` before
    touching the DB.
    """
    validate_override_key(key)
    coerced = _coerce_for_json(value)
    payload = json.dumps(coerced, sort_keys=True)
    _ensure_table(store)
    now = _utcnow_iso()
    with store.connect() as con:
        cur = con.execute(
            """INSERT INTO deal_overrides
                 (deal_id, override_key, override_value,
                  set_by, set_at, reason)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(deal_id, override_key) DO UPDATE SET
                   override_value = excluded.override_value,
                   set_by = excluded.set_by,
                   set_at = excluded.set_at,
                   reason = excluded.reason""",
            (str(deal_id), str(key), payload,
             str(set_by or "unknown"), now, reason),
        )
        con.commit()
        # lastrowid is 0 on UPDATE; re-read the id.
        if cur.lastrowid:
            return int(cur.lastrowid)
        row = con.execute(
            "SELECT id FROM deal_overrides "
            "WHERE deal_id = ? AND override_key = ?",
            (str(deal_id), str(key)),
        ).fetchone()
        return int(row["id"]) if row else 0


def get_overrides(store: Any, deal_id: str) -> Dict[str, Any]:
    """Return the decoded ``{key: value}`` map for one deal.

    Values are ``json.loads``-restored, so numbers remain numbers and
    objects remain dicts. Rows whose JSON fails to parse are logged
    and skipped rather than crashing the caller — a corrupt row
    shouldn't break an entire packet build.
    """
    _ensure_table(store)
    out: Dict[str, Any] = {}
    with store.connect() as con:
        rows = con.execute(
            "SELECT override_key, override_value FROM deal_overrides "
            "WHERE deal_id = ? ORDER BY override_key",
            (str(deal_id),),
        ).fetchall()
    for r in rows:
        try:
            out[str(r["override_key"])] = json.loads(r["override_value"])
        except (json.JSONDecodeError, TypeError):
            logger.warning(
                "deal_overrides: malformed JSON at deal=%s key=%s",
                deal_id, r["override_key"],
            )
    return out


def clear_override(store: Any, deal_id: str, key: str) -> bool:
    """Delete one override. Returns ``True`` when a row was removed."""
    _ensure_table(store)
    with store.connect() as con:
        cur = con.execute(
            "DELETE FROM deal_overrides "
            "WHERE deal_id = ? AND override_key = ?",
            (str(deal_id), str(key)),
        )
        con.commit()
        return int(cur.rowcount or 0) > 0


def list_overrides(
    store: Any, deal_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Flat audit-trail view. One row per override. Most recent first."""
    _ensure_table(store)
    with store.connect() as con:
        if deal_id is not None:
            rows = con.execute(
                """SELECT id, deal_id, override_key, override_value,
                          set_by, set_at, reason
                   FROM deal_overrides
                   WHERE deal_id = ? ORDER BY set_at DESC""",
                (str(deal_id),),
            ).fetchall()
        else:
            rows = con.execute(
                """SELECT id, deal_id, override_key, override_value,
                          set_by, set_at, reason
                   FROM deal_overrides ORDER BY set_at DESC"""
            ).fetchall()
    out: List[Dict[str, Any]] = []
    for r in rows:
        try:
            decoded = json.loads(r["override_value"])
        except (json.JSONDecodeError, TypeError):
            decoded = None
        out.append({
            "id": int(r["id"]),
            "deal_id": str(r["deal_id"]),
            "override_key": str(r["override_key"]),
            "override_value": decoded,
            "set_by": str(r["set_by"]),
            "set_at": str(r["set_at"]),
            "reason": r["reason"],
        })
    return out


# ── Grouping helper ────────────────────────────────────────────────

def group_overrides(overrides: Dict[str, Any]) -> Dict[str, Any]:
    """Split a flat ``{key: value}`` map into namespaces the builder
    can slot into their natural places.

    Output shape::

        {
            "payer_mix":           {"commercial": 0.55, ...},
            "method_distribution": {"commercial": {"fee_for_service": 0.8}, ...},
            "bridge":              {"exit_multiple": 11.0, ...},
            "ramp":                {"denial_management": {"months_to_full": 9}, ...},
            "metric_target":       {"denial_rate": 6.0, ...},
        }

    Unknown keys are silently dropped — they've already been blocked
    by :func:`validate_override_key` at write time, but a belt-and-
    braces filter here protects the builder from whatever the caller
    hand-assembles.
    """
    out: Dict[str, Any] = {
        "payer_mix": {}, "method_distribution": {}, "bridge": {},
        "ramp": {}, "metric_target": {},
    }
    for key, value in (overrides or {}).items():
        prefix, _, rest = key.partition(".")
        if prefix not in out:
            continue
        if prefix == "payer_mix":
            # Strip the trailing ``_share`` so the payer name aligns
            # with the raw ``HospitalProfile.payer_mix`` keys.
            payer = rest[:-len("_share")] if rest.endswith("_share") else rest
            out["payer_mix"][payer] = value
        elif prefix == "method_distribution":
            parts = rest.split(".")
            if len(parts) != 2:
                continue
            payer, method = parts
            out["method_distribution"].setdefault(payer, {})[method] = value
        elif prefix == "bridge":
            out["bridge"][rest] = value
        elif prefix == "ramp":
            parts = rest.split(".")
            if len(parts) != 2:
                continue
            family, fld = parts
            out["ramp"].setdefault(family, {})[fld] = value
        elif prefix == "metric_target":
            out["metric_target"][rest] = value
    return out
