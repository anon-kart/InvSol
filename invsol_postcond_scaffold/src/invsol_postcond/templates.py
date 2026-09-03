from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Set

MIN_SUPPORT = 2


@dataclass
class DynamicInvariant:
    """One candidate produced by a named template, with its evidence."""

    template: str
    expr: str
    scope: str
    function: str = ""
    support: int = 0
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "template": self.template,
            "expr": self.expr,
            "scope": self.scope,
            "function": self.function,
            "support": self.support,
            "note": self.note,
        }


def _state_types(ir: Dict[str, Any]) -> Dict[str, str]:
    contract = ir.get("contract") or ir
    state = contract.get("state") or {}
    out: Dict[str, str] = {}
    for variable in state.get("variables") or []:
        if variable.get("name"):
            out[variable["name"]] = str(variable.get("type") or "")
    return out


def _mapping_value_types(ir: Dict[str, Any]) -> Dict[str, str]:
    contract = ir.get("contract") or ir
    state = contract.get("state") or {}
    return {
        entry["name"]: str(entry.get("value") or "")
        for entry in (state.get("mappings") or [])
        if entry.get("name")
    }


def _functions_with_external_calls(ir: Dict[str, Any]) -> Set[str]:
    contract = ir.get("contract") or ir
    out: Set[str] = set()
    for fn in contract.get("functions") or []:
        if fn.get("external_calls"):
            out.add(fn.get("name") or "")
    return out


def monotonic_counter(calls: Sequence[Any]) -> List[DynamicInvariant]:
    """
    Values that never decrease from one call boundary to the next.

    A counter that only ever grows is the shape InvCon calls MonotonicCounter.
    A value that never changed at all is excluded, because reporting it as
    monotonic would say nothing about the contract.
    """
    seen: Dict[str, int] = {}
    grew: Dict[str, bool] = {}

    for call in calls:
        for name, after in call.post.values.items():
            before = call.pre.values.get(name)
            if before is None:
                continue
            if after < before:
                seen[name] = -1
                continue
            if seen.get(name, 0) >= 0:
                seen[name] = seen.get(name, 0) + 1
                grew[name] = grew.get(name, False) or after > before

    out: List[DynamicInvariant] = []
    for name, support in sorted(seen.items()):
        if support < MIN_SUPPORT or not grew.get(name):
            continue
        out.append(
            DynamicInvariant(
                template="MonotonicCounter",
                expr=f"{name} >= old({name})",
                scope="contract",
                support=support,
            )
        )
    return out


def allowance_non_negativity(
    calls: Sequence[Any], value_types: Dict[str, str]
) -> List[DynamicInvariant]:
    """
    Mapping values that stay non-negative even though they are reduced.

    On an unsigned mapping this is only worth reporting once a decrease has
    actually been observed, since otherwise the bound holds by typing alone and
    carries no information about the contract.
    """
    support: Dict[str, int] = {}
    decreased: Dict[str, bool] = {}
    negative: Set[str] = set()

    for call in calls:
        for name, after in call.post.mappings.items():
            before = call.pre.mappings.get(name) or {}
            for key, value in after.items():
                if value < 0:
                    negative.add(name)
                    continue
                support[name] = support.get(name, 0) + 1
                if key in before and value < before[key]:
                    decreased[name] = True

    out: List[DynamicInvariant] = []
    for name in sorted(support):
        if name in negative or not decreased.get(name):
            continue
        if support[name] < MIN_SUPPORT:
            continue
        out.append(
            DynamicInvariant(
                template="AllowanceNonNegativity",
                expr=f"forall k in observed({name}): {name}[k] >= 0",
                scope="contract",
                support=support[name],
                note=f"value type {value_types.get(name, 'unknown')}, decrease observed",
            )
        )
    return out


def distinct_address_precondition(
    calls: Sequence[Any], state_types: Dict[str, str]
) -> List[DynamicInvariant]:
    """
    Address arrays whose observed entries were never repeated.

    Duplicate entries are what make a payout loop pay someone twice, so an
    array that stays free of them is worth stating.
    """
    support: Dict[str, int] = {}
    repeated: Set[str] = set()

    for call in calls:
        for snapshot in (call.pre, call.post):
            for name, entries in snapshot.elements.items():
                if "address" not in state_types.get(name, ""):
                    continue
                values = list(entries.values())
                if len(values) < 2:
                    continue
                if len(set(values)) != len(values):
                    repeated.add(name)
                    continue
                support[name] = support.get(name, 0) + 1

    return [
        DynamicInvariant(
            template="DistinctAddressPrecondition",
            expr=f"forall j, k (j != k): {name}[j] != {name}[k]",
            scope="contract",
            support=support[name],
        )
        for name in sorted(support)
        if name not in repeated and support[name] >= MIN_SUPPORT
    ]


