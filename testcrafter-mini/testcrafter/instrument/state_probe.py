from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .loop_probe import Edit, SourceIndex, add_console_import, apply_edits

MARKER = "[INVSOL]"
MAX_ARRAY_ELEMENTS = 8
SCALAR_PREFIXES = ("uint", "int", "address", "bool", "bytes32")


@dataclass
class StateProbe:
    """What was logged at one function's boundary."""

    contract: str
    function: str
    scalars: List[Tuple[str, str]] = field(default_factory=list)
    arrays: List[Tuple[str, str]] = field(default_factory=list)
    mapping_keys: List[Tuple[str, str, str]] = field(default_factory=list)
    struct_keys: List[Tuple[str, str]] = field(default_factory=list)
    exit_points: int = 0
    skipped_returns: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contract": self.contract,
            "function": self.function,
            "scalars": [{"name": n, "type": t} for n, t in self.scalars],
            "arrays": [{"name": n, "type": t} for n, t in self.arrays],
            "mapping_keys": [
                {"name": n, "key": k, "value_type": v} for n, k, v in self.mapping_keys
            ],
            "struct_keys": [{"name": n, "key": k} for n, k in self.struct_keys],
            "exit_points": self.exit_points,
            "skipped_returns": self.skipped_returns,
        }


def _parse_src(src: Any) -> Optional[Tuple[int, int]]:
    if not src:
        return None
    parts = str(src).split(":")
    if len(parts) < 2:
        return None
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return None


def _is_scalar(sol_type: str) -> bool:
    t = (sol_type or "").strip()
    if not t or "mapping" in t or "[" in t:
        return False
    return t.startswith(SCALAR_PREFIXES)


def _is_array(sol_type: str) -> bool:
    t = (sol_type or "").strip()
    return "[" in t and "mapping" not in t


def _element_type(sol_type: str) -> str:
    """
    The type one indexing step removes.

    Only the last array suffix comes off, so the element of uint256[][] is
    uint256[] and not uint256. Splitting on the first bracket instead would
    claim a row of a grid is a plain integer, and the probe generated from that
    does not compile.
    """
    t = (sol_type or "").strip()
    if not t.endswith("]"):
        return t
    opening = t.rfind("[")
    if opening == -1:
        return t
    return t[:opening].strip()


def _cast(name: str, sol_type: str) -> str:
    """
    Widen a value to something console.log has an overload for.

    forge-std has no console.log taking a bytes32, but bytes32 and uint256 are
    the same width and convert explicitly, so the value survives.
    """
    t = (sol_type or "").strip()
    if t.startswith("uint"):
        return f"uint256({name})"
    if t.startswith("int"):
        return f"int256({name})"
    if t.startswith("bytes32"):
        return f"uint256({name})"
    return name


def _struct_fields(contract: Dict[str, Any]) -> Dict[str, List[Tuple[str, str]]]:
    """Scalar fields of each struct, by struct name."""
    state = contract.get("state") or {}
    out: Dict[str, List[Tuple[str, str]]] = {}
    for struct in state.get("structs") or []:
        name = struct.get("name") or ""
        if not name:
            continue
        out[name] = [
            (f.get("name") or "", str(f.get("type") or ""))
            for f in struct.get("fields") or []
            if f.get("name") and _is_scalar(str(f.get("type") or ""))
        ]
    return out


def _struct_named(sol_type: str) -> str:
    """The struct name inside a type string, if it names one."""
    token = (sol_type or "").strip()
    if token.startswith("struct "):
        token = token[len("struct "):]
    token = token.split()[0] if token else ""
    return token.split(".")[-1]


def _state_of(contract: Dict[str, Any]) -> Tuple[
    List[Tuple[str, str]],
    List[Tuple[str, str]],
    Dict[str, str],
    Dict[str, str],
]:
    state = contract.get("state") or {}
    scalars: List[Tuple[str, str]] = []
    arrays: List[Tuple[str, str]] = []
    mappings: Dict[str, str] = {}
    key_types: Dict[str, str] = {}

    for variable in state.get("variables") or []:
        name = variable.get("name") or ""
        sol_type = str(variable.get("type") or "")
        if not name:
            continue
        if "mapping" in sol_type:
            continue
        if _is_array(sol_type):
            arrays.append((name, sol_type))
        elif _is_scalar(sol_type):
            scalars.append((name, sol_type))

    for entry in state.get("mappings") or []:
        name = entry.get("name") or ""
        value = str(entry.get("value") or "").strip()
        # A mapping to a struct or a nested mapping has no single value to log.
        if name and _is_scalar(value):
            mappings[name] = value
            key_types[name] = str(entry.get("key") or "").strip()

    return scalars, arrays, mappings, key_types


