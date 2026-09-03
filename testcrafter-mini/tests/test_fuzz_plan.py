from testcrafter.synthesis.fuzz_plan import (
    bounds_from_requires,
    caller_for,
    loop_driving_params,
    plan_for_function,
    render_bound_statements,
    render_prank,
)


def fn(name, params=None, requires=None, loops=None, **kw):
    return {
        "name": name,
        "visibility": "external",
        "params": params or [],
        "requires": requires or [],
        "loops": loops or [],
        **kw,
    }


class TestLoopDrivingParams:
    def test_param_in_guard_is_detected(self):
        f = fn("g", [{"name": "n", "type": "uint256"}], loops=[{"guard": "(i < n)"}])
        assert loop_driving_params(f) == {"n"}

    def test_param_absent_from_guard_is_not_detected(self):
        f = fn(
            "g",
            [{"name": "n", "type": "uint256"}, {"name": "k", "type": "uint256"}],
            loops=[{"guard": "(i < n)"}],
        )
        assert loop_driving_params(f) == {"n"}

    def test_bounds_upper_is_also_searched(self):
        f = fn("g", [{"name": "m", "type": "uint256"}], loops=[{"guard": "", "bounds": {"upper": "m"}}])
        assert loop_driving_params(f) == {"m"}


class TestRequireBounds:
    def test_less_or_equal_literal(self):
        f = fn("g", [{"name": "n", "type": "uint256"}], requires=["n <= 16"])
        assert bounds_from_requires(f)["n"] == ("0", "16")

    def test_strict_less_than_literal_drops_one(self):
        f = fn("g", [{"name": "n", "type": "uint256"}], requires=["n < 100"])
        assert bounds_from_requires(f)["n"] == ("0", "99")

    def test_relation_to_another_param_is_kept(self):
        f = fn(
            "g",
            [{"name": "n", "type": "uint256"}, {"name": "maxN", "type": "uint256"}],
            requires=["n <= maxN"],
        )
        assert bounds_from_requires(f)["n"] == ("0", "maxN")

    def test_non_parameter_left_side_is_ignored(self):
        f = fn("g", [{"name": "n", "type": "uint256"}], requires=["totalSupply <= 100"])
        assert "totalSupply" not in bounds_from_requires(f)


class TestPlanning:
    def test_loop_driving_param_is_capped(self):
        f = fn("g", [{"name": "n", "type": "uint256"}], loops=[{"guard": "(i < n)"}])
        plan = plan_for_function(f, [], [], trip_cap=16)
        assert plan.bounds[0].high == "16"
        assert plan.bounds[0].drives_loop is True

    def test_non_driving_param_keeps_a_wide_range(self):
        f = fn("g", [{"name": "amount", "type": "uint256"}])
        plan = plan_for_function(f, [], [])
        assert plan.bounds[0].drives_loop is False
        assert int(plan.bounds[0].high) > 1000

    def test_require_and_trip_cap_take_the_smaller(self):
        f = fn("g", [{"name": "n", "type": "uint256"}], requires=["n <= 64"], loops=[{"guard": "(i < n)"}])
        plan = plan_for_function(f, [], [], trip_cap=16)
        assert plan.bounds[0].high == "16"

    def test_dependent_bound_is_emitted_after_its_reference(self):
        f = fn(
            "g",
            [{"name": "n", "type": "uint256"}, {"name": "maxN", "type": "uint256"}],
            requires=["n <= maxN"],
            loops=[{"guard": "(i <= n)"}],
        )
        plan = plan_for_function(f, [], [])
        assert [b.name for b in plan.bounds] == ["maxN", "n"]

    def test_array_params_are_listed_separately(self):
        f = fn("g", [{"name": "to", "type": "address[]"}, {"name": "n", "type": "uint256"}])
        plan = plan_for_function(f, [], [])
        assert plan.array_params == [("to", "address[]")]
        assert [b.name for b in plan.bounds] == ["n"]

    def test_bound_statements_are_valid_shape(self):
        f = fn("g", [{"name": "n", "type": "uint256"}], loops=[{"guard": "(i < n)"}])
        stmts = render_bound_statements(plan_for_function(f, [], []))
        assert stmts == ["n = uint256(bound(uint256(n), 0, 16));"]


