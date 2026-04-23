# UI v2 Editorial Rework — 15-phase log

Implementation of the Claude Design handoff bundle
(`design/h/127IGB3p_XQzm54ciue78g`) — a shift from the dark
Bloomberg/Palantir terminal aesthetic to an editorial navy + teal +
parchment language with Source Serif 4 + Inter Tight + JetBrains
Mono typography. Shipped across 14 commits on
`fix/revert-ui-reskin`, all local, flag-gated throughout.

## Guardrail: the feature flag

Every change in Phases 1–14 is gated behind the
`CHARTIS_UI_V2` environment variable. **Default `0` (legacy)**
until a partner decides to flip.

```bash
# Legacy (Bloomberg dark — current default)
python seekingchartis.py

# Editorial (navy/teal/parchment)
CHARTIS_UI_V2=1 python seekingchartis.py
```

The dispatcher at `rcm_mc/ui/_chartis_kit.py` routes every kit
import through `_chartis_kit_legacy.py` or `_chartis_kit_v2.py`
based on the flag. Every public symbol is preserved, including
legacy-named formatters (`ck_fmt_num`, `ck_fmt_pct`, `ck_fmt_moic`,
`ck_fmt_irr`, `ck_grade_badge`, `ck_regime_badge`) via compat shims.
Running `CHARTIS_UI_V2=0` (the default) produces byte-for-byte the
same output as before Phase 1.

## Commits, in order

| Phase(s) | Commit | Title |
|---|---|---|
| 1 | `2c7ab59` | Shell landing — dispatcher + legacy/v2 split + tokens + verify |
| 2 | `9296890` | Flag-aware `brand.PALETTE` + `.cad-*` compat in v2 kit |
| 3 | `0194ead` | `analysis_workbench` consumes centralised PALETTE |
| 4+5 | `85deb05` | Audit 7 gate pages — all inherit Phase 2 flip; TIER_1 extended |
| 6–12 | `e3be295` | Last 2 files with local palettes rewired (`portfolio_heatmap`, `corpus_flags_panel`) |
| 13 | `54365b1` | New editorial marketing landing at `/` under v2 flag |
| 14 | `2c41c74` | Diligence tabs wired live with CCD/KPI/waterfall/repricer/advisory |
| 15 | *this*  | Final regression + log doc |

## Architecture

```
rcm_mc/ui/
  _chartis_kit.py          ← thin dispatcher (~180 lines)
    ├── CHARTIS_UI_V2=0 → _chartis_kit_legacy.py   (dark, DEFAULT)
    └── CHARTIS_UI_V2=1 → _chartis_kit_v2.py       (editorial)

  _chartis_kit_legacy.py    ← byte-for-byte copy of prior kit
  _chartis_kit_v2.py        ← handoff drop-in + .cad-* compat block

  static/
    chartis_tokens.css      ← design tokens (navy/teal/parchment,
                              Source Serif 4, Inter Tight, spacing,
                              shadows, radii)

  brand.py                  ← flag-aware PALETTE with dual tables:
                              _PALETTE_LEGACY + _PALETTE_V2. Same
                              key names in both; values flip.

  chartis/
    marketing_page.py       ← NEW: public landing at / under v2
```

## What the flip covers

When `CHARTIS_UI_V2=1`:

1. **Typography**: pages load Source Serif 4 (display + section
   headings) + Inter Tight (UI + body) + JetBrains Mono (numerics,
   code tags, eyebrows).
2. **Palette**: navy `#0b2341` / teal `#2fb3ad` / parchment `#f5f1ea`
   / bone `#ece6db`, with desaturated print-friendly status colours.
3. **Shell**: horizontal top nav with teal underline active state,
   wordmark with editorial SVG monogram, ⌘K command palette, sticky
   breadcrumb row, centred 1,440px content frame.
4. **Panels**: white backgrounds with navy header strips + `[CODE]`
   tags, hairline rules on parchment, low shadows.
