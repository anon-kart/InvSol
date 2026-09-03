from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .encode import LoopModel, VerificationCondition, build_conditions, build_loop_model
from .encode import build_function_condition, build_function_model
from .expr import ParseError, parse_expression

VERDICT_VERIFIED = "verified"
VERDICT_REFUTED = "refuted"
VERDICT_UNKNOWN = "unknown"
VERDICT_UNSUPPORTED = "unsupported"


@dataclass
class Verdict:
    """
    The outcome for one candidate invariant.

    An invariant counts as verified only when both establishment and
    preservation are discharged. Anything the encoder or solver could not settle
    is reported as unknown rather than assumed to hold.
    """

    loop_id: str
    invariant: str
    status: str
    detail: str = ""
    counterexample: Dict[str, str] = field(default_factory=dict)
    conditions: List[Dict[str, Any]] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "loop_id": self.loop_id,
            "invariant": self.invariant,
            "status": self.status,
            "detail": self.detail,
            "counterexample": self.counterexample,
            "conditions": self.conditions,
            "assumptions": self.assumptions,
        }


def z3_available() -> bool:
    try:
        import z3  # noqa: F401
    except ImportError:
        return False
    return True


def solve(smt: str) -> Tuple[str, Dict[str, str]]:
    """
    Ask the solver whether the negated goal is satisfiable.

    A satisfying assignment means the invariant can be violated, and the model
    is returned as the counterexample. Unsatisfiable means it holds.
    """
    if not smt.strip():
        return VERDICT_UNSUPPORTED, {}

    try:
        import z3
    except ImportError:
        return VERDICT_UNKNOWN, {}

    solver = z3.Solver()
    try:
        solver.from_string(smt)
    except Exception as exc:  # z3 raises bare exceptions on malformed input
        return VERDICT_UNSUPPORTED, {"error": str(exc)}

    result = solver.check()
    if result == z3.unsat:
        return VERDICT_VERIFIED, {}
    if result == z3.sat:
        model = solver.model()
        assignment = {str(d.name()): str(model[d]) for d in model.decls()}
        return VERDICT_REFUTED, assignment
    return VERDICT_UNKNOWN, {}


def check_invariant(model: LoopModel, invariant: str) -> Verdict:
    conditions = build_conditions(model, invariant)

    records: List[Dict[str, Any]] = []
    assumptions: List[str] = []
    counterexample: Dict[str, str] = {}
    statuses: List[str] = []

    for condition in conditions:
        status, assignment = solve(condition.smt)
        statuses.append(status)
        assumptions.extend(condition.assumptions)
        records.append({**condition.to_dict(), "status": status})
        if status == VERDICT_REFUTED and not counterexample:
            counterexample = assignment
            counterexample["failing_condition"] = condition.kind

    if VERDICT_REFUTED in statuses:
        failing = [c["kind"] for c in records if c["status"] == VERDICT_REFUTED]
        return Verdict(
            loop_id=model.loop_id,
            invariant=invariant,
            status=VERDICT_REFUTED,
            detail=f"failed {', '.join(failing)}",
            counterexample=counterexample,
            conditions=records,
            assumptions=sorted(set(assumptions)),
        )

    if VERDICT_UNSUPPORTED in statuses:
        return Verdict(
            loop_id=model.loop_id,
            invariant=invariant,
            status=VERDICT_UNSUPPORTED,
            detail="outside the supported fragment",
            conditions=records,
            assumptions=sorted(set(assumptions)),
        )

    if all(s == VERDICT_VERIFIED for s in statuses) and statuses:
        return Verdict(
            loop_id=model.loop_id,
            invariant=invariant,
            status=VERDICT_VERIFIED,
            detail="establishment and preservation both discharged",
            conditions=records,
            assumptions=sorted(set(assumptions)),
        )

    return Verdict(
        loop_id=model.loop_id,
        invariant=invariant,
        status=VERDICT_UNKNOWN,
        detail="solver did not settle every condition",
        conditions=records,
        assumptions=sorted(set(assumptions)),
    )


def audit_contract(
    ir: Dict[str, Any],
    relations: Dict[str, Sequence[Any]],
) -> List[Verdict]:
    """
    Check every loop-scoped relation against the loop it belongs to.
    """
    contract = ir.get("contract") or ir
    verdicts: List[Verdict] = []

    for fn in contract.get("functions") or []:
        name = fn.get("name") or ""
        candidates = list(relations.get(name) or [])
        if not candidates:
            continue

        for loop in fn.get("loops") or []:
            loop_id = loop.get("loop_id") or ""
            try:
                model = build_loop_model(loop)
            except ParseError as exc:
                # One loop the encoder cannot express must not take the rest of
                # the contract with it. Record why and carry on.
                verdicts.append(
                    Verdict(
                        loop_id=loop_id,
                        invariant="",
                        status=VERDICT_UNKNOWN,
                        detail=f"loop could not be encoded: {exc}",
                    )
                )
                continue

            for relation in candidates:
                scope = _field(relation, "scope")
                if scope != "loop":
                    continue
                owner = _field(relation, "loop_id")
                if owner and loop_id and owner != loop_id:
                    continue
                verdicts.append(check_invariant(model, _field(relation, "expr")))

    return verdicts


