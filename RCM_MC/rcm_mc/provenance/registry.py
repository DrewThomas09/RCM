"""ProvenanceRegistry — per-deal collection of DataPoints.

A registry is created at the start of a calculation, passed into the
simulator / pe_math / data-loaders, and at the end contains the full
dependency tree for every metric produced during the run. It can be:

- persisted to the SQLite ``metric_provenance`` table keyed on
  ``(deal_id, run_id)``,
- exported as a JSON dependency graph,
- queried for a plain-English explanation of any one metric via
  :meth:`ProvenanceRegistry.human_explain`.

The registry is intentionally standalone — it does not depend on the
simulator or any other module. Callers import it, create an instance,
and pass it along.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from .tracker import DataPoint, Source


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ────────────────────────────────────────────────────────────────────
# SQLite persistence
# ────────────────────────────────────────────────────────────────────

def _ensure_provenance_table(store) -> None:
    """Create the metric_provenance table. Idempotent."""
    store.init_db()
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS metric_provenance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deal_id TEXT NOT NULL,
                run_id TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                value REAL NOT NULL,
                source TEXT NOT NULL,
                source_detail TEXT NOT NULL DEFAULT '',
                confidence REAL NOT NULL DEFAULT 1.0,
                as_of_date TEXT NOT NULL,
                upstream_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL
            )"""
        )
        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_metric_provenance_deal_metric "
            "ON metric_provenance(deal_id, metric_name)"
        )
        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_metric_provenance_run "
            "ON metric_provenance(deal_id, run_id)"
        )
        con.commit()


# ────────────────────────────────────────────────────────────────────
# Registry
# ────────────────────────────────────────────────────────────────────

