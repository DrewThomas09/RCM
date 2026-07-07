"""Deep recovery — the full v49 networked ``run_pipeline`` as a background job.

This is the complete Steps 0–8 pipeline: live NPPES enrichment, CMS biller /
Open Payments / 340B pulls, entity resolution, statistical fill/imputation,
calibrated capture, and the multi-tab Excel report. It is fundamentally a
**networked batch job** — ``candidates.build_candidate_pools`` warms the CMS
data catalog over HTTP regardless of which sub-steps are enabled — so:

  * it needs ``requests`` (not a base RCM dependency) and outbound access to
    data.cms.gov / npiregistry.cms.hhs.gov;
  * it can run for minutes;
  * in an environment without outbound access it would otherwise hang on
    urllib3 retry-backoff.

So this runs opt-in, in the background job thread, under a **wall-clock
timeout watchdog**: if the pipeline does not finish in time the job is failed
with a clear message (the abandoned worker is a daemon thread and cannot block
the server) rather than hanging the UI. Everything is guarded — a missing
``requests``, a blocked network, or any pipeline error returns a structured
error and the fast deterministic results still stand.
"""
from __future__ import annotations

import threading
import uuid
from pathlib import Path
from typing import Callable, Dict, Optional

WORKDIR = Path("/tmp/npi_cleaner_web")
WORKDIR.mkdir(parents=True, exist_ok=True)

# Default wall-clock ceiling for a web-initiated deep run. Generous enough for
# a real networked pass on a modest file, tight enough that a blocked network
# fails the job in minutes instead of never.
DEFAULT_TIMEOUT_S = 420

# Preflight TCP-connect budget. On a no-egress box the old behavior held the
# job's back-half progress bar for the full 7-minute watchdog before the
# honest timeout message; a bounded connect answers the same question in
# seconds.
_PREFLIGHT_TIMEOUT_S = 4.0


def _default_probe(timeout: float = _PREFLIGHT_TIMEOUT_S) -> bool:
    """Can this box plausibly reach data.cms.gov? Delegates to the bounded
    TCP preflight in the connectors estate (``connectors.net_preflight``) —
    the codebase's home for network-touching code — so this offline cleaner
    package itself imports no network modules. When that helper is not
    importable (or itself misbehaves) the probe answers optimistically and
    the wall-clock watchdog remains the only guard, exactly the
    pre-preflight behavior. Never raises."""
    try:
        from connectors.net_preflight import can_reach_cms
    except Exception:  # noqa: BLE001 — no preflight helper: watchdog guards
        return True
    try:
        return bool(can_reach_cms(timeout=timeout))
    except Exception:  # noqa: BLE001 — a broken probe must not block a run
        return True


def available() -> bool:
    """True when requests + the vendored pipeline import (i.e. deep mode can
    at least be attempted). Does not prove outbound access exists."""
    try:
        import requests  # noqa: F401
        from .vendor_v49.npi_recovery import pipeline  # noqa: F401
        from .vendor_v49.npi_recovery import report  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False


def run(
    data: bytes, src_name: str, *,
    timeout_s: int = DEFAULT_TIMEOUT_S,
    progress: Optional[Callable[[str, float], None]] = None,
    probe: Optional[Callable[[], bool]] = None,
) -> Dict[str, object]:
    """Run the full pipeline with a timeout. Returns a structured dict:

        {"ok": bool, "error": str|None, "stats": {...},
         "workbook_path": str|None, "workbook_name": str}

    ``probe`` (injectable for tests) is a fast reachability check run
    BEFORE the worker spawns; when it returns False the run fails in
    seconds with the honest no-egress message instead of burning the full
    watchdog. The watchdog still guards the slow-but-reachable case.

    Never raises.
    """
    def cb(msg: str, frac: float) -> None:
        if progress:
            # Deep run occupies the back half of the job's progress bar.
            progress(f"Deep recovery — {msg}", 0.5 + 0.5 * float(frac))

    out: Dict[str, object] = {
        "ok": False, "error": None, "stats": {},
        "workbook_path": None,
        "workbook_name": (Path(src_name).stem.replace(" ", "_") or "claims")
        + "_recovered.xlsx",
    }

    try:
        import requests  # noqa: F401
        from .vendor_v49.npi_recovery import pipeline as P
        from .vendor_v49.npi_recovery import report as R
    except Exception:  # noqa: BLE001
        out["error"] = ("Deep recovery needs the 'requests' package and the "
                        "v49 pipeline. Install requests to enable it.")
        return out

    # Fast no-egress preflight — fail in seconds, not after the watchdog.
    try:
        reachable = (probe or _default_probe)()
    except Exception:  # noqa: BLE001 — a broken probe must not block a run
        reachable = True
    if not reachable:
        out["error"] = (
            "Deep recovery preflight could not reach data.cms.gov — this "
            "environment may not allow outbound access. The deterministic "
            "results above are unaffected.")
        cb("preflight failed — no outbound access", 1.0)
        return out

    # Persist the upload to a file the pipeline can read (it takes a path).
    suffix = ".xlsx" if data[:4] == b"PK\x03\x04" else ".csv"
    src_path = WORKDIR / f"deep_{uuid.uuid4().hex}{suffix}"
    src_path.write_bytes(data)

    box: Dict[str, object] = {}

    def _work() -> None:
        try:
            cb("starting (warming CMS catalog)…", 0.0)
            # Bounded caps so a web run stays minutes, not hours. Network
            # sub-steps stay on — deep mode is explicitly the online path.
            res = P.run_pipeline(
                str(src_path), progress=cb,
                enrich_max_npis=300, connector_max_npis=300,
                connector_max_drugs=100, fill_max_npis=20000,
            )
            box["res"] = res
        except Exception as exc:  # noqa: BLE001
            box["err"] = exc

    th = threading.Thread(target=_work, daemon=True)
    th.start()
    th.join(timeout_s)

    if th.is_alive():
        out["error"] = (
            f"Deep recovery timed out after {timeout_s}s — this environment "
            "may not allow outbound access to data.cms.gov / NPPES. The "
            "deterministic results above are unaffected.")
        return out
    if "err" in box:
        exc = box["err"]
        out["error"] = f"Deep recovery failed: {type(exc).__name__}: {exc}"
        return out

    res = box.get("res")
    if res is None:
        out["error"] = "Deep recovery returned no result."
        return out

    try:
        wb_path = WORKDIR / f"deep_{uuid.uuid4().hex}_{out['workbook_name']}"
        R.write_report(res, str(wb_path))
        out["workbook_path"] = str(wb_path)
    except Exception as exc:  # noqa: BLE001
        out["error"] = f"Deep recovery ran but the report failed: {exc}"

    out["stats"] = dict(getattr(res, "stats", {}) or {})
    out["ok"] = out["error"] is None
    cb("done", 1.0)
    return out
