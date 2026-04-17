"""Packet-driven export layer.

Every export the platform emits renders from a single
:class:`DealAnalysisPacket` instance — never from direct store queries.
This is the load-bearing invariant: if the UI and the memo disagree on
a number, it's a renderer bug, not a data bug.
"""
from .packet_renderer import PacketRenderer  # noqa: F401
from .export_store import (  # noqa: F401
    list_exports,
    record_export,
)

__all__ = ["PacketRenderer", "list_exports", "record_export"]
