from invsol_audit.encode import build_conditions, build_loop_model


def loop(unchecked):
    return {
        "loop_id": "C.f#loop0",
        "bounds": {"index": "i", "lower": "0", "upper": "n"},
        "body_summary": {
            "indices": ["i"],
            "has_unchecked": unchecked,
            "accumulator_facts": [
                {
                    "var": "s",
                    "op": "+=",
                    "container": "scalar",
                    "source": {"expr": "1"},
                }
            ],
        },
    }


def smt(unchecked, invariant="s >= 0"):
    model = build_loop_model(loop(unchecked))
    return model, build_conditions(model, invariant)[0]


class TestCheckedArithmetic:
    def test_integers_with_a_range_constraint_are_used(self):
        _, condition = smt(False)
        assert "(set-logic QF_LIA)" in condition.smt
        assert "(declare-const s Int)" in condition.smt
        assert "(<= s 115792089237316195423570985008687907853269984665640564039457584007913129639935)" in condition.smt

    def test_the_assumption_names_the_language_rule(self):
        # Solidity 0.8 reverts on overflow, so this is a property of the
        # language rather than something assumed away.
        _, condition = smt(False)
        assert any("reverts on overflow" in a for a in condition.assumptions)


class TestUncheckedArithmetic:
    def test_a_loop_with_an_unchecked_block_wraps(self):
        model, _ = smt(True)
        assert model.wraps is True

    def test_bit_vectors_are_used(self):
        _, condition = smt(True)
        assert "(set-logic QF_BV)" in condition.smt
        assert "(declare-const s (_ BitVec 256))" in condition.smt

    def test_no_range_constraint_is_needed(self):
        # A 256-bit vector is already confined to the uint256 range.
        _, condition = smt(True)
        assert "115792089237316195423570985008687907853269984665640564039457584007913129639935" not in condition.smt

    def test_literals_are_bit_vector_literals(self):
        _, condition = smt(True, "s >= 0")
        assert "(_ bv0 256)" in condition.smt

    def test_comparisons_are_unsigned(self):
        _, condition = smt(True, "s >= 0")
        assert "bvuge" in condition.smt or "bvult" in condition.smt

    def test_the_assumption_names_the_wraparound(self):
        _, condition = smt(True)
        assert any("wraps modulo" in a for a in condition.assumptions)
