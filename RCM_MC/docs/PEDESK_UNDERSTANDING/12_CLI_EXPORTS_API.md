# 12 · CLI, exports & API — the non-browser surfaces

> PE Desk isn't only a web app. The same engines are reachable from the command line (for scripting/cron), produce file exports (IC memos, LP digests, packets), and expose a JSON API. Same code, same numbers (everything still flows through the packet / corpus / store) — just different front doors.

---

## CLI (`rcm-mc`)
Stdlib `argparse`, entry-pointed as `rcm-mc` (also `python -m rcm_mc`). Subcommands:

| Command | What it does |
|---|---|
| `rcm-mc serve --db p.db --port 8080` | Start the HTTP app (the whole web UI). |
| `rcm-mc analysis <deal_id>` | Build/load a **DealAnalysisPacket** offline and export it — the same packet the UI renders (§01). The CLI path is how you regenerate a packet for cron/batch. |
| `rcm-mc data status` | Read-only freshness table of the CMS data sources (`data_source_status`). |
| `rcm-mc data refresh [--source hcris\|care_compare\|utilization\|irs990\|cms_pos\|cms_general\|cms_hrrp\|all]` | Download + load public data into `hospital_benchmarks` (partial-failure tolerant). |
| `rcm-mc data refresh-nppes --ccn <CCN>` | Pull a hospital's NPPES provider roster (`nppes_live_cache`). |
| `rcm-mc pe {bridge\|returns\|grid\|covenant}` | Run PE-math from the CLI (`--json`, `--from-run`) — the bridge/MOIC/IRR/covenant/hold-grid functions from `pe_math` (§03 / `PEDESK_ALGORITHMS` §10). |
| `rcm-mc portfolio {register\|list\|show\|rollup\|users …}` | Portfolio + **user management** (this is where you create the admin user: `portfolio users create --username … --role admin`). Default DB `~/.rcm_mc/portfolio.db`. |
| `rcm-mc run / intake / lookup / ingest / challenge / deal / hcris` | Lower-level simulator/data utilities. |

**Critical/cron runs should go via the CLI**, not the web UI's in-memory job queue (which loses jobs on restart).

## Exports & reports
A deal's analysis can leave PE Desk as a file. The export layer:

- **Packet export** (`exports/packet_renderer.py`) — renders a `DealAnalysisPacket` to HTML/JSON/XLSX. Reached from the focused-deal bar (`/api/analysis/<id>/export?format=html|xlsx|json`) and the CLI. **Byte-for-byte reproducible** because the packet is frozen.
- **Reports** (`rcm_mc/reports/`) — full report, HTML report, markdown report, narrative, **exit memo**, **LP update**, **partner brief**, **PPTX export** (`[pptx]` extra), markdown report. These format packet/portfolio data into partner deliverables.
- **IC packet / QoE memo** — the IC master bundle (§03) and the QoE memo (§04) are standalone documents built for Print→PDF.
- **CSV exports everywhere** — deal/portfolio/risk-scan CSVs. **Defanged against Excel formula injection** (leading `=+-@` are neutralized) so an exported CSV can't execute a formula in Excel.
- **`generated_exports` table** — the manifest of produced files (drives the `/app` deliverables block, §02). Its `deal_id` FK uses **ON DELETE SET NULL** so a historical export survives the deal's deletion.

## API (`/api/*`)
Server-rendered JSON from the same `RCMHandler`. There's a **52-path OpenAPI spec** at `/api/openapi.json` and a **Swagger UI** at `/api/docs`; `/api` is the route index.

**GET (read):** `/api/health[/deep]`, `/api/metrics` (p50/p95/p99, admin), `/api/system/info`, `/api/search` + `/api/global-search`, `/api/deals/{search,stats,compare}`, `/api/portfolio/{attribution,health,alerts,regression,matrix,summary}`, `/api/portfolio/risk-scan.csv`, `/api/export/portfolio.csv`, `/api/runs`, `/api/scenarios`, `/api/calibration/priors`, `/api/jobs/<id>`, `/api/insights`, `/api/market-pulse`, `/api/counterfactual*`, `/api/regulatory-calendar/exposure`, `/api/diligence/comparable-outcomes(.csv/.memo)`, `/api/analysis/<id>/export`, `/api/backup`.

**POST (write):** `/api/login`, `/api/logout`, `/api/upload-{actuals,initiatives,notes}`, `/api/deals/{bulk,import,import-csv,wizard/*}`, `/api/screener/run`, `/api/portfolio/register`, `/api/webhooks`, `/api/metrics/custom`. CSRF-protected for browser form paths; a short exempt list covers login/logout/health.

**Optional FastAPI surface** (`rcm_mc/api.py`, requires the `[api]` extra) — a separate, opt-in programmatic `/simulate` endpoint. Not the main app.

---

## Where the numbers come from (unchanged)
The CLI, exports, and API are **alternate front doors to the same engines** — a packet exported via `rcm-mc analysis` or `/api/analysis/<id>/export` carries the identical numbers the web `/deal/<id>` pages show, because all three render the same `DealAnalysisPacket`. There's no separate calculation path.

---
*Next: `13_ENGAGEMENT_AUTH.md` — the consulting engagement layer and access control.*
