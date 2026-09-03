from invsol_audit.auditor import (
    VERDICT_UNKNOWN,
    VERDICT_VERIFIED,
    audit_contract_invariants,
    z3_available,
)
from invsol_audit.encode import build_function_condition, build_function_model

IR = {
    "contract": {
        "name": "Bank",
        "functions": [
            {
                "name": "deposit",
                "mutability": "payable",
                "writes": ["total"],
                "storage_writes": [{"var": "total", "key": None, "kind": "assign"}],
            },
            {
                "name": "enrol",
                "mutability": "nonpayable",
                "writes": [],
                "storage_writes": [],
                "length_effects": [{"var": "holders", "op": "push"}],
            },
            {
                "name": "peek",
                "mutability": "view",
                "writes": [],
                "storage_writes": [],
            },
        ],
    }
}


class TestFunctionModel:
    def test_writes_are_collected_from_every_route(self):
        enrol = IR["contract"]["functions"][1]
        assert build_function_model(enrol).writes == {"holders"}

    def test_an_external_call_is_noted(self):
        model = build_function_model({"name": "pay", "external_calls": ["transfer"]})
        assert any("reentrant" in n for n in model.notes)


class TestConditions:
    def test_untouched_state_needs_no_exit_symbol(self):
        model = build_function_model(IR["contract"]["functions"][1])
        condition = build_function_condition(model, "total >= 0")
        assert "__after" not in condition.smt
        assert any("writes none of the locations" in a for a in condition.assumptions)

    def test_written_state_gets_an_unconstrained_exit_symbol(self):
        model = build_function_model(IR["contract"]["functions"][0])
        condition = build_function_condition(model, "total >= 0")
        assert "(declare-const total__after Int)" in condition.smt
        assert any("not modelled" in a for a in condition.assumptions)

    def test_a_length_effect_counts_as_a_write(self):
        model = build_function_model(IR["contract"]["functions"][1])
        condition = build_function_condition(model, "holders_length >= 0")
        assert "holders_length__after" in condition.smt


class TestAuditing:
    def test_read_only_functions_are_not_checked(self):
        verdicts = audit_contract_invariants(IR, ["total >= 0"])
        assert all("peek" not in v.loop_id for v in verdicts)

    def test_every_state_changing_function_is_checked(self):
        verdicts = audit_contract_invariants(IR, ["total >= 0"])
        assert {v.loop_id for v in verdicts} == {
            "deposit::contract",
            "enrol::contract",
        }

    def test_a_function_that_cannot_touch_it_preserves_it(self):
        verdicts = audit_contract_invariants(IR, ["total >= 0"])
        enrol = [v for v in verdicts if v.loop_id.startswith("enrol")][0]
        if z3_available():
            assert enrol.status == VERDICT_VERIFIED
        else:
            # Without a solver nothing can be discharged, so the most that can
            # be checked is that the query was built without an exit symbol.
            assert enrol.status == VERDICT_UNKNOWN
            assert any("writes none" in a for a in enrol.assumptions)

    def test_a_function_that_writes_it_is_not_claimed_either_way(self):
        # The IR records that a write happens, not what it stores, so this is
        # a failure to rule out a violation rather than a violation. The bound
        # has to be one the uint256 range does not already give, or the check
        # succeeds no matter what the function writes.
        verdicts = audit_contract_invariants(IR, ["total <= 100"])
        deposit = [v for v in verdicts if v.loop_id.startswith("deposit")][0]
        if z3_available():
            assert deposit.status == VERDICT_UNKNOWN
        assert any("not modelled" in a for a in deposit.assumptions)

    def test_a_bound_the_type_already_gives_is_verified_regardless(self):
        # total is a uint256, so total >= 0 cannot be falsified whatever the
        # function stores. Worth stating: such an invariant carries no
        # information about the contract.
        verdicts = audit_contract_invariants(IR, ["total >= 0"])
        deposit = [v for v in verdicts if v.loop_id.startswith("deposit")][0]
        if z3_available():
            assert deposit.status == VERDICT_VERIFIED


class TestTwoStateInvariants:
    def test_old_refers_to_the_entry_value(self):
        model = build_function_model(IR["contract"]["functions"][0])
        condition = build_function_condition(model, "total >= old(total)")
        # The bare name moves to the exit state; old(total) stays as it is.
        assert "(assert (not (>= total__after old_total)))" in condition.smt

    def test_a_two_state_claim_assumes_nothing_beforehand(self):
        model = build_function_model(IR["contract"]["functions"][0])
        condition = build_function_condition(model, "total >= old(total)")
        asserts = [l for l in condition.smt.splitlines() if l.startswith("(assert (")]
        # Only range constraints and the negated goal, no assumed premise.
        assert not any(l == "(assert (>= total old_total))" for l in asserts)

    def test_a_state_property_is_still_assumed_at_entry(self):
        model = build_function_model(IR["contract"]["functions"][0])
        condition = build_function_condition(model, "total <= 100")
        assert "(assert (<= total 100))" in condition.smt


class TestUnsupportedNotation:
    def test_template_notation_gets_one_verdict_not_one_per_function(self):
        expr = "forall k in observed(stakeOf): k in stakers"
        verdicts = audit_contract_invariants(IR, [expr])
        assert len(verdicts) == 1
        assert verdicts[0].loop_id == "contract"
        assert verdicts[0].status == "unsupported"

    def test_a_checkable_invariant_is_still_checked_per_function(self):
        verdicts = audit_contract_invariants(IR, ["total <= 100"])
        assert len(verdicts) == 2


class TestFrameReasoning:
    def untouched(self):
        return build_function_model(
            {"name": "enrol", "writes": ["holders"], "storage_writes": []}
        )

    def test_old_is_tied_to_the_entry_symbol(self):
        # Without this a function that never touches total would still fail
        # total >= old(total), because the names would be unrelated.
        condition = build_function_condition(self.untouched(), "total >= old(total)")
        assert "(assert (= old_total total))" in condition.smt

    def test_an_untouched_two_state_claim_is_discharged(self):
        condition = build_function_condition(self.untouched(), "total >= old(total)")
        assert "total__after" not in condition.smt
        if z3_available():
            from invsol_audit.auditor import solve
            assert solve(condition.smt)[0] == VERDICT_VERIFIED

    def test_a_composed_symbol_counts_as_written(self):
        # stake writes stakeOf, so sum(observed(stakeOf)) can move with it.
        # Missing this reported the invariant as verified, which is worse than
        # reporting it unknown.
        model = build_function_model(
            {"name": "stake", "writes": ["stakeOf"], "storage_writes": [{"var": "stakeOf"}]}
        )
        condition = build_function_condition(model, "sum(observed(stakeOf)) <= cap")
        assert "sum_observed_stakeOf__after" in condition.smt

    def test_an_unrelated_symbol_is_left_alone(self):
        model = build_function_model(
            {"name": "stake", "writes": ["stakeOf"], "storage_writes": [{"var": "stakeOf"}]}
        )
        condition = build_function_condition(model, "cap >= 0")
        assert "cap__after" not in condition.smt
