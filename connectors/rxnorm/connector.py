"""The RxNorm connector: ``discover()`` + ``fetch()``.

Every dataset here is **roster-driven** — RxNav resolves one identifier
per request, so a pull is driven by a caller-supplied list (``ndcs`` /
``names`` / ``rxcuis``), exactly like the NPI Registry and QPP
eligibility connectors. The natural roster is a distinct-NDC or
distinct-drug-name query against the NADAC / SDUD / Part D tables this
estate already ingests.

``fetch`` is a single *step* of that state machine: it drains up to
``MAX_IDS_PER_STEP`` identifiers, returns those resolved records plus a
``next_cursor`` describing where in the roster to resume, and ``None``
when the roster is exhausted. Every cursor is JSON-serialisable so a run
can persist it and resume exactly where it stopped.

An identifier RxNav cannot resolve is recorded in ``unresolved`` and
skipped — never an error, so one junk NDC can't abort a 10k-row sweep.

The resolve sequence per identifier (all verified envelope keys):

  NDC   → ``/rxcui.json?idtype=NDC&id=`` → ``idGroup.rxnormId[0]``
  name  → ``/rxcui.json?name=&search=2`` → ``idGroup.rxnormId[0]``,
          falling back to ``/approximateTerm.json?term=&maxEntries=1``
          → ``approximateGroup.candidate[0].rxcui`` (flagged
          ``match_type='approximate'`` so a fuzzy join is visible)
  then enrich the RxCUI:
          ``/rxcui/{rxcui}/properties.json`` → ``properties``
          ``/rxcui/{rxcui}/related.json?tty=IN``
              → ``relatedGroup.conceptGroup[].conceptProperties[].name``
          ``/rxclass/class/byRxcui.json?rxcui=&relaSource=ATC``
              → ``rxclassDrugInfoList.rxclassDrugInfo[]
                  .rxclassMinConceptItem.className``
          with a ``relaSource=DAILYMED`` fallback when a concept carries
          no ATC class (common for biologics — precisely the high-cost
          Part B injectables an analysis cares about).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

from .endpoints import (
    APPROXIMATE_PATH, CLASS_PATH, CLASS_SOURCES, ENDPOINTS, EndpointSpec,
    PROPERTIES_PATH_TEMPLATE, RELATED_PATH_TEMPLATE,
)
from .transport import Opener, RxNavTransport

MAX_IDS_PER_STEP = 25          # bound the work (and rows) one fetch() returns
MIN_NDC_DIGITS = 9             # shorter strings are not resolvable NDCs


@dataclass
class FetchResult:
    """One ``fetch`` step's output."""

    rows: List[Dict[str, Any]]
    next_cursor: Optional[Dict[str, Any]]
    endpoint: str
    unresolved: List[str] = field(default_factory=list)
    requests: int = 0

    @property
    def done(self) -> bool:
        return self.next_cursor is None


