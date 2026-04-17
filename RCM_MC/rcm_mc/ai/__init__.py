"""AI-assisted analysis — LLM client, memo writer, conversation, document QA.

All LLM features degrade gracefully when the API key is absent: the
platform continues to function using template-based rendering and
keyword search.  No new runtime dependencies beyond stdlib + numpy.
"""