def _struct_valued_mappings(
    contract: Dict[str, Any], fields: Dict[str, List[Tuple[str, str]]]
) -> Dict[str, str]:
    """Mappings whose value is a struct we know the fields of."""
    state = contract.get("state") or {}
    out: Dict[str, str] = {}
    for entry in state.get("mappings") or []:
        name = entry.get("name") or ""
        struct = _struct_named(str(entry.get("value") or ""))
        if name and struct in fields and fields[struct]:
            out[name] = struct
    return out


def _touched_struct_keys(
    fn: Dict[str, Any],
    struct_mappings: Dict[str, str],
    fields: Dict[str, List[Tuple[str, str]]],
) -> List[Tuple[str, str, List[Tuple[str, str]]]]:
    """Struct-valued mapping entries this function reads or writes."""
    out: List[Tuple[str, str, List[Tuple[str, str]]]] = []
    seen = set()

    for touch in (fn.get("storage_reads") or []) + (fn.get("storage_writes") or []):
        name = touch.get("var") or ""
        key = touch.get("key")
        if name not in struct_mappings or not key:
            continue
        key = str(key).strip()
        if not key or key.isdigit():
            continue
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", key):
            continue
        if (name, key) in seen:
            continue
        seen.add((name, key))
        out.append((name, key, fields[struct_mappings[name]]))

    return out


def _touched_mapping_keys(
    fn: Dict[str, Any], mappings: Dict[str, str]
) -> List[Tuple[str, str, str]]:
    """
    Mapping entries this function reads or writes, as name and key expression.

    Mappings cannot be enumerated on chain, so the only entries that can be
    recorded are the ones an execution actually touches. Section 3.4.1 calls
    this reconstructing the mapping from observed key accesses.
    """
    out: List[Tuple[str, str, str]] = []
    seen = set()

    for touch in (fn.get("storage_reads") or []) + (fn.get("storage_writes") or []):
        name = touch.get("var") or ""
        key = touch.get("key")
        if name not in mappings or not key:
            continue
        key = str(key).strip()
        if not key or key.isdigit():
            continue
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", key):
            continue
        if (name, key) in seen:
            continue
        seen.add((name, key))
        out.append((name, key, mappings[name]))

    return out


def _key_sources(
    fn: Dict[str, Any],
    mappings: Dict[str, str],
    key_types: Dict[str, str],
    arrays: List[Tuple[str, str]],
) -> List[Tuple[str, str, str]]:
    """
    Mappings this function touches, paired with an array holding their keys.

    Only arrays whose element type matches the mapping's key type qualify, so
    the generated lookup type-checks.
    """
    touched = {
        touch.get("var")
        for touch in (fn.get("storage_reads") or []) + (fn.get("storage_writes") or [])
        if touch.get("var") in mappings
    }
    touched |= {
        effect.get("var")
        for effect in (fn.get("length_effects") or [])
        if effect.get("var") in mappings
    }

    out: List[Tuple[str, str, str]] = []
    for mapping in sorted(n for n in touched if n):
        key_type = key_types.get(mapping, "")
        for array_name, array_type in arrays:
            if _element_type(array_type) == key_type and key_type:
                out.append((mapping, mappings[mapping], array_name))
                break
    return out


def _snapshot_lines(
    phase: str,
    function: str,
    scalars: List[Tuple[str, str]],
    arrays: List[Tuple[str, str]],
    mapping_keys: List[Tuple[str, str, str]],
    struct_keys: List[Tuple[str, str, List[Tuple[str, str]]]],
    key_sources: List[Tuple[str, str, str]],
    indent: str,
) -> List[str]:
    lines = [f'console.log("{MARKER} STATE_{phase} {function}");']

    for name, sol_type in scalars:
        lines.append(
            f'console.log("{MARKER} VAR {function} {name}", {_cast(name, sol_type)});'
        )

    for name, sol_type in arrays:
        lines.append(
            f'console.log("{MARKER} VAR {function} {name}_length", {name}.length);'
        )
        element = _element_type(sol_type)
        if not _is_scalar(element):
            continue
        lines.append(
            f"for (uint256 _p = 0; _p < {name}.length && _p < {MAX_ARRAY_ELEMENTS}; _p++) {{"
        )
        lines.append(
            f'    console.log("{MARKER} ELEM {function} {name}", _p, '
            f"{_cast(f'{name}[_p]', element)});"
        )
        lines.append("}")

    for name, key, value_type in mapping_keys:
        lines.append(
            f'console.log("{MARKER} KEY {function} {name}", {key}, '
            f"{_cast(f'{name}[{key}]', value_type)});"
        )

    for mapping, value_type, array in key_sources:
        # A mapping cannot be enumerated, but a contract that needs to iterate
        # one keeps its keys in an array. Walking that array records entries
        # whose key expression is not in scope at the boundary, such as
        # owed[beneficiaries[i]] written inside a loop.
        lines.append(
            f"for (uint256 _m = 0; _m < {array}.length "
            f"&& _m < {MAX_ARRAY_ELEMENTS}; _m++) {{"
        )
        lines.append(
            f'    console.log("{MARKER} KEY {function} {mapping}", {array}[_m], '
            f"{_cast(f'{mapping}[{array}[_m]]', value_type)});"
        )
        lines.append("}")

    for name, key, fields in struct_keys:
        # A struct has no single value, so each field is recorded separately
        # under the flattened name the Daikon layer expects.
        for field, field_type in fields:
            lines.append(
                f'console.log("{MARKER} FIELD {function} {name}_{field}", {key}, '
                f"{_cast(f'{name}[{key}].{field}', field_type)});"
            )

    return [f"{indent}{line}" for line in lines]


