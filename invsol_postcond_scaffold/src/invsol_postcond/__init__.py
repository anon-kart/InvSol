# src/invsol_postcond/__init__.py
"""
invsol_postcond — Postcondition inference scaffold.

This package wires together:
- AST IR loader/parsers
- Foundry logs parser
- Simple rule-based postcondition inference
- A small CLI

Everything is intentionally lightweight/typed to help you iterate quickly.
"""

from __future__ import annotations

# Re-export data models
from .models import (
    LoopBounds,
    LoopSummary,
    LoopInfo,  # alias to LoopSummary
    ASTFunctionIR,
    FunctionIR,  # alias to ASTFunctionIR
    ContractIR,
    FoundryCall,
    FunctionTraces,
    CandidatePostcondition,
    InferenceResult,
)

# IR and logs loaders/parsers
from .ast_ir import parse_ir_from_file, load_ast_ir_file
from .logs_parser import (
    parse_foundry_logs,
    FoundryTraceEvent,
    FoundryTraceBlock,
    FoundryFunctionTrace,
)

# Inference
from .inference import infer_all, infer_postconditions

# Utilities / validators
from .io_utils import read_json, read_text
from .validators import validate_paths, validate_inputs

__all__ = [
    # Models
    "LoopBounds",
    "LoopSummary",
    "LoopInfo",
    "ASTFunctionIR",
    "FunctionIR",
    "ContractIR",
    "FoundryCall",
    "FunctionTraces",
    "CandidatePostcondition",
    "InferenceResult",
    # Parsers
    "parse_ir_from_file",
    "load_ast_ir_file",
    "parse_foundry_logs",
    "FoundryTraceEvent",
    "FoundryTraceBlock",
    "FoundryFunctionTrace",
    # Inference
    "infer_all",
    "infer_postconditions",
    # Utils
    "read_json",
    "read_text",
    "validate_paths",
    "validate_inputs",
]
