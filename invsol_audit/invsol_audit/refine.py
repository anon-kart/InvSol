from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from .auditor import VERDICT_REFUTED, Verdict

UINT_MAX = (1 << 256) - 1
MAX_SEEDS_PER_FUNCTION = 4

LENGTH_SUFFIX = "_length"
MAX_SHAPE_LENGTH = 16
MAX_SHAPE_CALLS = 8
DEFAULT_BOUND = "64"
FILL_VALUE = "7"


@dataclass
class ShapeRequest:
    """
    A length the solver asked for, expressed over a state array.

    A counterexample naming row_length says the loop failed when a row held one
    element. That is useful only once row has been traced back to grid and to a
    function that can give grid a row of that length.
    """

    symbol: str
    var: str
    target: int
    nested: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "var": self.var,
            "target": self.target,
            "nested": self.nested,
        }


@dataclass
class ShapeCall:
    """One producer call, with the arguments that give the requested length."""

    function: str
    arguments: List[str] = field(default_factory=list)
    array_argument: Optional[Tuple[int, str, int]] = None
    repeat: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "function": self.function,
            "arguments": self.arguments,
            "repeat": self.repeat,
        }


@dataclass
class Seed:
    """
    Concrete arguments that drove an invariant to fail.

    Replaying these makes the next round of fuzzing visit the state the solver
    found, rather than relying on random draws to rediscover it.
    """

    function: str
    loop_id: str
    invariant: str
    arguments: Dict[str, str] = field(default_factory=dict)
    shape: List[ShapeRequest] = field(default_factory=list)
    shape_calls: List[ShapeCall] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "function": self.function,
            "loop_id": self.loop_id,
            "invariant": self.invariant,
            "arguments": self.arguments,
            "shape": [s.to_dict() for s in self.shape],
            "shape_calls": [c.to_dict() for c in self.shape_calls],
        }