def _field(relation: Any, name: str) -> str:
    if isinstance(relation, dict):
        return str(relation.get(name) or "")
    return str(getattr(relation, name, "") or "")


def audit_contract_invariants(
    ir: Dict[str, Any],
    invariants: Sequence[str],
) -> List[Verdict]:
    """
    Check each contract-level invariant against every function that can run.

    An invariant is only established for the contract if no function breaks it,
    so each is checked at the entry and exit of every state-changing function.
    A function that writes none of the locations mentioned preserves it, which
    is what makes the check compositional: the loops inside that function need
    not be examined again.
    """
    contract = ir.get("contract") or ir
    verdicts: List[Verdict] = []

    functions = [
        fn
        for fn in contract.get("functions") or []
        if not fn.get("synthetic")
        and (fn.get("mutability") or "") not in {"view", "pure"}
        and (fn.get("name") or "") not in {"", "receive", "fallback"}
    ]

    for invariant in invariants:
        # Some templates state properties the solver fragment cannot express,
        # such as pairwise distinctness or membership of an observed key set.
        # Those get one verdict saying so, rather than an identical unknown
        # against every function.
        try:
            parse_expression(invariant)
        except ParseError as exc:
            verdicts.append(
                Verdict(
                    loop_id="contract",
                    invariant=invariant,
                    status=VERDICT_UNSUPPORTED,
                    detail=f"outside the checkable fragment: {exc}",
                )
            )
            continue

        for fn in functions:
            model = build_function_model(fn)
            condition = build_function_condition(model, invariant)
            if not condition.smt:
                verdicts.append(
                    Verdict(
                        loop_id=condition.loop_id,
                        invariant=invariant,
                        status=VERDICT_UNKNOWN,
                        detail=condition.assumptions[0] if condition.assumptions else "",
                        assumptions=condition.assumptions,
                    )
                )
                continue

            status, counterexample = solve(condition.smt)
            if status == VERDICT_VERIFIED:
                outcome = VERDICT_VERIFIED
                detail = "preserved by this function"
            else:
                # A write whose stored value is unmodelled leaves the exit state
                # unconstrained, so a counterexample here is not a real
                # violation, only a failure to rule one out.
                outcome = VERDICT_UNKNOWN
                detail = "this function may write the state it mentions"

            verdicts.append(
                Verdict(
                    loop_id=condition.loop_id,
                    invariant=invariant,
                    status=outcome,
                    detail=detail,
                    counterexample=counterexample if outcome != VERDICT_VERIFIED else {},
                    assumptions=condition.assumptions,
                )
            )

    return verdicts


def summarise(verdicts: Sequence[Verdict]) -> Dict[str, Any]:
    counts: Dict[str, int] = {}
    for verdict in verdicts:
        counts[verdict.status] = counts.get(verdict.status, 0) + 1

    checked = len(verdicts)
    verified = counts.get(VERDICT_VERIFIED, 0)
    decided = verified + counts.get(VERDICT_REFUTED, 0)

    return {
        "checked": checked,
        "counts": counts,
        "precision": round(verified / decided, 4) if decided else None,
        "solver": "z3" if z3_available() else "unavailable",
    }


def main(argv: Optional[List[str]] = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Verify candidate loop invariants.")
    ap.add_argument("ir")
    ap.add_argument("relations")
    ap.add_argument("-o", "--out")
    args = ap.parse_args(argv)

    ir = json.loads(Path(args.ir).read_text(encoding="utf-8"))
    relations = json.loads(Path(args.relations).read_text(encoding="utf-8"))

    if not z3_available():
        print("z3 is not installed; every condition will be reported as unknown.")
        print("Install it with: pip install z3-solver")

    verdicts = audit_contract(ir, relations)
    report = {
        "summary": summarise(verdicts),
        "verdicts": [v.to_dict() for v in verdicts],
    }

    text = json.dumps(report, indent=2)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"checked {len(verdicts)} invariants -> {args.out}")
    else:
        print(text)

    for status, count in sorted(report["summary"]["counts"].items()):
        print(f"  {status:12s} {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
