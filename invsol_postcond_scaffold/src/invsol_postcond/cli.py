# src/invsol_postcond/cli.py
from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Dict, List, Optional

from .ast_ir import parse_ast_ir
from .inference import infer_all
from .io_utils import read_json, read_text, write_text, as_path
from .models import InferenceResult
from .validators import validate_paths
from .info_exporter import render_info


# ----------------------------
# Arg parsing
# ----------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="invsol_postcond",
        description="Infer simple (now loop-aware) postconditions from AST IR and optional Foundry logs.",
    )
    p.add_argument("--ir", required=True, help="Path to AST IR JSON (e.g., examples/ir/output.json)")
    p.add_argument(
        "--logs",
        required=False,
        help="Optional path to Foundry logs text (e.g., examples/logs/foundry_logs.txt)",
    )
    p.add_argument("--pretty", action="store_true", help="Pretty-print JSON when not annotating Solidity")

    # Comment/annotation filtering
    p.add_argument(
        "--loops-only",
        action="store_true",
        help="When annotating Solidity, include only loop-scoped postconditions (hide function-scope facts).",
    )

    # Solidity annotation options
    p.add_argument("--sol", help="Path to Solidity file to annotate with inferred postconditions")
    p.add_argument(
        "--write-annotated",
        action="store_true",
        help="If set with --sol, writes <sol>.annotated.sol next to the source",
    )

    # New: output LoopSynth-compatible .info file
    p.add_argument(
        "--info-out",
        help="Write a LoopSynth-style .info file instead of (or in addition to) JSON/Solidity output",
    )

    return p


# ----------------------------
# JSON helpers
# ----------------------------

def _result_to_dict(r: InferenceResult) -> Dict:
    return {
        "function": r.function,
        "candidates": [
            {
                **({"expr": getattr(c, "expr", None)} if getattr(c, "expr", None) else {}),
                **({"description": getattr(c, "description", None)} if getattr(c, "description", None) else {}),
                "holds": getattr(c, "holds", True),
                "falsifying_runs": list(getattr(c, "falsifying_runs", [])),
                "origin": getattr(c, "origin", "ast"),
                "support": getattr(c, "support", 0),
                "scope": getattr(c, "scope", "function"),
                "loop_idx": getattr(c, "loop_idx", None),
            }
            for c in r.candidates
        ],
    }


def _results_as_json(results: List[InferenceResult], pretty: bool) -> str:
    data = [_result_to_dict(r) for r in results]
    return json.dumps(data, indent=2 if pretty else None)


# ----------------------------
# Legacy description → expr fallback
# ----------------------------

def _expr_from_description(desc: str) -> Optional[str]:
    d = (desc or "").strip()

    if d.startswith("no state writes"):
        return "NoStateWrites()"

    if d.startswith("precondition"):
        parts = d.split(":", 1)
        if len(parts) == 2:
            expr = parts[1].strip()
            return expr or None

    if d.startswith("loop index bounds:"):
        rhs = d.split(":", 1)[1].strip()
        return rhs or None

    if d.startswith("no external calls in function"):
        return "NoExternalCallsInFunction()"
    if d.startswith("function performs at least one external call"):
        return "HasExternalCallsInFunction()"

    if d.startswith("no external calls inside loop body"):
        return "NoExternalCallsInLoopBody()"
    if d.startswith("loop body contains at least one external call"):
        return "HasExternalCallsInLoopBody()"

    if d.startswith("emits event:"):
        rest = d.split(":", 1)[1].strip()
        ev = rest.split()[0].split("(")[0]
        if ev:
            return f"Emits({ev})"

    return None


# ----------------------------
# Build the map of comments to inject
# ----------------------------

def _compose_post_map(results: List[InferenceResult], *, loops_only: bool) -> Dict[str, List[str]]:
    post_map: Dict[str, List[str]] = {}

    for r in results:
        header_added = False
        out_lines: List[str] = []

        for c in r.candidates:
            scope = getattr(c, "scope", "function")
            loop_idx = getattr(c, "loop_idx", None)

            if loops_only and scope != "loop":
                continue

            expr = getattr(c, "expr", None) or _expr_from_description(getattr(c, "description", "") or "")
            if not expr:
                continue

            if not header_added:
                out_lines.append("// --- Inferred Postconditions ---")
                header_added = True

            if scope == "loop" and loop_idx is not None:
                out_lines.append(f"// POST_EXPR [loop#{loop_idx}]: {expr}")
            else:
                out_lines.append(f"// POST_EXPR: {expr}")

        if out_lines:
            post_map[r.function] = out_lines

    return post_map


# ----------------------------
# Solidity annotation
# ----------------------------

FUNC_HEADER_RE = re.compile(
    r"""^
        \s*function\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(
        |
        \s*constructor\s*\(
    """,
    re.VERBOSE,
)


def _annotate_solidity(sol_src: str, post_map: Dict[str, List[str]]) -> str:
    out_lines: List[str] = []
    lines = sol_src.splitlines()
    injected_for: Dict[str, bool] = {}

    for line in lines:
        m = FUNC_HEADER_RE.match(line)
        if m:
            leading = m.group(0).lstrip()
            is_function = leading.startswith("function")
            fn_name = m.group("name") if is_function else "constructor"

            to_inject = post_map.get(fn_name)
            if to_inject and not injected_for.get(fn_name, False):
                if out_lines and out_lines[-1].strip() != "":
                    out_lines.append("")
                out_lines.extend(to_inject)
                injected_for[fn_name] = True

        out_lines.append(line)

    return "\n".join(out_lines) + ("" if sol_src.endswith("\n") else "\n")


# ----------------------------
# Main
# ----------------------------

def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    # Validate inputs
    ir_path, maybe_logs_path = validate_paths(args.ir, args.logs)

    # Load & parse IR
    ir_json = read_json(ir_path)
    contract = parse_ast_ir(ir_json)

    # Load logs only if provided
    logs_text = read_text(maybe_logs_path) if maybe_logs_path else ""

    # Infer postconditions
    results = infer_all(contract, logs_text)

    # Handle Solidity annotation
    if args.sol:
        sol_path = as_path(args.sol)
        try:
            sol_src = read_text(sol_path)
        except Exception as e:
            print(f"error: failed reading Solidity source '{args.sol}': {e}", file=sys.stderr)
            return 2

        post_map = _compose_post_map(results, loops_only=bool(args.loops_only))
        annotated = _annotate_solidity(sol_src, post_map)

        if args.write_annotated:
            out_path = sol_path.with_suffix(".annotated.sol")
            write_text(out_path, annotated)
            print(str(out_path))
        else:
            print(annotated)
        return 0

    # Handle .info file generation
    if args.info_out:
        try:
            info_txt = render_info(contract, results, package_name=contract.name)
            write_text(args.info_out, info_txt)
            print(f"[+] Wrote LoopSynth-compatible info file → {args.info_out}")
        except Exception as e:
            print(f"error: failed to render .info file: {e}", file=sys.stderr)
            return 3
        return 0

    # Otherwise, default to JSON output
    print(_results_as_json(results, pretty=args.pretty))
    return 0


if __name__ == "__main__":
    sys.exit(main())
