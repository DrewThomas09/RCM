# Synthetic corpus structural-integrity violations

Log of rows in the **synthetic** half of the deals corpus that fail
the structural checks in
[`tests/test_corpus_synthetic_integrity.py`](../RCM_MC/tests/test_corpus_synthetic_integrity.py).

**Scope:** synthetic-tagged rows only. Real deals have a separate
validation (plausibility_note on MOIC / IRR outliers). This file
tracks fabrication errors inside the demonstration data — not bugs
in the analytical math.

**Policy (agreed in the Phase-B sprint plan):** we do NOT modify
synthetic rows to "fix" them. Editing fabricated data to be more
plausible is its own trap — it creates half-laundered data that
partners might mistake for real. Offending rows stay logged here
and are addressed only when the corpus is fully regenerated.

The failing tests are marked `@unittest.expectedFailure` so CI
passes while the record is preserved.

---

## Violation categories

The test suite covers three structural impossibilities:

1. **buyer == seller** — can't acquire something from yourself
2. **deal_year < buyer's founded year** — high-confidence sponsor
   founding dates (KKR 1976, Bain 1984, …) checked against the
   deal's claimed transaction year
3. **deal_year outside 1990..current_year+1** — obviously-wrong dates

## Current findings

### Category 1 — buyer == seller (1 row)

| Deal | Violation |
|---|---|
| Shields Health Solutions / Summit Partners exit | `buyer == seller == "Summit Partners"` |

Fix direction when this gets regenerated: exits from a PE sponsor
should have either a strategic acquirer, a secondary sponsor, or a
public-market exit route — not the same sponsor on both sides.

### Category 2 — deal_year < buyer founded (0 rows)

Clean. The synthetic corpus never claims a deal predated its
sponsor's founding. The sponsor-founded-year list in the test is
small (27 entries) — may surface more violations if expanded.

### Category 3 — deal_year out of 1990..2027 range (0 rows)

Clean.

---

## Not logged here

Rows where the sponsor and target are real but the year is wrong
(e.g., "VITAS Healthcare / Chemed 2020" when Chemed has owned VITAS
since 2004) — those are in the `extended_seed_2..40` range and were
the evidence that tipped the Phase-B spot-check toward synthetic
tagging. The structural tests don't catch them because Chemed is
not a named sponsor in the founded-year table; the error is
"acquirer already owned the target", which requires domain knowledge
per deal, not a programmatic rule.

Catching those would require either:
  - an M&A timeline database to cross-reference (out of scope)
  - a human-curated ownership-history table per target (infeasible
    at 1,700-row scale)

Accepting that limitation is the reason the whole range was tagged
synthetic rather than carved piecemeal.
