from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

DEFAULT_TRIP_CAP = 16
DEFAULT_ARRAY_LEN = 8
DEFAULT_UINT_CAP = 1_000_000

IDENT_RE = re.compile(r"[A-Za-z_]\w*")
NUM_RE = re.compile(r"\b(\d+)\b")

COMPARE_RE = re.compile(
    r"(?P<left>[A-Za-z_]\w*)\s*(?P<op><=|<|>=|>|==)\s*(?P<right>[A-Za-z_]\w*|\d+)"
)

ROLE_HINTS = ("owner", "admin", "arbiter", "seller", "manager", "operator", "minter")


@dataclass
class ParamBound:
    name: str
    sol_type: str
    low: str = "0"
    high: str = str(DEFAULT_UINT_CAP)
    reason: str = "default"
    drives_loop: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.sol_type,
            "low": self.low,
            "high": self.high,
            "reason": self.reason,
            "drives_loop": self.drives_loop,
        }


@dataclass
class FuzzPlan:
    function: str
    caller_role: Optional[str] = None
    caller_expr: Optional[str] = None
    bounds: List[ParamBound] = field(default_factory=list)
    array_params: List[Tuple[str, str]] = field(default_factory=list)
    loop_ids: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "function": self.function,
            "caller_role": self.caller_role,
            "caller_expr": self.caller_expr,
            "bounds": [b.to_dict() for b in self.bounds],
            "array_params": [{"name": n, "type": t} for n, t in self.array_params],
            "loop_ids": self.loop_ids,
            "notes": self.notes,
        }


def _is_numeric(sol_type: str) -> bool:
    t = (sol_type or "").strip()
    return t.startswith("uint") or t.startswith("int")


def _is_array(sol_type: str) -> bool:
    return "[" in (sol_type or "")


def identifiers(text: str) -> Set[str]:
    return set(IDENT_RE.findall(text or ""))


def loop_step_params(fn: Dict[str, Any]) -> Set[str]:
    """
    Parameters used as the amount added to a loop-carried accumulator.

    A while loop whose progress depends on such a parameter never terminates if
    the value is zero, so these must be drawn from one upward rather than zero.
    """
    names = {p.get("name") for p in fn.get("params") or [] if p.get("name")}
    steps: Set[str] = set()

    for loop in fn.get("loops") or []:
        guard_names = identifiers(loop.get("guard") or "")

        body = loop.get("body_summary") or {}
        facts = list(body.get("accumulator_facts") or [])
        facts += list(body.get("nested_accumulator_facts") or [])
        for fact in facts:
            if fact.get("var") not in guard_names:
                continue
            source = (fact.get("source") or {}).get("expr") or ""
            steps |= identifiers(source) & names

        steps |= identifiers(loop.get("update") or "") & names

    return steps


def loop_driving_params(fn: Dict[str, Any]) -> Set[str]:
    """
    Parameters that appear in a loop guard, so their magnitude decides how many
    times the loop runs. These need a small cap or the fuzzer will pick values
    that exhaust gas before the body is ever observed.
    """
    names = {p.get("name") for p in fn.get("params") or [] if p.get("name")}
    driving: Set[str] = set()
    for loop in fn.get("loops") or []:
        guard = loop.get("guard") or ""
        bounds = loop.get("bounds") or {}
        text = f"{guard} {bounds.get('upper', '')} {bounds.get('lower', '')}"
        driving |= identifiers(text) & names
    return driving


def bounds_from_requires(fn: Dict[str, Any]) -> Dict[str, Tuple[str, str]]:
    """
    Read simple comparisons out of require clauses.

    require(n <= maxN) gives n an upper bound of maxN, and require(n < 100)
    gives an upper bound of 99. Anything more complex is left alone.
    """
    names = {p.get("name") for p in fn.get("params") or [] if p.get("name")}
    found: Dict[str, Tuple[str, str]] = {}

    for clause in fn.get("requires") or []:
        for m in COMPARE_RE.finditer(clause or ""):
            left, op, right = m.group("left"), m.group("op"), m.group("right")
            if left not in names:
                continue
            if op == "<=":
                found[left] = ("0", right)
            elif op == "<":
                if right.isdigit():
                    found[left] = ("0", str(max(0, int(right) - 1)))
                else:
                    found[left] = ("0", f"{right} == 0 ? 0 : {right} - 1")
            elif op == "==":
                found[left] = (right, right)
    return found


