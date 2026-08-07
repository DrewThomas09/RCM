"""Every Medicare-certified provider class, not just the acute hospital.

Why the hospital universe is not the universe
---------------------------------------------
HCRIS gives us 6,123 hospitals. That is where the beds and the revenue
are, and it is where a crosswalk naturally starts — but it is a small
minority of the CCNs a health system actually holds. A regional system
with eight hospitals routinely also operates two dozen dialysis
stations, a home-health agency, a hospice, and a nursing home, each
carrying its own CCN and each invisible to a hospital-only mapping.

CMS certifies and publishes six more provider classes, all bundled in
this repository already:

  ============  ======  ===================================================
  class          CCNs   source
  ============  ======  ===================================================
  snf           14,699  Nursing Home Care Compare — Provider Information
  hha           12,392  Provider Data Catalog — Home Health Agencies
  dialysis       7,557  Dialysis Facility Compare — Listing by Facility
  hospice        6,852  Provider Data Catalog — Hospice General Information
  irf            1,221  Inpatient Rehabilitation Facility Compare
  ltch             317  Long-Term Care Hospital Compare
  ============  ======  ===================================================

Together that is 43,038 rows against the hospital file's 6,123.

Two of those classes overlap the hospital universe on purpose. An IRF
or LTCH that files its own cost report already appears in HCRIS — 342
of 1,221 IRFs and 309 of 317 LTCHs. Those rows are dropped here rather
than in the crosswalk, because the HCRIS row is strictly richer: it
carries beds, revenue, and a filing-recency status the Compare files
have no equivalent for. What is left is 42,387 CCNs the hospital
universe genuinely never had.

The chain column
----------------
The dialysis file is the only one of the six that publishes an
explicit chain owner, and it is unusually good: 6,699 of 7,557
facilities name a parent (DaVita 2,800, Fresenius 2,772, US Renal Care
404, DCI 242 …). That column is carried through as ``chain_name`` and
used as a mapping source in its own right — an operator-published
parent beats any inference we could make from a facility name.

The other five classes leave ``chain_name`` empty. They are mapped the
same way hospitals are: by matching the facility name against the
system registry.

What this module does *not* do
------------------------------
It does not decide whether a provider is operating. The Compare files
carry a certification date but no termination date, so a facility that
closed last year still appears. The hospital universe infers status
from filing recency; there is no equivalent signal here, and inventing
one would be worse than admitting the gap. ``certification_date`` is
normalised and carried, and that is the whole of what these files
support.
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

_DATA = Path(__file__).resolve().parent

# The columns every class is flattened onto. Deliberately narrower than
# any single source file: a union crosswalk can only carry fields every
# member can populate, and per-class extras (SFF status, dialysis
# stations, abuse icons) belong to the class-specific readers.
UNIVERSE_COLUMNS: Tuple[str, ...] = (
    "ccn", "name", "street", "city", "state", "zip", "county",
    "provider_class", "provider_class_label", "cms_ownership",
    "beds", "chain_name", "certification_date", "source",
)


@dataclass(frozen=True)
class ClassSpec:
    """How one Compare file maps onto the common shape."""

    provider_class: str
    label: str
    filename: str
    name_column: str
    #: Column holding a bed/station/capacity count, if the file has one.
    beds_column: Optional[str] = None
    #: Column naming an explicit parent chain, if the file has one.
    chain_column: Optional[str] = None


CLASS_SPECS: Tuple[ClassSpec, ...] = (
    ClassSpec("snf", "Skilled Nursing", "snf_providers.csv",
              "provider_name", beds_column="certified_beds"),
    ClassSpec("hha", "Home Health", "home_health_providers.csv",
              "provider_name"),
    ClassSpec("dialysis", "Dialysis", "dialysis_providers.csv",
              "facility_name", beds_column="dialysis_stations",
              chain_column="chain_org"),
    ClassSpec("hospice", "Hospice", "hospice_providers.csv",
              "facility_name"),
    ClassSpec("irf", "Inpatient Rehab", "irf_providers.csv",
              "provider_name"),
    ClassSpec("ltch", "Long-Term Care", "ltch_providers.csv",
              "provider_name", beds_column="total_beds"),
)

CLASS_LABELS: Dict[str, str] = {s.provider_class: s.label for s in CLASS_SPECS}

# Values in a chain column that name no chain. "Independent" is a real
# answer to "who owns this?" and must not be mistaken for a parent.
_NON_CHAINS = {"", "independent", "other", "state owned", "unknown", "n/a", "none"}


_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}$")
_US_DATE = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})$")


def _norm_date(raw: str) -> str:
    """ISO-8601, from either format CMS uses; empty for anything else.

    The nursing-home file writes 1969-09-01; the rehab and long-term
    files write 10/01/1983. Storing both verbatim would make the column
    unsortable, which is the only thing a certification date is for.

    Anything that parses as neither becomes empty rather than passing
    through. One home-health agency files its certification date as a
    bare "-", and a sentinel that sorts before every real date is worse
    than an absent one.
    """
    text = (raw or "").strip()
    if not text:
        return ""
    if _ISO_DATE.match(text):
        return text
    us = _US_DATE.match(text)
    if us:
        month, day, year = us.groups()
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    return ""


def _norm_beds(raw: str) -> Optional[float]:
    try:
        value = float(str(raw).strip())
    except (TypeError, ValueError):
        return None
    return value if value >= 0 else None


def _norm_chain(raw: str) -> str:
    text = (raw or "").strip()
    return "" if text.lower() in _NON_CHAINS else text


def _read_class(spec: ClassSpec) -> List[Dict[str, object]]:
    path = _DATA / spec.filename
    if not path.exists():
        return []
    rows: List[Dict[str, object]] = []
    with path.open(newline="", encoding="utf-8") as fh:
        for raw in csv.DictReader(fh):
            ccn = str(raw.get("ccn") or "").strip()
            if not ccn:
                continue
            rows.append({
                "ccn": ccn,
                "name": str(raw.get(spec.name_column) or "").strip(),
                "street": str(raw.get("address") or "").strip(),
                "city": str(raw.get("city") or "").strip(),
                "state": str(raw.get("state") or "").strip().upper(),
                "zip": str(raw.get("zip") or "").strip()[:5],
                "county": str(raw.get("county") or "").strip(),
                "provider_class": spec.provider_class,
                "provider_class_label": spec.label,
                "cms_ownership": str(raw.get("ownership") or "").strip(),
                "beds": _norm_beds(raw.get(spec.beds_column or "", "")),
                "chain_name": _norm_chain(raw.get(spec.chain_column or "", "")),
                "certification_date": _norm_date(str(raw.get("certification_date") or "")),
                "source": str(raw.get("source") or "").strip(),
            })
    return rows


@lru_cache(maxsize=1)
def _raw_universe() -> pd.DataFrame:
    frames = [pd.DataFrame(_read_class(spec), columns=list(UNIVERSE_COLUMNS))
              for spec in CLASS_SPECS]
    frames = [f for f in frames if not f.empty]
    if not frames:
        return pd.DataFrame(columns=list(UNIVERSE_COLUMNS))
    return pd.concat(frames, ignore_index=True)


def load_post_acute_universe(
    exclude_ccns: Optional[frozenset] = None,
) -> pd.DataFrame:
    """The six non-hospital classes, one row per CCN.

    ``exclude_ccns`` drops CCNs already covered by a richer source —
    in practice the HCRIS hospital universe, which carries beds,
    revenue, and a filing-recency status these files cannot supply.
    Passing it here rather than filtering downstream keeps the "one row
    per CCN" invariant true of the frame itself.
    """
    out = _raw_universe().copy()
    if out.empty:
        return out
    if exclude_ccns:
        out = out[~out["ccn"].isin(exclude_ccns)]
    # A CCN can legitimately appear in two Compare files (an IRF that is
    # also listed as an LTCH). Keep the first, which follows CLASS_SPECS
    # order — the larger, better-attributed file wins.
    out = out.drop_duplicates(subset=["ccn"], keep="first").reset_index(drop=True)
    return out


def class_counts(df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Rows and chain attribution per provider class."""
    universe = load_post_acute_universe() if df is None else df
    if universe.empty:
        return pd.DataFrame(columns=["provider_class", "provider_class_label",
                                     "facilities", "with_chain"])
    grouped = universe.groupby(["provider_class", "provider_class_label"], as_index=False)
    out = grouped.agg(
        facilities=("ccn", "size"),
        with_chain=("chain_name", lambda s: int(s.astype(str).ne("").sum())),
    )
    return out.sort_values("facilities", ascending=False).reset_index(drop=True)


def chain_roster(df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Named parent chains, largest first — the operator-published ones.

    Only the dialysis file publishes this, so the roster is dialysis
    today. It is kept general because the shape is the useful thing:
    when CMS adds a chain column to another Compare file, or when a
    vendor file is dropped in, it lands here without a schema change.
    """
    universe = load_post_acute_universe() if df is None else df
    if universe.empty:
        return pd.DataFrame(columns=["chain_name", "facilities", "states", "classes"])
    named = universe[universe["chain_name"].astype(str).ne("")]
    if named.empty:
        return pd.DataFrame(columns=["chain_name", "facilities", "states", "classes"])
    out = named.groupby("chain_name", as_index=False).agg(
        facilities=("ccn", "size"),
        states=("state", "nunique"),
        classes=("provider_class", "nunique"),
    )
    return out.sort_values(["facilities", "chain_name"],
                           ascending=[False, True]).reset_index(drop=True)


def _clear_cache() -> None:
    """Test hook."""
    _raw_universe.cache_clear()
