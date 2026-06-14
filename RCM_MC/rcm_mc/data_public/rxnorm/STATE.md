# RxNorm / RxNav connector — STATE

Filesystem-as-memory checkpoint. The pipeline resumes from the JSON
block at the bottom; re-running is idempotent (upserts keyed by rxcui
/ ndc_11), so a hard kill loses no committed work.

- **RRF release / concept-source version:** seed-2026-06 (offline representative slice)
- **Last run (UTC):** 2026-06-14T00:05:13.214957+00:00
- **Last concept batch cursor:** complete
- **Last NDC resolved:** 62037072701
- **Concepts enriched:** 18
- **Open failures (requeued next run):** 0

## Cumulative row counts

- `xwalk_ndc_rxcui`: 9
- `dim_rxnorm_concept`: 18
- `bridge_rxcui_related`: 6
- `dim_drug_class`: 33
- `dim_ndc_properties`: 9

## Drug-class coverage

- Concepts: 18; classified rxcui: 13; coverage: 72.22%
- By class type: {'ATC': 13, 'mechanism_of_action': 12, 'therapeutic': 8}

<!--STATE_JSON
{
  "class_coverage": {
    "by_class_type": {
      "ATC": 13,
      "mechanism_of_action": 12,
      "therapeutic": 8
    },
    "classified_rxcui": 13,
    "concepts": 18,
    "coverage_pct": 72.22
  },
  "counts": {
    "bridge_rxcui_related": 6,
    "dim_drug_class": 33,
    "dim_ndc_properties": 9,
    "dim_rxnorm_concept": 18,
    "xwalk_ndc_rxcui": 9
  },
  "failures": [],
  "last_concept_cursor": "complete",
  "last_ndc_resolved": "62037072701",
  "last_run": "2026-06-14T00:05:13.214957+00:00",
  "processed_rxcui": [
    "1191",
    "17767",
    "215568",
    "243670",
    "2598",
    "29046",
    "40048",
    "48937",
    "617312",
    "617318",
    "6470",
    "6809",
    "6901",
    "6902",
    "7052",
    "7646",
    "83367",
    "9999999"
  ],
  "release_version": "seed-2026-06 (offline representative slice)"
}
STATE_JSON-->