class ProvenanceRegistry:
    """Per-deal collection of DataPoints.

    Insertion order matters for ties: recording two DataPoints under
    the same ``metric_name`` overwrites in-order (last-write-wins).
    This matches how a partner intuits "the number" for a metric —
    the latest calculation is the canonical one; older versions are
    visible only in the SQLite audit log.
    """

    def __init__(self, deal_id: Optional[str] = None,
                 run_id: Optional[str] = None) -> None:
        self.deal_id = deal_id
        self.run_id = run_id
        self._points: Dict[str, DataPoint] = {}

    # ---- Core record / lookup API ----

    def record(self, dp: DataPoint) -> DataPoint:
        """Store a DataPoint. Returns the stored DataPoint."""
        if not isinstance(dp, DataPoint):
            raise TypeError("record() expects a DataPoint")
        self._points[dp.metric_name] = dp
        return dp

    def get(self, metric_name: str) -> Optional[DataPoint]:
        """Return the DataPoint for a metric, or None if absent."""
        return self._points.get(metric_name)

    def all_metrics(self) -> List[str]:
        """All metric names currently in the registry, insertion
        order."""
        return list(self._points.keys())

    def __contains__(self, metric_name: str) -> bool:
        return metric_name in self._points

    def __len__(self) -> int:
        return len(self._points)

    # ---- Convenience recorders (one per Source) ----

    def record_user_input(
        self,
        value: float,
        metric_name: str,
        *,
        source_detail: str = "",
        as_of_date: Optional[date] = None,
    ) -> DataPoint:
        return self.record(DataPoint(
            value=value, metric_name=metric_name,
            source=Source.USER_INPUT,
            source_detail=source_detail or "User-provided value",
            confidence=1.0,
            as_of_date=as_of_date or date.today(),
        ))

    def record_hcris(
        self,
        value: float,
        metric_name: str,
        *,
        ccn: str,
        fiscal_year: int,
        source_detail: str = "",
        as_of_date: Optional[date] = None,
        confidence: float = 0.95,
    ) -> DataPoint:
        detail = source_detail or f"HCRIS {fiscal_year} CCN {ccn}"
        return self.record(DataPoint(
            value=value, metric_name=metric_name,
            source=Source.HCRIS,
            source_detail=detail, confidence=confidence,
            as_of_date=as_of_date or date(fiscal_year, 12, 31),
        ))

    def record_irs990(
        self,
        value: float,
        metric_name: str,
        *,
        ein: str,
        tax_year: int,
        source_detail: str = "",
        confidence: float = 0.95,
    ) -> DataPoint:
        detail = source_detail or f"IRS Form 990 EIN {ein} TY{tax_year}"
        return self.record(DataPoint(
            value=value, metric_name=metric_name,
            source=Source.IRS990,
            source_detail=detail, confidence=confidence,
            as_of_date=date(tax_year, 12, 31),
        ))

    def record_regression(
        self,
        value: float,
        metric_name: str,
        *,
        upstream: Iterable[DataPoint],
        r_squared: float,
        n_samples: int,
        predictor_summary: str = "",
        as_of_date: Optional[date] = None,
    ) -> DataPoint:
        detail = (
            f"Linear regression from {n_samples} comparable hospitals"
            + (f" ({predictor_summary})" if predictor_summary else "")
            + f", R²={r_squared:.2f}"
        )
        # Clamp confidence — R² can exceed 1 on some out-of-sample
        # metrics or go negative; 0-1 is our invariant.
        conf = max(0.0, min(1.0, float(r_squared)))
        return self.record(DataPoint(
            value=value, metric_name=metric_name,
            source=Source.REGRESSION_PREDICTED,
            source_detail=detail, confidence=conf,
            as_of_date=as_of_date or date.today(),
            upstream=list(upstream),
        ))

    def record_benchmark_median(
        self,
        value: float,
        metric_name: str,
        *,
        cohort_description: str,
        n_peers: int,
        confidence: float = 0.8,
        as_of_date: Optional[date] = None,
    ) -> DataPoint:
        detail = (
            f"Peer-group median ({n_peers} peers: {cohort_description})"
        )
        return self.record(DataPoint(
            value=value, metric_name=metric_name,
            source=Source.BENCHMARK_MEDIAN,
            source_detail=detail, confidence=confidence,
            as_of_date=as_of_date or date.today(),
        ))

    def record_mc(
        self,
        value: float,
        metric_name: str,
        *,
        n_sims: int,
        percentile: int = 50,
        stddev: Optional[float] = None,
        upstream: Optional[Iterable[DataPoint]] = None,
        as_of_date: Optional[date] = None,
    ) -> DataPoint:
        detail = f"Monte Carlo p{percentile} of {n_sims} simulations"
        # Confidence derived from coefficient of variation when
        # stddev is provided.
        conf = 0.8
        if stddev is not None and value:
            cv = abs(stddev) / max(abs(value), 1e-9)
            conf = max(0.0, min(1.0, 1.0 - cv))
        return self.record(DataPoint(
            value=value, metric_name=metric_name,
            source=Source.MONTE_CARLO_P50,
            source_detail=detail, confidence=conf,
            as_of_date=as_of_date or date.today(),
            upstream=list(upstream or []),
        ))

    def record_calc(
        self,
        value: float,
        metric_name: str,
        *,
        formula: str,
        upstream: Iterable[DataPoint],
        confidence: Optional[float] = None,
        as_of_date: Optional[date] = None,
    ) -> DataPoint:
        upstream_list = list(upstream)
        # Default: propagate the minimum-confidence input so a
        # calculation is never more trustworthy than its weakest link.
        if confidence is None:
            confidence = (
                min((u.confidence for u in upstream_list), default=1.0)
                if upstream_list else 1.0
            )
        return self.record(DataPoint(
            value=value, metric_name=metric_name,
            source=Source.CALCULATED,
            source_detail=formula, confidence=confidence,
            as_of_date=as_of_date or date.today(),
            upstream=upstream_list,
        ))

    # ---- Traversal ----

    def trace(
        self, metric_name: str, *, max_depth: int = 64,
    ) -> List[DataPoint]:
        """Recursive upstream chain for ``metric_name``, topologically
        ordered (roots first). Returns empty list on unknown metric.

        Cycle-safe: a seen set prevents infinite recursion if two
        DataPoints ever reference each other.
        """
        root = self._points.get(metric_name)
        if root is None:
            return []
        out: List[DataPoint] = []
        seen: set = set()

        def _walk(dp: DataPoint, depth: int) -> None:
            key = id(dp)
            if key in seen or depth > max_depth:
                return
            seen.add(key)
            for u in dp.upstream:
                _walk(u, depth + 1)
            out.append(dp)

        _walk(root, 0)
        return out

    def dependency_graph(self) -> Dict[str, Any]:
        """Export the full graph as a JSON-serialisable dict.

        Shape::

            {
              "nodes": [{ metric_name, value, source, ... }, ...],
              "edges": [[from_metric_name, to_metric_name], ...]
            }

        ``from → to`` means "from feeds into to" (i.e. from is an
        upstream of to)."""
        nodes = [dp.to_dict() for dp in self._points.values()]
        edges = []
        for dp in self._points.values():
            for u in dp.upstream:
                edges.append([u.metric_name, dp.metric_name])
        return {"nodes": nodes, "edges": edges}

    # ---- Human explanation ----

    def human_explain(self, metric_name: str) -> str:
        """Plain-English one- or two-paragraph explanation of how a
        metric was produced. Returns a fallback string if the metric
        isn't in the registry — never raises, because this is called
        from partner-facing UI."""
        dp = self._points.get(metric_name)
        if dp is None:
            return (
                f"No provenance recorded for {metric_name!r}. "
                f"The metric may not have been produced in the latest run."
            )

        value_str = _fmt_value(dp.value, metric_name)

        # Headline — what IS the number, how was it produced
        if dp.source == Source.USER_INPUT:
            headline = (
                f"{_pretty_metric(metric_name)} of {value_str} was "
                f"provided directly by the analyst."
            )
        elif dp.source == Source.HCRIS:
            headline = (
                f"{_pretty_metric(metric_name)} of {value_str} was "
                f"pulled from the HCRIS dataset. {dp.source_detail}."
            )
        elif dp.source == Source.IRS990:
            headline = (
                f"{_pretty_metric(metric_name)} of {value_str} was "
                f"pulled from IRS Form 990. {dp.source_detail}."
            )
        elif dp.source == Source.REGRESSION_PREDICTED:
            headline = (
                f"{_pretty_metric(metric_name)} of {value_str} was "
                f"predicted using {dp.source_detail.lower()}."
            )
        elif dp.source == Source.BENCHMARK_MEDIAN:
            headline = (
                f"{_pretty_metric(metric_name)} of {value_str} was "
                f"taken as a {dp.source_detail.lower()}."
            )
        elif dp.source == Source.MONTE_CARLO_P50:
            headline = (
                f"{_pretty_metric(metric_name)} of {value_str} is the "
                f"{dp.source_detail}."
            )
        elif dp.source == Source.CALCULATED:
            headline = (
                f"{_pretty_metric(metric_name)} of {value_str} was "
                f"computed as {dp.source_detail}."
            )
        else:  # pragma: no cover — new source?
            headline = (
                f"{_pretty_metric(metric_name)} of {value_str} "
                f"(source: {dp.source.value})."
            )

        confidence_note = (
            f"Confidence: {dp.confidence:.0%}."
            if dp.confidence < 1.0 else ""
        )

        # Upstream driver summary — only the direct parents, not the
        # full recursive tree (the partner asked "why is this 8.2%";
        # showing a tree of 40 nodes doesn't answer that).
        if dp.upstream:
            bits = []
            for u in dp.upstream[:6]:  # cap at 6 to keep it readable
                uval = _fmt_value(u.value, u.metric_name)
                src = _source_short(u.source)
                bits.append(f"{_pretty_metric(u.metric_name)} ({uval}, {src})")
            more = (
                f", plus {len(dp.upstream) - 6} more inputs"
                if len(dp.upstream) > 6 else ""
            )
            drivers = "Key drivers: " + ", ".join(bits) + more + "."
        else:
            drivers = ""

        parts = [p for p in [headline, confidence_note, drivers] if p]
        return " ".join(parts)

    # ---- Persistence ----

    def save(self, store, deal_id: Optional[str] = None,
             run_id: Optional[str] = None) -> int:
        """Write all DataPoints to the ``metric_provenance`` table.
        Returns the number of rows inserted.

        ``deal_id`` and ``run_id`` are required either on the registry
        or as arguments. Saving the same registry twice under the
        same ``(deal_id, run_id)`` appends — historical versions are
        preserved."""
        did = deal_id or self.deal_id
        rid = run_id or self.run_id
        if not did or not rid:
            raise ValueError("deal_id and run_id required to save")
        _ensure_provenance_table(store)
        inserted = 0
        now = _utcnow_iso()
        with store.connect() as con:
            for dp in self._points.values():
                con.execute(
                    "INSERT INTO metric_provenance "
                    "(deal_id, run_id, metric_name, value, source, "
                    " source_detail, confidence, as_of_date, "
                    " upstream_json, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (did, rid, dp.metric_name, dp.value,
                     dp.source.value, dp.source_detail, dp.confidence,
                     dp.as_of_date.isoformat(),
                     json.dumps([u.metric_name for u in dp.upstream]),
                     now),
                )
                inserted += 1
            con.commit()
        return inserted

    @classmethod
    def load(cls, store, deal_id: str,
             run_id: Optional[str] = None) -> "ProvenanceRegistry":
        """Read a registry back from SQLite. When ``run_id`` is None,
        loads the most-recent run for the deal.

        Rows written by multiple saves of the same (deal_id, run_id)
        collapse to the latest-inserted DataPoint per metric_name —
        matching the in-memory last-write-wins semantic."""
        _ensure_provenance_table(store)
        with store.connect() as con:
            if run_id is None:
                row = con.execute(
                    "SELECT run_id FROM metric_provenance "
                    "WHERE deal_id = ? "
                    "ORDER BY id DESC LIMIT 1",
                    (deal_id,),
                ).fetchone()
                if row is None:
                    return cls(deal_id=deal_id)
                run_id = row["run_id"]
            rows = con.execute(
                """SELECT metric_name, value, source, source_detail,
                          confidence, as_of_date, upstream_json, id
                   FROM metric_provenance
                   WHERE deal_id = ? AND run_id = ?
                   ORDER BY id ASC""",
                (deal_id, run_id),
            ).fetchall()
        reg = cls(deal_id=deal_id, run_id=run_id)
        # First pass: rehydrate without upstream (we need all names
        # available before we can wire up references).
        by_name: Dict[str, DataPoint] = {}
        raw_upstream: Dict[str, List[str]] = {}
        for r in rows:
            name = r["metric_name"]
            try:
                upstream_names = json.loads(r["upstream_json"] or "[]")
            except (ValueError, TypeError):
                upstream_names = []
            dp = DataPoint(
                value=float(r["value"]),
                metric_name=name,
                source=Source(r["source"]),
                source_detail=r["source_detail"] or "",
                confidence=float(r["confidence"]),
                as_of_date=date.fromisoformat(r["as_of_date"]),
                upstream=[],  # filled in second pass
            )
            by_name[name] = dp
            raw_upstream[name] = upstream_names
        # Second pass: wire upstream references (cycle-safe — a
        # malformed cycle in the DB would only produce a flat graph
        # when walked, not infinite recursion, because trace() has
        # its own seen-set).
        for name, up_names in raw_upstream.items():
            dp = by_name[name]
            upstream_resolved = [by_name[u] for u in up_names
                                  if u in by_name]
            # Rebuild with upstream; frozen=True means we must
            # construct a new instance.
            by_name[name] = DataPoint(
                value=dp.value,
                metric_name=dp.metric_name,
                source=dp.source,
                source_detail=dp.source_detail,
                confidence=dp.confidence,
                as_of_date=dp.as_of_date,
                upstream=upstream_resolved,
            )
        for name in raw_upstream:  # preserve insertion order
            reg.record(by_name[name])
        return reg


