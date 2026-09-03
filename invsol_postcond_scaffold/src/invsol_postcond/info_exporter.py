# src/invsol_postcond/info_exporter.py
from __future__ import annotations

import re
from typing import List, Set
from .models import ContractIR, InferenceResult, CandidatePostcondition


# ---------- helper functions ----------

def _collect_int_symbols(contract: ContractIR, fn_name: str, cand: List[CandidatePostcondition]) -> List[str]:
    """
    Build the '== Integer expressions ==' section.
    Keeps numeric, loop, and accumulator variables, filters symbolic noise.
    """
    ints: Set[str] = set()

    # --- 1) From function IR (params, loop indices, accumulators)
    fn_ir = next((f for f in contract.functions if f.name == fn_name), None)
    if fn_ir:
        for p in fn_ir.params:
            name = p.get("name") or p.get("identifier") or ""
            if name:
                ints.add(name)

        for lp in fn_ir.loops:
            if lp.bounds.index:
                ints.add(lp.bounds.index)
            for idx in lp.indices or []:
                ints.add(idx)
            for acc in lp.accumulators or []:
                tok = str(acc).split()[0]
                if tok:
                    ints.add(tok)

    # --- 2) From candidate expressions
    for c in cand:
        e = (c.expr or "").strip()
        for token in e.replace("(", " ").replace(")", " ").replace(";", " ").replace(",", " ").split():
            if token.isidentifier():
                ints.add(token)

    # --- 3) Remove noise / non-numeric identifiers
    blacklist = {
        "Guard", "NoStateWrites", "NoExternalCalls", "HasExternalCalls",
        "HasExternalCallsInLoop", "NoExternalCallsInLoop", "Accumulator", "Update",
        "FoundAt", "SumResult", "MatrixDot", "Filled", "Sorted", "Emits",
        "N", "UpdatesArray", "Accumulated", "UpdatedDeposit", "threshold"
    }
    ints = {x for x in ints if x not in blacklist}

    # --- 4) Add placeholders and constants
    base = ["#", "x", "y"]
    ints.update(base)
    consts = ["1", "-1", "2", "-2", "100"]

    # --- 5) Preserve order
    out: List[str] = ["#"]
    for s in sorted(ints):
        if s != "#":
            out.append(s)
    out.extend(consts)

    # --- 6) Simple composites
    syms = [s for s in out if s not in ("#", "1", "-1", "2", "-2", "100")]
    if len(syms) >= 2:
        a, b = syms[0], syms[1]
        out.extend([f"{a} + {b}", f"{a} * {b}", f"{a} - {b}"])

    # --- 7) Canonical templates
    out.extend(["# + 1", "# - 1", "# * #", "# / #"])

    # --- 8) Deduplicate while preserving order
    seen: Set[str] = set()
    final: List[str] = []
    for it in out:
        if it not in seen:
            seen.add(it)
            final.append(it)

    return final


def _collect_bool_exprs(int_exprs: List[str], cands: List[CandidatePostcondition]) -> List[str]:
    """
    Collect both schema-style and candidate-derived boolean expressions.
    """
    out: List[str] = [
        "# > 0", "# < #", "# >= #", "# <= #", "# == #", "# != #"
    ]

    for c in cands:
        e = (c.expr or "").strip()
        if not e or e.endswith("()"):
            continue
        if any(op in e for op in ("<", ">", "==", "<=", ">=", "!=")):
            out.append(e)

    seen: Set[str] = set()
    final: List[str] = []
    for b in out:
        if b not in seen:
            seen.add(b)
            final.append(b)
    return final


