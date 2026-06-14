# NPPES CDD Analytics — Methodology & Caveats

Analyst-facing reference for the commercial-diligence signals this connector
derives from the NPPES provider universe. Every metric below is computed
read-only over the canonical tables (`dim_provider`,
`bridge_provider_taxonomy`, `dim_taxonomy`, `dim_provider_address`,
`bridge_provider_affiliation`). Read this before quoting a number in a memo —
each signal has a defined meaning and a known limitation.

## Geography & market definition
- **Market** = (practice-location geography × primary-taxonomy
  classification). Geography defaults to `state`; `city`/`zip5` are available
  now, and `county` (FIPS) activates automatically once the Census geocoder
  populates `dim_provider_address.fips_county` — no metric logic changes.
- "Provider" = an NPI with a primary practice address. Deactivated NPIs are
  excluded from market sizing/concentration but retained for roster analysis.

## Metrics

### TAM — `tam_by_taxonomy_geography`
Provider count by market. The sizing spine. **Caveat:** counts providers, not
revenue or capacity; a market's provider count is a proxy for addressable
scale, not billings.

### Concentration (HHI) — `market_concentration`
HHI = Σ(firm share)² × 10000, where a "firm" is the organization a provider
is affiliated to (highest-confidence link) or a singleton if independent.
Share = the firm's captive-provider count ÷ market providers. Banded on the
DOJ/FTC Horizontal Merger Guidelines (<1500 unconcentrated · 1500–2500
moderate · >2500 highly concentrated). **Caveat:** provider share is a
revenue proxy; a few large-billing orgs can be under-weighted vs. many small
ones. Affiliation is heuristic (see below), so HHI inherits that uncertainty.

### Fragmentation / roll-up runway — `fragmentation_scan`
`rollup_score = independent_share × (1 − HHI/10000) × min(firm_count/20, 1)`,
0–100. High = fragmented market with consolidation headroom. **Caveat:** a
heuristic composite, not a financial model; use it to rank markets, not to
size returns.

### Growth — `enumeration_trend`
New NPI enumerations vs. deactivations per year, with net + cumulative.
Year extraction tolerates both NPPES `MM/DD/YYYY` and API `YYYY-MM-DD`.
**Caveat:** enumeration date ≈ when the NPI was issued, a lagged/imperfect
proxy for when a provider began practicing; reflects registration, not
utilization.

### Referral hubs — `referral_hubs`
Practice addresses where many distinct providers operate, with the
individual/org split. Co-location density approximates referral / captive-
volume concentration. **Caveat:** co-location ≠ referral; a shared medical-
office building inflates counts. Address is normalized but not geocoded.

### Roster integrity — `roster_integrity`
Deactivation / reactivation rates, the terminated-provider risk to a target's
revenue base. **Caveat:** NPPES deactivation lags real-world termination and
does not capture provider *departures* that keep the NPI active.

### Platforms — `affiliation_footprint`
Organizations ranked by captive (affiliated) provider count above a
confidence floor — a captive-volume / platform-scale proxy.

### Roll-up targets — `rollup_targets`
Sub-scale active Type-2 orgs (few captive providers) in the target market —
add-on candidates.

### Health systems — `systems.health_systems`
Type-2 orgs clustered into multi-site systems via shared distinctive
brand/surname name token + a corroborating signal (second shared token or
shared state). **Caveat:** common surnames can over-merge unrelated solo
practices in one state; the `cohesion` score and member list expose this.
Heuristic — confirm material systems against ground truth.

### Target screen — `screen.screen_targets`
Ranks orgs into a platform/add-on acquisition long-list:
`score = 0.35·market_growth + 0.35·fragmentation + 0.30·scale_fit`
(weights overridable; `scale_fit` inverts between theses). Each candidate
carries the component breakdown + rationale. **Caveat:** a screening
heuristic to prioritize diligence, not an investment recommendation.

## Affiliation heuristic (underpins HHI, platforms, systems, screen)
`bridge_provider_affiliation` links a Type-1 individual to a Type-2 org on
shared normalized practice address (+ surname/legal-name overlap), with a
confidence in [0,1] and stored evidence. It approximates employment/billing
relationships that NPPES does not state explicitly. Treat affiliation-derived
metrics as directional. Full method in `DECISIONS.md` D6 (individuals→orgs)
and D13 (orgs→systems).

## Reproduce
```bash
python -m connectors.nppes.cli build --db nppes.db            # load universe
python -m connectors.nppes.cli cdd report --db nppes.db --geo TX   # one brief
python -m connectors.nppes.cli profile --db nppes.db          # data-room view
```
