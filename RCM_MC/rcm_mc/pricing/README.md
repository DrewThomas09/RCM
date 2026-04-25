# pricing/

Hospital and payer price-transparency data ingestion. Reads CMS Hospital MRF (Machine-Readable File) and payer-side Transparency-in-Coverage MRFs.

| File | Purpose |
|------|---------|
| `hospital_mrf.py` | CY2024+ Hospital MRF schema parser — `gross_charge`, `discounted_cash`, `negotiated_dollar`, `negotiated_percentage`, `negotiated_algorithm` |
| `payer_mrf.py` | Payer Transparency-in-Coverage MRF parser — in-network rates, allowed amounts, plan tier |
| `payer_mrf_streaming.py` | Streaming parser for the massive payer MRFs (often 100GB+ uncompressed). Reads one rate row at a time |
| `normalize.py` | Cross-source normalization to a common `negotiated_rate` schema |
| `nppes.py` | NPPES (NPI registry) loader for provider-side joins |
| `nppes_incremental.py` | Weekly NPPES delta loader — only pulls newly-changed providers |
| `reads.py` | Convenience read helpers used by `ml/contract_strength.py` |

## Why streaming matters

The largest payer (UnitedHealthcare) has published Transparency-in-Coverage MRFs that approach **terabytes** uncompressed. `payer_mrf_streaming.py` uses a one-row-at-a-time parser so memory stays bounded regardless of file size.

## Used by

- `ml/contract_strength.py` (the contract-strength estimator)
- `diligence/payer_stress/` (payer-side rate-shock priors)
- `analytics/pricing_dashboard.py` (the pricing-comparison UI)
