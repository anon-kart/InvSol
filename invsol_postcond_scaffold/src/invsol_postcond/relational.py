from __future__ import annotations

import re
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

ROUND_CONSTANTS = [10, 100, 128, 256, 1000, 10000]
MIN_RUNS_FOR_CAP = 2
MIN_STEPS_FOR_COUNTER = 3
MIN_DISTINCT_FOR_COUNTER = 2


@dataclass
class Relation:
    """
    One candidate relation over loop state.

    scope is "post" for a property expected when the loop finishes, and "loop"
    for one expected at every iteration. Only the second kind can be handed to
    the mutation engine as an inductive seed.
    """

    expr: str
    scope: str
    origin: str
    support: int = 0
    holds: bool = True
    loop_id: str = ""
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "expr": self.expr,
            "scope": self.scope,
            "origin": self.origin,
            "support": self.support,
            "holds": self.holds,
            "loop_id": self.loop_id,
            "note": self.note,
        }


@dataclass
class LoopObservation:
    """
    Everything the traces recorded for one loop, grouped by run.
    """

    loop_id: str
    runs: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def run_count(self) -> int:
        return len(self.runs)

    def trip_counts(self) -> List[int]:
        return [r.get("trip_count") or 0 for r in self.runs]

    def variables(self) -> List[str]:
        names: Set[str] = set()
        for run in self.runs:
            names |= set(run.get("entry") or {})
            names |= set(run.get("exit") or {})
            for it in run.get("iterations") or []:
                names |= set(it.get("values") or {})
        return sorted(names)

    def series(self, name: str) -> List[List[int]]:
        """
        Values of one variable across the iterations of each run.
        """
        out: List[List[int]] = []
        for run in self.runs:
            values: List[int] = []
            for it in run.get("iterations") or []:
                raw = (it.get("values") or {}).get(name)
                parsed = _as_int(raw)
                if parsed is not None:
                    values.append(parsed)
            if values:
                out.append(values)
        return out

    def entry_exit(self, name: str) -> List[Tuple[Optional[int], Optional[int]]]:
        pairs: List[Tuple[Optional[int], Optional[int]]] = []
        for run in self.runs:
            pairs.append(
                (
                    _as_int((run.get("entry") or {}).get(name)),
                    _as_int((run.get("exit") or {}).get(name)),
                )
            )
        return pairs


def _as_int(raw: Any) -> Optional[int]:
    if raw is None:
        return None
    text = str(raw).strip().replace("_", "")
    try:
        if text.lower().startswith("0x"):
            return int(text, 16)
        return int(text)
    except ValueError:
        return None


def load_observations(path: str) -> Dict[str, LoopObservation]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return observations_from_summary(data)


def observations_from_summary(data: Dict[str, Any]) -> Dict[str, LoopObservation]:
    out: Dict[str, LoopObservation] = {}
    for entry in data.get("loops") or []:
        loop_id = entry.get("loop_id") or ""
        if not loop_id:
            continue
        out[loop_id] = LoopObservation(loop_id=loop_id, runs=entry.get("samples") or [])
    return out


def _nearest_round_bound(value: int) -> Optional[int]:
    """
    Pick a constant a developer would plausibly have written.

    An observed maximum of 100 is far more likely to reflect a real cap than a
    maximum of 97, so only exact matches against familiar constants are used.
    """
    for candidate in ROUND_CONSTANTS:
        if value == candidate:
            return candidate
    return None


