"""Final-parent resolution — the walk, the tie-breaks, and the real graph.

No single source gets an identifier to the top of its ownership tree, so
the engine composes the hops that exist and walks them. That makes three
things worth testing hard: that the walk terminates on data that lies
(cycles, self-parents), that the tie-breaks are the ones documented
rather than whatever iteration order produced, and that the sentinel for
"no system found" never becomes a health system.

The last one is the dangerous failure. 34,085 of the crosswalk's 48,510
rows carry ``_unmapped``; treating it as a node would report seven
facilities in ten as owned and be entirely wrong.
"""
from __future__ import annotations

import unittest

import pandas as pd

from rcm_mc.data.health_systems import UNMAPPED_ID
from rcm_mc.data.parent_resolution import (
    MAX_HOPS, NS_CCN, NS_CHAIN, NS_NPI, NS_ORG, NS_PECOS, NS_SYSTEM,
    DISAGREEMENT_COLUMNS, PARENT_COLUMNS, RESOLUTION_COLUMNS,
    TIER_AFFILIATION,
    TIER_CCN_CHAIN, TIER_CCN_PARENT, TIER_CCN_SYSTEM, TIER_CONFIDENCE,
    TIER_NAME_SYSTEM, TIER_NPI_CCN, TIER_NPPES_SUBPART, TIER_PECOS_GROUP,
    TIER_RANK, ParentGraph, attach_parents, build_parent_graph,
    edges_from_affiliations, edges_from_crosswalk, edges_from_npi_frame,
    load_affiliations, node_key, ownership_disagreements,
    resolve_identifiers,
)


class NodeKeyTests(unittest.TestCase):
    def test_namespaces_keep_lookalike_identifiers_apart(self):
        # A CCN and an NPI can be the same digits. Without a namespace
        # the graph joins them once and is wrong forever.
        self.assertNotEqual(node_key(NS_CCN, "1234567890"),
                            node_key(NS_NPI, "1234567890"))

    def test_empty_values_do_not_become_bare_colons(self):
        for junk in ("", None, "   "):
            self.assertEqual(node_key(NS_CCN, junk), "")

    def test_the_unmapped_sentinel_is_not_a_health_system(self):
        self.assertEqual(node_key(NS_SYSTEM, UNMAPPED_ID), "")

    def test_names_are_normalised_so_punctuation_does_not_split_a_chain(self):
        self.assertEqual(node_key(NS_CHAIN, "DaVita, Inc."),
                         node_key(NS_CHAIN, "DAVITA INC"))


class GraphConstructionTests(unittest.TestCase):
    def test_a_self_edge_is_refused(self):
        g = ParentGraph()
        self.assertFalse(g.add_edge("ccn:1", "ccn:1", TIER_CCN_SYSTEM))
        self.assertEqual(g.resolve("ccn:1").hops, 0)

    def test_an_empty_endpoint_is_refused(self):
        g = ParentGraph()
        self.assertFalse(g.add_edge("", "sys:x", TIER_CCN_SYSTEM))
        self.assertFalse(g.add_edge("ccn:1", "", TIER_CCN_SYSTEM))

    def test_children_of_is_the_reverse_index(self):
        g = ParentGraph()
        g.add_edge("npi:1", "pecos:9", TIER_PECOS_GROUP)
        g.add_edge("npi:2", "pecos:9", TIER_PECOS_GROUP)
        self.assertEqual(g.children_of("pecos:9"), ("npi:1", "npi:2"))
        self.assertEqual(g.children_of("pecos:404"), ())


