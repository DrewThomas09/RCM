"""DataPoint — the atomic unit of provenance.

Every scalar surfaced by the platform is backed by a DataPoint. The
DataPoint answers four partner-facing questions:

- **What is it?**       ``metric_name`` + ``value``
- **Where'd it come from?**  ``source`` + ``source_detail``
- **How much do we trust it?**  ``confidence``
- **What fed into it?**  ``upstream`` (another list of DataPoints)

Design notes:

- DataPoints are immutable once created. If a downstream calculation
  needs to "refine" an estimate, record a new DataPoint — the old one
  stays in the audit trail.
- ``upstream`` is a list of other DataPoints that ARE THE INPUTS.
  Walking upstream gives the full dependency tree.
- ``value`` is ``float`` by design. Categorical / string metrics
  belong in a different system (deal tags, notes).
- ``as_of_date`` separates "when the underlying fact was true" from
  "when we ran the calculation." A HCRIS row loaded today for 2022
  has ``as_of_date = 2022-12-31`` (the HCRIS fiscal year end), not
  ``date.today()``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Dict, List, Optional


class Source(str, Enum):
    """Provenance source types. The enum values are the strings
    serialized into the audit log — so do not rename without a
    migration."""

    #: User explicitly entered this value (via UI form, config yaml, CLI).
    USER_INPUT = "USER_INPUT"

    #: Pulled from the bundled HCRIS dataset.
    HCRIS = "HCRIS"

    #: Pulled from IRS Form 990 data.
    IRS990 = "IRS990"

    #: Output of a regression model trained on comparable deals.
    REGRESSION_PREDICTED = "REGRESSION_PREDICTED"

    #: A peer-group median / percentile from external benchmark data.
    BENCHMARK_MEDIAN = "BENCHMARK_MEDIAN"

    #: A Monte Carlo simulation percentile (p50/p90/etc.).
    MONTE_CARLO_P50 = "MONTE_CARLO_P50"

    #: A deterministic calculation over other DataPoints (e.g. EBITDA
    #: bridge, IRR). Upstream list carries the inputs.
    CALCULATED = "CALCULATED"


@dataclass(frozen=True)
class DataPoint:
    """One provenance-tagged scalar.

    Parameters
    ----------
    value
        The numeric value being recorded.
    metric_name
        Canonical name — e.g. ``"denial_rate"``, ``"days_in_ar"``,
        ``"weighted_moic"``. Use snake_case, no spaces.
    source
        One of the :class:`Source` enum values.
    source_detail
        Human-readable string describing exactly where this came
        from. E.g. ``"HCRIS 2022 CCN 450321"``,
        ``"Linear regression from 47 comparable hospitals, R²=0.84"``.
    confidence
        Subjective 0-1 confidence. User inputs default to 1.0;
        regressions use their R²-like score; Monte Carlo p50 uses
        something like 1 - stddev/|value|.
    as_of_date
        The real-world date the underlying fact was true. NOT the
        date the calculation ran.
    upstream
        DataPoints that fed into this one. Empty for leaf sources
        (HCRIS rows, user inputs). Populated for CALCULATED and
        REGRESSION_PREDICTED.
    """

    value: float
    metric_name: str
    source: Source
    source_detail: str = ""
    confidence: float = 1.0
    as_of_date: date = field(default_factory=date.today)
    upstream: List["DataPoint"] = field(default_factory=list)

    # ---- Validation & invariants ----

    def __post_init__(self) -> None:
        # dataclass(frozen=True) wraps __setattr__; use object.__setattr__
        if not isinstance(self.metric_name, str) or not self.metric_name:
            raise ValueError("metric_name must be a non-empty string")
        if not isinstance(self.source, Source):
            # Accept string-valued enums passed in by callers for ergonomics
            try:
                object.__setattr__(self, "source", Source(self.source))
            except Exception as exc:  # noqa: BLE001
                raise ValueError(
                    f"source must be a Source enum, got {self.source!r}"
                ) from exc
        if not (0.0 <= float(self.confidence) <= 1.0):
            raise ValueError(
                f"confidence must be in [0, 1], got {self.confidence}"
            )
        # Coerce value to float for consistent downstream handling
        try:
            object.__setattr__(self, "value", float(self.value))
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"value must be numeric, got {self.value!r}"
            ) from exc

    # ---- Serialization ----

    def to_dict(self) -> Dict[str, Any]:
        """JSON-safe dict. ``upstream`` is serialized by metric_name
        references — the full DataPoint objects live in the
        ProvenanceRegistry, not in each parent."""
        return {
            "metric_name": self.metric_name,
            "value": self.value,
            "source": self.source.value,
            "source_detail": self.source_detail,
            "confidence": self.confidence,
            "as_of_date": self.as_of_date.isoformat(),
            "upstream": [u.metric_name for u in self.upstream],
        }

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
        lookup: Optional[Dict[str, "DataPoint"]] = None,
    ) -> "DataPoint":
        """Inverse of ``to_dict``. ``lookup`` maps metric_name → full
        DataPoint so we can rehydrate ``upstream`` references. When
        ``lookup`` is missing a name, that upstream entry is skipped
        (graceful for partial loads)."""
        lookup = lookup or {}
        upstream: List[DataPoint] = []
        for name in data.get("upstream", []):
            dp = lookup.get(name)
            if dp is not None:
                upstream.append(dp)
        as_of_str = data.get("as_of_date") or date.today().isoformat()
        return cls(
            value=float(data["value"]),
            metric_name=str(data["metric_name"]),
            source=Source(data["source"]),
            source_detail=str(data.get("source_detail") or ""),
            confidence=float(data.get("confidence") or 1.0),
            as_of_date=date.fromisoformat(as_of_str),
            upstream=upstream,
        )
