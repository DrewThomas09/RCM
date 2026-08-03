# Report 0281: Two live cross-module contradictions closed, and a guard so they cannot come back

## Scope

The sourcing program has so far treated staleness as the enemy. This iteration found a
worse failure mode that the program itself was *creating*: **partial refreshes**. When a
wave updates some modules citing a statistic and not others, the platform stops being
merely out of date and starts contradicting itself — two pages of the same report giving
different answers to the same question, with nothing to tell a reader which one the
platform believes.

Two instances were live in `market_reports/` simultaneously. Both are now closed, and the
class is now enforced by a test.

## Instance 1 — GADCS cost/revenue means (self-inflicted, disclosed in `06c7efc`)

A refresh wave moved 9 of 14 IFT modules to the CMS/RAND GADCS **Year 1–Year 4 cohort
appendix**, leaving 5 asserting the superseded **Year 1–2** figures as current. This was
disclosed in the commit that caused it rather than discovered later; the completion wave
followed immediately.

Every value was verified by reading the CMS PDF directly (`pdftotext -layout`), not taken
on an agent's report:

| Figure | Was (Y1–2, Dec 2024) | Now (Y1–4, Dec 2025) | PDF corroboration |
|---|---|---|---|
| Mean total cost / transport, all NPIs | $2,673 | **$2,763** | n=9,599, median $1,355 |
| … for-profit / unknown agencies | $1,788 | **$1,912** | n=1,869 |
| … governmental agencies | $3,127 | **$3,167** | n=5,121 |
| Mean total revenue / transport | $1,147 | **$1,268** | n=9,599, median **$613** |

The sample sizes and medians corroborate the means independently — the module text already
claimed "n=9,599; median $613", and the PDF row matches exactly, which is what
distinguishes a real citation from a plausible one.

**A residual bug surfaced during this work.** `ift_mmt.py` held `cost = 1778.0` — the
*transposed* form of $1,788. Commit `ddc941c` had fixed that transposition across 19 label
strings but missed the numeric field itself, so the module rendered "$1,778" as its value
while its own derivation line said "$1,788". Moving to $1,912 closed the residual and the
vintage gap in one edit.

## Instance 2 — CERT ambulance improper-payment rate (pre-existing, found by grep)

`ift_indepth_q23`, `q456` and `q910` cited the **CMS CERT 2025** supplemental release.
`ift_indepth_q78` still cited **2024** — in 10 places. Verified from the CMS PDF:

```
Ambulance   $452,598,022   10.4%   CI 5.6% - 15.3%
            No Doc 11.5% | Insufficient Doc 46.7% | Medical Necessity 24.9%
            Incorrect Coding 0.3% | Other 16.6% | 1.5% of overall improper payments
```

So 13.2% → **10.4%**, $595.1M → **$452.6M**, 63.5% → **46.7%**, 27.5% → **24.9%**. The
evidence rows previously carried a bare `(re-verify)` marker and an *empty URL*; they now
carry the release identity and a fetchable primary source. Zero occurrences of the 2024
figures remain anywhere in the package.

## The actual deliverable: `test_market_reports_vintage_consistency.py`

Both incidents were caught by a manual grep that happened to be run. Nothing in the test
suite would have failed. That is the real defect.

The test encodes the rule that makes the failure impossible to reintroduce silently:

> A superseded figure may appear **only** inside explicit historical framing.

This is deliberately not a ban. Naming what a number replaced is good provenance writing,
and several modules do it well — `"SUPERSEDES the Year 1–2 cohort figures ($2,673 / $3,127
/ $1,788, Dec 2024)"` stays legal. Asserting $2,673 as current does not. Detection uses a
two-line lookback window because these modules wrap prose, so a docstring's "previously
quoted" marker often sits on an earlier line than the number it governs.

Two secondary assertions stop the guard from rotting:

- the **current** figures must still be cited somewhere, so the check cannot pass trivially
  on a codebase that dropped the claims entirely;
- both primary-source URLs must be present, since a figure without a fetchable source is
  precisely what this program exists to eliminate.

**Mutation-tested rather than assumed.** Reintroducing the `13.2% / 63.5%` line makes the
test fail with the exact `file:line` and the replacement value. A guard that has never been
seen to fail is not yet a guard.

## Process finding — an agent destroyed uncommitted work

Mid-iteration, a wave agent ran `git stash`, reverting roughly 1,000 lines of validated but
uncommitted work: the 5 vintage modules, 2 finished UI pages, and an in-progress page.
Recovered with `git checkout stash@{0} -- <paths>`, keeping the stash entry intact because
it still held a version of a file another agent was actively rewriting.

Two standing rules follow, both now applied to every agent prompt:

1. Agent prompts **explicitly forbid all git commands** — and say why, because a bare
   prohibition reads as boilerplate and a concrete incident does not.
2. Validated work is committed and pushed **immediately**, never left in the worktree while
   other agents run.

## Evidence

`test_ift_markets`, `test_market_intel`, `test_ift_indepth`, `test_ift_mmt` → 119 passed.
Plus 5 new vintage-consistency tests, and 435 passed across
`test_npi_cleaner` / `test_target_screener` / `test_palette_routes` / 5 screener suites for
the UI pages landed alongside. Commits `022ec09`, `8b8b64c`.

One test change was required: `test_ift_mmt` pinned $1,147/$1,778 as an *honesty guard*
against a previously fabricated 0–60% margin. It was re-anchored to the new published pair
rather than loosened — the guard it exists to enforce (the published mean spread is
negative) still holds at $1,268 vs $1,912.

## Follow-ups

- Cross-module conflict detection is now running as a program rather than a grep
  (`w38zx2azh`): 10 extractors over the 20 densest modules, deterministic clustering by
  normalized subject, then adjudicators that must **fetch** a primary source. Step 1 of
  adjudication is "is this even a real conflict?", to avoid the earlier regex trap where the
  same label across sector modules is legitimately different values.
- UI improvement wave 1 continues; 4 of 18 pages landed.
- Unchanged from 0279: 41 weak citations, 16 unrepaired dead links, 13 items needing owner
  judgement.

---

Report/Report-0281.md written.