class WalkTests(unittest.TestCase):
    def test_a_node_with_nothing_above_it_is_its_own_parent(self):
        res = ParentGraph().resolve("sys:ascension")
        self.assertEqual(res.final_parent, "sys:ascension")
        self.assertTrue(res.is_root)
        self.assertEqual(res.confidence, 1.0)

    def test_the_walk_reaches_the_top_not_the_next_step(self):
        g = ParentGraph()
        g.add_edge("ccn:01T011", "ccn:010011", TIER_CCN_PARENT)
        g.add_edge("ccn:010011", "sys:ascension", TIER_CCN_SYSTEM)
        res = g.resolve("ccn:01T011")
        self.assertEqual(res.final_parent, "sys:ascension")
        self.assertEqual(res.hops, 2)
        self.assertEqual(res.path,
                         ("ccn:01T011", "ccn:010011", "sys:ascension"))

    def test_a_cycle_is_flagged_not_followed_forever(self):
        """Two facilities each naming the other is a real filing error.
        A flagged cycle is a finding; a hung process is not."""
        g = ParentGraph()
        g.add_edge("ccn:a", "ccn:b", TIER_CCN_PARENT)
        g.add_edge("ccn:b", "ccn:a", TIER_CCN_PARENT)
        res = g.resolve("ccn:a")
        self.assertTrue(res.cycle)
        self.assertLessEqual(res.hops, 2)

    def test_a_pathological_chain_is_truncated_not_walked(self):
        g = ParentGraph()
        for i in range(MAX_HOPS + 5):
            g.add_edge(f"ccn:{i}", f"ccn:{i + 1}", TIER_CCN_PARENT)
        res = g.resolve("ccn:0")
        self.assertTrue(res.truncated)
        self.assertLessEqual(res.hops, MAX_HOPS)

    def test_a_guarded_result_is_not_memoised_for_other_entry_points(self):
        """A walk that hit the cycle guard is only correct for the node it
        started from — caching it would poison every other node."""
        g = ParentGraph()
        g.add_edge("ccn:a", "ccn:b", TIER_CCN_PARENT)
        g.add_edge("ccn:b", "ccn:c", TIER_CCN_PARENT)
        g.add_edge("ccn:c", "ccn:a", TIER_CCN_PARENT)
        self.assertTrue(g.resolve("ccn:a").cycle)
        self.assertTrue(g.resolve("ccn:b").cycle)
        self.assertTrue(g.resolve("ccn:c").cycle)


class TieBreakTests(unittest.TestCase):
    def test_the_strongest_tier_decides_where_a_node_lands(self):
        g = ParentGraph()
        g.add_edge("npi:1", "sys:by_name", TIER_NAME_SYSTEM)
        g.add_edge("npi:1", "org:filed", TIER_NPPES_SUBPART)
        self.assertEqual(g.resolve("npi:1").final_parent, "org:filed")

    def test_corroboration_raises_confidence_rather_than_lowering_it(self):
        """A dialysis clinic naming both its chain and its system used to
        score 0.60 on the chain route while a 0.75 system edge sat right
        beside it. The destination is the same; the score should be the
        best-supported route to it, not the top-ranked one."""
        g = ParentGraph()
        g.add_edge("ccn:1", "chain:DAVITA", TIER_CCN_CHAIN)
        g.add_edge("ccn:1", "sys:davita", TIER_CCN_SYSTEM)
        g.add_edge("chain:DAVITA", "sys:davita", TIER_NAME_SYSTEM)
        res = g.resolve("ccn:1")
        self.assertEqual(res.final_parent, "sys:davita")
        self.assertEqual(res.confidence, TIER_CONFIDENCE[TIER_CCN_SYSTEM])

    def test_confidence_is_the_weakest_hop_not_the_product(self):
        g = ParentGraph()
        g.add_edge("ccn:1", "chain:SMALL CHAIN", TIER_CCN_CHAIN)
        g.add_edge("chain:SMALL CHAIN", "sys:x", TIER_NAME_SYSTEM)
        res = g.resolve("ccn:1")
        self.assertEqual(res.confidence, TIER_CONFIDENCE[TIER_NAME_SYSTEM])
        self.assertEqual(res.weakest_tier, TIER_NAME_SYSTEM)

    def test_ties_break_deterministically_not_on_insertion_order(self):
        forward, backward = ParentGraph(), ParentGraph()
        forward.add_edge("ccn:1", "sys:aaa", TIER_CCN_SYSTEM)
        forward.add_edge("ccn:1", "sys:zzz", TIER_CCN_SYSTEM)
        backward.add_edge("ccn:1", "sys:zzz", TIER_CCN_SYSTEM)
        backward.add_edge("ccn:1", "sys:aaa", TIER_CCN_SYSTEM)
        self.assertEqual(forward.resolve("ccn:1").final_parent,
                         backward.resolve("ccn:1").final_parent)

    def test_tier_ranks_and_confidences_agree_on_the_ordering(self):
        """A tier that outranks another must not be less confident — the
        two tables would then contradict each other row by row."""
        ordered = sorted(TIER_RANK, key=lambda t: TIER_RANK[t])
        scores = [TIER_CONFIDENCE[t] for t in ordered]
        self.assertEqual(scores, sorted(scores, reverse=True))


