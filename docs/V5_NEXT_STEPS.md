# V5 Next Steps — Strategic Roadmap

A concrete cycle plan for advancing V5 fidelity from the cycle-32
checkpoint state (~53% passing) toward 80%+. Each proposed cycle
names the work, the expected lift, the risk, and the dependencies
on prior cycles.

## Current state (cycle 33 audit)

After cycle 33's audit-bug fix (recognizes
`editorial_chartis_shell` alias + excludes helper-only modules):

| | |
|---|---|
| Audit denominator | **299 real pages** (was 310 with helpers) |
| Passers | **159 of 299 (53.2%)** |
| Above 80 | 28 |
| 70–79 | 131 |
| 60–69 | 3 |
| 50–59 | 23 |
| <50 | 114 |

The 14 pages flagged in cycle 32 as "no `chartis_shell` calls"
turned out to be 5 audit false-positives (use the
`editorial_chartis_shell` alias) plus 11 helper modules.
Cycle 33 fixes both.

## What advances V5 from here — ordered by leverage

### Tier 1 — concrete cycles, +20-50 passers each

#### Cycle 34 — wire `ck_provenance_tooltip` on top-tier pages

The current top of leaderboard tops out at 89/100 because no
page uses `ck_provenance_tooltip` (worth +5 in the audit) or
heavy `ck_fmt_*` helpers (worth +10 max).

**Work:** Identify the 28 pages in the 80-89 tier; for each
add 2-3 `ck_provenance_tooltip` wraps on key partner-facing
numbers (MOIC, IRR, EBITDA bridge values). Pre-existing
`ck_provenance_tooltip` already supports a 4-line tooltip
shape — the cycle 22 doc named "explain this number" 4C
foundation as already shipped.

**Expected lift:** 28 pages from ~85 to ~92. New 90+ tier
created. No new passers (those are already passing) but the
top of the campaign has somewhere to go.

**Risk:** Low. Each tooltip is a wrapper; doesn't change
content semantics. Test fixtures need to assert tooltip
markup.

**Cost:** ~30 min per page × 28 pages = ~14 hours, OR a
script that adds tooltips to a list of (page, value-name)
pairs — probably faster.

#### Cycle 35 — handle dynamic-color cells in `migrate_inline_cells.py`

Cycle 23 deferred ~1175 cells because they use
`color:{cc}` where `cc` is a runtime variable like
`pos if x > 0 else neg`. The migration script can't resolve
those at static-analysis time.

**Work:** Update the script to detect the conditional pattern
and rewrite as `ck_data_cell(value, tone="pos" if x > 0 else "neg")`.
The helper already accepts `tone` per call, so the rewrite
is mechanical — just need the regex to recognise the
ternary form in surrounding source.

**Expected lift:** ~1175 cells migrated → ~80-100 pages
gain ~5 fidelity points each → 30-50 pages cross 70 from
the 50-59 tier (currently 23 pages).

**Risk:** Medium. The dynamic-color resolution requires
careful regex (the `cc` variable may be defined far from
the cell in the page's body). Conservative-by-default means
some pages skip migration.

**Cost:** ~3 hours to write + test the script; bulk apply
+ verify imports + audit ~1 hour.

#### Cycle 36 — KPI-card helper + migration

Pages render their KPI strips with bespoke
`<div style="font-size:18px;font-weight:700;...">{value}</div>` +
`<div style="font-size:12px;color:{text_dim};margin-top:4px">{sub}</div>`.
~150 instances per page * ~140 pages = ~3000 inline-style
instances if `ck_kpi_block` is called manually but its body
spans inline-styled divs.

**Wait** — `ck_kpi_block` already exists from cycle 6 and IS
used by data_public pages. The migration would be from
hand-rolled divs to `ck_kpi_block(label, value, sub=...)`
calls.

**Work:** Survey the actual non-`ck_kpi_block` KPI patterns
across data_public; build `ck_kpi_card` (or just utility
classes if `ck_kpi_block` is the right shape); script the
migration.

**Expected lift:** Already-using pages don't gain; pages
with bespoke KPI markup gain ~3-5 fidelity points each.
Probably 20-30 pages cross 70.

**Risk:** Low-medium. Cycle 22-style pattern.

**Cost:** ~4 hours.

### Tier 2 — structural ports (one cycle per page)

#### Cycle 37+ — port the 5 real no-shell pages

Cycle 33 surfaced these as the only non-helper pages
without an editorial-shell call:

- `rcm_mc/ui/chartis/login_page.py` (369 LOC) — already
  uses `editorial_chartis_shell` alias; cycle 33's audit
  fix should credit it. Verify.
- `rcm_mc/ui/chartis/forgot_page.py` (121 LOC) — same.
- `rcm_mc/ui/chartis/marketing_page.py` (423 LOC) — public
  landing at `/`. Already editorial; verify.
- `rcm_mc/ui/chartis/app_page.py` (220 LOC) — `/app`
  dashboard orchestrator. Already editorial.
- `rcm_mc/ui/compare.py` (360 LOC) — deal-comparison page.
  Genuinely needs a port to use `chartis_shell`.

**After cycle 33 audit fix, only `compare.py` is a real
candidate for a structural port.**

**Work:** Cycle-6-style port. Wrap the comparison body in
`chartis_shell` with appropriate `active_nav` and
`editorial_intro`.

**Expected lift:** +1 page over threshold.

**Risk:** Low. Single-page port.

**Cost:** ~2 hours.

#### Cycle 38+ — port the 23 pages in the 50-59 tier

These are the next-most-recoverable tier. Most have low
primitive density + moderate inline-style residue. Each
needs ~2-3 cycles 22-style touches (intro + ck_data_cell
calls).

**Work:** Run the existing migration scripts (cycles 21, 23,
28, 30, 31) on this tier. Some already failed cycle 25's
bulk apply because of variant patterns.

**Expected lift:** ~10-15 cross 70.

**Risk:** Low. Same playbook as cycles 22-31.

**Cost:** ~6 hours.

### Tier 3 — fundamentally different work

#### Cycle 39+ — live-rendered DOM audit

The current source-only audit can't see runtime DOM (font
loading, palette application, layout grid, color contrast).
Cycle 16 Option C was deferred. After source-side migrations
plateau, this is the next signal.

