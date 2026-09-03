from __future__ import annotations

"""
Expression-style postcondition inference.

This module converts your AST IR + (optionally) traces into **candidate
postconditions expressed as compact expressions** rather than NL sentences.

Function-level facts (parity with earlier behavior):
  - NoStateWrites() when writes=[] && storage_writes=[]
  - require(...) clauses -> raw boolean expressions
  - Emits(EventName) facts
  - Whole-function external call summary: HasExternalCalls() / NoExternalCalls()

Loop-scoped seeds (primary output for downstream invariant synthesis):
  - Bounds as atomic comparisons: "0 <= i", "i < n"
  - Loop purity: HasExternalCallsInLoop() / NoExternalCallsInLoop()
  - Semantic seeds from IR roles:
      * Accumulator(role:var)   # role normalized (sum/count/product), carries original var
      * UpdatesArray(name)
      * UpdatesMapping(name)
  - Loop headers as mutation seeds:
      * Guard(<guard>)
      * Update(<update>)

Trace integration (when logs are provided):
  - Populate 'support' from traces for Emits(...) and (No|Has)ExternalCalls facts
  - Flip 'holds' to False and record 'falsifying_runs' if traces contradict AST facts

Future extensions: support/falsification from traces, storage-read/write facts, etc.
"""

from dataclasses import replace
from typing import Dict, List, Optional

from .logs_parser import parse_foundry_logs
from .models import (
    ASTFunctionIR,
    CandidatePostcondition,
    ContractIR,
    FunctionTraces,
    InferenceResult,
    LoopBounds,
    LoopSummary,
)

# =============================================================================
# Utilities
# =============================================================================

def _expr(
    expr: str,
    *,
    holds: bool = True,
    origin: str = "ast",
    desc: Optional[str] = None,
    scope: str = "function",
    loop_idx: Optional[int] = None,
) -> CandidatePostcondition:
    """
    Build a CandidatePostcondition carrying an expression.
    - expr: the machine-friendly expression string.
    - holds: whether we currently believe it holds (default True).
    - origin: tag for provenance ("ast", "trace", ...).
    - desc: optional human note (kept minimal since downstream uses expr).
    - scope: "function" or "loop"
    - loop_idx: 0-based loop index when scope=="loop"
    """
    return CandidatePostcondition(
        expr=expr,
        holds=holds,
        origin=origin,
        description=desc,
        falsifying_runs=[],
        support=0,
        scope=scope,
        loop_idx=loop_idx,
    )


def _sanitize_ident(x: str) -> str:
    """
    Very light sanitizer for variable/index names we surface in expressions.
    (We keep it minimal on purpose—your downstream parser can enforce stricter rules.)
    """
    return (x or "").strip()


# =============================================================================
# Accumulator normalization
# =============================================================================

# Map common short-hands to canonical roles
_ACC_CANON = {
    "s": "sum",
    "sum": "sum",
    "total": "sum",
    "acc": "sum",
    "accum": "sum",
    "cnt": "count",
    "count": "count",
    "counted": "count",
    "prod": "product",
    "product": "product",
}

def _normalize_acc_name(raw: str) -> str:
    r = (raw or "").strip()
    key = r.lower()
    return _ACC_CANON.get(key, r)  # fall back to original if unknown


# =============================================================================
# Trace helpers (schema-tolerant)
# =============================================================================

def _get_fn_traces(traces_by_fn: Dict[str, FunctionTraces] | None, fn_name: str) -> Optional[FunctionTraces]:
    if not traces_by_fn:
        return None
    # tolerate name styles with/without trailing ()
    return traces_by_fn.get(fn_name) or traces_by_fn.get(f"{fn_name}()")


