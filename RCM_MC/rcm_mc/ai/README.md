# AI

LLM-powered features for natural-language interaction with the platform. Wraps the Anthropic Messages API with cost tracking, response caching, and graceful fallback when no API key is configured. All LLM features are "optional acceleration" -- the platform works without them.

| File | Purpose |
|------|---------|
| `llm_client.py` | Anthropic Messages API wrapper with cost tracking, response caching, and no-op fallback when `ANTHROPIC_API_KEY` is unset |
| `conversation.py` | Multi-turn conversational interface that dispatches natural-language portfolio questions to platform functions via tool-calling |
| `document_qa.py` | Per-deal document indexing, chunking, and keyword-overlap search with optional LLM-synthesized answers |
| `memo_writer.py` | LLM-assisted memo composition with automatic fact-checking of dollar amounts and percentages against the source packet |

## Key Concepts

- **Graceful degradation**: Every AI feature returns a useful fallback (template-based memo, raw search chunks, query-interface redirect) when the LLM is not configured.
- **Fact-checking**: Generated text is cross-checked against packet data; numbers not found within 1% tolerance are flagged as warnings.
- **Cost tracking**: All LLM calls are logged to a SQLite `llm_calls` table; identical prompts are served from cache.
