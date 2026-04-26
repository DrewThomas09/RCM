"""Demo database seeder — populate a SQLite DB so the v3 dashboard renders.

Per ``docs/design-handoff/SEEDER_PROPOSAL.md`` (commit ``e27c5de``) and
``docs/DEMO_CHECKLIST.md``: the editorial dashboard at ``/app?ui=v3``
renders empty-state across every block when the DB has no data. That's
correct behaviour, but unusable for a partner walkthrough. This module
populates a clean DB with 7 curated fictional hospital systems so every
block on the dashboard demonstrates real analytical work.

Public API:
    seed_demo_db(db_path, *, deal_count=7, snapshot_quarters=8,
                 seed_random=20260425, overwrite=False,
                 write_export_files=True, base_dir=None) -> SeedResult

CLI:
    python -m rcm_mc.dev.seed --db /tmp/demo.db
    python -m rcm_mc.dev.seed --db /tmp/demo.db --overwrite --deal-count 10
    python -m rcm_mc.dev.seed --db /tmp/demo.db --no-export-files
    python -m rcm_mc.dev.seed --db /tmp/demo.db --verify

The seeder refuses to run against a path that looks like production
(`/data/...` or filenames matching `seekingchartis.db`) unless
``force=True`` is passed. This is the "I meant /tmp/demo.db but typed
seekingchartis.db" guard.

Determinism: same ``seed_random`` produces byte-for-byte identical
data — same deal names, same EBITDA values, same covenant trajectories.
The default ``20260425`` is the date this seeder was authored.

Honesty: the seeder runs the real ``get_or_build_packet()`` pipeline for
focused-candidate deals so the EBITDA-drag block renders against actual
bridge math, not a hand-crafted fake. ~10-30 sec one-time cost; this is
the operator's tax for not inventing numbers.

Q1-Q6 decisions resolved per SEEDER_PROPOSAL.md (Andrew, 2026-04-26):
  C1 — base dir defaults to tempfile.gettempdir() / rcm_mc_demo_exports
  C2 — run real packet builder synchronously
  C3 — deal_count keeps first N curated deals; >7 extends with extra_NNN
  C4 — --verify flag included from first commit
  C5 — both unit and integration tests in separate commits
  C6 — function name seed_demo_db()
"""
from __future__ import annotations

import argparse
import logging
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Union

logger = logging.getLogger(__name__)


# ── Production-target guard ─────────────────────────────────────────

class SeederRefuseError(RuntimeError):
    """Raised when the seeder declines to run against a target.

    Reasons:
      - db_path looks like a production location (`/data/...` or
        `seekingchartis.db`) and force=False
      - db_path exists with non-empty deals table and overwrite=False
    """


_PROD_HINTS = ("/data/", "seekingchartis.db")


def _guard_against_production(db_path: Path, *, force: bool) -> None:
    """Refuse to seed if the target path looks like a production DB.

    Soft heuristic — operator can override with ``force=True`` (or the
    ``--force-prod-path`` CLI flag). The default refusal eliminates the
    "I meant /tmp/demo.db but typed seekingchartis.db" failure mode.
    """
    if force:
        return
    resolved = str(db_path.resolve())
    if any(hint in resolved for hint in _PROD_HINTS):
        raise SeederRefuseError(
            f"db_path {resolved!r} looks like a production target. "
            f"Pass force=True (or --force-prod-path on the CLI) to override. "
            f"Recognized production hints: {_PROD_HINTS}"
        )


# ── Result + counters ───────────────────────────────────────────────

@dataclass
class SeedResult:
    """Counts of what landed in the seeded DB.

    Returned from seed_demo_db() so callers (and the verify path) can
    sanity-check the result. All counts default to 0; sections that
    aren't seeded leave their counter at 0.
    """
    deals_inserted: int = 0
    snapshots_inserted: int = 0
    stage_transitions_inserted: int = 0
    actuals_inserted: int = 0
    packets_built: int = 0
    exports_inserted: int = 0
    export_files_written: int = 0
    deals_skipped: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0

    def summary(self) -> str:
        """One-line summary for CLI output."""
        return (
            f"deals={self.deals_inserted} snapshots={self.snapshots_inserted} "
            f"stages={self.stage_transitions_inserted} "
            f"actuals={self.actuals_inserted} packets={self.packets_built} "
            f"exports={self.exports_inserted} files={self.export_files_written} "
            f"in {self.duration_seconds:.1f}s"
        )


# ── Public API skeleton ─────────────────────────────────────────────

