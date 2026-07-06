"""One-command ingest across the whole connector estate.

Each connector ships its own CLI with its own ingest verbs (``discover``,
``fetch``, ``ingest``, ``backfill``) and its own storage flag (``--db`` for
the catalog-style connectors, ``--root`` for the earlier four). That
per-connector autonomy is deliberate — but it makes "just give me a seeded
estate database" a ten-command chore. This module owns the chore: a
declarative plan of polite, page-capped CLI invocations per connector,
executed as subprocesses of the same interpreter so each connector keeps
its self-contained import world.

Why subprocess rather than importing the connectors' Python APIs: the CLIs
are the *stable* per-connector surface (their flags are tested), the
processes keep SQLite writers isolated one-per-file, and a wedged fetch
cannot take the whole refresh down — failures are recorded per step and the
sweep continues.

The quick plan is sized to be runnable on a laptop in a few minutes and to
stay polite to the public APIs (catalog syncs + one-or-two page slices of
the flagship datasets). ``--full`` widens the caps but still never does an
unbounded pull of the multi-million-row files; those stay filter-driven by
design (see each connector's README).
"""
from __future__ import annotations

import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from ._spi import CONNECTOR_NAMES

# Connectors whose CLI takes --root DIR (db lives inside that dir) rather
# than --db FILE. The earlier four slices predate the --db convention.
_ROOT_STYLE = {"openfda", "cms_coverage", "npi_registry", "icd10", "hrsa_data"}

# Connectors that declare --db on each subcommand instead of the top-level
# parser; their storage flag must FOLLOW the verb or argparse rejects it.
_SUBCMD_DB_STYLE = {"cms_open_data", "open_payments"}

# ``quick`` argv suffixes per connector, run in order after
# ``python -m connectors.<name>.cli [--db …|--root …]``. Every entry is a
# catalog sync or a page-capped slice of a flagship dataset. census_acs is
# marked optional: api.census.gov requires CENSUS_API_KEY for data pulls,
# so without the env var those steps fail and are reported, not fatal.
_QUICK_PLAN: Dict[str, List[List[str]]] = {
    "cms_open_data": [
        ["discover"],
        ["fetch", "--dataset", "geo_variation_state_county", "--max-pages", "2"],
        ["fetch", "--dataset", "market_saturation_state_county", "--max-pages", "2"],
        ["fetch", "--dataset", "medicare_monthly_enrollment", "--max-pages", "2"],
        ["fetch", "--dataset", "part_b_spending_by_drug", "--max-pages", "1"],
        ["fetch", "--dataset", "part_d_spending_by_drug", "--max-pages", "1"],
        ["fetch", "--dataset", "hospital_cost_report", "--max-pages", "1"],
        ["fetch", "--dataset", "acos", "--max-pages", "1"],
        ["fetch", "--dataset", "pos_qies", "--max-pages", "2"],
        ["fetch", "--dataset", "pos_internet_qies", "--max-pages", "2"],
        ["fetch", "--dataset", "home_infusion_therapy_providers", "--max-pages", "2"],
        ["fetch", "--dataset", "rbcs", "--max-pages", "2"],
    ],
    "provider_data": [
        ["discover"],
        ["fetch", "--dataset", "hospital_general", "--max-pages", "4"],
        ["fetch", "--dataset", "nursing_home_provider_info", "--max-pages", "2"],
        ["fetch", "--dataset", "home_health_agencies", "--max-pages", "2"],
        ["fetch", "--dataset", "hospice_general", "--max-pages", "2"],
        ["fetch", "--dataset", "dialysis_facilities", "--max-pages", "2"],
        ["fetch", "--dataset", "dialysis_state_averages", "--max-pages", "1"],
        ["fetch", "--dataset", "dialysis_national_averages", "--max-pages", "1"],
        ["fetch", "--dataset", "ich_cahps_state", "--max-pages", "1"],
        ["fetch", "--dataset", "ich_cahps_national", "--max-pages", "1"],
        ["fetch", "--dataset", "esrd_qip_tps", "--max-pages", "2"],
        ["fetch", "--dataset", "asc_quality_state", "--max-pages", "1"],
        ["fetch", "--dataset", "asc_quality_national", "--max-pages", "1"],
        ["fetch", "--dataset", "medical_equipment_suppliers", "--max-pages", "2"],
    ],
    "open_payments": [
        ["discover"],
        ["fetch", "--dataset", "summary_dashboard"],
        ["fetch", "--dataset", "state_payment_totals"],
    ],
    "medicaid_data": [
        ["discover"],
        ["fetch", "--dataset", "nadac_2026", "--max-pages", "2"],
        ["fetch", "--dataset", "enrollment_monthly", "--max-pages", "2"],
        ["fetch", "--dataset", "managed_care_by_state_2024", "--max-pages", "1"],
    ],
    "healthcare_gov": [
        ["discover"],
        ["fetch", "--dataset", "plan_attributes_py2026", "--max-pages", "1"],
        ["fetch", "--dataset", "quality_puf_py2026", "--max-pages", "2"],
        ["fetch", "--dataset", "service_area_puf_py2026", "--max-pages", "2"],
    ],
    "cdc_data": [
        ["discover"],
        ["fetch", "--dataset", "places_county", "--max-pages", "2"],
        ["fetch", "--dataset", "places_county_ckd", "--max-pages", "2"],
        ["fetch", "--dataset", "vsrr_drug_overdose", "--max-pages", "1"],
        ["fetch", "--dataset", "nchs_leading_causes", "--max-pages", "1"],
        ["fetch", "--dataset", "flu_vaccination_coverage", "--max-pages", "1"],
        ["fetch", "--dataset", "stroke_mortality_county", "--max-pages", "2"],
        ["fetch", "--dataset", "infant_mortality_state", "--max-pages", "1"],
    ],
    "hrsa_data": [
        ["fetch", "--dataset", "hpsa_primary_care", "--max-rows", "5000"],
        ["fetch", "--dataset", "mua", "--max-rows", "3000"],
        ["fetch", "--dataset", "health_center_sites", "--max-rows", "5000"],
    ],
    "nih_reporter": [
        ["fetch", "--dataset", "projects", "--fiscal-year", "2025", "--max-pages", "2"],
    ],
    "census_acs": [
        ["fetch", "--dataset", "state_profile", "--year", "2023"],
        ["fetch", "--dataset", "county_profile", "--year", "2023"],
    ],
    "oig_leie": [
        ["fetch", "--dataset", "exclusions", "--max-rows", "5000"],
    ],
    "bls_qcew": [
        ["fetch", "--dataset", "industry_area", "--industry", "62",
         "--max-rows", "5000"],
        ["fetch", "--dataset", "industry_area", "--industry", "622",
         "--max-rows", "5000"],
    ],
    "healthdata_gov": [
        ["discover"],
        ["fetch", "--dataset", "hospital_ids"],
        ["fetch", "--dataset", "hospital_capacity_state_ts", "--max-pages", "2"],
        ["fetch", "--dataset", "community_profile_county", "--max-pages", "2"],
    ],
}

