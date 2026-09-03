import pytest

from invsol_audit.auditor import (
    VERDICT_REFUTED,
    VERDICT_VERIFIED,
    audit_contract,
    check_invariant,
    summarise,
    z3_available,
)
from invsol_audit.encode import build_conditions, build_loop_model
from invsol_audit.expr import ParseError, free_variables, parse_expression, render

SUM_LOOP = {
    "loop_id": "S.total#loop0",
    "index_direction": "increasing",
    "bounds": {"index": "i", "lower": "0", "upper": "n", "inclusive_upper": False},
    "body_summary": {
        "accumulator_facts": [
            {
                "var": "s",
                "op": "+=",
                "kind": "sum",
                "source": {"expr": "numbers[i]", "base": "numbers", "container": "array"},
            }
        ]
    },
}

needs_z3 = pytest.mark.skipif(not z3_available(), reason="z3-solver is not installed")


class TestExpressions:
    @pytest.mark.parametrize(
        "text",
        [
            "s <= sum(numbers)",
            "i < n",
            "total >= old(total)",
            "sumShares <= 100",
            "i <= numbers.length",
            "isActive => balance >= 0",
            "shares[k] >= 0",
            "a + b * 2 <= c",
        ],
    )
    def test_round_trip(self, text):
        assert render(parse_expression(text))

    def test_aggregate_call_is_one_symbol(self):
        assert free_variables(parse_expression("s <= sum(numbers)")) == {"s", "sum_numbers"}

    def test_member_access_becomes_one_symbol(self):
        assert "numbers_length" in free_variables(parse_expression("i <= numbers.length"))

    def test_implication_parses(self):
        node = parse_expression("isActive => balance >= 0")
        assert node.op == "=>"

    def test_malformed_input_raises(self):
        with pytest.raises(ParseError):
            parse_expression("i <=")


class TestLoopModel:
    def test_index_advances_by_one(self):
        model = build_loop_model(SUM_LOOP)
        assert model.updates["i"] == "i + 1"

    def test_accumulator_update_comes_from_the_fact(self):
        model = build_loop_model(SUM_LOOP)
        assert model.updates["s"] == "s + numbers_at_i"

    def test_guard_follows_the_bounds(self):
        assert build_loop_model(SUM_LOOP).guard_expression() == "i < n"

    def test_decreasing_loop_counts_down(self):
        loop = {
            **SUM_LOOP,
            "index_direction": "decreasing",
            "bounds": {"index": "i", "lower": "0", "upper": "n", "inclusive_upper": False},
        }
        assert build_loop_model(loop).updates["i"] == "i - 1"


class TestConditions:
    def test_two_conditions_are_produced(self):
        conditions = build_conditions(build_loop_model(SUM_LOOP), "i <= n")
        assert [c.kind for c in conditions] == ["establishment", "preservation"]

    def test_establishment_substitutes_the_initial_index(self):
        conditions = build_conditions(build_loop_model(SUM_LOOP), "i <= n")
        assert "(<= 0 n)" in conditions[0].smt

    def test_preservation_states_the_transition(self):
        conditions = build_conditions(build_loop_model(SUM_LOOP), "i <= n")
        assert "(= i__next (+ i 1))" in conditions[1].smt

    def test_goal_is_asserted_negated(self):
        conditions = build_conditions(build_loop_model(SUM_LOOP), "i <= n")
        assert "(assert (not" in conditions[1].smt

    def test_unsigned_range_is_assumed(self):
        conditions = build_conditions(build_loop_model(SUM_LOOP), "s >= 0")
        assert ">= s 0" in conditions[0].smt

    def test_overflow_assumption_is_recorded(self):
        conditions = build_conditions(build_loop_model(SUM_LOOP), "s >= 0")
        assert any("overflow" in a for a in conditions[0].assumptions)

    def test_unparseable_invariant_is_reported_not_ignored(self):
        conditions = build_conditions(build_loop_model(SUM_LOOP), "i <=")
        assert conditions[0].kind == "parse"


@needs_z3
class TestVerdicts:
    def test_index_bound_is_verified(self):
        verdict = check_invariant(build_loop_model(SUM_LOOP), "i <= n")
        assert verdict.status == VERDICT_VERIFIED

    def test_accumulator_non_negativity_is_verified(self):
        verdict = check_invariant(build_loop_model(SUM_LOOP), "s >= 0")
        assert verdict.status == VERDICT_VERIFIED

    def test_false_invariant_is_refuted_with_a_model(self):
        verdict = check_invariant(build_loop_model(SUM_LOOP), "i >= n")
        assert verdict.status == VERDICT_REFUTED
        assert verdict.counterexample

    def test_arbitrary_cap_is_refuted(self):
        verdict = check_invariant(build_loop_model(SUM_LOOP), "s <= 100")
        assert verdict.status == VERDICT_REFUTED

    def test_summary_reports_precision(self):
        ir = {"contract": {"functions": [{"name": "total", "loops": [SUM_LOOP]}]}}
        relations = {
            "total": [
                {"expr": "i <= n", "scope": "loop"},
                {"expr": "i >= n", "scope": "loop"},
            ]
        }
        report = summarise(audit_contract(ir, relations))
        assert report["checked"] == 2
        assert report["precision"] == 0.5

    def test_postconditions_are_not_checked_as_loop_invariants(self):
        ir = {"contract": {"functions": [{"name": "total", "loops": [SUM_LOOP]}]}}
        relations = {"total": [{"expr": "s == sum(numbers)", "scope": "post"}]}
        assert audit_contract(ir, relations) == []
