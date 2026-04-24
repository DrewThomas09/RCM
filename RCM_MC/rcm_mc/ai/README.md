# AI

LLM-powered features for natural-language interaction with the platform. Wraps the Anthropic Messages API with cost tracking, response caching, and graceful fallback when no API key is configured.

---

## `llm_client.py` — Anthropic Messages API Wrapper

**What it does:** Wraps the Anthropic API (claude-sonnet-4-6 or claude-opus-4-7 based on task complexity) with cost tracking, response caching, and a no-op fallback when `ANTHROPIC_API_KEY` is not set.

**How it works:** `LLMClient` class with `complete(prompt, system, model, max_tokens)` method. If `ANTHROPIC_API_KEY` is unset, returns a structured fallback response (template-generated text, not a real LLM response). Otherwise: calls the Anthropic Messages API via `urllib.request` (no third-party HTTP lib), parses the JSON response, logs the call to the `llm_calls` SQLite table (model, prompt hash, tokens used, cost estimate, cached). Caches: if an identical prompt hash has been called within the last 24 hours, returns the cached response without calling the API. Cost tracking: `input_tokens × model_price + output_tokens × model_price`.

**Data in:** Prompt and system strings from calling modules; `ANTHROPIC_API_KEY` environment variable.

**Data out:** LLM response text; cost/token log entry in `llm_calls` table.

---

## `conversation.py` — Multi-Turn Portfolio Chat

**What it does:** Multi-turn conversational interface that dispatches natural-language portfolio questions to platform functions via tool-calling. "Which deals have denial rates above 12%?" → calls `analysis/deal_query.py`.

**How it works:** Maintains conversation history in memory (per-session). On each user message: builds a system prompt describing available tools (deal query, metric lookup, analysis summary, cross-deal search). Sends to the LLM with the tool schemas. If the LLM calls a tool, executes the corresponding platform function and feeds the result back as a tool result. If the LLM produces a text response, returns it directly. Supported tools: `query_deals`, `get_deal_metrics`, `get_analysis_summary`, `search_notes`, `get_portfolio_stats`. Falls back to a static FAQ when LLM is unavailable.

**Data in:** User message from `POST /api/chat`; conversation history (in-session); platform data via tool dispatch.

**Data out:** LLM response text (or tool dispatch result) for the chat UI.

---

## `document_qa.py` — Per-Deal Document Q&A

**What it does:** Indexes deal documents and answers natural-language questions about them. "What did the seller say about their denial management program?" → searches the CIM and returns the relevant passage.

**How it works:** On document upload: splits the document into 500-token chunks with 50-token overlap, stores chunks in the `document_chunks` SQLite table with deal_id and document_id. On query: tokenizes the query, computes keyword overlap scores between the query and each chunk (TF-IDF-style without a vector database), retrieves the top-3 chunks. If LLM is available: synthesizes the chunks into a coherent answer with source citations. If not: returns the top chunk verbatim with a confidence score.

**Data in:** Uploaded documents from `data/data_room.py`; natural-language query from `GET /api/deals/<id>/qa?q=...`.

**Data out:** Answer text with source citations (document name, page/section) for the deal Q&A panel.

---

## `memo_writer.py` — LLM-Assisted IC Memo Composer

**What it does:** Generates an IC memo draft with automatic fact-checking of all dollar amounts and percentages against the source `DealAnalysisPacket`. Flags any number the LLM generated that doesn't match the packet.

**How it works:** Builds a structured prompt including the deal's key metrics, bridge summary, risk flags, and comparable context. Calls the LLM to generate the memo body (executive summary, investment thesis, key risks, value creation plan, returns summary). After generation: extracts all dollar and percentage values from the generated text using regex, cross-checks each value against the packet (within 1% tolerance), and flags mismatches as `[UNVERIFIED: LLM says $X, packet shows $Y]`. Returns the memo text with any flags for analyst review before use.

**Data in:** `DealAnalysisPacket` for fact-checking; deal notes from `deals/deal_notes.py` for narrative context; LLM from `llm_client.py`.

**Data out:** Draft IC memo HTML with verification flags for `GET /api/deals/<id>/memo?llm=1`.

---

## Key Concepts

- **Graceful degradation**: Every AI feature returns a useful fallback (template-based memo, raw search chunks, query-interface redirect) when the LLM is not configured. The platform is fully functional without any LLM key.
- **Fact-checking**: Generated text is cross-checked against packet data; numbers not found within 1% tolerance are flagged as warnings — the analyst is always the final check.
- **Cost tracking**: All LLM calls are logged to a SQLite `llm_calls` table; identical prompts are served from cache.
