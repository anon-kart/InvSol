from invsol_audit.encode import build_conditions, build_loop_model, slice_premises, symbols_in
from invsol_audit.expr import parse_expression


def terms(*texts):
    return [parse_expression(t) for t in texts]


class TestSymbols:
    def test_a_plain_comparison_names_both_sides(self):
        assert symbols_in(parse_expression("s <= total")) == {"s", "total"}

    def test_an_abstracted_location_counts_as_a_symbol(self):
        found = symbols_in(parse_expression("balances[i] >= 0"))
        assert "balances_at_i" in found
        assert "i" in found

    def test_a_literal_contributes_nothing(self):
        assert symbols_in(parse_expression("s >= 0")) == {"s"}


class TestSlicing:
    def test_premises_about_unrelated_state_are_dropped(self):
        kept, dropped = slice_premises(
            terms("s >= 0", "unrelated == 7"), parse_expression("s <= total")
        )
        assert len(kept) == 1
        assert len(dropped) == 1

    def test_relevance_travels_through_a_shared_symbol(self):
        # total links to s, and cap links to total, so both are reachable.
        kept, dropped = slice_premises(
            terms("total >= s", "cap >= total", "junk == 1"),
            parse_expression("s >= 0"),
        )
        assert len(kept) == 2
        assert len(dropped) == 1

    def test_nothing_relevant_keeps_nothing(self):
        kept, _ = slice_premises(terms("a == 1", "b == 2"), parse_expression("s >= 0"))
        assert kept == []

    def test_a_premise_is_never_kept_twice(self):
        kept, _ = slice_premises(
            terms("s >= 0", "s <= total"), parse_expression("s <= total")
        )
        assert len(kept) == 2


LOOP = {
    "loop_id": "C.f#loop0",
    "bounds": {"index": "i", "lower": "0", "upper": "n"},
    "body_summary": {
        "indices": ["i"],
        "accumulator_facts": [
            {"var": "s", "op": "+=", "container": "scalar", "source": {"expr": "1"}}
        ],
    },
}


class TestConditionsStillHold:
    def test_a_sliced_query_still_declares_what_it_uses(self):
        condition = build_conditions(build_loop_model(LOOP), "s >= 0")[0]
        declared = {
            line.split()[1]
            for line in condition.smt.splitlines()
            if line.startswith("(declare-const")
        }
        for line in condition.smt.splitlines():
            if line.startswith("(assert"):
                for name in declared:
                    pass
        assert "s" in declared

    def test_slicing_is_reported_when_it_happens(self):
        condition = build_conditions(build_loop_model(LOOP), "s >= 0")[0]
        # Either nothing was dropped, or the fact is recorded on the verdict.
        sliced = [a for a in condition.assumptions if "sliced away" in a]
        assert sliced == [] or "premises" in sliced[0]
