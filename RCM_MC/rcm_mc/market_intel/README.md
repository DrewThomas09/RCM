# market_intel/

**Public-market context layer** — 7 files covering public healthcare-operator comparables, curated PE-transaction library, target-relevant news feed, and peer-snapshot drop-in for any target-aware page.

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring — public comps + PE multiples + news layer. |
| `adapters.py` | **Vendor adapters** — Protocol-per-source pattern, same as `integrations.{chart_audit,contract_digitization}`. Keeps the data-contract layer separate from the fetchers. |
| `public_comps.py` | **Public-operator comparables loader + comparable-finder.** Given target category + size → relevant public comps (HCA / THC / CYH / UHS / EHC / ARDT / PRVA / DVA / FMS / SGRY / UNH / ELV / MPW / WELL — 14 operators). |
| `peer_snapshot.py` | **Drop-in peer-comparison component** for any target-aware page. "Your target vs public comps" in one compact block. Used by HCRIS X-Ray and Deal Profile. |
| `pe_transactions.py` | **Curated healthcare PE transaction library.** Loads YAML fixture at `content/pe_transactions.yaml` → sponsor, target, multiple, narrative, outcome for each named transaction. |
| `transaction_multiples.py` | Private-market PE transaction multiple lookups — segment bucket → P25/P50/P75 multiples. |
| `news_feed.py` | **Curated news-feed loader + target-relevance filter.** Takes a target profile → filters aggregated news for relevance. |

## Where it plugs in

- **`/market-intel/seeking-alpha`** page (`ui/seeking_alpha_page.py`) — 3 stacked sections (public comps + PE transactions + sentiment/news)
- **HCRIS X-Ray page** — `peer_snapshot` rendered in the public-market-context block
- **Deal Profile** — sector-sentiment pull from `news_feed`

## The curated data layer

`pe_transactions.yaml` and `public_comps.yaml` under `market_intel/content/` are **hand-curated, refresh weekly**. Source format matches — named sponsor + target + rationale + outcome. Never auto-scraped into these files; auto-scraped feeds populate the news_feed but not the transaction library.

## Distinction from `data_public/`

- `market_intel/` = **public-market context** (listed stocks + named deals + live news)
- `data_public/` = **corpus intelligence** (the 635+ healthcare-PE transaction corpus used for benchmarking)

Different audiences, different refresh cadence, different data model.

## Related

- `cms_medicare-master/` — source for some comp multiples (ported)
- `ui/seeking_alpha_page.py` — primary renderer
- `integrations/` — same adapter pattern for vendor sockets