# ────────────────────────────────────────────────────────────────────
# Formatting helpers (partner-facing prose)
# ────────────────────────────────────────────────────────────────────

_PERCENT_METRICS = {
    "denial_rate", "initial_denial_rate", "idr_blended",
    "final_writeoff_rate", "fwr_blended", "clean_claim_rate",
    "medicare_day_pct", "irr", "weighted_irr",
    "variance_pct", "moic_growth_pct", "exit_multiple_delta",
}

_MULTIPLE_METRICS = {
    "moic", "weighted_moic", "entry_multiple", "exit_multiple",
    "covenant_headroom_turns", "actual_leverage",
}

_DAYS_METRICS = {
    "days_in_ar", "dar_clean_days", "dar", "hold_years",
    "days_open", "days_overdue",
}


def _pretty_metric(name: str) -> str:
    """'denial_rate' → 'Denial rate'."""
    return name.replace("_", " ").capitalize()


def _fmt_value(v: float, metric_name: str) -> str:
    """Format a metric value per the project-wide conventions in
    CLAUDE.md (2dp money, 1dp %, 2dp x-multiples)."""
    if metric_name in _PERCENT_METRICS:
        return f"{v * 100:.1f}%"
    if metric_name in _MULTIPLE_METRICS:
        return f"{v:.2f}x"
    if metric_name in _DAYS_METRICS:
        return f"{v:.1f} days"
    # Financial default: 2 decimals, thousands separators
    if abs(v) >= 1_000:
        return f"{v:,.2f}"
    return f"{v:.2f}"


def _source_short(source: Source) -> str:
    return {
        Source.USER_INPUT: "user-provided",
        Source.HCRIS: "from HCRIS",
        Source.IRS990: "from IRS Form 990",
        Source.REGRESSION_PREDICTED: "regression-predicted",
        Source.BENCHMARK_MEDIAN: "peer median",
        Source.MONTE_CARLO_P50: "MC simulation",
        Source.CALCULATED: "calculated",
    }.get(source, source.value)