def sum_mapping_bound(calls: Sequence[Any]) -> List[DynamicInvariant]:
    """
    Mappings whose observed entries always summed to at most some scalar.

    This is the SumMappingBound shape from Section 3.4.1, the mapping analogue
    of totalSupply bounding the balances.
    """
    support: Dict[str, int] = {}
    broken: Set[str] = set()

    for call in calls:
        for snapshot in (call.pre, call.post):
            for name, entries in snapshot.mappings.items():
                if not entries:
                    continue
                total = sum(entries.values())
                for scalar, value in snapshot.values.items():
                    if scalar.endswith("_length"):
                        continue
                    pair = f"{name}|{scalar}"
                    if total > value:
                        broken.add(pair)
                    else:
                        support[pair] = support.get(pair, 0) + 1

    out: List[DynamicInvariant] = []
    for pair in sorted(support):
        if pair in broken or support[pair] < MIN_SUPPORT:
            continue
        name, scalar = pair.split("|", 1)
        out.append(
            DynamicInvariant(
                template="SumMappingBound",
                expr=f"sum(observed({name})) <= {scalar}",
                scope="contract",
                support=support[pair],
            )
        )
    return out


def reentrancy_guarded_state(
    calls: Sequence[Any], with_external_calls: Set[str]
) -> List[DynamicInvariant]:
    """
    State a function leaves untouched despite making an external call.

    Section 3.4.1 asks for state that does not move across an external call
    boundary, which is what makes a reentrant re-entry harmless.
    """
    support: Dict[str, int] = {}
    changed: Set[str] = set()

    for call in calls:
        if call.function not in with_external_calls:
            continue
        for name, before in call.pre.values.items():
            after = call.post.values.get(name)
            if after is None:
                continue
            pair = f"{call.function}|{name}"
            if after != before:
                changed.add(pair)
            else:
                support[pair] = support.get(pair, 0) + 1

    out: List[DynamicInvariant] = []
    for pair in sorted(support):
        if pair in changed or support[pair] < MIN_SUPPORT:
            continue
        function, name = pair.split("|", 1)
        out.append(
            DynamicInvariant(
                template="ReentrancyGuardedState",
                expr=f"{name} == old({name})",
                scope="function",
                function=function,
                support=support[pair],
                note="held across an external call",
            )
        )
    return out


def valid_sender_constraint(
    calls: Sequence[Any], state_types: Dict[str, str]
) -> List[DynamicInvariant]:
    """
    Mappings whose observed keys always came from a recorded address array.

    A mapping keyed by an authorised set is the ValidSenderConstraint shape:
    every key that was touched also appears in the array the contract keeps.
    """
    support: Dict[str, int] = {}
    outside: Set[str] = set()

    for call in calls:
        # Only the post-state counts. A function that records a caller writes
        # the mapping entry before appending to the array, so its entry
        # snapshot shows a key that is not yet a member.
        for snapshot in (call.post,):
            arrays = {
                name: set(entries.values())
                for name, entries in snapshot.elements.items()
                if "address" in state_types.get(name, "") and entries
            }
            for mapping, entries in snapshot.mappings.items():
                if not entries:
                    continue
                for array, members in arrays.items():
                    pair = f"{mapping}|{array}"
                    if set(entries) <= members:
                        support[pair] = support.get(pair, 0) + 1
                    else:
                        outside.add(pair)

    out: List[DynamicInvariant] = []
    for pair in sorted(support):
        if pair in outside or support[pair] < MIN_SUPPORT:
            continue
        mapping, array = pair.split("|", 1)
        out.append(
            DynamicInvariant(
                template="ValidSenderConstraint",
                expr=f"forall k in observed({mapping}): k in {array}",
                scope="contract",
                support=support[pair],
            )
        )
    return out


def explore(calls: Sequence[Any], ir: Dict[str, Any]) -> List[DynamicInvariant]:
    """
    Run every template over the observed calls.

    Each template needs the same relation to hold on at least MIN_SUPPORT
    observations and never to be contradicted, so a single lucky execution
    cannot produce a candidate.
    """
    state_types = _state_types(ir)
    value_types = _mapping_value_types(ir)
    external = _functions_with_external_calls(ir)

    found: List[DynamicInvariant] = []
    found.extend(monotonic_counter(calls))
    found.extend(allowance_non_negativity(calls, value_types))
    found.extend(distinct_address_precondition(calls, state_types))
    found.extend(sum_mapping_bound(calls))
    found.extend(reentrancy_guarded_state(calls, external))
    found.extend(valid_sender_constraint(calls, state_types))
    return found


def tally(found: Sequence[DynamicInvariant]) -> Dict[str, int]:
    counts: Dict[str, int] = {
        "MonotonicCounter": 0,
        "AllowanceNonNegativity": 0,
        "DistinctAddressPrecondition": 0,
        "SumMappingBound": 0,
        "ReentrancyGuardedState": 0,
        "ValidSenderConstraint": 0,
    }
    for item in found:
        counts[item.template] = counts.get(item.template, 0) + 1
    return counts
