"""Provenance tracking: every number has a story.

The #1 partner complaint against the platform was "I don't know where
any number came from." This subpackage fixes that: every scalar the
platform shows a partner is backed by a :class:`DataPoint` describing
what produced it, what it was built from, and how confident we are.

Public API::

    from rcm_mc.provenance import (
        DataPoint,
        Source,
        ProvenanceRegistry,
    )
"""
from .tracker import DataPoint, Source
from .registry import ProvenanceRegistry
from .graph import (
    EdgeRelationship,
    NodeType,
    ProvenanceEdge,
    ProvenanceGraph,
    ProvenanceNode,
    build_rich_graph,
)
from .explain import explain_for_ui, explain_metric

__all__ = [
    "DataPoint", "Source", "ProvenanceRegistry",
    "ProvenanceGraph", "ProvenanceNode", "ProvenanceEdge",
    "NodeType", "EdgeRelationship", "build_rich_graph",
    "explain_metric", "explain_for_ui",
]
