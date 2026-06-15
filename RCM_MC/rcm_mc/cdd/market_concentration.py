"""NEW-25 Market concentration overlay.

The "who controls each vertical" layer: a chart-ready set of market-structure
headlines so any vertical chart can flag its concentration (the dialysis tile
reads "77 percent two-firm share"). Dialysis is the most concentrated of all
health care sectors; the big-three PBMs clear 80 percent of prescription claims
and the big-three distributors over 90 percent of drug distribution. Hospital
systems sit at the other end, where the top two chains hold about 5 percent
combined, which is what makes dialysis anomalous.

Each row carries the firm count behind the share, its source and vintage, and an
estimate flag for the industry-estimate rows that lack peer-reviewed rigor.

Statistical and deterministic. No LLM on any path.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

from .exhibit import Exhibit, Flag, Footnote, Reconciliation, Series
from .registry import CddFeature, register

FEATURE_ID = "NEW-25"

# A top-firm share at or above this earns the highly-concentrated flag.
HIGH_CONCENTRATION_PCT = 70.0


@dataclass(frozen=True)
class ConcentrationRow:
    """One vertical's market-structure headline.

    ``share_pct`` is the share held by the named ``firms`` (a count). ``est_verify``
    marks an industry estimate that lacks the rigor of the peer-reviewed rows.
    """

    vertical: str
    share_pct: float
    firms: int
    headline: str
    source: str
    vintage: str
    est_verify: bool = False

    def validate(self) -> "ConcentrationRow":
        if not 0.0 <= self.share_pct <= 100.0:
            raise ValueError(f"{self.vertical}: share must be 0 to 100 percent")
        if self.firms < 1:
            raise ValueError(f"{self.vertical}: firm count must be at least one")
        return self


CONCENTRATION: List[ConcentrationRow] = [
    ConcentrationRow("Dialysis", 77.1, 2,
                     "DaVita and Fresenius hold 77.1 percent of US facilities",
                     "JAMA Health Forum 2025 (Xia et al.)", "2019"),
    ConcentrationRow("Drug wholesale distribution", 95.0, 3,
                     "McKesson, Cencora, and Cardinal control about 95 percent",
                     "IntuitionLabs, Drug Channels", "2024"),
    ConcentrationRow("Pharmacy benefit managers", 80.0, 3,
                     "the big-three PBMs processed 80 percent of prescription claims",
                     "Drug Channels Institute", "2024"),
    ConcentrationRow("Group purchasing organizations", 75.0, 3,
                     "the top-three GPOs run about 75 percent of purchasing volume",
                     "Industry estimate", "2025", est_verify=True),
    ConcentrationRow("Medicare Advantage enrollment", 50.0, 2,
                     "Medicare Advantage covers over half of eligible beneficiaries",
                     "KFF, MedPAC", "2026"),
    ConcentrationRow("Hospital electronic health records", 40.0, 1,
                     "Epic holds a dominant share of acute-care beds",
                     "Industry estimate", "2025", est_verify=True),
    ConcentrationRow("Hospital systems", 5.0, 2,
                     "the two largest hospital chains hold about 5 percent combined",
                     "JAMA Health Forum 2025", "2025"),
]


def market_concentration(
    rows: Optional[Sequence[ConcentrationRow]] = None,
    *,
    source: str = "Market-structure concentration benchmarks",
    vintage: str = "2024/26",
    audience: str = "both",
) -> Exhibit:
    """Build the market-structure concentration overlay."""
    table = list(rows) if rows is not None else list(CONCENTRATION)
    if not table:
        raise ValueError("market_concentration requires at least one row")
    for r in table:
        r.validate()

    points: List[Dict[str, Any]] = []
    for r in sorted(table, key=lambda x: x.share_pct, reverse=True):
        points.append({
            "label": r.vertical,
            "value": r.share_pct,
            "firms": r.firms,
            "headline": r.headline,
            "est_verify": r.est_verify,
            "source": r.source,
            "vintage": r.vintage,
        })

    concentrated = [p for p in points if p["value"] >= HIGH_CONCENTRATION_PCT]
    flags: List[Flag] = []
    for p in concentrated:
        flags.append(Flag(
            code="highly_concentrated",
            severity="warn",
            message=(
                f"{p['label']} is highly concentrated: {p['firms']} firms hold "
                f"{p['value']:.1f} percent."
            ),
            source=p["source"],
        ))
    n_estimates = sum(1 for r in table if r.est_verify)
    if n_estimates:
        flags.append(Flag(
            code="estimates_present",
            severity="info",
            message=(
                f"{n_estimates} rows are industry estimates without peer-reviewed "
                "rigor. Verify before citing as a point."
            ),
            source=source,
        ))

    # Reconciliation: every share is a valid percentage, and the most
    # concentrated charted row equals the maximum share in the table.
    n_valid = sum(1 for r in table if 0.0 <= r.share_pct <= 100.0)
    reconciliations = [
        Reconciliation(
            identity="every share is between 0 and 100 percent",
            lhs=n_valid,
            rhs=len(table),
            tolerance=1e-9,
        ),
        Reconciliation(
            identity="top charted share equals the maximum share",
            lhs=points[0]["value"],
            rhs=max(r.share_pct for r in table),
            tolerance=1e-9,
        ),
    ]

    series = [Series(name="Top-firm share by vertical", kind="bar", points=points)]

    footnote = Footnote(
        source=source,
        vintage=vintage,
        assumptions=[
            "Share is the percent held by the named top firms in each vertical.",
            "Dialysis 77.1 percent is the 2019 peer-reviewed figure; industry framing cites about 80 percent.",
            "Industry-estimate rows are flagged and should be verified.",
        ],
    )

    ex = Exhibit(
        feature_id=FEATURE_ID,
        title="Market concentration by vertical",
        audience=audience,
        series=series,
        footnote=footnote,
        flags=flags,
        reconciliations=reconciliations,
        summary=(
            f"{len(table)} verticals. {len(concentrated)} are highly concentrated, "
            f"led by {points[0]['label']} at {points[0]['value']:.1f} percent."
        ),
        meta={
            "n_rows": len(table),
            "n_highly_concentrated": len(concentrated),
            "n_estimates": n_estimates,
            "top_share_vertical": points[0]["label"],
            "table": points,
        },
    )
    return ex.validate()


def _demo() -> Exhibit:
    return market_concentration(
        source="Market-structure concentration benchmarks",
        vintage="2024/26",
    )


register(
    CddFeature(
        feature_id=FEATURE_ID,
        title="Market concentration overlay",
        audience="both",
        demo=_demo,
    )
)
