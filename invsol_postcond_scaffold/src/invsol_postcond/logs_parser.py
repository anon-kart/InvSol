from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .models import FoundryCall, FunctionTraces


# ============================
# Public lightweight structures
# ============================

@dataclass(frozen=True)
class FoundryTraceEvent:
    """
    Very lightweight representation of an 'emit ...' or 'Event:' block
    extracted from Foundry -vvvv logs. Best-effort only.
    """
    address: Optional[str]          # emitting contract/address if found
    topic_like: Optional[str]       # first topic/hash if present (best-effort)
    data_like: Optional[str]        # trailing bytes/int blob if present (best-effort)
    raw: str                        # the full (or multi-line) log snippet


@dataclass(frozen=True)
class FoundryTraceBlock:
    """
    A group of related trace lines (calls/events) that belong together under a
    single outer "test" function in the logs.
    """
    lines: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class FoundryFunctionTrace:
    """
    A higher-level view of traces grouped under a single outer function
    (e.g., a Foundry test function). This mirrors FunctionTraces in spirit
    but is kept for compatibility with older code paths.
    """
    function: str
    block: FoundryTraceBlock
    calls: List[FoundryCall] = field(default_factory=list)
    events: List[FoundryTraceEvent] = field(default_factory=list)


__all__ = [
    "parse_foundry_logs",
    "parse_foundry_traces",   # back-compat alias
    "FoundryTraceEvent",
    "FoundryTraceBlock",
    "FoundryFunctionTrace",
    "FoundryCall",
    "FunctionTraces",
]


# ============================
# Regexes (loose / best-effort)
# ============================

# Matches a call line like:
#   ├─ [46276] SimpleToken::mint(0xABC..., 1000)
#   ├─ [552] SimpleToken::balanceOf(0xABC...) [staticcall]
CALL_LINE_RE = re.compile(
    r"""
    ^\s* [├│└]*       # optional tree glyphs
    \s* \[\d+\] \s+   # gas-ish counter in brackets
    (?P<contract>[A-Za-z0-9_:\[\]\-]+)?   # optional contract hint
    ::?
    (?P<func>[A-Za-z0-9_]+)               # function name
    \s* \(                                 # opening paren of args
    """,
    re.VERBOSE,
)

# Foundry sometimes prints an "Event:" block
EVENT_BLOCK_MARKER_RE = re.compile(r"\bEvent:\b", re.IGNORECASE)

