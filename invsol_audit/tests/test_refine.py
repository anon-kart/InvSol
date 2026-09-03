from invsol_audit.auditor import Verdict
from invsol_audit.refine import (
    RoundSummary,
    has_converged,
    inject_seed_tests,
    priority_functions,
    render_seed_tests,
    seeds_from_verdicts,
)

IR = {
    "contract": {
        "name": "C",
        "functions": [
            {
                "name": "scaled",
                "params": [
                    {"name": "scale", "type": "uint256"},
                    {"name": "maxCells", "type": "uint256"},
                ],
                "loops": [{"loop_id": "C.scaled#loop1"}],
            },
            {
                "name": "summed",
                "params": [{"name": "limit", "type": "uint256"}],
                "loops": [{"loop_id": "C.summed#loop0"}],
            },
            {
                "name": "batched",
                "params": [{"name": "to", "type": "address[]"}],
                "loops": [{"loop_id": "C.batched#loop0"}],
            },
        ],
    }
}


def refuted(loop_id, invariant, counterexample):
    return Verdict(
        loop_id=loop_id, invariant=invariant, status="refuted", counterexample=counterexample
    )


class TestSeedExtraction:
    def test_parameter_values_become_a_seed(self):
        seeds = seeds_from_verdicts(
            IR, [refuted("C.scaled#loop1", "touched <= n", {"scale": "7", "maxCells": "2"})]
        )
        assert seeds[0].arguments == {"scale": "7", "maxCells": "2"}

    def test_non_parameter_symbols_are_ignored(self):
        seeds = seeds_from_verdicts(
            IR, [refuted("C.summed#loop0", "s <= 100", {"limit": "9", "s": "101", "i": "3"})]
        )
        assert seeds[0].arguments == {"limit": "9"}

    def test_primed_names_map_back_to_the_parameter(self):
        seeds = seeds_from_verdicts(
            IR, [refuted("C.summed#loop0", "x", {"limit__next": "4"})]
        )
        assert seeds[0].arguments == {"limit": "4"}

    def test_verified_results_produce_no_seed(self):
        verdict = Verdict(loop_id="C.summed#loop0", invariant="i >= 0", status="verified")
        assert seeds_from_verdicts(IR, [verdict]) == []

    def test_negative_value_for_an_unsigned_parameter_is_dropped(self):
        seeds = seeds_from_verdicts(IR, [refuted("C.summed#loop0", "x", {"limit": "-3"})])
        assert seeds == []

    def test_seed_count_per_function_is_capped(self):
        many = [refuted("C.summed#loop0", f"inv{i}", {"limit": str(i)}) for i in range(10)]
        assert len(seeds_from_verdicts(IR, many, limit=3)) == 3

    def test_unknown_loop_is_skipped(self):
        assert seeds_from_verdicts(IR, [refuted("C.missing#loop0", "x", {"limit": "1"})]) == []


class TestPriority:
    def test_functions_are_ordered_by_failure_count(self):
        verdicts = [
            refuted("C.summed#loop0", "a", {"limit": "1"}),
            refuted("C.summed#loop0", "b", {"limit": "2"}),
            refuted("C.scaled#loop1", "c", {"scale": "1"}),
        ]
        assert priority_functions(verdicts, IR) == ["summed", "scaled"]

    def test_verified_results_do_not_raise_priority(self):
        verdicts = [Verdict(loop_id="C.summed#loop0", invariant="x", status="verified")]
        assert priority_functions(verdicts, IR) == []


class TestReplayTests:
    def test_directed_test_uses_the_reported_values(self):
        seeds = seeds_from_verdicts(
            IR, [refuted("C.scaled#loop1", "x", {"scale": "7", "maxCells": "2"})]
        )
        rendered = "\n".join(render_seed_tests(seeds, IR))
        assert "uut.scaled(7, 2)" in rendered

    def test_missing_parameters_get_a_default(self):
        seeds = seeds_from_verdicts(IR, [refuted("C.scaled#loop1", "x", {"scale": "5"})])
        assert "uut.scaled(5, 1)" in "\n".join(render_seed_tests(seeds, IR))

    def test_array_parameters_are_not_replayed(self):
        seeds = [
            s
            for s in seeds_from_verdicts(IR, [refuted("C.batched#loop0", "x", {"to": "1"})])
        ]
        assert render_seed_tests(seeds, IR) == []

    def test_injection_keeps_braces_balanced(self):
        seeds = seeds_from_verdicts(IR, [refuted("C.summed#loop0", "x", {"limit": "9"})])
        harness = "contract H is Test {\n    function testFuzz_x() public {}\n}\n"
        out = inject_seed_tests(harness, render_seed_tests(seeds, IR))
        assert out.count("{") == out.count("}")
        assert "test_seed_summed" in out

    def test_injection_without_seeds_is_a_no_op(self):
        harness = "contract H is Test {}\n"
        assert inject_seed_tests(harness, []) == harness


class TestConvergence:
    def test_progress_means_another_round(self):
        assert has_converged([RoundSummary(1, 61, 23, 38, 4)]) is False

    def test_no_refutations_stops(self):
        assert has_converged([RoundSummary(1, 61, 61, 0, 0)]) is True

    def test_no_new_seeds_stops(self):
        assert has_converged([RoundSummary(1, 61, 50, 11, 0)]) is True

    def test_repeated_outcome_stops(self):
        history = [RoundSummary(1, 61, 60, 1, 1), RoundSummary(2, 61, 60, 1, 1)]
        assert has_converged(history) is True

    def test_empty_history_does_not_stop(self):
        assert has_converged([]) is False
