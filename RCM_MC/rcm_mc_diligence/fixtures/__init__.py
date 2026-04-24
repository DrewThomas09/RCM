"""Synthetic diligence fixtures — adversarial, stable under a seed.

Each ``mess_scenario_N_*`` module exposes:

- ``FIXTURE_NAME``: the slug used by the CLI (``--dataset <name>``).
- ``EXPECTED_OUTCOME``: dict summarising what the DQ report *should*
  say. Tests assert against this dict; when the fixture's contract
  changes intentionally, the test fails loudly — that's the whole
  point of regression locks.
- ``generate(output_dir, *, seed=...) -> Path``: emits a raw-data
  directory and a README next to it.

A central :data:`FIXTURES` registry is the CLI's lookup table.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict

from . import (
    mess_scenario_1_multi_ehr,
    mess_scenario_2_orphaned_835s,
    mess_scenario_3_duplicate_adjudication,
    mess_scenario_4_unmapped_codes,
    mess_scenario_5_partial_payer_mix,
    synthetic,
)


FIXTURES: Dict[str, Dict[str, object]] = {
    mess_scenario_1_multi_ehr.FIXTURE_NAME: {
        "generate": mess_scenario_1_multi_ehr.generate,
        "expected": mess_scenario_1_multi_ehr.EXPECTED_OUTCOME,
    },
    mess_scenario_2_orphaned_835s.FIXTURE_NAME: {
        "generate": mess_scenario_2_orphaned_835s.generate,
        "expected": mess_scenario_2_orphaned_835s.EXPECTED_OUTCOME,
    },
    mess_scenario_3_duplicate_adjudication.FIXTURE_NAME: {
        "generate": mess_scenario_3_duplicate_adjudication.generate,
        "expected": mess_scenario_3_duplicate_adjudication.EXPECTED_OUTCOME,
    },
    mess_scenario_4_unmapped_codes.FIXTURE_NAME: {
        "generate": mess_scenario_4_unmapped_codes.generate,
        "expected": mess_scenario_4_unmapped_codes.EXPECTED_OUTCOME,
    },
    mess_scenario_5_partial_payer_mix.FIXTURE_NAME: {
        "generate": mess_scenario_5_partial_payer_mix.generate,
        "expected": mess_scenario_5_partial_payer_mix.EXPECTED_OUTCOME,
    },
}

__all__ = [
    "FIXTURES",
    "mess_scenario_1_multi_ehr",
    "mess_scenario_2_orphaned_835s",
    "mess_scenario_3_duplicate_adjudication",
    "mess_scenario_4_unmapped_codes",
    "mess_scenario_5_partial_payer_mix",
    "synthetic",
]
