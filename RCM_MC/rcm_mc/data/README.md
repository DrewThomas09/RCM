# Data

Data ingestion, public-data loaders, and hospital profile assembly. Connects to CMS (HCRIS, Care Compare, Utilization), IRS 990, SEC EDGAR, and seller-provided files. All external fetches use stdlib `urllib` -- no third-party HTTP libraries.

| File | Purpose |
|------|---------|
| `auto_populate.py` | One-name-to-full-profile assembly: merges HCRIS, benchmarks, quality, and utilization data with per-field source attribution |
| `benchmark_evolution.py` | Tracks year-over-year benchmark drift; flags when P50 has shifted >1pp so re-marks use current industry context |
| `claim_analytics.py` | Denial rates, top denial reasons, and payer aging analytics over the `claim_records` table |
| `cms_care_compare.py` | CMS Care Compare loader: star ratings, HCAHPS scores, complications, and readmissions per provider |
| `cms_hcris.py` | HCRIS benchmark-database loader: normalizes cost report data into `hospital_benchmarks` rows |
| `cms_utilization.py` | Medicare inpatient utilization loader: charge-to-payment ratios, DRG concentration, and discharge volumes |
| `data_refresh.py` | Orchestrator for the four core CMS data sources; sequences refresh, records provenance, handles partial failures |
| `data_scrub.py` | Board-ready data scrubbing: winsorizes outliers, standardizes naming, caps EBITDA drag artifacts |
| `document_reader.py` | Drag-drop extraction of RCM metrics from seller Excel/CSV/TSV files using alias-aware column matching |
| `edi_parser.py` | EDI 837/835 parser for claim submission and remittance data; extracts the minimum segments for denial and AR analytics |
| `geo_lookup.py` | City/state to approximate lat/lon lookup using US state capital centroids for portfolio map plotting |
| `hcris.py` | CMS HCRIS public-data layer: extracts ~15 fields per hospital from annual Cost Reports; ships as pre-parsed parquet |
| `ingest.py` | `rcm-mc ingest` CLI: turns messy seller data packs (Excel, zip, folder) into three canonical calibration CSVs |
| `intake.py` | Interactive 11-prompt intake wizard that collapses a 131-field config surface into a 5-minute analyst session |
| `irs990.py` | IRS Form 990 cross-check for non-profit hospitals via ProPublica API; flags >15% variance against HCRIS |
| `irs990_loader.py` | IRS 990 benchmark loader: normalizes charity-care and bad-debt numbers into `hospital_benchmarks` |
| `lookup.py` | `rcm-lookup` CLI: fast terminal browser for CMS HCRIS data by CCN, name, state, or bed count |
| `market_intelligence.py` | Competitor finder and HHI market concentration analysis using Haversine distance on state centroids |
| `sec_edgar.py` | SEC EDGAR integration: fetches revenue, margin, and leverage from XBRL for ~25 public hospital systems |
| `sources.py` | Observed/prior/assumed tagging for config parameters; classifies every model driver's provenance |
| `state_regulatory.py` | State-level regulatory registry: CON laws, Medicaid expansion, rate comparisons, and commercial market concentration |
| `system_network.py` | Hospital system network graph builder; finds standalone add-on acquisition targets near a system's footprint |
| `_cms_download.py` | Shared download helper (atomic fetch, respectful retry, cache directory) for all CMS data loaders |

## Key Concepts

- **No runtime network calls for core analysis**: Public data ships pre-parsed; `data_refresh` is an explicit analyst action.
- **Alias-aware column matching**: Seller files use hundreds of different column names for the same metrics; the alias table handles the mapping.
- **Per-field provenance**: Every auto-populated value is tagged with its source so the analyst can defend each number in IC.