def _event_support_from_traces(ft: FunctionTraces | None, ev_name: str) -> int:
    if not ft:
        return 0
    # Prefer dict of counts
    cnt = getattr(ft, "event_counts", None)
    if isinstance(cnt, dict):
        try:
            return int(cnt.get(ev_name, 0))
        except Exception:
            return 0
    # Fallback: flat list of names
    names = getattr(ft, "events_emitted", None)
    if isinstance(names, list):
        return sum(1 for x in names if str(x) == ev_name)
    return 0


def _has_external_calls_support(ft: FunctionTraces | None) -> tuple[int, List]:
    """
    Return (count, runs) for function-level external calls observed in traces.
    """
    if not ft:
        return 0, []
    n = int(getattr(ft, "external_calls_count", 0))
    runs = list(getattr(ft, "external_calls_runs", []) or [])
    # Fallbacks if only booleans/lists are present
    if n == 0:
        if getattr(ft, "has_external_calls", False):
            n = 1
        elif isinstance(getattr(ft, "external_calls", None), list) and ft.external_calls:
            n = len(ft.external_calls)
    return n, runs


def _loop_has_external_calls_support(ft: FunctionTraces | None, loop_idx: int) -> tuple[int, List]:
    """
    Return (count, runs) of external calls for a specific loop index if available.
    Accepts shapes like:
      - {0: 3, 1: 0}
      - {"0": {"count": 2, "runs": [...]}}
      - {0: [run1, run2, ...]}
    """
    if not ft:
        return 0, []
    per_loop = getattr(ft, "loop_external_calls", None)
    if isinstance(per_loop, dict):
        key = loop_idx if loop_idx in per_loop else str(loop_idx)
        val = per_loop.get(key)
        if isinstance(val, dict):
            return int(val.get("count", 0)), list(val.get("runs", []) or [])
        if isinstance(val, int):
            return int(val), []
        if isinstance(val, list):
            return len(val), list(val)
    return 0, []


# =============================================================================
# Candidate builders (function-level)
# =============================================================================

def _no_state_writes(fn: ASTFunctionIR) -> Optional[CandidatePostcondition]:
    """
    If the IR reports no state writes, emit NoStateWrites().
    """
    if not fn.writes and not fn.storage_writes:
        return _expr("NoStateWrites()", desc="from AST IR: writes=[], storage_writes[]", scope="function")
    return None


def _requires_exprs(fn: ASTFunctionIR) -> List[CandidatePostcondition]:
    """
    Turn require(...) strings from IR into expressions verbatim.
    Example IR: "(n <= maxN)" -> expr: "(n <= maxN)"
    """
    out: List[CandidatePostcondition] = []
    for req in fn.requires:
        r = _sanitize_ident(req)
        if r:
            out.append(_expr(r, desc="require(...) from AST IR", scope="function"))
    return out


def _event_exprs(fn: ASTFunctionIR) -> List[CandidatePostcondition]:
    """
    Turn events into Emits(EventName) facts.
    """
    out: List[CandidatePostcondition] = []
    for ev in fn.events_emitted:
        name = _sanitize_ident(ev)
        if name:
            out.append(_expr(f"Emits({name})", scope="function"))
    return out


def _fn_external_calls(fn: ASTFunctionIR) -> CandidatePostcondition:
    """
    Whole-function summary of external calls (outside the loop granularity).
    """
    if fn.external_calls:
        return _expr("HasExternalCalls()", desc="from AST IR", scope="function")
    return _expr("NoExternalCalls()", desc="from AST IR", scope="function")


# =============================================================================
# Loop-specific candidate builders
# =============================================================================

