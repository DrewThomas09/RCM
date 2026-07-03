# V33 QUOTE FIX MAP

Every material quote from the meeting notes, verbatim, with the step by step fix and where that fix lives in the toolkit. Cite the tab, the flag, and the selftest; nothing here rests on memory. Versions: v31 (six formulary and channel fixes), v32 (ceiling, scope, universe, gross-up), v33 (loop closing: trend integrity, cross-source parity, roster forensics, calibration, triangulation). 151 offline selftests cover all of it.

---

## 1. The ceiling and what suppression actually hides

**Quote:** "suppression hides distribution, not volume" (Evan, 0:03)

What it names: the VRDC export carries unsuppressed aggregate totals; cell suppression removed the NPI-level breakdown, not the money. Any recovery must reconcile to those totals, never rebuild past them.

Fix, step by step:
1. Load the suppressed export and detect the suppression pattern (blank or masked cells against a populated row total).
2. Recover exactly-determined cells by complement: where a row total exists and all but one cell is known, the last cell is arithmetic, not estimation.
3. Distribute any remaining suppressed mass proportionally, capped so no cell exceeds what the row total permits.
4. Reconcile the recovered table to the unsuppressed aggregates and print the residual.

Where it lives: v32, `vrdc_suppression.py`, tabs `VRDC_Suppression_Audit` and `VRDC_Ceiling_Report`, flag `--vrdc-suppressed`.

**Quote:** "Gap-filling can only rebuild to a ceiling that is already wrong" (report, Problem 1 header)

What it names: the pull was roughly half of expectations, so the deficit is upstream of suppression. Perfect gap-filling recovers distribution under a total that is itself short.

Fix, step by step:
1. Compare captured panel dollars to the expected control total before any recovery step runs.
2. Attribute the gap across the four candidate causes (see section 7) instead of treating it as a suppression problem.
3. Render the ceiling verdict: if the unsuppressed total is materially below expectation, print UPSTREAM DEFICIT DOMINATES and stop treating gap-filling as the remedy.

Where it lives: v31 `control_total.py` (tab `Control_Total_Reconciliation`, flags `--control-total`, `--per-drug-control`); v32 `vrdc_suppression.ceiling_report` (tab `VRDC_Ceiling_Report`); v33 self-fed `Deficit_Diagnosis`.

---

## 2. The formulary filter and the grain error

