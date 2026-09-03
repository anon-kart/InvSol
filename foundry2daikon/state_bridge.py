"""
Solidity-to-Daikon translation layer.

Daikon expects a flat list of scalar variables at each program point, which is
not how Solidity storage is shaped. Section 3.4.1 of the paper describes the
three conversions this module performs:

  - nested structs are flattened so each field becomes its own variable,
    a struct `u` with fields `age` and `balance` becoming `u_age` and
    `u_balance`;
  - arrays are serialised as a length plus their individual elements,
    `arr_length = 3`, `arr[0] = x`, and so on, which is what lets Daikon
    recognise index-based patterns;
  - mappings, which cannot be enumerated on chain, are reconstructed from the
    keys an execution actually touched, so `balances[0xabc...] = 100` records
    one observed key-value pair.

The reconstruction is for candidate generation only. It says nothing about keys
no execution touched.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from model import ProgramPoint, TraceRun, VariableInstance

HEX_PREFIX = "0x"


def _daikon_type(value: str) -> str:
    """Daikon's notion of the type, which is coarser than Solidity's."""
    token = str(value).strip()
    if token.lower().startswith(HEX_PREFIX):
        return "hashcode"
    try:
        int(token)
        return "int"
    except (TypeError, ValueError):
        return "java.lang.String"


def _add(point: ProgramPoint, name: str, value: Any) -> None:
    token = str(value)
    point.variables[name] = VariableInstance(
        name=name, type=_daikon_type(token), value=token
    )


def flatten(snapshot: Any) -> Dict[str, str]:
    """
    One snapshot as the flat variables Daikon reads.

    Struct fields arrive from the probe already joined with an underscore, so
    they need no further work here; arrays and mappings are expanded.
    """
    flat: Dict[str, str] = {}

    for name, value in (getattr(snapshot, "values", None) or {}).items():
        flat[name] = str(value)

    for name, entries in (getattr(snapshot, "elements", None) or {}).items():
        flat.setdefault(f"{name}_length", str(len(entries)))
        for index in sorted(entries):
            flat[f"{name}[{index}]"] = str(entries[index])

    for name, entries in (getattr(snapshot, "mappings", None) or {}).items():
        for key in sorted(entries):
            flat[f"{name}[{key}]"] = str(entries[key])

    return flat


def _point(contract: str, function: str, phase: str, snapshot: Any) -> ProgramPoint:
    suffix = ":::ENTER" if phase == "enter" else ":::EXIT1"
    point = ProgramPoint(
        name=f"{contract}.{function}(){suffix}",
        ppt_type="enter" if phase == "enter" else "exit",
    )
    for name, value in flatten(snapshot).items():
        _add(point, name, value)
    return point


def to_trace_runs(calls: List[Any], contract: str) -> List[TraceRun]:
    """
    One call becomes one run with an entry and an exit point.

    Daikon pairs an exit with its entry by invocation nonce, so a call whose
    exit was never observed is dropped rather than paired with the wrong entry.
    """
    runs: List[TraceRun] = []
    for nonce, call in enumerate(calls or [], start=1):
        function = getattr(call, "function", "") or ""
        if not function:
            continue
        runs.append(
            TraceRun(
                invocation_nonce=nonce,
                program_points=[
                    _point(contract, function, "enter", call.pre),
                    _point(contract, function, "exit", call.post),
                ],
            )
        )
    return runs


def write_daikon_files(
    calls: List[Any], contract: str, out_dir: Any
) -> Optional[Tuple[Any, Any]]:
    """
    Write the .decls and .dtrace pair, returning their paths.

    Returns None when there is nothing to write, so a caller can tell an empty
    run from a failed one.
    """
    from pathlib import Path

    runs = to_trace_runs(calls, contract)
    if not runs:
        return None

    from decls_writer import generate_decls
    from dtrace_writer import generate_dtrace

    decls_text, declared = generate_decls(runs)
    dtrace_text = generate_dtrace(runs, declared)

    directory = Path(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    decls_path = directory / f"{contract}.decls"
    dtrace_path = directory / f"{contract}.dtrace"
    decls_path.write_text(decls_text, encoding="utf-8")
    dtrace_path.write_text(dtrace_text, encoding="utf-8")
    return decls_path, dtrace_path
