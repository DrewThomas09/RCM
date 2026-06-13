# RxNorm / RxNav connector — STATE

Filesystem-as-memory checkpoint. The pipeline resumes from the JSON
block at the bottom; re-running is idempotent (upserts keyed by rxcui
/ ndc_11), so a hard kill loses no committed work.

- **RRF release / concept-source version:** seed-2026-06 (offline representative slice)
- **Last run (UTC):** 2026-06-13T23:17:22.071304+00:00
- **Last concept batch cursor:** complete
- **Last NDC resolved:** 55150031301
- **Concepts enriched:** 9
- **Open failures (requeued next run):** 0

## Cumulative row counts

- `xwalk_ndc_rxcui`: 4
- `dim_rxnorm_concept`: 9
- `bridge_rxcui_related`: 6
- `dim_drug_class`: 10
- `dim_ndc_properties`: 4

## Drug-class coverage

- Concepts: 9; classified rxcui: 4; coverage: 44.44%
- By class type: {'ATC': 4, 'mechanism_of_action': 3, 'therapeutic': 3}

<!--STATE_JSON
{
  "class_coverage": {
    "by_class_type": {
      "ATC": 4,
      "mechanism_of_action": 3,
      "therapeutic": 3
    },
    "classified_rxcui": 4,
    "concepts": 9,
    "coverage_pct": 44.44
  },
  "counts": {
    "bridge_rxcui_related": 6,
    "dim_drug_class": 10,
    "dim_ndc_properties": 4,
    "dim_rxnorm_concept": 9,
    "xwalk_ndc_rxcui": 4
  },
  "failures": [],
  "last_concept_cursor": "complete",
  "last_ndc_resolved": "55150031301",
  "last_run": "2026-06-13T23:17:22.071304+00:00",
  "processed_rxcui": [
    "1191",
    "215568",
    "243670",
    "617312",
    "617318",
    "6902",
    "7052",
    "83367",
    "9999999"
  ],
  "release_version": "seed-2026-06 (offline representative slice)"
}
STATE_JSON-->
