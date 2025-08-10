"""
model.py

Defines core data classes for representing Foundry trace runs and
their mapping to Daikon-compatible structures.
"""

from dataclasses import dataclass, field
from typing import Dict, List

@dataclass
class VariableInstance:
    """
    Represents a single variable observed in a program point.
    """
    name: str
    type: str    # E.g. 'int', 'string'
    value: str

@dataclass
class ProgramPoint:
    """
    Represents a single program point (ENTER or EXIT) for a function
    in one fuzz run, with all variables observed there.
    """
    name: str                         # E.g. 'Bank.deposit(uint256):::ENTER'
    ppt_type: str                     # 'enter' or 'exit'
    variables: Dict[str, VariableInstance] = field(default_factory=dict)

@dataclass
class TraceRun:
    """
    Represents one complete fuzz test run with multiple program points.
    """
    invocation_nonce: int
    program_points: List[ProgramPoint] = field(default_factory=list)
