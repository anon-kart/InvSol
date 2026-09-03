from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from .fuzz_plan import FuzzPlan, plan_for_model, render_bound_statements

DEFAULT_ARRAY_LEN = 6
ACTORS = ["actorA", "actorB", "actorC"]


def _is_array(sol_type: str) -> bool:
    return "[" in (sol_type or "")


def _element_type(sol_type: str) -> str:
    return (sol_type or "").split("[")[0].strip()


def _is_dynamic_array(sol_type: str) -> bool:
    return "[]" in (sol_type or "")


def _mutability(fn: Dict[str, Any]) -> str:
    return (fn.get("mutability") or "").lower()


def _is_read_only(fn: Dict[str, Any]) -> bool:
    return _mutability(fn) in {"view", "pure"}


def _is_payable(fn: Dict[str, Any]) -> bool:
    return _mutability(fn) == "payable"


def _callable(fn: Dict[str, Any], state_names: Set[str]) -> bool:
    if fn.get("synthetic"):
        return False
    if fn.get("name") in state_names:
        return False
    if (fn.get("visibility") or "") not in {"public", "external"}:
        return False
    return fn.get("name") not in {"constructor", "receive", "fallback"}


def _state_names(contract: Dict[str, Any]) -> Set[str]:
    state = contract.get("state") or {}
    names = {v.get("name") for v in (state.get("variables") or []) if v.get("name")}
    names |= {m.get("name") for m in (state.get("mappings") or []) if m.get("name")}
    return names


def loop_state_dependencies(fn: Dict[str, Any]) -> Set[str]:
    """
    State variables a function's loops depend on.

    A loop over a storage array or mapping does nothing on a freshly deployed
    contract, so these names decide which other functions must run first.
    """
    names: Set[str] = set()
    for touch in fn.get("storage_reads") or []:
        if touch.get("var"):
            names.add(touch["var"])

    for loop in fn.get("loops") or []:
        body = loop.get("body_summary") or {}
        for fact in body.get("accumulator_facts") or []:
            source = fact.get("source") or {}
            if source.get("scope") == "state" and source.get("base"):
                names.add(source["base"])
        guard = loop.get("guard") or ""
        for token in guard.replace("(", " ").replace(")", " ").replace(".", " ").split():
            names.add(token)

    return names


def find_producers(
    target: Dict[str, Any],
    functions: List[Dict[str, Any]],
    state_names: Set[str],
) -> List[Dict[str, Any]]:
    """
    Functions that write the state the target's loops read.

    Ordering these before the target is what turns an empty loop into one that
    actually iterates.
    """
    wanted = loop_state_dependencies(target) & state_names
    if not wanted:
        return []

    producers: List[Dict[str, Any]] = []
    for fn in functions:
        if fn.get("name") == target.get("name"):
            continue
        if not _callable(fn, state_names) or _is_read_only(fn):
            continue
        written = {t.get("var") for t in (fn.get("storage_writes") or []) if t.get("var")}
        written |= set(fn.get("writes") or [])
        if written & wanted:
            producers.append(fn)

    producers.sort(key=lambda f: (len(f.get("params") or []), f.get("name") or ""))
    return producers[:2]


def _literal_for(sol_type: str, index: int) -> str:
    t = (sol_type or "").strip()
    if t.startswith("uint") or t.startswith("int"):
        return str(10 * (index + 1))
    if t == "address":
        return ACTORS[index % len(ACTORS)]
    if t == "bool":
        return "true"
    if t.startswith("bytes32"):
        return f'keccak256(abi.encodePacked(uint256({index + 1})))'
    if t.startswith("bytes"):
        return 'hex"1234"'
    if t == "string":
        return '"invsol"'
    return f"{t}(0)"


def _array_setup(
    name: str, sol_type: str, index: int, indent: str, tag: str
) -> Tuple[List[str], str]:
    """
    Build a small in-memory array for a call argument.

    The length is fixed rather than fuzzed so the number of loop iterations in
    the contract under test stays predictable. The tag identifies the call site,
    because one test may seed state and then call the function under test, and
    both may take an array parameter of the same name at the same position.
    """
    element = _element_type(sol_type)
    var = f"_{tag}_{name}_{index}"
    lines = [f"{element}[] memory {var} = new {element}[]({DEFAULT_ARRAY_LEN});"]
    lines.append(f"for (uint256 k = 0; k < {DEFAULT_ARRAY_LEN}; k++) {{")
    if element == "address":
        lines.append(f"    {var}[k] = address(uint160(0x1000 + k));")
    elif element.startswith("uint") or element.startswith("int"):
        lines.append(f"    {var}[k] = {element}((k + 1) * 7);")
    elif element.startswith("bytes32"):
        lines.append(f"    {var}[k] = keccak256(abi.encodePacked(k));")
    else:
        lines.append(f"    {var}[k] = {_literal_for(element, 0)};")
    lines.append("}")
    return [f"{indent}{line}" for line in lines], var


def _call_arguments(
    fn: Dict[str, Any],
    plan: Optional[FuzzPlan],
    indent: str,
    tag: str,
) -> Tuple[List[str], List[str]]:
    setup: List[str] = []
    args: List[str] = []
    bounded = {b.name for b in (plan.bounds if plan else [])}

    for i, param in enumerate(fn.get("params") or []):
        name = param.get("name") or f"arg{i}"
        sol_type = param.get("type") or "uint256"

        if _is_array(sol_type):
            if _is_dynamic_array(sol_type):
                lines, var = _array_setup(name, sol_type, i, indent, tag)
                setup.extend(lines)
                args.append(var)
            else:
                args.append(f"{sol_type}(0)")
            continue

        if name in bounded:
            args.append(name)
            continue

        if sol_type == "address":
            args.append(ACTORS[i % len(ACTORS)])
        else:
            args.append(_literal_for(sol_type, i))

    return setup, args