def _extract_pre_post_inv(cands: List[CandidatePostcondition], fn_ir=None):
    """
    Separate candidates into preconditions, postconditions, and invariants.
    Adds heuristic preconditions:
      - extracts require()/assert() contents
      - lifts simple loop bounds as implicit preconditions
    """
    pre: List[str] = []
    post: List[str] = []
    invs: List[str] = []

    # --- 1) From candidate expressions ---
    for c in cands:
        e = (c.expr or "").strip()
        if not e:
            continue

        if e.startswith("require(") or "require" in e:
            inner = re.findall(r"require\s*\(([^)]+)\)", e)
            for cond in inner:
                pre.append(cond.strip() + ";")
        elif e.startswith("assert("):
            inner = re.findall(r"assert\s*\(([^)]+)\)", e)
            for cond in inner:
                pre.append(cond.strip() + ";")
        elif e.startswith("(") and e.endswith(")"):
            pre.append(e.strip("()") + ";")
        elif e.startswith(("Emits(", "Accumulator(", "Update(", "Guard(", "NoStateWrites(", "HasExternalCalls(",
                            "NoExternalCalls(", "NoExternalCallsInLoop(", "HasExternalCallsInLoop(", "UpdatesArray(")):
            post.append(e + ";")
        elif e.endswith("()"):
            invs.append(e + ";")
        else:
            post.append(e + ";")

    # --- 2) Add heuristic preconditions from function IR ---
    if fn_ir:
        for lp in getattr(fn_ir, "loops", []):
            idx = lp.bounds.index or "i"
            lo = lp.bounds.lower or "0"
            hi = lp.bounds.upper or "N"
            op = "<=" if lp.bounds.inclusive_upper else "<"
            # Common preconditions: index bounds
            pre.append(f"{lo} <= {idx};")
            pre.append(f"{idx} {op} {hi};")

    # --- deduplicate while preserving order ---
    def _dedupe(xs: List[str]) -> List[str]:
        seen = set()
        out = []
        for x in xs:
            if x not in seen:
                seen.add(x)
                out.append(x)
        return out

    return _dedupe(pre), _dedupe(post), _dedupe(invs)


def render_info(
    contract: ContractIR,
    results: List[InferenceResult],
    *,
    package_name: str | None = None,
) -> str:
    """
    Render all functions into .info blocks suitable for LoopSynth.
    Produces clean, structured output with heuristic preconditions.
    """
    lines: List[str] = []
    pkg = package_name or contract.name or "InvSolPackage"

    for r in results:
        fn_name = r.function
        cands = r.candidates
        fn_ir = next((f for f in contract.functions if f.name == fn_name), None)

        int_exprs = _collect_int_symbols(contract, fn_name, cands)
        bool_exprs = _collect_bool_exprs(int_exprs, cands)
        pre, post, invs = _extract_pre_post_inv(cands, fn_ir)

        lines.append("== Package ==")
        lines.append(pkg)
        lines.append("== Method ==")
        lines.append(fn_name)
        lines.append("== Static ==")
        lines.append("N")

        lines.append("== Integer expressions ==")
        lines.extend(int_exprs)

        lines.append("== Boolean expressions ==")
        lines.extend(bool_exprs)

        lines.append("== Preconditions ==")
        lines.extend(pre if pre else [";"])

        lines.append("== Postconditions ==")
        lines.extend(post if post else [";"])

        lines.append("== Invariants ==")
        lines.extend(invs if invs else [";"])

        lines.append("== Commands ==")

        # --- reconstruct loop structure ---
        if fn_ir and fn_ir.loops:
            for lp in fn_ir.loops:
                idx = lp.bounds.index or "i"
                lo = lp.bounds.lower or "0"
                hi = lp.bounds.upper or "N"
                op = "<=" if lp.bounds.inclusive_upper else "<"

                if lp.accumulators:
                    acc = str(lp.accumulators[0]).split()[0]
                    lines.append(f"for (uint {idx} = {lo}; {idx} {op} {hi}; {idx}++) {{ {acc} += ...; }}")
                elif lp.mapping_updates:
                    mv = lp.mapping_updates[0]
                    lines.append(f"for (uint {idx} = {lo}; {idx} {op} {hi}; {idx}++) {{ {mv}[...] = ...; }}")
                else:
                    lines.append(f"for (uint {idx} = {lo}; {idx} {op} {hi}; {idx}++) {{ /* loop body */ }}")
        else:
            lines.append("// (no commands reconstructed)")

        lines.append("")  # blank line between function blocks

    return "\n".join(lines)