class ContestedTests(unittest.TestCase):
    def test_two_roads_to_the_same_place_are_not_a_disagreement(self):
        g = ParentGraph()
        g.add_edge("ccn:1", "chain:DAVITA", TIER_CCN_CHAIN)
        g.add_edge("ccn:1", "sys:davita", TIER_CCN_SYSTEM)
        g.add_edge("chain:DAVITA", "sys:davita", TIER_NAME_SYSTEM)
        self.assertEqual(g.contested(), {})

    def test_genuinely_different_destinations_are_reported(self):
        g = ParentGraph()
        g.add_edge("ccn:1", "chain:INNOVATIVE DIALYSIS", TIER_CCN_CHAIN)
        g.add_edge("ccn:1", "sys:us_renal_care", TIER_CCN_SYSTEM)
        contested = g.contested()
        self.assertIn("ccn:1", contested)
        self.assertEqual(contested["ccn:1"],
                         ("chain:INNOVATIVE DIALYSIS", "sys:us_renal_care"))


class NamedOwnerPreferenceTests(unittest.TestCase):
    """A stronger tier that names nobody must not bury a weaker tier that
    names someone."""

    def test_a_dead_end_on_another_facility_loses_to_a_named_system(self):
        # Five hospital-based units hit this on the real data: the unit
        # knew it was UCHealth, its parent hospital's filed name carried
        # no brand, and ccn_parent (0.90) buried the answer under a bare
        # ccn: node.
        g = ParentGraph()
        g.add_edge("ccn:06T022", "ccn:060022", TIER_CCN_PARENT)
        g.add_edge("ccn:06T022", "sys:uchealth", TIER_CCN_SYSTEM)
        res = g.resolve("ccn:06T022")
        self.assertEqual(res.final_parent, "sys:uchealth")

    def test_the_stronger_tier_still_wins_when_both_name_an_owner(self):
        g = ParentGraph()
        g.add_edge("ccn:01T011", "ccn:010011", TIER_CCN_PARENT)
        g.add_edge("ccn:010011", "sys:ascension", TIER_CCN_SYSTEM)
        g.add_edge("ccn:01T011", "sys:other", TIER_CCN_SYSTEM)
        self.assertEqual(g.resolve("ccn:01T011").final_parent, "sys:ascension")

    def test_a_facility_root_is_still_the_answer_when_it_is_the_only_one(self):
        """"Inside hospital X, owner unknown" beats no answer at all."""
        g = ParentGraph()
        g.add_edge("ccn:06T022", "ccn:060022", TIER_CCN_PARENT)
        self.assertEqual(g.resolve("ccn:06T022").final_parent, "ccn:060022")

    def test_a_dead_end_claim_is_not_counted_as_a_disagreement(self):
        g = ParentGraph()
        g.add_edge("ccn:06T022", "ccn:060022", TIER_CCN_PARENT)
        g.add_edge("ccn:06T022", "sys:uchealth", TIER_CCN_SYSTEM)
        self.assertEqual(g.contested(), {})


