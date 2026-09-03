import pytest

from invsol_ast.ast.call_kinds import classify_call
from invsol_ast.ast.loop_roles import (
    analyze_loop_body,
    annotate_loop_nesting,
    classify_loop,
    source_offset,
)


def ident(name, typ="uint256"):
    return {"nodeType": "Identifier", "name": name, "typeDescriptions": {"typeString": typ}}


def lit(value):
    return {"nodeType": "Literal", "value": str(value), "typeDescriptions": {"typeString": "int_const"}}


def member(base, name, base_type, out_type="uint256"):
    return {
        "nodeType": "MemberAccess",
        "expression": {**base, "typeDescriptions": {"typeString": base_type}},
        "memberName": name,
        "typeDescriptions": {"typeString": out_type},
    }


def index(base, idx, base_type, elem_type="uint256"):
    return {
        "nodeType": "IndexAccess",
        "baseExpression": {**base, "typeDescriptions": {"typeString": base_type}},
        "indexExpression": idx,
        "typeDescriptions": {"typeString": elem_type},
    }


def stmt(expression):
    return {"nodeType": "ExpressionStatement", "expression": expression}


def assign(lhs, op, rhs):
    return {"nodeType": "Assignment", "operator": op, "leftHandSide": lhs, "rightHandSide": rhs}


def incr(name):
    return {"nodeType": "UnaryOperation", "operator": "++", "prefix": False, "subExpression": ident(name)}


def for_loop(node_id, index_name, bound, body_statements, update=None):
    return {
        "nodeType": "ForStatement",
        "id": node_id,
        "initializationExpression": {
            "nodeType": "VariableDeclarationStatement",
            "declarations": [{"name": index_name, "typeDescriptions": {"typeString": "uint256"}}],
            "initialValue": lit(0),
        },
        "condition": {
            "nodeType": "BinaryOperation",
            "operator": "<",
            "leftExpression": ident(index_name),
            "rightExpression": bound,
        },
        "loopExpression": stmt(update or incr(index_name)),
        "body": {"nodeType": "Block", "statements": body_statements},
    }


STATE = {
    "payees": "address[]",
    "shares": "mapping(address => uint256)",
    "totalSupply": "uint256",
}


class TestCallClassification:
    @pytest.mark.parametrize(
        "base_type,name,expected_external",
        [
            ("uint256[]", "length", False),
            ("address[] storage ref", "push", False),
            ("address payable", "transfer", True),
            ("address", "send", True),
            ("address", "call", True),
            ("address", "delegatecall", True),
            ("address", "staticcall", False),
            ("contract IERC20", "transferFrom", True),
        ],
    )
    def test_member_calls(self, base_type, name, expected_external):
        call = {
            "nodeType": "FunctionCall",
            "expression": member(ident("x", base_type), name, base_type),
            "arguments": [],
        }
        assert classify_call(call)["external"] is expected_external

    def test_context_globals_are_not_calls(self):
        call = {
            "nodeType": "FunctionCall",
            "expression": member(ident("msg", "msg"), "sender", "msg"),
            "arguments": [],
        }
        assert classify_call(call)["kind"] == "builtin"

    def test_plain_identifier_call_is_internal(self):
        call = {"nodeType": "FunctionCall", "expression": ident("_helper", "function"), "arguments": []}
        assert classify_call(call)["external"] is False

    def test_type_conversion_receiver_resolves_to_argument(self):
        conversion = {
            "nodeType": "FunctionCall",
            "kind": "typeConversion",
            "expression": ident("payable", "type"),
            "arguments": [ident("recipient", "address")],
            "typeDescriptions": {"typeString": "address payable"},
        }
        call = {
            "nodeType": "FunctionCall",
            "expression": member(conversion, "transfer", "address payable"),
            "arguments": [],
        }
        info = classify_call(call)
        assert info["kind"] == "transfer"
        assert info["receiver"] == "recipient"


