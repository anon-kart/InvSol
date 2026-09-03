from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from .extractor_core import find_by_type

LENGTH_MEMBERS = {"push", "pop"}
LOOP_NODES = ("ForStatement", "WhileStatement", "DoWhileStatement")
BRANCH_NODES = ("IfStatement",)


def _src_span(node: Any) -> Optional[Tuple[int, int]]:
    if not isinstance(node, dict):
        return None
    src = node.get("src")
    if not isinstance(src, str):
        return None
    parts = src.split(":")
    if len(parts) < 2:
        return None
    try:
        start = int(parts[0])
        length = int(parts[1])
    except ValueError:
        return None
    return start, start + length


def _contains(outer: Tuple[int, int], inner: Tuple[int, int]) -> bool:
    return outer[0] <= inner[0] and inner[1] <= outer[1]


def _identifier_name(node: Any) -> str:
    if isinstance(node, dict) and node.get("nodeType") == "Identifier":
        return node.get("name") or ""
    return ""


def _base_identifier(node: Any) -> str:
    if not isinstance(node, dict):
        return ""
    nt = node.get("nodeType")
    if nt == "Identifier":
        return node.get("name") or ""
    if nt == "IndexAccess":
        return _base_identifier(node.get("baseExpression"))
    if nt == "MemberAccess":
        return _base_identifier(node.get("expression"))
    return ""


def _render(node: Any) -> str:
    if not isinstance(node, dict):
        return ""
    nt = node.get("nodeType")
    if nt == "Identifier":
        return node.get("name") or ""
    if nt == "Literal":
        value = node.get("value")
        if value is None:
            value = node.get("hexValue") or node.get("number")
        return str(value) if value is not None else ""
    if nt == "MemberAccess":
        base = _render(node.get("expression"))
        member = node.get("memberName") or ""
        return f"{base}.{member}" if base else member
    if nt == "IndexAccess":
        return f"{_render(node.get('baseExpression'))}[{_render(node.get('indexExpression'))}]"
    if nt == "BinaryOperation":
        left = _render(node.get("leftExpression"))
        right = _render(node.get("rightExpression"))
        return f"({left} {node.get('operator') or '?'} {right})"
    if nt == "TupleExpression":
        return _render((node.get("components") or [None])[0])
    return ""


def _guard_upper_bound(loop: Dict[str, Any]) -> str:
    """
    The expression a counted loop runs up to.

    Only the simple comparison forms are read here. Anything else leaves the
    bound empty, which callers treat as an unknown iteration count rather than
    guessing a number.
    """
    condition = loop.get("condition")
    if not isinstance(condition, dict):
        return ""
    if condition.get("nodeType") != "BinaryOperation":
        return ""
    operator = condition.get("operator") or ""
    if operator not in {"<", "<=", ">", ">=", "!="}:
        return ""
    if operator in {"<", "<=", "!="}:
        return _render(condition.get("rightExpression"))
    return _render(condition.get("leftExpression"))


