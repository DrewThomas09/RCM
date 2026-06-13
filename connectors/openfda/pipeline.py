"""Pipeline orchestrator: backfill + nightly incremental, resumable.

Drives the connector for each endpoint: resume from STATE.md → ``fetch``
a step → land raw → normalize → upsert canonical rows → persist STATE →
append to PROGRESS.md, looping until the endpoint's cursor is exhausted.
Then resolve the crosswalk (NDC→RxCUI, deferred when no RxNorm), rebuild
the device product_code dimension, and persist the company rollup.

Operating rules from the brief, all enforced here:
  * **Never block on one endpoint.** Each endpoint runs in its own
    try/except; a failure marks it ``failed`` and we move on, retrying
    the failures once at the end.
  * **Idempotent + resumable.** Every step persists the cursor; a hard
    kill resumes from STATE.md. Upserts make replays safe.
  * **Backfill vs incremental.** Backfill walks history from
    ``backfill_start``; incremental only re-pulls a recent date window
    for nightly-cadence endpoints (dimensions refresh on their cadence).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from .connector import OpenFdaConnector, FetchResult
from .crosswalk import (RxcuiResolver, persist_companies,
                        rebuild_device_product_code, resolve_ndc_rxcui)
from .endpoints import ENDPOINTS, EndpointSpec
from .normalize import normalize
from .raw_store import RawStore
from .state import EndpointState, StateStore
from .tables import OpenFdaStore
from .transport import Opener

# Hard ceiling on steps per endpoint per run so a pathological cursor can't
# spin forever; a real backfill resumes across runs via STATE.md anyway.
_MAX_STEPS_PER_ENDPOINT = 100_000


@dataclass
class PipelineConfig:
    mode: str = "backfill"          # "backfill" | "incremental"
    incremental_lookback_days: int = 7
    backfill_start: str = "20040101"
    max_steps_per_endpoint: int = _MAX_STEPS_PER_ENDPOINT


class OpenFdaPipeline:
    def __init__(
        self,
        store: OpenFdaStore,
        state: StateStore,
        raw: RawStore,
        connector: Optional[OpenFdaConnector] = None,
        *,
        config: Optional[PipelineConfig] = None,
        rxcui_resolver: Optional[RxcuiResolver] = None,
    ) -> None:
        self.store = store
        self.state_store = state
        self.raw = raw
        self.config = config or PipelineConfig()
        self.connector = connector or OpenFdaConnector(
            backfill_start=self.config.backfill_start)
        self.rxcui_resolver = rxcui_resolver
        self._all_ndcs: set = set()
        self._companies: Dict[str, Dict[str, Any]] = {}

    # ── public entrypoint ─────────────────────────────────────────────
    def run(
        self,
        endpoints: Optional[List[str]] = None,
        *,
        opener: Optional[Opener] = None,
    ) -> Dict[str, EndpointState]:
        """Run the selected endpoints, then finalize the crosswalk."""
        states = self.state_store.load()
        # Incremental runs only re-pull a recent date window.
        if self.config.mode == "incremental":
            start = (datetime.now(timezone.utc).date()
                     - timedelta(days=self.config.incremental_lookback_days))
            self.connector.backfill_start = start.strftime("%Y%m%d")
        selected = self._select_endpoints(endpoints)
        failed: List[str] = []

        for spec in selected:
            st = states.get(spec.key) or EndpointState(endpoint=spec.key)
            states[spec.key] = st
            try:
                self._run_endpoint(spec, st, opener)
            except Exception as exc:  # never block on one endpoint
                st.status = "failed"
                st.last_error = f"{type(exc).__name__}: {exc}"
                st.touch()
                self.state_store.save(states)
                self.state_store.log(f"[{spec.key}] FAILED: {st.last_error}")
                failed.append(spec.key)

        # Retry the failures once, at the end.
        for key in failed:
            spec = ENDPOINTS[key]
            st = states[key]
            try:
                self.state_store.log(f"[{key}] retrying after end-of-run")
                self._run_endpoint(spec, st, opener)
            except Exception as exc:
                st.status = "failed"
                st.last_error = f"retry: {type(exc).__name__}: {exc}"
                st.touch()
                self.state_store.log(f"[{key}] retry FAILED: {st.last_error}")

        self.state_store.save(states)
        self._finalize()
        return states

    # ── one endpoint, stepwise + resumable ────────────────────────────
    def _run_endpoint(self, spec: EndpointSpec, st: EndpointState,
                      opener: Optional[Opener]) -> None:
        params = self._params_for(spec)
        cursor = st.cursor if st.status != "complete" else None
        if st.status == "complete" and self.config.mode == "incremental":
            cursor = None  # re-seed a fresh incremental window
        st.status = "in_progress"
        steps = 0
        prev_cursor_repr = object()
        while True:
            result: FetchResult = self.connector.fetch(
                spec, params, cursor, opener=opener)
            self._absorb(spec, result, st)
            st.cursor = result.next_cursor
            st.touch()
            self._save_one(st)
            steps += 1

            if result.next_cursor is None:
                st.status = "complete"
                self._save_one(st)
                self.state_store.log(
                    f"[{spec.key}] complete — {st.rows_ingested} rows, "
                    f"{st.requests_made} requests")
                break
            # Guard against a non-advancing cursor (would loop forever).
            cur_repr = repr(result.next_cursor)
            if cur_repr == prev_cursor_repr:
                self.state_store.decide(
                    f"{spec.key}: non-advancing cursor",
                    "Cursor repeated between steps; stopping this endpoint to "
                    "avoid an infinite loop. Investigate the window/skip math "
                    f"for this endpoint. Cursor: {cur_repr}")
                st.status = "failed"
                st.last_error = "non-advancing cursor"
                self._save_one(st)
                break
            prev_cursor_repr = cur_repr
            cursor = result.next_cursor
            if steps >= self.config.max_steps_per_endpoint:
                self.state_store.log(
                    f"[{spec.key}] hit max steps ({steps}); will resume next run")
                break

    def _absorb(self, spec: EndpointSpec, result: FetchResult,
                st: EndpointState) -> None:
        """Land raw, normalize, upsert; update counters + audit."""
        tag = self._window_tag(result)
        self.raw.write(spec.key, tag, result.rows)
        st.raw_rows_seen += len(result.rows)
        st.requests_made = self.connector.transport.requests_made
        st.last_window = (f"{result.window[0]}..{result.window[1]}"
                          if result.window else tag)

        norm = normalize(spec, result.rows)
        written = 0
        for table, rows in norm.rows.items():
            written += self.store.upsert(table, rows)
        st.rows_ingested += written
        self._all_ndcs.update(norm.ndcs)
        for k, c in norm.companies.items():
            entry = self._companies.setdefault(k, {**c, "raw_names": set()})
            entry["raw_names"].update(
                c.get("raw_names") if isinstance(c.get("raw_names"), set) else [])
            entry.setdefault("normalized_name", c.get("normalized_name"))
            entry.setdefault("kind", c.get("kind"))

        if result.truncated:
            self.state_store.decide(
                f"{spec.key}: window truncated at skip cap",
                "A single-day (or single-partition) window exceeded openFDA's "
                "~25k skip ceiling, so rows beyond the cap were not pulled for "
                "this slice. Recorded so the gap is visible; revisit with a "
                "finer partition key if the count reconciliation flags it.")
        if norm.unmapped:
            top = ", ".join(f"{k}({v})" for k, v in
                            sorted(norm.unmapped.items(), key=lambda x: -x[1])[:12])
            self.state_store.decide(
                f"{spec.key}: unmapped fields",
                "Fields present on raw records but not placed by the "
                f"normalizer (count): {top}. Left in the raw lake; map later "
                "if a downstream surface needs them.")

    # ── crosswalk finalize ────────────────────────────────────────────
    def _finalize(self) -> None:
        stats = resolve_ndc_rxcui(self.store, self._all_ndcs,
                                  resolver=self.rxcui_resolver)
        if stats["resolved"] == 0 and stats["total"] > 0:
            self.state_store.decide(
                "NDC→RxCUI deferred (no RxNorm session)",
                f"{stats['total']} NDCs ingested; RxCUI left NULL with status "
                "'deferred_no_rxnorm'. The xwalk_ndc_rxcui rows + the "
                "dim_drug_product.rxcui column exist and are wireable — a "
                "later RxNorm session back-fills them without re-ingesting.")
        pcodes = rebuild_device_product_code(self.store)
        companies = persist_companies(self.store, self._companies)
        self.state_store.log(
            f"finalize — ndc_rxcui {stats}, product_codes {pcodes}, "
            f"companies {companies}")

    # ── helpers ───────────────────────────────────────────────────────
    def _select_endpoints(self, endpoints: Optional[List[str]]) -> List[EndpointSpec]:
        if endpoints:
            return [ENDPOINTS[e] for e in endpoints]
        if self.config.mode == "incremental":
            return [s for s in ENDPOINTS.values() if s.refresh_cadence == "nightly"]
        return list(ENDPOINTS.values())

    def _params_for(self, spec: EndpointSpec) -> Dict[str, Any]:
        params = dict(spec.default_params)
        return params

    def _window_tag(self, result: FetchResult) -> str:
        if result.window:
            return f"{result.window[0]}_{result.window[1]}"
        return "batch"

    def _save_one(self, st: EndpointState) -> None:
        states = self.state_store.load()
        states[st.endpoint] = st
        self.state_store.save(states)
