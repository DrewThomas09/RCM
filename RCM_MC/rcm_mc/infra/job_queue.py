"""In-process simulation job queue (Brick 95).

Allows the web UI to trigger a full ``rcm-mc run`` without blocking the
request. Analysts post simulation parameters, get back a job ID, and poll
for progress / completion on a dedicated page.

Design constraints:

- **Single-process, in-memory registry.** No Redis, no Celery. The
  portfolio we target is 5-30 deals and the server is a single Python
  process running on one analyst's laptop or a small team VM. Jobs live
  in a dict keyed by UUID; a `threading.Lock` guards access.

- **One worker thread.** Monte Carlo runs are CPU-bound and writing to
  the same SQLite file serially is simpler than coordinating
  concurrent writes. A single worker processes jobs FIFO.

- **Pluggable runner.** The worker calls a ``run_fn`` that tests can
  replace with a fast mock. Production uses the real
  :func:`rcm_mc.cli.run_main`.

- **No persistence across process restarts.** If the server restarts,
  in-flight jobs show as ``orphaned``. Acceptable for MVP — the run
  outputs still land on disk, users can re-register the snapshot.

Public API::

    registry = get_default_registry()
    job_id = registry.submit_run(actual, benchmark, outdir, n_sims, seed)
    job = registry.get(job_id)           # → Job dataclass
    jobs = registry.list_recent(n=20)    # newest first
"""
from __future__ import annotations

import contextlib
import io
import os
import queue
import threading
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional


# ── Dataclass ─────────────────────────────────────────────────────────────

# Status values flow linearly queued → running → (done | failed).
# Jobs never move backward. Terminal states remain in memory until the
# registry is dropped.
JOB_STATUSES = ("queued", "running", "done", "failed")


@dataclass
class Job:
    """One simulation job tracked in the registry.

    Attributes are written by the worker; tests read them via the
    registry's thread-safe accessors (``get`` / ``list_recent``).
    """
    job_id: str
    status: str
    created_at: str
    kind: str                              # "sim_run" for now; future types possible
    params: Dict[str, Any] = field(default_factory=dict)
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    # Tail of captured stdout/stderr for the progress UI (last N lines).
    output_tail: str = ""
    error: Optional[str] = None            # populated on failure
    result: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "status": self.status,
            "kind": self.kind,
            "params": dict(self.params),
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "output_tail": self.output_tail,
            "error": self.error,
            "result": dict(self.result),
        }


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Registry ───────────────────────────────────────────────────────────────

# Default runner — the thing a worker actually invokes for a ``sim_run``.
# Signature: ``runner(params: dict) -> dict (result)``. Raises on failure.
# Production implementation calls ``rcm_mc.cli.run_main``; tests override.

def _default_sim_runner(params: Dict[str, Any]) -> Dict[str, Any]:
    """Run the real simulation via rcm_mc.cli.run_main with captured output.

    Reads standard run flags from ``params``:
      - ``actual``       (required) — path to actual.yaml
      - ``benchmark``    (required) — path to benchmark.yaml
      - ``outdir``       (required) — where to write results
      - ``n_sims``       (default 5000)
      - ``seed``         (default 42)

    Returns ``{"outdir": ..., "summary_csv": ...}``. Captured stdout/stderr
    is stored on the Job by the caller.
    """
    from rcm_mc import cli as _cli

    argv = [
        "--actual", str(params["actual"]),
        "--benchmark", str(params["benchmark"]),
        "--outdir", str(params["outdir"]),
        "--n-sims", str(params.get("n_sims", 5000)),
        "--seed", str(params.get("seed", 42)),
    ]
    if params.get("no_report"):
        argv.append("--no-report")
    if params.get("partner_brief"):
        argv.append("--partner-brief")
    # Prevent the portfolio auto-register from tripping over the separate
    # job DB — let the caller opt in per-run if they want.
    if not params.get("portfolio_register", True):
        argv.append("--no-portfolio")

    # Run; on error, re-raise so the worker can set status=failed
    _cli.run_main(argv)
    return {
        "outdir": str(params["outdir"]),
        "summary_csv": os.path.join(str(params["outdir"]), "summary.csv"),
    }