def _param_types(fn: Dict[str, Any]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    params = (fn.get("parameters") or {}).get("parameters") or []
    for param in params:
        name = param.get("name") or ""
        if not name:
            continue
        type_string = ((param.get("typeDescriptions") or {}).get("typeString")) or ""
        out[name] = type_string
    return out


def _element_source(argument: Any, params: Dict[str, str]) -> Dict[str, Any]:
    """
    Describe what a push puts into the array.

    Seeding needs this to control the shape of nested arrays: pushing a
    parameter of type uint256[] means the caller chooses the inner length,
    whereas pushing an array literal fixes it.
    """
    if not isinstance(argument, dict):
        return {"kind": "unknown", "name": "", "type": "", "length": None}

    name = _identifier_name(argument)
    if name and name in params:
        return {
            "kind": "param",
            "name": name,
            "type": params[name],
            "length": None,
        }

    nt = argument.get("nodeType")
    if nt in {"TupleExpression", "ArrayLiteral"}:
        components = argument.get("components") or []
        return {
            "kind": "literal",
            "name": "",
            "type": ((argument.get("typeDescriptions") or {}).get("typeString")) or "",
            "length": len(components) or None,
        }

    return {
        "kind": "expression",
        "name": _render(argument),
        "type": ((argument.get("typeDescriptions") or {}).get("typeString")) or "",
        "length": None,
    }


def extract_length_effects(
    fn: Dict[str, Any],
    state_index: Dict[str, str],
) -> List[Dict[str, Any]]:
    """
    How one call to this function changes the length of each state array.

    A push outside any loop grows the array by one. A push inside a counted
    loop grows it by the loop's upper bound, which is often a parameter and so
    lets a caller ask for a specific length. Both forms are recorded, together
    with whether a branch can skip the write.
    """
    effects: List[Dict[str, Any]] = []
    params = _param_types(fn)

    loops: List[Tuple[Tuple[int, int], Dict[str, Any]]] = []
    for node_type in LOOP_NODES:
        for loop in find_by_type(fn, node_type):
            span = _src_span(loop)
            if span:
                loops.append((span, loop))

    branches: List[Tuple[int, int]] = []
    for node_type in BRANCH_NODES:
        for branch in find_by_type(fn, node_type):
            span = _src_span(branch)
            if span:
                branches.append(span)

    for call in find_by_type(fn, "FunctionCall"):
        expression = call.get("expression") or {}
        if expression.get("nodeType") != "MemberAccess":
            continue
        member = expression.get("memberName") or ""
        if member not in LENGTH_MEMBERS:
            continue

        base = _base_identifier(expression.get("expression"))
        if not base or base not in state_index:
            continue

        span = _src_span(call)
        enclosing = [(s, loop) for s, loop in loops if span and _contains(s, span)]
        enclosing.sort(key=lambda item: item[0][1] - item[0][0])

        in_loop = bool(enclosing)
        bound = _guard_upper_bound(enclosing[0][1]) if enclosing else ""
        conditional = bool(span) and any(_contains(b, span) for b in branches)

        arguments = call.get("arguments") or []
        source = _element_source(arguments[0], params) if arguments else {
            "kind": "none",
            "name": "",
            "type": "",
            "length": None,
        }

        effects.append(
            {
                "var": base,
                "op": member,
                "count": bound if in_loop and bound else "1",
                "in_loop": in_loop,
                "loop_bound": bound,
                "conditional": conditional,
                "element_source": source,
            }
        )

    for unary in find_by_type(fn, "UnaryOperation"):
        if (unary.get("operator") or "") != "delete":
            continue
        target = _identifier_name(unary.get("subExpression"))
        if target and target in state_index:
            effects.append(
                {
                    "var": target,
                    "op": "clear",
                    "count": "0",
                    "in_loop": False,
                    "loop_bound": "",
                    "conditional": False,
                    "element_source": {"kind": "none", "name": "", "type": "", "length": None},
                }
            )

    effects.sort(key=lambda e: (e["var"], e["op"], e["count"]))
    return effects


def extract_storage_aliases(
    fn: Dict[str, Any],
    state_index: Dict[str, str],
) -> List[Dict[str, Any]]:
    """
    Local storage pointers and the state variable they refer to.

    A loop guarded by row.length, where row was declared as
    uint256[] storage row = grid[r], is really bounded by the length of a row
    of grid. Recording the alias is what lets a counterexample about row be
    traced back to a function that can change grid.
    """
    aliases: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    for statement in find_by_type(fn, "VariableDeclarationStatement"):
        declarations = statement.get("declarations") or []
        value = statement.get("initialValue")
        if not declarations or not isinstance(value, dict):
            continue

        declaration = declarations[0]
        if not isinstance(declaration, dict):
            continue
        if (declaration.get("storageLocation") or "") != "storage":
            continue

        name = declaration.get("name") or ""
        base = _base_identifier(value)
        if not name or not base or base not in state_index:
            continue
        if name in seen:
            continue
        seen.add(name)

        via = "direct"
        index = None
        if value.get("nodeType") == "IndexAccess":
            via = "index"
            index = _render(value.get("indexExpression")) or None
        elif value.get("nodeType") == "MemberAccess":
            via = "member"
            index = value.get("memberName") or None

        aliases.append(
            {
                "name": name,
                "base": base,
                "via": via,
                "index": index,
                "type": ((declaration.get("typeDescriptions") or {}).get("typeString")) or "",
            }
        )

    aliases.sort(key=lambda a: a["name"])
    return aliases
