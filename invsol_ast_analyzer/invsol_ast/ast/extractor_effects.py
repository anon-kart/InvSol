# invsol_ast/ast/extractor_effects.py
from __future__ import annotations
from typing import Any, Dict, List, Optional, Set, Tuple
from .extractor_core import find_by_type
from .call_kinds import classify_call
from .loop_roles import analyze_loop_body, classify_loop
from .array_effects import extract_length_effects, extract_storage_aliases

# -------- local rendering (to avoid circular imports) --------

def _render_expr_simple(e: Any) -> str:
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
        L = _render_expr_simple(e.get("leftExpression"))
        R = _render_expr_simple(e.get("rightExpression"))
        return f"({L} {op} {R})"
    if nt == "UnaryOperation":
        op = e.get("operator") or "?"
        sub = _render_expr_simple(e.get("subExpression"))
        if e.get("prefix") is False:
            return f"({sub}{op})"
        return f"({op}{sub})"
    if nt == "Assignment":
        op = e.get("operator") or "="
        L = _render_expr_simple(e.get("leftHandSide"))
        R = _render_expr_simple(e.get("rightHandSide"))
        return f"({L} {op} {R})"
    if nt == "FunctionCall":
        fn = e.get("expression") or {}
        fn_name = fn.get("name") or fn.get("memberName") or _render_expr_simple(fn) or "call"
        args = e.get("arguments") or []
        args_s = ", ".join(_render_expr_simple(a) for a in args)
        return f"{fn_name}({args_s})"
    if nt == "IndexAccess":
        a = _render_expr_simple(e.get("baseExpression"))
        i = _render_expr_simple(e.get("indexExpression"))
        return f"{a}[{i}]"
    if nt == "MemberAccess":
        b = _render_expr_simple(e.get("expression"))
        n = e.get("memberName") or ""
        return f"{b}.{n}"
    if nt == "TupleExpression":
        comps = e.get("components") or []
        return "(" + ", ".join(_render_expr_simple(c) for c in comps) + ")"
    return nt or "expr"

# -------- helpers --------

def _get_type_string(n: Dict[str, Any]) -> str:
    td = (n or {}).get("typeDescriptions") or {}
    return td.get("typeString") or ""

def _is_state_identifier(name: str, state_index: Dict[str, str]) -> bool:
    return name in state_index

def _id_name(n: Dict[str, Any]) -> str:
    if isinstance(n, dict) and n.get("nodeType") == "Identifier":
        return n.get("name") or ""
    return ""

def _lhs_base_identifier(lhs: Dict[str, Any]) -> str:
    """Return base state var name for LHS: x, arr[i], mapping[k]."""
    if not isinstance(lhs, dict):
        return ""
    nt = lhs.get("nodeType")
    if nt == "Identifier":
        return lhs.get("name") or ""
    if nt == "IndexAccess":
        return _lhs_base_identifier(lhs.get("baseExpression"))
    if nt == "MemberAccess":
        return _lhs_base_identifier(lhs.get("expression"))
    return ""

def _base_state_identifier(n: Dict[str, Any]) -> str:
    """Return base Identifier name if n is IndexAccess/MemberAccess/Identifier, else ''. """
    if not isinstance(n, dict):
        return ""
    nt = n.get("nodeType")
    if nt == "Identifier":
        return n.get("name") or ""
    if nt == "IndexAccess":
        return _base_state_identifier(n.get("baseExpression") or {})
    if nt == "MemberAccess":
        return _base_state_identifier(n.get("expression") or {})
    return ""

def _collect_ident_reads(expr: Any, state_index: Dict[str, str], out: Set[str]) -> None:
    """Collect identifiers that read state in an expression subtree."""
    if isinstance(expr, dict):
        if expr.get("nodeType") == "Identifier":
            name = expr.get("name") or ""
            if _is_state_identifier(name, state_index):
                out.add(name)
        for v in expr.values():
            if isinstance(v, (dict, list)):
                _collect_ident_reads(v, state_index, out)
    elif isinstance(expr, list):
        for it in expr:
            if isinstance(it, (dict, list)):
                _collect_ident_reads(it, state_index, out)

