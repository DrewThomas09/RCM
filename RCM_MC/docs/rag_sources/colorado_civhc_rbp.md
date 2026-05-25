# Colorado CIVHC — Medicare Reference-Based Pricing (RBP)

**Source:** CIVHC (Center for Improving Value in Health Care), the Colorado
All-Payer Claims Database administrator. Public-use file (FY2026).
**Geography:** Colorado (provider-level, by county + DOI region).
**Years:** 2021–2024.
**Fields:** organization_name, claim_type, county, urban/rural, DOI region,
CAH/AMB flags, **hospital % of Medicare**, claims, URF % of Medicare, payer
min/median/max.
**Powers:** `/ref-pricing` (LIVE provider table), `/payer-stress` (CONTEXTUAL
payer-pressure median).

**What it indicates:** how much commercial payers reimburse a Colorado provider
relative to Medicare (e.g. 2.5x = 250% of Medicare). Higher = more expensive vs
Medicare / more commercial leverage.

**What it does NOT prove:** it is not a specific contract rate, not the
provider's margin, and not national. 216 CO providers only.

**Diligence use cases:** benchmark a Colorado target hospital/ASC's
commercial-to-Medicare position; identify high- vs low-priced providers in a
county/region.

**Caveats:** Colorado-only — do not generalize nationally. ~1% missing on
payer fields (shown as "—", never 0). Provider-level but resolvable to a CCN
only by name match (not yet wired).

**Suggested questions:**
- "What does a Colorado provider's % of Medicare indicate?"
- "Is this provider-specific or market context?" (provider-specific for RBP)
- "Can I generalize Colorado RBP nationally?" (no)
- "What data would make this investment-grade for a specific deal?"