def _bounds_to_exprs(b: LoopBounds, idx_label: str, *, loop_idx: int) -> List[CandidatePostcondition]:
    """
    Convert loop bounds into a pair of atomic expressions when present:
      lower:  "<lower> <= <i>"
      upper:  "<i> <= <upper>"    (inclusive_upper)
              "<i> < <upper>"     (exclusive)
    All outputs are **loop-scoped** and tagged with loop_idx.
    """
    out: List[CandidatePostcondition] = []
    i = _sanitize_ident(idx_label)

    # lower
    lo = _sanitize_ident(b.lower)
    if lo:
        out.append(_expr(f"{lo} <= {i}", scope="loop", loop_idx=loop_idx))

    # upper
    hi = _sanitize_ident(b.upper)
    if hi:
        if b.inclusive_upper:
            out.append(_expr(f"{i} <= {hi}", scope="loop", loop_idx=loop_idx))
        else:
            out.append(_expr(f"{i} < {hi}", scope="loop", loop_idx=loop_idx))

    return out


def _loop_body_external_expr(loop: LoopSummary, *, loop_idx: int) -> CandidatePostcondition:
    """
    Emit loop-body external call fact, loop-scoped.
    """
    if loop.has_external_call_in_loop:
        return _expr("HasExternalCallsInLoop()", scope="loop", loop_idx=loop_idx)
    return _expr("NoExternalCallsInLoop()", scope="loop", loop_idx=loop_idx)


def _loop_semantic_exprs(loop: LoopSummary, *, loop_idx: int) -> List[CandidatePostcondition]:
    """
    Emit loop-specific **semantic seeds** from IR roles:
      - Accumulator(role:var)  # role normalized (sum/count/product)
      - UpdatesMapping(name)
      - UpdatesArray(name)
    """
    out: List[CandidatePostcondition] = []

    # Accumulators (normalize to canonical role; keep original var)
    for acc in loop.accumulators or []:
        var = _sanitize_ident(str(acc).split()[0])  # tolerate "s +=" shapes
        if var:
            role = _normalize_acc_name(var)
            out.append(_expr(f"Accumulator({role}:{var})", scope="loop", loop_idx=loop_idx))

    # Mapping updates
    for m in loop.mapping_updates or []:
        name = _sanitize_ident(str(m))
        if name:
            out.append(_expr(f"UpdatesMapping({name})", scope="loop", loop_idx=loop_idx))

    # Array updates
    for a in loop.array_updates or []:
        name = _sanitize_ident(str(a))
        if name:
            out.append(_expr(f"UpdatesArray({name})", scope="loop", loop_idx=loop_idx))

    return out


def _loop_header_exprs(loop: LoopSummary, *, loop_idx: int) -> List[CandidatePostcondition]:
    """
    Surface the loop header as seeds:
      - Guard(<guard>)
      - Update(<update>)
    """
    out: List[CandidatePostcondition] = []
    g = (loop.guard or "").strip()
    if g:
        out.append(_expr(f"Guard({g})", scope="loop", loop_idx=loop_idx))
    u = (loop.update or "").strip()
    if u:
        out.append(_expr(f"Update({u})", scope="loop", loop_idx=loop_idx))
    return out


def _loop_exprs(loop: LoopSummary, *, loop_idx: int) -> List[CandidatePostcondition]:
    """
    Driver for loop-derived expressions (all **loop-scoped**):
      - bounds -> atomic comparisons
      - body external call summary
      - semantic seeds from IR roles (accumulators / updates)
      - loop-header seeds (guard/update)
    """
    out: List[CandidatePostcondition] = []

    # pick index var label from bounds or fallback to first index name (or "i")
    idx = _sanitize_ident(loop.bounds.index) or (loop.indices[0] if loop.indices else "i")
    idx = _sanitize_ident(idx)

    # bounds
    out.extend(_bounds_to_exprs(loop.bounds, idx, loop_idx=loop_idx))

    # body external calls
    out.append(_loop_body_external_expr(loop, loop_idx=loop_idx))

    # semantic seeds
    out.extend(_loop_semantic_exprs(loop, loop_idx=loop_idx))

    # loop header seeds
    out.extend(_loop_header_exprs(loop, loop_idx=loop_idx))

    return out


# =============================================================================
# Top-level inference
# =============================================================================