def _resolvable(expr: str, param_names: Set[str]) -> bool:
    """Whether every name in an expression is visible from the test."""
    return all(ident in param_names for ident in identifiers(expr))


def address_getters(contract: Dict[str, Any]) -> Set[str]:
    """
    Names callable as uut.<name>() and yielding an address.

    A modifier called onlyOperator suggests the role name "operator", but the
    contract may only have a mapping called operators, whose getter takes an
    argument. Pranking as uut.operator() then does not compile, so a role is
    only used when a matching getter really exists.
    """
    out: Set[str] = set()
    for fn in contract.get("functions") or []:
        name = fn.get("name") or ""
        if not name or fn.get("params"):
            continue
        if (fn.get("visibility") or "") not in {"public", "external"}:
            continue
        returns = fn.get("returns") or []
        if len(returns) == 1 and str(returns[0].get("type") or "") == "address":
            out.add(name)
    return out


def caller_for(
    fn: Dict[str, Any],
    access_edges: List[Dict[str, Any]],
    access_deps: List[Dict[str, Any]],
    getters: Optional[Set[str]] = None,
) -> Tuple[Optional[str], List[str]]:
    """
    Work out which account must send the transaction.

    Returns the name of the state variable holding the privileged address, so
    the harness can prank as whatever that variable currently holds rather than
    assuming a fixed OWNER constant.
    """
    notes: List[str] = []
    name = fn.get("name")

    def usable(role: str) -> bool:
        if getters is None:
            return True
        if role in getters:
            return True
        notes.append(f"role {role} has no zero-argument address getter, not pranking")
        return False

    for dep in access_deps or []:
        if dep.get("function") != name:
            continue
        condition = dep.get("condition") or ""
        if "msg.sender" not in condition:
            continue
        for ident in identifiers(condition):
            if ident in {"msg", "sender", "require"}:
                continue
            if ident.lower() in ROLE_HINTS or dep.get("role") == ident:
                if not usable(ident):
                    continue
                notes.append(f"caller from {dep.get('source') or 'require'}: {condition}")
                return ident, notes

    for edge in access_edges or []:
        if edge.get("function") != name:
            continue
        role = edge.get("role")
        if role and role not in {"unknown", ""}:
            if usable(role):
                notes.append(f"caller from modifier {edge.get('modifier')}")
                return role, notes
        modifier = (edge.get("modifier") or "").lower()
        for hint in ROLE_HINTS:
            if hint in modifier:
                if usable(hint):
                    notes.append(
                        f"caller inferred from modifier name {edge.get('modifier')}"
                    )
                    return hint, notes

    for clause in fn.get("requires") or []:
        if "msg.sender" not in clause:
            continue
        for ident in identifiers(clause):
            if ident.lower() in ROLE_HINTS:
                if not usable(ident):
                    continue
                notes.append(f"caller from require: {clause}")
                return ident, notes

    return None, notes