def relations_from_facts(loop: Dict[str, Any]) -> List[Relation]:
    """
    Structural relations implied by what the loop body does.

    An accumulator that adds successive elements of an array yields the total of
    that array on exit, and no more than that total at any point in between.
    """
    loop_id = loop.get("loop_id") or ""
    body = loop.get("body_summary") or {}
    bounds = loop.get("bounds") or {}
    out: List[Relation] = []

    for fact in body.get("accumulator_facts") or []:
        var = fact.get("var") or ""
        if not var:
            continue
        kind = fact.get("kind") or ""
        source = fact.get("source") or {}
        base = source.get("base") or ""
        container = source.get("container")

        if kind == "sum" and container in {"array", "mapping"} and base:
            out.append(
                Relation(
                    expr=f"{var} == sum({base})",
                    scope="post",
                    origin="fact",
                    loop_id=loop_id,
                    note="accumulator adds each element of the traversed container",
                )
            )
            out.append(
                Relation(
                    expr=f"{var} <= sum({base})",
                    scope="loop",
                    origin="fact",
                    loop_id=loop_id,
                    note="partial sum never exceeds the total",
                )
            )

        if kind == "count":
            upper = str(bounds.get("upper") or "").strip()
            if upper:
                comparator = "<=" if bounds.get("inclusive_upper") else "<="
                out.append(
                    Relation(
                        expr=f"{var} {comparator} {upper}",
                        scope="loop",
                        origin="fact",
                        loop_id=loop_id,
                        note="counter advances once per iteration",
                    )
                )
            out.append(
                Relation(
                    expr=f"{var} >= 0",
                    scope="loop",
                    origin="fact",
                    loop_id=loop_id,
                    note="counter is non-negative",
                )
            )

        if kind == "sum" and not base:
            out.append(
                Relation(
                    expr=f"{var} >= 0",
                    scope="loop",
                    origin="fact",
                    loop_id=loop_id,
                    note="accumulator only grows",
                )
            )

    for write in body.get("mapping_update_facts") or []:
        name = write.get("var") or ""
        if name:
            out.append(
                Relation(
                    expr=f"sum({name}) >= 0",
                    scope="loop",
                    origin="fact",
                    loop_id=loop_id,
                    note="mapping totals stay non-negative",
                )
            )

    return out


def relations_from_traces(
    observation: LoopObservation,
    *,
    skip_caps_for: Optional[Set[str]] = None,
) -> List[Relation]:
    """
    Relations that held across every observed execution of the loop.

    Each candidate is checked against all runs, so a relation that fails once is
    reported as not holding rather than silently dropped.
    """
    out: List[Relation] = []
    runs = observation.run_count
    if runs == 0:
        return out

    excluded = set(skip_caps_for or set())

    trips = observation.trip_counts()
    if trips:
        highest = max(trips)
        rounded = _nearest_round_bound(highest)
        if rounded is not None and _reached_repeatedly(trips, highest):
            out.append(
                Relation(
                    expr=f"iterations <= {rounded}",
                    scope="loop",
                    origin="trace",
                    support=runs,
                    loop_id=observation.loop_id,
                    note=f"largest observed trip count was {highest}",
                )
            )

    for name in observation.variables():
        series = observation.series(name)
        if not series:
            continue

        flat = [v for run in series for v in run]
        for entry, exit_value in observation.entry_exit(name):
            if entry is not None:
                flat.append(entry)
            if exit_value is not None:
                flat.append(exit_value)
        if not flat:
            continue

        low, high = min(flat), max(flat)

        if low >= 0:
            out.append(
                Relation(
                    expr=f"{name} >= 0",
                    scope="loop",
                    origin="trace",
                    support=runs,
                    loop_id=observation.loop_id,
                    note="never observed below zero",
                )
            )

        rounded = _nearest_round_bound(high)
        if rounded is not None and name not in excluded and _peak_is_repeatable(observation, name, high):
            out.append(
                Relation(
                    expr=f"{name} <= {rounded}",
                    scope="loop",
                    origin="trace",
                    support=runs,
                    loop_id=observation.loop_id,
                    note=f"largest observed value was {high}",
                )
            )

        if _is_non_decreasing(series):
            out.append(
                Relation(
                    expr=f"{name} >= old({name})",
                    scope="loop",
                    origin="trace",
                    support=runs,
                    loop_id=observation.loop_id,
                    note="value never decreased between iterations",
                )
            )

        if _is_constant(series):
            out.append(
                Relation(
                    expr=f"{name} == old({name})",
                    scope="loop",
                    origin="trace",
                    support=runs,
                    loop_id=observation.loop_id,
                    note="value unchanged across the loop",
                )
            )

        for pair in _linear_with_index(observation, name):
            out.append(pair)

    for name in observation.variables():
        pairs = observation.entry_exit(name)
        usable = [(a, b) for a, b in pairs if a is not None and b is not None]
        if usable and all(b >= a for a, b in usable):
            out.append(
                Relation(
                    expr=f"{name} >= entry({name})",
                    scope="post",
                    origin="trace",
                    support=len(usable),
                    loop_id=observation.loop_id,
                    note="exit value never below the entry value",
                )
            )

    return out