def _numeric_params(fn: Dict[str, Any]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for param in fn.get("params") or []:
        name = param.get("name") or ""
        sol_type = str(param.get("type") or "")
        if name and (sol_type.startswith("uint") or sol_type.startswith("int")):
            out[name] = sol_type
    return out


def _owner_of_loop(ir: Dict[str, Any], loop_id: str) -> Optional[Dict[str, Any]]:
    contract = ir.get("contract") or ir
    for fn in contract.get("functions") or []:
        for loop in fn.get("loops") or []:
            if (loop.get("loop_id") or "") == loop_id:
                return fn
    return None


def _clamp(value: str, sol_type: str) -> Optional[str]:
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    if sol_type.startswith("uint"):
        if number < 0:
            return None
        number = min(number, UINT_MAX)
    return str(number)


def _state_arrays(ir: Dict[str, Any]) -> Dict[str, str]:
    contract = ir.get("contract") or ir
    state = contract.get("state") or {}
    out: Dict[str, str] = {}
    for variable in state.get("variables") or []:
        name = variable.get("name") or ""
        sol_type = str(variable.get("type") or "")
        if name and "[" in sol_type:
            out[name] = sol_type
    return out


def _alias_index(fn: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        alias.get("name"): alias
        for alias in (fn.get("storage_aliases") or [])
        if alias.get("name")
    }


def shape_requests(
    ir: Dict[str, Any],
    fn: Dict[str, Any],
    counterexample: Dict[str, str],
) -> List[ShapeRequest]:
    """
    Read the array lengths out of a counterexample.

    A symbol of the form x_length refers either to a state array directly or to
    a local storage pointer, in which case the alias recorded by the analyzer
    says which state array it points into. Lengths that are absurdly large are
    dropped, because they describe a state no test can build.
    """
    arrays = _state_arrays(ir)
    aliases = _alias_index(fn)

    requests: List[ShapeRequest] = []
    seen: Set[str] = set()

    for key, value in counterexample.items():
        if not key.endswith(LENGTH_SUFFIX):
            continue
        base = key[: -len(LENGTH_SUFFIX)]
        if not base or base in seen:
            continue

        try:
            target = int(str(value).strip())
        except (TypeError, ValueError):
            continue
        if target < 0 or target > MAX_SHAPE_LENGTH:
            continue

        if base in arrays:
            seen.add(base)
            requests.append(ShapeRequest(symbol=key, var=base, target=target))
            continue

        alias = aliases.get(base)
        if alias and (alias.get("base") or "") in arrays:
            seen.add(base)
            requests.append(
                ShapeRequest(
                    symbol=key,
                    var=alias["base"],
                    target=target,
                    nested=(alias.get("via") == "index"),
                )
            )

    requests.sort(key=lambda r: (r.var, r.symbol))
    return requests


def _producers_for(ir: Dict[str, Any], var: str) -> List[Tuple[Dict[str, Any], List[Dict[str, Any]]]]:
    """
    Callable functions that push onto a state array, with all of their pushes.

    A function containing three unconditional pushes to the same array grows it
    by three per call, so the effects are grouped rather than taken one at a
    time. Functions whose push sits behind a branch are tried last, since a call
    to one is not guaranteed to grow anything.
    """
    contract = ir.get("contract") or ir
    out: List[Tuple[Dict[str, Any], List[Dict[str, Any]]]] = []
    for fn in contract.get("functions") or []:
        if fn.get("synthetic"):
            continue
        if (fn.get("visibility") or "") not in {"public", "external"}:
            continue
        if (fn.get("name") or "") in {"constructor", "receive", "fallback"}:
            continue
        pushes = [
            effect
            for effect in (fn.get("length_effects") or [])
            if effect.get("var") == var and effect.get("op") == "push"
        ]
        if pushes:
            out.append((fn, pushes))
    out.sort(
        key=lambda pair: (
            all(bool(e.get("conditional")) for e in pair[1]),
            len(pair[0].get("params") or []),
            pair[0].get("name") or "",
        )
    )
    return out


def _element_type(sol_type: str) -> str:
    return (sol_type or "").split("[")[0].strip()


def _default_argument(name: str, sol_type: str) -> str:
    sol_type = (sol_type or "").strip()
    if sol_type.startswith("uint") or sol_type.startswith("int"):
        return DEFAULT_BOUND
    if sol_type == "address":
        return "actorA"
    if sol_type == "bool":
        return "true"
    if sol_type.startswith("bytes32"):
        return "bytes32(uint256(1))"
    if sol_type.startswith("bytes"):
        return 'hex"1234"'
    if sol_type == "string":
        return '"invsol"'
    return ""


def plan_shape_call(
    request: ShapeRequest,
    ir: Dict[str, Any],
) -> Optional[ShapeCall]:
    """
    Choose calls that give a state array the length the solver asked for.

    A nested request needs a producer that pushes one of its own array
    parameters, since the caller then controls the inner length. A direct
    request is satisfied either by one call to a producer whose push sits in a
    loop bounded by a parameter, or by repeating a single-push producer.
    """
    if request.target <= 0:
        return None

    for fn, pushes in _producers_for(ir, request.var):
        params = fn.get("params") or []
        name = fn.get("name") or ""

        if request.nested:
            chosen = next(
                (
                    effect
                    for effect in pushes
                    if (effect.get("element_source") or {}).get("kind") == "param"
                ),
                None,
            )
            if chosen is None:
                continue
            pushed = (chosen.get("element_source") or {}).get("name") or ""
            position = next(
                (i for i, p in enumerate(params) if (p.get("name") or "") == pushed),
                None,
            )
            if position is None:
                continue
            element = _element_type(str(params[position].get("type") or ""))
            if not element:
                continue

            arguments: List[str] = []
            usable = True
            for index, param in enumerate(params):
                if index == position:
                    arguments.append("")
                    continue
                literal = _default_argument(
                    param.get("name") or "", str(param.get("type") or "")
                )
                if not literal:
                    usable = False
                    break
                arguments.append(literal)
            if not usable:
                continue

            return ShapeCall(
                function=name,
                arguments=arguments,
                array_argument=(position, element, request.target),
                repeat=1,
            )

        bound_position = None
        for effect in pushes:
            if not effect.get("in_loop"):
                continue
            count = str(effect.get("count") or "1")
            candidate = next(
                (i for i, p in enumerate(params) if (p.get("name") or "") == count),
                None,
            )
            if candidate is not None:
                bound_position = candidate
                break

        arguments = []
        usable = True
        for index, param in enumerate(params):
            sol_type = str(param.get("type") or "")
            if "[" in sol_type:
                usable = False
                break
            if index == bound_position:
                arguments.append(str(request.target))
                continue
            literal = _default_argument(param.get("name") or "", sol_type)
            if not literal:
                usable = False
                break
            arguments.append(literal)
        if not usable:
            continue

        if bound_position is not None:
            return ShapeCall(function=name, arguments=arguments, repeat=1)

        per_call = max(
            1, sum(1 for effect in pushes if not effect.get("conditional") and not effect.get("in_loop"))
        )
        repeat = min(-(-request.target // per_call), MAX_SHAPE_CALLS)
        return ShapeCall(function=name, arguments=arguments, repeat=repeat)

    return None


def seeds_from_verdicts(
    ir: Dict[str, Any],
    verdicts: Sequence[Verdict],
    *,
    limit: int = MAX_SEEDS_PER_FUNCTION,
) -> List[Seed]:
    """
    Read concrete argument values out of refuted verdicts.

    Only names that are parameters of the owning function are usable, because
    those are the values a test can actually supply.
    """
    seeds: List[Seed] = []
    per_function: Dict[str, int] = {}

    for verdict in verdicts:
        if verdict.status != VERDICT_REFUTED or not verdict.counterexample:
            continue

        fn = _owner_of_loop(ir, verdict.loop_id)
        if fn is None:
            continue

        name = fn.get("name") or ""
        if per_function.get(name, 0) >= limit:
            continue

        params = _numeric_params(fn)
        arguments: Dict[str, str] = {}
        for key, value in verdict.counterexample.items():
            base = key.split("__next")[0]
            if base in params:
                clamped = _clamp(value, params[base])
                if clamped is not None:
                    arguments.setdefault(base, clamped)

        requests = shape_requests(ir, fn, verdict.counterexample)
        calls: List[ShapeCall] = []
        for request in requests:
            call = plan_shape_call(request, ir)
            if call is not None:
                calls.append(call)

        if not arguments and not calls:
            continue

        per_function[name] = per_function.get(name, 0) + 1
        seeds.append(
            Seed(
                function=name,
                loop_id=verdict.loop_id,
                invariant=verdict.invariant,
                arguments=arguments,
                shape=requests,
                shape_calls=calls,
            )
        )

    return seeds


def priority_functions(verdicts: Sequence[Verdict], ir: Dict[str, Any]) -> List[str]:
    """
    Functions whose invariants failed, ordered by how many failed.

    Later rounds spend their budget here rather than spreading it evenly, which
    is the feedback weighting the refinement loop depends on.
    """
    counts: Dict[str, int] = {}
    for verdict in verdicts:
        if verdict.status != VERDICT_REFUTED:
            continue
        fn = _owner_of_loop(ir, verdict.loop_id)
        if fn is None:
            continue
        name = fn.get("name") or ""
        counts[name] = counts.get(name, 0) + 1
    return [name for name, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]


def render_seed_tests(
    seeds: Sequence[Seed],
    ir: Dict[str, Any],
    *,
    round_index: int = 0,
) -> List[str]:
    """
    Emit directed tests that call each function with the failing arguments.

    These are ordinary tests rather than fuzz tests, so the values are used
    exactly as the solver reported them. The round number is part of every
    generated name, because a later round adds its tests to a harness that
    already holds the earlier ones and two functions cannot share a name.
    """
    contract = ir.get("contract") or ir
    by_name = {fn.get("name"): fn for fn in contract.get("functions") or []}

    lines: List[str] = []
    for index, seed in enumerate(seeds):
        fn = by_name.get(seed.function)
        if fn is None:
            continue

        args: List[str] = []
        usable = True
        for param in fn.get("params") or []:
            name = param.get("name") or ""
            sol_type = str(param.get("type") or "")
            if name in seed.arguments:
                args.append(seed.arguments[name])
            elif sol_type.startswith("uint") or sol_type.startswith("int"):
                args.append("1")
            elif sol_type == "address":
                args.append("actorA")
            elif sol_type == "bool":
                args.append("true")
            elif "[" in sol_type:
                usable = False
                break
            else:
                usable = False
                break

        if not usable:
            continue

        lines.append("")
        lines.append(f"    // replay for: {seed.invariant}")
        lines.append(
            f"    function test_seed_{seed.function}_{round_index}_{index}() public {{"
        )
        lines.extend(render_shape_calls(seed.shape_calls, round_index, index))
        lines.append(f"        try uut.{seed.function}({', '.join(args)}) {{}} catch {{}}")
        lines.append("    }")

    return lines


def render_shape_calls(
    calls: Sequence[ShapeCall],
    round_index: int,
    index: int,
) -> List[str]:
    """
    Statements that put the contract into the shape the solver described.

    These run before the replay call, so the loop under test iterates over the
    data the counterexample referred to rather than whatever the constructor
    happened to leave behind.
    """
    lines: List[str] = []
    for position, call in enumerate(calls):
        arguments = list(call.arguments)

        if call.array_argument is not None:
            slot, element, length = call.array_argument
            variable = f"_shape{round_index}_{index}_{position}"
            lines.append(
                f"        {element}[] memory {variable} = new {element}[]({length});"
            )
            if length:
                lines.append(f"        for (uint256 k = 0; k < {length}; k++) {{")
                if element == "address":
                    lines.append(f"            {variable}[k] = address(uint160(0x2000 + k));")
                else:
                    lines.append(f"            {variable}[k] = {element}({FILL_VALUE});")
                lines.append("        }")
            arguments[slot] = variable

        rendered = ", ".join(arguments)
        if call.repeat > 1:
            lines.append(f"        for (uint256 s = 0; s < {call.repeat}; s++) {{")
            lines.append(f"            try uut.{call.function}({rendered}) {{}} catch {{}}")
            lines.append("        }")
        else:
            lines.append(f"        try uut.{call.function}({rendered}) {{}} catch {{}}")

    return lines


def inject_seed_tests(harness_source: str, seed_lines: Sequence[str]) -> str:
    """
    Add the replay tests to an existing harness, just before its closing brace.
    """
    if not seed_lines:
        return harness_source

    marker = harness_source.rstrip().rfind("}")
    if marker == -1:
        return harness_source

    head = harness_source[:marker].rstrip("\n")
    return head + "\n" + "\n".join(seed_lines) + "\n}\n"


@dataclass
class RoundSummary:
    round_index: int
    checked: int
    verified: int
    refuted: int
    new_seeds: int
    priority: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "round": self.round_index,
            "checked": self.checked,
            "verified": self.verified,
            "refuted": self.refuted,
            "new_seeds": self.new_seeds,
            "priority": self.priority,
        }


def has_converged(history: Sequence[RoundSummary]) -> bool:
    """
    Whether another round is worth running.

    Refinement stops when nothing is refuted, when no new seed can be produced,
    or when a round repeats the previous one's outcome.
    """
    if not history:
        return False

    latest = history[-1]
    if latest.refuted == 0 or latest.new_seeds == 0:
        return True

    if len(history) >= 2:
        previous = history[-2]
        if (latest.refuted, latest.verified) == (previous.refuted, previous.verified):
            return True

    return False


def load_verdicts(path: str) -> List[Verdict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    out: List[Verdict] = []
    for record in data.get("verdicts") or []:
        out.append(
            Verdict(
                loop_id=record.get("loop_id") or "",
                invariant=record.get("invariant") or "",
                status=record.get("status") or "",
                detail=record.get("detail") or "",
                counterexample=record.get("counterexample") or {},
                conditions=record.get("conditions") or [],
                assumptions=record.get("assumptions") or [],
            )
        )
    return out


def main(argv: Optional[List[str]] = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(
        description="Turn refuted invariants into directed fuzzing seeds."
    )
    ap.add_argument("ir")
    ap.add_argument("audit")
    ap.add_argument("--harness", help="harness file to extend with replay tests")
    ap.add_argument("-o", "--out", help="where to write the seed record")
    args = ap.parse_args(argv)

    ir = json.loads(Path(args.ir).read_text(encoding="utf-8"))
    verdicts = load_verdicts(args.audit)

    seeds = seeds_from_verdicts(ir, verdicts)
    priority = priority_functions(verdicts, ir)

    print(f"{len(seeds)} seeds from {sum(1 for v in verdicts if v.status == VERDICT_REFUTED)} refutations")
    for seed in seeds:
        for request in seed.shape:
            print(f"  shape: {request.symbol} = {request.target} via {request.var}")
        for call in seed.shape_calls:
            suffix = f" x{call.repeat}" if call.repeat > 1 else ""
            print(f"  producer: {call.function}{suffix}")
    for name in priority:
        print(f"  priority: {name}")

    if args.out:
        Path(args.out).write_text(
            json.dumps({"seeds": [s.to_dict() for s in seeds], "priority": priority}, indent=2),
            encoding="utf-8",
        )

    if args.harness and seeds:
        path = Path(args.harness)
        source = path.read_text(encoding="utf-8")
        path.write_text(inject_seed_tests(source, render_seed_tests(seeds, ir)), encoding="utf-8")
        print(f"added replay tests to {args.harness}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