def plan_for_function(
    fn: Dict[str, Any],
    access_edges: List[Dict[str, Any]],
    access_deps: List[Dict[str, Any]],
    *,
    trip_cap: int = DEFAULT_TRIP_CAP,
    getters: Optional[Set[str]] = None,
) -> FuzzPlan:
    plan = FuzzPlan(function=fn.get("name") or "")

    role, notes = caller_for(fn, access_edges, access_deps, getters)
    plan.notes.extend(notes)
    if role:
        plan.caller_role = role
        plan.caller_expr = f"{role}()"

    driving = loop_driving_params(fn)
    steps = loop_step_params(fn)
    from_requires = bounds_from_requires(fn)
    param_names = {
        p.get("name") for p in (fn.get("params") or []) if p.get("name")
    }

    plan.loop_ids = [lp.get("loop_id") for lp in (fn.get("loops") or []) if lp.get("loop_id")]

    for param in fn.get("params") or []:
        pname = param.get("name") or ""
        ptype = param.get("type") or ""
        if not pname:
            continue

        if _is_array(ptype):
            plan.array_params.append((pname, ptype))
            continue

        if not _is_numeric(ptype):
            continue

        bound = ParamBound(name=pname, sol_type=ptype)
        bound.drives_loop = pname in driving

        if pname in from_requires:
            low, high = from_requires[pname]
            # A bound taken from a require may name contract state, as in
            # require(r < grid.length). The harness runs outside the contract
            # and cannot see grid, so anything that is not a parameter or a
            # literal is dropped rather than emitted.
            if _resolvable(low, param_names) and _resolvable(high, param_names):
                bound.low, bound.high, bound.reason = low, high, "require"
            else:
                plan.notes.append(
                    f"{pname}: bound from require names contract state, using the cap instead"
                )

        if bound.drives_loop:
            if bound.reason == "require" and bound.high.isdigit():
                bound.high = str(min(int(bound.high), trip_cap))
                bound.reason = "require+trip-cap"
            elif bound.reason == "require":
                other = bound.high
                bound.high = f"{other} < {trip_cap} ? {other} : {trip_cap}"
                bound.reason = "require+trip-cap"
            else:
                bound.low, bound.high = "0", str(trip_cap)
                bound.reason = "trip-cap"

        if bound.reason == "default":
            bound.high = str(DEFAULT_UINT_CAP)

        if pname in steps:
            bound.low = "1"
            bound.reason = f"{bound.reason}+nonzero-step"
            plan.notes.append(
                f"{pname} advances a loop accumulator, so zero would not terminate"
            )

        plan.bounds.append(bound)

    plan.bounds = _order_by_dependency(plan.bounds)
    return plan


def _order_by_dependency(bounds: List[ParamBound]) -> List[ParamBound]:
    """
    A bound may refer to another parameter, as in require(n <= maxN). The
    referenced parameter has to be narrowed first or the reference reads a
    value that is still unconstrained.
    """
    names = {b.name for b in bounds}
    ordered: List[ParamBound] = []
    placed: Set[str] = set()

    remaining = list(bounds)
    for _ in range(len(remaining) + 1):
        progressed = False
        for b in list(remaining):
            deps = (identifiers(b.low) | identifiers(b.high)) & names - {b.name}
            if deps <= placed:
                ordered.append(b)
                placed.add(b.name)
                remaining.remove(b)
                progressed = True
        if not remaining or not progressed:
            break

    ordered.extend(remaining)
    return ordered


def plan_for_model(model: Dict[str, Any], *, trip_cap: int = DEFAULT_TRIP_CAP) -> List[FuzzPlan]:
    contract = model.get("contract") or model
    edges = contract.get("access_control") or []
    deps = contract.get("access_dependencies") or []

    getters = address_getters(contract)

    state = contract.get("state") or {}
    generated = {v.get("name") for v in (state.get("variables") or []) if v.get("name")}
    generated |= {m.get("name") for m in (state.get("mappings") or []) if m.get("name")}

    plans: List[FuzzPlan] = []
    for fn in contract.get("functions") or []:
        if fn.get("synthetic"):
            continue
        if fn.get("name") in generated:
            continue
        if (fn.get("visibility") or "") not in {"public", "external"}:
            continue
        if fn.get("name") == "constructor":
            continue
        plans.append(
            plan_for_function(fn, edges, deps, trip_cap=trip_cap, getters=getters)
        )
    return plans


def render_bound_statements(plan: FuzzPlan) -> List[str]:
    """
    Emit forge-std bound() calls. bound is preferred over vm.assume because it
    maps every draw into range instead of discarding it, so no fuzz budget is
    wasted on rejected inputs.
    """
    lines: List[str] = []
    for b in plan.bounds:
        cast = "uint256" if b.sol_type.startswith("uint") else "int256"
        lines.append(f"{b.name} = {b.sol_type}(bound({cast}({b.name}), {b.low}, {b.high}));")
    return lines


def render_prank(plan: FuzzPlan, uut: str) -> Tuple[List[str], List[str]]:
    """
    Return the statements that open and close an impersonated call.
    """
    if not plan.caller_expr:
        return [], []
    return [f"vm.startPrank({uut}.{plan.caller_expr});"], ["vm.stopPrank();"]
