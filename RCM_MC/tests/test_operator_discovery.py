"""Operators the system registry does not carry.

The failure mode this guards against is the one this repo has already
shipped twice: a name-based grouping that manufactures systems. ``CHI``
pulled in CHINLE and CHINESE HOSPITAL; a bare ``^TRINITY`` claimed
UnityPoint's hospitals. Both were prefix matches with nothing behind
them.

So the assertions here are mostly about *refusal*. Eight hospitals named
MEMORIAL HOSPITAL in seven states must not become an operator, and the
thing that stops them is not the name — it is that they file four
different ownership structures, which one company cannot do.
"""
from __future__ import annotations

import unittest

import pandas as pd

from rcm_mc.data.operator_discovery import (
    MIN_OWNERSHIP_AGREEMENT, OPERATOR_COLUMNS, discover_operators,
    discovered_operator_frame, discovery_coverage, operator_key,
    ownership_family,
)


def _facility(ccn: str, name: str, state: str, ownership: str, *,
              provider_class: str = "hha", system_id: str = "_unmapped",
              operating: bool = True) -> dict:
    return {"ccn": ccn, "name": name, "state": state,
            "cms_ownership": ownership, "provider_class": provider_class,
            "system_id": system_id, "is_operating": operating}


def _chain() -> pd.DataFrame:
    """A four-branch agency, and four unrelated hospitals sharing a name."""
    rows = [
        _facility("157034", "Caretenders", "IN", "PROPRIETARY"),
        _facility("187084", "CARETENDERS", "KY", "For-Profit"),
        _facility("227269", "Caretenders, Inc.", "MA", "PROPRIETARY"),
        _facility("367296", "CARETENDERS", "OH", "For profit - Corporation"),
        # Same name, four different answers to who owns us.
        _facility("010001", "Memorial Hospital", "AL", "Government - Local",
                  provider_class="hospital"),
        _facility("100002", "MEMORIAL HOSPITAL", "FL",
                  "Voluntary non-profit - Private", provider_class="hospital"),
        _facility("230003", "Memorial Hospital", "MI", "Proprietary",
                  provider_class="hospital"),
        _facility("450004", "MEMORIAL HOSPITAL", "TX", "Physician",
                  provider_class="hospital"),
    ]
    return pd.DataFrame(rows)


class OperatorKeyTests(unittest.TestCase):
    """CMS certifies one operator under several spellings of its own
    name. The key has to see through the legal form without seeing
    through anything else."""

    def test_a_legal_form_does_not_split_an_operator(self) -> None:
        """LIBERTY HOME CARE and LIBERTY HOME CARE LLC are one company
        reported as a 7 and a 6 where a 13 exists."""
        self.assertEqual(operator_key("Liberty Home Care"),
                         operator_key("Liberty Home Care, LLC"))

    def test_stacked_legal_forms_all_come_off(self) -> None:
        self.assertEqual(operator_key("Foo Care Ltd LLC"), "FOO CARE")

    def test_a_county_keeps_its_co(self) -> None:
        """ADVANCED CARE HOSPITAL OF WHITE CO is White County. Stripping
        CO rewrites which facility this is."""
        self.assertEqual(operator_key("Advanced Care Hospital of White Co"),
                         "ADVANCED CARE HOSPITAL OF WHITE CO")

    def test_a_state_keeps_its_pa(self) -> None:
        self.assertEqual(operator_key("Angels of Care of PA"),
                         "ANGELS OF CARE OF PA")

    def test_a_legal_form_inside_a_name_is_left_alone(self) -> None:
        """Only the tail is a legal form. CORPUS CHRISTI is a city."""
        self.assertEqual(operator_key("Corpus Christi Home Health"),
                         "CORPUS CHRISTI HOME HEALTH")

    def test_a_name_is_never_stripped_to_nothing(self) -> None:
        """A facility certified as "LLC" keeps it, rather than joining a
        bucket with every other unnameable row."""
        self.assertEqual(operator_key("LLC"), "LLC")

    def test_a_blank_name_has_no_key(self) -> None:
        for junk in ("", "   ", None):
            with self.subTest(junk=junk):
                self.assertEqual(operator_key(junk), "")