class ChainAliasTests(unittest.TestCase):
    """CMS's chain strings have a curated mapping in the registry, and the
    regex patterns are a second route for names it does not cover."""

    def _frame(self, chain: str, system_id: str, state: str = "NY"):
        return pd.DataFrame([{
            "ccn": "332514", "parent_ccn": "", "parent_ccn_source": "",
            "chain_name": chain, "system_id": system_id, "system_match": "",
            "system_name": "", "npi": "", "npi_source": "", "state": state}])

    def test_a_chain_alias_reaches_the_system_its_pattern_cannot(self):
        # atlantic_dms's pattern is "NY:^ATLANTIC DMS"; CMS files the
        # chain as "ATLANTIC DIALYSIS MANAGEMENT SERVICES". Same
        # operator, two spellings — and without the alias table they
        # showed up as an ownership disagreement with each other.
        graph = build_parent_graph(
            crosswalk=self._frame("ATLANTIC DIALYSIS MANAGEMENT SERVICES",
                                  "atlantic_dms"))
        self.assertEqual(graph.resolve(node_key(NS_CCN, "332514")).final_parent,
                         node_key(NS_SYSTEM, "atlantic_dms"))
        self.assertEqual(graph.contested(), {})

    def test_a_state_scoped_pattern_fires_using_its_facilities_states(self):
        """The node key is a normalised name that has thrown the state
        away, so the lift has to be told where the facilities are."""
        graph = build_parent_graph(
            crosswalk=self._frame("NORTHWEST KIDNEY CENTERS",
                                  "northwest_kidney", state="WA"))
        self.assertEqual(graph.resolve(node_key(NS_CCN, "332514")).final_parent,
                         node_key(NS_SYSTEM, "northwest_kidney"))


class AffiliationTierTests(unittest.TestCase):
    """The only route by which a person gets a parent, and the fence
    around it."""

    def _frame(self):
        return pd.DataFrame([
            {"individual_npi": "3333333333", "organization_npi": "1111111111",
             "method": "shared_address+name", "confidence": 0.85,
             "evidence": "co-located @ 810 ST VINCENTS DR|35205; "
                         "name token overlap ['SMITH']"},
            # Co-location alone: two providers in the same building.
            {"individual_npi": "4444444444", "organization_npi": "1111111111",
             "method": "shared_practice_address", "confidence": 0.45,
             "evidence": "co-located @ 810 ST VINCENTS DR|35205; 3 org(s)"},
            # Name overlap in a tower so crowded the token is noise.
            {"individual_npi": "5555555555", "organization_npi": "1111111111",
             "method": "shared_address+name", "confidence": 0.28,
             "evidence": "co-located; 40 org(s) at address"},
        ])

    def test_a_named_and_co_located_pair_becomes_an_edge(self):
        edges = edges_from_affiliations(self._frame())
        self.assertEqual([e.child for e in edges], ["npi:3333333333"])
        self.assertEqual(edges[0].tier, TIER_AFFILIATION)

    def test_bare_co_location_is_refused_not_merely_scored_down(self):
        """Two physicians in the same medical office building are not
        colleagues. A low number on a claim that should not have been
        made is still the claim."""
        edges = edges_from_affiliations(self._frame())
        self.assertNotIn("npi:4444444444", {e.child for e in edges})

    def test_a_weak_pair_is_dropped_by_the_confidence_floor(self):
        edges = edges_from_affiliations(self._frame())
        self.assertNotIn("npi:5555555555", {e.child for e in edges})

    def test_the_bridges_own_score_is_carried_not_flattened(self):
        """The bridge already knows a pair in a two-tenant building is
        stronger than one in a forty-tenant tower. Collapsing that to a
        tier constant throws away the only thing separating them."""
        edge = edges_from_affiliations(self._frame())[0]
        self.assertEqual(edge.confidence, 0.85)
        self.assertNotEqual(edge.confidence, TIER_CONFIDENCE[TIER_AFFILIATION])

    def test_a_person_reaches_the_system_their_organization_belongs_to(self):
        graph = build_parent_graph(affiliations=self._frame())
        graph.add_edge(node_key(NS_NPI, "1111111111"),
                       node_key(NS_SYSTEM, "ascension"), TIER_CCN_SYSTEM)
        res = graph.resolve(node_key(NS_NPI, "3333333333"))
        self.assertEqual(res.final_parent, node_key(NS_SYSTEM, "ascension"))
        self.assertEqual(res.hops, 2)
        self.assertIn(TIER_AFFILIATION, res.tiers)

    def test_affiliation_is_the_weakest_tier(self):
        # Anything an organization files about itself outranks an
        # inference about where a person practises.
        self.assertEqual(max(TIER_RANK, key=lambda t: TIER_RANK[t]),
                         TIER_AFFILIATION)
        graph = build_parent_graph(affiliations=self._frame())
        graph.add_edge("npi:3333333333", "org:FILED", TIER_NPPES_SUBPART)
        self.assertEqual(graph.resolve("npi:3333333333").final_parent,
                         "org:FILED")

    def test_a_missing_bridge_database_is_empty_not_an_error(self):
        """Every optional reference source in this package degrades to
        empty rather than taking the build down."""
        frame = load_affiliations("/nonexistent/nppes.db")
        self.assertTrue(frame.empty)
        self.assertEqual(build_parent_graph(affiliations=frame).nodes,
                         frozenset())