**Work:** Boot in-process server, fetch each page, parse the
HTML output, check for chartis-grade DOM signals: navy
topbar present, italic-serif font loaded, palette tokens
applied, no high-contrast violations, layout grid responds
to viewport.

**Expected lift:** Catches gaps source audit missed. May
surface that some 80+ pages render with broken fonts in
production. New signal, not directly comparable to source
audit.

**Risk:** Medium. Auth sequencing (most routes need login),
fixture data setup, parser fragility. Cycle 13's azure_smoke
solves the auth seq for one URL — generalize that.

**Cost:** ~8 hours.

#### Cycle 40+ — port the 114 sub-50 pages

These need real cycle-6-style ports — they have shells but
score badly because they're inline-style heavy with low
primitive density. Each needs:

- Replace bespoke divs with ck_panel / ck_kpi_block
- Replace inline styles with classes
- Add italic-serif intro
- Add fmt_helper calls

**Work:** Cycle-6-style port per page, BUT amortized via
the migration scripts (cycles 21, 23, 28, 30, 31) for the
mechanical 80%. The remaining 20% is per-page.

**Expected lift:** ~80 of 114 cross 70 = +80 passers.
(Some pages have such bespoke chrome that they need real
cycle-6 ports.)

**Risk:** Medium. Long tail; gradient of difficulty.

**Cost:** ~30+ cycles. Major undertaking.

## Recommended near-term sequence

1. **Cycle 34**: Provenance tooltips on top tier (immediate
   visible polish).
2. **Cycle 35**: Dynamic-color cell migration (biggest source-
   audit lift available).
3. **Cycle 36**: KPI-card cluster (compounds cycle 35).
4. **Cycle 37**: Port `/compare`.
5. **Cycle 38**: Run all 5 migration scripts against the 50-59
   tier.
6. **Cycle 39**: Live-rendered DOM audit (when source audit
   saturates).
7. **Cycle 40+**: Sub-50 long tail (pace this with a roadmap,
   one batch per session).

After cycles 34-38: expected ~190-210 passers (~65-70%).
After cycle 39: orthogonal signal — pass rate doesn't change
but quality bar lifted.
After cycle 40+ (long tail): toward 80%+.

## What "advances V5" doesn't mean

- More commits per session — diminishing returns past cycle 28
  in this session.
- Forced bulk migrations on patterns where the script's
  conservative-by-default skip rate is high (signals the
  pattern needs human review, not more script tweaking).
- Recalibrating the audit rubric to make numbers go up. The
  cycle 24 recal was justified (saturating penalty masked
  real progress); cycle 33 audit fix was justified (false
  positives). Further calibration without a real source change
  is gaming.

## What this campaign needs that's NOT script work

- **A real Azure ship** to flip the 3 remaining deploy rows
  from `[~]` to `[x]`.
- **A user / partner reviewing the editorial chrome on a
  live page** to identify visual gaps the audit can't catch.
- **A merge of `design-v5` to `main`** to consolidate. The
  branch is ~50+ commits ahead.
