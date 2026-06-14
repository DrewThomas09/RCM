"""Shared exhibit contract for CDD analytics.

Every CDD analytic returns an :class:`Exhibit`: a typed, audience-aware,
machine-reconcilable result object. The exhibit carries:

- ``series``/``rows``: the numeric payload (the chart data).
- ``footnotes``: machine-readable source, vintage, and key assumptions.
- ``assumptions``: named, editable, sourced assumption nodes. These are
  internal-only and are stripped from partner output unless ``internal_mode``.
- ``reconciliation``: the self-check an exhibit emits so a test can prove the
  numbers tie out to their source within a stated tolerance.
- ``flags``: statistical-reliability and diligence flags (small cohort, basis
  mismatch, divergence, concentration risk, and so on).

Two audiences are enforced in code, not by convention. ``Exhibit.render`` with
``internal_mode=False`` removes assumption nodes and any series tagged
internal-only, so a partner surface cannot leak model internals.

All user-facing copy passes :func:`lint_copy`, which rejects em-dashes and
AI-sounding filler. The estimators in this package are statistical only: no
LLM is ever on a path that produces a forecast, score, interval, or flag.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Sequence


# Audience that may see a piece of content.
AUDIENCE_BOTH = "both"
AUDIENCE_INTERNAL = "internal"
AUDIENCE_PARTNER = "partner"


# Phrases that read as AI filler. Rejected in user-facing copy.
_FILLER_PATTERNS = [
    r"in today'?s (?:fast[- ]paced|ever[- ]changing|rapidly evolving)",
    r"it'?s worth noting",
    r"it is worth noting",
    r"in the world of",
    r"when it comes to",
    r"at the end of the day",
    r"navigating the (?:complex|complexities)",
    r"in conclusion",
    r"furthermore,? it",
    r"as we (?:all )?know",
    r"dive deep",
    r"unlock(?:ing)? (?:the )?(?:power|potential)",
    r"leverage(?:s|d)? synerg",
    r"game[- ]chang",
]
_FILLER_RE = re.compile("|".join(_FILLER_PATTERNS), re.IGNORECASE)


class CopyError(ValueError):
    """Raised when user-facing copy violates the prose constraints."""


def lint_copy(text: str, *, where: str = "copy") -> str:
    """Reject em-dashes and AI filler in user-facing prose.

    Returns the text unchanged when it is clean so call sites can wrap inline.
    Code is exempt; this guards labels, titles, tooltips, and report text.
    """
    if text is None:
        return text
    if "—" in text or "–" in text:
        raise CopyError(
            f"{where}: em-dash or en-dash found in user-facing copy: {text!r}. "
            "Use a comma, colon, or period."
        )
    m = _FILLER_RE.search(text)
    if m:
        raise CopyError(
            f"{where}: AI-sounding filler found ({m.group(0)!r}) in: {text!r}."
        )
    return text


@dataclass
class Footnote:
    """Machine-readable provenance for an exhibit.

    ``source`` is the dataset or filing, ``vintage`` is its date or release,
    ``assumptions`` is a short list of key assumptions stated plainly.
    """

    source: str
    vintage: str
    assumptions: List[str] = field(default_factory=list)
    basis: str = ""  # e.g. "medical-services-repriced" vs "facility-inclusive"

    def validate(self) -> "Footnote":
        lint_copy(self.source, where="footnote.source")
        lint_copy(self.vintage, where="footnote.vintage")
        if self.basis:
            lint_copy(self.basis, where="footnote.basis")
        for a in self.assumptions:
            lint_copy(a, where="footnote.assumption")
        return self

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AssumptionNode:
    """A named, editable, sourced assumption.

    Internal-only by construction: partner renders strip these unless
    ``internal_mode`` is set. ``value`` is editable so an analyst can revise it.
    """

    key: str
    label: str
    value: float
    source: str
    editable: bool = True
    unit: str = ""

    def validate(self) -> "AssumptionNode":
        lint_copy(self.label, where=f"assumption[{self.key}].label")
        lint_copy(self.source, where=f"assumption[{self.key}].source")
        if self.unit:
            lint_copy(self.unit, where=f"assumption[{self.key}].unit")
        return self

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Flag:
    """A reliability or diligence flag with a one-line rationale and source."""

    code: str
    severity: str  # "info" | "warn" | "risk"
    message: str
    source: str = ""

    def validate(self) -> "Flag":
        lint_copy(self.message, where=f"flag[{self.code}].message")
        if self.source:
            lint_copy(self.source, where=f"flag[{self.code}].source")
        return self

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Reconciliation:
    """The self-check an exhibit emits so a test can prove the numbers tie out.

    ``identity`` names what is being reconciled (e.g. "volume+price+mix==total").
    ``lhs``/``rhs`` are the two sides; ``gap`` is their difference;
    ``tolerance`` is the allowed gap; ``ok`` is whether it ties out.
    """

    identity: str
    lhs: float
    rhs: float
    tolerance: float

    @property
    def gap(self) -> float:
        return float(self.lhs) - float(self.rhs)

    @property
    def ok(self) -> bool:
        return abs(self.gap) <= self.tolerance + 1e-12

    def validate(self) -> "Reconciliation":
        lint_copy(self.identity, where="reconciliation.identity")
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "identity": self.identity,
            "lhs": float(self.lhs),
            "rhs": float(self.rhs),
            "gap": float(self.gap),
            "tolerance": float(self.tolerance),
            "ok": bool(self.ok),
        }


@dataclass
class Series:
    """A named numeric series. ``internal_only`` series are partner-stripped."""

    name: str
    points: List[Dict[str, Any]] = field(default_factory=list)
    kind: str = "bar"  # bar | line | waterfall | bubble | choropleth | scatter
    internal_only: bool = False

    def validate(self) -> "Series":
        lint_copy(self.name, where=f"series[{self.name}].name")
        return self

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Exhibit:
    """An audience-aware, reconcilable CDD analytic result.

    ``feature_id`` ties the exhibit back to feature_list.json. ``audience``
    declares who the exhibit is built for. ``render`` produces the dict that a
    surface serializes, gating internal content on ``internal_mode``.
    """

    feature_id: str
    title: str
    audience: str
    series: List[Series] = field(default_factory=list)
    footnote: Optional[Footnote] = None
    assumptions: List[AssumptionNode] = field(default_factory=list)
    flags: List[Flag] = field(default_factory=list)
    reconciliations: List[Reconciliation] = field(default_factory=list)
    summary: str = ""
    meta: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> "Exhibit":
        lint_copy(self.title, where=f"{self.feature_id}.title")
        if self.summary:
            lint_copy(self.summary, where=f"{self.feature_id}.summary")
        if self.footnote is None:
            raise ValueError(f"{self.feature_id}: every exhibit must carry a footnote")
        self.footnote.validate()
        for s in self.series:
            s.validate()
        for a in self.assumptions:
            a.validate()
        for f in self.flags:
            f.validate()
        for r in self.reconciliations:
            r.validate()
        return self

    @property
    def reconciled(self) -> bool:
        """True when every emitted reconciliation ties out within tolerance."""
        return all(r.ok for r in self.reconciliations)

    def flag_codes(self) -> List[str]:
        return [f.code for f in self.flags]

    def render(self, internal_mode: bool = False) -> Dict[str, Any]:
        """Serialize for a surface.

        Partner render (``internal_mode=False``) strips assumption nodes and any
        internal-only series. This is the audience separation, enforced in code:
        a partner surface literally cannot receive the internal nodes.
        """
        self.validate()
        series = [s for s in self.series if internal_mode or not s.internal_only]
        out: Dict[str, Any] = {
            "feature_id": self.feature_id,
            "title": self.title,
            "audience": self.audience,
            "internal_mode": bool(internal_mode),
            "summary": self.summary,
            "series": [s.to_dict() for s in series],
            "footnote": self.footnote.to_dict() if self.footnote else None,
            "flags": [f.to_dict() for f in self.flags],
            "reconciliations": [r.to_dict() for r in self.reconciliations],
            "reconciled": self.reconciled,
            "meta": dict(self.meta),
        }
        if internal_mode:
            out["assumptions"] = [a.to_dict() for a in self.assumptions]
        return out


def safe_div(num: float, den: float, default: float = 0.0) -> float:
    """Division that returns ``default`` on a zero or non-finite denominator."""
    if den is None or not math.isfinite(den) or den == 0:
        return default
    val = num / den
    return val if math.isfinite(val) else default