class AttachParentsTests(unittest.TestCase):
    """Widening a frame of CCNs with where each one's owner ends up."""

    def _frame(self) -> pd.DataFrame:
        return pd.DataFrame([
            {"ccn": "012501", "parent_ccn": "", "parent_ccn_source": "",
             "chain_name": "DAVITA", "system_id": "", "system_match": "",
             "system_name": "", "npi": "", "npi_source": "", "state": "AL"},
            {"ccn": "010001", "parent_ccn": "", "parent_ccn_source": "",
             "chain_name": "", "system_id": "", "system_match": "",
             "system_name": "", "npi": "", "npi_source": "", "state": "AL"},
        ])

    def test_the_declared_columns_are_all_added(self):
        widened = attach_parents(self._frame())
        for column in PARENT_COLUMNS:
            self.assertIn(column, widened.columns)

    def test_the_original_columns_survive_untouched(self):
        original = self._frame()
        widened = attach_parents(original)
        for column in original.columns:
            self.assertIn(column, widened.columns)
            self.assertEqual(list(widened[column]), list(original[column]))

    def test_a_resolved_row_carries_a_readable_name_not_just_a_key(self):
        row = attach_parents(self._frame()).iloc[0]
        self.assertEqual(row["final_parent"], node_key(NS_SYSTEM, "davita"))
        self.assertEqual(row["final_parent_name"], "DaVita Kidney Care")
        self.assertIn("012501", row["parent_basis"])

    def test_an_unresolved_row_is_blank_text_and_zero_counts(self):
        """Mixing "" into the count columns makes them object-typed, and
        every downstream `parent_hops > 1` then raises rather than
        filtering."""
        widened = attach_parents(self._frame())
        row = widened[widened["ccn"] == "010001"].iloc[0]
        self.assertEqual(row["final_parent"], "")
        self.assertEqual(row["parent_hops"], 0)
        self.assertEqual(row["parent_contested"], 0)
        self.assertEqual(widened["parent_hops"].dtype.kind, "i")

    def test_an_empty_frame_is_still_widened(self):
        widened = attach_parents(pd.DataFrame(columns=["ccn"]))
        for column in PARENT_COLUMNS:
            self.assertIn(column, widened.columns)

    def test_a_frame_without_the_key_column_is_not_an_error(self):
        widened = attach_parents(pd.DataFrame([{"something": "else"}]))
        self.assertEqual(list(widened["final_parent"]), [""])

    def test_a_supplied_graph_is_used_rather_than_rebuilt(self):
        """A parent is a fact about the whole graph. Resolving inside a
        filtered slice would drop every parent outside it."""
        graph = build_parent_graph(crosswalk=self._frame())
        one_row = self._frame().iloc[[1]]          # the unresolved CCN
        graph.add_edge(node_key(NS_CCN, "010001"),
                       node_key(NS_SYSTEM, "ascension"), TIER_CCN_SYSTEM)
        widened = attach_parents(one_row, graph=graph)
        self.assertEqual(widened.iloc[0]["final_parent"],
                         node_key(NS_SYSTEM, "ascension"))


