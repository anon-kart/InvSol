from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

MARKER = "[INVSOL]"
COUNTER_PREFIX = "__invsol_it"

LOGGABLE = ("uint", "int", "address", "bool", "bytes32")

PRAGMA_RE = re.compile(r"pragma\s+solidity[^;]*;", re.IGNORECASE)
IMPORT_LINE = 'import {console} from "forge-std/console.sol";'


@dataclass
class Edit:
    offset: int
    length: int
    text: str


@dataclass
class LoopProbe:
    loop_id: str
    contract: str
    function: str
    category: str
    depth: int
    counter: str
    index_vars: List[str] = field(default_factory=list)
    watched: List[Tuple[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "loop_id": self.loop_id,
            "contract": self.contract,
            "function": self.function,
            "category": self.category,
            "depth": self.depth,
            "counter": self.counter,
            "index_vars": self.index_vars,
            "watched": [{"name": n, "type": t} for n, t in self.watched],
        }



class SourceIndex:
    """
    Translate solc source positions into Python string positions.

    solc reports a src range as a byte offset and byte length, while Python
    indexes strings by character. Any non-ASCII character in the file, such as
    an arrow or an accented letter in a comment, makes the two disagree and
    shifts every later edit.
    """

    def __init__(self, source: str) -> None:
        self.source = source
        self.ascii_only = source.isascii()
        if self.ascii_only:
            self._map: Dict[int, int] = {}
            return

        self._map = {0: 0}
        byte = 0
        for char_index, ch in enumerate(source):
            byte += len(ch.encode("utf-8"))
            self._map[byte] = char_index + 1

    def char_offset(self, byte_offset: int) -> int:
        if self.ascii_only:
            return byte_offset
        if byte_offset in self._map:
            return self._map[byte_offset]
        candidates = [b for b in self._map if b <= byte_offset]
        return self._map[max(candidates)] if candidates else 0

    def span(self, byte_start: int, byte_length: int) -> Tuple[int, int]:
        start = self.char_offset(byte_start)
        end = self.char_offset(byte_start + byte_length)
        return start, max(0, end - start)

def _parse_src(src: str) -> Optional[Tuple[int, int]]:
    if not src:
        return None
    parts = str(src).split(":")
    if len(parts) < 2:
        return None
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return None


def _is_loggable(sol_type: str) -> bool:
    t = (sol_type or "").strip()
    if not t or "mapping" in t or "[" in t:
        return False
    if t.startswith("struct ") or t.startswith("contract ") or t.startswith("enum "):
        return False
    return t.startswith(LOGGABLE)


def _log_call(label: str, name: str, sol_type: str) -> str:
    t = (sol_type or "").strip()
    if t.startswith("uint") or t.startswith("int"):
        cast = "uint256" if t.startswith("uint") else "int256"
        return f'console.log("{label}", {cast}({name}));'
    if t == "address":
        return f'console.log("{label}", {name});'
    if t == "bool":
        return f'console.log("{label}", {name});'
    if t.startswith("bytes32"):
        # logBytes32 takes no label, so the trace could not say which variable
        # it belonged to. bytes32 and uint256 are the same width.
        return f'console.log("{label}", uint256({name}));'
    return f'console.log("{label}", {name});'


def _watched_for(loop: Dict[str, Any], exclude_declared: bool) -> List[Tuple[str, str]]:
    """
    Variables safe to log outside the loop.

    A name declared in the loop body or in the init clause of a for statement
    is scoped to the loop, so referring to it before or after would not compile.
    Index variables are reported separately at each iteration instead.
    """
    body = loop.get("body_summary") or {}
    types: Dict[str, str] = dict(body.get("carried_types") or {})
    out_of_scope = set(body.get("declared_vars") or []) | set(body.get("indices") or [])

    # A name that is written through an index is a mapping or an array, whatever
    # type was recorded for the element. Logging it by name would not compile.
    for fact in (body.get("mapping_update_facts") or []) + (
        body.get("array_update_facts") or []
    ):
        if fact.get("var"):
            out_of_scope.add(fact["var"])

    out: List[Tuple[str, str]] = []
    for name in body.get("carried_vars") or []:
        if exclude_declared and name in out_of_scope:
            continue
        sol_type = types.get(name, "")
        if _is_loggable(sol_type):
            out.append((name, sol_type))
    return out


def _index_vars(loop: Dict[str, Any]) -> List[str]:
    body = loop.get("body_summary") or {}
    types: Dict[str, str] = dict(body.get("carried_types") or {})
    names = [n for n in (body.get("indices") or []) if n]
    return [n for n in names if _is_loggable(types.get(n, "uint256"))]


def _enter_block(probe: LoopProbe, indent: str) -> str:
    lines = [f"uint256 {probe.counter} = 0;"]
    lines.append(f'console.log("{MARKER} LOOP_ENTER {probe.loop_id}");')
    for name, sol_type in probe.watched:
        lines.append(_log_call(f"{MARKER} ENTER_VAR {probe.loop_id} {name}", name, sol_type))
    body = f"\n{indent}".join(lines)
    return f"{body}\n{indent}"


def _iter_block(probe: LoopProbe, indent: str) -> str:
    lines = [f"{probe.counter}++;"]
    lines.append(f'console.log("{MARKER} LOOP_ITER {probe.loop_id}", {probe.counter});')
    for name in probe.index_vars:
        lines.append(
            _log_call(f"{MARKER} ITER_IDX {probe.loop_id} {name}", name, "uint256")
        )
    for name, sol_type in probe.watched:
        lines.append(_log_call(f"{MARKER} ITER_VAR {probe.loop_id} {name}", name, sol_type))
    return f"\n{indent}".join(lines)


def _exit_block(probe: LoopProbe, indent: str) -> str:
    lines = [f'console.log("{MARKER} LOOP_EXIT {probe.loop_id}", {probe.counter});']
    for name, sol_type in probe.watched:
        lines.append(_log_call(f"{MARKER} EXIT_VAR {probe.loop_id} {name}", name, sol_type))
    return f"\n{indent}".join(lines)


def _indent_at(source: str, offset: int) -> str:
    line_start = source.rfind("\n", 0, offset) + 1
    prefix = source[line_start:offset]
    return re.match(r"[ \t]*", prefix).group(0)



def _span_with_terminator(source: str, start: int, length: int) -> int:
    """
    Extend a statement span to cover its trailing semicolon.

    solc reports the source range of an ExpressionStatement without the
    terminator in some versions. Replacing the reported range alone would drop
    the semicolon from the rewritten statement and leave a stray one behind.
    """
    end = start + length
    if end < len(source) and source[end - 1 : end] == ";":
        return length
    cursor = end
    while cursor < len(source) and source[cursor] in " \t\r\n":
        cursor += 1
    if cursor < len(source) and source[cursor] == ";":
        return cursor + 1 - start
    return length

def _loops_from_ir(ir: Dict[str, Any]) -> List[Dict[str, Any]]:
    contract = ir.get("contract") or {}
    name = contract.get("name") or ""
    out: List[Dict[str, Any]] = []
    for fn in contract.get("functions") or []:
        for lp in fn.get("loops") or []:
            record = dict(lp)
            record["_contract"] = name
            record["_function"] = fn.get("name") or ""
            out.append(record)
    return out


def build_edits(source: str, loops: List[Dict[str, Any]]) -> Tuple[List[Edit], List[LoopProbe]]:
    """
    Produce the text edits that add loop probes, plus a manifest describing them.

    Edits are returned in source order. Callers apply them from the end of the
    file backwards so earlier offsets stay valid.
    """
    edits: List[Edit] = []
    probes: List[LoopProbe] = []
    index = SourceIndex(source)

    for k, loop in enumerate(loops):
        span = _parse_src(loop.get("src") or "")
        body_span = _parse_src(loop.get("body_src") or "")
        if span is None or body_span is None:
            continue

        loop_start, loop_len = index.span(*span)
        body_start, body_len = index.span(*body_span)

        probe = LoopProbe(
            loop_id=loop.get("loop_id") or f"loop{k}",
            contract=loop.get("_contract", ""),
            function=loop.get("_function", ""),
            category=loop.get("category") or "",
            depth=int(loop.get("depth") or 0),
            counter=f"{COUNTER_PREFIX}_{k}",
            index_vars=_index_vars(loop),
            watched=_watched_for(loop, exclude_declared=True),
        )
        probes.append(probe)

        outer_indent = _indent_at(source, loop_start)
        inner_indent = outer_indent + "    "

        edits.append(Edit(loop_start, 0, _enter_block(probe, outer_indent)))

        if loop.get("body_is_block"):
            brace = source.find("{", body_start)
            if brace == -1:
                continue
            block = _iter_block(probe, inner_indent).rstrip("\n")
            edits.append(Edit(brace + 1, 0, f"\n{inner_indent}{block.lstrip()}"))
        else:
            body_len = _span_with_terminator(source, body_start, body_len)
            statement = source[body_start : body_start + body_len].strip()
            if statement and not statement.endswith((";", "}")):
                statement += ";"
            block = _iter_block(probe, inner_indent).rstrip("\n")
            wrapped = (
                "{\n"
                + f"{inner_indent}{block.lstrip()}\n"
                + f"{inner_indent}{statement}\n"
                + f"{outer_indent}}}"
            )
            edits.append(Edit(body_start, body_len, wrapped))
            loop_len = max(loop_len, body_start + body_len - loop_start)

        loop_end = loop_start + loop_len
        exit_text = _exit_block(probe, outer_indent)
        edits.append(Edit(loop_end, 0, f"\n{outer_indent}{exit_text}"))

    edits.sort(key=lambda e: e.offset)
    return edits, probes


def apply_edits(source: str, edits: List[Edit]) -> str:
    out = source
    for edit in sorted(edits, key=lambda e: e.offset, reverse=True):
        out = out[: edit.offset] + edit.text + out[edit.offset + edit.length :]
    return out


def add_console_import(source: str) -> str:
    if "forge-std/console.sol" in source:
        return source
    match = PRAGMA_RE.search(source)
    if not match:
        return IMPORT_LINE + "\n" + source
    end = match.end()
    return source[:end] + "\n" + IMPORT_LINE + source[end:]


def instrument(source: str, ir: Dict[str, Any]) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Rewrite a contract so each loop reports its boundaries and per-iteration state.

    Every loop gains a private counter, a LOOP_ENTER line, a LOOP_ITER line for
    each pass through the body, and a LOOP_EXIT line carrying the final count.
    Loop-carried variables are logged alongside, which is what lets downstream
    inference observe intermediate states rather than only the final result.
    """
    loops = _loops_from_ir(ir)
    edits, probes = build_edits(source, loops)
    out = apply_edits(source, edits)
    out = add_console_import(out)
    return out, [p.to_dict() for p in probes]


def main(argv: Optional[List[str]] = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Add loop boundary probes to a Solidity contract.")
    ap.add_argument("contract")
    ap.add_argument("ir")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--manifest")
    args = ap.parse_args(argv)

    source = Path(args.contract).read_text(encoding="utf-8")
    ir = json.loads(Path(args.ir).read_text(encoding="utf-8"))

    out, probes = instrument(source, ir)
    Path(args.out).write_text(out, encoding="utf-8")

    if args.manifest:
        Path(args.manifest).write_text(json.dumps(probes, indent=2), encoding="utf-8")

    print(f"instrumented {len(probes)} loops -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
