# RAG source — CMS Provider X-Ray design pattern (generalizing HCRIS X-Ray)

CMS Provider X-Ray (`/diligence/xray`) is the universal diligence scanner — it
reuses the **HCRIS X-Ray design system** (the shared `xray_kit`: navy ribbons,
paper cards, green-dash eyebrow, peer-band visual, sharp 1px-rule corners) so
it reads as HCRIS X-Ray *generalized across verticals*, not a generic sector
table.

**Shared structure.** Identity row → diligence signal strip → benchmark table
→ market context → risk indicators → suggested questions → evidence &
limitations. Section headers are kit ribbons; the page is scoped in `.xr` so
the kit tokens resolve.

**Per-vertical reality (render only what the data supports).** Verticals
differ, so the report shows only real sections and degrades honestly:
- not every vertical has revenue, HCRIS metrics, payer mix, or trend data;
- Home Health uses **city** (no county) for locality;
- small sectors (IRF ~1,200, LTCH ~320) carry **sample-size caveats** and
  suppress percentile/z-score below n=5;
- non-HCRIS verticals **never** fake HCRIS-specific financial sections.

**Reuse, don't rebuild.** Benchmarks come from the cross-sector framework
(#619) and the investable-evidence layer (#620); the resolver detects the
vertical (and surfaces a resolver when a CCN — e.g. a hospital-based IRF/LTCH
unit — maps to more than one). Hospital/HCRIS resolves to identity + a pointer
to the HCRIS-powered hospital profile rather than fabricated post-acute
benchmarks.

**HCRIS X-Ray vs CMS Provider X-Ray.** HCRIS X-Ray = hospital cost-report
financials (beds/revenue/margin, P25–P75 peer band). CMS Provider X-Ray = CMS
**quality** measures across post-acute verticals (percentile peer sets, risk
indicators). Same look, different data; neither claims commercial revenue
(except HCRIS hospital fields), market share, causation, or a recommendation.

**Risk indicators are not forecasts.** They are transparent, rule-based
current-state signals (each shows its components); true prediction is
panel-data-blocked (single-snapshot data) — see the prediction-readiness audit.
