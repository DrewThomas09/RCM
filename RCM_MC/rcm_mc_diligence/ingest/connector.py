"""dbt connector orchestration.

Wraps a single dbt invocation against our ``seekingchartis`` connector
project. dbt is called via its programmatic ``dbtRunner`` (preferred)
which returns structured results without shelling out. If that is
unavailable we fall back to subprocess + parse ``run_results.json``.

The connector is intentionally scoped to the **input layer** only. The
full Tuva claims mart (CCSR, HCC, financial_pmpm, etc.) requires a
large set of seeds downloaded from Tuva's S3 bucket and would dominate
test runtime. Input layer is what partners need to trust the
ingestion step — the marts arrive in Phase 0.B.
"""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .warehouse import WarehouseAdapter


# ── Constants ────────────────────────────────────────────────────────

CONNECTOR_ROOT = Path(__file__).resolve().parent.parent / "connectors" / "seekingchartis"
CONNECTOR_VERSION = "0.1.0"
DEFAULT_TARGET = "dev"
DEFAULT_PROFILE = "seekingchartis"

# Restrict every run to the three Tuva input-layer models we care about
# in Phase 0.A. Each one is `select * from ref('<our_model>')`, so
# upstream selection `+` pulls in our connector models too.
DEFAULT_SELECT = [
    "+input_layer__medical_claim",
    "+input_layer__pharmacy_claim",
    "+input_layer__eligibility",
]


# ── Result shapes ────────────────────────────────────────────────────

@dataclass
class DbtTestResult:
    """One dbt test outcome — Tuva's DQ tests flow through here into
    ``DQReport.tuva_dq_results``."""
    unique_id: str
    name: str
    status: str          # "pass" | "fail" | "warn" | "error" | "skipped"
    severity: str        # "error" | "warn"
    failures: int
    message: str
    tags: Tuple[str, ...] = ()


@dataclass
class DbtRunResult:
    """Summary of one dbt invocation."""
    success: bool
    models: List[Dict[str, Any]] = field(default_factory=list)
    tests: List[DbtTestResult] = field(default_factory=list)
    elapsed_seconds: float = 0.0
    invocation_id: str = ""
    dbt_version: str = ""
    tuva_version: str = ""
    stdout_tail: str = ""
    stderr_tail: str = ""


# ── Public API ───────────────────────────────────────────────────────

def run_connector(
    adapter: WarehouseAdapter,
    *,
    run_dir: Path,
    select: Optional[Sequence[str]] = None,
    vars_overrides: Optional[Dict[str, Any]] = None,
) -> DbtRunResult:
    """Invoke dbt against the seekingchartis connector.

    ``run_dir`` is where we write a per-run ``profiles/`` directory and
    where dbt drops its ``target/`` artefacts. We isolate these per run
    so concurrent runs don't clobber each other and the global
    ``~/.dbt/profiles.yml`` stays untouched.
    """
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    # dbt wants a profiles.yml but reads it by pointing DBT_PROFILES_DIR
    # at the containing directory. Render ours against the adapter's
    # profile block so the file stays parameterised, not templated.
    profiles_dir = run_dir / "dbt_profiles"
    profiles_dir.mkdir(exist_ok=True)
    db_path = _resolve_db_path(adapter, run_dir)
    profile_block = adapter.profile_config(db_path)
    _write_profiles_yaml(profiles_dir / "profiles.yml", profile_block)

    target_dir = run_dir / "dbt_target"
    log_dir = run_dir / "dbt_logs"
    packages_dir = run_dir / "dbt_packages"
    target_dir.mkdir(exist_ok=True)
    log_dir.mkdir(exist_ok=True)
    packages_dir.mkdir(exist_ok=True)

    # Packages install into CONNECTOR_ROOT/dbt_packages — dbt's deps
    # command doesn't accept --packages-install-path in dbt-core 1.11,
    # so we rely on the default location inside the project dir.
    # Tuva + dbt_utils at fixed versions install once per project
    # checkout; subsequent `deps` calls are idempotent no-ops.
    shared_packages_dir = CONNECTOR_ROOT / "dbt_packages"
    _dbt_invoke(
        ["deps"],
        project_dir=CONNECTOR_ROOT,
        profiles_dir=profiles_dir,
        target_path=None,
        log_path=log_dir,
        packages_install_path=None,
    )

    select_list = list(select) if select is not None else list(DEFAULT_SELECT)
    args = ["build", "--select"] + select_list
    if vars_overrides:
        args += ["--vars", json.dumps(vars_overrides)]
    # dbt-core 1.11's build command also rejects --packages-install-path
    # (it's deps-time state). Both deps and build use the default
    # in-project location.
    cmd_result = _dbt_invoke(
        args,
        project_dir=CONNECTOR_ROOT,
        profiles_dir=profiles_dir,
        target_path=target_dir,
        log_path=log_dir,
        packages_install_path=None,
    )

    return _parse_run_results(cmd_result, target_dir)


# ── Internals ────────────────────────────────────────────────────────

def _resolve_db_path(adapter: WarehouseAdapter, run_dir: Path) -> Path:
    """Pull the DuckDB path off the adapter when we can, otherwise fall
    back to a default under ``run_dir``. Only DuckDBAdapter exposes
    ``db_path``; other backends raise :class:`NotImplementedError`
    before we get here.
    """
    path_attr = getattr(adapter, "db_path", None)
    if isinstance(path_attr, Path):
        return path_attr
    return run_dir / "diligence.duckdb"


