"""IRS Form 990 loader for non-profit hospitals.

Thin wrapper around the existing :mod:`rcm_mc.data.irs990` fetcher
(ProPublica Nonprofit Explorer API) that normalizes the data into
:class:`IRS990Record` rows and pushes them into ``hospital_benchmarks``.

Non-profits are ~58% of US hospitals, and Schedule H of Form 990 is
the authoritative source for charity-care and bad-debt numbers —
cleaner than HCRIS for those specific lines because the 990 has them
at-cost rather than at-charges.

The "index" functions are nominal — ProPublica doesn't expose a bulk
hospital-list endpoint, so refreshing here means iterating over a
caller-supplied EIN list. We persist the resolved EIN→CCN crosswalk
where possible so future refreshes don't need the partner to re-enter it.
"""
from __future__ import annotations

import json
import logging
import urllib.parse
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from . import _cms_download
from .irs990 import fetch_990, filings_by_tax_year

logger = logging.getLogger(__name__)


# ProPublica Nonprofit Explorer — nonprofit search. NTEE codes E20/21/22
# are hospital / hospital-system categories.
_PROPUBLICA_SEARCH = (
    "https://projects.propublica.org/nonprofits/api/v2/search.json"
    "?q={q}&ntee%5B%5D=E20&ntee%5B%5D=E21&ntee%5B%5D=E22"
)


# ── Record ───────────────────────────────────────────────────────────

@dataclass
class IRS990Record:
    ein: str
    name: str = ""
    fiscal_year: Optional[int] = None
    total_revenue: Optional[float] = None
    total_expenses: Optional[float] = None
    charity_care_at_cost: Optional[float] = None
    bad_debt_expense: Optional[float] = None
    medicare_surplus_or_shortfall: Optional[float] = None
    medicaid_surplus_or_shortfall: Optional[float] = None
    #: List of ``{"name": str, "title": str, "compensation": float}`` rows.
    executive_compensation: List[Dict[str, Any]] = field(default_factory=list)

    provider_id: Optional[str] = None   # CMS CCN when known (analyst-supplied)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def benchmark_rows(self, *, period: Optional[str] = None) -> List[Dict[str, Any]]:
        """Benchmark rows key on provider_id (CCN) if available, otherwise EIN."""
        pid = self.provider_id or f"EIN:{self.ein}"
        per = period or (str(self.fiscal_year) if self.fiscal_year else "")
        out: List[Dict[str, Any]] = []
        for k in ("total_revenue", "total_expenses", "charity_care_at_cost",
                  "bad_debt_expense", "medicare_surplus_or_shortfall",
                  "medicaid_surplus_or_shortfall"):
            v = getattr(self, k)
            if v is None:
                continue
            out.append({
                "provider_id": pid,
                "metric_key": k,
                "value": v,
                "period": per,
            })
        if self.executive_compensation:
            total = sum(float(e.get("compensation") or 0.0)
                        for e in self.executive_compensation[:5])
            out.append({
                "provider_id": pid,
                "metric_key": "top5_exec_compensation_total",
                "value": total,
                "period": per,
            })
        return out


# ── Download / index ─────────────────────────────────────────────────

def download_990_index(
    year: int,
    *,
    query: str = "hospital",
    dest: Optional[Path] = None,
    overwrite: bool = False,
) -> Path:
    """Fetch a ProPublica search JSON for hospital non-profits.

    Not a bulk index — ProPublica returns the first ~100 hits. Partners
    wanting comprehensive coverage should run this once per query and
    concatenate the results. Caller is expected to extract the EIN list
    and feed it to :func:`refresh_from_ein_list`.
    """
    url = _PROPUBLICA_SEARCH.format(q=urllib.parse.quote(query))
    dest = Path(dest) if dest else _cms_download.cache_dir("irs990") / f"index_{year}_{query}.json"
    return _cms_download.fetch_url(url, dest, overwrite=overwrite)


# ── Parse ────────────────────────────────────────────────────────────

# Schedule H of Form 990 reports charity care at cost, bad debt, and
# payer-surplus lines. ProPublica flattens some of these into the
# root filing object; field names vary by tax year.
_SCHEDULE_H_FIELDS = {
    "charity_care_at_cost": ("charitycareatcost", "totchrtycrcost"),
    "bad_debt_expense":     ("baddebtexpense", "badeebtexp", "totbaddebtexp"),
    "medicare_surplus_or_shortfall": ("mcaresurplsshtfl", "mcaresurplsshortfall"),
    "medicaid_surplus_or_shortfall": ("mcaidsurplsshtfl", "mcaidsurplsshortfall"),
    "total_revenue":        ("totrevenue", "totrev"),
    "total_expenses":       ("totfuncexpns", "totexpenses"),
}


def _first_num(obj: Dict[str, Any], keys: Iterable[str]) -> Optional[float]:
    for k in keys:
        v = obj.get(k)
        if v is None or v == "":
            continue
        try:
            return float(v)
        except (TypeError, ValueError):
            continue
    return None