class OwnershipFamilyTests(unittest.TestCase):
    """CMS spells the same structure five ways across its files. Grouping
    on the raw string scores a chain's own spellings as a disagreement."""

    def test_the_for_profit_spellings_all_land_together(self) -> None:
        for raw in ("PROPRIETARY", "Proprietary", "For-Profit", "For profit",
                    "For profit - Corporation",
                    "For profit - Limited Liability company",
                    "Proprietary - Partnership"):
            with self.subTest(raw=raw):
                self.assertEqual(ownership_family(raw), "forprofit")

    def test_the_non_profit_spellings_all_land_together(self) -> None:
        for raw in ("Non profit - Corporation", "NON-PROFIT",
                    "Voluntary non-profit - Private",
                    "Voluntary non-profit - Church"):
            with self.subTest(raw=raw):
                self.assertEqual(ownership_family(raw), "nonprofit")

    def test_a_hospital_district_is_government_not_a_corporation(self) -> None:
        """"Government - Hospital District or Authority" carries none of
        the for-profit markers, but the ordering is what guarantees a
        district authority is never read as a proprietary corporation."""
        self.assertEqual(
            ownership_family("Government - Hospital District or Authority"),
            "government")
        self.assertEqual(ownership_family("Government - State"), "government")

    def test_an_absent_answer_is_not_a_family(self) -> None:
        """CMS writes "-" where nothing was filed. Counting that as a
        family would let a group who all declined look unanimous."""
        for raw in ("", "   ", "-", None, "Other", "UNKNOWN"):
            with self.subTest(raw=raw):
                self.assertEqual(ownership_family(raw), "")


class DiscoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.by_name = {o.name: o for o in discover_operators(_chain())}

    def test_a_chain_filing_one_structure_is_discovered(self) -> None:
        operator = self.by_name["CARETENDERS"]
        self.assertEqual(operator.facilities, 4)
        self.assertEqual(operator.ownership_family, "forprofit")
        self.assertEqual(operator.ownership_agreement, 1.0)
        self.assertTrue(operator.is_confident)
        self.assertTrue(operator.is_multi_state)

    def test_a_name_collision_is_refused_however_many_share_it(self) -> None:
        """Four hospitals, one name, four ownership structures. One
        company cannot be simultaneously a local government, a private
        non-profit, a proprietary corporation and a physician group."""
        operator = self.by_name["MEMORIAL HOSPITAL"]
        self.assertEqual(operator.facilities, 4)
        self.assertLess(operator.ownership_agreement, MIN_OWNERSHIP_AGREEMENT)
        self.assertFalse(operator.is_confident)

    def test_the_rejected_group_is_still_returned(self) -> None:
        """A big group that fails the test is the most interesting row on
        the page — a collision, or a chain mid-sale. Dropping it silently
        answers neither question."""
        self.assertIn("MEMORIAL HOSPITAL", self.by_name)
        self.assertNotIn("MEMORIAL HOSPITAL",
                         {o.name for o in
                          discover_operators(_chain(), confident_only=True)})

    def test_punctuation_does_not_split_a_chain(self) -> None:
        """"Caretenders, Inc." and "CARETENDERS" are the same company
        filing the same name twice."""
        self.assertEqual(self.by_name["CARETENDERS"].facilities, 4)

    def test_a_singleton_is_not_an_operator(self) -> None:
        frame = pd.DataFrame([_facility("1", "Lone Agency", "AL",
                                        "PROPRIETARY")])
        self.assertEqual(discover_operators(frame), [])

    def test_a_mapped_facility_is_not_a_discovery(self) -> None:
        """It already has a system. Re-reporting it as something the
        registry misses would make the backlog look larger than it is."""
        frame = pd.DataFrame([
            _facility("1", "Ascension Saint Vincents", "AL", "Non-profit",
                      system_id="ascension"),
            _facility("2", "Ascension Saint Vincents", "TN", "Non-profit",
                      system_id="ascension"),
        ])
        self.assertEqual(discover_operators(frame), [])

    def test_a_closed_facility_does_not_pad_a_group(self) -> None:
        """A chain that no longer operates is not a target, and counting
        its closed sites inflates every group with beds nobody can buy."""
        frame = pd.DataFrame([
            _facility("1", "Alpine Care", "AZ", "PROPRIETARY"),
            _facility("2", "Alpine Care", "NV", "PROPRIETARY"),
            _facility("3", "Alpine Care", "UT", "PROPRIETARY",
                      operating=False),
        ])
        self.assertEqual(discover_operators(frame)[0].facilities, 2)

    def test_a_group_that_filed_no_ownership_cannot_be_confident(self) -> None:
        frame = pd.DataFrame([
            _facility("1", "Quiet Agency", "AL", "-"),
            _facility("2", "Quiet Agency", "GA", ""),
        ])
        operator = discover_operators(frame)[0]
        self.assertEqual(operator.ownership_family, "")
        self.assertEqual(operator.ownership_agreement, 0.0)
        self.assertFalse(operator.is_confident)

    def test_a_single_state_chain_is_still_a_chain(self) -> None:
        """Millers Merry Manor runs twelve nursing homes in Indiana and
        nowhere else. Requiring multi-state would discard it."""
        frame = pd.DataFrame([
            _facility(str(n), "Millers Merry Manor", "IN", "PROPRIETARY",
                      provider_class="snf") for n in range(4)])
        operator = discover_operators(frame)[0]
        self.assertTrue(operator.is_confident)
        self.assertFalse(operator.is_multi_state)

    def test_an_empty_universe_discovers_nothing(self) -> None:
        self.assertEqual(discover_operators(pd.DataFrame()), [])
        self.assertEqual(
            discover_operators(pd.DataFrame(columns=["name"])), [])


