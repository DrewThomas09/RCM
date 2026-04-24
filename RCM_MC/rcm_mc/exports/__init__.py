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
from .ic_packet import (  # noqa: F401
    ICPacketMetadata,
    render_ic_packet_html,
)
from .qoe_memo import (  # noqa: F401
    QoEMemoMetadata,
    render_qoe_memo_html,
)

__all__ = [
    "PacketRenderer", "list_exports", "record_export",
    "QoEMemoMetadata", "render_qoe_memo_html",
    "ICPacketMetadata", "render_ic_packet_html",
]
