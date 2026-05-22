"""Local evaluation harness for the PEdesk Guide (read-only, local).

A quality gate, NOT a product feature: it runs a fixed set of
representative questions against the Guide in packet-only and RAG modes
and scores the answers with read-only / honesty heuristics. No uploads,
no memory, no mutation, no persistence beyond a local ignored report
folder. Requires a local Ollama to actually call the model.
"""
