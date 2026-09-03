from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from .extractor_core import find_by_type
from .call_kinds import classify_call

LOOP_NODE_TYPES = ("ForStatement", "WhileStatement", "DoWhileStatement")

CONTEXT_ROOTS = {"msg", "block", "tx"}

_COMPOUND_OPS = {"+=", "-=", "*=", "/=", "%=", "|=", "&=", "^=", "<<=", ">>="}

_OP_KIND = {
    "+=": "sum",
    "-=": "difference",
    "*=": "product",
    "/=": "quotient",
    "%=": "modulo",
    "|=": "bitwise_or",
    "&=": "bitwise_and",
    "^=": "bitwise_xor",
    "<<=": "shift_left",
    ">>=": "shift_right",
}


def _render(e: Any) -> str:
    if not isinstance(e, dict):
        return ""
    nt = e.get("nodeType")
    if nt == "Identifier":
        return e.get("name") or ""
    if nt == "Literal":
        val = e.get("value")
        if val is None:
            val = e.get("hexValue") or e.get("number")
        return str(val)
    if nt == "BinaryOperation":
        op = e.get("operator") or "?"
        return f"({_render(e.get('leftExpression'))} {op} {_render(e.get('rightExpression'))})"
    if nt == "UnaryOperation":
        op = e.get("operator") or "?"
        sub = _render(e.get("subExpression"))
        return f"({sub}{op})" if e.get("prefix") is False else f"({op}{sub})"
    if nt == "Assignment":
        op = e.get("operator") or "="
        return f"({_render(e.get('leftHandSide'))} {op} {_render(e.get('rightHandSide'))})"
    if nt == "FunctionCall":
        fn = e.get("expression") or {}
        name = fn.get("name") or fn.get("memberName") or _render(fn) or "call"
        args = ", ".join(_render(a) for a in (e.get("arguments") or []))
        return f"{name}({args})"
    if nt == "IndexAccess":
        return f"{_render(e.get('baseExpression'))}[{_render(e.get('indexExpression'))}]"
    if nt == "MemberAccess":
        return f"{_render(e.get('expression'))}.{e.get('memberName') or ''}"
    if nt == "TupleExpression":
        return "(" + ", ".join(_render(c) for c in (e.get("components") or [])) + ")"
    if nt == "Conditional":
        return (
            f"({_render(e.get('condition'))} ? {_render(e.get('trueExpression'))}"
            f" : {_render(e.get('falseExpression'))})"
        )
    return nt or "expr"


def _type_string(node: Optional[Dict[str, Any]]) -> str:
    return ((node or {}).get("typeDescriptions") or {}).get("typeString") or ""


def _root_identifier(node: Optional[Dict[str, Any]]) -> str:
    if not isinstance(node, dict):
        return ""
    nt = node.get("nodeType")
    if nt == "Identifier":
        return node.get("name") or ""
    if nt == "IndexAccess":
        return _root_identifier(node.get("baseExpression"))
    if nt == "MemberAccess":
        return _root_identifier(node.get("expression"))
    return ""


def _id_name(node: Optional[Dict[str, Any]]) -> str:
    if isinstance(node, dict) and node.get("nodeType") == "Identifier":
        return node.get("name") or ""
    return ""


def _is_literal_one(node: Optional[Dict[str, Any]]) -> bool:
    if not isinstance(node, dict) or node.get("nodeType") != "Literal":
        return False
    val = node.get("value") or node.get("number") or node.get("hexValue")
    return str(val).strip() in {"1", "0x1", "0x01"}


def _scope_of(name: str, state_index: Dict[str, str]) -> str:
    return "state" if name in state_index else "local"


