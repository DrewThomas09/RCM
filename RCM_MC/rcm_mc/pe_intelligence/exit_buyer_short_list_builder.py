"""Exit buyer short list — named candidates for exit.

Partner statement: "An exit thesis isn't a multiple
— it's a named list of buyers. Who are the 5-10
strategic acquirers, sponsor platforms, or IPO
comps? If you can't name them, the exit is
hypothetical. I'll trade multiple points for a
credible bidder list."

Distinct from:
- `buyer_type_fit_analyzer` — 8 buyer type profiles.
- `exit_buyer_view_mirror` — first-person buyer IC.
- `exit_alternative_comparator` — 5 exit paths.

This module builds a **ranked named-buyer short
list** based on subsector, asset size, and
strategic/financial buyer profiles.

### Buyer catalog (by subsector)

Named plausible acquirers — strategic, sponsor
platforms with healthcare presence, and public
comparables that would IPO.

### Output

Ranked list of 5-10 candidates with rationale per
buyer + bucket (strategic / sponsor / public-comp-
ipo).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# Per-subsector buyer catalog with (name, bucket,
# min_target_ev_m, note)
SUBSECTOR_BUYERS: Dict[str, List[Dict[str, Any]]] = {
    "dental_dso": [
        {"name": "Heartland Dental",
         "bucket": "sponsor_platform",
         "min_target_ev_m": 100,
         "note": "KKR-backed; largest DSO by practice count."},
        {"name": "Smile Brands",
         "bucket": "sponsor_platform",
         "min_target_ev_m": 80,
         "note": "Gryphon-backed; add-on appetite."},
        {"name": "Aspen Dental",
         "bucket": "sponsor_platform",
         "min_target_ev_m": 150,
         "note": "Ares-backed; mid-market focused."},
        {"name": "Pacific Dental Services",
         "bucket": "strategic",
         "min_target_ev_m": 60,
         "note": "Founder-led but acquisitive."},
    ],
    "physician_practice_multi_specialty": [
        {"name": "OptumHealth",
         "bucket": "strategic",
         "min_target_ev_m": 300,
         "note": "UnitedHealth-owned; aggressive PG acquirer."},
        {"name": "Amedisys (HUM)",
         "bucket": "strategic",
         "min_target_ev_m": 200,
         "note": "Humana-owned post-merger; scale appetite."},
        {"name": "VillageMD",
         "bucket": "sponsor_platform",
         "min_target_ev_m": 150,
         "note": "Walgreens-anchored; PCP-focused."},
        {"name": "Oak Street Health",
         "bucket": "strategic",
         "min_target_ev_m": 200,
         "note": "CVS-owned; Medicare risk focus."},
        {"name": "PE sponsor platforms",
         "bucket": "sponsor_platform",
         "min_target_ev_m": 75,
         "note": "Various — TPG, New Mountain, Leonard Green all active."},
    ],
    "asc": [
        {"name": "USPI (Tenet)",
         "bucket": "strategic",
         "min_target_ev_m": 100,
         "note": "Public; largest ASC chain; acquisitive."},
        {"name": "SCA (Optum)",
         "bucket": "strategic",
         "min_target_ev_m": 80,
         "note": "UnitedHealth-owned; scale strategy."},
        {"name": "HCA Healthcare",
         "bucket": "strategic",
         "min_target_ev_m": 200,
         "note": "Public; geographic fit drives."},
        {"name": "Surgery Partners",
         "bucket": "strategic",
         "min_target_ev_m": 50,
         "note": "Public; Bain-backed; mid-market."},
    ],
    "behavioral": [
        {"name": "Acadia Healthcare",
         "bucket": "strategic",
         "min_target_ev_m": 150,
         "note": "Public; largest behavioral platform."},
        {"name": "Universal Health Services",
         "bucket": "strategic",
         "min_target_ev_m": 100,
         "note": "Public; behavioral + acute."},
        {"name": "LifeStance Health",
         "bucket": "public_comp_ipo",
         "min_target_ev_m": 50,
         "note": "Public; outpatient focus."},
        {"name": "Summit Behavioral",
         "bucket": "sponsor_platform",
         "min_target_ev_m": 60,
         "note": "FFL-backed addiction platform."},
    ],
    "home_health": [
        {"name": "Amedisys",
         "bucket": "strategic",
         "min_target_ev_m": 100,
         "note": "Humana-owned; scale strategy."},
        {"name": "LHC Group",
         "bucket": "strategic",
         "min_target_ev_m": 100,
         "note": "Optum-owned."},
        {"name": "Encompass Health",
         "bucket": "strategic",
         "min_target_ev_m": 150,
         "note": "Public; IRF + home health."},
        {"name": "Enhabit",
         "bucket": "public_comp_ipo",
         "min_target_ev_m": 75,
         "note": "Public spin-off; acquisitive."},
    ],
    "ophthalmology": [
        {"name": "EyeCare Partners",
         "bucket": "sponsor_platform",
         "min_target_ev_m": 75,
         "note": "Partners Group; largest ophtho platform."},
        {"name": "US Eye",
         "bucket": "sponsor_platform",
         "min_target_ev_m": 60,
         "note": "Waud-backed; Southeast focus."},
        {"name": "AEG Vision",
         "bucket": "sponsor_platform",
         "min_target_ev_m": 50,
         "note": "Platinum Equity-backed."},
        {"name": "Acuity Eyecare",
         "bucket": "sponsor_platform",
         "min_target_ev_m": 40,
         "note": "Riata Capital-backed."},
    ],
    "dermatology": [
        {"name": "Advanced Dermatology & Cosmetic Surgery",
         "bucket": "sponsor_platform",
         "min_target_ev_m": 75,
         "note": "Harvest-backed."},
        {"name": "Forefront Dermatology",
         "bucket": "sponsor_platform",
         "min_target_ev_m": 60,
         "note": "OMERS-backed."},
        {"name": "Epiphany Dermatology",
         "bucket": "sponsor_platform",
         "min_target_ev_m": 50,
         "note": "BC Partners."},
        {"name": "U.S. Dermatology Partners",
         "bucket": "sponsor_platform",
         "min_target_ev_m": 60,
         "note": "ABRY-backed."},
    ],
}


@dataclass
class ExitBuyerShortListInputs:
    subsector: str = "dental_dso"
    expected_exit_ev_m: float = 500.0


@dataclass
class NamedBuyer:
    name: str
    bucket: str
    fits_size: bool
    min_target_ev_m: float
    note: str


@dataclass
class ExitBuyerShortListReport:
    subsector: str = ""
    in_catalog: bool = False
    buyers: List[NamedBuyer] = field(default_factory=list)
    strategic_count: int = 0
    sponsor_count: int = 0
    public_count: int = 0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subsector": self.subsector,
            "in_catalog": self.in_catalog,
            "buyers": [
                {"name": b.name,
                 "bucket": b.bucket,
                 "fits_size": b.fits_size,
                 "min_target_ev_m": b.min_target_ev_m,
                 "note": b.note}
                for b in self.buyers
            ],
            "strategic_count": self.strategic_count,
            "sponsor_count": self.sponsor_count,
            "public_count": self.public_count,
            "partner_note": self.partner_note,
        }


def build_exit_buyer_short_list(
    inputs: ExitBuyerShortListInputs,
) -> ExitBuyerShortListReport:
    catalog = SUBSECTOR_BUYERS.get(inputs.subsector)
    if catalog is None:
        return ExitBuyerShortListReport(
            subsector=inputs.subsector,
            in_catalog=False,
            partner_note=(
                f"Subsector '{inputs.subsector}' not in "
                "buyer catalog. Build named bidder list "
                "via industry specialist / banker."
            ),
        )

    buyers: List[NamedBuyer] = []
    for entry in catalog:
        fits = inputs.expected_exit_ev_m >= entry["min_target_ev_m"]
        buyers.append(NamedBuyer(
            name=entry["name"],
            bucket=entry["bucket"],
            fits_size=fits,
            min_target_ev_m=float(entry["min_target_ev_m"]),
            note=entry["note"],
        ))

    buyers.sort(
        key=lambda b: (not b.fits_size,
                       b.min_target_ev_m),
    )

    fit_buyers = [b for b in buyers if b.fits_size]
    strategic = sum(
        1 for b in fit_buyers
        if b.bucket == "strategic")
    sponsor = sum(
        1 for b in fit_buyers
        if b.bucket == "sponsor_platform")
    public = sum(
        1 for b in fit_buyers
        if b.bucket == "public_comp_ipo")

    if len(fit_buyers) >= 5:
        note = (
            f"{len(fit_buyers)} named size-fit buyers "
            f"(strategic: {strategic}, sponsor: "
            f"{sponsor}, public: {public}). Credible "
            "bidder list — exit thesis holds."
        )
    elif len(fit_buyers) >= 3:
        note = (
            f"{len(fit_buyers)} size-fit buyers — thin "
            "bidder field. Run competitive process but "
            "expect fewer bids; downside is real."
        )
    else:
        note = (
            f"Only {len(fit_buyers)} size-fit buyer(s) "
            "in catalog — exit auction is thin. "
            "Consider continuation vehicle or single-"
            "bidder sale as alternatives."
        )

    return ExitBuyerShortListReport(
        subsector=inputs.subsector,
        in_catalog=True,
        buyers=buyers,
        strategic_count=strategic,
        sponsor_count=sponsor,
        public_count=public,
        partner_note=note,
    )


def render_exit_buyer_short_list_markdown(
    r: ExitBuyerShortListReport,
) -> str:
    if not r.in_catalog:
        return (
            "# Exit buyer short list\n\n"
            f"_{r.partner_note}_\n"
        )
    lines = [
        "# Exit buyer short list",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Subsector: {r.subsector}",
        f"- Strategic: {r.strategic_count}, "
        f"Sponsor: {r.sponsor_count}, "
        f"Public: {r.public_count}",
        "",
        "| Buyer | Bucket | Fits size | Min EV $M | Note |",
        "|---|---|---|---|---|",
    ]
    for b in r.buyers:
        lines.append(
            f"| {b.name} | {b.bucket} | "
            f"{'✓' if b.fits_size else '—'} | "
            f"${b.min_target_ev_m:.0f} | {b.note} |"
        )
    return "\n".join(lines)