class DisagreementFrameTests(unittest.TestCase):
    def _graph(self) -> ParentGraph:
        g = ParentGraph()
        g.add_edge("ccn:052583", "chain:INNOVATIVE DIALYSIS SYSTEMS",
                   TIER_CCN_CHAIN, "Innovative Dialysis Systems")
        g.add_edge("ccn:052583", "sys:us_renal_care", TIER_CCN_SYSTEM,
                   "^USRC ")
        return g

    def test_the_frame_has_the_declared_columns(self):
        frame = ownership_disagreements(self._graph())
        self.assertEqual(list(frame.columns), list(DISAGREEMENT_COLUMNS))

    def test_both_candidates_and_the_evidence_for_each_are_carried(self):
        """A work queue is useless if a reviewer has to go and find the
        two answers themselves."""
        row = ownership_disagreements(self._graph()).iloc[0]
        self.assertEqual(row["identifier"], "052583")
        self.assertEqual(row["resolved_parent"],
                         "chain:INNOVATIVE DIALYSIS SYSTEMS")
        self.assertEqual(row["rival_parent"], "sys:us_renal_care")
        self.assertIn("Innovative Dialysis Systems", row["evidence"])
        self.assertIn("^USRC", row["evidence"])

    def test_an_agreeing_graph_produces_an_empty_typed_frame(self):
        g = ParentGraph()
        g.add_edge("ccn:1", "chain:DAVITA", TIER_CCN_CHAIN)
        g.add_edge("ccn:1", "sys:davita", TIER_CCN_SYSTEM)
        g.add_edge("chain:DAVITA", "sys:davita", TIER_NAME_SYSTEM)
        frame = ownership_disagreements(g)
        self.assertTrue(frame.empty)
        self.assertEqual(list(frame.columns), list(DISAGREEMENT_COLUMNS))


class CrosswalkEdgeTests(unittest.TestCase):
    def _frame(self) -> pd.DataFrame:
        return pd.DataFrame([
            {"ccn": "010011", "parent_ccn": "", "chain_name": "",
             "system_id": "ascension", "system_match": "^ASCENSION",
             "system_name": "Ascension", "npi": "1111111111",
             "npi_source": "name+state+zip", "parent_ccn_source": ""},
            {"ccn": "01T011", "parent_ccn": "010011",
             "parent_ccn_source": "parent facility", "chain_name": "",
             "system_id": "ascension", "system_match": "", "system_name": "",
             "npi": "", "npi_source": ""},
            {"ccn": "012501", "parent_ccn": "", "chain_name": "DAVITA",
             "system_id": UNMAPPED_ID, "system_match": "", "system_name": "",
             "npi": "", "npi_source": "", "parent_ccn_source": ""},
        ])

    def test_each_claim_in_a_row_is_kept_separately(self):
        edges = edges_from_crosswalk(self._frame())
        tiers = sorted({e.tier for e in edges})
        self.assertEqual(tiers, sorted([TIER_CCN_PARENT, TIER_CCN_CHAIN,
                                        TIER_CCN_SYSTEM, TIER_NPI_CCN]))

    def test_the_unmapped_sentinel_never_becomes_an_edge(self):
        edges = edges_from_crosswalk(self._frame())
        self.assertFalse([e for e in edges if UNMAPPED_ID in e.parent])

    def test_the_billing_npi_hangs_off_its_facility(self):
        edges = edges_from_crosswalk(self._frame())
        npi_edges = [e for e in edges if e.child == node_key(NS_NPI,
                                                             "1111111111")]
        self.assertEqual(len(npi_edges), 1)
        self.assertEqual(npi_edges[0].parent, node_key(NS_CCN, "010011"))


