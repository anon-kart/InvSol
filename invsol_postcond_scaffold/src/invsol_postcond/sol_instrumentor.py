# src/invsol_postcond/sol_instrumentor.py
from __future__ import annotations

import os
import re
from typing import Dict, List, Tuple, Iterable, Optional, Any


# ----------------------------
# Helpers: pick good postconds
# ----------------------------
def _iter_post_exprs_for_function(results: List[Any], fn_name: str) -> List[str]:
    """
    Extract candidate postconditions for a given function name from `results`.

    We assume `results` is a List[InferenceResult] where:
      - r.function is the function name
      - r.candidates is a list, each candidate may have:
          expr: str
          holds: bool
          support: int
    """
    exprs: List[str] = []
    for r in results:
        if getattr(r, "function", None) != fn_name:
            continue
        for c in getattr(r, "candidates", []) or []:
            expr = getattr(c, "expr", None)
            if not expr or not isinstance(expr, str):
                continue
            holds = getattr(c, "holds", True)
            support = getattr(c, "support", 0)
            if holds is not True:
                continue
            # keep only supported candidates (tune as you like)
            if support < 3:
                continue

            cleaned = expr.strip().rstrip(";").strip()
            if not cleaned:
                continue

            # very light sanity: must look boolean-ish
            if not any(op in cleaned for op in ("<", ">", "<=", ">=", "==", "!=", "&&", "||", "!", "true", "false")):
                # allow predicate calls like P_xxx(...)
                if "(" not in cleaned:
                    continue

            # forbid multiline / braces
            if "\n" in cleaned or "{" in cleaned or "}" in cleaned:
                continue

            exprs.append(cleaned)

    # de-dup while preserving order
    seen = set()
    out: List[str] = []
    for e in exprs:
        if e not in seen:
            seen.add(e)
            out.append(e)
    return out


def _group_postconds(results: List[Any]) -> Dict[str, List[str]]:
    """
    Map fn_name -> list[expr]
    """
    fn_map: Dict[str, List[str]] = {}
    for r in results:
        fn = getattr(r, "function", None)
        if not fn or not isinstance(fn, str):
            continue
        fn_map.setdefault(fn, [])
    for fn in list(fn_map.keys()):
        fn_map[fn] = _iter_post_exprs_for_function(results, fn)
    return fn_map


# ----------------------------
# Helpers: Solidity text edits
# ----------------------------
def _find_matching_brace(src: str, open_brace_idx: int) -> Optional[int]:
    """
    Given src and index of '{', return index of matching '}'.
    Very simple brace matching (no string/comment awareness).
    """
    if open_brace_idx < 0 or open_brace_idx >= len(src) or src[open_brace_idx] != "{":
        return None

    depth = 0
    for i in range(open_brace_idx, len(src)):
        ch = src[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
    return None


def _find_function_body_ranges(src: str) -> Dict[str, Tuple[int, int]]:
    """
    Return mapping of function-name -> (body_open_idx, body_close_idx),
    where body_open_idx points to '{' and body_close_idx points to matching '}'.

    Handles:
      - function <name>(...) { ... }
      - constructor(...) { ... }

    Skips declarations without body: `function f(...) external;`
    """
    ranges: Dict[str, Tuple[int, int]] = {}

    # We find candidates for "function NAME" and "constructor"
    # then locate the first '{' after the signature.
    func_pat = re.compile(r"\bfunction\s+([A-Za-z_][A-Za-z0-9_]*)\b", re.MULTILINE)
    ctor_pat = re.compile(r"\bconstructor\b", re.MULTILINE)

    def scan_matches(matches: Iterable[Tuple[str, int]]) -> None:
        for name, start in matches:
            # find first '{' after this point
            brace = src.find("{", start)
            if brace == -1:
                continue

            # ensure this is not a declaration ending with ';' before '{'
            semi = src.find(";", start, brace)
            if semi != -1:
                # there's a ';' before '{' → declaration, skip
                continue

            close = _find_matching_brace(src, brace)
            if close is None:
                continue

            # If multiple functions share same name (overloads), keep first only
            ranges.setdefault(name, (brace, close))

    func_matches = [(m.group(1), m.start()) for m in func_pat.finditer(src)]
    ctor_matches = [("constructor", m.start()) for m in ctor_pat.finditer(src)]

    scan_matches(func_matches)
    scan_matches(ctor_matches)
    return ranges


def _inject_asserts_into_body(
    src: str,
    body_open: int,
    body_close: int,
    asserts: List[str],
    *,
    indent: str = "        ",
) -> str:
    """
    Inject assert(<expr>); lines just before the closing brace of a function body.
    """
    if not asserts:
        return src

    insertion_point = body_close  # index of '}'
    block_lines = []
    block_lines.append("")
    block_lines.append(f"{indent}// --- InvSol inferred postconditions (injected) ---")
    for e in asserts:
        block_lines.append(f"{indent}assert({e});")
    block_lines.append(f"{indent}// --- end injected ---")
    block_lines.append("")

    inject_text = "\n".join(block_lines)

    return src[:insertion_point] + inject_text + src[insertion_point:]


def _cap_postconds(exprs: List[str], cap: int) -> List[str]:
    if cap <= 0:
        return []
    if len(exprs) <= cap:
        return exprs
    return exprs[:cap]


# ----------------------------
# Public API
# ----------------------------
def inject_postconditions(sol_in_path: str, results: List[Any], sol_out_path: str) -> None:
    """
    Read Solidity source from `sol_in_path`, inject inferred postconditions from `results`
    as Solidity `assert(...)` statements at the end of each function, and write to `sol_out_path`.

    Notes:
    - This is a best-effort text-based instrumentor.
    - It does NOT parse Solidity fully; it relies on brace matching.
    - It skips function declarations without bodies.
    """
    if not os.path.exists(sol_in_path):
        raise FileNotFoundError(f"Solidity input not found: {sol_in_path}")

    with open(sol_in_path, "r", encoding="utf-8") as f:
        src = f.read()

    fn_to_posts = _group_postconds(results)

    # Find function body ranges
    body_ranges = _find_function_body_ranges(src)

    # We must inject from the end backwards so indices don't shift
    injections: List[Tuple[int, int, str, List[str]]] = []
    for fn_name, (bopen, bclose) in body_ranges.items():
        posts = fn_to_posts.get(fn_name, [])
        posts = _cap_postconds(posts, cap=8)  # cap per-function
        if posts:
            injections.append((bopen, bclose, fn_name, posts))

    # sort by close brace descending
    injections.sort(key=lambda x: x[1], reverse=True)

    instrumented = src
    for bopen, bclose, fn_name, posts in injections:
        # choose indent: try to infer from line containing the closing brace
        # default "        " (8 spaces)
        indent = "        "
        line_start = instrumented.rfind("\n", 0, bclose)
        if line_start != -1:
            # count whitespace after newline
            j = line_start + 1
            while j < len(instrumented) and instrumented[j] in (" ", "\t"):
                j += 1
            indent = instrumented[line_start + 1 : j] or indent

        instrumented = _inject_asserts_into_body(
            instrumented, bopen, bclose, posts, indent=indent
        )

    os.makedirs(os.path.dirname(os.path.abspath(sol_out_path)), exist_ok=True)
    with open(sol_out_path, "w", encoding="utf-8") as f:
        f.write(instrumented)

