"""
foundry2daikon

A framework to convert Foundry-generated Solidity fuzzing execution traces
into Daikon-compatible .decls and .dtrace files for invariant inference.
"""

from parser import parse_trace_file
from decls_writer import generate_decls
from dtrace_writer import generate_dtrace
