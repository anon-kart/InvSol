from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .io_utils import as_path, read_json
from .models import (
    ASTFunctionIR,
    ContractIR,
    LoopBounds,
    LoopSummary,
)

PathLike = Union[str, Path]

__all__ = [
    "load_ast_ir_file",
    "parse_ir_from_file",
    "parse_ast_ir",
]

# ----------------------------
# Utilities
# ----------------------------

def _norm_storage_pairs(items: List[Any]) -> List[Tuple[str, Optional[str]]]:
    """
    Normalize storage read/write records which may be either strings or objects
    like {"var": "...", "key": "..."} into (var, key) tuples.
    """
    out: List[Tuple[str, Optional[str]]] = []
    for it in items or []:
        if isinstance(it, str):
            # best effort: no key information
            out.append((it, None))
        elif isinstance(it, dict):
            var = it.get("var")
            key = it.get("key")
            out.append((str(var) if var is not None else "", key if key is not None else None))
        else:
            # unknown shape; stringify
            out.append((str(it), None))
    return out


def _parse_loop(loop_obj: Dict[str, Any]) -> LoopSummary:
    # bounds block
    b = loop_obj.get("bounds", {}) or {}
    bounds = LoopBounds(
        index=str(b.get("index", "")),
        lower=str(b.get("lower", "")),
        upper=str(b.get("upper", "")),
        inclusive_upper=bool(b.get("inclusive_upper", False)),
    )

    # body summary (indices/accumulators/updates/external calls)
    body = loop_obj.get("body_summary", {}) or {}
    indices = list(body.get("indices", []) or [])
    accumulators = list(body.get("accumulators", []) or [])
    mapping_updates = list(body.get("mapping_updates", []) or [])
    array_updates = list(body.get("array_updates", []) or [])
    has_external_call_in_loop = bool(body.get("has_external_call_in_loop", False))

    return LoopSummary(
        indices=indices,
        accumulators=accumulators,
        mapping_updates=mapping_updates,
        array_updates=array_updates,
        has_external_call_in_loop=has_external_call_in_loop,
        bounds=bounds,
        loop_type=str(loop_obj.get("type", "") or ""),
        init=str(loop_obj.get("init", "") or ""),
        guard=str(loop_obj.get("guard", "") or ""),
        update=str(loop_obj.get("update", "") or ""),
        accumulator_facts=list(body.get("accumulator_facts") or []),
        nested_accumulator_facts=list(body.get("nested_accumulator_facts") or []),
        carried_vars=list(body.get("carried_vars") or []),
        loop_id=str(loop_obj.get("loop_id", "") or ""),
        category=str(loop_obj.get("category", "") or ""),
    )


def _parse_function(fn_obj: Dict[str, Any]) -> ASTFunctionIR:
    loops = [_parse_loop(l) for l in (fn_obj.get("loops") or [])]

    # storage reads/writes may be strings or objects; normalize to tuples
    storage_reads = _norm_storage_pairs(fn_obj.get("storage_reads") or [])
    storage_writes = _norm_storage_pairs(fn_obj.get("storage_writes") or [])

    return ASTFunctionIR(
        contract=str(fn_obj.get("contract", "")),
        name=str(fn_obj.get("name", "")),
        visibility=str(fn_obj.get("visibility", "")),
        mutability=str(fn_obj.get("mutability", "")),
        modifiers=list(fn_obj.get("modifiers", []) or []),
        params=list(fn_obj.get("params", []) or []),
        returns=list(fn_obj.get("returns", []) or []),
        loops=loops,
        requires=list(fn_obj.get("requires", []) or []),
        reads=list(fn_obj.get("reads", []) or []),
        writes=list(fn_obj.get("writes", []) or []),
        member_accesses=list(fn_obj.get("member_accesses", []) or []),
        internal_calls=list(fn_obj.get("internal_calls", []) or []),
        external_calls=list(fn_obj.get("external_calls", []) or []),
        events_emitted=list(fn_obj.get("events_emitted", []) or []),
        storage_reads=storage_reads,
        storage_writes=storage_writes,
        synthetic=bool(fn_obj.get("synthetic", False)),
    )


def _parse_contract(contract_obj: Dict[str, Any]) -> ContractIR:
    name = str(contract_obj.get("name", ""))
    sol_ver = str(contract_obj.get("solidity_version", ""))

    functions = [_parse_function(f) for f in (contract_obj.get("functions") or [])]

    return ContractIR(
        name=name,
        solidity_version=sol_ver,
        functions=functions,
        raw=contract_obj,
    )

# ----------------------------
# Public API
# ----------------------------

def load_ast_ir_file(path: PathLike) -> ContractIR:
    """
    Read a JSON IR file from disk and parse into ContractIR.
    """
    p = as_path(path)
    data = read_json(p)
    return parse_ast_ir(data)


def parse_ir_from_file(path: PathLike) -> ContractIR:
    """
    Back-compat alias; same as load_ast_ir_file.
    """
    return load_ast_ir_file(path)


def parse_ast_ir(ir_or_path: Union[Dict[str, Any], PathLike]) -> ContractIR:
    """
    Accepts either:
      - a dict already loaded from JSON, or
      - a filesystem path to the JSON file.
    """
    # If it's already a dict (like when CLI does read_json(...) first), parse directly.
    if isinstance(ir_or_path, dict):
        # IR can be either {"contract": {...}} or the contract object directly.
        if "contract" in ir_or_path and isinstance(ir_or_path["contract"], dict):
            return _parse_contract(ir_or_path["contract"])
        # If the dict looks like the inner "contract" object already:
        return _parse_contract(ir_or_path)

    # Otherwise treat as a file path
    return load_ast_ir_file(ir_or_path)
