"""In-memory fake RxNav server — no socket, deterministic.

A :class:`FakeRxNav` is an :data:`Opener` (``(url, headers, timeout) ->
RawResponse``) that serves canned RxNorm payloads under the **real
envelope keys** RxNav uses (``idGroup`` / ``properties`` /
``relatedGroup`` / ``rxclassDrugInfoList`` / ``approximateGroup``), for
the exact routes the connector emits. It also models RxNav's
empty-result behaviour — HTTP 200 with the payload key simply absent,
not a 404 — plus 429 + ``Retry-After`` and 5xx so the transport's retry
path is exercised without a network.

Envelope shapes are the ones this repo's production RxNav client
(``rcm_mc/npi_cleaner/vendor_v49/npi_recovery/clients.py``) already
resolves against, so the fake mirrors verified reality rather than a
guess.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List
from urllib.parse import parse_qs, urlparse

from ..transport import RawResponse


class FakeRxNav:
    def __init__(self) -> None:
        self.ndc_to_rxcui: Dict[str, str] = {}
        self.name_to_rxcui: Dict[str, str] = {}
        self.approx_to_rxcui: Dict[str, str] = {}
        # rxcui -> {"properties": {...}, "ingredients": [...],
        #           "classes": {"ATC": [...], "DAILYMED": [...]}}
        self.concepts: Dict[str, Dict[str, Any]] = {}
        self.calls: List[str] = []
        # Scripted transient responses keyed by call index: {idx: (status, headers)}.
        self.transients: Dict[int, Any] = {}

    # ── seeding helpers ───────────────────────────────────────────────
    def add_ndc(self, ndc: str, rxcui: str) -> "FakeRxNav":
        self.ndc_to_rxcui["".join(c for c in ndc if c.isdigit())] = str(rxcui)
        return self

    def add_name(self, name: str, rxcui: str) -> "FakeRxNav":
        self.name_to_rxcui[name.lower()] = str(rxcui)
        return self

    def add_approximate(self, term: str, rxcui: str) -> "FakeRxNav":
        self.approx_to_rxcui[term.lower()] = str(rxcui)
        return self

    def add_concept(self, rxcui: str, name: str, *, tty: str = "SCD",
                    ingredients: List[str] = (), atc: List[str] = (),
                    dailymed: List[str] = ()) -> "FakeRxNav":
        self.concepts[str(rxcui)] = {
            "properties": {"rxcui": str(rxcui), "name": name, "tty": tty,
                           "synonym": ""},
            "ingredients": list(ingredients),
            "classes": {"ATC": list(atc), "DAILYMED": list(dailymed)},
        }
        return self

    # ── the opener ────────────────────────────────────────────────────
    def __call__(self, url: str, headers: Dict[str, str], timeout: float
                 ) -> RawResponse:
        idx = len(self.calls)
        self.calls.append(url)
        if idx in self.transients:
            status, hdrs = self.transients[idx]
            return RawResponse(status=status, headers=hdrs or {}, body=b"{}")

        parsed = urlparse(url)
        path = parsed.path
        qs = {k: v[0] for k, v in parse_qs(parsed.query).items()}

        if path.endswith("/rxcui.json"):
            return self._ok(self._id_group(qs))
        if path.endswith("/approximateTerm.json"):
            rxcui = self.approx_to_rxcui.get(str(qs.get("term", "")).lower())
            if not rxcui:
                return self._ok({"approximateGroup": {}})
            return self._ok({"approximateGroup":
                             {"candidate": [{"rxcui": rxcui, "score": "50"}]}})
        if path.endswith("/properties.json"):
            rxcui = _rxcui_from_path(path)
            concept = self.concepts.get(rxcui)
            if not concept:
                return self._ok({})          # RxNav: 200 with no payload key
            return self._ok({"properties": concept["properties"]})
        if path.endswith("/related.json"):
            rxcui = _rxcui_from_path(path)
            concept = self.concepts.get(rxcui) or {}
            ings = concept.get("ingredients") or []
            if not ings:
                return self._ok({"relatedGroup": {}})
            return self._ok({"relatedGroup": {"conceptGroup": [
                {"tty": "IN", "conceptProperties": [
                    {"rxcui": f"i{n}", "name": nm, "tty": "IN"}
                    for n, nm in enumerate(ings)]}]}})
        if path.endswith("/rxclass/class/byRxcui.json"):
            rxcui = str(qs.get("rxcui", ""))
            source = str(qs.get("relaSource", ""))
            names = ((self.concepts.get(rxcui) or {})
                     .get("classes", {}).get(source) or [])
            if not names:
                return self._ok({"rxclassDrugInfoList": {}})
            return self._ok({"rxclassDrugInfoList": {"rxclassDrugInfo": [
                {"rxclassMinConceptItem": {"className": nm, "classId": f"C{n}",
                                           "classType": source}}
                for n, nm in enumerate(names)]}})
        return RawResponse(status=404, body=b"{}")

    def _id_group(self, qs: Dict[str, str]) -> Dict[str, Any]:
        if qs.get("idtype") == "NDC":
            digits = "".join(c for c in str(qs.get("id", "")) if c.isdigit())
            rxcui = self.ndc_to_rxcui.get(digits)
        else:
            rxcui = self.name_to_rxcui.get(str(qs.get("name", "")).lower())
        if not rxcui:
            # RxNav returns the envelope with no rxnormId list at all.
            return {"idGroup": {}}
        return {"idGroup": {"rxnormId": [rxcui]}}

    @staticmethod
    def _ok(payload: Dict[str, Any]) -> RawResponse:
        return RawResponse(status=200, body=json.dumps(payload).encode())


def _rxcui_from_path(path: str) -> str:
    """``/REST/rxcui/{rxcui}/properties.json`` → ``{rxcui}``."""
    parts = [p for p in path.split("/") if p]
    for i, p in enumerate(parts):
        if p == "rxcui" and i + 1 < len(parts):
            return parts[i + 1]
    return ""