class NpiFrameEdgeTests(unittest.TestCase):
    def test_a_frame_without_pecos_or_subpart_still_contributes(self):
        """Sources differ in what they carry. A missing column is a
        smaller contribution, never an exception."""
        frame = pd.DataFrame([{"npi": "1111111111", "system_id": "amr",
                               "match_basis": "legal name: ^AMR"}])
        edges = edges_from_npi_frame(frame)
        self.assertEqual([e.tier for e in edges], [TIER_NAME_SYSTEM])

    def test_subpart_and_pecos_are_read_when_present(self):
        frame = pd.DataFrame([{
            "npi": "1111111111", "parent_org_lbn": "ASCENSION HEALTH",
            "pecos_group": "0648177949", "system_id": "", "ccn": "010011"}])
        tiers = sorted({e.tier for e in edges_from_npi_frame(frame)})
        self.assertEqual(tiers, sorted([TIER_NPPES_SUBPART, TIER_PECOS_GROUP,
                                        TIER_NPI_CCN]))


class GroupLiftTests(unittest.TestCase):
    """A PECOS group outranks a name match, so an NPI stops at the group.
    The group's own members are what tell us whose group it is."""

    def _frame(self, systems) -> pd.DataFrame:
        return pd.DataFrame([
            {"npi": f"111111111{i}", "pecos_group": "555",
             "system_id": system, "match_basis": "legal name"}
            for i, system in enumerate(systems)])

    def test_a_unanimous_group_inherits_its_members_brand(self):
        graph = build_parent_graph(
            npi_frame=self._frame(["air_methods", "air_methods", ""]))
        res = graph.resolve(node_key(NS_NPI, "1111111112"))
        # The third member carries no brand of its own and still lands
        # under the system, via the group.
        self.assertEqual(res.final_parent, node_key(NS_SYSTEM, "air_methods"))
        self.assertEqual(res.hops, 2)

    def test_a_split_group_is_left_alone_rather_than_guessed(self):
        """A group whose members point at two systems has been through an
        acquisition, a mis-match, or both. Picking one puts the whole
        group under the wrong parent."""
        graph = build_parent_graph(
            npi_frame=self._frame(["air_methods", "global_medical_response"]))
        res = graph.resolve(node_key(NS_PECOS, "555"))
        self.assertTrue(res.is_root)


class BuildAndLiftTests(unittest.TestCase):
    def test_a_chain_is_lifted_to_the_system_behind_it(self):
        frame = pd.DataFrame([{
            "ccn": "012501", "parent_ccn": "", "parent_ccn_source": "",
            "chain_name": "DAVITA", "system_id": "", "system_match": "",
            "system_name": "", "npi": "", "npi_source": ""}])
        graph = build_parent_graph(crosswalk=frame)
        res = graph.resolve(node_key(NS_CCN, "012501"))
        self.assertEqual(res.final_parent, node_key(NS_SYSTEM, "davita"))
        self.assertEqual(res.hops, 2)

    def test_lifting_can_be_turned_off_to_see_the_raw_structure(self):
        frame = pd.DataFrame([{
            "ccn": "012501", "parent_ccn": "", "parent_ccn_source": "",
            "chain_name": "DAVITA", "system_id": "", "system_match": "",
            "system_name": "", "npi": "", "npi_source": ""}])
        graph = build_parent_graph(crosswalk=frame,
                                   lift_names_to_systems=False)
        res = graph.resolve(node_key(NS_CCN, "012501"))
        self.assertEqual(res.final_parent, node_key(NS_CHAIN, "DAVITA"))

    def test_a_chain_the_registry_does_not_know_stays_its_own_root(self):
        frame = pd.DataFrame([{
            "ccn": "012501", "parent_ccn": "", "parent_ccn_source": "",
            "chain_name": "SOME LOCAL DIALYSIS PARTNERSHIP",
            "system_id": "", "system_match": "", "system_name": "",
            "npi": "", "npi_source": ""}])
        graph = build_parent_graph(crosswalk=frame)
        res = graph.resolve(node_key(NS_CCN, "012501"))
        self.assertEqual(res.final_parent.split(":")[0], NS_CHAIN)
        self.assertEqual(res.hops, 1)

    def test_an_empty_build_is_an_empty_graph_not_an_error(self):
        graph = build_parent_graph()
        self.assertEqual(graph.nodes, frozenset())
        self.assertEqual(graph.stats()["claims"], 0)