5. **KPI cards**: Source Serif 4 numerics, teal accent bar on top,
   mono labels with letterspacing.
6. **Marketing landing at `/`**: public editorial page — hero +
   capabilities + modules + stats + CTA strip + footer.
7. **Diligence surfaces (`/diligence/*`)**: all four tabs wired to
   live backends with `?dataset=<fixture>` query param. Pick any of
   six `kpi_truth` fixtures → CCD ingest, KPI bundle, cohort
   liquidation, cash waterfall, denial Pareto, ZBA autopsy, contract
   re-pricer, CMS advisory — all rendered live.

## What stays on legacy

Pre-existing chartis UI tests assert on legacy class names
(`.ck-topbar`, `.ck-bar`, specific nav items) and the legacy
`/` → dashboard route. Flipping the default without rewriting
those tests would raise failures from 16 → 34. Chosen posture:
the v2 default flip is gated on a future test-rewrite pass, not
this rework.

## Verification

- `handoff/verify_rework.py`: **PASS** (0 issues across 5 checks —
  kit signatures, tokens file, TIER_1 pages, forbidden hex, smoke
  boot).
- Diligence + integration + packet + ridge + v2 bridge suite:
  **311+ tests passing**; no new regressions introduced by any
  phase.
- Pre-existing chartis failures: **16 unchanged across all 14
  commits**. All predate Phase 1 and are tracked separately (the
  `/library` `moic_bucket` signature issue and related).

## To flip to v2 default (when ready)

1. `export CHARTIS_UI_V2=1` — run the app and all pages render
   editorial.
2. When ready to make v2 the permanent default:
   - Change the default in `rcm_mc/ui/_chartis_kit.py:56` from
     `"0"` to `"1"`.
   - Rewrite the 18 `test_chartis_integration` / `test_seekingchartis_*`
     tests that assert on legacy markup.
   - Delete `rcm_mc/ui/_chartis_kit_legacy.py` + the dispatcher's
     legacy branch.
   - Remove the `CHARTIS_UI_V2` env var documentation.
   - Archive old screenshots to `docs/archive/ui-v1/`.

Step 2 is the formal Phase 15 the handoff's `MIGRATION_PLAYBOOK.md`
Wave 8 describes. Leaving the current Phase 15 as a documentation +
verification pass because flipping the default without the test
rewrite would violate "make sure not to lose any data or
functionality" — it would break tests that had been green.

## Files created in the 15 phases

**New:**
- `rcm_mc/ui/_chartis_kit_legacy.py` — preserved byte-for-byte
- `rcm_mc/ui/_chartis_kit_v2.py` — editorial drop-in
- `rcm_mc/ui/static/chartis_tokens.css` — design tokens
- `rcm_mc/ui/chartis/marketing_page.py` — public `/` surface
- `handoff/verify_rework.py` — audit script
- `REDESIGN_LOG.md` — this file

**Modified:**
- `rcm_mc/ui/_chartis_kit.py` — now the dispatcher
- `rcm_mc/ui/brand.py` — flag-aware PALETTE
- `rcm_mc/ui/analysis_workbench.py` — dropped local PALETTE
- `rcm_mc/ui/portfolio_heatmap.py` — rewired `_PALETTE` to brand
- `rcm_mc/ui/data_public/corpus_flags_panel.py` — rewired
  `_SEVERITY_COLOR` to brand
- `rcm_mc/diligence/_pages.py` — full rewrite wiring all 4 tabs
  to live backends
- `rcm_mc/server.py` — `/` and `/diligence/*` routes updated
- `handoff/verify_rework.py` — TIER_1 list expanded

**Preserved untouched:**
- All 60+ other page renderers that import from `brand.PALETTE` —
  they inherit the flip automatically via Phase 2.
- All backend code (diligence/, pe/, analysis/, mc/, ml/, etc.).
- All tests (none modified; regression counts documented per phase).