def _describe_target(lhs: Dict[str, Any], state_index: Dict[str, str]) -> Dict[str, Any]:
    base = _root_identifier(lhs)
    nt = (lhs or {}).get("nodeType")
    record = {
        "var": base,
        "expr": _render(lhs),
        "scope": _scope_of(base, state_index),
        "type": _type_string(lhs),
        "container": "scalar",
        "key": None,
    }
    if nt == "IndexAccess":
        base_type = _type_string(lhs.get("baseExpression"))
        record["container"] = "mapping" if base_type.startswith("mapping") else "array"
        record["key"] = _render(lhs.get("indexExpression"))
    elif nt == "MemberAccess":
        record["container"] = "member"
        record["key"] = lhs.get("memberName")
    return record


def _describe_source(rhs: Dict[str, Any], state_index: Dict[str, str]) -> Dict[str, Any]:
    base = _root_identifier(rhs)
    nt = (rhs or {}).get("nodeType")
    record = {
        "expr": _render(rhs),
        "base": base,
        "scope": _scope_of(base, state_index) if base else "literal",
        "indexed": nt == "IndexAccess",
        "index": None,
        "container": None,
    }
    if nt == "IndexAccess":
        base_type = _type_string(rhs.get("baseExpression"))
        record["container"] = "mapping" if base_type.startswith("mapping") else "array"
        record["index"] = _render(rhs.get("indexExpression"))
    return record


def _accumulator_from_assignment(
    assign: Dict[str, Any], state_index: Dict[str, str]
) -> Optional[Dict[str, Any]]:
    if not isinstance(assign, dict) or assign.get("nodeType") != "Assignment":
        return None

    op = assign.get("operator") or "="
    lhs = assign.get("leftHandSide") or {}
    rhs = assign.get("rightHandSide") or {}

    if op in _COMPOUND_OPS:
        kind = _OP_KIND.get(op, "accumulate")
        if op == "+=" and _is_literal_one(rhs):
            kind = "count"
        target = _describe_target(lhs, state_index)
        return {
            **target,
            "op": op,
            "kind": kind,
            "source": _describe_source(rhs, state_index),
        }

    if op == "=" and rhs.get("nodeType") == "BinaryOperation":
        lhs_text = _render(lhs)
        left = rhs.get("leftExpression") or {}
        right = rhs.get("rightExpression") or {}
        operator = rhs.get("operator") or ""
        if operator not in {"+", "-", "*", "/", "%", "|", "&", "^"}:
            return None
        if _render(left) == lhs_text:
            other = right
        elif _render(right) == lhs_text and operator in {"+", "*", "|", "&", "^"}:
            other = left
        else:
            return None
        kind = _OP_KIND.get(operator + "=", "accumulate")
        if operator == "+" and _is_literal_one(other):
            kind = "count"
        target = _describe_target(lhs, state_index)
        return {
            **target,
            "op": operator + "=",
            "kind": kind,
            "source": _describe_source(other, state_index),
        }

    return None


def _accumulator_from_unary(
    unary: Dict[str, Any], state_index: Dict[str, str]
) -> Optional[Dict[str, Any]]:
    if not isinstance(unary, dict) or unary.get("nodeType") != "UnaryOperation":
        return None
    op = unary.get("operator")
    if op not in {"++", "--"}:
        return None
    sub = unary.get("subExpression") or {}
    target = _describe_target(sub, state_index)
    if not target["var"]:
        return None
    return {
        **target,
        "op": "+=" if op == "++" else "-=",
        "kind": "count",
        "source": {
            "expr": "1",
            "base": "",
            "scope": "literal",
            "indexed": False,
            "index": None,
            "container": None,
        },
    }


def _direct_body_nodes(loop_node: Dict[str, Any]) -> Dict[str, Any]:
    return loop_node.get("body") or {}


def _inner_loops(loop_node: Dict[str, Any]) -> List[Dict[str, Any]]:
    body = _direct_body_nodes(loop_node)
    found: List[Dict[str, Any]] = []
    for nt in LOOP_NODE_TYPES:
        found.extend(find_by_type(body, nt))
    return found