def infer_postconditions(
    contract: ContractIR,
    traces: Dict[str, FunctionTraces] | None = None,
) -> List[InferenceResult]:
    """
    Produce expression-style postcondition candidates for each function.

    - Function-level facts are emitted with scope="function".
    - Loop-derived facts are emitted with scope="loop" and carry loop_idx.

    With traces (if provided), we:
      - fill 'support' for Emits(...) and external-call facts,
      - flip 'holds' + record 'falsifying_runs' if traces contradict AST facts.
    """
    results: List[InferenceResult] = []

    for fn in contract.functions:
        cands: List[CandidatePostcondition] = []

        # 1) AST-only whole-function facts
        ns = _no_state_writes(fn)
        if ns:
            cands.append(ns)

        cands.append(_fn_external_calls(fn))
        cands.extend(_requires_exprs(fn))
        cands.extend(_event_exprs(fn))

        # 2) Loop-derived facts (bounds + purity + semantic + header), tagged with loop_idx
        for k, loop in enumerate(fn.loops):
            cands.extend(_loop_exprs(loop, loop_idx=k))

        # 3) Integrate traces for support/falsification (if available)
        ft = _get_fn_traces(traces, fn.name) if traces else None
        new_cands: List[CandidatePostcondition] = []

        for cand in cands:
            updated = cand
            e = getattr(cand, "expr", "")
            scope = getattr(cand, "scope", "function")

            # a) Function-level: HasExternalCalls() / NoExternalCalls()
            if scope == "function" and e in ("HasExternalCalls()", "NoExternalCalls()"):
                has_calls_count, runs = _has_external_calls_support(ft)
                if e == "HasExternalCalls()":
                    # set support; falsify if 0 while we have traces
                    if ft is not None:
                        updated = replace(updated, support=has_calls_count)
                        if has_calls_count == 0:
                            updated = replace(updated, holds=False, falsifying_runs=list(runs or []), origin="ast+trace")
                else:  # NoExternalCalls()
                    if ft is not None and has_calls_count > 0:
                        updated = replace(updated, holds=False, falsifying_runs=list(runs or []), origin="ast+trace")

            # b) Function-level: Emits(Event)
            if e.startswith("Emits(") and e.endswith(")"):
                ev_name = e[len("Emits("):-1]
                sup = _event_support_from_traces(ft, ev_name)
                if ft is not None:
                    updated = replace(updated, support=sup)
                    executed = int(getattr(ft, "num_runs", getattr(ft, "runs", 0)) or 0)
                    if executed > 0 and sup == 0:
                        updated = replace(updated, holds=False, origin="ast+trace")

            # c) Loop-level: (No|Has)ExternalCallsInLoop() per loop_idx
            if scope == "loop" and e in ("HasExternalCallsInLoop()", "NoExternalCallsInLoop()"):
                k = getattr(cand, "loop_idx", None)
                if k is not None:
                    count, lruns = _loop_has_external_calls_support(ft, k)
                    if ft is not None:
                        updated = replace(updated, support=count)
                        if e == "HasExternalCallsInLoop()" and count == 0:
                            updated = replace(updated, holds=False, falsifying_runs=list(lruns or []), origin="ast+trace")
                        if e == "NoExternalCallsInLoop()" and count > 0:
                            updated = replace(updated, holds=False, falsifying_runs=list(lruns or []), origin="ast+trace")

            new_cands.append(updated)

        results.append(InferenceResult(function=fn.name, candidates=new_cands))

    return results


def infer_all(contract: ContractIR, logs_text: str) -> List[InferenceResult]:
    """
    Parse Foundry logs (best-effort) to keep the door open for:
      - support counting for Emits/Calls
      - cross-checking internal call observations
      - falsification / counterexamples

    If logs_text is empty, we just do AST-only inference.
    """
    _traces_by_outer: Dict[str, FunctionTraces] = parse_foundry_logs(logs_text)
    return infer_postconditions(contract, _traces_by_outer)