# Steps widened (not unbounded) by --full: bigger page caps on the slices.
_FULL_OVERRIDES: Dict[str, List[List[str]]] = {
    "cms_open_data": [
        ["discover"],
        ["fetch", "--dataset", "geo_variation_state_county", "--max-pages", "10"],
        ["fetch", "--dataset", "market_saturation_state_county", "--max-pages", "10"],
        ["fetch", "--dataset", "medicare_monthly_enrollment", "--max-pages", "10"],
        ["fetch", "--dataset", "part_b_spending_by_drug", "--max-pages", "2"],
        ["fetch", "--dataset", "part_d_spending_by_drug", "--max-pages", "5"],
        ["fetch", "--dataset", "hospital_cost_report", "--max-pages", "15"],
        ["fetch", "--dataset", "hospital_all_owners", "--max-pages", "10"],
        ["fetch", "--dataset", "acos", "--max-pages", "2"],
    ],
    "provider_data": [
        ["discover"],
        ["fetch", "--dataset", "hospital_general", "--max-pages", "12"],
        ["fetch", "--dataset", "nursing_home_provider_info", "--max-pages", "32"],
        ["fetch", "--dataset", "home_health_agencies", "--max-pages", "25"],
        ["fetch", "--dataset", "hospice_general", "--max-pages", "15"],
        ["fetch", "--dataset", "dialysis_facilities", "--max-pages", "17"],
        ["fetch", "--dataset", "irf_general", "--max-pages", "3"],
        ["fetch", "--dataset", "ltch_general", "--max-pages", "2"],
    ],
    "medicaid_data": [
        ["discover"],
        ["fetch", "--dataset", "nadac_2026", "--max-pages", "10"],
        ["fetch", "--dataset", "enrollment_monthly", "--max-pages", "10"],
        ["fetch", "--dataset", "managed_care_by_state_2024", "--max-pages", "1"],
        ["fetch", "--dataset", "financial_management_data", "--max-pages", "10"],
    ],
    "hrsa_data": [
        ["fetch", "--dataset", "hpsa_primary_care", "--full"],
        ["fetch", "--dataset", "hpsa_dental", "--full"],
        ["fetch", "--dataset", "hpsa_mental_health", "--full"],
        ["fetch", "--dataset", "mua", "--full"],
        ["fetch", "--dataset", "health_center_sites", "--full"],
    ],
    "oig_leie": [
        ["fetch", "--dataset", "exclusions", "--full"],
        ["fetch", "--dataset", "reinstatements"],
    ],
}