def seed_demo_db(
    db_path: Union[str, Path],
    *,
    deal_count: int = 7,
    snapshot_quarters: int = 8,
    seed_random: int = 20260425,
    overwrite: bool = False,
    write_export_files: bool = True,
    base_dir: Optional[Union[str, Path]] = None,
    force: bool = False,
) -> SeedResult:
    """Seed a SQLite DB with fictional hospital-system demo data.

    Args:
        db_path: SQLite file. Created if missing. Refused if it looks
            like a production target (see ``_guard_against_production``).
        deal_count: How many of the 7 curated deals to seed. ``>7``
            extends with auto-named ``extra_NNN`` deals at ``sourced``
            stage.
        snapshot_quarters: How many trailing quarters of snapshots
            per held deal. Default 8 = 2 fiscal years.
        seed_random: Seed for the random module. Same value produces
            byte-for-byte identical output.
        overwrite: If True and ``db_path`` has any rows in ``deals``,
            drop and recreate the seeded tables. Default False raises
            ``SeederRefuseError`` instead of clobbering.
        write_export_files: If False, write ``generated_exports`` rows
            but skip writing placeholder files to disk. Saves I/O on
            "I just want the dashboard to render" runs.
        base_dir: Where placeholder export files land. Default
            ``tempfile.gettempdir() / "rcm_mc_demo_exports"``.
        force: Override the production-target guard. Use with care.

    Returns:
        ``SeedResult`` with counts.

    Raises:
        SeederRefuseError: production-target guard tripped, or db_path
            already populated and overwrite=False.
    """
    # Skeleton only in this commit. Subsequent commits add the per-block
    # seed logic (deals, snapshots, actuals, packets, exports).
    db_path_obj = Path(db_path)
    _guard_against_production(db_path_obj, force=force)

    if base_dir is None:
        base_dir = Path(tempfile.gettempdir()) / "rcm_mc_demo_exports"
    base_dir = Path(base_dir)

    import time
    started = time.monotonic()
    result = SeedResult()

    # Body wired in subsequent commits — for now, just create the DB
    # and verify the guard + signature work end-to-end.
    from rcm_mc.portfolio.store import PortfolioStore
    from rcm_mc.infra.migrations import run_pending
    store = PortfolioStore(str(db_path_obj))
    run_pending(store)

    if not overwrite:
        with store.connect() as con:
            existing = con.execute(
                "SELECT COUNT(*) AS n FROM deals"
            ).fetchone()
            if existing and existing["n"] > 0:
                raise SeederRefuseError(
                    f"db_path {db_path_obj} already has "
                    f"{existing['n']} rows in deals. Pass overwrite=True "
                    f"(or --overwrite on the CLI) to clobber."
                )

    result.duration_seconds = time.monotonic() - started
    return result


# ── CLI entrypoint ──────────────────────────────────────────────────

def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m rcm_mc.dev.seed",
        description="Seed a SQLite DB with demo data for /app?ui=v3.",
    )
    p.add_argument("--db", required=True,
                   help="Path to SQLite DB to seed (created if missing)")
    p.add_argument("--deal-count", type=int, default=7,
                   help="Number of curated deals to seed (default 7)")
    p.add_argument("--snapshot-quarters", type=int, default=8,
                   help="Trailing quarters of snapshots per held deal")
    p.add_argument("--seed", dest="seed_random", type=int, default=20260425,
                   help="Random seed for determinism")
    p.add_argument("--overwrite", action="store_true",
                   help="Drop+recreate seeded tables if DB is non-empty")
    p.add_argument("--no-export-files", dest="write_export_files",
                   action="store_false",
                   help="Skip writing placeholder export files to disk")
    p.add_argument("--export-base", dest="base_dir", default=None,
                   help="Where placeholder export files land "
                        "(default: tempfile)")
    p.add_argument("--force-prod-path", dest="force", action="store_true",
                   help="Override the production-target guard")
    p.add_argument("--verify", action="store_true",
                   help="After seeding, re-run DEMO_CHECKLIST verification "
                        "commands and exit non-zero if any expected counts "
                        "fail")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    try:
        result = seed_demo_db(
            args.db,
            deal_count=args.deal_count,
            snapshot_quarters=args.snapshot_quarters,
            seed_random=args.seed_random,
            overwrite=args.overwrite,
            write_export_files=args.write_export_files,
            base_dir=args.base_dir,
            force=args.force,
        )
    except SeederRefuseError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    print(result.summary())
    if args.verify:
        # --verify path lands in a later commit. Skeleton commit just
        # acknowledges the flag exists.
        print("(--verify body lands in a subsequent commit)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