class TestCallerSelection:
    def test_role_from_access_edge(self):
        f = fn("batchSend", modifiers=["onlyOwner"])
        edges = [{"function": "batchSend", "modifier": "onlyOwner", "role": "owner"}]
        role, _ = caller_for(f, edges, [])
        assert role == "owner"

    def test_role_from_dependency_condition(self):
        f = fn("releaseAll")
        deps = [
            {
                "function": "releaseAll",
                "source": "modifier:onlyArbiter",
                "condition": "msg.sender == arbiter",
                "role": "arbiter",
            }
        ]
        role, _ = caller_for(f, [], deps)
        assert role == "arbiter"

    def test_role_inferred_from_modifier_name(self):
        f = fn("settle")
        edges = [{"function": "settle", "modifier": "onlySeller", "role": ""}]
        role, _ = caller_for(f, edges, [])
        assert role == "seller"

    def test_role_from_bare_require(self):
        f = fn("withdraw", requires=["msg.sender == owner"])
        role, _ = caller_for(f, [], [])
        assert role == "owner"

    def test_unguarded_function_has_no_caller(self):
        f = fn("total")
        role, _ = caller_for(f, [], [])
        assert role is None

    def test_prank_statements_wrap_the_call(self):
        f = fn("batchSend")
        edges = [{"function": "batchSend", "modifier": "onlyOwner", "role": "owner"}]
        plan = plan_for_function(f, edges, [])
        pre, post = render_prank(plan, "uut")
        assert pre == ["vm.startPrank(uut.owner());"]
        assert post == ["vm.stopPrank();"]

    def test_no_prank_for_unguarded_function(self):
        plan = plan_for_function(fn("total"), [], [])
        assert render_prank(plan, "uut") == ([], [])


class TestTerminationSafety:
    def test_accumulator_step_param_cannot_be_zero(self):
        f = fn(
            "extend",
            [{"name": "step", "type": "uint256"}],
            loops=[
                {
                    "guard": "(added + step <= cap)",
                    "body_summary": {
                        "accumulator_facts": [
                            {"var": "added", "op": "+=", "source": {"expr": "step"}}
                        ]
                    },
                }
            ],
        )
        plan = plan_for_function(f, [], [])
        assert plan.bounds[0].low == "1"

    def test_plain_bound_param_may_be_zero(self):
        f = fn("g", [{"name": "n", "type": "uint256"}], loops=[{"guard": "(i < n)"}])
        assert plan_for_function(f, [], []).bounds[0].low == "0"

    def test_step_in_update_clause_is_also_protected(self):
        f = fn(
            "g",
            [{"name": "stride", "type": "uint256"}],
            loops=[{"guard": "(i < n)", "update": "(i += stride)"}],
        )
        assert plan_for_function(f, [], []).bounds[0].low == "1"


class TestGetterSuppression:
    @staticmethod
    def _model():
        return {
            "contract": {
                "name": "A",
                "access_control": [],
                "access_dependencies": [],
                "state": {"variables": [{"name": "items"}], "mappings": [{"name": "ownerOf"}]},
                "functions": [
                    fn("ownerOf", [{"name": "index", "type": "uint256"}]),
                    fn("items", [{"name": "index", "type": "uint256"}]),
                    fn("real", [{"name": "n", "type": "uint256"}]),
                ],
            }
        }

    def test_generated_getters_are_not_planned(self):
        from testcrafter.synthesis.fuzz_plan import plan_for_model

        assert [p.function for p in plan_for_model(self._model())] == ["real"]

    def test_synthetic_flag_is_also_respected(self):
        from testcrafter.synthesis.fuzz_plan import plan_for_model

        model = self._model()
        model["contract"]["state"] = {}
        model["contract"]["functions"][0]["synthetic"] = True
        assert "ownerOf" not in [p.function for p in plan_for_model(model)]


from testcrafter.synthesis.fuzz_plan import address_getters, caller_for

ROLE_REGISTRY = {
    "name": "RoleRegistry",
    "functions": [
        {
            "name": "operators",
            "visibility": "public",
            "params": [{"name": "", "type": "address"}],
            "returns": [{"type": "bool"}],
        },
        {
            "name": "admin",
            "visibility": "public",
            "params": [],
            "returns": [{"type": "address"}],
        },
    ],
}

GATED = {"name": "grant", "params": [], "requires": [], "loops": []}
BY_MODIFIER = [{"function": "grant", "modifier": "onlyOperator", "role": None}]


def test_a_role_without_a_zero_argument_getter_is_not_used():
    # onlyOperator suggests "operator", but the contract only has a mapping
    # called operators, whose getter takes an address.
    getters = address_getters(ROLE_REGISTRY)
    role, notes = caller_for(GATED, BY_MODIFIER, [], getters)
    assert role is None
    assert any("no zero-argument address getter" in n for n in notes)


def test_a_role_backed_by_a_real_getter_is_used():
    getters = address_getters(ROLE_REGISTRY)
    edges = [{"function": "grant", "modifier": "onlyAdmin", "role": "admin"}]
    role, _ = caller_for(GATED, edges, [], getters)
    assert role == "admin"


def test_address_getters_ignores_getters_that_take_arguments():
    assert address_getters(ROLE_REGISTRY) == {"admin"}


def test_a_bound_naming_contract_state_is_replaced_by_the_cap():
    fn = {
        "name": "fill",
        "visibility": "external",
        "params": [{"name": "r", "type": "uint256"}],
        "requires": ["require(r < grid.length)"],
        "loops": [{"loop_id": "C.fill#loop0", "guard": "(i < r)"}],
    }
    from testcrafter.synthesis.fuzz_plan import plan_for_function

    plan = plan_for_function(fn, [], [])
    high = {b.name: b.high for b in plan.bounds}
    # grid is contract state and is invisible from the test.
    assert "grid" not in high.get("r", "")