class TestAccumulators:
    def test_compound_add_records_operator_and_source(self):
        loop = for_loop(
            1,
            "i",
            ident("n"),
            [stmt(assign(ident("total"), "+=", index(ident("arr", "uint256[] memory"), ident("i"), "uint256[] memory")))],
        )
        facts = analyze_loop_body(loop, STATE)["accumulator_facts"]
        assert len(facts) == 1
        fact = facts[0]
        assert fact["var"] == "total"
        assert fact["op"] == "+="
        assert fact["kind"] == "sum"
        assert fact["source"]["expr"] == "arr[i]"
        assert fact["source"]["container"] == "array"

    def test_expanded_form_is_recognised(self):
        rhs = {
            "nodeType": "BinaryOperation",
            "operator": "+",
            "leftExpression": ident("total"),
            "rightExpression": index(ident("arr", "uint256[] memory"), ident("i"), "uint256[] memory"),
        }
        loop = for_loop(2, "i", ident("n"), [stmt(assign(ident("total"), "=", rhs))])
        facts = analyze_loop_body(loop, STATE)["accumulator_facts"]
        assert facts[0]["op"] == "+="
        assert facts[0]["kind"] == "sum"

    def test_increment_is_a_counter(self):
        loop = for_loop(3, "i", ident("n"), [stmt(incr("count"))])
        facts = analyze_loop_body(loop, STATE)["accumulator_facts"]
        assert facts[0]["kind"] == "count"
        assert facts[0]["source"]["expr"] == "1"

    def test_multiplication_is_a_product(self):
        loop = for_loop(4, "i", ident("n"), [stmt(assign(ident("acc"), "*=", ident("factor")))])
        assert analyze_loop_body(loop, STATE)["accumulator_facts"][0]["kind"] == "product"

    def test_mapping_source_is_tagged_as_state(self):
        source = index(ident("shares", "mapping(address => uint256)"), ident("k"), "mapping(address => uint256)")
        loop = for_loop(5, "i", ident("n"), [stmt(assign(ident("sumShares"), "+=", source))])
        fact = analyze_loop_body(loop, STATE)["accumulator_facts"][0]
        assert fact["source"]["scope"] == "state"
        assert fact["source"]["container"] == "mapping"


class TestClassification:
    def test_parameter_bound_is_simple(self):
        loop = for_loop(6, "i", ident("n"), [])
        assert classify_loop(loop, STATE)["category"] == "simple"

    def test_state_bound_is_dynamic(self):
        bound = member(ident("payees", "address[] storage ref"), "length", "address[] storage ref")
        loop = for_loop(7, "i", bound, [])
        result = classify_loop(loop, STATE)
        assert result["category"] == "dynamic"
        assert "state:payees" in result["guard_runtime_dependencies"]

    def test_block_context_bound_is_dynamic(self):
        bound = member(ident("block", "block"), "timestamp", "block")
        loop = for_loop(8, "i", bound, [])
        assert classify_loop(loop, STATE)["category"] == "dynamic"

    def test_containing_loop_is_nested(self):
        inner = for_loop(11, "j", ident("m"), [])
        outer = for_loop(10, "i", ident("n"), [inner])
        assert classify_loop(outer, STATE)["category"] == "nested"

    def test_nesting_depths_are_recorded(self):
        inner = for_loop(21, "j", ident("m"), [])
        outer = for_loop(20, "i", ident("n"), [inner])
        nesting = annotate_loop_nesting({"nodeType": "ContractDefinition", "nodes": [outer]})
        assert nesting[20]["depth"] == 0
        assert nesting[20]["has_inner_loop"] is True
        assert nesting[21]["depth"] == 1
        assert nesting[21]["parent_id"] == 20

    def test_inner_loop_is_nested_by_depth(self):
        inner = for_loop(31, "j", ident("m"), [])
        outer = for_loop(30, "i", ident("n"), [inner])
        nesting = annotate_loop_nesting({"nodeType": "ContractDefinition", "nodes": [outer]})
        info = nesting[31]
        result = classify_loop(inner, STATE, depth=info["depth"], has_inner_loop=info["has_inner_loop"])
        assert result["category"] == "nested"

    @pytest.mark.parametrize(
        "update,expected",
        [
            ({"nodeType": "UnaryOperation", "operator": "++", "prefix": False, "subExpression": ident("i")}, "increasing"),
            ({"nodeType": "UnaryOperation", "operator": "--", "prefix": False, "subExpression": ident("i")}, "decreasing"),
            (assign(ident("i"), "+=", lit(2)), "increasing"),
            (assign(ident("i"), "-=", lit(1)), "decreasing"),
        ],
    )
    def test_index_direction(self, update, expected):
        loop = for_loop(40, "i", ident("n"), [], update=update)
        assert classify_loop(loop, STATE)["index_direction"] == expected


class TestLoopEffects:
    def test_transfer_in_body_marks_external(self):
        call = {
            "nodeType": "FunctionCall",
            "expression": member(ident("to", "address payable"), "transfer", "address payable"),
            "arguments": [ident("amount")],
        }
        loop = for_loop(50, "i", ident("n"), [stmt(call)])
        roles = analyze_loop_body(loop, STATE)
        assert roles["has_external_call_in_loop"] is True
        assert roles["external_call_kinds"] == ["transfer"]

    def test_length_read_does_not_mark_external(self):
        call = {
            "nodeType": "FunctionCall",
            "expression": member(ident("arr", "uint256[]"), "length", "uint256[]"),
            "arguments": [],
        }
        loop = for_loop(51, "i", ident("n"), [stmt(call)])
        assert analyze_loop_body(loop, STATE)["has_external_call_in_loop"] is False

    def test_carried_variables_are_collected(self):
        loop = for_loop(
            52,
            "i",
            ident("n"),
            [
                stmt(assign(ident("total"), "+=", ident("x"))),
                stmt(assign(ident("seen"), "=", lit(1))),
            ],
        )
        assert analyze_loop_body(loop, STATE)["carried_vars"] == ["seen", "total"]


