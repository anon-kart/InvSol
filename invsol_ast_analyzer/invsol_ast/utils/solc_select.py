from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

Version = Tuple[int, int, int]

PRAGMA_RE = re.compile(r"pragma\s+solidity\s+([^;]+);", re.IGNORECASE)
VERSION_RE = re.compile(r"(\d+)\.(\d+)(?:\.(\d+))?")
COMPARATOR_RE = re.compile(r"(\^|~|>=|<=|>|<|=)?\s*v?(\d+\.\d+(?:\.\d+)?)")

SOLC_SELECT_DIR = Path.home() / ".solc-select" / "artifacts"
SOLCX_DIR = Path.home() / ".solcx"


def parse_version(text: str) -> Optional[Version]:
    m = VERSION_RE.search(text.strip())
    if not m:
        return None
    major, minor, patch = m.group(1), m.group(2), m.group(3)
    return (int(major), int(minor), int(patch) if patch is not None else 0)


def read_pragma(source_path: str) -> str:
    """
    Return the raw version constraint from the first solidity pragma, or "".
    """
    try:
        text = Path(source_path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    m = PRAGMA_RE.search(text)
    return m.group(1).strip() if m else ""


def _caret_upper(v: Version) -> Version:
    major, minor, _ = v
    if major == 0:
        return (0, minor + 1, 0)
    return (major + 1, 0, 0)


def _tilde_upper(v: Version) -> Version:
    major, minor, _ = v
    return (major, minor + 1, 0)


def constraint_bounds(pragma: str) -> List[Tuple[str, Version]]:
    """
    Turn a pragma constraint into a list of (operator, version) bounds.

    Handles the forms that appear in practice: an exact pin, a caret or tilde
    range, and explicit comparators combined with whitespace or ||.
    """
    bounds: List[Tuple[str, Version]] = []
    for chunk in re.split(r"\|\|", pragma):
        for m in COMPARATOR_RE.finditer(chunk):
            op = m.group(1) or "="
            v = parse_version(m.group(2))
            if v is None:
                continue
            if op == "^":
                bounds.append((">=", v))
                bounds.append(("<", _caret_upper(v)))
            elif op == "~":
                bounds.append((">=", v))
                bounds.append(("<", _tilde_upper(v)))
            else:
                bounds.append((op, v))
        break
    return bounds


def satisfies(version: Version, pragma: str) -> bool:
    bounds = constraint_bounds(pragma)
    if not bounds:
        return True
    for op, target in bounds:
        if op == "=" and version != target:
            return False
        if op == ">=" and version < target:
            return False
        if op == ">" and version <= target:
            return False
        if op == "<=" and version > target:
            return False
        if op == "<" and version >= target:
            return False
    return True


def discover_solc_binaries() -> Dict[Version, str]:
    """
    Locate every solc binary this machine can offer.

    Looks at the solc-select artifact directory, the py-solc-x cache, and any
    solc on PATH.
    """
    found: Dict[Version, str] = {}

    if SOLC_SELECT_DIR.is_dir():
        for entry in SOLC_SELECT_DIR.iterdir():
            if not entry.is_dir():
                continue
            v = parse_version(entry.name)
            if v is None:
                continue
            for candidate in (entry / f"solc-{v[0]}.{v[1]}.{v[2]}", entry / "solc"):
                if candidate.is_file() and os.access(candidate, os.X_OK):
                    found[v] = str(candidate)
                    break

    if SOLCX_DIR.is_dir():
        for entry in SOLCX_DIR.iterdir():
            if not entry.is_file() or not entry.name.startswith("solc-v"):
                continue
            v = parse_version(entry.name)
            if v is not None and os.access(entry, os.X_OK):
                found.setdefault(v, str(entry))

    on_path = shutil.which("solc")
    if on_path:
        v = version_of(on_path)
        if v is not None:
            found.setdefault(v, on_path)

    return found


def version_of(solc_path: str) -> Optional[Version]:
    try:
        out = subprocess.check_output(
            [solc_path, "--version"], stderr=subprocess.STDOUT, timeout=30
        ).decode(errors="replace")
    except (OSError, subprocess.SubprocessError):
        return None
    m = re.search(r"Version:\s*(\d+\.\d+\.\d+)", out)
    return parse_version(m.group(1)) if m else None


def select_solc_for(source_path: str) -> Tuple[Optional[str], str]:
    """
    Choose the solc binary whose version satisfies the file's pragma.

    Returns (path_or_None, explanation). SOLC_PATH always wins when set, so an
    operator can override the choice.
    """
    override = os.environ.get("SOLC_PATH")
    if override:
        return override, f"SOLC_PATH override: {override}"

    pragma = read_pragma(source_path)
    available = discover_solc_binaries()

    if not available:
        return None, "No solc binary was found on PATH, in ~/.solc-select, or in ~/.solcx."

    if not pragma:
        best = max(available)
        return available[best], f"No pragma found; using solc {_fmt(best)}."

    matching = sorted(v for v in available if satisfies(v, pragma))
    if matching:
        chosen = matching[-1]
        return available[chosen], f"pragma '{pragma}' satisfied by solc {_fmt(chosen)}."

    have = ", ".join(_fmt(v) for v in sorted(available))
    return None, (
        f"pragma '{pragma}' is not satisfied by any installed solc.\n"
        f"Installed: {have}\n"
        f"Install a matching one with: solc-select install <version>"
    )


def _fmt(v: Version) -> str:
    return f"{v[0]}.{v[1]}.{v[2]}"


def format_version(v: Version) -> str:
    return _fmt(v)
