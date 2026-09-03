from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from .expr import (
    Binary,
    Call,
    Index,
    Member,
    Not,
    Num,
    ParseError,
    Var,
    free_variables,
    parse_expression,
    rename,
    render,
    symbol_for,
)

UINT_MAX = (1 << 256) - 1
BITS = 256

# Unsigned comparisons and modular arithmetic, for loops whose updates happen
# inside an unchecked block.
SMT_BV_OPS = {
    "+": "bvadd",
    "-": "bvsub",
    "*": "bvmul",
    "/": "bvudiv",
    "%": "bvurem",
    "<": "bvult",
    "<=": "bvule",
    ">": "bvugt",
    ">=": "bvuge",
    "==": "=",
    "!=": "=",
    "&&": "and",
    "||": "or",
}
PRIME_SUFFIX = "__next"

SMT_OPS = {
    "+": "+",
    "-": "-",
    "*": "*",
    "/": "div",
    "%": "mod",
    "==": "=",
    "<": "<",
    "<=": "<=",
    ">": ">",
    ">=": ">=",
    "&&": "and",
    "||": "or",
    "=>": "=>",
}


@dataclass
class LoopModel:
    """
    A transition system for one loop.

    State is the loop index together with the variables the body updates. The
    transition comes from the accumulator facts recorded during AST analysis,
    so it reflects what the body actually does rather than a guess.
    """

    loop_id: str
    index: str = ""
    lower: str = "0"
    upper: str = ""
    inclusive_upper: bool = False
    direction: str = "increasing"
    updates: Dict[str, str] = field(default_factory=dict)
    state: Set[str] = field(default_factory=set)
    # True when the body updates a variable inside an unchecked block, where
    # arithmetic wraps rather than reverting.
    wraps: bool = False
    # Local storage pointers resolved to the location they alias.
    aliases: Dict[str, Any] = field(default_factory=dict)
    symbols: Set[str] = field(default_factory=set)
    notes: List[str] = field(default_factory=list)

    aggregates: Dict[str, str] = field(default_factory=dict)
    initial: Dict[str, str] = field(default_factory=dict)

    def initial_constraints(self) -> List[str]:
        """
        What is known when the loop is first reached.

        An accumulator declared for the loop starts at zero, which is what makes
        a bound such as partial <= total provable at entry.
        """
        out = [f"{name} == {value}" for name, value in sorted(self.initial.items())]
        out.extend(self.ghost_constraints())
        return out

    def ghost_constraints(self) -> List[str]:
        """
        Relate each accumulator to the total of the container it reads.

        The remaining amount is the part of the total not yet added. Keeping it
        non-negative is what lets a partial sum be shown never to exceed the
        whole.
        """
        out: List[str] = []
        for var, base in sorted(self.aggregates.items()):
            out.append(f"{var} + rem_{base} == sum_{base}")
            out.append(f"rem_{base} >= 0")
        return out

    def ghost_transition(self) -> List[str]:
        out: List[str] = []
        for var, base in sorted(self.aggregates.items()):
            element = f"{base}_at_{self.index}" if self.index else f"{base}_element"
            out.append(f"{element} <= rem_{base}")
            out.append(f"rem_{base}{PRIME_SUFFIX} == rem_{base} - {element}")
            out.append(f"{_primed(var)} + rem_{base}{PRIME_SUFFIX} == sum_{base}")
        return out

    def guard_expression(self) -> Optional[str]:
        if not self.index or not self.upper:
            return None
        comparator = "<=" if self.inclusive_upper else "<"
        if self.direction == "decreasing":
            comparator = ">=" if self.inclusive_upper else ">"
            return f"{self.index} {comparator} {self.lower or '0'}"
        return f"{self.index} {comparator} {self.upper}"


