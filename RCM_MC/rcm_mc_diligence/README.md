# rcm_mc_diligence/

Standalone CLI + connector layer for diligence-flow data ingestion. Ships its own `rcm-mc-diligence` console-script entry point (see `pyproject.toml`).

| Subdirectory | Purpose |
|--------------|---------|
| `connectors/` | Inbound data adapters — Excel, EDI 837/835, claims feeds, HCRIS gz |
| `dq/` | Data-quality validators — schema checks, completeness, plausibility ranges |
| `fixtures/` | Sample input files for development and testing |
| `ingest/` | Pipeline orchestration that wires connectors → DQ → calibrated analysis packet |
| `tests/` | Test suite for this package only (separate from the main `RCM_MC/tests/`) |

| File | Purpose |
|------|---------|
| `cli.py` | `rcm-mc-diligence` entry point — `validate`, `ingest`, `run` subcommands |

## Why a separate package

This package can be installed independently for partners who only need the data-ingest pipeline (e.g., a consulting firm preparing a deal book). The full analytics platform (`rcm_mc/`) depends on this package, but not vice-versa.
