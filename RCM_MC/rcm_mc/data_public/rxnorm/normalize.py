"""NDC + RxNorm concept normalization — the join-correctness core.

Why this module is load-bearing: the NDC→RxCUI crosswalk is the spine that
ties NDC-keyed records (recalls, adverse events, drug spend) back to a single
molecule. Other sources (openFDA in particular) present NDCs in *different*
formats, so a record only joins if both sides agree on one canonical key.
The single biggest cause of broken drug joins is NDC format drift, so every
NDC is reduced here to a canonical **11-digit, hyphen-free 5-4-2** form, and
the raw value is always retained alongside it.

NDC format primer (the HIPAA 11-digit convention):
  An NDC has three segments — labeler, product, package. The FDA prints it in
  one of four 10-digit configurations (by segment length):
      4-4-2, 5-3-2, 5-4-1   (10-digit, deficient in one segment)
      5-4-2                 (already 11-digit)
  The canonical 11-digit form is 5-4-2; you convert a 10-digit NDC by
  left-padding the *deficient* segment with a single zero. Which segment is
  deficient is only knowable from the hyphenation, which is exactly why an
  unhyphenated 10-digit NDC is ambiguous (see DECISIONS.md).

Stdlib only. Pure functions — no I/O, no network, nothing runs at import.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


class NdcNormalizationError(ValueError):
    """Raised when an NDC string cannot be reduced to a canonical 11-digit form."""


# Target canonical segmentation: labeler-product-package = 5-4-2 = 11 digits.
_CANON = (5, 4, 2)


def _pad_segment(seg: str, width: int) -> str:
    """Left-pad one NDC segment to ``width`` with zeros (HIPAA 11-digit rule)."""
    return seg.zfill(width)


def normalize_ndc(raw: str, *, assume_unhyphenated_10: str = "4-4-2") -> str:
    """Reduce any NDC representation to a canonical 11-digit, hyphen-free string.

    Handles the four hyphenated configurations by segment length, and an
    already-11-digit unhyphenated value as a pass-through. An unhyphenated
    10-digit NDC is genuinely ambiguous (the segmentation is unknowable); we
    fall back to ``assume_unhyphenated_10`` (default 4-4-2, i.e. prepend one
    zero to the labeler — the most common case in practice) and the raw value
    is always retained by the caller so nothing is lost. See DECISIONS.md.

    Raises :class:`NdcNormalizationError` for inputs that cannot be a valid NDC
    rather than guessing — a wrong key silently drops records, so we fail loud.
    """
    if raw is None:
        raise NdcNormalizationError("NDC is None")
    s = str(raw).strip()
    if not s:
        raise NdcNormalizationError("empty NDC")

    if "-" in s:
        segs = s.split("-")
        if len(segs) != 3 or not all(seg.isdigit() for seg in segs):
            raise NdcNormalizationError(f"malformed hyphenated NDC: {raw!r}")
        lengths = tuple(len(seg) for seg in segs)
        # Pad each segment up to the canonical width. This is correct for the
        # three deficient configs (4-4-2, 5-3-2, 5-4-1) and a no-op for 5-4-2.
        if any(lengths[i] > _CANON[i] for i in range(3)):
            raise NdcNormalizationError(
                f"NDC segment longer than canonical 5-4-2: {raw!r}"
            )
        out = "".join(_pad_segment(segs[i], _CANON[i]) for i in range(3))
        if len(out) != 11:
            raise NdcNormalizationError(f"NDC did not reduce to 11 digits: {raw!r}")
        return out

    digits = "".join(ch for ch in s if ch.isdigit())
    if len(digits) != len(s):
        raise NdcNormalizationError(f"non-digit characters in NDC: {raw!r}")
    if len(digits) == 11:
        return digits
    if len(digits) == 10:
        # Ambiguous without hyphens; apply the configured assumption.
        layout = {
            "4-4-2": (4, 4, 2),
            "5-3-2": (5, 3, 2),
            "5-4-1": (5, 4, 1),
        }.get(assume_unhyphenated_10)
        if layout is None:
            raise NdcNormalizationError(
                f"unknown assume_unhyphenated_10={assume_unhyphenated_10!r}"
            )
        a, b, c = layout
        segs = (digits[:a], digits[a:a + b], digits[a + b:])
        return "".join(_pad_segment(segs[i], _CANON[i]) for i in range(3))
    raise NdcNormalizationError(
        f"NDC has {len(digits)} digits; expected 10 or 11: {raw!r}"
    )


def format_ndc_11(ndc_11: str) -> str:
    """Render a canonical 11-digit NDC back into 5-4-2 hyphenated form.

    Used by the round-trip DQ test: ``normalize_ndc(format_ndc_11(x)) == x``.
    """
    d = "".join(ch for ch in str(ndc_11) if ch.isdigit())
    if len(d) != 11:
        raise NdcNormalizationError(f"not an 11-digit NDC: {ndc_11!r}")
    return f"{d[:5]}-{d[5:9]}-{d[9:]}"


# ── RxNorm concept status / history ───────────────────────────────────────

# Term types we treat as the in-scope concept universe (see source spec).
IN_SCOPE_TTY = ("IN", "PIN", "MIN", "BN", "SCD", "SBD", "SCDC", "GPCK", "BPCK")

# RxNav historystatus → our normalized status vocabulary.
_STATUS_MAP = {
    "active": "active",
    "retired": "retired",
    "remapped": "remapped",
    "quantified": "active",   # quantified concepts are live concepts
    "obsolete": "retired",
    "alien": "remapped",
    "ndc": "active",
    "never%20active": "retired",
    "never active": "retired",
    "unknown": "active",
}


def normalize_status(raw_status: str) -> str:
    """Map an RxNav historystatus string to {active, retired, remapped}."""
    return _STATUS_MAP.get(str(raw_status or "").strip().lower(), "active")


# Relationship label normalization for bridge_rxcui_related. RxNav expresses
# relationships as term-type group names (IN, BN, SCD, SBD, …) on allrelated;
# we map the related concept's tty to a directional relationship label.
_RELATIONSHIP_BY_TTY = {
    "IN": "ingredient_of",
    "PIN": "ingredient_of",
    "MIN": "ingredient_of",
    "BN": "brand_of",
    "SCD": "clinical_drug",
    "SBD": "branded_drug",
    "SCDC": "clinical_drug_component",
    "GPCK": "clinical_pack",
    "BPCK": "branded_pack",
}


def relationship_for_tty(tty: str) -> str:
    """Relationship label for a related concept of the given term type."""
    return _RELATIONSHIP_BY_TTY.get(str(tty or "").strip().upper(), "related")


@dataclass(frozen=True)
class ConceptRow:
    rxcui: str
    name: str
    tty: str
    status: str = "active"
    remapped_to_rxcui: str = ""


def parse_allconcepts(payload: Dict) -> List[ConceptRow]:
    """Parse /allconcepts.json (minConceptGroup.minConcept) → ConceptRow list."""
    if not isinstance(payload, dict):
        return []
    group = payload.get("minConceptGroup", {}) or {}
    out: List[ConceptRow] = []
    for c in group.get("minConcept", []) or []:
        rxcui = str(c.get("rxcui", "")).strip()
        if not rxcui:
            continue
        out.append(ConceptRow(
            rxcui=rxcui,
            name=str(c.get("name", "")).strip(),
            tty=str(c.get("tty", "")).strip().upper(),
        ))
    return out


def parse_properties(payload: Dict) -> Optional[ConceptRow]:
    """Parse /rxcui/{rxcui}/properties.json → one ConceptRow (or None)."""
    if not isinstance(payload, dict):
        return None
    props = payload.get("properties", {}) or {}
    rxcui = str(props.get("rxcui", "")).strip()
    if not rxcui:
        return None
    return ConceptRow(
        rxcui=rxcui,
        name=str(props.get("name", "")).strip(),
        tty=str(props.get("tty", "")).strip().upper(),
    )


def parse_historystatus(payload: Dict) -> Tuple[str, str]:
    """Parse /rxcui/{rxcui}/historystatus.json → (status, remapped_to_rxcui).

    Retired/remapped handling is what stops stale codes from silently
    corrupting joins: we surface the current status and, when the concept was
    remapped, the rxcui it was remapped *to* so the crosswalk can resolve
    through it.
    """
    if not isinstance(payload, dict):
        return ("active", "")
    hist = payload.get("rxcuiStatusHistory", {}) or {}
    meta = hist.get("metaData", {}) or {}
    status = normalize_status(meta.get("status", ""))
    remapped_to = ""
    # Remapped concepts list their target(s) under derivedConcepts /
    # remappedConcept (shape varies by release); take the first remap target.
    derived = hist.get("derivedConcepts", {}) or {}
    remaps = derived.get("remappedConcept", []) or []
    if isinstance(remaps, dict):
        remaps = [remaps]
    for r in remaps:
        cand = str((r or {}).get("remappedRxCui", "")).strip()
        if cand:
            remapped_to = cand
            break
    if status == "remapped" and not remapped_to:
        # Some releases put the target on attributes; leave empty if truly
        # absent — the resolver treats an empty remap as unresolved.
        pass
    return (status, remapped_to)


def parse_related(payload: Dict) -> List[Tuple[str, str, str]]:
    """Parse /rxcui/{rxcui}/allrelated.json → [(related_rxcui, tty, relationship)]."""
    if not isinstance(payload, dict):
        return []
    group = payload.get("allRelatedGroup", {}) or {}
    out: List[Tuple[str, str, str]] = []
    for cg in group.get("conceptGroup", []) or []:
        tty = str(cg.get("tty", "")).strip().upper()
        for cp in cg.get("conceptProperties", []) or []:
            rxcui = str(cp.get("rxcui", "")).strip()
            if rxcui:
                out.append((rxcui, tty, relationship_for_tty(tty)))
    return out


def parse_ndcs_for_rxcui(payload: Dict) -> List[str]:
    """Parse /rxcui/{rxcui}/ndcs.json → list of raw NDC strings."""
    if not isinstance(payload, dict):
        return []
    grp = payload.get("ndcGroup", {}) or {}
    lst = (grp.get("ndcList", {}) or {}).get("ndc", []) or []
    return [str(n).strip() for n in lst if str(n).strip()]


def parse_rxcui_by_ndc(payload: Dict) -> List[str]:
    """Parse /rxcui.json?idtype=NDC&id=... → list of rxcui strings."""
    if not isinstance(payload, dict):
        return []
    grp = payload.get("idGroup", {}) or {}
    return [str(x).strip() for x in (grp.get("rxnormId", []) or []) if str(x).strip()]


def parse_approximate(payload: Dict) -> List[Dict[str, str]]:
    """Parse /approximateTerm.json → ranked candidate rxcui matches.

    Supports manufacturer / product-name normalization other sources rely on:
    a fuzzy string resolves to candidate concepts with a score + rank.
    """
    if not isinstance(payload, dict):
        return []
    grp = payload.get("approximateGroup", {}) or {}
    out: List[Dict[str, str]] = []
    for c in grp.get("candidate", []) or []:
        rxcui = str(c.get("rxcui", "")).strip()
        if not rxcui:
            continue
        out.append({
            "rxcui": rxcui,
            "score": str(c.get("score", "")).strip(),
            "rank": str(c.get("rank", "")).strip(),
        })
    return out


def parse_drugs(payload: Dict) -> List[Dict[str, str]]:
    """Parse /drugs.json → concept rows grouped by term type (name search)."""
    if not isinstance(payload, dict):
        return []
    grp = payload.get("drugGroup", {}) or {}
    out: List[Dict[str, str]] = []
    for cg in grp.get("conceptGroup", []) or []:
        tty = str(cg.get("tty", "")).strip().upper()
        for cp in cg.get("conceptProperties", []) or []:
            rxcui = str(cp.get("rxcui", "")).strip()
            if rxcui:
                out.append({"rxcui": rxcui,
                            "name": str(cp.get("name", "")).strip(),
                            "tty": tty})
    return out


@dataclass(frozen=True)
class DrugClassRow:
    rxcui: str
    class_id: str
    class_name: str
    class_type: str  # ATC | therapeutic | mechanism_of_action


# RxClass classType → our normalized class_type vocabulary.
_CLASS_TYPE_MAP = {
    "ATC1-4": "ATC",
    "ATC": "ATC",
    "VA": "therapeutic",
    "MESHPA": "therapeutic",
    "EPC": "therapeutic",
    "DISEASE": "therapeutic",
    "MOA": "mechanism_of_action",
    "PE": "mechanism_of_action",
    "CHEM": "mechanism_of_action",
}


def normalize_class_type(raw: str) -> str:
    return _CLASS_TYPE_MAP.get(str(raw or "").strip().upper(), "therapeutic")


def parse_rxclass(payload: Dict, rxcui: str) -> List[DrugClassRow]:
    """Parse /rxclass/class/byRxcui.json → DrugClassRow list for one rxcui."""
    if not isinstance(payload, dict):
        return []
    info_list = (payload.get("rxclassDrugInfoList", {}) or {}).get(
        "rxclassDrugInfo", []) or []
    out: List[DrugClassRow] = []
    seen = set()
    for info in info_list:
        cls = (info or {}).get("rxclassMinConceptItem", {}) or {}
        class_id = str(cls.get("classId", "")).strip()
        if not class_id:
            continue
        key = (rxcui, class_id)
        if key in seen:
            continue
        seen.add(key)
        out.append(DrugClassRow(
            rxcui=str(rxcui),
            class_id=class_id,
            class_name=str(cls.get("className", "")).strip(),
            class_type=normalize_class_type(cls.get("classType", "")),
        ))
    return out
