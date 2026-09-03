# src/invsol_postcond/models.py
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

# ----------------------------
# IR loop structures
# ----------------------------

@dataclass(frozen=True)
class LoopBounds:
    index: str
    lower: str
    upper: str
    inclusive_upper: bool = False


@dataclass(frozen=True)
class LoopSummary:
    # Body features
    indices: List[str] = field(default_factory=list)
    accumulators: List[str] = field(default_factory=list)
    mapping_updates: List[str] = field(default_factory=list)
    array_updates: List[str] = field(default_factory=list)
    has_external_call_in_loop: bool = False

    accumulator_facts: List[Dict[str, Any]] = field(default_factory=list)
    nested_accumulator_facts: List[Dict[str, Any]] = field(default_factory=list)
    carried_vars: List[str] = field(default_factory=list)
    loop_id: str = ""
    category: str = ""

    # Structural info
    bounds: LoopBounds = field(default_factory=lambda: LoopBounds("", "", "", False))
    loop_type: str = ""   # "for", "while", ...
    init: str = ""        # e.g., "i = 0"
    guard: str = ""       # e.g., "(i < n)"
    update: str = ""      # e.g., "(i++)"


# ----------------------------
# AST/Contract IR models
# ----------------------------

@dataclass(frozen=True)
class ASTFunctionIR:
    contract: str
    name: str
    visibility: str
    mutability: str
    modifiers: List[str] = field(default_factory=list)
    params: List[Dict[str, str]] = field(default_factory=list)
    returns: List[Dict[str, str]] = field(default_factory=list)

    # Loops parsed from IR
    loops: List[LoopSummary] = field(default_factory=list)

    # Requirements / effects / calls
    requires: List[str] = field(default_factory=list)
    reads: List[str] = field(default_factory=list)
    writes: List[str] = field(default_factory=list)
    member_accesses: List[str] = field(default_factory=list)
    internal_calls: List[str] = field(default_factory=list)
    external_calls: List[str] = field(default_factory=list)
    events_emitted: List[str] = field(default_factory=list)

    # Normalized as (var, key) pairs; key can be None
    storage_reads: List[Tuple[str, Optional[str]]] = field(default_factory=list)
    storage_writes: List[Tuple[str, Optional[str]]] = field(default_factory=list)

    # NEW: optional raw source snippet for heuristic analysis
    source_code: Optional[str] = None

    # Synthetic = auto-generated or placeholder functions
    synthetic: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ContractIR:
    name: str
    solidity_version: str
    functions: List[ASTFunctionIR] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)

    def function_map(self) -> Dict[str, ASTFunctionIR]:
        return {f.name: f for f in self.functions}


# ----------------------------
# Foundry trace models
# ----------------------------

@dataclass(frozen=True)
class FoundryCall:
    contract: Optional[str]  # can be "SimpleToken" or address-like, etc.
    function: Optional[str]
    raw: str  # the full trace line


@dataclass  # NOTE: not frozen → parser can update counters safely
class FunctionTraces:
    function: str
    calls: List[FoundryCall] = field(default_factory=list)

    # --- Optional analytics populated by logs_parser.py ---
    num_runs: int = 0                                # how many times this outer function appeared
    external_calls_count: int = 0                    # heuristic count of external-ish calls
    has_external_calls: bool = False                 # quick flag derived from the above
    external_calls_runs: List[str] = field(default_factory=list)  # raw lines for debugging
    event_counts: Dict[str, int] = field(default_factory=dict)    # EventName -> occurrences
    events_emitted: List[str] = field(default_factory=list)       # flat list of seen event names
    loop_external_calls: Dict[int, int] = field(default_factory=dict)  # loop_idx -> count (if available)

    def called_internal(self, name: str) -> bool:
        target = (name or "").lower()
        for c in self.calls:
            if (c.function or "").lower() == target:
                return True
        return False


# ----------------------------
# Inference models (expression-first)
# ----------------------------

@dataclass(frozen=True)
class CandidatePostcondition:
    """
    Machine-usable postcondition expression (tiny DSL).
    Examples:
      - "0 <= i && i < n"
      - "Emits(SumResult)"
      - "NoExternalCalls()"
      - "NoStateWrites()"
      - "(n <= maxN)"
    """
    expr: str
    holds: bool
    falsifying_runs: List[str] = field(default_factory=list)
    origin: str = "ast"           # "ast" | "trace" | "synth"
    support: int = 0              # number of traces supporting the expr
    description: Optional[str] = None  # optional human note

    # --- Loop scoping metadata ---
    scope: str = "function"                 # "function" | "loop"
    loop_idx: Optional[int] = None          # 0-based loop index within the function

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class InferenceResult:
    function: str
    candidates: List[CandidatePostcondition] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"function": self.function, "candidates": [c.to_dict() for c in self.candidates]}


# ----------------------------
# Re-exports / compat
# ----------------------------

# Backward-compatibility alias (older code may refer to FunctionIR)
FunctionIR = ASTFunctionIR
LoopInfo = LoopSummary  # some code used this old name

__all__ = [
    # Loop structs
    "LoopBounds",
    "LoopSummary",
    # IR models
    "ASTFunctionIR",
    "FunctionIR",
    "ContractIR",
    # Foundry traces
    "FoundryCall",
    "FunctionTraces",
    # Inference results
    "CandidatePostcondition",
    "InferenceResult",
]