def _update_direction(loop_node: Dict[str, Any]) -> str:
    update = loop_node.get("loopExpression") or {}
    if update.get("nodeType") == "ExpressionStatement":
        update = update.get("expression") or {}
    nt = update.get("nodeType")
    if nt == "UnaryOperation":
        op = update.get("operator")
        if op == "++":
            return "increasing"
        if op == "--":
            return "decreasing"
    if nt == "Assignment":
        op = update.get("operator") or ""
        if op == "+=":
            return "increasing"
        if op == "-=":
            return "decreasing"
        if op == "=":
            rhs = update.get("rightHandSide") or {}
            if rhs.get("nodeType") == "BinaryOperation":
                if rhs.get("operator") == "+":
                    return "increasing"
                if rhs.get("operator") == "-":
                    return "decreasing"
    return ""


def _guard_depends_on_runtime(
    condition: Any, state_index: Dict[str, str]
) -> Tuple[bool, List[str]]:
    reasons: List[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, list):
            for item in node:
                walk(item)
            return
        if not isinstance(node, dict):
            return
        nt = node.get("nodeType")
        if nt == "Identifier":
            name = node.get("name") or ""
            if name in state_index:
                reasons.append(f"state:{name}")
        elif nt == "MemberAccess":
            root = _root_identifier(node)
            if root in CONTEXT_ROOTS:
                reasons.append(f"context:{root}.{node.get('memberName')}")
            elif root in state_index:
                reasons.append(f"state:{root}")
        elif nt == "IndexAccess":
            root = _root_identifier(node)
            if root in state_index:
                reasons.append(f"state:{root}")
        elif nt == "FunctionCall":
            info = classify_call(node)
            if info.get("external"):
                reasons.append(f"external_call:{info.get('callee')}")
            elif info.get("kind") == "internal" and info.get("callee"):
                reasons.append(f"call:{info.get('callee')}")
        for value in node.values():
            if isinstance(value, (dict, list)):
                walk(value)

    walk(condition)
    ordered = sorted(set(reasons))
    return (len(ordered) > 0), ordered


