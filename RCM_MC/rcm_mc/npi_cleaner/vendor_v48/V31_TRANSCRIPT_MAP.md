# v31 quick map — transcript problem → fix → where to look

Each row ties a thing said on the Onyx / Project Infusion call to the module that
fixes it, the tab that proves it, and the flag that drives it.

| # | What was said on the call | Module | Tab(s) to look at | Flag |
|---|---|---|---|---|
| 1 | "We only captured half of Stelara. The rest is under another code lower down and our formula takes the first one." | `common_name.py` | Common_Name_Rollup (plus the 4 per-drug cuts now group on the molecule) | none (always on) |
| 2 | "Some NDCs map to multiple J-codes, find the best match." | `ndc_jcode.py` | NDC_JCode_BestMatch | `--per-drug-control` optional |
| 3 | "Exclude by inclusion: keep formulary + keep-list, flag the Keytrudas, never force it." | `formulary.py` | Formulary_Gate, Formulary_Exclusions_Review | `--formulary <file>` |
| 4 | "Not all NDCs have a J-code, don't force-map those." | `ndc_jcode.py` | NDC_NoJCode_KeptAsNDC | none |
| 5 | "Government claims run through their own pharmacies with unique NPIs, which are they?" | `npi_channel.py` | NPI_Channel_Classification, NPI_Government_Reconciliation | `--gov-npi-list <csv>` |
| 6 | "The unblinded total is inexplicably low, we're rebuilding to numbers too low." | `control_total.py` | Control_Total_Reconciliation, Control_Total_Exposure, Capture_By_Drug | `--control-total <amount>` |

## One-line reasoning per fix
1. Group every row to its molecule (`drug_common_name`) so a drug billed under
   several J-codes is summed once. A bare NOC/catch-all code never borrows a real
   molecule's identity.
2. Pick one J-code per NDC, brand-first, and prefer the ASP-priced or class-NOS code
   over some other brand's exclusive code.
3. Tag IN_FORMULARY / KEEP_OFF_FORMULARY / EXCLUDE_CONFIRMED / *_REVIEW; explicit
   excludes win; nothing dropped unless you opt in.
4. NDCs with no real J-code stay as NDC (NO_JCODE_KEEP_AS_NDC) rather than being
   mapped to a code that misstates CMS spend.
5. Classify each NPI by payer-type mix + pharmacy taxonomy, then reconcile against the
   client's own government-NPI list so nothing is taken on faith.
6. Reconcile captured vs the control total, and show the split-code and
   government-channel dollars a naive rebuild drops (as exposure, not double-added).

## Example run
```
python -m npi_recovery.cli INPUT.csv \
  --control-total 38000000 \
  --gov-npi-list client_gov_npis.csv \
  --formulary client_formulary.csv \
  --per-drug-control per_drug_targets.json
```
Every flag is optional. With none supplied, the new tabs still build from the shipped
seeds (or emit an honest note) and NPI recovery is unchanged.