# Connectors with no unattended ingest in the plan (their ingest verbs need
# domain arguments — search terms, NPI lists, code ranges — and
# cms_coverage's ``discover`` is informational, not an ingest). They stay
# manual; see each README.
UNPLANNED: tuple = ("openfda", "cms_coverage", "npi_registry", "icd10")

_STEP_TIMEOUT_S = 600


@dataclass
class StepResult:
    connector: str
    argv: List[str]
    ok: bool
    returncode: int
    seconds: float
    tail: str = ""


@dataclass
class RefreshReport:
    db_dir: str
    steps: List[StepResult] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(s.ok for s in self.steps)

    def summary(self) -> str:
        lines = []
        for s in self.steps:
            mark = "ok " if s.ok else "FAIL"
            lines.append(f"{mark} {s.connector:16} {s.seconds:6.1f}s  {' '.join(s.argv)}")
        n_fail = sum(1 for s in self.steps if not s.ok)
        lines.append(f"{len(self.steps)} steps, {n_fail} failed, db_dir={self.db_dir}")
        return "\n".join(lines)


def plan(quick: bool = True,
         connectors: Optional[Sequence[str]] = None) -> Dict[str, List[List[str]]]:
    """The argv plan that :func:`refresh` would run (used by --dry-run)."""
    names = list(connectors) if connectors else [
        n for n in CONNECTOR_NAMES if n not in UNPLANNED]
    out: Dict[str, List[List[str]]] = {}
    for name in names:
        if name not in _QUICK_PLAN:
            raise KeyError(f"no refresh plan for connector {name!r}")
        steps = _QUICK_PLAN[name]
        if not quick and name in _FULL_OVERRIDES:
            steps = _FULL_OVERRIDES[name]
        out[name] = [list(s) for s in steps]
    return out


def _storage_argv(name: str, db_dir: str) -> List[str]:
    if name in _ROOT_STYLE:
        # --root connectors write {root}/{name}.db themselves; pointing root
        # at db_dir keeps every db at {db_dir}/{name}.db — the exact layout
        # the unified server's open_stores() expects.
        return ["--root", db_dir.rstrip("/")]
    return ["--db", f"{db_dir.rstrip('/')}/{name}.db"]


def refresh(db_dir: str, *, quick: bool = True,
            connectors: Optional[Sequence[str]] = None,
            runner: Any = None) -> RefreshReport:
    """Run the ingest plan, one subprocess per step, never raising per-step.

    ``runner`` is injectable for tests (same signature as
    ``subprocess.run``); default is the real thing.
    """
    run = runner or subprocess.run
    if runner is None:
        # Only touch the filesystem for a real run — injected-runner tests
        # must not leave stray directories in the caller's cwd.
        import os
        os.makedirs(db_dir, exist_ok=True)  # sqlite cannot create parent dirs
    report = RefreshReport(db_dir=db_dir)
    for name, steps in plan(quick=quick, connectors=connectors).items():
        storage = _storage_argv(name, db_dir)
        for argv in steps:
            if name in _SUBCMD_DB_STYLE:
                full = [sys.executable, "-m", f"connectors.{name}.cli",
                        *argv, *storage]
            else:
                full = [sys.executable, "-m", f"connectors.{name}.cli",
                        *storage, *argv]
            t0 = time.monotonic()
            try:
                proc = run(full, capture_output=True, text=True,
                           timeout=_STEP_TIMEOUT_S)
                ok = proc.returncode == 0
                tail = (proc.stdout or "").strip()[-400:] if ok else \
                    ((proc.stderr or "") + (proc.stdout or "")).strip()[-400:]
                report.steps.append(StepResult(
                    connector=name, argv=argv, ok=ok,
                    returncode=proc.returncode,
                    seconds=time.monotonic() - t0, tail=tail))
            except Exception as exc:  # timeout / spawn failure — record, continue
                report.steps.append(StepResult(
                    connector=name, argv=argv, ok=False, returncode=-1,
                    seconds=time.monotonic() - t0, tail=str(exc)[-400:]))
    return report
