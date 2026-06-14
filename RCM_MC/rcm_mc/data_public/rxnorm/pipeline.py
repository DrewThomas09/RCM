"""Resumable, idempotent ingestion pipeline for the RxNorm slice.

Continuous-operation contract:
  * Maintains ``STATE.md`` (release version, last concept batch, last NDC
    resolved, cumulative row counts, last-run timestamp) with a machine-readable
    JSON block so a restart resumes instead of restarting.
  * Every pull is idempotent (upserts keyed by ``rxcui`` / ``ndc_11``), so
    resuming after a hard kill converges to the same state.
  * Never blocks on one step: a failing concept/endpoint is queued and retried
    at the end; the run continues past it.
  * Appends to ``PROGRESS.log`` so the run is auditable.

Offline by default: this environment cannot reach RxNav (network policy blocks
it), so the pipeline drives the connector with :func:`seed.seed_opener`. Pass
``live=True`` to use the real ``urllib`` opener where the environment permits.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from . import seed as seedmod
from . import store as st
from .connector import RxNormConnector
from .normalize import (ConceptRow, DrugClassRow, normalize_ndc,
                        NdcNormalizationError)

_STATE_DIR = Path(__file__).resolve().parent
_STATE_JSON_RE = re.compile(r"<!--STATE_JSON\s*(\{.*?\})\s*STATE_JSON-->", re.DOTALL)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── filesystem-as-memory ────────────────────────────────────────────────────

def load_state(state_dir: Path) -> Dict[str, Any]:
    """Parse the machine-readable JSON block out of STATE.md (or {} if absent)."""
    p = Path(state_dir) / "STATE.md"
    if not p.exists():
        return {}
    m = _STATE_JSON_RE.search(p.read_text(encoding="utf-8"))
    if not m:
        return {}
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return {}


def write_state(state_dir: Path, state: Dict[str, Any]) -> None:
    """Render STATE.md: human summary + an embedded JSON block for resume."""
    p = Path(state_dir) / "STATE.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    counts = state.get("counts", {})
    cov = state.get("class_coverage", {})
    lines = [
        "# RxNorm / RxNav connector — STATE",
        "",
        "Filesystem-as-memory checkpoint. The pipeline resumes from the JSON",
        "block at the bottom; re-running is idempotent (upserts keyed by rxcui",
        "/ ndc_11), so a hard kill loses no committed work.",
        "",
        f"- **RRF release / concept-source version:** {state.get('release_version', '—')}",
        f"- **Last run (UTC):** {state.get('last_run', '—')}",
        f"- **Last concept batch cursor:** {state.get('last_concept_cursor', '—')}",
        f"- **Last NDC resolved:** {state.get('last_ndc_resolved', '—')}",
        f"- **Concepts enriched:** {len(state.get('processed_rxcui', []))}",
        f"- **Open failures (requeued next run):** {len(state.get('failures', []))}",
        "",
        "## Cumulative row counts",
        "",
        f"- `xwalk_ndc_rxcui`: {counts.get('xwalk_ndc_rxcui', 0)}",
        f"- `dim_rxnorm_concept`: {counts.get('dim_rxnorm_concept', 0)}",
        f"- `bridge_rxcui_related`: {counts.get('bridge_rxcui_related', 0)}",
        f"- `dim_drug_class`: {counts.get('dim_drug_class', 0)}",
        f"- `dim_ndc_properties`: {counts.get('dim_ndc_properties', 0)}",
        "",
        "## Drug-class coverage",
        "",
        f"- Concepts: {cov.get('concepts', 0)}; classified rxcui: "
        f"{cov.get('classified_rxcui', 0)}; coverage: {cov.get('coverage_pct', 0)}%",
        f"- By class type: {cov.get('by_class_type', {})}",
        "",
        "<!--STATE_JSON",
        json.dumps(state, indent=2, sort_keys=True),
        "STATE_JSON-->",
        "",
    ]
    p.write_text("\n".join(lines), encoding="utf-8")


def append_progress(state_dir: Path, msg: str) -> None:
    p = Path(state_dir) / "PROGRESS.log"
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(f"{_utcnow()}\t{msg}\n")


# ── pipeline ────────────────────────────────────────────────────────────────

class RxnormPipeline:
    """Drive the connector → normalize → upsert, resumably and idempotently."""

    def __init__(
        self,
        store: Any,
        *,
        state_dir: Optional[Path] = None,
        opener: Optional[Callable] = None,
        live: bool = False,
        connector: Optional[RxNormConnector] = None,
    ) -> None:
        self.store = store
        self.state_dir = Path(state_dir) if state_dir else _STATE_DIR
        # Offline by default — RxNav is unreachable here. live=True uses urllib.
        self.opener = opener if opener is not None else (
            None if live else seedmod.seed_opener)
        self.live = live
        self.connector = connector or RxNormConnector()

    # one isolated, never-blocking unit of work
    def _safe(self, state: Dict[str, Any], label: str, fn: Callable) -> Any:
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 — never block the pipeline
            state.setdefault("failures", []).append(
                {"label": label, "error": f"{type(exc).__name__}: {exc}"})
            append_progress(self.state_dir, f"FAIL {label}: {exc}")
            return None

    def _fetch(self, endpoint: str, params: Dict[str, str], cursor: str = ""):
        return self.connector.fetch(endpoint, params, cursor, opener=self.opener)

    def run(self, *, enrich_ndc_properties: bool = True) -> Dict[str, Any]:
        """Run a full (resumable) ingestion pass. Returns a report dict."""
        self.store.init_db()
        state = load_state(self.state_dir)
        state["release_version"] = seedmod.RELEASE_VERSION if not self.live else \
            state.get("release_version", "live")
        processed = set(state.get("processed_rxcui", []))
        state["failures"] = []  # fresh failure queue; requeue happens via retry
        append_progress(self.state_dir, f"RUN start (live={self.live})")

        # ── Stage 1: concept universe (paginated) ───────────────────────
        cursor = ""
        all_rxcui: List[str] = []
        while True:
            page, cursor = self._fetch(
                "allconcepts", dict(self.connector.discover()[0]["default_params"]),
                cursor)
            self._safe(state, "upsert_concepts", lambda p=page: st.upsert_concepts(
                self.store, [ConceptRow(rxcui=r["rxcui"], name=r["name"],
                                        tty=r["tty"]) for r in p]))
            all_rxcui.extend(r["rxcui"] for r in page)
            state["last_concept_cursor"] = cursor or "complete"
            if not cursor:
                break

        # ── Stage 2: per-concept enrichment (status, ndcs, related, class) ─
        for rxcui in all_rxcui:
            if rxcui in processed:
                continue
            self._enrich_concept(state, rxcui, enrich_ndc_properties)
            processed.add(rxcui)
            state["processed_rxcui"] = sorted(processed)

        # ── Retry the failure queue once, at the end ─────────────────────
        failures = list(state.get("failures", []))
        if failures:
            append_progress(self.state_dir, f"RETRY {len(failures)} failures")
            state["failures"] = []
            # Re-enrich each distinct concept that had a concept-scoped failure;
            # idempotent upserts make a retry safe even if the first pass
            # partially succeeded.
            retry_rxcui = set()
            for f in failures:
                token = f.get("label", "").split(":")[-1].strip()
                if token in set(all_rxcui):
                    retry_rxcui.add(token)
            for rxcui in sorted(retry_rxcui):
                self._enrich_concept(state, rxcui, enrich_ndc_properties)

        # ── Finalize state ───────────────────────────────────────────────
        state["counts"] = st.counts(self.store)
        state["class_coverage"] = st.class_coverage(self.store)
        state["last_run"] = _utcnow()
        write_state(self.state_dir, state)
        append_progress(self.state_dir,
                        f"RUN done counts={state['counts']} "
                        f"failures={len(state.get('failures', []))}")
        return {
            "release_version": state["release_version"],
            "counts": state["counts"],
            "class_coverage": state["class_coverage"],
            "failures": state.get("failures", []),
            "concepts_processed": len(processed),
        }

    def _enrich_concept(self, state: Dict[str, Any], rxcui: str,
                        enrich_ndc_properties: bool) -> None:
        # status + remap (authoritative source for retired/remapped handling)
        def _status():
            rows, _ = self._fetch("historystatus", {"rxcui": rxcui})
            if rows:
                r = rows[0]
                c = seedmod.SEED_CONCEPTS.get(rxcui, {})
                st.upsert_concepts(self.store, [ConceptRow(
                    rxcui=rxcui, name=c.get("name", ""), tty=c.get("tty", ""),
                    status=r["status"], remapped_to_rxcui=r["remapped_to_rxcui"])])
        self._safe(state, f"historystatus:{rxcui}", _status)

        # NDC crosswalk — normalize every NDC to canonical 11-digit form.
        def _ndcs():
            rows, _ = self._fetch("ndcs", {"rxcui": rxcui})
            xw: List[Dict[str, str]] = []
            status = _concept_status(self.store, rxcui)
            for r in rows:
                raw = r["ndc_raw"]
                try:
                    ndc_11 = normalize_ndc(raw)
                except NdcNormalizationError:
                    state.setdefault("failures", []).append(
                        {"label": f"ndc_norm:{rxcui}", "error": f"bad NDC {raw!r}"})
                    continue
                xw.append({"ndc_11": ndc_11, "ndc_raw": raw,
                           "rxcui": rxcui, "status": status})
                state["last_ndc_resolved"] = ndc_11
            if xw:
                st.upsert_crosswalk(self.store, xw)
                if enrich_ndc_properties:
                    self._enrich_ndc_props(state, xw)
        self._safe(state, f"ndcs:{rxcui}", _ndcs)

        # relationships
        def _related():
            rows, _ = self._fetch("allrelated", {"rxcui": rxcui})
            triples = [(r["related_rxcui"], r["tty"], r["relationship"])
                       for r in rows]
            if triples:
                st.upsert_related(self.store, rxcui, triples)
        self._safe(state, f"allrelated:{rxcui}", _related)

        # drug classes
        def _classes():
            rows, _ = self._fetch("rxclass", {"rxcui": rxcui})
            cls = [DrugClassRow(rxcui=r["rxcui"], class_id=r["class_id"],
                                class_name=r["class_name"],
                                class_type=r["class_type"]) for r in rows]
            if cls:
                st.upsert_drug_classes(self.store, cls)
        self._safe(state, f"rxclass:{rxcui}", _classes)

    def _enrich_ndc_props(self, state: Dict[str, Any],
                          xw: List[Dict[str, str]]) -> None:
        def _props():
            out: List[Dict[str, str]] = []
            for row in xw:
                rows, _ = self._fetch("ndcproperties", {"id": row["ndc_raw"]})
                for r in rows:
                    try:
                        ndc_11 = normalize_ndc(r.get("ndc_raw") or row["ndc_raw"])
                    except NdcNormalizationError:
                        continue
                    out.append({"ndc_11": ndc_11, "ndc_raw": r.get("ndc_raw", ""),
                                "rxcui": r.get("rxcui", row["rxcui"]),
                                "labeler": r.get("labeler", ""),
                                "packaging": r.get("packaging", ""),
                                "status": r.get("status", "")})
            if out:
                st.upsert_ndc_properties(self.store, out)
        self._safe(state, "ndcproperties", _props)


def _concept_status(store: Any, rxcui: str) -> str:
    # The crosswalk row records the concept's own status so a stale/retired
    # NDC inherits the remap state and joins can resolve through it.
    with store.connect() as con:
        st.ensure_tables(con)
        row = con.execute("SELECT status FROM dim_rxnorm_concept WHERE rxcui=?",
                          (rxcui,)).fetchone()
    return row["status"] if row else "active"


def seed_into(store: Any) -> Dict[str, Any]:
    """Populate the given store from the offline seed without touching the
    committed package STATE.md/PROGRESS.log — used by the UI 'populate' action,
    which writes its checkpoint to a throwaway temp dir.
    """
    import tempfile
    return RxnormPipeline(store, state_dir=Path(tempfile.mkdtemp())).run()


def run(store: Any, **kwargs: Any) -> Dict[str, Any]:
    """Module-level convenience: ``RxnormPipeline(store, **kw).run()``."""
    pipe_kwargs = {k: kwargs.pop(k) for k in
                   ("state_dir", "opener", "live", "connector") if k in kwargs}
    return RxnormPipeline(store, **pipe_kwargs).run(**kwargs)


if __name__ == "__main__":  # pragma: no cover - manual / cron entry
    import argparse
    import sys
    from ...portfolio.store import PortfolioStore

    ap = argparse.ArgumentParser(description="Ingest the RxNorm slice.")
    ap.add_argument("--db", required=True, help="SQLite DB path")
    ap.add_argument("--live", action="store_true",
                    help="Use the live RxNav API (default: offline seed)")
    ap.add_argument("--state-dir", default=None)
    args = ap.parse_args()
    report = run(PortfolioStore(args.db), live=args.live,
                 state_dir=Path(args.state_dir) if args.state_dir else None)
    json.dump(report, sys.stdout, indent=2)
    sys.stdout.write("\n")
