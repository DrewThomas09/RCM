"""Universal CMS provider resolver — the front door of CMS Provider X-Ray.

Enter a CCN / provider id / facility name and this resolves it across every
live CMS vertical (Hospital/HCRIS, SNF, Home Health, Hospice, Dialysis, IRF,
LTCH), detecting which vertical(s) the identifier belongs to. It is the
foundation the X-Ray diligence report builds on; the benchmarking + evidence
layers it feeds reuse the existing cross-sector (#619) and investable-evidence
(#620) modules rather than reimplementing them.

Composes the six post-acute verticals through the shared `cross_sector`
registry and adds Hospital/HCRIS via the HCRIS latest-per-CCN frame.

Honest by construction: identifiers are strings with leading zeroes
preserved; exact CCN/id matches are found before name matches; a query that
hits more than one provider returns *all* matches (the caller shows a
resolver, never a guess); unknown queries return nothing. No external calls,
no synthetic fallback rows.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from .cross_sector import SECTORS, SECTOR_BY_ID

# Resolver order: most-specific / highest-value vertical first. A CCN that
# exists in several verticals lists Hospital before the post-acute sectors.
_RESOLVE_ORDER = (
    "hospital", "nursing-homes", "home-health", "hospice",
    "dialysis", "inpatient-rehab", "long-term-care-hospital",
)
_HOSPITAL_SOURCE = "CMS HCRIS (Healthcare Cost Report Information System)"


@dataclass(frozen=True)
class ProviderMatch:
    vertical: str            # sector id, e.g. "nursing-homes" or "hospital"
    vertical_label: str
    provider_id: str         # the CCN (string; leading zeroes preserved)
    ccn: Optional[str]
    name: str
    state: str
    city: str
    county: Optional[str]
    source_dataset: str
    profile_url: Optional[str]   # native vertical profile, if one exists
    xray_url: str                # the X-Ray report for this provider


def _s(v) -> str:
    return ("" if v is None else str(v)).strip()


def _xray_url(vertical: str, ccn: str) -> str:
    return f"/diligence/xray?ccn={ccn}&vertical={vertical}"


# ── Hospital / HCRIS adapter (the one vertical not in cross_sector) ──────────

def _hospital_rows() -> List[dict]:
    try:
        from .hcris import _get_latest_per_ccn
        df = _get_latest_per_ccn()
    except Exception:  # noqa: BLE001 — HCRIS absence must not break the resolver
        return []
    if df is None or getattr(df, "empty", True):
        return []
    cols = [c for c in ("ccn", "name", "city", "state", "county") if c in df.columns]
    return df[cols].to_dict("records")


def _hospital_match(row: dict) -> ProviderMatch:
    ccn = _s(row.get("ccn"))
    return ProviderMatch(
        vertical="hospital", vertical_label="Hospital (HCRIS)",
        provider_id=ccn, ccn=ccn, name=_s(row.get("name")),
        state=_s(row.get("state")).upper(), city=_s(row.get("city")),
        county=_s(row.get("county")) or None,
        source_dataset=_HOSPITAL_SOURCE,
        profile_url=f"/hospital/{ccn}" if ccn else None,
        xray_url=_xray_url("hospital", ccn),
    )


def _sector_match(sector_id: str, ccn: str, provider) -> ProviderMatch:
    spec = SECTOR_BY_ID[sector_id]
    county = getattr(provider, "county", None)
    return ProviderMatch(
        vertical=sector_id, vertical_label=spec.label,
        provider_id=ccn, ccn=ccn,
        name=_s(getattr(provider, spec.name_attr, "")),
        state=_s(getattr(provider, "state", "")).upper(),
        city=_s(getattr(provider, "city", "")),
        county=_s(county) or None,
        source_dataset=_s(getattr(provider, "source", "")) or spec.label,
        profile_url=f"{spec.route}/{ccn}",
        xray_url=_xray_url(sector_id, ccn),
    )


# ── Search + resolve ─────────────────────────────────────────────────────────

def _exact_id_matches(identifier: str, state: Optional[str]) -> List[ProviderMatch]:
    """All providers whose CCN/id == identifier, across every vertical."""
    ident = _s(identifier)
    st = _s(state).upper() or None
    out: List[ProviderMatch] = []
    for vid in _RESOLVE_ORDER:
        if vid == "hospital":
            for row in _hospital_rows():
                if _s(row.get("ccn")) == ident:
                    m = _hospital_match(row)
                    if st is None or m.state == st:
                        out.append(m)
        else:
            provider = SECTOR_BY_ID[vid].providers_loader().get(ident)
            if provider is not None:
                m = _sector_match(vid, ident, provider)
                if st is None or m.state == st:
                    out.append(m)
    return out


def _name_matches(query: str, state: Optional[str],
                  limit: int = 25) -> List[ProviderMatch]:
    """Case-insensitive name-contains across verticals (resolver order)."""
    q = _s(query).upper()
    st = _s(state).upper() or None
    if not q:
        return []
    out: List[ProviderMatch] = []
    # Hospitals first.
    for row in _hospital_rows():
        if q in _s(row.get("name")).upper():
            m = _hospital_match(row)
            if st is None or m.state == st:
                out.append(m)
                if len(out) >= limit:
                    return out
    for spec in SECTORS:
        for ccn, provider in spec.providers_loader().items():
            nm = _s(getattr(provider, spec.name_attr, "")).upper()
            if q in nm:
                m = _sector_match(spec.id, ccn, provider)
                if st is None or m.state == st:
                    out.append(m)
                    if len(out) >= limit:
                        return out
    return out


def search_provider_xray(query: str, state: Optional[str] = None) -> List[ProviderMatch]:
    """Resolve a query to provider matches.

    Exact CCN/provider-id matches (across all verticals) take priority; if
    none, falls back to case-insensitive name-contains. ``state`` (postal
    code) optionally narrows the result. Returns ``[]`` when nothing matches.
    """
    ident = _s(query)
    if not ident:
        return []
    exact = _exact_id_matches(ident, state)
    if exact:
        return exact
    return _name_matches(ident, state)


@dataclass(frozen=True)
class Ambiguous:
    """More than one provider matched — the caller must show a resolver."""
    matches: List[ProviderMatch]


def resolve_provider_xray(identifier: str, state: Optional[str] = None):
    """Resolve to a single ``ProviderMatch``, ``Ambiguous``, or ``None``.

    Never guesses between multiple matches — returns ``Ambiguous`` so the UI
    can present a resolver table.
    """
    matches = search_provider_xray(identifier, state)
    if not matches:
        return None
    if len(matches) == 1:
        return matches[0]
    return Ambiguous(matches=matches)


# Caller-vertical aliases → canonical resolver sector ids. The Target Screener
# (and other callers) pass loader-style keys (home_health, snf, irf, ltch,
# hospitals); the resolver's sector ids are hyphenated CMS-compare names. Map
# them so ?vertical= from those surfaces resolves a real report instead of
# falling back to the search page.
_VERTICAL_ALIASES = {
    "hospitals": "hospital",
    "home_health": "home-health", "homehealth": "home-health", "hha": "home-health",
    "snf": "nursing-homes", "nursing": "nursing-homes", "nursing_homes": "nursing-homes",
    "irf": "inpatient-rehab", "inpatient_rehab": "inpatient-rehab",
    "ltch": "long-term-care-hospital", "long_term_care_hospital": "long-term-care-hospital",
}


def provider_match_by_ccn(ccn: str, vertical: str) -> Optional[ProviderMatch]:
    """Direct lookup for a specific (ccn, vertical) — used by the report route
    once the vertical is known (e.g. from ?vertical=). None if not found.

    Accepts caller-vertical aliases (e.g. ``home_health`` → ``home-health``,
    ``snf`` → ``nursing-homes``, ``hospitals`` → ``hospital``) so screener-style
    keys resolve."""
    ident = _s(ccn)
    vid = _s(vertical)
    vid = _VERTICAL_ALIASES.get(vid, vid)
    if vid == "hospital":
        for row in _hospital_rows():
            if _s(row.get("ccn")) == ident:
                return _hospital_match(row)
        return None
    spec = SECTOR_BY_ID.get(vid)
    if spec is None:
        return None
    provider = spec.providers_loader().get(ident)
    return _sector_match(vid, ident, provider) if provider is not None else None
