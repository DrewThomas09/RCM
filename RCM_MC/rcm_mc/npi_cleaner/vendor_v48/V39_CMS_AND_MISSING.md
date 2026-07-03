# V39 CMS AND MISSING

Two asks: more CMS connections, and more ways to address missing information.

## More CMS: jurisdiction-aware SAD, from real data

The self-administered-drug question has been a flat flag since v31, and a flat
flag is wrong twice. First, the SAD list is per-MAC: a drug excluded from Part
B in Texas (Novitas) can be Part B eligible in New York (National Government
Services), because each Medicare Administrative Contractor publishes its own
exclusion article. Second, the same molecule can be eligible by one route and
excluded by another: abatacept billed intravenously under modifier JA is
provider-administered and covered, while the subcutaneous form under JB is
self-administered and excluded, on the same J-code.

v39 ships sad_jurisdiction.py, built from a live pull of the CMS Coverage
Self-Administered Drug Exclusion List and the MAC roster. It maps billing state
to contractor, checks the HCPCS against that contractor's exclusion set, and
applies the route rule, returning one of five verdicts per line:
PART_B_ELIGIBLE, SAD_EXCLUDED, SAD_EXCLUDED_SC, ROUTE_AMBIGUOUS,
UNKNOWN_JURISDICTION. The SAD_Jurisdiction tab prices each verdict; the
SAD_Ambiguous_Worklist tab lists the specific lines that a modifier or a state
would resolve, so route-ambiguous dollars are a worklist, not a shrug.

The shipped snapshot is real: infliximab IV (J1745) is correctly eligible
because it is not on the list, etanercept (J1438) is excluded across all eight
MACs, and tocilizumab subcutaneous (J3262) is excluded in the Novitas and
Palmetto jurisdictions but eligible where the local MAC does not list it, all
verified in the selftest. Because a snapshot ages, refresh_from_cms re-pulls
the live list on demand when the CMS Coverage connector is passed in, and
normalizes it to the same shape for a diff before replacing the seed. It never
runs automatically; the pipeline stays deterministic and offline by default.

## More ways to close gaps: one resolver, dollars-first

Missing information was scattered across a dozen tabs with no single view of
what is missing, how much it is worth, and what fixes it. missing_resolver.py
consolidates it. gap_inventory walks the standardized frame and returns every
recoverable gap in one ranked table: blank billing NPI, blank referring NPI,
blank or ambiguous NDC, blank state, missing units on a paid line, blank payer,
and SAD route ambiguity, each priced in dollars and tiered HIGH, MEDIUM,
PARTIAL, or LOW by how deterministically it can be closed. resolution_plan
turns that into an executable action list, highest dollars first, where each
row is a concrete instruction: run --deep-clean --impute state:from_zip3,
supply the JA/JB modifier, enable the Open Payments connector, or request
hyphenated NDCs from the vendor. HIGH gaps are fillable now with a flag; LOW
gaps are honestly routed to a data request rather than chased.

The two modules connect: the resolver reads the SAD classifier, so a
route-ambiguous nine-figure code shows up in the same ranked plan as a blank
state, and the reader sees the whole recoverable surface in one place. 201
offline selftests pass, 10 of them pinning this release.
