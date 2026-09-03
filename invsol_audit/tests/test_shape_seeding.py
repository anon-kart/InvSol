from invsol_audit.auditor import Verdict
from invsol_audit.refine import (
    plan_shape_call,
    render_seed_tests,
    seeds_from_verdicts,
    shape_requests,
)

IR = {
    "contract": {
        "name": "LoopPlayground",
        "state": {
            "variables": [
                {"name": "numbers", "type": "uint256[]"},
                {"name": "grid", "type": "uint256[][]"},
                {"name": "depositorKeys", "type": "address[]"},
                {"name": "seededKeys", "type": "address[]"},
                {"name": "owner", "type": "address"},
            ],
            "mappings": [{"name": "deposits"}],
        },
        "functions": [
            {
                "name": "scaledAddToGrid",
                "visibility": "external",
                "params": [
                    {"name": "scale", "type": "uint256"},
                    {"name": "maxCells", "type": "uint256"},
                ],
                "loops": [{"loop_id": "LoopPlayground.scaledAddToGrid#loop1"}],
                "storage_aliases": [
                    {"name": "row", "base": "grid", "via": "index", "index": "r"}
                ],
            },
            {
                "name": "sumNumbersBounded",
                "visibility": "external",
                "params": [{"name": "limit", "type": "uint256"}],
                "loops": [{"loop_id": "LoopPlayground.sumNumbersBounded#loop0"}],
            },
            {
                "name": "accumulateDeposits",
                "visibility": "external",
                "params": [{"name": "limit", "type": "uint256"}],
                "loops": [{"loop_id": "LoopPlayground.accumulateDeposits#loop0"}],
            },
            {
                "name": "pushRow",
                "visibility": "external",
                "params": [
                    {"name": "row", "type": "uint256[]"},
                    {"name": "maxCols", "type": "uint256"},
                ],
                "length_effects": [
                    {
                        "var": "grid",
                        "op": "push",
                        "count": "1",
                        "in_loop": False,
                        "loop_bound": "",
                        "conditional": False,
                        "element_source": {
                            "kind": "param",
                            "name": "row",
                            "type": "uint256[]",
                        },
                    }
                ],
            },
            {
                "name": "appendMany",
                "visibility": "external",
                "params": [
                    {"name": "n", "type": "uint256"},
                    {"name": "base", "type": "uint256"},
                    {"name": "maxN", "type": "uint256"},
                ],
                "length_effects": [
                    {
                        "var": "numbers",
                        "op": "push",
                        "count": "n",
                        "in_loop": True,
                        "loop_bound": "n",
                        "conditional": False,
                        "element_source": {"kind": "expression", "name": "(base + i)"},
                    }
                ],
            },
            {
                "name": "deposit",
                "visibility": "external",
                "params": [],
                "length_effects": [
                    {
                        "var": "depositorKeys",
                        "op": "push",
                        "count": "1",
                        "in_loop": False,
                        "loop_bound": "",
                        "conditional": True,
                        "element_source": {"kind": "expression", "name": "msg.sender"},
                    }
                ],
            },
            {
                "name": "registerKey",
                "visibility": "external",
                "params": [{"name": "who", "type": "address"}],
                "length_effects": [
                    {
                        "var": "depositorKeys",
                        "op": "push",
                        "count": "1",
                        "in_loop": False,
                        "loop_bound": "",
                        "conditional": False,
                        "element_source": {"kind": "param", "name": "who", "type": "address"},
                    }
                ],
            },
            {
                "name": "seedThreeKeys",
                "visibility": "external",
                "params": [],
                "length_effects": [
                    {
                        "var": "seededKeys",
                        "op": "push",
                        "count": "1",
                        "in_loop": False,
                        "loop_bound": "",
                        "conditional": False,
                        "element_source": {"kind": "expression", "name": "a"},
                    },
                    {
                        "var": "seededKeys",
                        "op": "push",
                        "count": "1",
                        "in_loop": False,
                        "loop_bound": "",
                        "conditional": False,
                        "element_source": {"kind": "expression", "name": "b"},
                    },
                    {
                        "var": "seededKeys",
                        "op": "push",
                        "count": "1",
                        "in_loop": False,
                        "loop_bound": "",
                        "conditional": False,
                        "element_source": {"kind": "expression", "name": "c"},
                    },
                ],
            },
        ],
    }
}

SCALED = "LoopPlayground.scaledAddToGrid#loop1"
SUMMED = "LoopPlayground.sumNumbersBounded#loop0"
DEPOSITS = "LoopPlayground.accumulateDeposits#loop0"


def refuted(loop_id, invariant, counterexample):
    return Verdict(
        loop_id=loop_id,
        invariant=invariant,
        status="refuted",
        counterexample=counterexample,
    )


def function_named(name):
    for fn in IR["contract"]["functions"]:
        if fn["name"] == name:
            return fn
    raise AssertionError(name)


class TestShapeRequests:
    def test_alias_resolves_to_its_state_array(self):
        requests = shape_requests(
            IR,
            function_named("scaledAddToGrid"),
            {"row_length": "1", "touched": "1"},
        )
        assert len(requests) == 1
        assert requests[0].var == "grid"
        assert requests[0].target == 1
        assert requests[0].nested is True

    def test_state_array_is_read_directly(self):
        requests = shape_requests(
            IR, function_named("sumNumbersBounded"), {"numbers_length": "3"}
        )
        assert len(requests) == 1
        assert requests[0].var == "numbers"
        assert requests[0].nested is False

    def test_unknown_symbols_are_dropped(self):
        assert shape_requests(IR, function_named("sumNumbersBounded"), {"foo_length": "2"}) == []

    def test_unreachable_lengths_are_dropped(self):
        huge = str((1 << 256) - 1)
        assert shape_requests(IR, function_named("sumNumbersBounded"), {"numbers_length": huge}) == []


