from invsol_postcond.relational import (
    Relation,
    conjunctive_relations,
    element_values,
    quantified_relations,
)

FILL_LOOP = {
    "loop_id": "C.fillSequence#loop0",
    "guard": "(i < n)",
    "body_summary": {
        "indices": ["i"],
        "array_update_facts": [
            {
                "var": "numbers",
                "scope": "state",
                "container": "array",
                "key": "i",
                "type": "uint256",
                "op": "=",
            }
        ],
    },
}

SIGNED_LOOP = {
    "loop_id": "C.fill#loop0",
    "body_summary": {
        "indices": ["i"],
        "array_update_facts": [
            {
                "var": "deltas",
                "scope": "state",
                "container": "array",
                "key": "i",
                "type": "int256",
                "op": "=",
            }
        ],
    },
}


class Snapshot:
    def __init__(self, elements, values=None):
        self.elements = elements
        self.values = values or {}


class Call:
    def __init__(self, pre, post, pre_values=None, post_values=None):
        self.pre = Snapshot(pre, pre_values)
        self.post = Snapshot(post, post_values)


def observed(*snapshots):
    """Build the (arrays, scalars) sequence quantified_relations expects."""
    return list(snapshots)


class TestElementValues:
    def test_entries_are_ordered_by_index(self):
        calls = [Call({}, {"xs": {2: "30", 0: "10", 1: "20"}})]
        arrays, _ = element_values(calls)[0]
        assert arrays["xs"] == [10, 20, 30]

    def test_scalars_are_kept_alongside_the_arrays(self):
        calls = [Call({}, {"xs": {0: "1"}}, post_values={"cap": 9, "xs_length": 1})]
        arrays, scalars = element_values(calls)[0]
        assert arrays["xs"] == [1]
        # A length is not a scalar worth bounding elements against.
        assert scalars == {"cap": 9}

    def test_non_numeric_entries_are_dropped(self):
        calls = [Call({}, {"holders": {0: "0xaaa", 1: "0xbbb"}})]
        assert element_values(calls) == []


class TestQuantified:
    def test_a_scalar_that_dominated_every_element_is_reported(self):
        obs = observed(
            ({"numbers": [3, 1, 2]}, {"cap": 10}),
            ({"numbers": [5, 4]}, {"cap": 10}),
        )
        found = [r.expr for r in quantified_relations(FILL_LOOP, obs)]
        assert (
            "\\forall k : uint256 ; k < numbers.length ==> numbers[k] <= cap"
            in found
        )

    def test_a_scalar_beaten_in_one_state_is_not_reported(self):
        obs = observed(
            ({"numbers": [3]}, {"size": 3}),
            ({"numbers": [5, 4]}, {"size": 2}),
        )
        assert not [r for r in quantified_relations(FILL_LOOP, obs) if "size" in r.expr]

    def test_a_scalar_missing_from_one_state_is_not_reported(self):
        obs = observed(
            ({"numbers": [1]}, {"cap": 10}),
            ({"numbers": [2]}, {}),
        )
        assert quantified_relations(FILL_LOOP, obs) == []

    def test_a_sorted_array_yields_an_ordering_claim(self):
        obs = observed(
            ({"numbers": [20, 50, 80]}, {}),
            ({"numbers": [20, 50, 80, 110]}, {}),
        )
        found = [r.expr for r in quantified_relations(FILL_LOOP, obs)]
        assert found == [
            "\\forall k : uint256 ; "
            "k + 1 < numbers.length ==> numbers[k] <= numbers[k + 1]"
        ]

    def test_one_out_of_order_state_withdraws_the_claim(self):
        obs = observed(
            ({"numbers": [20, 50, 80]}, {}),
            ({"numbers": [80, 50, 20]}, {}),
        )
        assert quantified_relations(FILL_LOOP, obs) == []

    def test_a_single_observation_is_not_enough(self):
        assert quantified_relations(FILL_LOOP, observed(({"numbers": [1, 2]}, {}))) == []

    def test_non_negativity_is_skipped_for_an_unsigned_array(self):
        obs = observed(({"numbers": [1, 2]}, {}), ({"numbers": [3, 4]}, {}))
        assert not any(">= 0" in r.expr for r in quantified_relations(FILL_LOOP, obs))

    def test_non_negativity_is_kept_for_a_signed_array(self):
        obs = observed(({"deltas": [1, 2]}, {}), ({"deltas": [0, 5]}, {}))
        found = [r.expr for r in quantified_relations(SIGNED_LOOP, obs)]
        assert any("deltas[k] >= 0" in e for e in found)

    def test_an_array_the_loop_does_not_write_is_ignored(self):
        obs = observed(({"other": [1, 2]}, {}), ({"other": [3, 4]}, {}))
        assert quantified_relations(FILL_LOOP, obs) == []

    def test_the_emitted_form_matches_the_grammar(self):
        obs = observed(({"numbers": [1, 2]}, {"cap": 9}), ({"numbers": [3]}, {"cap": 9}))
        for rel in quantified_relations(FILL_LOOP, obs):
            # \forall IDENTIFIER : type ; expression, per SolidityInvariant.g
            assert rel.expr.startswith("\\forall k : uint256 ; ")
            assert " ==> " in rel.expr
            assert rel.scope == "post"


class TestConjunctive:
    def relations(self):
        # The shapes relational.py actually produces: the index bound is
        # "i >= 0", not "0 <= i".
        return [
            Relation(expr="i >= 0", scope="loop", origin="fact", support=3, loop_id="L"),
            Relation(expr="i >= old(i)", scope="loop", origin="fact", support=3, loop_id="L"),
            Relation(expr="s >= 0", scope="loop", origin="trace", support=5, loop_id="L"),
            Relation(expr="s <= sum(numbers)", scope="loop", origin="trace", support=5, loop_id="L"),
        ]

    def test_an_index_fact_is_paired_with_a_body_fact(self):
        found = conjunctive_relations(FILL_LOOP, self.relations())
        assert len(found) == 1
        assert found[0].expr == "i >= 0 && s >= 0"
        assert found[0].scope == "post"

    def test_halves_with_calls_or_previous_state_are_avoided(self):
        expr = conjunctive_relations(FILL_LOOP, self.relations())[0].expr
        assert "sum(" not in expr and "old(" not in expr

    def test_support_is_the_weaker_of_the_two(self):
        assert conjunctive_relations(FILL_LOOP, self.relations())[0].support == 3

    def test_nothing_is_composed_without_a_body_fact(self):
        only_index = [
            Relation(expr="i >= 0", scope="loop", origin="fact", support=3, loop_id="L")
        ]
        assert conjunctive_relations(FILL_LOOP, only_index) == []

    def test_nothing_is_composed_without_an_index(self):
        no_index = {"loop_id": "L", "body_summary": {"indices": []}}
        assert conjunctive_relations(no_index, self.relations()) == []