def classify_loop(
    loop_node: Dict[str, Any],
    state_index: Dict[str, str],
    *,
    depth: int = 0,
    has_inner_loop: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Assign the loop to one of the categories used in the evaluation:
    simple, nested, or dynamic.

    A loop is nested when it contains another loop or is contained in one.
    Otherwise it is dynamic when its guard reads contract state, transaction
    context, or the result of a call, and simple when the bound is fixed at
    entry.
    """
    inner = _inner_loops(loop_node) if has_inner_loop is None else []
    nested = bool(inner) if has_inner_loop is None else bool(has_inner_loop)
    nested = nested or depth > 0

    runtime, reasons = _guard_depends_on_runtime(loop_node.get("condition"), state_index)

    if nested:
        category = "nested"
    elif runtime:
        category = "dynamic"
    else:
        category = "simple"

    direction = _update_direction(loop_node) or _direction_from_body(
        loop_node, state_index
    )

    return {
        "category": category,
        "depth": depth,
        "has_inner_loop": bool(inner) if has_inner_loop is None else bool(has_inner_loop),
        "guard_runtime_dependencies": reasons,
        "index_direction": direction or "unknown",
    }


def analyze_loop_body(loop_node: Dict[str, Any], state_index: Dict[str, str]) -> Dict[str, Any]:
    """
    Describe what the loop body does to the variables it touches.

    Facts are split into those produced by statements directly in this loop and
    those inherited from loops nested inside it, because an inductive invariant
    for one loop must not be built from another loop's updates.
    """
    body = _direct_body_nodes(loop_node)

    def collect(scope: Any, direct: bool) -> Dict[str, Any]:
        finder = _find_direct if direct else find_by_type

        accumulators: List[Dict[str, Any]] = []
        seen: Set[Tuple[str, str, str]] = set()

        for assign in finder(scope, "Assignment"):
            fact = _accumulator_from_assignment(assign, state_index)
            if not fact:
                continue
            key = (fact["expr"], fact["op"], fact["source"]["expr"])
            if key in seen:
                continue
            seen.add(key)
            accumulators.append(fact)

        for unary in finder(scope, "UnaryOperation"):
            fact = _accumulator_from_unary(unary, state_index)
            if not fact:
                continue
            key = (fact["expr"], fact["op"], fact["source"]["expr"])
            if key in seen:
                continue
            seen.add(key)
            accumulators.append(fact)

        writes: List[Dict[str, Any]] = []
        write_keys: Set[str] = set()
        for assign in finder(scope, "Assignment"):
            target = _describe_target(assign.get("leftHandSide") or {}, state_index)
            if not target["var"] or target["expr"] in write_keys:
                continue
            write_keys.add(target["expr"])
            writes.append({**target, "op": assign.get("operator") or "="})

        calls: List[Dict[str, Any]] = []
        call_keys: Set[str] = set()
        for fc in finder(scope, "FunctionCall"):
            info = classify_call(fc)
            if info["kind"] in {"cast", "builtin"}:
                continue
            key = f"{info['kind']}:{info['receiver']}.{info['callee']}"
            if key in call_keys:
                continue
            call_keys.add(key)
            calls.append(info)

        return {"accumulators": accumulators, "writes": writes, "calls": calls}

    direct = collect(body, True)
    everything = collect(body, False)

    direct_keys = {(a["expr"], a["op"], a["source"]["expr"]) for a in direct["accumulators"]}
    inherited = [
        a
        for a in everything["accumulators"]
        if (a["expr"], a["op"], a["source"]["expr"]) not in direct_keys
    ]

    declared: List[str] = []
    for vds in _find_direct(body, "VariableDeclarationStatement"):
        for d in vds.get("declarations") or []:
            if isinstance(d, dict) and d.get("name"):
                declared.append(d["name"])

    # Only scalar accumulators can be named on their own. An accumulator like
    # rewardOf[stakers[i]] += x records var "rewardOf" with the value type
    # uint256, but rewardOf is the whole mapping, so logging it under that type
    # produces a cast the compiler rejects.
    typed: Dict[str, str] = {}
    for a in direct["accumulators"]:
        if a["var"] and a.get("type") and a.get("container") == "scalar":
            typed.setdefault(a["var"], a["type"])
    for w in direct["writes"]:
        if w["var"] and w.get("type") and w["container"] == "scalar":
            typed.setdefault(w["var"], w["type"])

    push_facts = _container_push_facts(body, state_index)
    writes = direct["writes"] + push_facts

    mapping_updates = [w for w in writes if w["container"] == "mapping"]
    array_updates = [w for w in writes if w["container"] == "array"]

    carried = sorted(
        {
            a["var"]
            for a in direct["accumulators"]
            if a["var"] and a.get("container") == "scalar"
        }
        | {
            w["var"]
            for w in direct["writes"]
            if w["scope"] == "local" and w.get("container") == "scalar"
        }
    )

    all_calls = everything["calls"]

    return {
        "accumulator_facts": direct["accumulators"],
        "nested_accumulator_facts": inherited,
        "writes": writes,
        "mapping_update_facts": mapping_updates,
        "array_update_facts": array_updates,
        "calls": all_calls,
        "direct_calls": direct["calls"],
        "carried_vars": carried,
        "declared_vars": sorted(set(declared)),
        "carried_types": typed,
        "has_external_call_in_loop": any(c["external"] for c in all_calls),
        "external_call_kinds": sorted({c["kind"] for c in all_calls if c["external"]}),
    }


def annotate_loop_nesting(contract: Dict[str, Any]) -> Dict[int, Dict[str, Any]]:
    """
    Walk every loop in the contract and record its nesting depth and parent.

    Returns a map from AST node id to {"depth": int, "parent_id": Optional[int],
    "has_inner_loop": bool}.
    """
    info: Dict[int, Dict[str, Any]] = {}

    def walk(node: Any, depth: int, parent_id: Optional[int]) -> None:
        if isinstance(node, list):
            for item in node:
                walk(item, depth, parent_id)
            return
        if not isinstance(node, dict):
            return

        if node.get("nodeType") in LOOP_NODE_TYPES:
            node_id = node.get("id")
            inner = _inner_loops(node)
            if node_id is not None:
                info[node_id] = {
                    "depth": depth,
                    "parent_id": parent_id,
                    "has_inner_loop": bool(inner),
                }
            for value in node.values():
                if isinstance(value, (dict, list)):
                    walk(value, depth + 1, node_id)
            return

        for value in node.values():
            if isinstance(value, (dict, list)):
                walk(value, depth, parent_id)

    walk(contract, 0, None)
    return info


def source_offset(node: Dict[str, Any]) -> int:
    """
    Byte offset of the node in the source file.

    solc numbers AST nodes bottom-up, so an inner loop can carry a lower id than
    the loop enclosing it. Ordering by source position keeps loop0 the first
    loop a reader sees.
    """
    src = (node or {}).get("src") or ""
    head = str(src).split(":")[0]
    try:
        return int(head)
    except ValueError:
        return 0


def _find_direct(root: Any, node_type: str) -> List[Dict[str, Any]]:
    """
    Collect nodes of a type without descending into nested loops, so an outer
    loop does not absorb the statements of the loops it contains.
    """
    out: List[Dict[str, Any]] = []

    def walk(node: Any, is_root: bool) -> None:
        if isinstance(node, list):
            for item in node:
                walk(item, False)
            return
        if not isinstance(node, dict):
            return
        if not is_root and node.get("nodeType") in LOOP_NODE_TYPES:
            return
        if node.get("nodeType") == node_type:
            out.append(node)
        for value in node.values():
            if isinstance(value, (dict, list)):
                walk(value, False)

    walk(root, True)
    return out


def _container_push_facts(
    body: Dict[str, Any], state_index: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    Record array growth performed through push and pop, which are calls rather
    than assignments and would otherwise be missed.
    """
    facts: List[Dict[str, Any]] = []
    for fc in _find_direct(body, "FunctionCall"):
        expr = fc.get("expression") or {}
        if expr.get("nodeType") != "MemberAccess":
            continue
        member_name = expr.get("memberName") or ""
        if member_name not in {"push", "pop"}:
            continue
        base = _root_identifier(expr.get("expression"))
        if not base:
            continue
        args = fc.get("arguments") or []
        facts.append(
            {
                "var": base,
                "expr": f"{base}.{member_name}()",
                "scope": _scope_of(base, state_index),
                "type": _type_string(expr.get("expression")),
                "container": "array",
                "key": None,
                "op": member_name,
                "source": _describe_source(args[0], state_index) if args else None,
            }
        )
    return facts


def _direction_from_body(
    loop_node: Dict[str, Any], state_index: Dict[str, str]
) -> str:
    """
    A while loop has no update clause, so the direction is taken from a counter
    updated inside the body.
    """
    body = _direct_body_nodes(loop_node)
    guard_names = set()

    def collect(node: Any) -> None:
        if isinstance(node, list):
            for item in node:
                collect(item)
        elif isinstance(node, dict):
            if node.get("nodeType") == "Identifier":
                guard_names.add(node.get("name") or "")
            for value in node.values():
                if isinstance(value, (dict, list)):
                    collect(value)

    collect(loop_node.get("condition"))

    for assign in _find_direct(body, "Assignment"):
        fact = _accumulator_from_assignment(assign, state_index)
        if fact and fact["var"] in guard_names:
            if fact["op"] in {"+=", "*="}:
                return "increasing"
            if fact["op"] == "-=":
                return "decreasing"

    for unary in _find_direct(body, "UnaryOperation"):
        if unary.get("operator") in {"++", "--"} and _id_name(
            unary.get("subExpression") or {}
        ) in guard_names:
            return "increasing" if unary.get("operator") == "++" else "decreasing"

    return "unknown"