class TestShapePlanning:
    def test_nested_length_uses_a_producer_that_pushes_a_parameter(self):
        request = shape_requests(
            IR, function_named("scaledAddToGrid"), {"row_length": "2"}
        )[0]
        call = plan_shape_call(request, IR)
        assert call.function == "pushRow"
        assert call.array_argument == (0, "uint256", 2)
        assert call.repeat == 1

    def test_loop_bounded_producer_is_called_once_with_the_target(self):
        request = shape_requests(
            IR, function_named("sumNumbersBounded"), {"numbers_length": "5"}
        )[0]
        call = plan_shape_call(request, IR)
        assert call.function == "appendMany"
        assert call.arguments[0] == "5"
        assert call.repeat == 1

    def test_single_push_producer_is_repeated(self):
        request = shape_requests(
            IR, function_named("accumulateDeposits"), {"depositorKeys_length": "3"}
        )[0]
        call = plan_shape_call(request, IR)
        assert call.function == "registerKey"
        assert call.repeat == 3

    def test_several_pushes_per_call_reduce_the_repeat_count(self):
        request = shape_requests(
            IR, function_named("accumulateDeposits"), {"seededKeys_length": "5"}
        )[0]
        call = plan_shape_call(request, IR)
        assert call.function == "seedThreeKeys"
        assert call.repeat == 2

    def test_conditional_producer_is_tried_last(self):
        request = shape_requests(
            IR, function_named("accumulateDeposits"), {"depositorKeys_length": "2"}
        )[0]
        assert plan_shape_call(request, IR).function == "registerKey"

    def test_zero_length_needs_no_calls(self):
        request = shape_requests(
            IR, function_named("sumNumbersBounded"), {"numbers_length": "0"}
        )[0]
        assert plan_shape_call(request, IR) is None


class TestSeedsAndRendering:
    def test_shape_alone_produces_a_seed(self):
        seeds = seeds_from_verdicts(
            IR, [refuted(SCALED, "touched <= row.length", {"row_length": "1"})]
        )
        assert len(seeds) == 1
        assert seeds[0].arguments == {}
        assert seeds[0].shape_calls[0].function == "pushRow"

    def test_rendered_test_builds_the_shape_before_replaying(self):
        seeds = seeds_from_verdicts(
            IR, [refuted(SCALED, "touched <= row.length", {"row_length": "1"})]
        )
        body = "\n".join(render_seed_tests(seeds, IR))

        assert "uint256[] memory _shape0_0_0 = new uint256[](1);" in body
        assert "uut.pushRow(_shape0_0_0, 64)" in body
        assert body.index("uut.pushRow") < body.index("uut.scaledAddToGrid")

    def test_round_number_keeps_generated_names_apart(self):
        seeds = seeds_from_verdicts(
            IR, [refuted(SCALED, "touched <= row.length", {"row_length": "1"})]
        )
        first = "\n".join(render_seed_tests(seeds, IR, round_index=0))
        second = "\n".join(render_seed_tests(seeds, IR, round_index=1))

        assert "test_seed_scaledAddToGrid_0_0" in first
        assert "test_seed_scaledAddToGrid_1_0" in second
        assert "_shape1_0_0" in second

    def test_repeated_producer_is_rendered_as_a_loop(self):
        seeds = seeds_from_verdicts(
            IR, [refuted(DEPOSITS, "total >= 0", {"depositorKeys_length": "3"})]
        )
        body = "\n".join(render_seed_tests(seeds, IR))

        assert "for (uint256 s = 0; s < 3; s++)" in body
        assert "uut.registerKey(actorA)" in body

    def test_parameters_and_shape_combine(self):
        seeds = seeds_from_verdicts(
            IR,
            [refuted(SUMMED, "s <= 100", {"limit": "4", "numbers_length": "5"})],
        )
        body = "\n".join(render_seed_tests(seeds, IR))

        assert seeds[0].arguments == {"limit": "4"}
        assert "uut.appendMany(5, 64, 64)" in body
        assert "uut.sumNumbersBounded(4)" in body

    def test_verdicts_without_shape_behave_as_before(self):
        seeds = seeds_from_verdicts(
            IR, [refuted(SUMMED, "s <= 100", {"limit": "9", "s": "101"})]
        )
        assert seeds[0].arguments == {"limit": "9"}
        assert seeds[0].shape_calls == []


class TestRepeatedRounds:
    def test_the_same_seed_renders_a_complete_test_each_round(self):
        seeds = seeds_from_verdicts(
            IR, [refuted(SCALED, "touched <= row.length", {"row_length": "1"})]
        )
        first = render_seed_tests(seeds, IR, round_index=0)
        second = render_seed_tests(seeds, IR, round_index=1)

        for lines in (first, second):
            body = "\n".join(lines)
            assert body.count("{") == body.count("}")
            assert "uut.pushRow" in body
            assert "uut.scaledAddToGrid" in body

    def test_line_level_deduplication_would_break_the_harness(self):
        seeds = seeds_from_verdicts(
            IR, [refuted(SCALED, "touched <= row.length", {"row_length": "1"})]
        )
        first = render_seed_tests(seeds, IR, round_index=0)
        second = render_seed_tests(seeds, IR, round_index=1)

        naive = [line for line in second if line not in first]
        body = "\n".join(naive)
        assert body.count("{") != body.count("}")
