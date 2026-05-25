# Data Source Classification Matrix

Single index of how every PEdesk surface is classified and disclosed.

## Generated artifacts (re-run after changes)

- **Tier taxonomy** → `docs/PEDESK_DILIGENCE_SURFACE_STATUS.md`
  (from `rcm_mc/diligence/surface_status.py`; regenerate via
  `scripts/gen_surface_status_doc.py`). green / navy / yellow / red.
- **Disclosure audit** → `docs/reports/PAGE_DATA_SOURCE_AUDIT.md` +
  `data_quality/page_data_source_audit.json` (from
  `scripts/audit_page_data_sources.py`). Flags data-rendering pages with no
  source disclosure.

## Real data sources (committed, with loaders + registry rows)

| Source | Loader | Disclosure label |
|---|---|---|
| CMS HCRIS hospital cost reports | `data/hcris` | HCRIS PUBLIC DATA |
| CMS Care Compare (SNF: turnover/ratings/enforcement) | `data/snf` | CMS PUBLIC DATA |
| CMS MIPS clinician quality | `data/mips_data` | CMS PUBLIC DATA |
| CMS MA Geographic Variation | `data/ma_data` | CMS PUBLIC DATA |
| CIVHC CO payer / APM / RBP | `data/payer_data` | CIVHC PUBLIC DATA |
| openFDA drug shortages | `data/drug_shortage_data` | CMS/FDA PUBLIC DATA |
| CMS MSSP ACO | `data/mssp_aco_data` | CMS PUBLIC DATA |
| HRSA HPSA shortage | `data/hrsa_data` | CMS/HRSA PUBLIC DATA |
| IBISWorld industry reports | `data/industry_intel` | LICENSED REPORT DERIVED |
| SimplyAnalytics market data | `data/market_intel` | LICENSED MARKET DATA DERIVED |

All registered in `rcm_mc/data/vendor/source_registry.csv`.

## Disclosure backlog

See the generated audit report for the live flagged list. The regression test
`tests/test_page_data_source_audit.py` fails if any page **outside** the
documented backlog renders data without disclosure — so the backlog can only
shrink, never silently grow.