class ResolutionFrameTests(unittest.TestCase):
    def _graph(self) -> ParentGraph:
        g = ParentGraph()
        g.add_edge("npi:1111111111", "ccn:010011", TIER_NPI_CCN)
        g.add_edge("ccn:010011", "sys:ascension", TIER_CCN_SYSTEM)
        return g

    def test_the_frame_has_the_declared_columns(self):
        frame = resolve_identifiers(self._graph())
        self.assertEqual(list(frame.columns), list(RESOLUTION_COLUMNS))

    def test_namespace_filtering_narrows_to_one_identifier_type(self):
        frame = resolve_identifiers(self._graph(), namespaces=(NS_NPI,))
        self.assertEqual(list(frame["node"]), ["npi:1111111111"])
        self.assertEqual(frame.iloc[0]["final_parent"], "sys:ascension")
        self.assertEqual(frame.iloc[0]["hops"], 2)

    def test_roots_are_included_rather_than_silently_dropped(self):
        """"This is the top of its tree" is an answer. A file that omits
        those rows looks like it lost them."""
        frame = resolve_identifiers(self._graph())
        self.assertIn("sys:ascension", set(frame["node"]))
        self.assertEqual(
            frame[frame["node"] == "sys:ascension"].iloc[0]["hops"], 0)

    def test_provenance_names_every_hop_and_the_tier_that_made_it(self):
        frame = resolve_identifiers(self._graph(), namespaces=(NS_NPI,))
        prov = frame.iloc[0]["provenance"]
        self.assertIn(TIER_NPI_CCN, prov)
        self.assertIn(TIER_CCN_SYSTEM, prov)
        self.assertIn("sys:ascension", prov)

    def test_an_empty_graph_yields_an_empty_typed_frame(self):
        frame = resolve_identifiers(ParentGraph())
        self.assertTrue(frame.empty)
        self.assertEqual(list(frame.columns), list(RESOLUTION_COLUMNS))


class RealGraphTests(unittest.TestCase):
    """Built once from the real crosswalk — the properties that have to
    hold on 48,510 rows, not on a fixture."""

    @classmethod
    def setUpClass(cls) -> None:
        from rcm_mc.data.provider_crosswalk import SCOPE_ALL, get_crosswalk
        cls.crosswalk = get_crosswalk(scope=SCOPE_ALL)
        cls.graph = build_parent_graph(crosswalk=cls.crosswalk)
        cls.stats = cls.graph.stats()

    def test_no_facility_is_parented_to_the_unmapped_sentinel(self):
        self.assertFalse([n for n in self.graph.nodes if UNMAPPED_ID in n])

    def test_the_real_ownership_graph_has_no_cycles(self):
        self.assertEqual(self.stats["cycles"], 0)
        self.assertEqual(self.stats["truncated"], 0)

    def test_real_chains_are_short(self):
        # Ownership here is facility → chain/parent → system. Anything
        # deeper would mean the graph has grown a structure nobody
        # designed.
        self.assertLessEqual(self.stats["max_hops"], 4)

    def test_most_certified_facilities_reach_a_named_parent(self):
        frame = resolve_identifiers(self.graph, namespaces=(NS_CCN,))
        reached = frame[frame["final_parent_namespace"] == NS_SYSTEM]
        self.assertGreater(len(reached), 10_000)
        # …and every one of them says which hop it is least sure about.
        self.assertTrue((reached["tier"].astype(str) != "").all())

    def test_disagreements_are_rare_enough_to_review_by_hand(self):
        """Contested rows are a work queue, not a statistic. If this
        number runs into the thousands the comparison is wrong again."""
        self.assertLess(self.stats["contested"], 500)

    def test_hospital_based_units_inherit_their_hospital_s_system(self):
        frame = resolve_identifiers(self.graph, namespaces=(NS_CCN,))
        units = frame[frame["identifier"].str.contains("T", regex=False)]
        self.assertGreater(len(units), 100)
        self.assertGreater((units["hops"] >= 2).sum(), 100)


if __name__ == "__main__":
    unittest.main()