def _signature_params(fn: Dict[str, Any], plan: Optional[FuzzPlan]) -> List[str]:
    bounded = {b.name: b for b in (plan.bounds if plan else [])}
    out: List[str] = []
    for param in fn.get("params") or []:
        name = param.get("name") or ""
        if name in bounded:
            out.append(f"{bounded[name].sol_type} {name}")
    return out


def _seed_block(
    producers: List[Dict[str, Any]],
    plans: Dict[str, FuzzPlan],
    indent: str,
) -> List[str]:
    lines: List[str] = []
    for position, producer in enumerate(producers):
        plan = plans.get(producer.get("name") or "")
        setup, args = _call_arguments(producer, None, indent, f"seed{position}")
        lines.extend(setup)

        caller = plan.caller_expr if plan and plan.caller_expr else None
        value = "{value: 1 ether}" if _is_payable(producer) else ""
        call = f"uut.{producer['name']}{value}({', '.join(args)})"

        if caller:
            lines.append(f"{indent}vm.startPrank(uut.{caller});")
            lines.append(f"{indent}try {call} {{}} catch {{}}")
            lines.append(f"{indent}vm.stopPrank();")
            continue

        if _writes_sender_keyed_state(producer):
            for actor in ACTORS:
                lines.append(f"{indent}vm.prank({actor});")
                lines.append(f"{indent}try {call} {{}} catch {{}}")
        else:
            lines.append(f"{indent}try {call} {{}} catch {{}}")
    return lines


def _writes_sender_keyed_state(fn: Dict[str, Any]) -> bool:
    """
    Whether the function records something against the caller.

    Such a function has to be invoked by several accounts, otherwise a loop
    over the recorded set only ever sees one entry.
    """
    for touch in fn.get("storage_writes") or []:
        key = (touch.get("key") or "")
        if "msg.sender" in key or "sender" in key.lower():
            return True
    for clause in fn.get("requires") or []:
        if "msg.sender" in clause:
            return True
    return any("msg.sender" in (m or "") for m in (fn.get("member_accesses") or []))


def _constructor_args(functions: List[Dict[str, Any]]) -> str:
    for fn in functions:
        if fn.get("name") == "constructor":
            args = []
            for i, param in enumerate(fn.get("params") or []):
                sol_type = param.get("type") or "uint256"
                if _is_dynamic_array(sol_type):
                    args.append(f"new {_element_type(sol_type)}[](0)")
                else:
                    args.append(_literal_for(sol_type, i))
            return ", ".join(args)
    return ""


def generate_loop_harness(model: Dict[str, Any], *, contract_name: str, import_path: str) -> str:
    """
    Emit a test contract that drives every loop-bearing function.

    Each test bounds its numeric arguments using the fuzz plan, impersonates the
    role the function requires, seeds any state the loops read, and calls the
    function inside try/catch so a revert records a trace without failing the
    run.
    """
    contract = model.get("contract") or model
    functions = list(contract.get("functions") or [])
    state_names = _state_names(contract)
    plans = {p.function: p for p in plan_for_model(model)}

    pragma = str(model.get("pragma") or "").strip()
    pragma_line = f"pragma solidity {pragma};" if pragma else "pragma solidity >=0.8.0 <0.9.0;"

    L: List[str] = []
    L.append("// SPDX-License-Identifier: MIT")
    L.append(pragma_line)
    L.append("")
    L.append('import "forge-std/Test.sol";')
    L.append(f'import {{{contract_name}}} from "{import_path}";')
    L.append("")
    L.append(f"contract {contract_name}_LoopHarness is Test {{")
    L.append(f"    {contract_name} internal uut;")
    for i, actor in enumerate(ACTORS):
        L.append(f"    address internal {actor} = address(uint160(0xA110 + {i}));")
    L.append("")
    L.append("    function setUp() public {")
    L.append(f"        uut = new {contract_name}({_constructor_args(functions)});")
    L.append("        vm.deal(address(this), 100 ether);")
    for actor in ACTORS:
        L.append(f"        vm.deal({actor}, 10 ether);")
    L.append("    }")

    emitted = 0
    for fn in functions:
        name = fn.get("name") or ""
        if not _callable(fn, state_names):
            continue
        if not (fn.get("loops") or []):
            continue

        plan = plans.get(name)
        producers = find_producers(fn, functions, state_names)
        sig = _signature_params(fn, plan)
        indent = "        "

        L.append("")
        L.append(f"    function testFuzz_{name}({', '.join(sig)}) public {{")

        for statement in render_bound_statements(plan) if plan else []:
            L.append(f"{indent}{statement}")

        L.extend(_seed_block(producers, plans, indent))

        setup, args = _call_arguments(fn, plan, indent, "call")
        L.extend(setup)

        caller = plan.caller_expr if plan and plan.caller_expr else None
        if caller:
            L.append(f"{indent}vm.startPrank(uut.{caller});")

        value = ""
        if _is_payable(fn):
            value = "{value: 1 ether}"

        L.append(f"{indent}try uut.{name}{value}({', '.join(args)}) {{}} catch {{}}")

        if caller:
            L.append(f"{indent}vm.stopPrank();")

        L.append("    }")
        emitted += 1

    if emitted == 0:
        L.append("")
        L.append("    function test_noLoops() public view {")
        L.append("        assertTrue(address(uut) != address(0));")
        L.append("    }")

    L.append("}")
    L.append("")
    return "\n".join(L)
