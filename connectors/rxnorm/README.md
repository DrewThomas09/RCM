# connectors/rxnorm — RxNorm drug identity (NLM RxNav)

A self-contained, **stdlib-only** connector over the public, keyless
RxNav REST API that resolves NDCs and free-text drug names to a stable
`rxcui`, its ingredient set, and its ATC / DailyMed pharmacologic class —
normalized into canonical SQLite tables and re-exposed behind the
estate's uniform `/v1` query surface.

## Why this is in a CMS estate

RxNorm is the **join dimension for drug money**. Every drug fact table
already here identifies products by NDC or by a label name:

| Table | Connector | Identifier |
|---|---|---|
| NADAC | `medicaid_data` | NDC |
| State Drug Utilization (SDUD) | `medicaid_data` | NDC |
| Part B / Part D spending by drug | `cms_open_data` | brand + generic name |
| Part D prescriber by drug | `cms_open_data` | brand + generic name |
| NDC directory | `openfda` | NDC |

Resolving those to `rxcui` → ingredient → drug class is what turns
per-product spend into **per-ingredient and per-class** spend, and what
lets a Medicaid NADAC unit price sit next to a Medicare Part B ASP for
the same molecule. It plays the same role for drugs that `icd10` plays
for diagnoses and `hcpcs` for procedures.

## Source

`https://rxnav.nlm.nih.gov/REST` — public and keyless. Endpoints and
envelope keys used (all verified against this repo's existing production
RxNav client in `rcm_mc/npi_cleaner/vendor_v49/npi_recovery/clients.py`):

| Call | Envelope key |
|---|---|
| `/rxcui.json?idtype=NDC&id=` | `idGroup.rxnormId[]` |
| `/rxcui.json?name=&search=2` | `idGroup.rxnormId[]` |
| `/approximateTerm.json?term=&maxEntries=` | `approximateGroup.candidate[]` |
| `/rxcui/{rxcui}/properties.json` | `properties` |
| `/rxcui/{rxcui}/related.json?tty=IN` | `relatedGroup.conceptGroup[].conceptProperties[]` |
| `/rxclass/class/byRxcui.json?rxcui=&relaSource=ATC\|DAILYMED` | `rxclassDrugInfoList.rxclassDrugInfo[].rxclassMinConceptItem.className` |

**Empty results are 200s, not 404s.** RxNav answers an unresolvable
identifier with HTTP 200 and an envelope that simply lacks its payload
key, so every field access in `connector.py` goes through a defensive
digger and an unresolved identifier is *recorded*, never raised.

**Rate floor, not a contract:** the transport enforces a conservative
minimum interval between requests plus exponential backoff on 429/5xx
(`Retry-After` honored). The constants in `transport.py` are a polite
floor and are constructor-overridable.

## Datasets

| dataset_id | Target table | Roster | Grain |
|------------|--------------|--------|-------|
| `rxnorm_ndc` | `xwalk_ndc_rxcui` | `--ndcs` | NDC → RxCUI |
| `rxnorm_name` | `xwalk_name_rxcui` | `--names` | drug name → RxCUI |
| `rxnorm_concept` | `dim_rxnorm_concept` | `--rxcuis` | RxCUI → concept |

Every dataset is **roster-driven** (RxNav resolves one identifier per
request), so ingest is manual like the NPI Registry connector — the
natural roster is a distinct-NDC query against the NADAC / SDUD /
Part D tables above.

Every resolved identifier writes its concept row too, so an NDC sweep
never leaves the drug dimension empty. Because `dim_rxnorm_concept` is
keyed by `rxcui`, a concept pulled in by the NDC sweep carries
`source_endpoint='ndc'` — which is why `/v1/query/rxnorm_concept`
returns only the concepts *that* dataset resolved, not every concept in
the table. Query `dim_rxnorm_concept` through `rxnorm_concept` for the
pinned slice, or join it from either crosswalk for everything.

## Ingredient and class columns

Ingredient and class sets are stored as `; `-joined TEXT with
`n_ingredients` alongside, so single-ingredient products are filterable
without parsing. ATC and DailyMed classes live in **separate columns**
(`atc_classes` / `dailymed_classes`) with `class_source` recording which
one populated — they are different taxonomies and must not be pooled.
The DailyMed fallback exists because many biologics (immune globulin,
for instance) carry no ATC class at all, and those are precisely the
high-cost Part B injectables an analysis cares about.

## CLI

```bash
python -m connectors.rxnorm.cli --root var/connectors datasets
python -m connectors.rxnorm.cli --root var/connectors discover
python -m connectors.rxnorm.cli --root var/connectors fetch --dataset ndc --ndcs 00006-3026-02,00002-1200-01
python -m connectors.rxnorm.cli --root var/connectors fetch --dataset name --names "KEYTRUDA,STELARA"
python -m connectors.rxnorm.cli --root var/connectors fetch --dataset concept --rxcuis 1547220
python -m connectors.rxnorm.cli --root var/connectors query rxnorm_ndc --filter rxcui=1547220
python -m connectors.rxnorm.cli --root var/connectors aggregate rxnorm_name --group-by match_type
python -m connectors.rxnorm.cli --root var/connectors lookup-ndc 00006-3026-02
python -m connectors.rxnorm.cli --root var/connectors lookup-concept 1547220
python -m connectors.rxnorm.cli --root var/connectors lookup-name KEYTRUDA
python -m connectors.rxnorm.cli --root var/connectors serve
```

`--root` is the working dir holding `rxnorm.db` (`./.rxnorm_data` by
default). Read verbs (`query` / `aggregate` / `lookup-*`) never create
the dir or the db — a never-ingested root answers from an empty
in-memory store instead of littering the cwd.

## `/v1` surface

```
/v1/datasets
/v1/query/rxnorm_ndc | rxnorm_name | rxnorm_concept
/v1/query/{dataset}/aggregate?group_by=
/v1/lookup/rxnorm-ndc/{ndc}          matched on the digits-only form
/v1/lookup/rxnorm-concept/{rxcui}    concept + reverse crosswalk
/v1/lookup/rxnorm-name/{name}        case-insensitive
```

`lookup-ndc` matches on the digits-only form because CMS files spell the
same NDC as `0002-1200-01`, `00021200 01` and `00002120001` across
NADAC, SDUD and the Part D files — all three have to find the row. The
lookup nouns are `rxnorm`-prefixed so the unified estate router
(first-match-wins) can never confuse them with openFDA's
`/v1/lookup/drug/{ndc}`, which answers from the FDA NDC directory — a
different source at a different grain.

## Canonical tables

* `dim_rxnorm_concept` — `rxcui` (pk), `name`, `tty`, `synonym`,
  `ingredients`, `n_ingredients`, `atc_classes`, `dailymed_classes`,
  `class_source`, `raw`.
* `xwalk_ndc_rxcui` — `ndc` (pk), `ndc_digits`, `rxcui`,
  `resolved_name`, `raw`.
* `xwalk_name_rxcui` — `name_key` (pk, lower-cased), `query_name`,
  `rxcui`, `resolved_name`, `matched_on`, `match_type`
  (`exact` | `approximate`), `raw`.

All plus the shared `source_endpoint` / `ingested_at` meta columns.
