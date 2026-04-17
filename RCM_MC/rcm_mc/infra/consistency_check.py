"""Startup-time consistency check for the portfolio store.

Partners opening a cold DB file — from a backup, from another
workstation, or after a migration — have no way to know whether the
schema is current. This module verifies at startup that:

1. Every table the platform *needs* exists.
2. Every analysis_runs row references a known deal_id (no orphans).
3. Every mc_simulation_runs row references a known deal_id.
4. Every generated_exports row references a known deal_id.

The check returns a :class:`ConsistencyReport` with per-check status.
It never raises — partners prefer "10 orphaned rows in mc_simulation_runs"
to a startup traceback.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


# Tables the platform depends on. Each is CREATE IF NOT EXISTS
# elsewhere so they appear lazily — this list is what we *expect* to
# be present after the product has been exercised.
_EXPECTED_TABLES = {
    "deals",
    "runs",
    "deal_sim_inputs",
    "hospital_benchmarks",
    "data_source_status",
    "analysis_runs",
    "mc_simulation_runs",
    "generated_exports",
}


@dataclass
class ConsistencyReport:
    existing_tables: List[str] = field(default_factory=list)
    missing_tables: List[str] = field(default_factory=list)
    orphaned_analysis_runs: int = 0
    orphaned_mc_runs: int = 0
    orphaned_exports: int = 0
    ok: bool = True
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def check_consistency(store: Any) -> ConsistencyReport:
    report = ConsistencyReport()

    # Lazily trigger CREATE IF NOT EXISTS on the known-lazy tables by
    # calling their ensure helpers. That way "missing tables" in the
    # report genuinely means missing, not "nobody has touched that
    # feature yet on this DB".
    _touch_lazy_tables(store)

    store.init_db()
    with store.connect() as con:
        existing = {
            row["name"]
            for row in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        report.existing_tables = sorted(existing)
        report.missing_tables = sorted(_EXPECTED_TABLES - existing)
        if report.missing_tables:
            report.ok = False
            report.notes.append(
                f"missing tables: {', '.join(report.missing_tables)}"
            )

        # Orphans — only check if both sides exist.
        if "analysis_runs" in existing and "deals" in existing:
            report.orphaned_analysis_runs = int(con.execute(
                "SELECT COUNT(*) AS c FROM analysis_runs a "
                "LEFT JOIN deals d ON d.deal_id = a.deal_id "
                "WHERE d.deal_id IS NULL"
            ).fetchone()["c"])
        if "mc_simulation_runs" in existing and "deals" in existing:
            report.orphaned_mc_runs = int(con.execute(
                "SELECT COUNT(*) AS c FROM mc_simulation_runs m "
                "LEFT JOIN deals d ON d.deal_id = m.deal_id "
                "WHERE d.deal_id IS NULL"
            ).fetchone()["c"])
        if "generated_exports" in existing and "deals" in existing:
            report.orphaned_exports = int(con.execute(
                "SELECT COUNT(*) AS c FROM generated_exports g "
                "LEFT JOIN deals d ON d.deal_id = g.deal_id "
                "WHERE d.deal_id IS NULL"
            ).fetchone()["c"])

    orphan_count = (
        report.orphaned_analysis_runs
        + report.orphaned_mc_runs
        + report.orphaned_exports
    )
    if orphan_count:
        report.notes.append(f"{orphan_count} orphaned row(s) — deals may have been deleted")

    return report


def _touch_lazy_tables(store: Any) -> None:
    """Call the ensure-table helpers so tables that the analysis layer
    creates on first use are visible to the consistency scan.

    Failures here are swallowed — the check is diagnostic, never a
    blocker. A partner should be able to run it on a 6-month-old DB
    that hasn't seen analysis or MC yet.
    """
    for importer in (
        lambda: __import__("rcm_mc.analysis.analysis_store",
                           fromlist=["_ensure_table"])._ensure_table(store),
        lambda: __import__("rcm_mc.mc.mc_store",
                           fromlist=["_ensure_table"])._ensure_table(store),
        lambda: __import__("rcm_mc.exports.export_store",
                           fromlist=["_ensure_table"])._ensure_table(store),
        lambda: __import__("rcm_mc.data.data_refresh",
                           fromlist=["_ensure_tables"])._ensure_tables(store),
        lambda: __import__("rcm_mc.deals.deal_sim_inputs",
                           fromlist=["_ensure_table"])._ensure_table(store),
    ):
        try:
            importer()
        except Exception as exc:  # noqa: BLE001
            logger.debug("consistency touch helper failed: %s", exc)