def _reached_repeatedly(values: List[int], peak: int) -> bool:
    """
    Whether a maximum was seen often enough to look like a real limit.

    A value hit in a single execution usually reflects the arguments that one
    test happened to pass, not a property of the contract.
    """
    return sum(1 for v in values if v == peak) >= MIN_RUNS_FOR_CAP


def _peak_is_repeatable(observation: LoopObservation, name: str, peak: int) -> bool:
    hits = 0
    for run in observation.runs:
        values = [_as_int((it.get("values") or {}).get(name)) for it in run.get("iterations") or []]
        values.append(_as_int((run.get("entry") or {}).get(name)))
        values.append(_as_int((run.get("exit") or {}).get(name)))
        if any(v == peak for v in values if v is not None):
            hits += 1
    return hits >= MIN_RUNS_FOR_CAP

def _is_non_decreasing(series: List[List[int]]) -> bool:
    seen_change = False
    for run in series:
        for a, b in zip(run, run[1:]):
            if b < a:
                return False
            if b > a:
                seen_change = True
    return seen_change


def _is_constant(series: List[List[int]]) -> bool:
    for run in series:
        if len(set(run)) > 1:
            return False
    return any(len(run) > 1 for run in series)


def _linear_with_index(observation: LoopObservation, name: str) -> List[Relation]:
    """
    Compare a variable against the iteration counter.

    A counter incremented once per pass tracks the iteration number exactly,
    which is the strongest form of the counter pattern in Table I.
    """
    out: List[Relation] = []
    matches_index = True
    observed: List[int] = []

    for run in observation.runs:
        for it in run.get("iterations") or []:
            index = it.get("index")
            value = _as_int((it.get("values") or {}).get(name))
            if index is None or value is None:
                continue
            observed.append(value)
            if value != index - 1:
                matches_index = False

    enough_steps = len(observed) >= MIN_STEPS_FOR_COUNTER
    enough_variety = len(set(observed)) >= MIN_DISTINCT_FOR_COUNTER

    if matches_index and enough_steps and enough_variety:
        out.append(
            Relation(
                expr=f"{name} == iterations - 1",
                scope="loop",
                origin="trace",
                support=observation.run_count,
                loop_id=observation.loop_id,
                note="advances exactly once per iteration",
            )
        )
    return out


def dedupe(relations: Iterable[Relation]) -> List[Relation]:
    seen: Dict[Tuple[str, str, str], Relation] = {}
    for rel in relations:
        key = (rel.loop_id, rel.scope, rel.expr)
        current = seen.get(key)
        if current is None or rel.support > current.support:
            seen[key] = rel
    return sorted(seen.values(), key=lambda r: (r.loop_id, r.scope, r.expr))


def derive_for_loop(
    loop: Dict[str, Any],
    observation: Optional[LoopObservation],
    elements: Optional[Dict[str, List[int]]] = None,
) -> List[Relation]:
    relations = relations_from_facts(loop)
    if observation is not None:
        body = loop.get("body_summary") or {}
        indices = set(body.get("indices") or [])
        relations += relations_from_traces(observation, skip_caps_for=indices)
        relations = _drop_unreset_counter_bounds(loop, observation, relations)

    relations = dedupe(relations)

    # Compound and quantified forms are derived from the relations that
    # survived, so they inherit their evidence rather than adding claims.
    relations += quantified_relations(loop, elements)
    relations += conjunctive_relations(loop, relations)
    return dedupe(relations)


