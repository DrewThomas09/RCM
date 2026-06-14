# RxNorm / RxNav connector — DECISIONS

Append-only record of judgement calls made while building this slice, with the
rationale, so a future maintainer (or a resumed run) doesn't re-litigate them.

## D1 — Package home: `rcm_mc/data_public/rxnorm/`
The spec says "Own: `connectors/rxnorm/`". This repo's public-data API
connectors live under `rcm_mc/data_public/` (NPPES, openFDA loaders, the shared
`public_api_clients` transport, the `public_api_catalog` / `open_data_registry`
registries). To stay idiomatic and reuse the existing registry/catalog wiring,
the connector lives at `rcm_mc/data_public/rxnorm/` as a self-contained
subpackage — the same intent as `connectors/rxnorm/`, in the location this
codebase actually keeps connectors.

## D2 — Offline by default; live ingestion is opt-in
Outbound calls to `rxnav.nlm.nih.gov` are blocked in this environment (verified:
HTTP 403). A live bulk backfill cannot run here, so the pipeline defaults to an
offline **representative seed** (`seed.py`) that renders RxNav-native JSON
through the same connector parse path. Pass `live=True` (or `--live`) to use the
real `urllib` opener where the network policy permits. The seed is small but
deliberately covers every DQ edge case (NDC format drift, a retired→remapped
RxCUI, all three drug-class types, and the exact openFDA shortage NDCs). This
keeps the pipeline verifiable and the DQ tests deterministic rather than
shipping an empty, untested pipeline.

## D3 — Storage is SQLite, raw landing is JSON (not parquet)
The spec mentions "land raw to parquet, then normalize." This repo is
stdlib-only (no pyarrow/pandas-parquet in the runtime contract) and stores
everything in SQLite via `PortfolioStore`. We conform to the repo: normalized
tables are SQLite; "raw landing" is the native RxNav JSON the connector parses
(seeded here, fetchable live). Adding a parquet dependency would violate the
"no new runtime dependencies" rule in CLAUDE.md.

## D4 — `/v1/query` and lookups are a router-agnostic library, not new routes
The spec's API contract describes `/v1/query/{dataset}` and
`/v1/lookup/rxnorm/...`. This repo's HTTP server (`server.py`,
`http.server`-based) has **no `/v1` router and no plugin-registration surface**,
and the `/v1` router core is explicitly out of scope to edit. So `query.py`
exposes the uniform filter/select/sort/paginate contract and the rxnorm-
namespace lookups as plain functions a router *could* register, with the
intended routes documented. We never define `/v1/lookup/drug/{ndc}` (openFDA
owns it) — lookups live under the `rxnorm` namespace per the collision warning.

## D5 — Self-contained transport (not the shared `HttpJsonClient`)
RxNav's rate-limit/retry semantics are specific: ~20 req/s/IP and 429/503 must
be retried with exponential backoff **plus jitter**, honouring `Retry-After`.
The shared `public_api_clients.HttpJsonClient` treats every `<500` as a hard
fail (so it would not retry a 429) and has no jitter. Rather than modify shared
infra used by other clients, the connector carries its own transport with the
RxNav-correct behaviour. The contract ("rate-limit handling and retries
internal to the connector") points the same way.

## D6 — NDC canonical form = 11-digit, hyphen-free 5-4-2; raw retained
Every NDC is reduced to the HIPAA 11-digit 5-4-2 form and the raw value is kept
alongside it in `xwalk_ndc_rxcui.ndc_raw`. Hyphenated inputs are disambiguated
by segment length (4-4-2 / 5-3-2 / 5-4-1 / 5-4-2). An **unhyphenated 10-digit**
NDC is genuinely ambiguous — the segmentation is unknowable without hyphens — so
we apply a configurable assumption (`assume_unhyphenated_10`, default `4-4-2`,
i.e. prepend one zero to the labeler, the most common case) and fail loud on
anything that cannot be a valid NDC, because a wrong key silently drops records.

## D7 — Retired/remapped resolution chases the remap chain
`dim_rxnorm_concept` stores `status` + `remapped_to_rxcui`. `store.resolve_rxcui`
follows `remapped_to_rxcui` until it reaches an active concept (depth-guarded
against cycles), and `lookup_ndc` resolves the crosswalk's stored rxcui through
that chain so a stale/remapped code does not drop the joined record. The
crosswalk row records the concept's own status so the remap state travels with
the NDC.

## D8 — Class-type vocabulary normalized to {ATC, therapeutic, mechanism_of_action}
RxClass exposes many `classType` values (ATC1-4, VA, MESHPA, EPC, DISEASE, MOA,
PE, CHEM, …). We fold them into the three the spec asks for: ATC, therapeutic,
and mechanism-of-action. The mapping lives in `normalize._CLASS_TYPE_MAP`;
unknown types default to `therapeutic`.

## D9 — openFDA join test reports the rate, doesn't assert a threshold
The read-only join against openFDA's vendored `package_ndc` column reports the
match rate rather than asserting a floor: with the offline seed only a couple of
NDCs overlap, so the check's value is proving the normalize→join→rate plumbing
works end-to-end (which is what makes a live backfill trustworthy). The seed
intentionally includes two of openFDA's shortage NDCs so `matched >= 2`.
