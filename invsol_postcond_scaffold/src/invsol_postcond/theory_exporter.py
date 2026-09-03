from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence

from .models import ContractIR, InferenceResult

MUTATION_STRATEGIES = [
    "variable_substitution_mutations",
    "constraint_relaxation_mutations",
    "boundary_adjustment_mutations",
    "quantifier_instantiation_mutations",
    "conditional_splitting_mutations",
]

BORING_INTS = {"1", "-1", "2", "-2", "100"}


def _dedupe(items: Iterable[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        text = (item or "").strip()
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def _relations_for(relations: Optional[Dict[str, Sequence[Any]]], name: str) -> List[Any]:
    if not relations:
        return []
    return list(relations.get(name) or [])


def _expr_of(relation: Any) -> str:
    if isinstance(relation, dict):
        return str(relation.get("expr") or "")
    return str(getattr(relation, "expr", "") or "")


def _scope_of(relation: Any) -> str:
    if isinstance(relation, dict):
        return str(relation.get("scope") or "")
    return str(getattr(relation, "scope", "") or "")


def _integer_terms(fn: Any, relations: Sequence[Any]) -> List[str]:
    """
    Scalar terms the mutation engine can substitute into a predicate.

    Without these the engine has nothing to build alternative expressions from,
    which is why an empty section produces no candidate invariants.
    """
    terms: List[str] = []

    for loop in getattr(fn, "loops", []) or []:
        bounds = getattr(loop, "bounds", None)
        if bounds is not None:
            for value in (bounds.index, bounds.lower, bounds.upper):
                if value:
                    terms.append(str(value))

        terms.extend(getattr(loop, "indices", []) or [])
        terms.extend(getattr(loop, "accumulators", []) or [])
        for fact in getattr(loop, "accumulator_facts", []) or []:
            if fact.get("var"):
                terms.append(fact["var"])
            source = (fact.get("source") or {}).get("base")
            if source:
                terms.append(f"sum({source})")

    for param in getattr(fn, "params", []) or []:
        sol_type = str(getattr(param, "type", "") or "")
        if sol_type.startswith("uint") or sol_type.startswith("int"):
            name = getattr(param, "name", "")
            if name:
                terms.append(str(name))

    for relation in relations:
        expr = _expr_of(relation)
        for token in expr.replace("(", " ").replace(")", " ").split():
            if token.isdigit() and token not in BORING_INTS:
                terms.append(token)

    return [t for t in _dedupe(terms) if t not in BORING_INTS]


def _boolean_terms(fn: Any, relations: Sequence[Any]) -> List[str]:
    bools = [_expr_of(r) for r in relations]

    for index, loop in enumerate(getattr(fn, "loops", []) or []):
        bounds = getattr(loop, "bounds", None)
        if bounds is None:
            continue
        idx = bounds.index or "i"
        if bounds.lower:
            bools.append(f"{bounds.lower} <= {idx}")
        if bounds.upper:
            comparator = "<=" if bounds.inclusive_upper else "<"
            bools.append(f"{idx} {comparator} {bounds.upper}")

    return _dedupe(bools)


def render_theory_sol(
    contract: ContractIR,
    results: List[InferenceResult],
    *,
    contract_name: str,
    relations: Optional[Dict[str, Sequence[Any]]] = None,
) -> str:
    """
    Emit the theory contract that accompanies the info file.

    Each predicate carries a real body derived from the loop bounds, rather than
    returning a constant, so the predicate means something when it is called.
    """
    lines: List[str] = []
    lines.append("// SPDX-License-Identifier: UNLICENSED")

    pragma = getattr(contract, "pragma", None) or "0.8.0"
    lines.append(f"pragma solidity ^{pragma};")
    lines.append("")
    lines.append(f"contract T{contract_name} {{")
    lines.append("")

    for fn in contract.functions:
        for loop_idx, loop in enumerate(fn.loops):
            idx = loop.bounds.index or "i"
            lower = loop.bounds.lower or "0"
            upper = loop.bounds.upper

            lines.append(
                f"    function P_{fn.name}_loop{loop_idx}_lower(uint256 {idx})"
                " public pure returns (bool) {"
            )
            lines.append(f"        return {lower} <= {idx};")
            lines.append("    }")
            lines.append("")

            if upper and upper.isidentifier():
                op = "<=" if loop.bounds.inclusive_upper else "<"
                lines.append(
                    f"    function P_{fn.name}_loop{loop_idx}_upper(uint256 {idx}, uint256 {upper})"
                    " public pure returns (bool) {"
                )
                lines.append(f"        return {idx} {op} {upper};")
                lines.append("    }")
                lines.append("")

            lines.append(
                f"    function P_{fn.name}_loop{loop_idx}_monotone(uint256 current, uint256 previous)"
                " public pure returns (bool) {"
            )
            lines.append("        return current >= previous;")
            lines.append("    }")
            lines.append("")

            lines.append(
                f"    function P_{fn.name}_loop{loop_idx}_bounded(uint256 partial, uint256 total)"
                " public pure returns (bool) {"
            )
            lines.append("        return partial <= total;")
            lines.append("    }")
            lines.append("")

    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def render_theory_info(
    contract: ContractIR,
    results: List[InferenceResult],
    *,
    contract_name: str,
    relations: Optional[Dict[str, Sequence[Any]]] = None,
) -> str:
    """
    Emit the info file the mutation engine reads.

    The reader expects one Method block per function, and flushes the block it
    was building whenever a new Method marker appears. A file carrying only the
    global sections therefore describes no methods at all, which is why every
    method previously arrived with no postconditions to mutate.
    """
    pragma = getattr(contract, "pragma", None) or "0.8.0"

    posts_by_fn: Dict[str, List[str]] = {}
    for result in results or []:
        bucket = posts_by_fn.setdefault(result.function, [])
        for candidate in getattr(result, "candidates", []) or []:
            expr = getattr(candidate, "expr", None) or getattr(candidate, "expression", None)
            if expr:
                bucket.append(str(expr))

    lines: List[str] = []
    lines.append("== Package ==")
    lines.append(str(pragma))
    lines.append("")

    for fn in contract.functions:
        fn_relations = _relations_for(relations, fn.name)
        invariants = [_expr_of(r) for r in fn_relations if _scope_of(r) == "loop"]
        postconditions = [_expr_of(r) for r in fn_relations if _scope_of(r) == "post"]
        postconditions += posts_by_fn.get(fn.name, [])

        ints = _integer_terms(fn, fn_relations)
        bools = _boolean_terms(fn, fn_relations)

        if not (ints or bools or invariants or postconditions):
            continue

        lines.append("== Method ==")
        lines.append(fn.name)
        lines.append("")
        lines.append("== Static ==")
        lines.append("N")
        lines.append("")
        lines.append("== Integer expressions ==")
        lines.extend(ints)
        lines.append("")
        lines.append("== Boolean expressions ==")
        lines.extend(bools)
        lines.append("")

        pres = [str(r) for r in (getattr(fn, "requires", []) or [])]
        lines.append("== Preconditions ==")
        lines.extend(_dedupe(pres))
        lines.append("")
        lines.append("== Postconditions ==")
        lines.extend(_dedupe(postconditions))
        lines.append("")
        lines.append("== Invariants ==")
        lines.extend(_dedupe(invariants))
        lines.append("")
        lines.append("== Commands ==")
        lines.append(";".join(MUTATION_STRATEGIES))
        lines.append("")

    return "\n".join(lines)
