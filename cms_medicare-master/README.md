## Center for Medicare Services Data

The Center for Medicare Services (CMS) has provided public datasets for many different aspects of healthcare, in an attempt to make the U.S. healthcare system more transparent.  The most recent healthcare provider data from 2014 is available in the [Medicare Provider Utilization and Payment Data: Physician and Other Supplier Public Use File](https://www.cms.gov/Research-Statistics-Data-and-Systems/Statistics-Trends-and-Reports/Medicare-Provider-Charge-Data/Physician-and-Other-Supplier2014.html).  

The file contains annual data from over 980,000 physicians and other healthcare providers, including: 
+ provider type
+ provider location
+ total cost of submitted claims
+ total Medicare payment amount 
+ total number of services (doctors visits or procedures)
+ total number of beneficiaries (patients)
+ some drug costs (full drug data is in other datasets)
+ provider and patient gender
+ summary of anonymized beneficiary information

### Preliminary Analysis
To get an idea of actual health care costs for consumers, we did a preliminary analysis of the total Medicare payment amount per service and per beneficiary.  Typically, a beneficiary has supplemental insurance to cover the remainder of the claims, which often pays 20% of the approved Medicare payment.  Extra costs are typically fixed at a fraction of the approved payment.  We calculated two extra columns:
+ payment per service = log10 ( total Medicare payment amount / total number of services )
+ payment per person = log10 ( total Medicare payment amount / total number of beneficiaries )

We find a log scale gives data closer to a normal distribution, and use log base 10 for numerical convenience.  Grouping the payments by the 91 provider types in the data, we find a lot of variation for each provider type.  Histograms for all provider types are given in __cms_hist_plots/__.  A histogram of some specialties is shown below.  

<img src="https://github.com/bfetler/cms_medicare/blob/master/cms_hist_plots/hist_pay_per_person_group7.png" alt="example histogram per person" />

A good number of provider types have well-defined costs that follow a log normal distribution, while others have a lot of variation.  Some categories have very few providers, for whom it is difficult to do statistics.  Nonetheless, we find some trends by provider type.

#### Payment Per Service
Of the top dozen provider types by median payment per service, nine are for Surgery, with the most expensive being Ambulatory Surgery, and three are for Radiation or Oncology.  A summary is given in the table and figure below.  

<table>
<th>Provider Type</th><th>Payment Per Service (USD)</th>
<tr><td>Ambulatory Surgical Center</td><td>457</td></tr>
<tr><td>Cardiac Surgery</td><td>353</td></tr>
<tr><td>Thoracic Surgery</td><td>262</td></tr>
<tr><td>Neurosurgery</td><td>220</td></tr>
<tr><td>Surgical Oncology</td><td>167</td></tr>
<tr><td>Plastic and Reconstructive Surgery</td><td>164</td></tr>
<tr><td>Radiation Therapy</td><td>155</td></tr>
<tr><td>Colorectal Surgery</td><td>152</td></tr>
<tr><td>General Surgery</td><td>145</td></tr>
<tr><td>Anesthesiology</td><td>131</td></tr>
<tr><td>Vascular Surgery</td><td>125</td></tr>
<tr><td>Gynecological/Oncology</td><td>118</td></tr>
</table>

<img src="https://github.com/bfetler/cms_medicare/blob/master/cms_cost_plots/bar_pay_per_service.png" alt="bar plot per service" />

#### Payment Per Beneficiary
Of the top dozen provider types by median payment per beneficiary, two are for Radiation or Oncology, with the most expensive being Radiation Therapy, and five are for Surgery, as shown in the table and figure below.  

<table>
<th>Provider Type</th><th>Payment Per Person (USD)</th>
<tr><td>Radiation Therapy</td><td>7039</td></tr>
<tr><td>Cardiac Surgery</td><td>934</td></tr>
<tr><td>Ambulatory Surgical Center</td><td>893</td></tr>
<tr><td>Psychologist (billing independently)</td><td>867</td></tr>
<tr><td>Radiation Oncology</td><td>830</td></tr>
<tr><td>Thoracic Surgery</td><td>689</td></tr>
<tr><td>Ambulance Service Supplier</td><td>580</td></tr>
<tr><td>Clinical Psychologist</td><td>571</td></tr>
<tr><td>Neurosurgery</td><td>549</td></tr>
<tr><td>Physical Therapist</td><td>529</td></tr>
<tr><td>Plastic and Reconstructive Surgery</td><td>500</td></tr>
<tr><td>Speech Language Pathologist</td><td>463</td></tr>
</table>

<img src="https://github.com/bfetler/cms_medicare/blob/master/cms_cost_plots/bar_pay_per_person.png" alt="bar plot per person" />

For consumers, the payment per person is probably of most interest, since a patient is typically prescribed a series of treatments, not just a single service.

#### Medicare Total Beneficiaries and Payment

The total number of medicare beneficiaries by provider type is shown below.  This gives some idea of the most and least popular care options provided by Medicare.  Diagnostic Radiology, Internal Medicine, Clinical Laboratory and Cardiology are in the top five most popular.

<img src="https://github.com/bfetler/cms_medicare/blob/master/cms_pop_plots/bar_total_unique_benes_sum.png" alt="bar plot total beneficiaries" />

The total medicare payment by provider type is shown below.  This gives some idea of the most and least expensive care provided by Medicare.  Internal Medicine, Ophthalmology, Clinical Laboratory and Cardiology are in the top five most expensive.

<img src="https://github.com/bfetler/cms_medicare/blob/master/cms_pop_plots/bar_total_medicare_payment_amt.png" alt="bar plot total payment" />

#### Medicare Payment By State

Absolute cost per person of each provider type is shown above in the figure "Median Log10 Pay Per Person".

To show relative cost, maps of median cost per person by state were created for provider types.  Three common provider types are summarized below:
+ Physical Therapist (expensive, $509 USD)
+ General Surgery (intermediate, $338 USD)
+ Internal Medicine (inexpensive, $207 USD)

The absolute cost per person may seem counterintuitive, but is due to the number of sessions for treatment.  For example, General Surgery takes on average 2.4 sessions, while Physical Therapy takes 25 sessions.  

Below, a median color of red was used for each map, showing relative cost by state.  More expensive states trend purple, while less expensive states trend yellow.

<img src="https://github.com/bfetler/cms_medicare/blob/master/cms_state_person_plots/map_cost_per_person_physical_therapist.png" alt="median cost per person by state for physical therapist" />

<img src="https://github.com/bfetler/cms_medicare/blob/master/cms_state_person_plots/map_cost_per_person_general_surgery.png" alt="median cost per person by state for general surgery" />

<img src="https://github.com/bfetler/cms_medicare/blob/master/cms_state_person_plots/map_cost_per_person_internal_medicine.png" alt="median cost per person by state for internal medicine" />

Some of the western states such as Utah and Montana appear to be expensive for Surgery, while the northeast, California and Florida appear to be generally expensive.

#### Provider Gender

We further analyzed the data by provider gender, with some types of facilities categorized as neither.  In general, we find some specialties have a sizeable gender gap, while others do not.  This somewhat reflects traditional roles in society, with more female nurses and more male surgeons.  

<img src="https://github.com/bfetler/cms_medicare/blob/master/cms_gender_plots/bar_count_fraction.png" alt="gender count bar plot" />

We also find that female providers generally cost less than male providers, depending on specialty.  Consumers who choose female providers may see reduced costs.  On the other hand, the data also may indicate a persistent wage gap among female providers.  The median cost ratio is less than 20% for 80% of providers.  

<img src="https://github.com/bfetler/cms_medicare/blob/master/cms_gender_plots/bar_cost_ratio.png" alt="gender cost ratio bar plot" />

<img src="https://github.com/bfetler/cms_medicare/blob/master/cms_gender_plots/scatter_cost_ratio_by_fraction.png" alt="gender cost ratio scatter plot" />

Here is an example plot of a histogram of log costs by provider gender.  There does not appear to be a large difference in cost distribution based upon gender for most provider types.

<img src="https://github.com/bfetler/cms_medicare/blob/master/cms_hist_gender_plots/hist_gender_pay_per_person_group7.png" alt="gender cost histogram plot" />

#### Patient Age

We have data on average patient age, and age broken into four categories, which we can group by provider type.  The information is not broken down into cost per service by age, but it is still interesting to consider the popularity of different specialists by age.  

<img src="https://github.com/bfetler/cms_medicare/blob/master/cms_pop_plots/bar_beneficiary_average_age.png" alt="beneficiary average age by provider" />

Apparently Psychiatry is needed more by people in their mid-50's, while Radiation Oncology is more common in the mid-70's.  

<img src="https://github.com/bfetler/cms_medicare/blob/master/bene_average_age_plots/hist_beneficiary_average_age_group7.png" alt="beneficiary age subgroup" />

#### Patient Gender

Patient gender also affects the types of medical procedures needed.  The results are for total population.  

<img src="https://github.com/bfetler/cms_medicare/blob/master/cms_pop_gender_plots/bar_provider_type_group1.png" alt="beneficiary gender subgroup" />

#### Conclusion

Health care costs are a sobering reminder for consumers and anyone concerned with health care in the U.S.

## CMS Data API Advisory Analytics

For deeper PE-advisory workflows (correlations, concentration, volatility, and geo hot-spots), run:

```bash
python cms_api_advisory_analytics.py \
  --endpoint "https://data.cms.gov/data-api/v1/dataset/<DATASET_ID>/data" \
  --max-pages 12 \
  --limit 5000 \
  --top-n 25 \
  --extra-param "column=value" \
  --output-dir cms_advisory_outputs
```

Useful options:
- `--provider-col`, `--state-col`, `--year-col`: override column names for datasets that use non-standard CMS schema labels.
- `--extra-param key=value` (repeatable): pass filters/arguments supported by the CMS endpoint.
- `--min-services`, `--min-benes`: filter low-signal rows before ranking.
- `--winsor-upper-quantile`: clip extreme outliers in payment metrics (default 0.99).
- `--watch-min-growth`, `--watch-max-volatility`: tune watchlist sensitivity for risk/return screening.
- `--min-state-provider-rows`: minimum row count for provider-state regional opportunity scoring.
- `--benchmark-z-threshold`: z-score threshold for provider-state price outlier flagging vs provider peers.
- `--retry-count`, `--retry-backoff-s`: retry behavior for transient CMS API fetch failures.
- `--min-year`, `--max-year`: optional inclusive year filtering for multi-year datasets.
- `--baseline-year`, `--compare-year`: optional provider trend-shift comparison window (both required together).
- `--downside-shock`, `--upside-shock`: scenario stress-test assumptions for investability resilience scoring.
- `--momentum-min-years`: minimum historical depth required to score durable provider momentum.
- `--anomaly-z-threshold`, `--anomaly-min-rows`: detect provider-state-year cost anomalies relative to provider peer baselines.
- `--regime-strong-growth`, `--regime-high-volatility`: tune provider regime classification sensitivity (durable growth vs emerging volatility).
- `--artifact-prefix`: prepend output filenames to keep multiple scenario runs in one directory.
- `--white-space-min-percentile`: minimum blended white-space confidence percentile for provider-state expansion targets.
- `--scenario-downside-step`, `--scenario-upside-step`: control stress-grid granularity for scenario robustness output.
- `--geo-dependency-threshold`: threshold for flagging providers overly dependent on a single state market.
- `--reliability-min-observations`: minimum YoY observations required for provider trend reliability scoring.
- `--scenario-min-win-share`: threshold for tagging providers as scenario leaders in the operating-posture model.
- `--no-plots`: skip PNG generation for faster headless / batch workflows.
- runtime validation now hard-fails invalid settings (for example `--top-n <= 0`, empty extra-param keys, or invalid quantiles/volatility thresholds).

Generated artifacts include:
- `provider_opportunity_scores.csv`: weighted score using scale, margin proxy, acuity, and fragmentation.
- `provider_volatility.csv`: growth and volatility by provider type from YoY payment/service changes.
- `provider_value_summary.csv` + `provider_value_top.png`: risk-adjusted cost efficiency/value leaders by provider type.
- `provider_investability_summary.csv` + `provider_investability_top.png`: blended opportunity/value/stability ranking for deal-screen prioritization.
- `provider_stress_test.csv` + `provider_stress_test_top.png`: downside/upside scenario-adjusted investability ranking.
- `provider_momentum_profile.csv`: multi-year consistency scoring to separate durable provider growth from one-year spikes.
- `provider_state_year_anomalies.csv`: provider-state-year cost spike/trough detection against provider peer-year medians.
- `provider_regime_classification.csv`: classify providers into durable-growth, emerging-volatile, steady, stagnant, or declining-risk regimes.
- `state_portfolio_fit.csv`: blended state expansion fit score combining growth, volatility, concentration, and scale.
- `provider_consensus_rank.csv`: robust cross-model provider leaderboard blending opportunity/value/stability/stress/momentum/regime signals.
- `state_provider_white_space.csv` + `state_provider_white_space_top.png`: blended provider-state expansion white-space ranking (regional opportunity + state-fit + benchmark signal).
- `stress_scenario_grid.csv`: multi-scenario stress robustness table showing top providers across downside/upside shock combinations.
- `provider_geo_dependency.csv` + `provider_geo_dependency_top.png`: provider geographic concentration/dependency risk (top-state share) summary.
- `provider_trend_reliability.csv` + `provider_trend_reliability_top.png`: provider growth reliability score (signal-to-noise and consistency) leaderboard.
- `provider_operating_posture.csv` + `provider_operating_posture_top.png`: provider posture map (`scenario_leader`, `resilient_core`, `balanced`, `growth_optional`, `concentration_risk`).
- `provider_watchlist.csv`: provider buckets (`priority`, `monitor`, `high_risk`) from growth-vs-volatility rules.
- `state_growth_summary.csv`: state-level growth momentum table.
- `state_volatility_summary.csv` + `state_volatility_top.png`: volatility leaderboard for state-level payment instability.
- `provider_state_opportunities.csv`: ranked provider-type x state opportunities for regional expansion.
- `provider_state_benchmark_flags.csv`: provider-state price outlier flags (`high_price` / `low_price`) vs provider peer benchmarks.
- `market_concentration_summary.csv`: state-year concentration metrics (HHI, CR3, CR5) for rollup/consolidation screening.
- `correlation_matrix.csv` + `correlation_heatmap.png`.
- `yearly_provider_trends.csv` + `provider_yoy_growth.png`.
- `state_provider_heatmap.csv` + `state_provider_heatmap.png` for median payment-per-beneficiary by state/provider.
- `provider_opportunity_scatter.png` to visualize scale vs margin for top opportunities.
- `provider_watchlist_quadrant.png` to visualize risk-return positioning (growth vs volatility).
- `provider_state_opportunity_top.png` to visualize top provider-state opportunities.
- `provider_state_benchmark_flags.png` to visualize provider-state peer benchmark outliers.
- `market_concentration_hhi_top.png` to visualize most concentrated state-year markets.
- `provider_trend_shift.csv` + `provider_trend_shift_top.png` for largest provider payment shifts between baseline/compare years.
- `run_summary.json`: machine-readable run metadata (row counts, top provider, flagged counts, min/max year in filtered data).
- `data_quality_report.csv`: column-level null/zero-rate and cardinality diagnostics for data QA.
- provider-level and regional outputs now include percentile columns (for quick rank-based screening in BI tools).
- `advisory_snapshot.md`: auto-generated executive memo summarizing top provider and geography signals.
