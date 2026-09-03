import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "testcrafter-mini"))

from invsol_postcond.templates import explore, tally
from testcrafter.instrument.state_trace import parse_text

TRACE = """
  [INVSOL] STATE_ENTER deposit
  [INVSOL] VAR deposit total 0
  [INVSOL] VAR deposit holders_length 0
  [INVSOL] KEY deposit balances 0xAAA 0
  [INVSOL] STATE_EXIT deposit
  [INVSOL] VAR deposit total 100
  [INVSOL] VAR deposit holders_length 1
  [INVSOL] ELEM deposit holders 0 0xAAA
  [INVSOL] KEY deposit balances 0xAAA 100
  [INVSOL] STATE_ENTER deposit
  [INVSOL] VAR deposit total 100
  [INVSOL] VAR deposit holders_length 1
  [INVSOL] ELEM deposit holders 0 0xAAA
  [INVSOL] KEY deposit balances 0xBBB 0
  [INVSOL] STATE_EXIT deposit
  [INVSOL] VAR deposit total 250
  [INVSOL] VAR deposit holders_length 2
  [INVSOL] ELEM deposit holders 0 0xAAA
  [INVSOL] ELEM deposit holders 1 0xBBB
  [INVSOL] KEY deposit balances 0xAAA 100
  [INVSOL] KEY deposit balances 0xBBB 150
  [INVSOL] STATE_ENTER payout
  [INVSOL] VAR payout total 250
  [INVSOL] VAR payout holders_length 2
  [INVSOL] ELEM payout holders 0 0xAAA
  [INVSOL] ELEM payout holders 1 0xBBB
  [INVSOL] KEY payout balances 0xAAA 100
  [INVSOL] STATE_EXIT payout
  [INVSOL] VAR payout total 250
  [INVSOL] VAR payout holders_length 2
  [INVSOL] ELEM payout holders 0 0xAAA
  [INVSOL] ELEM payout holders 1 0xBBB
  [INVSOL] KEY payout balances 0xAAA 40
  [INVSOL] STATE_ENTER payout
  [INVSOL] VAR payout total 250
  [INVSOL] VAR payout holders_length 2
  [INVSOL] ELEM payout holders 0 0xAAA
  [INVSOL] ELEM payout holders 1 0xBBB
  [INVSOL] KEY payout balances 0xBBB 150
  [INVSOL] STATE_EXIT payout
  [INVSOL] VAR payout total 250
  [INVSOL] VAR payout holders_length 2
  [INVSOL] ELEM payout holders 0 0xAAA
  [INVSOL] ELEM payout holders 1 0xBBB
  [INVSOL] KEY payout balances 0xBBB 90
"""

IR = {
    "contract": {
        "name": "Bank",
        "state": {
            "variables": [
                {"name": "total", "type": "uint256"},
                {"name": "holders", "type": "address[]"},
                {"name": "balances", "type": "mapping(address => uint256)"},
            ],
            "mappings": [
                {"name": "balances", "key": "address", "value": "uint256"}
            ],
        },
        "functions": [
            {"name": "deposit", "external_calls": []},
            {"name": "payout", "external_calls": ["transfer"]},
        ],
    }
}


def calls():
    return parse_text(TRACE)


def expressions(template):
    return [i.expr for i in explore(calls(), IR) if i.template == template]


class TestParsing:
    def test_every_call_yields_a_pre_and_post_pair(self):
        observed = calls()
        assert [c.function for c in observed] == ["deposit", "deposit", "payout", "payout"]

    def test_values_arrays_and_mapping_entries_are_read(self):
        first = calls()[0]
        assert first.pre.values["total"] == 0
        assert first.post.values["holders_length"] == 1
        assert first.post.elements["holders"][0] == "0xaaa"
        assert first.post.mappings["balances"]["0xaaa"] == 100

    def test_forge_echoes_are_not_counted_twice(self):
        echoed = TRACE + '\n  console::log("[INVSOL] STATE_ENTER deposit")\n'
        assert len(parse_text(echoed)) == len(calls())

    def test_a_call_without_an_exit_is_not_observed(self):
        partial = "[INVSOL] STATE_ENTER deposit\n[INVSOL] VAR deposit total 5\n"
        assert parse_text(partial) == []


class TestTemplates:
    def test_monotonic_counter_finds_the_growing_total(self):
        assert "total >= old(total)" in expressions("MonotonicCounter")
        assert "holders_length >= old(holders_length)" in expressions("MonotonicCounter")

    def test_allowance_non_negativity_needs_an_observed_decrease(self):
        # balances[0xAAA] drops from 100 to 40 in payout without going negative.
        assert expressions("AllowanceNonNegativity")

    def test_distinct_addresses_are_reported(self):
        assert "forall j, k (j != k): holders[j] != holders[k]" in expressions(
            "DistinctAddressPrecondition"
        )

    def test_a_repeated_address_suppresses_the_claim(self):
        repeated = TRACE.replace("ELEM deposit holders 1 0xBBB", "ELEM deposit holders 1 0xAAA")
        found = explore(parse_text(repeated), IR)
        assert not [i for i in found if i.template == "DistinctAddressPrecondition"]

    def test_sum_mapping_bound_finds_the_scalar_that_dominates(self):
        assert "sum(observed(balances)) <= total" in expressions("SumMappingBound")

    def test_reentrancy_guarded_state_is_scoped_to_the_calling_function(self):
        found = [i for i in explore(calls(), IR) if i.template == "ReentrancyGuardedState"]
        assert found
        assert all(i.function == "payout" for i in found)

    def test_valid_sender_constraint_links_keys_to_the_recorded_array(self):
        assert "forall k in observed(balances): k in holders" in expressions(
            "ValidSenderConstraint"
        )

    def test_a_key_outside_the_array_suppresses_the_claim(self):
        stray = TRACE.replace("KEY payout balances 0xAAA 40", "KEY payout balances 0xCCC 40")
        found = explore(parse_text(stray), IR)
        assert not [i for i in found if i.template == "ValidSenderConstraint"]

    def test_all_six_templates_are_reported_even_when_empty(self):
        counts = tally(explore(calls(), IR))
        assert set(counts) == {
            "MonotonicCounter",
            "AllowanceNonNegativity",
            "DistinctAddressPrecondition",
            "SumMappingBound",
            "ReentrancyGuardedState",
            "ValidSenderConstraint",
        }

    def test_a_single_observation_is_not_enough(self):
        one = "\n".join(TRACE.splitlines()[1:9])
        assert explore(parse_text(one), IR) == []
