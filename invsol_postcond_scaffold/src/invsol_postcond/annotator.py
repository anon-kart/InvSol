from __future__ import annotations

import re
from typing import Dict, List, Tuple

from .models import InferenceResult, CandidatePostcondition, ContractIR, ASTFunctionIR


# ---------- helpers ----------

def _group_results_by_function(results: List[InferenceResult]) -> Dict[str, InferenceResult]:
    return {r.function: r for r in results}


def _format_candidate(c: CandidatePostcondition) -> str:
    """
    Render one candidate into a compact, single-line Solidity comment body.
    Keep it short so it doesn't clutter source.
    """
    status = "✓" if c.holds else "×"
    return f"{status} {c.description}"


def _postcondition_block(fn_ir: ASTFunctionIR, fn_res: InferenceResult | None) -> List[str]:
    """
    Produce a /** ... */ style block for a function header.
    Includes function/loop facts that 'hold' (true).
    """
    lines: List[str] = []
    lines.append("/**")
    lines.append(f" * Postconditions for {fn_ir.name}:")
    added_any = False

    # List loop bounds & external-call markers from IR (structural facts).
    for lp in fn_ir.loops:
        # Bounds (split into two lines if we emitted in separate candidates)
        idx = (lp.bounds.index or "").strip()
        lower = (lp.bounds.lower or "").strip()
        upper = (lp.bounds.upper or "").strip()
        incl = lp.bounds.inclusive_upper
        if idx and lower:
            lines.append(f" *   - ✓ loop index bound: {lower} ≤ {idx}")
            added_any = True
        if idx and upper:
            op = "≤" if incl else "<"
            lines.append(f" *   - ✓ loop index bound: {idx} {op} {upper}")
            added_any = True
        # External call marker
        if lp.has_external_call_in_loop:
            lines.append(" *   - ✓ loop body contains at least one external call")
            added_any = True
        else:
            lines.append(" *   - ✓ no external calls inside loop body")
            added_any = True

    # Emit AST-level facts (events/no writes/no external call at function-level) from inference.
    if fn_res:
        for c in fn_res.candidates:
            if c.holds:
                lines.append(f" *   - {_format_candidate(c)}")
                added_any = True

    if not added_any:
        lines.append(" *   (no postconditions inferred)")

    lines.append(" */")
    return lines


def _inject_above_line(src_lines: List[str], insert_at: int, block_lines: List[str]) -> None:
    """Insert a block of lines *above* the given index."""
    for i, ln in enumerate(block_lines):
        src_lines.insert(insert_at + i, ln)


def _find_function_headers(src: str, contract: ContractIR) -> Dict[str, int]:
    """
    Best-effort regex find of Solidity function header lines.
    Returns: { function_name -> line_index }
    """
    lines = src.splitlines()
    idx_map: Dict[str, int] = {}

    # Regex tries to match function keyword and a name that appears in IR
    # e.g., 'function sumNumbersBounded(' or 'function sumNumbersBounded (' with modifiers
    fn_names = {f.name for f in contract.functions}
    # very permissive: captures `function <name>(`
    fn_re = re.compile(r"\bfunction\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")

    for i, l in enumerate(lines):
        m = fn_re.search(l)
        if not m:
            continue
        name = m.group(1)
        if name in fn_names and name not in idx_map:
            idx_map[name] = i

    return idx_map


def annotate_solidity(solidity_text: str, contract: ContractIR, results: List[InferenceResult]) -> str:
    """
    Insert /** Postconditions ... */ blocks above each function header found in `solidity_text`.
    We keep it simple and robust: only annotate function headers we can locate by name.
    """
    grouped = _group_results_by_function(results)
    header_line_by_fn = _find_function_headers(solidity_text, contract)
    lines = solidity_text.splitlines()

    # We insert from bottom to top so earlier insertions don't shift later positions
    items: List[Tuple[int, List[str]]] = []

    # Map function IRs by name for easy lookup
    fn_ir_map: Dict[str, ASTFunctionIR] = {f.name: f for f in contract.functions}

    for fn_name, header_line in header_line_by_fn.items():
        fn_ir = fn_ir_map.get(fn_name)
        fn_res = grouped.get(fn_name)
        if not fn_ir:
            continue
        block = _postcondition_block(fn_ir, fn_res)
        items.append((header_line, block))

    # sort by line number descending
    items.sort(key=lambda x: x[0], reverse=True)

    for header_line, block in items:
        _inject_above_line(lines, header_line, block)

    return "\n".join(lines)
