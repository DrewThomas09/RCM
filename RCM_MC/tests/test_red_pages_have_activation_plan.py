"""Every RED surface must have a documented activation path.

Product-readiness rule: a page may stay RED only while it is triaged in
docs/reports/RED_PAGE_ACTIVATION_PLAN.md with an honest activation path
(USER DATA REQUIRED / DATA REQUIRED / DEFERRED WITH REASON). This fails if a
new RED route is added without a plan entry — forcing the honest decision.
"""
import re
import unittest
from pathlib import Path

from rcm_mc.diligence.surface_status import _RED

_PLAN = Path(__file__).resolve().parents[1] / "docs" / "reports" / "RED_PAGE_ACTIVATION_PLAN.md"


class RedActivationPlanTests(unittest.TestCase):
    def test_every_red_route_is_in_the_plan(self):
        self.assertTrue(_PLAN.exists(), "RED_PAGE_ACTIVATION_PLAN.md missing")
        text = _PLAN.read_text()
        # plan references routes as `/foo` in table cells; match exact tokens
        missing = [r for r in sorted(_RED)
                   if not re.search(re.escape(r) + r"(?=[\s|`)])", text)]
        self.assertEqual(missing, [],
                         "RED routes with no activation-plan entry:\n" + "\n".join(missing))


if __name__ == "__main__":
    unittest.main()
