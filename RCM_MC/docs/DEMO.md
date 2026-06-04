# Demo Mode — the KKR healthcare portfolio

Demo Mode turns the empty console into a **fully populated, credible
showcase**: one click loads a curated portfolio of real KKR healthcare
investments so the command center, portfolio map, alerts, cohorts, deal
pages, PE math and RCM analytics all light up. It exists so a partner can
evaluate every feature against true, internally-consistent numbers — and
then clear it and load their own deals.

## How to use it

1. **Settings → Demo Mode** (or go to `/demo`).
2. Click **Load KKR demo portfolio**. The workspace fills; you're redirected
   to the command center with a **Demo mode** banner.
3. Explore — see the guided tour on `/demo` for a walk-through.
4. When you're done, click **Unload demo portfolio** on `/demo` to return to
   a clean workspace. Your own deals are never touched.

Loading and unloading are both idempotent and reversible.

## What's real vs modeled (credibility)

The demo is built to be defensible in front of a partner:

| Aspect | Treatment |
|---|---|
| **Deals** | **Real.** Every deal is an actual KKR healthcare investment, also present in the source-cited `verified_deals` corpus (`source_url` carried through). |
| **Enterprise values** | **Real where disclosed** — Envision (~$9.9B), Cotiviti (~$4.9B), BrightSpring (~$1.3B), Therapy Brands (~$1.2B). Others are modeled at sector-typical entry multiples and flagged with `*` in the UI and `ev_disclosed: false` in the data. |
| **Operating metrics, leverage, MOIC/IRR, covenant headroom, quarterly variance** | **Modeled** from a per-deal performance tier — realistic and internally consistent, not represented as audited returns. |
| **The downside** | **Honest.** KKR's Envision Healthcare seeds as the documented ~$10B write-off / 2023 Chapter 11: covenant tripped, EBITDA sliding ~30% below plan. A real track record contains losses. |
| **The upside** | Gland Pharma is the ~4x exit (2020 IPO) — the bookend to Envision. |

The RCM EBITDA-bridge opportunity is calibrated to a credible band
(red ≈5%, amber ≈4%, green ≈2.4% of net revenue), not an exaggerated figure.

## What it populates

17 deals · 11 sectors · 12 US states · ~$34B entry EV. After loading:

- **Command center / home** (`/app`, `/home`) — pipeline, alerts, health-band
  distribution, recent deals, deadlines, with a demo-mode banner.
- **Portfolio map** (`/portfolio/map`) — 16 deals shaded across 12 real US
  states (Gland Pharma is India-based and honestly left off the US map);
  CON jurisdictions flagged.
- **Heatmap, cohorts, watchlist, monitor** — all resolve to the KKR deals.
- **Deal pages** (`/deal/<id>`, `/analysis/<id>`, `/hold/<id>`,
  `/ebitda-bridge/<id>`) — snapshot trail, a seven-quarter EBITDA trajectory
  + variance, RCM profile, the PE bridge, covenant headroom, health trend.
- **Alerts** — seeded mid-lifecycle: one acked, one snoozed, Envision's
  covenant breach left live, so ack / snooze / escalate are all demonstrable.
- **Deadlines** — upcoming and overdue (restructuring review, covenant tests).
- **Notes** — analyst storylines on the marquee deals.

A smoke test (`tests/test_demo_smoke.py`) asserts every deal and every
demo-critical surface renders 200, traceback-free, on each commit.

## Downloads (ingestion files)

`/demo` offers the portfolio as **`kkr-deals.json`** and **`kkr-deals.csv`**.
These are the real import format and round-trip cleanly:

- `kkr-deals.json` → `POST /api/deals/import` recreates the profile-populated
  deals (sector, sponsor, vintage, HQ state, RCM metrics).
- `kkr-deals.csv` → the CSV importer (flat columns map into each deal's
  profile).

The full hold-period analytics (snapshots, returns, variance) come from the
one-click load; the import reproduces the deal roster + profiles.

## Where it lives

- `rcm_mc/demo/kkr_demo.py` — the dataset (`KKR_DEMO_DEALS`), the seeder
  (`seed_kkr_demo`), the inverse (`unload_kkr_demo`), and `demo_deal_rows`.
- `rcm_mc/ui/demo_page.py` — the `/demo` page (load/unload, tutorial, table).
- `rcm_mc/ui/demo_banner.py` — the demo-mode banner.
- Routes: `GET /demo`, `POST /demo/load`, `POST /demo/unload`,
  `GET /demo/download/kkr-deals.{json,csv}`.
