from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

MARKER = "[INVSOL]"

ENTER_RE = re.compile(r"\[INVSOL\]\s+LOOP_ENTER\s+(\S+)")
ITER_RE = re.compile(r"\[INVSOL\]\s+LOOP_ITER\s+(\S+)\s+(\d+)")
EXIT_RE = re.compile(r"\[INVSOL\]\s+LOOP_EXIT\s+(\S+)\s+(\d+)")
VAR_RE = re.compile(r"\[INVSOL\]\s+(ENTER_VAR|ITER_VAR|EXIT_VAR|ITER_IDX)\s+(\S+)\s+(\S+)\s+(.+?)\s*$")


@dataclass
class Iteration:
    index: int
    values: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"index": self.index, "values": self.values}


@dataclass
class LoopRun:
    loop_id: str
    entry: Dict[str, str] = field(default_factory=dict)
    iterations: List[Iteration] = field(default_factory=list)
    exit: Dict[str, str] = field(default_factory=dict)
    trip_count: Optional[int] = None
    closed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "loop_id": self.loop_id,
            "entry": self.entry,
            "iterations": [i.to_dict() for i in self.iterations],
            "exit": self.exit,
            "trip_count": self.trip_count,
        }


ECHOED = '"[INVSOL]'


def _is_trace_echo(line: str) -> bool:
    """
    At high verbosity forge prints every console.log twice: once as emitted
    output and once as a call in the trace tree, where the payload is quoted.
    Counting both would double every loop run, so the quoted form is skipped.
    """
    return ECHOED in line


def _clean(value: str) -> str:
    return value.strip().strip('"').rstrip(',)"').strip()


def _clean_name(name: str) -> str:
    """
    Foundry renders console.log("label", v) as "label: v", so the captured name
    keeps a trailing colon that has to come off.
    """
    return name.strip().rstrip(':,)"').strip()


def parse_lines(lines: Iterable[str]) -> List[LoopRun]:
    """
    Rebuild loop runs from a Foundry trace containing InvSol probe output.

    A run starts at LOOP_ENTER and closes at the matching LOOP_EXIT. Nested
    loops produce a separate run for every execution of the inner loop, so a
    loop entered once per outer iteration yields one run per outer pass.
    """
    runs: List[LoopRun] = []
    stack: List[LoopRun] = []
    open_runs: Dict[str, List[LoopRun]] = {}

    for raw in lines:
        line = raw.rstrip("\n")
        if MARKER not in line or _is_trace_echo(line):
            continue

        m = ENTER_RE.search(line)
        if m:
            loop_id = m.group(1)
            bucket = open_runs.setdefault(loop_id, [])
            while bucket and bucket[-1].closed:
                bucket.pop()
            run = LoopRun(loop_id=loop_id)
            stack.append(run)
            bucket.append(run)
            runs.append(run)
            continue

        m = ITER_RE.search(line)
        if m:
            loop_id, index = m.group(1), int(m.group(2))
            run = _current(open_runs, loop_id)
            if run is not None:
                run.iterations.append(Iteration(index=index))
            continue

        m = EXIT_RE.search(line)
        if m:
            loop_id, count = m.group(1), int(m.group(2))
            run = _current(open_runs, loop_id)
            if run is not None:
                run.trip_count = count
                run.closed = True
                if stack and stack[-1] is run:
                    stack.pop()
            continue

        m = VAR_RE.search(line)
        if m:
            kind, loop_id, name, value = m.groups()
            run = _current(open_runs, loop_id)
            if run is None:
                continue
            name = _clean_name(name)
            value = _clean(value)
            if kind == "ENTER_VAR":
                run.entry[name] = value
            elif kind == "EXIT_VAR":
                run.exit[name] = value
            elif run.iterations:
                run.iterations[-1].values[name] = value

    return runs


def _current(open_runs: Dict[str, List[LoopRun]], loop_id: str) -> Optional[LoopRun]:
    """
    The most recent run for a loop, including one already closed, because the
    EXIT_VAR lines are emitted after LOOP_EXIT.
    """
    bucket = open_runs.get(loop_id)
    return bucket[-1] if bucket else None


def parse_file(path: str) -> List[LoopRun]:
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    return parse_lines(text.splitlines())


def summarise(runs: List[LoopRun]) -> Dict[str, Any]:
    """
    Aggregate runs per loop so downstream inference sees one record per loop.
    """
    by_loop: Dict[str, Dict[str, Any]] = {}
    for run in runs:
        entry = by_loop.setdefault(
            run.loop_id,
            {
                "loop_id": run.loop_id,
                "runs": 0,
                "trip_counts": [],
                "max_trip_count": 0,
                "observed_vars": [],
                "samples": [],
            },
        )
        entry["runs"] += 1
        if run.trip_count is not None:
            entry["trip_counts"].append(run.trip_count)
            entry["max_trip_count"] = max(entry["max_trip_count"], run.trip_count)

        names = set(entry["observed_vars"])
        names |= set(run.entry) | set(run.exit)
        for it in run.iterations:
            names |= set(it.values)
        entry["observed_vars"] = sorted(names)
        entry["samples"].append(run.to_dict())

    return {"loops": list(by_loop.values())}


def main(argv: Optional[List[str]] = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Extract loop iteration traces from Foundry output.")
    ap.add_argument("trace")
    ap.add_argument("-o", "--out")
    ap.add_argument("--summary", action="store_true")
    args = ap.parse_args(argv)

    runs = parse_file(args.trace)
    payload = summarise(runs) if args.summary else {"runs": [r.to_dict() for r in runs]}

    text = json.dumps(payload, indent=2)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"parsed {len(runs)} loop runs -> {args.out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
