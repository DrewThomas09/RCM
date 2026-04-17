"""Deal query engine — rule-based parser + executor (Prompt 53).

Partners type natural queries like ``"denial rate > 10"`` or
``"state = IL"`` and the system returns matching deals. This avoids
SQL exposure while giving power users filter-and-sort capability
across the portfolio.

The parser handles simple ``field operator value`` triples. The
executor loads the latest packet per deal and applies filters
against the packet's nested structure via ``QUERY_FIELD_MAP``.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Dataclasses ───────────────────────────────────────────────────

@dataclass
class QueryFilter:
    field: str
    operator: str  # ">", "<", ">=", "<=", "=", "!="
    value: Any

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field,
            "operator": self.operator,
            "value": self.value,
        }


@dataclass
class DealSummary:
    deal_id: str
    deal_name: str
    matched_values: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deal_id": self.deal_id,
            "deal_name": self.deal_name,
            "matched_values": dict(self.matched_values),
        }


# ── Field mapping ─────────────────────────────────────────────────
# Maps user-friendly names to (accessor_type, path) tuples.
# accessor_type:
#   "profile" — packet.profile.<attr>
#   "observed" — packet.observed_metrics[key].value
#   "bridge" — packet.ebitda_bridge.<attr>
#   "meta" — packet.<attr>

QUERY_FIELD_MAP: Dict[str, tuple[str, str]] = {
    # Profile fields
    "state": ("profile", "state"),
    "bed count": ("profile", "bed_count"),
    "beds": ("profile", "bed_count"),
    "region": ("profile", "region"),
    "teaching": ("profile", "teaching_status"),
    # Observed / RCM metrics (common shorthand)
    "denial rate": ("observed", "initial_denial_rate"),
    "idr": ("observed", "initial_denial_rate"),
    "write off": ("observed", "final_write_off_rate"),
    "fwr": ("observed", "final_write_off_rate"),
    "dar": ("observed", "dar_clean_days"),
    "clean dar": ("observed", "dar_clean_days"),
    "npsr": ("observed", "net_patient_service_revenue"),
    # Bridge / financial
    "ebitda": ("bridge", "total_ebitda_impact"),
    "total ebitda": ("bridge", "total_ebitda_impact"),
    # Meta
    "deal name": ("meta", "deal_name"),
    "deal id": ("meta", "deal_id"),
}

# Recognized operators.
_OPERATORS = {">=", "<=", "!=", ">", "<", "="}

# Regex: optional quotes around field, operator, value.
_QUERY_RE = re.compile(
    r"^\s*"
    r"(?P<field>[a-zA-Z_ ]+?)"
    r"\s*"
    r"(?P<op>>=|<=|!=|>|<|=)"
    r"\s*"
    r"(?P<value>.+?)"
    r"\s*$"
)


# ── Parser ────────────────────────────────────────────────────────

def _parse_value(raw: str) -> Any:
    """Coerce a value string to the appropriate Python type."""
    raw = raw.strip().strip("'\"")
    # Handle M/K suffixes for financial values.
    upper = raw.upper()
    if upper.endswith("M"):
        try:
            return float(upper[:-1]) * 1_000_000
        except ValueError:
            pass
    if upper.endswith("K"):
        try:
            return float(upper[:-1]) * 1_000
        except ValueError:
            pass
    # Try numeric.
    try:
        if "." in raw:
            return float(raw)
        return int(raw)
    except ValueError:
        pass
    # String fallback.
    return raw


def parse_query(query_str: str) -> List[QueryFilter]:
    """Parse a query string into a list of :class:`QueryFilter`.

    Supports multiple clauses separated by ``and`` (case-insensitive)
    or semicolons. Each clause is ``field op value``.

    Examples::

        "denial rate > 10"
        "state = IL and ebitda > 5M"
        "beds >= 200; state = TX"
    """
    filters: List[QueryFilter] = []
    # Split on " and " (case-insensitive) or ";"
    clauses = re.split(r"\s+and\s+|;", query_str, flags=re.IGNORECASE)
    for clause in clauses:
        clause = clause.strip()
        if not clause:
            continue
        m = _QUERY_RE.match(clause)
        if not m:
            logger.warning("Could not parse query clause: %r", clause)
            continue
        field_raw = m.group("field").strip().lower()
        op = m.group("op")
        val = _parse_value(m.group("value"))
        filters.append(QueryFilter(field=field_raw, operator=op, value=val))
    return filters


# ── Accessor ──────────────────────────────────────────────────────

def _extract_value(packet: Any, field_name: str) -> Any:
    """Extract a value from a packet given a field name in QUERY_FIELD_MAP."""
    mapping = QUERY_FIELD_MAP.get(field_name)
    if mapping is None:
        return None
    accessor_type, path = mapping
    try:
        if accessor_type == "profile":
            return getattr(packet.profile, path, None)
        elif accessor_type == "observed":
            om = packet.observed_metrics or {}
            metric = om.get(path)
            if metric is not None:
                return metric.value
            return None
        elif accessor_type == "bridge":
            br = packet.ebitda_bridge
            if br is not None:
                return getattr(br, path, None)
            return None
        elif accessor_type == "meta":
            return getattr(packet, path, None)
    except Exception:  # noqa: BLE001
        return None
    return None


def _compare(actual: Any, op: str, target: Any) -> bool:
    """Apply a comparison operator."""
    if actual is None:
        return False
    # String comparison for = and !=.
    if isinstance(target, str) or isinstance(actual, str):
        a_str = str(actual).strip().upper()
        t_str = str(target).strip().upper()
        if op == "=":
            return a_str == t_str
        if op == "!=":
            return a_str != t_str
        # Fall through to numeric for other ops.
        try:
            actual = float(actual)
            target = float(target)
        except (TypeError, ValueError):
            return False

    try:
        actual = float(actual)
        target = float(target)
    except (TypeError, ValueError):
        return False

    if op == ">":
        return actual > target
    if op == "<":
        return actual < target
    if op == ">=":
        return actual >= target
    if op == "<=":
        return actual <= target
    if op == "=":
        return abs(actual - target) < 1e-9
    if op == "!=":
        return abs(actual - target) >= 1e-9
    return False


# ── Executor ──────────────────────────────────────────────────────

def execute_query(
    store: Any,
    filters: List[QueryFilter],
) -> List[DealSummary]:
    """Load latest packet per deal, apply filters, return matches.

    Each deal is tested against all filters (AND semantics). A deal
    passes only if every filter matches.
    """
    from .analysis_store import list_packets, load_packet_by_id

    # Get all packets grouped by deal_id (latest first).
    all_rows = list_packets(store)
    if not all_rows:
        return []

    # Deduplicate: keep only the latest packet per deal.
    seen_deals: set = set()
    latest_rows: List[Dict[str, Any]] = []
    for row in all_rows:
        did = row.get("deal_id") or ""
        if did not in seen_deals:
            seen_deals.add(did)
            latest_rows.append(row)

    results: List[DealSummary] = []
    for row in latest_rows:
        packet = load_packet_by_id(store, row["id"])
        if packet is None:
            continue

        # Check all filters.
        all_match = True
        matched_values: Dict[str, Any] = {}
        for f in filters:
            actual = _extract_value(packet, f.field)
            if not _compare(actual, f.operator, f.value):
                all_match = False
                break
            matched_values[f.field] = actual

        if all_match:
            results.append(DealSummary(
                deal_id=packet.deal_id,
                deal_name=packet.deal_name or "",
                matched_values=matched_values,
            ))

    return results