def _drop_unreset_counter_bounds(
    loop: Dict[str, Any],
    observation: LoopObservation,
    relations: List[Relation],
) -> List[Relation]:
    """
    Remove counter bounds for counters that carry over between entries.

    A counter compared against the loop bound is only limited by it when the
    counter starts from zero each time the loop is reached. One that keeps its
    value across outer iterations passes the bound on a later entry, so the
    relation is not an invariant even though it holds on the first pass.
    """
    body = loop.get("body_summary") or {}
    upper = str((loop.get("bounds") or {}).get("upper") or "").strip()
    if not upper:
        return relations

    carried_over: Set[str] = set()
    for fact in body.get("accumulator_facts") or []:
        var = fact.get("var") or ""
        if fact.get("kind") != "count" or not var:
            continue
        entries = [a for a, _ in observation.entry_exit(var) if a is not None]
        if entries and any(value != 0 for value in entries):
            carried_over.add(var)

    if not carried_over:
        return relations

    blocked = {f"{var} <= {upper}" for var in carried_over}
    return [r for r in relations if r.expr not in blocked]


def derive_for_contract(
    ir: Dict[str, Any],
    observations: Dict[str, LoopObservation],
    elements: Optional[Dict[str, List[int]]] = None,
) -> Dict[str, List[Relation]]:
    """
    Relations for every loop in the contract, keyed by function name.
    """
    contract = ir.get("contract") or ir
    out: Dict[str, List[Relation]] = {}
    for fn in contract.get("functions") or []:
        name = fn.get("name") or ""
        collected: List[Relation] = []
        for loop in fn.get("loops") or []:
            loop_id = loop.get("loop_id") or ""
            collected.extend(
                derive_for_loop(loop, observations.get(loop_id), elements)
            )
        if collected:
            out[name] = _merge_across_loops(collected)
    return out


def _merge_across_loops(relations: List[Relation]) -> List[Relation]:
    """
    Collapse relations that several loops in one function state identically.

    Two loops using the same index name would otherwise each contribute the
    same fact, which inflates the count without adding information.
    """
    best: Dict[Tuple[str, str], Relation] = {}
    for rel in relations:
        key = (rel.scope, rel.expr)
        current = best.get(key)
        if current is None or rel.support > current.support:
            best[key] = rel
    return sorted(best.values(), key=lambda r: (r.scope, r.expr))


QUANTIFIED_TYPE = "uint256"


def element_values(calls: Sequence[Any]) -> List[Tuple[Dict[str, List[int]], Dict[str, int]]]:
    """
    Array contents and scalar state at each function boundary.

    Each entry is one snapshot: the numeric arrays in index order, paired with
    the scalar values recorded at the same moment. Keeping them together is
    what allows an element to be compared against a scalar that held at the
    same time.
    """
    out: List[Tuple[Dict[str, List[int]], Dict[str, int]]] = []
    for call in calls or []:
        for snapshot in (call.pre, call.post):
            arrays: Dict[str, List[int]] = {}
            for name, entries in (snapshot.elements or {}).items():
                ordered: List[int] = []
                for index in sorted(entries):
                    token = str(entries[index]).strip()
                    # Base 0 would read an address as a number and invite
                    # claims about the ordering of account identifiers.
                    if token.lower().startswith("0x"):
                        ordered = []
                        break
                    try:
                        ordered.append(int(token))
                    except (TypeError, ValueError):
                        ordered = []
                        break
                if ordered:
                    arrays[name] = ordered

            scalars = {
                name: value
                for name, value in (snapshot.values or {}).items()
                if not name.endswith("_length") and isinstance(value, int)
            }
            if arrays:
                out.append((arrays, scalars))
    return out


def _written_arrays(loop: Dict[str, Any]) -> List[str]:
    """State arrays this loop writes through an index."""
    body = loop.get("body_summary") or {}
    names: List[str] = []
    for fact in body.get("array_update_facts") or []:
        if fact.get("scope") != "state" or fact.get("container") != "array":
            continue
        if not fact.get("key"):
            continue
        name = fact.get("var") or ""
        if name and name not in names:
            names.append(name)
    return names


