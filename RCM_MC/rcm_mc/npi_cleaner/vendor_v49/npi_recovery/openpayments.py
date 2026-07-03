"""CMS Open Payments connector (v18) — free, public, no license.

For each drug on the panel, this pulls the physicians the drug's MANUFACTURER
paid (general payments), keyed to a real ``covered_recipient_npi``. Two uses:

  • the strongest *free* signal for the referring/prescriber gap the external-data
    strategy flagged (~14k missing referring NPIs) — the physicians a drug-maker
    pays are exactly the ones who prescribe/refer that product; and
  • a genuine diligence signal in its own right: a financial relationship between
    the billed drug's maker and the referring physician (KOL / steering context).

What it does NOT do: recover the branded PAYER. Nothing public can — the branded
carrier on a closed, self-funded claim is ERISA-preempted and contractually
blinded. See the Recoverability_Map sheet for the full field-by-field floor.

The Open Payments general-payment file is large, so queries are bounded (one drug
at a time, capped rows, state-scoped) and cached pickle-per-key like every other
connector, so re-runs are instant.
"""
from __future__ import annotations
import re

OP_BASE = "https://openpaymentsdata.cms.gov/api/1"
_DRUG_FIELD = "name_of_drug_or_biological_or_device_or_medical_supply_1"


def brand_from_name(nm: str) -> str:
    """Brand sits in the trailing [brackets] of an RxNorm SBD name."""
    m = re.search(r"\[([^\]]+)\]", nm or "")
    return m.group(1).strip() if m else ""


class OpenPaymentsClient:
    def __init__(self, cache, timeout=90, max_rows=1500):
        from .clients import _make_session
        self.cache = cache
        self.timeout = timeout
        self.max_rows = max_rows
        self.session = _make_session()
        self._dist = None

    def _distribution(self):
        """Resolve the most-recent General Payment dataset distribution id (cached)."""
        if self._dist:
            return self._dist
        cached = self.cache.get("open_payments", "_distribution")
        if cached:
            self._dist = cached
            return cached
        try:
            r = self.session.get(f"{OP_BASE}/metastore/schemas/dataset/items",
                                 params={"show-reference-ids": ""}, timeout=self.timeout)
            items = r.json()
            gp = [d for d in items if "General Payment Data" in (d.get("title") or "")]

            def _yr(d):
                m = re.search(r"(20\d\d)", d.get("title", ""))
                return int(m.group(1)) if m else 0
            gp.sort(key=_yr, reverse=True)
            for d in gp:
                dist = d.get("distribution", [])
                if dist and isinstance(dist[0], dict) and dist[0].get("identifier"):
                    self._dist = dist[0]["identifier"]
                    self.cache.set("open_payments", "_distribution", self._dist)
                    return self._dist
        except Exception:
            return None
        return None

    def paid_physicians(self, drug_name: str, state: str = "") -> set:
        """Distinct physician NPIs the maker of `drug_name` paid (optionally in `state`)."""
        if not drug_name:
            return set()
        key = f"{drug_name.lower()}|{(state or '').upper()}"
        cached = self.cache.get("open_payments", key)
        if cached is not None:
            return set(cached)
        dist = self._distribution()
        if not dist:
            return set()
        url = f"{OP_BASE}/datastore/query/{dist}"
        conds = [{"property": _DRUG_FIELD, "value": f"%{drug_name}%", "operator": "like"},
                 {"property": "covered_recipient_type", "value": "%Physician%", "operator": "like"}]
        if state:
            conds.append({"property": "recipient_state", "value": state.upper(), "operator": "="})
        npis, offset = set(), 0
        try:
            while len(npis) < self.max_rows and offset < self.max_rows * 3:
                body = {"conditions": conds, "limit": 500, "offset": offset,
                        "properties": ["covered_recipient_npi"]}
                r = self.session.post(url, json=body, timeout=self.timeout)
                res = r.json().get("results", [])
                if not res:
                    break
                for x in res:
                    n = str(x.get("covered_recipient_npi", "") or "").strip()
                    if n.isdigit() and len(n) == 10:
                        npis.add(n)
                if len(res) < 500:
                    break
                offset += 500
        except Exception:
            pass
        self.cache.set("open_payments", key, sorted(npis))
        return npis


def build_paid_map(client, drug_ident, states, max_drugs=25, progress=None):
    """brand(lower) -> set(NPIs the maker paid), unioned over the panel's states.

    `drug_ident` is the verified-connector drug dictionary (records carry an
    RxNorm name with the brand in brackets); `states` are the distinct claim
    states. Bounded by `max_drugs` so a wide book stays cheap.
    """
    progress = progress or (lambda m, f: None)
    if client is None or not drug_ident:
        return {}
    brands = set()
    for rec in drug_ident.values():
        b = brand_from_name((rec or {}).get("name", ""))
        if b:
            brands.add(b)
    brands = sorted(brands)[:max_drugs]
    states = [s for s in (states or []) if isinstance(s, str) and len(s) == 2] or [""]
    paid = {}
    for i, b in enumerate(brands):
        acc = set()
        for st in states:
            acc |= client.paid_physicians(b, st)
        if acc:
            paid[b.lower()] = acc
        progress(f"Open Payments: {b}", (i + 1) / max(1, len(brands)))
    return paid