class TestNestingIsolation:
    @staticmethod
    def _nested_pair():
        inner = for_loop(50, "j", ident("m"), [stmt(assign(ident("total"), "+=", ident("j")))])
        inner["src"] = "40:20:0"
        outer = for_loop(
            100,
            "i",
            ident("n"),
            [stmt(assign(ident("outerAcc"), "+=", lit(5))), inner],
        )
        outer["src"] = "10:200:0"
        return outer, inner

    def test_outer_loop_does_not_absorb_inner_updates(self):
        outer, _ = self._nested_pair()
        roles = analyze_loop_body(outer, STATE)
        assert [a["var"] for a in roles["accumulator_facts"]] == ["outerAcc"]

    def test_inner_updates_are_reported_as_inherited(self):
        outer, _ = self._nested_pair()
        roles = analyze_loop_body(outer, STATE)
        assert {a["var"] for a in roles["nested_accumulator_facts"]} == {"total", "j"}

    def test_inner_loop_reports_its_own_update(self):
        _, inner = self._nested_pair()
        roles = analyze_loop_body(inner, STATE)
        assert [a["var"] for a in roles["accumulator_facts"]] == ["total"]

    def test_source_order_puts_the_outer_loop_first(self):
        outer, inner = self._nested_pair()
        assert sorted([inner, outer], key=source_offset)[0] is outer


class TestWhileAndContainers:
    def test_while_direction_comes_from_body_counter(self):
        loop = {
            "nodeType": "WhileStatement",
            "id": 7,
            "src": "0:10:0",
            "condition": {
                "nodeType": "BinaryOperation",
                "operator": "<",
                "leftExpression": ident("i"),
                "rightExpression": ident("n"),
            },
            "body": {
                "nodeType": "Block",
                "statements": [
                    stmt(assign(ident("s"), "+=", ident("x"))),
                    stmt(assign(ident("i"), "+=", lit(1))),
                ],
            },
        }
        assert classify_loop(loop, STATE)["index_direction"] == "increasing"

    def test_while_direction_from_postfix_increment(self):
        loop = {
            "nodeType": "WhileStatement",
            "id": 9,
            "src": "0:10:0",
            "condition": {
                "nodeType": "BinaryOperation",
                "operator": "<",
                "leftExpression": ident("i"),
                "rightExpression": ident("n"),
            },
            "body": {"nodeType": "Block", "statements": [stmt(incr("i"))]},
        }
        assert classify_loop(loop, STATE)["index_direction"] == "increasing"

    def test_while_direction_from_prefix_decrement(self):
        loop = {
            "nodeType": "WhileStatement",
            "id": 10,
            "src": "0:10:0",
            "condition": {
                "nodeType": "BinaryOperation",
                "operator": ">",
                "leftExpression": ident("i"),
                "rightExpression": lit(0),
            },
            "body": {
                "nodeType": "Block",
                "statements": [
                    stmt({
                        "nodeType": "UnaryOperation",
                        "operator": "--",
                        "prefix": True,
                        "subExpression": ident("i"),
                    })
                ],
            },
        }
        assert classify_loop(loop, STATE)["index_direction"] == "decreasing"

    def test_braceless_body_does_not_break_analysis(self):
        loop = {
            "nodeType": "ForStatement",
            "id": 11,
            "src": "0:10:0",
            "initializationExpression": {
                "nodeType": "VariableDeclarationStatement",
                "declarations": [{"name": "i", "typeDescriptions": {"typeString": "uint256"}}],
                "initialValue": lit(0),
            },
            "condition": {
                "nodeType": "BinaryOperation",
                "operator": "<",
                "leftExpression": ident("i"),
                "rightExpression": ident("n"),
            },
            "loopExpression": stmt(incr("i")),
            "body": stmt(assign(ident("total"), "+=", ident("x"))),
        }
        roles = analyze_loop_body(loop, STATE)
        assert [a["var"] for a in roles["accumulator_facts"]] == ["total"]

    def test_array_push_is_recorded(self):
        call = {
            "nodeType": "FunctionCall",
            "expression": {
                "nodeType": "MemberAccess",
                "memberName": "push",
                "expression": ident("numbers", "uint256[] storage ref"),
                "typeDescriptions": {"typeString": "function()"},
            },
            "arguments": [ident("v")],
        }
        loop = for_loop(8, "i", ident("n"), [stmt(call)])
        roles = analyze_loop_body(loop, {"numbers": "uint256[]"})
        assert [(w["var"], w["op"]) for w in roles["array_update_facts"]] == [("numbers", "push")]