class FrameTests(unittest.TestCase):
    def test_the_frame_declares_its_columns(self) -> None:
        frame = discovered_operator_frame(_chain())
        self.assertEqual(list(frame.columns), list(OPERATOR_COLUMNS))

    def test_an_empty_result_is_an_empty_typed_frame(self) -> None:
        frame = discovered_operator_frame(pd.DataFrame())
        self.assertTrue(frame.empty)
        self.assertEqual(list(frame.columns), list(OPERATOR_COLUMNS))

    def test_the_ccns_travel_with_the_row(self) -> None:
        """The whole point is that a reviewer can go and check. A group
        without its CCNs is an assertion with no way to audit it."""
        frame = discovered_operator_frame(_chain())
        row = frame[frame["operator_name"] == "CARETENDERS"].iloc[0]
        self.assertEqual(len(row["ccns"].split("|")), 4)
        self.assertIn("157034", row["ccns"])

    def test_groups_are_ranked_by_size(self) -> None:
        frame = discovered_operator_frame(_chain())
        self.assertEqual(list(frame["facilities"]),
                         sorted(frame["facilities"], reverse=True))


class RealRegisterTests(unittest.TestCase):
    """Against the certified register on disk, not a fixture."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.cov = discovery_coverage()
        cls.operators = discover_operators(confident_only=True)

    def test_it_finds_operators_the_registry_does_not_carry(self) -> None:
        self.assertGreater(self.cov["confident_groups"], 500)
        self.assertGreater(self.cov["facilities_in_confident_groups"], 1_500)

    def test_the_denominator_is_reported_beside_the_finding(self) -> None:
        """"1,185 operators discovered" without "out of 33,998 unmapped"
        reads like the gap is closed when most of it is not."""
        self.assertGreater(self.cov["unmapped_operating"], 30_000)
        self.assertLess(self.cov["facilities_in_confident_groups"],
                        self.cov["unmapped_operating"] * 0.25)

    def test_post_acute_is_where_the_operators_are(self) -> None:
        """The gap is 86% SNF, home health and hospice, and so is what
        this finds. A result dominated by hospitals would mean the pass
        is matching the sector it was not built for."""
        mix = self.cov["by_class"]
        self.assertGreater(mix.get("hha", 0), mix.get("hospital", 0))

    def test_the_classic_name_collisions_are_all_refused(self) -> None:
        """These are the families that produced the CHI and TRINITY
        incidents. Every one of them must fail the ownership test."""
        confident = {o.name for o in self.operators}
        for collision in ("MEMORIAL HOSPITAL", "COMMUNITY MEMORIAL HOSPITAL",
                          "GOOD SAMARITAN HOSPITAL",
                          "SAINT JOSEPH MEDICAL CENTER"):
            with self.subTest(name=collision):
                self.assertNotIn(collision, confident)

    def test_a_known_multi_state_agency_is_found(self) -> None:
        found = {o.name: o for o in self.operators}
        self.assertIn("CARETENDERS", found)
        self.assertGreater(found["CARETENDERS"].facilities, 10)
        self.assertGreater(len(found["CARETENDERS"].states), 3)

    def test_every_confident_group_agrees_on_one_structure(self) -> None:
        for operator in self.operators:
            with self.subTest(name=operator.name):
                self.assertTrue(operator.ownership_family)
                self.assertGreaterEqual(operator.ownership_agreement,
                                        MIN_OWNERSHIP_AGREEMENT)

    def test_the_coverage_report_is_json_serialisable(self) -> None:
        import json
        json.loads(json.dumps(self.cov, default=int))


if __name__ == "__main__":
    unittest.main()


class CacheTests(unittest.TestCase):
    """The pass is seven seconds over the bundled register and both the
    page and the route ask for it per request."""

    def test_an_explicit_register_bypasses_the_cache(self) -> None:
        """The cache is keyed on the size floor alone, so a caller's own
        frame must never be served from it — or answered into it."""
        mine = discover_operators(_chain())
        theirs = discover_operators()
        self.assertEqual({o.name for o in mine},
                         {"CARETENDERS", "MEMORIAL HOSPITAL"})
        self.assertGreater(len(theirs), 500)
        self.assertEqual({o.name for o in discover_operators(_chain())},
                         {"CARETENDERS", "MEMORIAL HOSPITAL"})

    def test_mutating_the_result_does_not_corrupt_the_next_caller(self) -> None:
        first = discover_operators()
        count = len(first)
        first.clear()
        self.assertEqual(len(discover_operators()), count)

    def test_the_size_floor_is_part_of_the_key(self) -> None:
        """Two floors are two different answers. Sharing one cache slot
        between them would serve whichever ran first."""
        everything = discover_operators()
        big = discover_operators(min_facilities=8)
        self.assertLess(len(big), len(everything))
        self.assertTrue(all(o.facilities >= 8 for o in big))
        self.assertEqual(len(discover_operators()), len(everything))


class PagePanelTests(unittest.TestCase):
    """The queue on /health-system-lookup."""

    @classmethod
    def setUpClass(cls) -> None:
        from rcm_mc.ui.data_public.health_system_lookup_page import (
            render_health_system_lookup)
        cls.html = render_health_system_lookup({})

    def test_the_panel_is_on_the_page(self) -> None:
        self.assertIn("Discovered Operators", self.html)
        self.assertIn("CARETENDERS", self.html)

    def test_the_denominator_is_shown_beside_the_finding(self) -> None:
        """A count of discovered operators with no "out of" reads like
        the registry gap is closed."""
        self.assertIn("the registry does not map", self.html)
        self.assertIn("closes part of the gap and not most of it", self.html)

    def test_the_page_names_the_families_it_refuses(self) -> None:
        """The refusals are the credibility of the list. A reader who
        cannot see that SAINT JOSEPH was considered and rejected has no
        reason to believe CARETENDERS was tested at all."""
        for collision in ("MEMORIAL HOSPITAL", "GOOD SAMARITAN HOSPITAL",
                          "SAINT JOSEPH MEDICAL CENTER"):
            with self.subTest(name=collision):
                self.assertIn(collision, self.html)

    def test_the_page_says_it_is_a_queue_not_a_mapping(self) -> None:
        self.assertIn("system_id", self.html)
        self.assertIn("registry edit", self.html)


class RouteTests(unittest.TestCase):
    """Served over real HTTP, like every other export."""

    @classmethod
    def setUpClass(cls) -> None:
        import os
        import socket
        import tempfile
        import threading
        import time
        from contextlib import closing

        from rcm_mc.server import build_server

        cls._tmp = tempfile.TemporaryDirectory()
        with closing(socket.socket()) as sock:
            sock.bind(("127.0.0.1", 0))
            cls._port = sock.getsockname()[1]
        srv, _ = build_server(port=cls._port, host="127.0.0.1",
                              db_path=os.path.join(cls._tmp.name, "m.db"))
        cls._srv = srv
        cls._thread = threading.Thread(target=srv.serve_forever, daemon=True)
        cls._thread.start()
        time.sleep(0.2)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._srv.shutdown()
        cls._srv.server_close()
        cls._thread.join(timeout=5)
        cls._tmp.cleanup()

    def _rows(self, route: str):
        import csv
        import io
        import urllib.request

        resp = urllib.request.urlopen(
            f"http://127.0.0.1:{self._port}{route}", timeout=180)
        self.assertEqual(resp.status, 200)
        self.assertIn("text/csv", resp.headers.get("Content-Type", ""))
        return list(csv.DictReader(io.StringIO(resp.read().decode("utf-8"))))

    def test_the_route_serves_the_whole_queue(self) -> None:
        rows = self._rows("/discovered-operators.csv")
        self.assertGreater(len(rows), 500)
        self.assertEqual(list(rows[0]), list(OPERATOR_COLUMNS))

    def test_the_failed_groups_ship_by_default(self) -> None:
        """They are the rows worth reading. Confident-only is opt-in for
        the same reason `parented=1` is on the master file: a queue that
        silently drops its own rejects looks more certain than it is."""
        rows = self._rows("/discovered-operators.csv")
        self.assertTrue(any(r["is_confident"] == "0" for r in rows))
        confident = self._rows("/discovered-operators.csv?confident=1")
        self.assertTrue(all(r["is_confident"] == "1" for r in confident))
        self.assertLess(len(confident), len(rows))

    def test_the_state_filter_asks_where_it_operates(self) -> None:
        """A group is multi-state by construction, so filtering on one
        state has to mean "runs a facility here", not "is based here"."""
        rows = self._rows("/discovered-operators.csv?state=TX")
        self.assertTrue(rows)
        for row in rows:
            self.assertIn("TX", row["state_list"].split("|"))

    def test_a_size_floor_narrows_without_changing_the_shape(self) -> None:
        rows = self._rows("/discovered-operators.csv?min_facilities=8")
        self.assertTrue(rows)
        self.assertTrue(all(int(r["facilities"]) >= 8 for r in rows))
        self.assertEqual(list(rows[0]), list(OPERATOR_COLUMNS))

    def test_a_junk_size_falls_back_rather_than_raising(self) -> None:
        rows = self._rows("/discovered-operators.csv?min_facilities=abc")
        self.assertGreater(len(rows), 500)
