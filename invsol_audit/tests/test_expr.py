

from invsol_audit.expr import Binary, Index, Num, Var, symbol_for


def test_a_computed_subscript_is_nameable():
    # buffer[(head + i) % CAPACITY] in a ring buffer. The element is opaque
    # either way, so the subscript becomes part of the name.
    node = Index(
        base=Var("buffer"),
        key=Binary("%", Binary("+", Var("head"), Var("i")), Var("CAPACITY")),
    )
    assert symbol_for(node) == "buffer_at_head_plus_i_mod_CAPACITY"


def test_arithmetic_in_a_subscript_is_stable():
    assert symbol_for(Index(Var("a"), Binary("-", Var("n"), Num(1)))) == "a_at_n_minus_1"
