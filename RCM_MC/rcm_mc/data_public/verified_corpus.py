"""Bridge the source-cited ``verified_deals.VERIFIED_DEALS`` reference list
into the analytics corpus as first-class **real** deals.

Why this exists
---------------
``verified_deals.py`` holds 79 hand-curated, individually source-cited PE
healthcare deals (every row has a real ``source_url`` — SEC EDGAR, sponsor
sites, trade press). But it was a *standalone reference list*: the corpus
loader never read it, so those validated deals did not count toward the
provenance-tagged "real" universe (only ~68 did). With the product moving
toward running on real rather than synthetic data, those 79 belong in the
corpus.

This module adapts the ``verified_deals`` schema (target / sponsor / year /
ev_usd_mm / sector / outcome / source_url …) to the corpus schema (deal_name /
buyer / year / ev_mm / sector / realized_moic …) and exposes
``VERIFIED_CORPUS_DEALS``. ``corpus_provenance`` tags the group "real" and
``corpus_loader`` loads it.

Discipline (credibility first)
------------------------------
- Identity facts (target, sponsor, year, sector, EV) are copied verbatim from
  the already-sourced ``verified_deals`` rows — nothing is invented here.
- ``ev_mm`` is carried only where ``verified_deals`` recorded it (26 of 79);
  the rest stay ``None`` rather than guessing.
- ``realized_moic`` is derived ONLY for the unambiguous ``outcome == "bankrupt"``
  case (Chapter 11 with equity wiped/severely impaired → ~0.0x), flagged in
  the notes. ``distressed`` / ``active`` / ``exited`` keep ``realized_moic =
  None`` (sponsor returns were not disclosed) — exactly the corpus's existing
  rule. ``realized_irr``, ``hold_years``, ``ebitda_at_entry_mm`` and
  ``payer_mix`` are left ``None``; they are not in the verified source and are
  not fabricated.
- Rows that duplicate a deal already in the real seed corpus (same company +
  same year — e.g. LifePoint/KKR 2018, Prospect/Leonard-Green) are dropped so
  the bridge only adds *net-new* real deals.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


# verified_deals uses a clean 12-value sector vocab; the corpus uses lowercase
# canonical sectors (see deals_corpus.REAL_DEAL_SECTORS). Map so the bridged
# deals AGGREGATE with the existing corpus rows instead of forming near-name
# duplicate buckets ("hospitals" vs "hospital").
_SECTOR_MAP: Dict[str, str] = {
    "hospitals": "hospital",
    "physician_practices": "physician_group",
    "rcm_healthtech": "health_it",
    "home_health_hospice": "home_health",
    "behavioral_health": "behavioral_health",
    "dental": "dental",
    "dermatology": "dermatology",
    "ophthalmology": "ophthalmology",
    "asc": "asc",
    "dialysis": "dialysis",
    "urgent_care": "urgent_care",
    "veterinary": "veterinary",
    "value_based_care": "value_based_care",
    "other_services": "other_services",
}


def _norm_name(s: str) -> str:
    """First two significant (len>1) word tokens, lowercased — used for the
    company-identity half of the dedup key."""
    toks = [t for t in re.findall(r"[a-z0-9]+", (s or "").lower()) if len(t) > 1]
    return " ".join(toks[:2])


def _existing_real_keys() -> set:
    """(_norm_name(deal_name), year) for every deal already tagged real in the
    seed corpus, so the bridge can skip true duplicates."""
    keys = set()
    try:
        from .deals_corpus import _SEED_DEALS
        from .extended_seed import EXTENDED_SEED_DEALS
        for d in list(_SEED_DEALS) + list(EXTENDED_SEED_DEALS):
            nm = _norm_name(d.get("deal_name", ""))
            yr = d.get("year")
            if nm:
                keys.add((nm, yr))
    except ImportError:
        pass
    return keys


def _moic_from_outcome(outcome: str) -> Optional[float]:
    # Only the unambiguous total-loss case gets a number; everything else is
    # an undisclosed return -> None (no fabrication).
    return 0.0 if outcome == "bankrupt" else None


def _adapt(v: Dict[str, Any], idx: int) -> Dict[str, Any]:
    target = v.get("target", "")
    sponsor = v.get("sponsor", "")
    outcome = v.get("outcome", "")
    note_bits = [v.get("outcome_note", "") or ""]
    if v.get("subsector_note"):
        note_bits.append(v["subsector_note"])
    src = " · ".join(b for b in (v.get("source_note"), v.get("source_url")) if b)
    if src:
        note_bits.append(f"Source: {src}")
    moic = _moic_from_outcome(outcome)
    if moic is not None:
        note_bits.append("realized_moic≈0 derived from documented Chapter 11 (equity impaired).")
    return {
        "source_id": f"vd_{idx:03d}",
        "source": "verified_deals",
        "deal_name": f"{target} – {sponsor}" if sponsor else target,
        "year": v.get("year"),
        "buyer": sponsor,
        "seller": "",
        "ev_mm": v.get("ev_usd_mm"),
        "ebitda_at_entry_mm": None,
        "hold_years": None,
        "realized_moic": moic,
        "realized_irr": None,
        "payer_mix": None,
        "sector": _SECTOR_MAP.get(v.get("sector", ""), v.get("sector") or None),
        "outcome": outcome,
        "source_url": v.get("source_url"),
        "notes": " | ".join(b for b in note_bits if b),
    }


def _build() -> List[Dict[str, Any]]:
    from .verified_deals import VERIFIED_DEALS
    existing = _existing_real_keys()
    seen: set = set()  # also guard against duplicate rows WITHIN verified_deals
    out: List[Dict[str, Any]] = []
    idx = 1
    for v in VERIFIED_DEALS:
        key = (_norm_name(v.get("target", "")), v.get("year"))
        if key in existing or key in seen:
            continue  # duplicate of a seed-corpus deal, or already emitted
        seen.add(key)
        out.append(_adapt(v, idx))
        idx += 1
    return out


VERIFIED_CORPUS_DEALS: List[Dict[str, Any]] = _build()