def _alias_map(aliases: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Parse each recorded storage alias into the term it stands for.

    An alias the parser cannot read is left out rather than guessed at, so the
    pointer stays an opaque symbol and no false identity is introduced.
    """
    out: Dict[str, Any] = {}
    for alias in aliases:
        name = alias.get("name") or ""
        base = alias.get("base") or ""
        if not name or not base:
            continue
        if alias.get("via") == "index" and alias.get("index"):
            text = f"{base}[{alias['index']}]"
        elif alias.get("via") == "member" and alias.get("index"):
            text = f"{base}.{alias['index']}"
        else:
            text = base
        try:
            out[name] = parse_expression(text)
        except ParseError:
            continue
    return out


def build_loop_model(loop: Dict[str, Any]) -> LoopModel:
    bounds = loop.get("bounds") or {}
    body = loop.get("body_summary") or {}

    model = LoopModel(
        loop_id=loop.get("loop_id") or "",
        index=str(bounds.get("index") or ""),
        lower=str(bounds.get("lower") or "0"),
        upper=str(bounds.get("upper") or ""),
        inclusive_upper=bool(bounds.get("inclusive_upper")),
        direction=str(loop.get("index_direction") or body.get("index_direction") or "increasing"),
        wraps=bool(body.get("has_unchecked")),
        aliases=_alias_map(body.get("storage_aliases") or []),
    )

    if model.index:
        model.state.add(model.index)
        step = "+ 1" if model.direction != "decreasing" else "- 1"
        model.updates[model.index] = f"{model.index} {step}"
        model.initial[model.index] = model.lower or "0"

        # iterations counts passes through the body, starting at one
        model.state.add("iterations")
        model.updates["iterations"] = "iterations + 1"
        model.initial["iterations"] = "1"

    for fact in body.get("accumulator_facts") or []:
        var = fact.get("var") or ""
        if not var:
            continue
        source = (fact.get("source") or {}).get("expr") or "0"
        op = fact.get("op") or "+="

        model.state.add(var)
        container = (fact.get("source") or {}).get("container")
        base = (fact.get("source") or {}).get("base") or ""
        if op == "+=" and container in {"array", "mapping"} and base:
            model.aggregates[var] = base
        if fact.get("scope") == "local" or fact.get("kind") in {"sum", "count"}:
            model.initial.setdefault(var, "0")
        if op == "+=":
            model.updates[var] = f"{var} + {_scalar(source)}"
        elif op == "-=":
            model.updates[var] = f"{var} - {_scalar(source)}"
        elif op == "*=":
            model.updates[var] = f"{var} * {_scalar(source)}"
        else:
            model.notes.append(f"{var} uses {op}, treated as unconstrained")

    return model


def _scalar(source: str) -> str:
    """
    Represent the accumulated term.

    An element read from an array or mapping is opaque here, so it becomes a
    single non-negative unknown rather than being modelled per index.
    """
    text = (source or "").strip()
    if not text:
        return "0"
    try:
        node = parse_expression(text)
    except ParseError:
        return "0"
    if isinstance(node, Num):
        return str(node.value)
    if isinstance(node, Var):
        return node.name
    return symbol_for(node)


class Encoder:
    """
    Translate parsed relations into SMT-LIB over unbounded integers with an
    explicit unsigned range.

    Section V restricts the tool to a decidable fragment, and linear integer
    arithmetic with range constraints stays inside it. Modular wraparound would
    need bit-vectors, so overflow is excluded by assumption rather than modelled,
    and that assumption is reported alongside each result.
    """

    def __init__(
        self,
        bitvector: bool = False,
        aliases: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.declared: Dict[str, None] = {}
        # Local storage pointers and the location they refer into. Writing
        # through row when row was declared as grid[r] writes grid, so both
        # have to resolve to one symbol or the solver treats them as separate
        # state and misses the interference.
        self.aliases: Dict[str, Any] = aliases or {}
        # Bit-vector mode represents wraparound faithfully, at the cost of
        # leaving linear integer arithmetic for a theory that is slower and
        # whose counterexamples read less clearly.
        self.bitvector = bitvector

    def declare(self, name: str) -> None:
        if name not in self.declared:
            self.declared[name] = None

    def literal(self, value: Any) -> str:
        if not self.bitvector:
            return str(value)
        return f"(_ bv{int(value)} {BITS})"

    def resolve(self, node: Any) -> Any:
        """Rewrite an aliased local pointer to the location it refers into."""
        if not self.aliases:
            return node
        if isinstance(node, Var):
            return self.aliases.get(node.name, node)
        if isinstance(node, Index):
            return Index(base=self.resolve(node.base), key=self.resolve(node.key))
        if isinstance(node, Member):
            return Member(base=self.resolve(node.base), field=node.field)
        if isinstance(node, Call):
            return Call(name=node.name, args=tuple(self.resolve(a) for a in node.args))
        if isinstance(node, Binary):
            return Binary(
                op=node.op,
                left=self.resolve(node.left),
                right=self.resolve(node.right),
            )
        if isinstance(node, Not):
            return Not(operand=self.resolve(node.operand))
        return node

    def term(self, node: Any) -> str:
        node = self.resolve(node)
        if isinstance(node, Num):
            return self.literal(node.value)
        if isinstance(node, Var):
            self.declare(node.name)
            return node.name
        if isinstance(node, (Call, Member, Index)):
            name = symbol_for(node)
            self.declare(name)
            return name
        if isinstance(node, Not):
            return f"(not {self.term(node.operand)})"
        if isinstance(node, Binary):
            table = SMT_BV_OPS if self.bitvector else SMT_OPS
            op = table.get(node.op)
            if op is None:
                raise ParseError(f"unsupported operator {node.op}")
            if node.op == "!=":
                return f"(not (= {self.term(node.left)} {self.term(node.right)}))"
            return f"({op} {self.term(node.left)} {self.term(node.right)})"
        raise ParseError(f"cannot encode {node!r}")

    def declarations(self) -> List[str]:
        sort = f"(_ BitVec {BITS})" if self.bitvector else "Int"
        return [f"(declare-const {name} {sort})" for name in self.declared]

    def range_assumptions(self) -> List[str]:
        # A 256-bit vector is already confined to the uint256 range, so the
        # bound has to be asserted only in the integer encoding.
        if self.bitvector:
            return []
        return [f"(assert (and (>= {name} 0) (<= {name} {UINT_MAX})))" for name in self.declared]


@dataclass
class VerificationCondition:
    loop_id: str
    invariant: str
    kind: str
    smt: str
    assumptions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "loop_id": self.loop_id,
            "invariant": self.invariant,
            "kind": self.kind,
            "smt": self.smt,
            "assumptions": self.assumptions,
        }


def _primed(name: str) -> str:
    return f"{name}{PRIME_SUFFIX}"


def build_conditions(model: LoopModel, invariant_text: str) -> List[VerificationCondition]:
    """
    Produce the two conditions an inductive invariant must satisfy.

    Establishment asks whether the invariant holds when the loop is first
    entered. Preservation asks whether one pass through the body keeps it true.
    Each is posed as a satisfiability query for the negation, so a model is a
    counterexample.
    """
    try:
        invariant = parse_expression(invariant_text)
    except ParseError as exc:
        return [
            VerificationCondition(
                loop_id=model.loop_id,
                invariant=invariant_text,
                kind="parse",
                smt="",
                assumptions=[f"could not parse: {exc}"],
            )
        ]

    conditions: List[VerificationCondition] = []
    two_state = _mentions_previous_state(invariant)

    if not two_state:
        entry_map = {model.index: model.lower or "0"} if model.index else {}
        entry_invariant = _substitute_text(invariant, entry_map, protect_calls=True)

        conditions.append(
            _condition(
                model,
                invariant_text,
                "establishment",
                premises=model.initial_constraints(),
                goal=entry_invariant,
            )
        )

    guard = model.guard_expression()
    prime_map = {name: _primed(name) for name in model.state}

    premises: List[str] = []
    if not two_state:
        premises.append(render(invariant))
    if guard:
        premises.append(guard)
    premises.extend(model.ghost_constraints())

    if two_state:
        goal_node = _resolve_previous_state(invariant, prime_map)
    else:
        goal_node = rename(invariant, prime_map)

    transition: List[str] = []
    for name in sorted(model.state):
        update = model.updates.get(name)
        if update:
            transition.append(f"{_primed(name)} == {update}")
    transition.extend(model.ghost_transition())

    conditions.append(
        _condition(
            model,
            invariant_text,
            "preservation",
            premises=premises + transition,
            goal=render(goal_node),
        )
    )

    return conditions


def _mentions_previous_state(node: Any) -> bool:
    """
    Whether the relation compares the current value against the previous one.

    A relation such as total >= old(total) constrains a step rather than a
    single state, so it has no establishment obligation and its preservation
    check reads old as the value before the step.
    """
    found = False

    def walk(item: Any) -> None:
        nonlocal found
        if isinstance(item, Call) and item.name in {"old", "entry"}:
            found = True
        elif isinstance(item, Binary):
            walk(item.left)
            walk(item.right)
        elif isinstance(item, Not):
            walk(item.operand)
        elif isinstance(item, Call):
            for arg in item.args:
                walk(arg)

    walk(node)
    return found


def _resolve_previous_state(node: Any, prime_map: Dict[str, str]) -> Any:
    """
    Rewrite a step relation into the two-state form the solver checks.

    old(v) becomes the pre-state variable and every other occurrence of v
    becomes the post-state one, so total >= old(total) is checked as
    total' >= total.
    """
    if isinstance(node, Call) and node.name in {"old", "entry"} and node.args:
        inner = node.args[0]
        return inner
    if isinstance(node, Var):
        return Var(prime_map.get(node.name, node.name))
    if isinstance(node, Binary):
        return Binary(
            node.op,
            _resolve_previous_state(node.left, prime_map),
            _resolve_previous_state(node.right, prime_map),
        )
    if isinstance(node, Not):
        return Not(_resolve_previous_state(node.operand, prime_map))
    if isinstance(node, Call):
        return Call(node.name, tuple(_resolve_previous_state(a, prime_map) for a in node.args))
    return node


def _rename_text(text: str, mapping: Dict[str, str], skip: bool = False) -> str:
    if skip:
        return text
    return render(rename(parse_expression(text), mapping))


def _substitute_text(node: Any, mapping: Dict[str, str], protect_calls: bool = False) -> str:
    if not mapping:
        return render(node)
    replaced = node
    for name, value in mapping.items():
        try:
            value_node = parse_expression(value)
        except ParseError:
            continue
        replaced = _replace_var(replaced, name, value_node, protect_calls)
    return render(replaced)


def _replace_var(node: Any, name: str, value: Any, protect_calls: bool = False) -> Any:
    """
    Substitute a variable, optionally leaving call arguments untouched.

    Rewriting the argument of old or sum would change what the term refers to,
    so those are left alone when the substitution models loop entry.
    """
    if isinstance(node, Var):
        return value if node.name == name else node
    if isinstance(node, Binary):
        return Binary(
            node.op,
            _replace_var(node.left, name, value, protect_calls),
            _replace_var(node.right, name, value, protect_calls),
        )
    if isinstance(node, Not):
        return Not(_replace_var(node.operand, name, value, protect_calls))
    if isinstance(node, Call):
        if protect_calls:
            return node
        return Call(node.name, tuple(_replace_var(a, name, value, protect_calls) for a in node.args))
    if isinstance(node, Member):
        return Member(_replace_var(node.base, name, value, protect_calls), node.field)
    if isinstance(node, Index):
        return Index(
            _replace_var(node.base, name, value, protect_calls),
            _replace_var(node.key, name, value, protect_calls),
        )
    return node


def symbols_in(node: Any) -> Set[str]:
    """Every variable and abstracted location a term mentions."""
    if isinstance(node, Var):
        return {node.name}
    if isinstance(node, Num):
        return set()
    if isinstance(node, (Call, Member, Index)):
        found = {symbol_for(node)}
        for child in _children(node):
            found |= symbols_in(child)
        return found
    if isinstance(node, Not):
        return symbols_in(node.operand)
    if isinstance(node, Binary):
        return symbols_in(node.left) | symbols_in(node.right)
    return set()


def _children(node: Any) -> List[Any]:
    if isinstance(node, Index):
        return [node.base, node.key]
    if isinstance(node, Member):
        return [node.base]
    if isinstance(node, Call):
        return list(node.args)
    return []


def slice_premises(premises: List[Any], goal: Any) -> Tuple[List[Any], List[Any]]:
    """
    Keep only the premises that can bear on the goal.

    Starting from the symbols the goal mentions, a premise is kept when it
    shares a symbol with anything already kept, and its own symbols then join
    the set. Premises about unrelated state are dropped, which shrinks the
    query without changing what it means: a dropped premise shares no symbol
    with the goal even indirectly, so it cannot constrain it.
    """
    relevant = symbols_in(goal)
    kept: List[Any] = []
    remaining = list(premises)

    changed = True
    while changed:
        changed = False
        still: List[Any] = []
        for premise in remaining:
            names = symbols_in(premise)
            if names & relevant:
                kept.append(premise)
                relevant |= names
                changed = True
            else:
                still.append(premise)
        remaining = still

    return kept, remaining


def _condition(
    model: LoopModel,
    invariant_text: str,
    kind: str,
    premises: List[str],
    goal: str,
) -> VerificationCondition:
    encoder = Encoder(bitvector=model.wraps, aliases=model.aliases)
    logic = "QF_BV" if model.wraps else "QF_LIA"
    lines: List[str] = [f"(set-logic {logic})"]

    # Encode the goal first so slicing knows what the query is about.
    try:
        goal_ast = encoder.resolve(parse_expression(goal))
    except ParseError as exc:
        return VerificationCondition(
            loop_id=model.loop_id,
            invariant=invariant_text,
            kind=kind,
            smt="",
            assumptions=[f"could not encode goal: {exc}"],
        )

    parsed_premises = []
    for premise in premises:
        try:
            parsed_premises.append(encoder.resolve(parse_expression(premise)))
        except ParseError:
            continue

    kept, dropped = slice_premises(parsed_premises, goal_ast)

    encoded_premises: List[str] = []
    for premise in kept:
        try:
            encoded_premises.append(encoder.term(premise))
        except ParseError:
            continue

    try:
        encoded_goal = encoder.term(goal_ast)
    except ParseError as exc:
        return VerificationCondition(
            loop_id=model.loop_id,
            invariant=invariant_text,
            kind=kind,
            smt="",
            assumptions=[f"could not encode goal: {exc}"],
        )

    lines.extend(encoder.declarations())
    lines.extend(encoder.range_assumptions())
    for premise in encoded_premises:
        lines.append(f"(assert {premise})")
    lines.append(f"(assert (not {encoded_goal}))")
    lines.append("(check-sat)")
    lines.append("(get-model)")

    if model.wraps:
        assumptions = [
            "arithmetic wraps modulo 2**256, modelled with 256-bit vectors"
        ]
    else:
        # Solidity 0.8 reverts on overflow, so any execution that reaches the
        # next iteration stayed in range. That is a property of the language
        # rather than something assumed away.
        assumptions = [
            "checked arithmetic: Solidity 0.8 reverts on overflow, "
            "so surviving executions stay within uint256"
        ]
    assumptions.extend(model.notes)
    if dropped:
        assumptions.append(
            f"{len(dropped)} premises about unrelated state were sliced away"
        )

    return VerificationCondition(
        loop_id=model.loop_id,
        invariant=invariant_text,
        kind=kind,
        smt="\n".join(lines),
        assumptions=assumptions,
    )


@dataclass
class FunctionModel:
    """
    What one function can change, seen from outside it.

    A contract-level invariant is checked against this rather than against a
    loop transition: the question is not how the body iterates but whether the
    function can disturb the property at all.
    """

    name: str
    writes: Set[str] = field(default_factory=set)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "writes": sorted(self.writes), "notes": self.notes}


def build_function_model(fn: Dict[str, Any]) -> FunctionModel:
    """State this function writes, by any route."""
    writes: Set[str] = set()
    notes: List[str] = []

    for name in fn.get("writes") or []:
        if name:
            writes.add(str(name))
    for touch in fn.get("storage_writes") or []:
        if touch.get("var"):
            writes.add(str(touch["var"]))
    for effect in fn.get("length_effects") or []:
        if effect.get("var"):
            writes.add(str(effect["var"]))

    if fn.get("external_calls"):
        notes.append("makes an external call, so reentrant writes are possible")

    return FunctionModel(name=fn.get("name") or "", writes=writes, notes=notes)


def _base_of(symbol: str) -> str:
    """The state variable an abstracted location belongs to."""
    for marker in ("_at_", "_length"):
        if marker in symbol:
            return symbol.split(marker, 1)[0]
    return symbol


def _mentions_written_state(symbol: str, writes: Set[str]) -> bool:
    """
    Whether a symbol can be disturbed by writing any of these variables.

    An abstracted location keeps the variable it came from somewhere in its
    name: balances_at_i, grid_at_r_length, sum_observed_stakeOf. Matching on
    any component over-approximates, which is the safe direction, since
    treating an unaffected symbol as affected costs an unknown while the
    reverse would claim an invariant the function can actually break.
    """
    parts = set(re.split(r"[^A-Za-z0-9]+", symbol))
    parts.discard("")
    return bool(parts & writes)


def build_function_condition(
    model: FunctionModel, invariant_text: str
) -> VerificationCondition:
    """
    Ask whether this function can break a contract-level invariant.

    The invariant is assumed at entry and denied at exit. Every location the
    function may write is renamed at exit and left unconstrained, because the
    IR records that a write happens but not what value it stores. An invariant
    over locations the function never touches therefore comes back verified,
    and one over locations it does touch comes back unknown rather than
    refuted: the tool has not shown a violation, only failed to rule one out.
    """
    encoder = Encoder()

    # An invariant mentioning old(v) is a two-state property: old(v) is the
    # entry value and a bare v is the exit value. One without it is a state
    # property, assumed at entry and re-checked at exit.
    two_state = "old(" in invariant_text.replace(" ", "")

    try:
        parsed = parse_expression(invariant_text)
        before = encoder.term(parsed)
    except ParseError as exc:
        return VerificationCondition(
            loop_id=f"{model.name}::contract",
            invariant=invariant_text,
            kind="cross-function",
            smt="",
            assumptions=[f"could not encode invariant: {exc}"],
        )

    touched = sorted(
        name
        for name in encoder.declared
        if _mentions_written_state(name, model.writes)
    )

    if two_state:
        # old_x already stands for the entry value, so only the bare names have
        # to move to the exit state. Nothing is assumed beforehand: the claim is
        # about the step itself.
        goal = before
        for name in touched:
            if name.startswith("old_"):
                continue
            goal = re.sub(rf"\b{re.escape(name)}\b", f"{name}__after", goal)
        premise = None
        renamed = [n for n in touched if not n.startswith("old_")]
    else:
        goal = before
        for name in touched:
            goal = re.sub(rf"\b{re.escape(name)}\b", f"{name}__after", goal)
        premise = before
        renamed = list(touched)

    lines: List[str] = ["(set-logic QF_LIA)"]
    lines.extend(encoder.declarations())
    for name in renamed:
        lines.append(f"(declare-const {name}__after Int)")
    lines.extend(encoder.range_assumptions())

    # old(v) is the entry value of v, so it has to be tied to the entry symbol.
    # Without this a function that never touches v still fails v >= old(v),
    # because the two names would be unrelated.
    for name in sorted(encoder.declared):
        if not name.startswith("old_"):
            continue
        entry = name[len("old_"):]
        if entry in encoder.declared:
            lines.append(f"(assert (= {name} {entry}))")
    for name in renamed:
        lines.append(
            f"(assert (and (>= {name}__after 0) (<= {name}__after {UINT_MAX})))"
        )
    if premise is not None:
        lines.append(f"(assert {premise})")
    lines.append(f"(assert (not {goal}))")
    lines.append("(check-sat)")
    lines.append("(get-model)")

    assumptions = list(model.notes)
    if renamed:
        assumptions.append(
            "the function writes "
            + ", ".join(sorted({_base_of(n) for n in renamed}))
            + ", and the stored value is not modelled"
        )
    else:
        assumptions.append("the function writes none of the locations mentioned")

    return VerificationCondition(
        loop_id=f"{model.name}::contract",
        invariant=invariant_text,
        kind="cross-function",
        smt="\n".join(lines),
        assumptions=assumptions,
    )
