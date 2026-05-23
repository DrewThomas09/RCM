"""Deterministic suggested-question generation for the PEdesk Guide."""
from __future__ import annotations

import unittest

from rcm_mc.assistant.context.suggested_questions import (
    _DEFAULTS,
    _MAX_QUESTIONS,
    get_suggested_questions_for_page,
)
from rcm_mc.assistant.context.types import PageContext, PageContextCategory


def _page(**over):
    base = dict(
        route="/x", normalized_route="/x", title="X",
        category=PageContextCategory.DILIGENCE_WORKSPACE,
        source_group="diligence", source_confidence=None, data_confidence=None,
        short_description="", primary_purpose="", intended_users=[],
        common_questions=[], inputs=[], outputs=[], key_metrics=[],
        data_sources=[], model_logic_summary="", why_it_matters="",
        diligence_use_cases=[], interpretation_guidance=[], limitations=[],
        related_routes=[], notes_for_assistant=[],
    )
    base.update(over)
    # Tolerate required-field differences across PageContext versions.
    try:
        return PageContext(**base)  # type: ignore[arg-type]
    except TypeError:
        # Fall back to a minimal namespace with the attrs the generator reads.
        class _P:  # noqa: D401
            pass
        p = _P()
        for k, v in base.items():
            setattr(p, k, v)
        return p


class SuggestedQuestionsTests(unittest.TestCase):
    def test_none_page_returns_defaults_only(self):
        self.assertEqual(get_suggested_questions_for_page(None), list(_DEFAULTS))

    def test_metric_aware_question_is_concrete(self):
        p = _page(key_metrics=["Denial Rate", "Clean DAR"])
        qs = get_suggested_questions_for_page(p)
        self.assertIn("What does Denial Rate mean?", qs)
        # uses the FIRST documented metric only (deterministic, not noisy)
        self.assertNotIn("What does Clean DAR mean?", qs)

    def test_source_aware_question_is_concrete(self):
        p = _page(data_sources=["CMS HCRIS"])
        qs = get_suggested_questions_for_page(p)
        self.assertIn("Where does CMS HCRIS come from?", qs)

    def test_sentinel_metric_is_skipped(self):
        p = _page(key_metrics=["Needs source documentation."])
        qs = get_suggested_questions_for_page(p)
        # No concrete metric question ("What does <metric> mean?") emitted.
        self.assertFalse(any(q.endswith(" mean?") for q in qs))
        self.assertNotIn("Needs source documentation.", " ".join(qs))

    def test_capped_and_deduped(self):
        p = _page(
            key_metrics=["Denial Rate"], data_sources=["CMS HCRIS"],
            category=PageContextCategory.DILIGENCE_WORKSPACE,
        )
        qs = get_suggested_questions_for_page(p)
        self.assertLessEqual(len(qs), _MAX_QUESTIONS)
        self.assertEqual(len(qs), len(set(qs)))           # no duplicates
        self.assertTrue(qs[:len(_DEFAULTS)] == list(_DEFAULTS))  # defaults first

    def test_deterministic(self):
        p = _page(key_metrics=["Denial Rate"], data_sources=["CMS HCRIS"])
        self.assertEqual(
            get_suggested_questions_for_page(p),
            get_suggested_questions_for_page(p),
        )


if __name__ == "__main__":
    unittest.main()