def parse_990_schedule_h(
    ein: str,
    *,
    fetcher=None,
    year: Optional[int] = None,
) -> IRS990Record:
    """Resolve a single EIN's 990 filing(s) to an :class:`IRS990Record`.

    ``fetcher`` is injected for tests (defaults to
    :func:`rcm_mc.data.irs990.fetch_990`). Picks the filing for ``year``
    if supplied, otherwise the most recent.
    """
    fetch = fetcher if fetcher is not None else fetch_990
    payload = fetch(ein)
    org = (payload.get("organization") or {}) if isinstance(payload, dict) else {}

    filings = filings_by_tax_year(payload)
    if not filings:
        return IRS990Record(ein=str(ein), name=str(org.get("name") or ""))
    chosen_year = year if (year is not None and year in filings) else max(filings.keys())
    filing = filings[chosen_year] or {}

    # Executive comp: ProPublica occasionally returns officers under
    # ``officers`` at the top level. When absent the list stays empty.
    officers_raw = payload.get("officers") or []
    officers: List[Dict[str, Any]] = []
    for o in officers_raw[:10]:
        if not isinstance(o, dict):
            continue
        officers.append({
            "name": str(o.get("name") or ""),
            "title": str(o.get("title") or ""),
            "compensation": _first_num(o, ("compensation", "reportablecompfromorg",
                                           "totcntrbgfts", "compdriven")) or 0.0,
        })
    # Sort by compensation descending so [:5] is top-5.
    officers.sort(key=lambda o: float(o.get("compensation") or 0.0), reverse=True)

    return IRS990Record(
        ein=str(ein),
        name=str(org.get("name") or ""),
        fiscal_year=int(chosen_year),
        total_revenue=_first_num(filing, _SCHEDULE_H_FIELDS["total_revenue"]),
        total_expenses=_first_num(filing, _SCHEDULE_H_FIELDS["total_expenses"]),
        charity_care_at_cost=_first_num(filing, _SCHEDULE_H_FIELDS["charity_care_at_cost"]),
        bad_debt_expense=_first_num(filing, _SCHEDULE_H_FIELDS["bad_debt_expense"]),
        medicare_surplus_or_shortfall=_first_num(filing, _SCHEDULE_H_FIELDS["medicare_surplus_or_shortfall"]),
        medicaid_surplus_or_shortfall=_first_num(filing, _SCHEDULE_H_FIELDS["medicaid_surplus_or_shortfall"]),
        executive_compensation=officers[:5],
    )


# ── Load ─────────────────────────────────────────────────────────────

def load_irs990_to_store(
    store: Any,
    records: Iterable[IRS990Record],
    *,
    period: Optional[str] = None,
) -> int:
    from .data_refresh import save_benchmarks
    rows: List[Dict[str, Any]] = []
    for rec in records:
        rows.extend(rec.benchmark_rows(period=period))
    return save_benchmarks(store, rows, source="IRS990", period=period)


def refresh_from_ein_list(
    store: Any,
    eins: Iterable[str],
    *,
    ein_to_ccn: Optional[Dict[str, str]] = None,
    fetcher=None,
) -> int:
    """Pull 990 data for each EIN in the list and load to ``hospital_benchmarks``."""
    ein_to_ccn = ein_to_ccn or {}
    records: List[IRS990Record] = []
    for ein in eins:
        try:
            rec = parse_990_schedule_h(ein, fetcher=fetcher)
        except Exception as exc:  # noqa: BLE001
            logger.warning("irs990: EIN %s failed: %s", ein, exc)
            continue
        rec.provider_id = ein_to_ccn.get(str(ein))
        records.append(rec)
    return load_irs990_to_store(store, records)


# ── Refresh entry point ──────────────────────────────────────────────

def refresh_irs990_source(store: Any) -> int:
    """Default refresher: reads an EIN list from the data cache.

    A real deployment seeds ``irs990/ein_list.json`` with the EINs of
    every target / comparable the portfolio tracks. When the file is
    missing we SKIP rather than fail — the IRS990 layer is optional
    (only non-profits file 990s), so silence is fine. A refresher that
    does nothing returns ``0``, which the orchestrator logs as OK.
    """
    path = _cms_download.cache_dir("irs990") / "ein_list.json"
    if not path.is_file():
        logger.info("irs990: no ein_list.json in cache; skipping refresh")
        return 0
    try:
        raw = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"irs990: bad ein_list.json: {exc}") from exc
    if isinstance(raw, list):
        eins = [str(e) for e in raw]
        ein_to_ccn: Dict[str, str] = {}
    elif isinstance(raw, dict):
        eins = list(raw.keys())
        ein_to_ccn = {str(k): str(v) for k, v in raw.items() if v}
    else:
        raise RuntimeError("irs990: ein_list.json must be a list or {ein: ccn} dict")
    return refresh_from_ein_list(store, eins, ein_to_ccn=ein_to_ccn)
