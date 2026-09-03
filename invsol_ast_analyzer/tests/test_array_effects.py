from invsol_ast.ast.array_effects import extract_length_effects, extract_storage_aliases

STATE_INDEX = {
    "numbers": "uint256[]",
    "grid": "uint256[][]",
    "depositorKeys": "address[]",
    "deposits": "mapping(address => uint256)",
}


def identifier(name, src, type_string=""):
    return {
        "nodeType": "Identifier",
        "name": name,
        "src": src,
        "typeDescriptions": {"typeString": type_string},
    }


def push_call(target, argument, src):
    return {
        "nodeType": "FunctionCall",
        "src": src,
        "expression": {
            "nodeType": "MemberAccess",
            "memberName": "push",
            "src": src,
            "expression": identifier(target, src),
        },
        "arguments": [argument],
    }


def function(name, params, body_statements, src="0:1000:0"):
    return {
        "nodeType": "FunctionDefinition",
        "name": name,
        "src": src,
        "parameters": {
            "parameters": [
                {
                    "name": pname,
                    "typeDescriptions": {"typeString": ptype},
                }
                for pname, ptype in params
            ]
        },
        "body": {"nodeType": "Block", "src": src, "statements": body_statements},
    }


def test_unconditional_push_grows_by_one():
    fn = function(
        "pushRow",
        [("row", "uint256[] calldata"), ("maxCols", "uint256")],
        [push_call("grid", identifier("row", "100:3:0", "uint256[] calldata"), "100:20:0")],
    )

    effects = extract_length_effects(fn, STATE_INDEX)

    assert len(effects) == 1
    effect = effects[0]
    assert effect["var"] == "grid"
    assert effect["op"] == "push"
    assert effect["count"] == "1"
    assert effect["in_loop"] is False
    assert effect["conditional"] is False
    assert effect["element_source"]["kind"] == "param"
    assert effect["element_source"]["name"] == "row"


def test_push_inside_counted_loop_takes_the_loop_bound():
    loop = {
        "nodeType": "ForStatement",
        "src": "100:200:0",
        "condition": {
            "nodeType": "BinaryOperation",
            "operator": "<",
            "src": "110:5:0",
            "leftExpression": identifier("i", "110:1:0"),
            "rightExpression": identifier("n", "114:1:0"),
        },
        "body": {
            "nodeType": "Block",
            "src": "120:80:0",
            "statements": [
                push_call(
                    "numbers",
                    {
                        "nodeType": "BinaryOperation",
                        "operator": "+",
                        "src": "150:7:0",
                        "leftExpression": identifier("base", "150:4:0"),
                        "rightExpression": identifier("i", "157:1:0"),
                    },
                    "130:40:0",
                )
            ],
        },
    }
    fn = function("appendMany", [("n", "uint256"), ("base", "uint256")], [loop])

    effects = extract_length_effects(fn, STATE_INDEX)

    assert len(effects) == 1
    assert effects[0]["var"] == "numbers"
    assert effects[0]["in_loop"] is True
    assert effects[0]["loop_bound"] == "n"
    assert effects[0]["count"] == "n"


def test_push_behind_a_branch_is_marked_conditional():
    branch = {
        "nodeType": "IfStatement",
        "src": "100:100:0",
        "condition": identifier("flag", "105:4:0"),
        "trueBody": {
            "nodeType": "Block",
            "src": "115:70:0",
            "statements": [
                push_call(
                    "depositorKeys",
                    {
                        "nodeType": "MemberAccess",
                        "memberName": "sender",
                        "src": "130:10:0",
                        "expression": identifier("msg", "130:3:0"),
                    },
                    "125:30:0",
                )
            ],
        },
    }
    fn = function("deposit", [], [branch])

    effects = extract_length_effects(fn, STATE_INDEX)

    assert len(effects) == 1
    assert effects[0]["var"] == "depositorKeys"
    assert effects[0]["conditional"] is True
    assert effects[0]["count"] == "1"


def test_pop_and_delete_are_recorded():
    pop = {
        "nodeType": "FunctionCall",
        "src": "100:12:0",
        "expression": {
            "nodeType": "MemberAccess",
            "memberName": "pop",
            "src": "100:12:0",
            "expression": identifier("numbers", "100:7:0"),
        },
        "arguments": [],
    }
    clear = {
        "nodeType": "UnaryOperation",
        "operator": "delete",
        "src": "200:12:0",
        "subExpression": identifier("grid", "207:4:0"),
    }
    fn = function("reset", [], [pop, clear])

    effects = extract_length_effects(fn, STATE_INDEX)
    operations = {(e["var"], e["op"]) for e in effects}

    assert ("numbers", "pop") in operations
    assert ("grid", "clear") in operations


def test_pushes_to_locals_are_ignored():
    fn = function(
        "buildLocal",
        [],
        [push_call("scratch", identifier("x", "100:1:0"), "100:20:0")],
    )

    assert extract_length_effects(fn, STATE_INDEX) == []


def test_storage_pointer_resolves_to_its_state_variable():
    declaration = {
        "nodeType": "VariableDeclarationStatement",
        "src": "100:40:0",
        "declarations": [
            {
                "nodeType": "VariableDeclaration",
                "name": "row",
                "storageLocation": "storage",
                "typeDescriptions": {"typeString": "uint256[] storage pointer"},
            }
        ],
        "initialValue": {
            "nodeType": "IndexAccess",
            "src": "130:7:0",
            "baseExpression": identifier("grid", "130:4:0"),
            "indexExpression": identifier("r", "135:1:0"),
        },
    }
    fn = function("scaledAddToGrid", [("scale", "uint256")], [declaration])

    aliases = extract_storage_aliases(fn, STATE_INDEX)

    assert len(aliases) == 1
    assert aliases[0]["name"] == "row"
    assert aliases[0]["base"] == "grid"
    assert aliases[0]["via"] == "index"
    assert aliases[0]["index"] == "r"


def test_memory_copies_are_not_aliases():
    declaration = {
        "nodeType": "VariableDeclarationStatement",
        "src": "100:40:0",
        "declarations": [
            {
                "nodeType": "VariableDeclaration",
                "name": "copy",
                "storageLocation": "memory",
                "typeDescriptions": {"typeString": "uint256[] memory"},
            }
        ],
        "initialValue": identifier("numbers", "130:7:0"),
    }
    fn = function("copyOut", [], [declaration])

    assert extract_storage_aliases(fn, STATE_INDEX) == []