class JobRegistry:
    """Thread-safe in-memory job registry + single worker thread."""

    def __init__(
        self,
        *,
        runner: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
        output_tail_lines: int = 80,
    ) -> None:
        self._jobs: Dict[str, Job] = {}
        self._order: List[str] = []           # insertion order for list_recent
        self._lock = threading.Lock()
        self._queue: queue.Queue = queue.Queue()
        self._runner = runner or _default_sim_runner
        self._output_tail_lines = output_tail_lines
        self._worker_thread: Optional[threading.Thread] = None
        self._worker_started = threading.Event()
        self._shutdown = threading.Event()

    # ── Worker lifecycle ──

    def _ensure_worker(self) -> None:
        """Lazy-start the worker on first submit. Idempotent."""
        if self._worker_started.is_set():
            return
        with self._lock:
            if self._worker_started.is_set():
                return
            t = threading.Thread(
                target=self._worker_loop, daemon=True,
                name="rcm-job-worker",
            )
            t.start()
            self._worker_thread = t
            self._worker_started.set()

    def _worker_loop(self) -> None:
        while not self._shutdown.is_set():
            try:
                job_id = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue
            if job_id is None:
                break
            self._run_one(job_id)

    def _run_one(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.status = "running"
            job.started_at = _utcnow()

        # Capture stdout + stderr during the run so the progress UI has
        # something meaningful to display.
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                result = self._runner(job.params)
            with self._lock:
                job.status = "done"
                job.result = result or {}
        except BaseException as exc:  # noqa: BLE001
            # B149 fix: catch BaseException so KeyboardInterrupt /
            # SystemExit raised inside a runner don't leave the job
            # permanently in "running" state. We intentionally do not
            # re-raise here: one bad runner should not kill the shared
            # worker thread and strand every later queued job.
            with self._lock:
                job.status = "failed"
                job.error = (
                    f"{type(exc).__name__}: {exc}\n{traceback.format_exc(limit=8)}"
                )
        finally:
            tail = buf.getvalue().splitlines()[-self._output_tail_lines:]
            with self._lock:
                job.output_tail = "\n".join(tail)
                job.finished_at = _utcnow()

    def shutdown(self, timeout: float = 2.0) -> None:
        """Stop the worker thread. Pending jobs remain ``queued``."""
        self._shutdown.set()
        self._queue.put(None)  # wake the thread
        if self._worker_thread:
            self._worker_thread.join(timeout=timeout)

    # ── Public API ──

    def submit_run(
        self,
        *,
        actual: str, benchmark: str, outdir: str,
        n_sims: int = 5000, seed: int = 42,
        no_report: bool = False, partner_brief: bool = False,
        portfolio_register: bool = True,
    ) -> str:
        """Queue a simulation run. Returns the new ``job_id``."""
        self._ensure_worker()
        job_id = uuid.uuid4().hex[:12]
        params = {
            "actual": actual, "benchmark": benchmark, "outdir": outdir,
            "n_sims": int(n_sims), "seed": int(seed),
            "no_report": bool(no_report), "partner_brief": bool(partner_brief),
            "portfolio_register": bool(portfolio_register),
        }
        job = Job(
            job_id=job_id, status="queued", created_at=_utcnow(),
            kind="sim_run", params=params,
        )
        with self._lock:
            self._jobs[job_id] = job
            self._order.append(job_id)
        self._queue.put(job_id)
        return job_id

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)

    def list_recent(self, n: int = 20) -> List[Job]:
        """Newest-first slice of recent jobs."""
        with self._lock:
            ids = list(reversed(self._order))[:n]
            return [self._jobs[j] for j in ids if j in self._jobs]

    def wait(self, job_id: str, timeout: float = 5.0) -> Optional[Job]:
        """Block until the job reaches a terminal state, or timeout. Test helper."""
        deadline = threading.Event()
        import time as _time
        t0 = _time.monotonic()
        while _time.monotonic() - t0 < timeout:
            job = self.get(job_id)
            if job is None:
                return None
            if job.status in ("done", "failed"):
                return job
            _time.sleep(0.02)
        return self.get(job_id)


# ── Module-level singleton ───────────────────────────────────────────────

_DEFAULT_REGISTRY: Optional[JobRegistry] = None


def get_default_registry() -> JobRegistry:
    """Return a process-wide registry; lazy-init on first call."""
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is None:
        _DEFAULT_REGISTRY = JobRegistry()
    return _DEFAULT_REGISTRY


def reset_default_registry() -> None:
    """Test-only helper: drop the singleton so the next call starts fresh."""
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is not None:
        _DEFAULT_REGISTRY.shutdown(timeout=1.0)
    _DEFAULT_REGISTRY = None
