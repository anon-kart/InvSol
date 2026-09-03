from testcrafter.synthesis.loop_harness import (
    find_producers,
    generate_loop_harness,
    loop_state_dependencies,
)


def model_with(functions, state=None, deps=None, pragma="0.8.19"):
    return {
        "pragma": pragma,
        "contract": {
            "name": "Bank",
            "access_control": [],
            "access_dependencies": deps or [],
            "state": state or {"variables": [{"name": "stakers"}], "mappings": [{"name": "stakeOf"}]},
            "functions": functions,
        },
    }


CTOR = {
    "name": "constructor",
    "visibility": "public",
    "mutability": "nonpayable",
    "params": [{"name": "rate", "type": "uint256"}],
    "loops": [],
}

STAKE = {
    "name": "stake",
    "visibility": "external",
    "mutability": "nonpayable",
    "params": [{"name": "amount", "type": "uint256"}],
    "requires": ["amount > 0"],
    "member_accesses": ["msg.sender"],
    "writes": ["stakeOf", "stakers"],
    "storage_writes": [{"var": "stakeOf", "key": "msg.sender"}, {"var": "stakers"}],
    "loops": [],
}

ACCRUE = {
    "name": "accrueAll",
    "visibility": "external",
    "mutability": "nonpayable",
    "modifiers": ["onlyOwner"],
    "params": [],
    "storage_reads": [{"var": "stakers"}, {"var": "stakeOf"}],
    "loops": [
        {
            "loop_id": "Bank.accrueAll#loop0",
            "guard": "(i < stakers.length)",
            "body_summary": {
                "accumulator_facts": [
                    {
                        "var": "issued",
                        "op": "+=",
                        "source": {"expr": "stakeOf[stakers[i]]", "base": "stakeOf", "scope": "state"},
                    }
                ]
            },
        }
    ],
}

OWNER_DEP = [
    {
        "function": "accrueAll",
        "source": "modifier:onlyOwner",
        "condition": "msg.sender == owner",
        "role": "owner",
    }
]


class TestDependencies:
    def test_state_read_by_loop_is_a_dependency(self):
        deps = loop_state_dependencies(ACCRUE)
        assert "stakers" in deps and "stakeOf" in deps

    def test_producer_is_the_function_writing_that_state(self):
        producers = find_producers(ACCRUE, [CTOR, STAKE, ACCRUE], {"stakers", "stakeOf"})
        assert [p["name"] for p in producers] == ["stake"]

    def test_function_with_no_state_loops_needs_no_producer(self):
        pure = {
            "name": "count",
            "visibility": "external",
            "mutability": "pure",
            "params": [{"name": "n", "type": "uint256"}],
            "loops": [{"guard": "(i < n)", "body_summary": {}}],
        }
        assert find_producers(pure, [CTOR, pure], {"stakers"}) == []

    def test_read_only_function_is_never_a_producer(self):
        viewer = {**STAKE, "name": "peek", "mutability": "view"}
        producers = find_producers(ACCRUE, [CTOR, viewer, ACCRUE], {"stakers", "stakeOf"})
        assert producers == []


# The public getter solc generates for `address public owner`. The harness
# only pranks as a role when a zero-argument address getter really exists.
OWNER_GETTER = {
    "name": "owner",
    "visibility": "public",
    "mutability": "view",
    "params": [],
    "returns": [{"type": "address"}],
    "loops": [],
}


class TestHarnessEmission:
    def _harness(self):
        return generate_loop_harness(
            model_with([CTOR, STAKE, ACCRUE, OWNER_GETTER], deps=OWNER_DEP),
            contract_name="Bank",
            import_path="src/Bank.sol",
        )

    def test_contract_pragma_is_reused(self):
        assert "pragma solidity 0.8.19;" in self._harness()

    def test_constructor_arguments_are_supplied(self):
        assert "new Bank(10);" in self._harness()

    def test_seed_call_precedes_the_target_call(self):
        out = self._harness()
        assert out.index("uut.stake(") < out.index("uut.accrueAll(")

    def test_sender_keyed_producer_is_called_by_several_actors(self):
        out = self._harness()
        assert out.count("uut.stake(10)") == 3
        assert "vm.prank(actorA);" in out

    def test_gated_target_is_called_through_a_prank(self):
        out = self._harness()
        assert "vm.startPrank(uut.owner());" in out
        assert "vm.stopPrank();" in out

    def test_calls_are_wrapped_so_a_revert_does_not_fail_the_run(self):
        assert "try uut.accrueAll() {} catch {}" in self._harness()

    def test_only_loop_bearing_functions_get_tests(self):
        out = self._harness()
        assert "function testFuzz_accrueAll(" in out
        assert "function testFuzz_stake(" not in out

    def test_bounded_parameter_appears_in_the_test_signature(self):
        fn = {
            "name": "batch",
            "visibility": "external",
            "mutability": "nonpayable",
            "params": [{"name": "n", "type": "uint256"}],
            "requires": ["n <= 32"],
            "loops": [{"guard": "(i < n)", "body_summary": {}}],
        }
        out = generate_loop_harness(
            model_with([CTOR, fn]), contract_name="Bank", import_path="src/Bank.sol"
        )
        assert "function testFuzz_batch(uint256 n) public" in out
        assert "bound(uint256(n), 0, 16)" in out

    def test_dynamic_array_argument_is_constructed(self):
        fn = {
            "name": "send",
            "visibility": "external",
            "mutability": "nonpayable",
            "params": [{"name": "to", "type": "address[]"}],
            "loops": [{"guard": "(i < to.length)", "body_summary": {}}],
        }
        out = generate_loop_harness(
            model_with([CTOR, fn]), contract_name="Bank", import_path="src/Bank.sol"
        )
        assert "new address[](6)" in out
        # The call-site tag is part of the name so two calls in one test
        # cannot declare the same temporary twice.
        assert "uut.send(_call_to_0)" in out

    def test_contract_without_loops_still_compiles_to_a_test(self):
        out = generate_loop_harness(
            model_with([CTOR, STAKE]), contract_name="Bank", import_path="src/Bank.sol"
        )
        assert "function test_noLoops()" in out