def _indent_at(source: str, offset: int) -> str:
    line_start = source.rfind("\n", 0, offset) + 1
    return re.match(r"[ \t]*", source[line_start:offset]).group(0)


def _inside_a_block(source: str, offset: int) -> bool:
    """
    Whether a statement can be inserted before this offset.

    `if (x) return i;` has a return that is the whole body of the branch. Adding
    a statement in front of it would move the return out of the branch and
    change what the function does, so those are left alone.
    """
    cursor = offset - 1
    while cursor >= 0 and source[cursor] in " \t\r\n":
        cursor -= 1
    if cursor < 0:
        return False
    return source[cursor] in "{;}"


def _callable_functions(contract: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    for fn in contract.get("functions") or []:
        if fn.get("synthetic"):
            continue
        if (fn.get("visibility") or "") not in {"public", "external"}:
            continue
        if (fn.get("mutability") or "") in {"view", "pure"}:
            continue
        if not fn.get("body_src"):
            continue
        out.append(fn)
    return out


def build_edits(source: str, ir: Dict[str, Any]) -> Tuple[List[Edit], List[StateProbe]]:
    """
    Place a state snapshot at the entry and at every exit of each function.

    Exits are every return statement plus the closing brace of the body, so a
    function that leaves early still records its final state.
    """
    contract = ir.get("contract") or ir
    scalars, arrays, mappings, key_types = _state_of(contract)
    fields = _struct_fields(contract)
    struct_mappings = _struct_valued_mappings(contract, fields)
    index = SourceIndex(source)

    edits: List[Edit] = []
    probes: List[StateProbe] = []

    for fn in _callable_functions(contract):
        name = fn.get("name") or ""
        body = _parse_src(fn.get("body_src"))
        if body is None:
            continue

        # solc reports byte offsets; Python indexes characters. One non-ASCII
        # character anywhere earlier in the file shifts every probe.
        start, length = index.span(*body)
        if start >= len(source) or source[start] != "{":
            continue

        keys = _touched_mapping_keys(fn, mappings)
        structs_here = _touched_struct_keys(fn, struct_mappings, fields)
        sources = _key_sources(fn, mappings, key_types, arrays)
        inner = _indent_at(source, start) + "    "

        entry = "\n" + "\n".join(
            _snapshot_lines("ENTER", name, scalars, arrays, keys, structs_here, sources, inner)
        )
        edits.append(Edit(offset=start + 1, length=0, text=entry))

        exits = 0
        skipped = 0
        for src in fn.get("return_srcs") or []:
            parsed = _parse_src(src)
            if parsed is None:
                continue
            span = index.span(*parsed)
            if not _inside_a_block(source, span[0]):
                skipped += 1
                continue
            indent = _indent_at(source, span[0])
            lines = _snapshot_lines("EXIT", name, scalars, arrays, keys, structs_here, sources, indent)
            edits.append(
                Edit(
                    offset=span[0],
                    length=0,
                    text="\n".join(lines).lstrip() + "\n" + indent,
                )
            )
            exits += 1

        close = start + length - 1
        if close < len(source) and source[close] == "}":
            indent = _indent_at(source, close)
            lines = _snapshot_lines("EXIT", name, scalars, arrays, keys, structs_here, sources, indent + "    ")
            edits.append(
                Edit(
                    offset=close,
                    length=0,
                    text="\n".join(lines).lstrip() + "\n" + indent,
                )
            )
            exits += 1

        probes.append(
            StateProbe(
                contract=contract.get("name") or "",
                function=name,
                scalars=scalars,
                arrays=arrays,
                mapping_keys=keys,
                struct_keys=[(n, k) for n, k, _ in structs_here],
                exit_points=exits,
                skipped_returns=skipped,
            )
        )

    return edits, probes


def instrument(source: str, ir: Dict[str, Any]) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Add function-boundary state logging to a contract.

    The loop probes record how state moves within one call. These record what
    the state was before and after the call, which is what the Dynamic
    Invariant Explorer compares across runs.
    """
    edits, probes = build_edits(source, ir)
    if not edits:
        return source, []
    return add_console_import(apply_edits(source, edits)), [p.to_dict() for p in probes]
