from invsol_audit.encode import build_conditions, build_loop_model

ALIASED = {
    "loop_id": "C.scaledAddToGrid#loop1",
    "bounds": {"index": "c", "lower": "0", "upper": "row.length"},
    "body_summary": {
        "indices": ["c"],
        "storage_aliases": [
            {"name": "row", "base": "grid", "via": "index", "index": "r"}
        ],
        "accumulator_facts": [
            {"var": "touched", "op": "+=", "container": "scalar", "source": {"expr": "1"}}
        ],
    },
}


def without_aliases():
    loop = {k: v for k, v in ALIASED.items()}
    body = dict(loop["body_summary"])
    body["storage_aliases"] = []
    loop["body_summary"] = body
    return loop


def declarations(loop, invariant):
    model = build_loop_model(loop)
    condition = build_conditions(model, invariant)[0]
    return [l for l in condition.smt.splitlines() if l.startswith("(declare")]


class TestStorageAliasing:
    def test_a_pointer_resolves_to_the_location_it_refers_into(self):
        model = build_loop_model(ALIASED)
        assert "row" in model.aliases

    def test_an_aliased_length_uses_the_base_location(self):
        decls = declarations(ALIASED, "touched <= row.length")
        assert any("grid_at_r_length" in d for d in decls)
        assert not any("row_length" in d for d in decls)

    def test_a_write_through_either_name_reaches_one_symbol(self):
        # touched <= row.length and touched <= grid[r].length must not become
        # two independent symbols, or interference between them is invisible.
        through_alias = declarations(ALIASED, "touched <= row.length")
        through_base = declarations(ALIASED, "touched <= grid[r].length")
        assert through_alias == through_base

    def test_an_element_of_an_aliased_row_resolves_too(self):
        # The initiation check substitutes the index with its lower bound, so
        # the subscript here is 0 rather than c.
        decls = declarations(ALIASED, "touched <= row[c]")
        assert any("grid_at_r_at_" in d for d in decls)
        assert not any(d.startswith("(declare-const row") for d in decls)

    def test_without_an_alias_the_pointer_stays_opaque(self):
        decls = declarations(without_aliases(), "touched <= row.length")
        assert any("row_length" in d for d in decls)

    def test_an_unparsable_alias_is_left_alone(self):
        loop = {k: v for k, v in ALIASED.items()}
        body = dict(loop["body_summary"])
        body["storage_aliases"] = [{"name": "row", "base": "grid", "via": "index", "index": "??"}]
        loop["body_summary"] = body
        # No false identity is introduced when the alias cannot be read.
        assert "row" not in build_loop_model(loop).aliases