**Quote:** "keep or drop NDCs absent from the target's formulary" (Curtis's question, 1:30)

What it names: the inclusion decision that started the whole thread. Answered wrong (drop, at the code grain), it silently deleted real spend.

Fix, step by step:
1. Treat the formulary extract as a code snapshot: one set of HCPCS, one set of NDCs, whatever columns it has.
2. Never answer keep-or-drop at the row level. Resolve the row to its molecule first, then apply the molecule's decision to the row.
3. Keep an explicit keep-list lane (OPAT antibiotics and similar) so clinical inclusions survive independent of formulary presence.

Where it lives: v31 `formulary.py` (exclude-by-inclusion), tab `Formulary_Screen`, flag `--formulary`.

**Quote:** "membership must be evaluated at the drug level, not the code level" (Evan, 2:15)

What it names: the grain principle. A molecule is in or out; its codes and NDCs follow.

Fix, step by step:
1. Group every claim row to a common name by NDC first, then brand name, then drug-exclusive J-code (v31 grouper).
2. Build each molecule's complete code array and complete NDC array from public references, not from observed claims (section 3).
3. Test membership as any-match: molecule is in if its code array intersects the formulary HCPCS set or its NDC array intersects the formulary NDC set.
4. If the molecule is in, every claim row of that molecule is in, whichever label the row happens to carry.

Where it lives: v32 `crosswalk_builder.any_match_membership`, tab `DualFlag_Membership`, flags `--formulary-codes`, `--asp-crosswalk`, `--fda-ndc`, `--dme-fee`. Selftests cover Stelara and Inflectra cases.

**Quote:** "an NDC not on the formulary that maps by J-code to a drug that is" (Curtis's counter-case, 2:58)

What it names: the concrete row the code-level filter deletes and the drug-level rule keeps.

Fix, step by step:
1. Resolve the row's NDC through the crosswalk to its molecule.
2. Check the molecule's membership, already decided by any-match.
3. The row is in, full stop; log the code-level evidence flag as absent so the stocking question stays answerable (section 4).

Where it lives: v32 `DualFlag_Membership` (`capture_in` true, `code_evidence` false on exactly these rows). Selftest: the Curtis counter-case check.

**Quote:** "we need both" (Nico, 3:11)

What it names: two different questions were being answered with one flag. What counts toward the market needs the drug-level flag; what the target stocks needs the code-level flag.

Fix, step by step:
1. Compute `capture_in` (drug-level membership) and `code_evidence` (this exact code or NDC appears in the snapshot) side by side on every row.
2. Drive all totals, trends, and mix charts off `capture_in` only.
3. Answer stocking and formulary-depth questions off `code_evidence` only.
4. Never collapse them; collapsing re-creates the original bug from the other direction.

Where it lives: v32 `DualFlag_Membership`, both flags on every row, plus `NOC_needs_NDC` for the carve-out below.

---

## 3. The missing array and where it actually comes from

**Quote:** "the current common-name and all-codes fields are built bottom-up from codes already observed in the dataset, so the array of all possible codes per common name doesn't exist" (Curtis, 3:23, addressed to Ryan)

What it names: the structural blocker. A bottom-up array can never contain a code the panel has not billed yet, so membership tested against it is circular.

Fix, step by step:
1. Ingest the CMS quarterly ASP NDC-HCPCS crosswalk: every Medicare-payable NDC and the code it bills under.
2. Ingest the DME drug fee schedule for the pump and SCIG channel codes the ASP file lacks.
3. Ingest the FDA NDC directory to resolve every NDC to its nonproprietary name (the molecule).
4. Normalize on ingest: NDC to digits-only 11-digit, HCPCS uppercased, names lowercased.
5. Roll up to the molecule so each carries its complete HCPCS array and complete NDC array, top-down.
6. Refresh quarterly with the ASP file; header sniffing tolerates CMS column drift.

Where it lives: v32 `crosswalk_builder.build_crosswalk`, flags `--asp-crosswalk`, `--fda-ndc`, `--dme-fee`, shipped example `asp_ndc_hcpcs_example.csv` as offline fallback. Infliximab in the example carries J1745 plus Q5103, Q5104, Q5121.

**Quote:** "J3490, J3590, and C9399 carry many molecules, so 'if the drug is in, all its codes are in' cannot admit every claim on a shared NOC code" (report, the required exception)

What it names: the one place the drug-level rule must not apply wholesale. A shared miscellaneous code is not evidence of identity.

Fix, step by step:
1. On any row billing a catch-all code, adjudicate membership by that row's own NDC through the crosswalk.
2. If the NDC maps to an in-scope molecule or appears on the formulary directly, the row is in.
3. If the NDC is blank or unmapped, route the row to a review bucket, counted in dollars and visible, never silently included or excluded.

Where it lives: v32 `NOC_needs_NDC` flag inside `DualFlag_Membership`; v31 `common_name.py` refuses to resolve identity through a miscellaneous code.

**Quote:** the Inflectra list "where gapping occurs at particular NDCs under a J-code rather than the whole code" (Nico, 1:59)

What it names: gaps live at the NDC grain even when the code is included, so the worklist must be NDC-level.

Fix, step by step:
1. For every in-scope molecule, list its complete NDC array from the crosswalk.
2. Mark which NDCs appear in the panel and with what dollars; flag the absent ones.
3. Work the gapped NDCs individually; never treat the whole code as gapped.
4. For J-code rows with a blank NDC, redistribute their dollars across the molecule's observed NDC mix, stamped, with anything unattributable reported rather than forced (v33).

Where it lives: v32 `crosswalk_builder.ndc_gap_targets`, tab `NDC_Gap_Targets`; v33 `crosswalk_builder.ndc_attribution`, tab `NDC_Attribution_Audit`, attribute `_ndc_attributed`, `unattributed_dollars` reported. Selftest: 60/40 split of blank-NDC dollars across the observed mix.

**Quote:** "the no-force-mapping rule for NDCs without natural J-code matches" (mid-meeting decision)

What it names: an NDC with no legitimate code home must not be misstated into someone else's code.

Fix, step by step:
1. Attempt NDC-to-J-code mapping only through the crosswalk.
2. On no match, keep the row as an NDC-grain row with its own identity (`NO_JCODE_KEEP_AS_NDC`).
3. Count it, display it, never merge it.

Where it lives: v31 `ndc_jcode.py`, status `NO_JCODE_KEEP_AS_NDC`, enforced in the grouper and preserved through every downstream tab.

---

## 4. One universe everywhere

**Quote:** "reuse the in/out flags Ryan built for the Komodo pull" (Evan's decision, 1:45)

What it names: the Medicare/Medicaid work and the commercial work must share one inclusion universe or every cross-source comparison is confounded.

Fix, step by step:
1. Define the universe once, at the molecule grain, on total panel spend (floor plus exclusions).
2. Freeze the resulting key set and persist it.
3. Apply the frozen keys identically to every source; no source re-derives membership.
4. Run the parity check before any cross-source chart: flag molecules present in some sources and absent in others, and any observed molecule outside the frozen universe.

Where it lives: v32 `universe.frozen_universe_keys` and `apply_frozen_universe`; v33 `cross_source.py`, tabs `CrossSource_Molecule_Matrix` and `Scope_Parity_Check` (hazards `PRESENT_IN_SOME_SOURCES_ONLY`, `OUT_OF_FROZEN_UNIVERSE_BUT_OBSERVED`), keyed off `_claim_source` when the pharmacy feed is present.

**Quote:** "a spend floor around $1M applied at the drug grain" and "define the floor once on total panel spend and freeze the resulting universe across all sources, otherwise drugs flicker in and out" (mid-meeting; the notes flag $1M as "e.g.")

What it names: the floor is a market-definition parameter, currently unpinned, and per-source floors cause flicker.

Fix, step by step:
1. Apply the floor once, at the molecule grain, on total panel spend.
2. Freeze the result (step above) so no per-source recomputation can flip a molecule.
3. Because the notes say "e.g.", run the floor at 0.5x, 1x, and 2x and report molecule count, spend share, and top-10 stability at each; either the floor does not matter (safe as stated) or it does (pin it before charting).

Where it lives: v32 `universe.define_universe`, flag `--spend-floor`; v33 `market_view.floor_sensitivity`, tab `Floor_Sensitivity`, verdict line pin-or-safe.

**Quote:** "quantify the excluded tail ('drugs below floor represent X% of spend')" (mid-meeting)

What it names: the reader's first question about any floor.

Fix, step by step:
1. Sum spend on below-floor molecules and print it as a share of the panel.
2. Keep the excluded molecules listed, not deleted, so the tail is inspectable.

Where it lives: v32 `Universe_Definition` tab, excluded-tail share printed; below-floor rows carry status, never dropped.

**Quote:** "Striking it is a market-definition act, not data cleaning, so it belongs on a documented exclusion list with one-line rationales, because it will be the first thing a reader clicks on" (mid-meeting, on Keytruda)

What it names: manual exclusions must be governed and citable, not ad hoc.

Fix, step by step:
1. Maintain a market-exclusion register: molecule, action, one-line rationale, decided-by, date.
2. Let explicit excludes win over any accidental formulary match, so a deliberate strike cannot be overridden.
3. Ship the register as a first-class tab so the click lands on a documented decision.

Where it lives: v31 `EXCLUDE_CONFIRMED` lane in `formulary.py`; v32 `exclusion_register` and seed `market_exclusions_seed.csv` with quoted rationales, tab `Exclusion_Register`.

---

## 5. Naming, grouping, and the client-facing grain

**Quote:** "add drug names" to the Tableau tabs (mid-meeting request)

What it names: common name is the client-facing display grain; codes alone are not reviewable.

Fix, step by step:
1. Carry `drug_common_name` on every row from the grouper forward.
2. Emit it on every analytic tab so nothing ships as a bare code.

Where it lives: v31 `common_name.py`; every v31+ tab carries the name column.

**Quote:** "rituximab-class products are the classic case where a single dominant-code decision determines whether a nine-figure molecule is in or out of the universe" (mid-meeting)

What it names: split-code molecules are the highest-stakes grouping decisions.

Fix, step by step:
1. Group split codes under one molecule (Stelara across J3357, J3358, and its J3590 residue; infliximab across J1745 and the Q-codes).
2. Flag genuine straddlers (rituximab across oncology and immunology indications) for a documented dominant-therapy review instead of a silent default.
3. Spot-check the known split molecules in the selftest so a regression cannot ship.

Where it lives: v31 `common_name.py` split-code grouper; v32 `therapy_area.dominant_therapy_review` with `STRADDLE` notes only on genuine straddlers, seed `therapy_area_seed.csv`.

**Quote:** "a computed acute share of 22% inside the client's 20 to 26% band is a joint test of the grouper and the mapping" (mid-meeting)

What it names: the one external validation the client handed over.

Fix, step by step:
1. Map grouped spend to the client's three-letter therapy codes.
2. Compute the acute share and test it against the 20 to 26 band.
3. Report pass or fail as a joint verdict on grouper plus mapping; a miss means one of them, not the market, moved.

Where it lives: v32 `therapy_area.acute_share_check`, tab `TherapyArea_AcuteShare`, flag `--therapy-map`. Selftest pins 22 inside the band.

**Quote:** "IG as the volume engine and shared risk, rare/orphan as the moat story" (mid-meeting)

What it names: the chronic book needs subdividing or the narrative flattens.

Fix, step by step:
1. Subdivide chronic into IVIG and rare/orphan lanes in the therapy map.
2. Report each lane's spend and share so the volume-engine and moat stories are separately quantified.

Where it lives: v32 `therapy_area.chronic_subdivision`, tab `TherapyArea_Chronic_Subdivision`.

---

## 6. The Komodo pivot and the gross-up

**Quote:** "$254M in Part D, $11M in Medicaid, and MA grossed up through a 14.1% coverage ratio" (Kyle's numbers)

What it names: the new market page. Three numbers, one of them a ratio-driven estimate.

Fix, step by step:
1. Reconcile captured Part D and Medicaid dollars against the stated observed figures.
2. Compute the MA gross-up explicitly from captured MA and the ratio, with the multiplier printed.
3. Show exposure: how much of the final market number is observed versus manufactured by the ratio.

Where it lives: v32 `coverage_grossup.grossup_estimate` and `grossup_panel`, tab `Coverage_Grossup`, flags `--coverage-ratio`, `--ma-captured`, `--part-d-observed`, `--medicaid-observed`.

**Quote:** "1/0.141 is a 7.1x multiplier, and two points of coverage-ratio error move the MA market estimate by roughly fifteen to seventeen percent" (report arithmetic)

What it names: the page's sensitivity to a single parameter.

Fix, step by step:
1. Run the gross-up at the stated ratio plus and minus two points.
2. Print the swing in dollars and percent next to the point estimate.
3. Never chart the point estimate without the band.

Where it lives: v32 `coverage_grossup.grossup_sensitivity`, tab `Grossup_Sensitivity`. Selftest pins the 15 to 17 percent swing.

**Quote:** "a ratio computed on lives applied to dollars silently assumes Komodo's captured payers carry the market's drug mix" (report)

What it names: the hidden assumption under the 14.1.

Fix, step by step:
1. Compare the captured drug mix to the census drug mix per molecule (parity index per drug).
2. Score the spend-weighted deviation; MATCHES clears the assumption, DIVERGES bans the blended ratio and routes to per-drug ratios.
3. Compute the per-drug ratios from the calibration table (next section) so the replacement exists the moment the blend fails.

Where it lives: v33 `coverage_grossup.mix_parity`, tab `Mix_Parity`; per-drug ratios from `calibration.komodo_ffs_calibration`. Selftest: skewed mix flagged DIVERGES.

**Quote:** "the referents of 254 and 11 are ambiguous in the notes (target-attributed spend versus universe-wide observed spend)" (report)

What it names: a stated ratio nobody can reproduce is a stated ratio nobody should chart.

Fix, step by step:
1. Obtain the components: captured and universe dollars per payer class.
2. Recompute the implied blend and compare to the stated 14.1 within half a point.
3. Print REPRODUCED or NOT REPRODUCED; a NOT REPRODUCED verdict blocks the ratio from the page until the referents are resolved.

Where it lives: v33 `coverage_grossup.ratio_decomposition`, tab `Ratio_Decomposition`, flag `--ratio-components`.

**Quote:** "the Medicaid figure deserves its own asterisk since managed-Medicaid capture varies enormously by state, making that gross-up the least stable number on the page" (report)

What it names: the asterisk needs a number.

Fix, step by step:
1. Load per-state managed-Medicaid coverage ratios.
2. Compute per-state multipliers and estimates where captured dollars are supplied.
3. Score the dispersion (coefficient of variation) into HIGH, MEDIUM, LOW stability; LOW means gross up state by state or carry a range, never one blended number.

Where it lives: v33 `coverage_grossup.medicaid_state_grossup`, tab `Medicaid_State_Grossup`, flag `--medicaid-state-ratios`. Selftest: wide state ratios score LOW.

**Quote:** "VRDC's residual role becomes calibration, a 100% FFS census against which to validate Komodo's FFS coverage drug by drug" (report resolution)

What it names: VRDC is demoted from primary source to the yardstick.

Fix, step by step:
1. Load Komodo FFS captured dollars and the VRDC FFS census per drug.
2. Compute the per-drug coverage ratio; flag thin capture below five percent where any gross-up is unstable.
3. Report the computed blend against the stated 14.1 in points, and the ratio span across drugs; a wide span is the argument for per-drug gross-ups.

Where it lives: v33 `calibration.komodo_ffs_calibration`, tab `Komodo_FFS_Calibration`, flags `--komodo-ffs`, `--vrdc-census`.

**Quote:** "FFS files carry no usable MA payment, and home infusion is structurally underweight in traditional FFS" (report, book structure)

What it names: half the miss may be the book, not the data. MA volumes exist even where MA payment does not.

Fix, step by step:
1. Price MA encounter units at an FFS allowed-per-unit or the ASP payment limit, every dollar stamped proxy-priced, unpriced drugs excluded and never guessed.
2. Triangulate three legs: the ratio gross-up, the proxy estimate, management's figure.
3. CONVERGENT within twenty percent clears the number for the page; DIVERGENT blocks a point estimate and makes the reconciliation the finding.
4. Feed the median leg into the deficit diagnosis as the book-structure dollar estimate.

Where it lives: v33 `ma_proxy.py`, tabs `MA_Proxy_Estimate` and `MA_Triangulation`, flags `--ma-encounters`, `--ma-prices`, `--asp-limits`, `--management-ma`.

---

## 7. The deficit, diagnosed instead of described

**Quote:** "a home infusion provider's traditional Medicare footprint runs disproportionately through the DME file (pump codes plus drugs billed to DME MACs), the home infusion therapy G-codes, and Part D PDE events, not Carrier and Outpatient files" (report, claim-type scope)

What it names: the most likely upstream cause of the halved pull is the files requested.

Fix, step by step:
1. Classify every claim by channel: Part B medical, DME supply, HIT professional (G0068 to G0090), Part D SAD.
2. Report captured dollars by channel against the channels a home-infusion book should show.
3. Flag the scope gap in dollars: the mass sitting in channels the original pull never requested.

Where it lives: v32 `deficit_diagnostics.classify_claim_channel` and `claim_scope_coverage`, tab `ClaimScope_Coverage`.

**Quote:** "the master list carries 270 NPIs the client file lacks, attributed to historical acquisitions with declining revenue" and "dropping retired billing entities manufactures artificial growth as volume migrates from legacy NPIs to surviving ones" (reconciliation finding)

What it names: the roster decision that quietly rewrites the growth rate.

Fix, step by step:
1. Compute per-period dollars on the full roster and on the surviving-only roster, with the legacy share printed.
2. Compute CAGR both ways; the surviving-only figure minus the full figure is the artificial growth in points, with the verdict naming it.
3. Estimate entity leakage: panel dollars on NPIs absent from the full roster, the ceiling on the entity-roster hypothesis, top absent NPIs listed for resolution.

Where it lives: v33 `roster_forensics.py`, tabs `Legacy_NPI_Migration`, `Artificial_Growth_Test`, `Entity_Leakage_Estimate`, flags `--roster-npis` (full list) and `--surviving-roster`. Selftests cover the inflation verdict and the leakage ceiling.

**Quote:** "A finder list assembled from medical-claims presence can reconcile perfectly against a client file and still miss the government-billing subset" (Joe's question)

What it names: reconciliation success is not roster completeness; government channels sit outside the medical panel.

Fix, step by step:
1. Classify roster NPIs by channel (government pharmacy versus commercial medical) via taxonomy and enrollment evidence.
2. Reconcile the client list against the panel with the government subset broken out, so absence from the panel is explained rather than alarming.

Where it lives: v31 `npi_channel.py`, tab `NPI_Channel_Reconciliation`, flag `--gov-npi-list`.

**Quote:** "the most useful answer back is not a flat NPI list but a mapping of which entities are enrolled where (pharmacy NPIs, DMEPOS numbers, HIT enrollment), plus whether health-system joint venture entities bill under their own NPIs in neither file" (report)

What it names: the data request should be an enrollment map, not a list.

Fix, step by step:
1. Structure the entity file as NPI by enrollment channel: Part D pharmacy, DMEPOS supplier, HIT supplier.
2. Flag joint-venture entities explicitly.
3. Report enrollment coverage: which channels each entity can even appear in, so a missing entity-channel pair is a request item, not a mystery.

Where it lives: v32 `npi_enrollment.py`, tab `Enrollment_File_Coverage`, channel map `CHANNEL_FILE`, JV flags.

**Quote:** "the cheap test from the morning, recomputing the unblinded VRDC totals with no formulary filter and again under drug-level inclusion, appears nowhere in the notes and is worth an hour" (report)

What it names: the decisive experiment nobody ran.

Fix, step by step:
1. Recompute totals three ways on every build: unfiltered, code-level rule, drug-level rule.
2. Print the recovered delta between code-level and drug-level: the false-exclusion mass, and the self-inflicted share of the low total.
3. Auto-derive the two masks from the dual-flag membership so the test costs zero marginal effort and cannot be skipped.

Where it lives: v32 `deficit_diagnostics.filter_attribution_test`; v33 wires it into every build as tab `Filter_Attribution` whenever `--formulary-codes` is supplied, and feeds the self-inflicted line into the deficit scorer.

**Putting the four together.** The deficit diagnosis scores all four hypotheses in dollars: claim-type scope (from `ClaimScope_Coverage`), entity leakage (from `Entity_Leakage_Estimate`), book structure (from `MA_Triangulation`), and self-inflicted filtering (from `Filter_Attribution`). In v33 all four feed automatically; no hand-typed numbers. A cause at forty percent or more of the gap is named dominant.

Where it lives: v32 `deficit_diagnostics.diagnose_deficit`; v33 self-fed `Deficit_Diagnosis` tab, flag `--expected-total`.

---

## 8. Protecting the fallback analysis

**Quote:** "the vendor-agnostic market view survives" and the team had "signaled a few times" (Joe, 0:52)

What it names: the retreat position. Everything below exists so the retreat position is actually safe.

Fix, step by step:
1. Run the surviving analyses on the grouped, drug-level, frozen universe: biosimilar adoption per molecule-year, panel rate versus the ASP payment limit per code, floor sensitivity.
2. Gate them behind the integrity checks in this section so the fallback cannot inherit the original defect.

Where it lives: v33 `market_view.py`, tabs `Biosimilar_Adoption`, `ASP_Rate_Position`, `Floor_Sensitivity`, flag `--asp-limits`.

**Quote:** "Code-level exclusion doesn't just shrink volume, it bends trends: the excluded share moves over time as NDCs rotate through package changes, labeler changes, and biosimilar entry, which can manufacture spurious mix shifts in exactly the vendor-agnostic analysis they're retreating to" (report, the sharpest unfixed claim)

What it names: the failure mode that would follow the team into the fallback.

Fix, step by step:
1. Compute the excluded share by period under the code-level rule and the drug-level rule side by side; the divergence is the false-exclusion share, and divergence that drifts across periods is the trend bend, printed in points.
2. Decompose each molecule's apparent share shift into the inclusion artifact and the real movement (artifact equals apparent minus real), sorted by absolute artifact.
3. List the concrete flicker events driving it: a biosimilar Q-code entering mid-window, a new NDC appearing under an existing molecule, each dated.

Where it lives: v33 `trend_integrity.py`, tabs `Trend_Bend_Audit`, `Trend_Bend_Decomposition`, `Inclusion_Flicker_Events`. Selftests pin the 28.6-point divergence drift and the Q5103 flicker event on the Inflectra pattern.

**Quote:** "The grouper fix is load-bearing for both views" (report)

What it names: the v31 grouper is not a cleanup detail; the Komodo pivot and the fallback both stand on it.

Fix, step by step:
1. Keep the grouper deterministic and reference-driven (sections 3 and 5).
2. Regression-pin the known split molecules in the selftest so no later change can silently un-group them.
3. Run every v32 and v33 analysis downstream of the grouper, never on raw codes.

Where it lives: v31 `common_name.py`; 151 selftests, all offline, gate every release.

---

## Note on the notes themselves

Three defects in the meeting notes are worth flagging when citing them: "G" and "Curtis" are the same attendee counted twice; Nick Herro is present in the meeting but erased from the attendee list while Christine appears with no attributed content; and "higher or expected spend" is a transcription garble, most plausibly "higher and closer to expected." None of these change the fixes above, but quote the notes with these corrections in hand.

---

Every module named here ships in `NPI_Recovery_and_Cleaner_v33.zip`, offline-safe with honest no-op notes when an input is absent, no sklearn, no scipy, no LLM calls, hand-rolled numpy and pandas only. Missing inputs never fabricate rows; nothing is invented above a suppression ceiling; NPI recovery output is byte-identical to prior versions when no new inputs are supplied.