# Try to capture the event name at the beginning of an Event: block, e.g.
# "Event: SumResult(indexed ...)" or "Event: LoopPlayground.SumResult(...)"
EVENT_NAME_RE = re.compile(
    r"""
    \bEvent:\s*
    (?:
        (?P<scoped>[A-Za-z0-9_]+)\.(?P<scoped_name>[A-Za-z0-9_]+)
        |
        (?P<bare>[A-Za-z0-9_]+)
    )
    \s*\(
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Detect "emit log_*(" console logs (kept for completeness)
EMIT_LINE_RE = re.compile(r"\bemit\s+(?P<kind>log_[a-zA-Z]+)\(.*\)", re.IGNORECASE)

# Helpers for extracting hex-ish blobs
HEX32_RE = re.compile(r"0x[0-9a-fA-F]{64}")
HEX_RE = re.compile(r"0x[0-9a-fA-F]+")

# A very loose matcher to detect outer frames like "MyTest::test_thing("
OUTER_RE = re.compile(r"([A-Za-z0-9_]+)::([A-Za-z0-9_]+)\(")

# Heuristic "external-ish" functions (used to increment external_calls_count)
EXTERNALISH_FUNCS = {
    "push",          # dynamic array push (treated as external-ish by your IR heuristics)
    "call",
    "delegatecall",
    "staticcall",
    "transfer",
    "send",
}


# ============================
# Internal helpers
# ============================

def _maybe_parse_event(lines: List[str], i: int) -> Optional[FoundryTraceEvent]:
    """
    Given the lines and a starting index that looks like either an 'emit' line
    or the beginning of an 'Event:' block, attempt to synthesize a FoundryTraceEvent.
    """
    raw = lines[i].rstrip("\n")

    # Case 1: 'emit log_*(' line
    if EMIT_LINE_RE.search(raw):
        return FoundryTraceEvent(address=None, topic_like=None, data_like=None, raw=raw)

    # Case 2: a block beginning with "Event:" followed by a few lines describing it
    if EVENT_BLOCK_MARKER_RE.search(raw):
        addr: Optional[str] = None
        topic: Optional[str] = None
        data: Optional[str] = None

        # Heuristically scan a few following lines to pick up fields
        for j in range(i, min(i + 6, len(lines))):
            lj = lines[j].rstrip("\n")
            if addr is None:
                m = HEX_RE.search(lj)
                if m:
                    addr = m.group(0)
            if topic is None:
                m2 = HEX32_RE.search(lj)
                if m2:
                    topic = m2.group(0)
            if data is None:
                m3 = list(HEX_RE.finditer(lj))
                if m3:
                    data = m3[-1].group(0)

        return FoundryTraceEvent(
            address=addr,
            topic_like=topic,
            data_like=data,
            raw="\n".join(lines[i:i + 6]),
        )

    return None


def _bump_attr(obj: object, name: str, inc: int = 1, default: int = 0) -> None:
    """Safely increment an integer attribute if it exists (ignore if not)."""
    if hasattr(obj, name):
        try:
            cur = getattr(obj, name)
        except Exception:
            cur = default
        try:
            setattr(obj, name, (cur or 0) + inc)
        except Exception:
            pass


def _ensure_ft(buckets: Dict[str, FunctionTraces], key: str) -> FunctionTraces:
    """Ensure a FunctionTraces exists for key and has the optional fields."""
    if key not in buckets:
        # minimal init; extra fields are optional and may not exist in older models.py
        buckets[key] = FunctionTraces(function=key)
    ft = buckets[key]

    # Lazily seed optional fields if they exist on the dataclass
    if hasattr(ft, "event_counts") and getattr(ft, "event_counts", None) is None:
        setattr(ft, "event_counts", {})
    if hasattr(ft, "events_emitted") and getattr(ft, "events_emitted", None) is None:
        setattr(ft, "events_emitted", [])
    if hasattr(ft, "external_calls_runs") and getattr(ft, "external_calls_runs", None) is None:
        setattr(ft, "external_calls_runs", [])
    if hasattr(ft, "loop_external_calls") and getattr(ft, "loop_external_calls", None) is None:
        setattr(ft, "loop_external_calls", {})
    if hasattr(ft, "num_runs") and getattr(ft, "num_runs", None) is None:
        setattr(ft, "num_runs", 0)
    if hasattr(ft, "external_calls_count") and getattr(ft, "external_calls_count", None) is None:
        setattr(ft, "external_calls_count", 0)
    if hasattr(ft, "has_external_calls") and getattr(ft, "has_external_calls", None) is None:
        setattr(ft, "has_external_calls", False)

    return ft


def _record_event_line(ft: FunctionTraces, lines: List[str], idx: int) -> None:
    """Best-effort extraction of an event name and counting it."""
    # Try to grab a synthetic event object (address/topics/data)
    _ = _maybe_parse_event(lines, idx)

    # Try to infer the event name from the Event: line itself
    name: Optional[str] = None
    mname = EVENT_NAME_RE.search(lines[idx])
    if mname:
        if mname.group("scoped_name"):
            name = mname.group("scoped_name")
        else:
            name = mname.group("bare")

    if name:
        # event_counts[name] += 1 (if field exists)
        if hasattr(ft, "event_counts"):
            d = getattr(ft, "event_counts", {})
            d[name] = d.get(name, 0) + 1
            try:
                setattr(ft, "event_counts", d)
            except Exception:
                pass
        # events_emitted.append(name) (if field exists)
        if hasattr(ft, "events_emitted"):
            try:
                getattr(ft, "events_emitted").append(name)
            except Exception:
                pass


# ============================
# Public API
# ============================

def parse_foundry_logs(text: str) -> Dict[str, FunctionTraces]:
    """
    Parse Foundry -vvvv logs (best-effort) and return a mapping
    from 'outer function' (typically a test function name like
    'MyTest::test_something') to FunctionTraces.

    We now also try to fill:
      - num_runs (per outer function)
      - external_calls_count (+ has_external_calls)
      - event_counts (by event name) and events_emitted list
      - loop_external_calls  (left empty; requires instrumentation to map to loops)

    All fields are optional and only set if they exist on FunctionTraces.
    """
    lines = text.splitlines()

    traces_by_outer: Dict[str, FunctionTraces] = {}
    current_outer: Optional[str] = None

    for idx, line in enumerate(lines):
        l = line.rstrip("\n")

        # Detect/refresh the outer scope if we see a frame header.
        # Count it as another "run" of that outer function.
        m_outer = OUTER_RE.search(l)
        if m_outer and not CALL_LINE_RE.search(l):
            outer_fn = f"{m_outer.group(1)}::{m_outer.group(2)}"
            current_outer = outer_fn
            ft = _ensure_ft(traces_by_outer, current_outer)
            _bump_attr(ft, "num_runs", inc=1, default=0)
            continue

        # Collect call lines (and heuristically treat some as "external-ish")
        m_call = CALL_LINE_RE.search(l)
        if m_call:
            contract = m_call.group("contract")
            func = m_call.group("func")
            call = FoundryCall(contract=contract, function=func, raw=l)

            bucket_name = current_outer or "<unknown>"
            ft = _ensure_ft(traces_by_outer, bucket_name)
            ft.calls.append(call)

            # Heuristic: mark certain calls as "external-ish" (push/call/transfer/etc.)
            if func and func.lower() in EXTERNALISH_FUNCS:
                _bump_attr(ft, "external_calls_count", inc=1, default=0)
                if hasattr(ft, "has_external_calls"):
                    try:
                        setattr(ft, "has_external_calls", True)
                    except Exception:
                        pass
                if hasattr(ft, "external_calls_runs"):
                    try:
                        ft.external_calls_runs.append(l)
                    except Exception:
                        pass
            continue

        # Parse "Event:" blocks (count by name if possible)
        if EVENT_BLOCK_MARKER_RE.search(l):
            bucket_name = current_outer or "<unknown>"
            ft = _ensure_ft(traces_by_outer, bucket_name)
            _record_event_line(ft, lines, idx)
            continue

        # Also record "emit log_*(" lines (we don't count them as events)
        if EMIT_LINE_RE.search(l):
            # Keep structure for future, but no counters are updated here.
            bucket_name = current_outer or "<unknown>"
            _ensure_ft(traces_by_outer, bucket_name)
            continue

    return traces_by_outer


# Back-compat alias expected by older imports
parse_foundry_traces = parse_foundry_logs
