"""PEdesk Guide page-context foundation.

Read-only structured context describing every PEdesk page/route, to
later power an explanatory (never autonomous) PEdesk Guide assistant.

Public surface (all read-only):
- get_page_context(route) / normalize_route(route)
- get_metric_context(id_or_label) / get_data_source_context(id_or_label)
- build_guide_context_packet(route) / summarize_context_packet(packet)
- GUIDE_PROMPT_POLICY / policy_as_dict()
- get_suggested_questions_for_page(page_context)
"""
from .get_page_context import get_page_context, normalize_route
from .get_metric_context import get_metric_context
from .get_data_source_context import get_data_source_context
from .guide_context_packet import (
    GuideContextPacket,
    build_guide_context_packet,
    packet_to_dict,
    summarize_context_packet,
)
from .guide_prompt_policy import GUIDE_PROMPT_POLICY, policy_as_dict
from .suggested_questions import get_suggested_questions_for_page

__all__ = [
    "get_page_context",
    "normalize_route",
    "get_metric_context",
    "get_data_source_context",
    "GuideContextPacket",
    "build_guide_context_packet",
    "packet_to_dict",
    "summarize_context_packet",
    "GUIDE_PROMPT_POLICY",
    "policy_as_dict",
    "get_suggested_questions_for_page",
]
