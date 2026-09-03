from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

MARKER = "[INVSOL]"

ENTER_RE = re.compile(r"\[INVSOL\]\s+STATE_ENTER\s+(\S+)\s*$")
EXIT_RE = re.compile(r"\[INVSOL\]\s+STATE_EXIT\s+(\S+)\s*$")
VAR_RE = re.compile(r"\[INVSOL\]\s+VAR\s+(\S+)\s+(\S+)\s+(-?\d+)\s*$")
ELEM_RE = re.compile(r"\[INVSOL\]\s+ELEM\s+(\S+)\s+(\S+)\s+(\d+)\s+(\S+)\s*$")
KEY_RE = re.compile(r"\[INVSOL\]\s+KEY\s+(\S+)\s+(\S+)\s+(\S+)\s+(-?\d+)\s*$")
FIELD_RE = re.compile(r"\[INVSOL\]\s+FIELD\s+(\S+)\s+(\S+)\s+(\S+)\s+(-?\d+)\s*$")


@dataclass
class Snapshot:
    """Contract state as it stood at one function boundary."""

    function: str
    phase: str
    values: Dict[str, int] = field(default_factory=dict)
    elements: Dict[str, Dict[int, str]] = field(default_factory=dict)
    mappings: Dict[str, Dict[str, int]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "function": self.function,
            "phase": self.phase,
            "values": self.values,
            "elements": {k: dict(v) for k, v in self.elements.items()},
            "mappings": {k: dict(v) for k, v in self.mappings.items()},
        }


@dataclass
class Call:
    """One observed call, with the state before and after it."""

    function: str
    pre: Snapshot
    post: Snapshot

    def to_dict(self) -> Dict[str, Any]:
        return {
            "function": self.function,
            "pre": self.pre.to_dict(),
            "post": self.post.to_dict(),
        }


def _is_echo(line: str) -> bool:
    """
    Whether this line is forge echoing a log inside its call trace.

    At -vvvv every console.log appears twice: once in the Logs block and once
    as a console::log entry in Traces. Counting both would double every
    observation.
    """
    return "console::log" in line or "console.log" in line


def parse_lines(lines: List[str]) -> List[Call]:
    """
    Rebuild per-call snapshots from the probe output.

    The probes emit a flat sequence, so the parser closes whichever snapshot is
    open as soon as the next boundary marker arrives. A call that reverts
    partway never emits its exit marker, so it leaves no pair behind and is
    simply not observed.
    """
    calls: List[Call] = []
    current: Optional[Snapshot] = None
    entered: Dict[str, Snapshot] = {}

    def close() -> None:
        nonlocal current
        if current is None:
            return
        if current.phase == "enter":
            entered[current.function] = current
        else:
            pre = entered.pop(current.function, None)
            if pre is not None:
                calls.append(Call(function=current.function, pre=pre, post=current))
        current = None

    for raw in lines:
        line = raw.strip()
        if MARKER not in line or _is_echo(line):
            continue

        enter = ENTER_RE.search(line)
        if enter:
            close()
            current = Snapshot(function=enter.group(1), phase="enter")
            continue

        exit_match = EXIT_RE.search(line)
        if exit_match:
            close()
            current = Snapshot(function=exit_match.group(1), phase="exit")
            continue

        if current is None:
            continue

        var = VAR_RE.search(line)
        if var and var.group(1) == current.function:
            current.values[var.group(2)] = int(var.group(3))
            continue

        elem = ELEM_RE.search(line)
        if elem and elem.group(1) == current.function:
            current.elements.setdefault(elem.group(2), {})[int(elem.group(3))] = (
                elem.group(4).lower()
            )
            continue

        key = KEY_RE.search(line)
        if key and key.group(1) == current.function:
            current.mappings.setdefault(key.group(2), {})[key.group(3).lower()] = int(
                key.group(4)
            )
            continue

        # A struct field arrives already flattened, as schedules_start, and is
        # kept alongside the mappings so each field reads as its own location.
        field = FIELD_RE.search(line)
        if field and field.group(1) == current.function:
            current.mappings.setdefault(field.group(2), {})[
                field.group(3).lower()
            ] = int(field.group(4))

    close()
    return calls


def parse_text(text: str) -> List[Call]:
    return parse_lines(text.splitlines())


def summarise(calls: List[Call]) -> Dict[str, Any]:
    per_function: Dict[str, int] = {}
    for call in calls:
        per_function[call.function] = per_function.get(call.function, 0) + 1
    return {
        "calls": len(calls),
        "functions": per_function,
        "observations": [c.to_dict() for c in calls],
    }