def _looks_external_member_call(fc: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Decide whether a call can hand control to another account.

    Member accesses such as arr.length, msg.sender, or a struct field are not
    calls out of the contract and must not be reported as external.
    """
    info = classify_call(fc)
    return bool(info["external"]), info["callee"] or "call"

def _accumulator_name(assign: Dict[str, Any]) -> str:
    """Detect x += y or x = x + y as accumulator."""
    if not isinstance(assign, dict) or assign.get("nodeType") != "Assignment":
        return ""
    op = assign.get("operator") or "="
    lhs = assign.get("leftHandSide") or {}
    rhs = assign.get("rightHandSide") or {}
    if op in {"+=", "-=", "*=", "/="}:
        return _id_name(lhs) or _id_name((lhs.get("baseExpression") or {}))
    if rhs.get("nodeType") == "BinaryOperation":
        left = rhs.get("leftExpression") or {}
        if _id_name(lhs) and _id_name(lhs) == _id_name(left):
            return _id_name(lhs)
    return ""

def _index_var_from_update(update_node: Dict[str, Any]) -> str:
    """Find i in i++ / ++i / i += k / i = i + 1."""
    if not isinstance(update_node, dict):
        return ""
    nt = update_node.get("nodeType")
    if nt == "ExpressionStatement":
        return _index_var_from_update(update_node.get("expression") or {})
    if nt == "UnaryOperation":
        sub = update_node.get("subExpression") or {}
        return _id_name(sub)
    if nt == "Assignment":
        lhs = update_node.get("leftHandSide") or {}
        return _id_name(lhs)
    return ""

def _names_from_var_decl_stmt(vds: Dict[str, Any]) -> List[str]:
    decls = vds.get("declarations") or []
    out = []
    for d in decls:
        n = d.get("name") or ""
        if n:
            out.append(n)
    return out

# -------- public API --------

def build_state_index_from_norm(norm_ast: Dict[str, Any]) -> Dict[str, str]:
    """
    Return {state_var_name: typeString}. Uses VariableDeclaration.stateVariable.
    """
    idx: Dict[str, str] = {}
    for contract in norm_ast.get("contracts", []):
        for vd in find_by_type(contract, "VariableDeclaration"):
            if vd.get("stateVariable"):
                name = vd.get("name") or ""
                if not name:
                    continue
                idx[name] = _get_type_string(vd)
    return idx

def _is_getter_fn(fn: Dict[str, Any], state_index: Dict[str, str]) -> bool:
    name = (fn.get("name") or "").strip()
    if not name or name not in state_index:
        return False
    mut = (fn.get("stateMutability") or "").lower()
    # Treat as getter if view/pure OR there are no state writes in the body.
    has_assignment = any(True for _ in find_by_type(fn, "Assignment"))
    return (mut in ("view", "pure")) or (not has_assignment)


def _is_empty_body(fn: Dict[str, Any]) -> bool:
    """A function is 'empty body' if body is missing or has no statements/nodes (getter heuristic)."""
    body = fn.get("body")
    if not body:
        return True
    if isinstance(body, dict):
        if not body.get("statements") and not body.get("nodes"):
            return True
    return False


# -------- public API --------


def extract_function_effects(norm_ast: Dict[str, Any], state_index: Dict[str, str]) -> Dict[Tuple[str, str], Dict[str, List[str]]]:
    """
    Returns {(contract, function): {
        reads, writes, member_accesses, internal_calls, external_calls, events_emitted,
        storage_reads, storage_writes
    }}
    (each value is a sorted unique list; storage_* are list[dict{var,key} with key possibly null]).
    """
    results: Dict[Tuple[str, str], Dict[str, Set]] = {}

    def ensure(c: str, f: str) -> Dict[str, Set]:
        key = (c, f)
        if key not in results:
            results[key] = {
                "reads": set(),
                "writes": set(),
                "member_accesses": set(),
                "internal_calls": set(),
                "external_calls": set(),
                "events_emitted": set(),
                "storage_reads": set(),   # of tuples (var, key_str_or_None)
                "storage_writes": set(),  # of tuples (var, key_str_or_None, kind)
                "length_effects": [],
                "storage_aliases": [],
            }
        return results[key]

    for contract in norm_ast.get("contracts", []):
        cname = contract.get("name") or ""
        for fn in find_by_type(contract, "FunctionDefinition"):
            fname = fn.get("name") or fn.get("kind") or "function"
            acc = ensure(cname, fname)

            # --- Robust getter detection (mapping/scalar public getters) ---
            # Requires helper: _is_getter_fn(fn, state_index)
            if _is_getter_fn(fn, state_index) and fname in state_index:
                acc["reads"].add(fname)
                ts = state_index[fname]
                if ts.startswith("mapping"):
                    # mapping getter: first parameter name is the key (may be empty string if unnamed)
                    params = (fn.get("parameters") or {}).get("parameters") or []
                    key_name = (params[0].get("name") if params else "") or ""
                    acc["storage_reads"].add((fname, key_name))
                else:
                    # scalar getter: null key
                    acc["storage_reads"].add((fname, None))

            # Assignments: writes + reads
            for a in find_by_type(fn, "Assignment"):
                lhs = a.get("leftHandSide") or {}
                rhs = a.get("rightHandSide")

                # writes set: base identifier (covers Identifier and IndexAccess)
                base_name = _lhs_base_identifier(lhs)
                if base_name and _is_state_identifier(base_name, state_index):
                    acc["writes"].add(base_name)

                # reads from RHS identifiers
                _collect_ident_reads(rhs, state_index, acc["reads"])

                # Storage writes:
                # Case 1: mapping/array write: state[idx] = ...
                if lhs.get("nodeType") == "IndexAccess":
                    base2 = _base_state_identifier(lhs.get("baseExpression") or {})
                    if base2 and _is_state_identifier(base2, state_index):
                        key_expr = _render_expr_simple(lhs.get("indexExpression"))
                        acc["storage_writes"].add((base2, key_expr, "element"))

                # Case 2: scalar state write: state = ..., state += ...
                if lhs.get("nodeType") == "Identifier":
                    vname = lhs.get("name") or ""
                    if vname and _is_state_identifier(vname, state_index):
                        t = state_index.get(vname, "")
                        if not t.startswith("mapping"):
                            # emit scalar write entry with a null key
                            acc["storage_writes"].add((vname, None, "assign"))

            # Length-changing calls: arr.push(x), arr.pop(), delete arr.
            # These are FunctionCall and UnaryOperation nodes rather than
            # Assignment nodes, so the loop above never sees them.
            length_effects = extract_length_effects(fn, state_index)
            acc["length_effects"] = length_effects
            for effect in length_effects:
                acc["writes"].add(effect["var"])
                acc["storage_writes"].add((effect["var"], None, effect["op"]))

            acc["storage_aliases"] = extract_storage_aliases(fn, state_index)

            # Generic reads from expressions (identifiers, binary ops)
            for bo in find_by_type(fn, "BinaryOperation"):
                _collect_ident_reads(bo, state_index, acc["reads"])
            for idn in find_by_type(fn, "Identifier"):
                nm = idn.get("name") or ""
                if _is_state_identifier(nm, state_index):
                    acc["reads"].add(nm)

            # Storage reads from IndexAccess (e.g., balanceOf[msg.sender])
            for ia in find_by_type(fn, "IndexAccess"):
                base = _base_state_identifier(ia.get("baseExpression") or {})
                if base and _is_state_identifier(base, state_index):
                    key_expr = _render_expr_simple(ia.get("indexExpression"))
                    acc["storage_reads"].add((base, key_expr))

            # Member accesses
            for ma in find_by_type(fn, "MemberAccess"):
                mname = ma.get("memberName") or ""
                if mname:
                    acc["member_accesses"].add(mname)

            # Calls: internal vs external (heuristic)
            for fc in find_by_type(fn, "FunctionCall"):
                is_ext, callee = _looks_external_member_call(fc)
                if is_ext:
                    acc["external_calls"].add(callee)
                else:
                    expr = fc.get("expression") or {}
                    if expr.get("nodeType") == "Identifier":
                        acc["internal_calls"].add(expr.get("name") or "call")

            # Emits
            for em in find_by_type(fn, "EmitStatement"):
                evcall = em.get("eventCall") or {}
                evexpr = evcall.get("expression") or {}
                evname = evexpr.get("name") or evexpr.get("memberName") or "event"
                acc["events_emitted"].add(evname)

    # Convert to serializable lists (keep key field, including null)
    final: Dict[Tuple[str, str], Dict[str, List[str]]] = {}
    for k, v in results.items():
        f: Dict[str, Any] = {
            "reads": sorted(v["reads"]),
            "writes": sorted(v["writes"]),
            "member_accesses": sorted(v["member_accesses"]),
            "internal_calls": sorted(v["internal_calls"]),
            "external_calls": sorted(v["external_calls"]),
            "events_emitted": sorted(v["events_emitted"]),
        }
        # sort storage tuples robustly (None-safe) and pack with explicit key (possibly None)
        sr_sorted = sorted(v["storage_reads"], key=lambda x: (x[0], "" if x[1] is None else x[1]))
        sw_sorted = sorted(
            v["storage_writes"],
            key=lambda x: (x[0], "" if x[1] is None else x[1], x[2]),
        )
        f["storage_reads"]  = [{"var": var, "key": key} for (var, key) in sr_sorted]
        f["storage_writes"] = [
            {"var": var, "key": key, "kind": kind} for (var, key, kind) in sw_sorted
        ]
        f["length_effects"] = v["length_effects"]
        f["storage_aliases"] = v["storage_aliases"]
        final[k] = f

    return final

def _unchecked_updates(loop_node: Dict[str, Any]) -> List[str]:
    """Variables assigned inside an unchecked block within this loop."""
    names: List[str] = []
    for block in find_by_type(loop_node, "UncheckedBlock"):
        for assignment in find_by_type(block, "Assignment"):
            lhs = assignment.get("leftHandSide") or {}
            if lhs.get("nodeType") == "Identifier" and lhs.get("name"):
                if lhs["name"] not in names:
                    names.append(lhs["name"])
        for unary in find_by_type(block, "UnaryOperation"):
            if (unary.get("operator") or "") not in {"++", "--"}:
                continue
            sub = unary.get("subExpression") or {}
            if sub.get("nodeType") == "Identifier" and sub.get("name"):
                if sub["name"] not in names:
                    names.append(sub["name"])
    return sorted(names)


def summarize_loop_body(
    loop_node: Dict[str, Any],
    state_index: Dict[str, str],
    *,
    depth: int = 0,
    has_inner_loop: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Describe one loop body for downstream postcondition inference.

    The name lists (indices, accumulators, mapping_updates, array_updates) are
    kept for consumers that expect plain strings. The *_facts entries carry the
    operator, the accumulated expression, and the variable scope, which is what
    relational postconditions are built from.
    """
    roles = analyze_loop_body(loop_node, state_index)

    indices: List[str] = []
    init = loop_node.get("initializationExpression")
    if isinstance(init, dict) and init.get("nodeType") == "VariableDeclarationStatement":
        indices.extend(_names_from_var_decl_stmt(init))
    idx = _index_var_from_update(loop_node.get("loopExpression") or {})
    if idx:
        indices.append(idx)

    classification = classify_loop(
        loop_node,
        state_index,
        depth=depth,
        has_inner_loop=has_inner_loop,
    )

    summary: Dict[str, Any] = {
        "indices": sorted(set(indices)),
        "accumulators": sorted({a["var"] for a in roles["accumulator_facts"] if a["var"]}),
        "mapping_updates": sorted({w["var"] for w in roles["mapping_update_facts"]}),
        "array_updates": sorted({w["var"] for w in roles["array_update_facts"]}),
        "has_external_call_in_loop": roles["has_external_call_in_loop"],
        "accumulator_facts": roles["accumulator_facts"],
        "nested_accumulator_facts": roles["nested_accumulator_facts"],
        "direct_calls": roles["direct_calls"],
        "mapping_update_facts": roles["mapping_update_facts"],
        "array_update_facts": roles["array_update_facts"],
        "writes": roles["writes"],
        "calls": roles["calls"],
        "carried_vars": roles["carried_vars"],
        "declared_vars": roles["declared_vars"],
        "carried_types": roles["carried_types"],
        "external_call_kinds": roles["external_call_kinds"],
        "storage_aliases": extract_storage_aliases(loop_node, state_index),
        "length_effects": extract_length_effects(loop_node, state_index),
        # Solidity 0.8 reverts on overflow, so checked arithmetic can be read as
        # unbounded integers. Inside an unchecked block it wraps modulo 2**256
        # instead, which only a bit-vector encoding represents faithfully.
        "has_unchecked": bool(list(find_by_type(loop_node, "UncheckedBlock"))),
        "unchecked_updates": _unchecked_updates(loop_node),
    }
    summary.update(classification)
    return summary