def _write_profiles_yaml(path: Path, profile_block: Dict[str, Any]) -> None:
    """Write a minimal profiles.yml. Hand-rolled because the alternative
    is adding PyYAML to the diligence extra just to serialise six
    lines — not worth it.
    """
    lines = [
        f"{DEFAULT_PROFILE}:",
        f"  target: {DEFAULT_TARGET}",
        "  outputs:",
        f"    {DEFAULT_TARGET}:",
    ]
    for k, v in sorted(profile_block.items()):
        if isinstance(v, str):
            lines.append(f"      {k}: \"{v}\"")
        else:
            lines.append(f"      {k}: {v}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


@dataclass
class _DbtInvokeResult:
    success: bool
    results: Any            # programmatic dbtRunnerResult or None
    stdout: str
    stderr: str


def _dbt_invoke(
    args: Sequence[str],
    *,
    project_dir: Path,
    profiles_dir: Path,
    target_path: Optional[Path],
    log_path: Path,
    packages_install_path: Optional[Path],
) -> _DbtInvokeResult:
    """Invoke dbt via its programmatic entrypoint.

    Programmatic mode returns a structured result we can introspect
    without parsing CLI output, which matters for reliability.

    Flags like ``--target-path`` and ``--packages-install-path`` are
    only accepted by certain subcommands (``build``, ``run``, ``test``)
    — dbt-core 1.11's ``deps`` rejects them. Pass ``None`` to skip.
    """
    from dbt.cli.main import dbtRunner

    full_args: List[str] = [
        *args,
        "--project-dir", str(project_dir),
        "--profiles-dir", str(profiles_dir),
        "--log-path", str(log_path),
    ]
    if target_path is not None:
        full_args += ["--target-path", str(target_path)]
    if packages_install_path is not None:
        full_args += ["--packages-install-path", str(packages_install_path)]
    runner = dbtRunner()
    result = runner.invoke(full_args)
    success = bool(getattr(result, "success", False))
    return _DbtInvokeResult(success=success, results=result, stdout="", stderr="")


def _parse_run_results(
    invoke_result: _DbtInvokeResult, target_dir: Path
) -> DbtRunResult:
    """Parse ``target/run_results.json`` into :class:`DbtRunResult`.

    We prefer the file on disk over ``invoke_result.results`` because
    the file format is stable across dbt versions; the Python object
    shape is not.
    """
    rr_path = target_dir / "run_results.json"
    models: List[Dict[str, Any]] = []
    tests: List[DbtTestResult] = []
    invocation_id = ""
    dbt_version = ""
    elapsed = 0.0

    if rr_path.exists():
        try:
            doc = json.loads(rr_path.read_text(encoding="utf-8"))
            invocation_id = str(doc.get("metadata", {}).get("invocation_id", ""))
            dbt_version = str(doc.get("metadata", {}).get("dbt_version", ""))
            elapsed = float(doc.get("elapsed_time", 0.0))
            # manifest.json for test metadata (tags, severity)
            manifest = _load_manifest(target_dir)
            for r in doc.get("results", []):
                unique_id = str(r.get("unique_id", ""))
                status = str(r.get("status", ""))
                message = str(r.get("message") or "")
                failures = int(r.get("failures") or 0)
                node = manifest.get(unique_id, {}) if manifest else {}
                if unique_id.startswith("test."):
                    sev = str((node.get("config") or {}).get("severity") or "error")
                    tags = tuple((node.get("tags") or []))
                    tests.append(DbtTestResult(
                        unique_id=unique_id,
                        name=str(node.get("name") or unique_id.rsplit(".", 1)[-1]),
                        status=status, severity=sev, failures=failures,
                        message=message, tags=tags,
                    ))
                else:
                    models.append({
                        "unique_id": unique_id, "status": status,
                        "execution_time": float(r.get("execution_time") or 0.0),
                        "message": message,
                    })
        except Exception as exc:
            return DbtRunResult(
                success=False, stderr_tail=f"failed to parse run_results.json: {exc}",
            )

    return DbtRunResult(
        success=invoke_result.success,
        models=models, tests=tests,
        elapsed_seconds=elapsed,
        invocation_id=invocation_id,
        dbt_version=dbt_version,
        tuva_version=_extract_tuva_version(target_dir),
        stdout_tail=invoke_result.stdout[-4000:],
        stderr_tail=invoke_result.stderr[-4000:],
    )


def _load_manifest(target_dir: Path) -> Dict[str, Any]:
    """Load manifest.json indexed by unique_id. Returns {} if absent."""
    p = target_dir / "manifest.json"
    if not p.exists():
        return {}
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    out: Dict[str, Any] = {}
    for bucket in ("nodes", "sources", "exposures"):
        for uid, node in (doc.get(bucket) or {}).items():
            out[uid] = node
    return out


def _extract_tuva_version(target_dir: Path) -> str:
    """Try to read Tuva's version from the installed package. dbt
    writes the installed package metadata to
    ``target/partial_parse.msgpack`` — too binary to parse lightly. The
    project yaml in the installed package is easier.
    """
    # The packages are installed into run_dir/dbt_packages by the
    # orchestration above — we're passed target_dir here, but the
    # packages dir is a sibling. Climb one level and look.
    candidate = target_dir.parent / "dbt_packages" / "the_tuva_project" / "dbt_project.yml"
    if not candidate.exists():
        return ""
    try:
        for line in candidate.read_text(encoding="utf-8").splitlines():
            if line.startswith("version:"):
                return line.split(":", 1)[1].strip().strip("'\"")
    except Exception:
        return ""
    return ""
