# reputational/

**Reputational + ESG risk** (Gap 12) — state AG enforcement heatmap, bankruptcy-contagion cluster detector, media risk scan.

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring — 3 submodules. |
| `state_ag_heatmap.py` | **State AG enforcement heatmap.** State AGs with active PE-healthcare review regimes + recent enforcement. Refresh quarterly against AG press releases. |
| `bankruptcy_contagion.py` | **Same-specialty / same-region / same-landlord cluster detector.** Target's signature × known-bankruptcy corpus → cluster-risk flag ("3 nearby bankruptcies in specialty Y, landlord Z"). |
| `media_risk_scan.py` | **Regex keyword scanner** over caller-supplied archived coverage (ProPublica, STAT, NYT, Kaiser Health News, Fierce Healthcare, Modern Healthcare, PESP). Target-name + risk-keyword hits. |

## Why this matters

### State AG exposure

CA AB 3129 (2023) requires notice to AG before PE-backed healthcare transactions above size thresholds. MA, IL, NY, OR, and others have similar or pending regimes. **Deal delay risk** is the primary concern — 90-180 days of AG review is a closing disruption. `state_ag_heatmap.py` maps target's footprint → delay exposure.

### Bankruptcy contagion

When 3 hospitals in the same MSA with the same landlord (MPT) go bankrupt, the 4th hospital in that cluster is statistically more likely to follow. `bankruptcy_contagion.py` pattern-matches target against known-failure clusters and flags proximate risk.

### Media risk

PE healthcare is a politically-charged space. Target names appearing in ProPublica investigations, congressional hearings, Kaiser Health News exposés, or Private Equity Stakeholder Project (PESP) reports is material reputational risk for the sponsor. `media_risk_scan.py` surfaces hits.

## Where it plugs in

- **Thesis Pipeline** — runs when media corpus + AG data supplied
- **Bear Case** — media hits feed PATTERN theme; state AG exposure feeds REGULATORY theme
- **LP Pitch** (pe_intelligence/lp_pitch.py) — reputational risk filters the LP-facing framing

## Data sources

- Cadence: state AG heatmap refreshed quarterly; media corpus caller-supplied or CI-scraped; bankruptcy corpus refreshed when new filings publish
- All sources public

## Tests

`tests/test_reputational*.py` — AG state lookup + cluster detection + regex keyword coverage.