def quantified_relations(
    loop: Dict[str, Any],
    observations: Optional[Sequence[Tuple[Dict[str, List[int]], Dict[str, int]]]],
) -> List[Relation]:
    """
    Claims over every element of an array the loop writes.

    Non-negativity is skipped for unsigned arrays, where it holds by typing and
    states nothing about the contract. What is left is a bound against a scalar
    that held at the same moment, and the ordering between neighbours, neither
    of which any type guarantees.
    """
    if not observations:
        return []

    out: List[Relation] = []
    loop_id = loop.get("loop_id") or ""

    for name in _written_arrays(loop):
        seen = [
            (arrays[name], scalars)
            for arrays, scalars in observations
            if arrays.get(name)
        ]
        if len(seen) < 2:
            continue

        header = f"\\forall k : {QUANTIFIED_TYPE} ; k < {name}.length ==> "

        # A scalar that dominated every element, every time it was recorded.
        candidates = set(seen[0][1])
        for _, scalars in seen[1:]:
            candidates &= set(scalars)
        for scalar in sorted(candidates):
            if scalar == name:
                continue
            if all(max(values) <= scalars[scalar] for values, scalars in seen):
                out.append(
                    Relation(
                        expr=f"{header}{name}[k] <= {scalar}",
                        scope="post",
                        origin="trace",
                        support=len(seen),
                        loop_id=loop_id,
                        note=f"held in all {len(seen)} observed states",
                    )
                )

        ordered = [values for values, _ in seen if len(values) >= 2]
        if len(ordered) >= 2 and all(
            all(a <= b for a, b in zip(values, values[1:])) for values in ordered
        ):
            out.append(
                Relation(
                    expr=(
                        f"\\forall k : {QUANTIFIED_TYPE} ; "
                        f"k + 1 < {name}.length ==> {name}[k] <= {name}[k + 1]"
                    ),
                    scope="post",
                    origin="trace",
                    support=len(ordered),
                    loop_id=loop_id,
                    note=f"non-decreasing in all {len(ordered)} observed states",
                )
            )

        if not _is_unsigned(loop, name) and all(
            all(v >= 0 for v in values) for values, _ in seen
        ):
            out.append(
                Relation(
                    expr=f"{header}{name}[k] >= 0",
                    scope="post",
                    origin="trace",
                    support=len(seen),
                    loop_id=loop_id,
                    note="signed array, no observed element was negative",
                )
            )
    return out


def _is_unsigned(loop: Dict[str, Any], name: str) -> bool:
    body = loop.get("body_summary") or {}
    for fact in body.get("array_update_facts") or []:
        if fact.get("var") == name:
            return str(fact.get("type") or "").startswith("uint")
    return True


def _mentions(expr: str, names: Set[str]) -> bool:
    tokens = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", expr or ""))
    return bool(tokens & names)


def conjunctive_relations(
    loop: Dict[str, Any], relations: Sequence[Relation]
) -> List[Relation]:
    """
    Pair a fact about the loop index with a fact about the loop body.

    Both halves already hold on their own, so the conjunction is sound. It is
    emitted because a compound property is what the conditional-splitting
    mutation is meant to take apart; on its own it adds nothing new.
    """
    body = loop.get("body_summary") or {}
    indices = {i for i in (body.get("indices") or []) if i}
    if not indices:
        return []

    # Prefer halves with no call or previous-state term. The mutation engine
    # rewrites these expressions, and a compound built from sum(...) or old(...)
    # gives it far less to work with than a plain comparison.
    loop_scoped = [
        r
        for r in relations
        if r.scope == "loop" and r.expr and "(" not in r.expr
    ]
    about_index = [r for r in loop_scoped if _mentions(r.expr, indices)]
    about_body = [r for r in loop_scoped if not _mentions(r.expr, indices)]
    if not about_index or not about_body:
        return []

    simplest = lambda r: (len(r.expr), r.expr)
    left = min(about_index, key=simplest)
    right = min(about_body, key=simplest)
    return [
        Relation(
            expr=f"{left.expr} && {right.expr}",
            scope="post",
            origin="composed",
            support=min(left.support, right.support),
            loop_id=loop.get("loop_id") or "",
            note="index fact and body fact, each independently supported",
        )
    ]