class RxNormConnector:
    """Stateless-per-call connector over an injected transport.

    All network I/O flows through ``self.transport``; pass ``opener`` on
    each call (or via the transport) so tests drive the full state
    machine with a fake server.
    """

    def __init__(self, transport: Optional[RxNavTransport] = None, *,
                 max_ids_per_step: int = MAX_IDS_PER_STEP) -> None:
        self.transport = transport or RxNavTransport.from_env()
        self.max_ids_per_step = max_ids_per_step
        self._requests = 0

    # ── discovery ─────────────────────────────────────────────────────
    def discover(self) -> List[EndpointSpec]:
        """Enumerate the endpoints this connector ingests."""
        return list(ENDPOINTS.values())

    # ── the fetch state machine ───────────────────────────────────────
    def fetch(
        self,
        endpoint: EndpointSpec,
        params: Optional[Dict[str, Any]] = None,
        cursor: Optional[Dict[str, Any]] = None,
        *,
        opener: Optional[Opener] = None,
    ) -> FetchResult:
        """Advance one step; ``next_cursor=None`` when the roster is done."""
        params = dict(params or {})
        roster = self._roster(endpoint, params)
        if not roster:
            raise ValueError(
                f"{endpoint.dataset_id} needs params[{endpoint.roster_param!r}] "
                f"(list or comma-joined string) — RxNav resolves one "
                f"identifier per request")
        idx = int((cursor or {}).get("idx", 0))
        stop = min(len(roster), idx + self.max_ids_per_step)
        self._requests = 0
        rows: List[Dict[str, Any]] = []
        unresolved: List[str] = []
        for i in range(idx, stop):
            ident = roster[i]
            row = self._resolve(endpoint, ident, opener)
            if row is None:
                unresolved.append(ident)
                continue
            rows.append(row)
        nxt = {"idx": stop} if stop < len(roster) else None
        return FetchResult(rows, nxt, endpoint.key, unresolved=unresolved,
                           requests=self._requests)

    # ── per-identifier resolve ────────────────────────────────────────
    def _resolve(self, spec: EndpointSpec, ident: str,
                 opener: Optional[Opener]) -> Optional[Dict[str, Any]]:
        if spec.kind == "ndc":
            return self._resolve_ndc(spec, ident, opener)
        if spec.kind == "name":
            return self._resolve_name(spec, ident, opener)
        return self._resolve_concept(spec, ident, opener)

    def _resolve_ndc(self, spec: EndpointSpec, ndc: str,
                     opener: Optional[Opener]) -> Optional[Dict[str, Any]]:
        digits = "".join(ch for ch in str(ndc) if ch.isdigit())
        if len(digits) < MIN_NDC_DIGITS:
            return None
        doc = self._get(spec.path, {"idtype": "NDC", "id": digits}, opener)
        rxcui = _first_rxnorm_id(doc)
        if not rxcui:
            return None
        return {"kind": "ndc", "ndc": str(ndc), "ndc_digits": digits,
                "rxcui": rxcui, "concept": self._enrich(rxcui, opener)}

    def _resolve_name(self, spec: EndpointSpec, name: str,
                      opener: Optional[Opener]) -> Optional[Dict[str, Any]]:
        query = str(name).strip()
        if len(query) < 3:
            return None
        doc = self._get(spec.path, {"name": query, "search": "2"}, opener)
        rxcui = _first_rxnorm_id(doc)
        match_type = "exact"
        if not rxcui:
            # Approximate match is the documented last resort; flagging it
            # keeps a fuzzy join distinguishable from a confident one.
            adoc = self._get(APPROXIMATE_PATH,
                             {"term": query, "maxEntries": 1}, opener)
            cands = _dig(adoc, "approximateGroup", "candidate") or []
            rxcui = (cands[0].get("rxcui")
                     if cands and isinstance(cands[0], dict) else None)
            match_type = "approximate"
        if not rxcui:
            return None
        return {"kind": "name", "query_name": query, "rxcui": str(rxcui),
                "matched_on": query, "match_type": match_type,
                "concept": self._enrich(str(rxcui), opener)}

    def _resolve_concept(self, spec: EndpointSpec, rxcui: str,
                         opener: Optional[Opener]) -> Optional[Dict[str, Any]]:
        rx = str(rxcui).strip()
        if not rx:
            return None
        concept = self._enrich(rx, opener)
        if not concept.get("name"):
            return None
        return {"kind": "concept", "rxcui": rx, "concept": concept}

    # ── concept enrichment ────────────────────────────────────────────
    def _enrich(self, rxcui: str, opener: Optional[Opener]) -> Dict[str, Any]:
        """RxCUI → ``{name, tty, synonym, ingredients, classes, source}``."""
        props = _dig(self._get(PROPERTIES_PATH_TEMPLATE.format(rxcui=rxcui),
                               None, opener), "properties") or {}
        related = self._get(RELATED_PATH_TEMPLATE.format(rxcui=rxcui),
                            {"tty": "IN"}, opener)
        ingredients = _concept_names(related)
        classes: List[str] = []
        class_source = ""
        for source in CLASS_SOURCES:
            doc = self._get(CLASS_PATH, {"rxcui": rxcui, "relaSource": source},
                            opener)
            classes = _class_names(doc)
            if classes:
                class_source = source
                break
        return {
            "rxcui": rxcui,
            "name": props.get("name") or "",
            "tty": props.get("tty") or "",
            "synonym": props.get("synonym") or "",
            "ingredients": ingredients,
            "classes": classes,
            "class_source": class_source,
            "properties": props,
        }

    def _get(self, path: str, params: Optional[Dict[str, Any]],
             opener: Optional[Opener]) -> Dict[str, Any]:
        self._requests += 1
        return self.transport.get_json(path, params, opener=opener) or {}

    # ── roster helper ─────────────────────────────────────────────────
    @staticmethod
    def _roster(spec: EndpointSpec, params: Dict[str, Any]) -> List[str]:
        raw = params.get(spec.roster_param)
        if raw is None:
            # Accept the singular form too — a one-identifier probe is the
            # most common interactive call.
            raw = params.get(spec.roster_param.rstrip("s")) or ""
        if isinstance(raw, (list, tuple)):
            vals = [str(v) for v in raw]
        else:
            vals = str(raw).split(",")
        return [v.strip() for v in vals if v.strip()]


# ── defensive payload digging ─────────────────────────────────────────
def _dig(doc: Any, *keys: str) -> Any:
    """Walk nested dict keys, returning ``None`` the moment one is absent.

    RxNav answers an unresolvable identifier with HTTP 200 and an
    envelope missing its payload key, so every access has to tolerate a
    hole rather than raise.
    """
    cur = doc
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur


def _first_rxnorm_id(doc: Any) -> str:
    """``idGroup.rxnormId[0]`` when present, else ``''``."""
    ids = _dig(doc, "idGroup", "rxnormId")
    if isinstance(ids, list) and ids:
        return str(ids[0])
    return ""


def _concept_names(doc: Any) -> List[str]:
    """Ordered, de-duplicated ``conceptProperties[].name`` from a related doc."""
    out: List[str] = []
    groups = _dig(doc, "relatedGroup", "conceptGroup") or []
    if not isinstance(groups, list):
        return out
    for grp in groups:
        if not isinstance(grp, dict):
            continue
        for c in grp.get("conceptProperties") or []:
            if isinstance(c, dict) and c.get("name"):
                out.append(str(c["name"]))
    return list(dict.fromkeys(out))


def _class_names(doc: Any) -> List[str]:
    """Ordered, de-duplicated class names from an ``rxclass`` doc."""
    out: List[str] = []
    infos = _dig(doc, "rxclassDrugInfoList", "rxclassDrugInfo") or []
    if not isinstance(infos, list):
        return out
    for ci in infos:
        if not isinstance(ci, dict):
            continue
        nm = _dig(ci, "rxclassMinConceptItem", "className")
        if nm:
            out.append(str(nm))
    return list(dict.fromkeys(out))


def parse_helpers() -> Tuple[Any, ...]:  # pragma: no cover - test convenience
    """The payload diggers, exposed for unit tests."""
    return (_dig, _first_rxnorm_id, _concept_names, _class_names)
