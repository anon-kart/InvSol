from __future__ import annotations

from typing import Any, Dict, List, Tuple

from . import loop_probe, state_probe
from .loop_probe import Edit, add_console_import, apply_edits


def _overlaps(a: Edit, b: Edit) -> bool:
    if a.length == 0 and b.length == 0:
        return False
    return a.offset < b.offset + b.length and b.offset < a.offset + a.length


def instrument(
    source: str,
    ir: Dict[str, Any],
    *,
    loops: bool = True,
    state: bool = True,
) -> Tuple[str, Dict[str, List[Dict[str, Any]]]]:
    """
    Add loop probes and function-boundary state probes in a single pass.

    Both probe sets are positioned using source offsets taken from the same IR,
    which describes the original file. Running one after the other would apply
    the second set of offsets to a file the first had already rewritten, so the
    edits are collected together and applied once.

    Where a loop probe rewrites a span and a state probe would insert inside it,
    the state probe is dropped. That only arises for a return used as the whole
    body of a brace-less loop, and losing one exit snapshot is preferable to
    producing a file that does not compile.
    """
    loop_edits: List[Edit] = []
    loop_manifest: List[Dict[str, Any]] = []
    if loops:
        found = loop_probe._loops_from_ir(ir)
        loop_edits, built = loop_probe.build_edits(source, found)
        loop_manifest = [p.to_dict() for p in built]

    state_edits: List[Edit] = []
    state_manifest: List[Dict[str, Any]] = []
    if state:
        state_edits, built = state_probe.build_edits(source, ir)
        state_manifest = [p.to_dict() for p in built]

    replacements = [e for e in loop_edits if e.length > 0]
    kept = [e for e in state_edits if not any(_overlaps(e, r) for r in replacements)]
    dropped = len(state_edits) - len(kept)

    edits = loop_edits + kept
    if not edits:
        return source, {"loops": [], "state": [], "dropped_state_edits": 0}

    out = add_console_import(apply_edits(source, edits))
    return out, {
        "loops": loop_manifest,
        "state": state_manifest,
        "dropped_state_edits": dropped,
    }
