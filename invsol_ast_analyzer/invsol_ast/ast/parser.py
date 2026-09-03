import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict

from ..utils.solc_select import select_solc_for


class SolcNotFound(Exception):
    pass


class SolcRunError(Exception):
    pass


class EmptyASTError(Exception):
    pass


ALLOW_PLACEHOLDER_ENV = "INVSOL_ALLOW_PLACEHOLDER_AST"


def _allow_placeholder() -> bool:
    return os.environ.get(ALLOW_PLACEHOLDER_ENV, "").strip().lower() in {"1", "true", "yes"}


def _run(cmd: list) -> str:
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        return out.decode()
    except FileNotFoundError as e:
        raise SolcNotFound("solc was not found on PATH. Install solc or set SOLC_PATH.") from e
    except subprocess.CalledProcessError as e:
        raise SolcRunError(e.output.decode(errors="replace")) from e


def _count_contracts(ast: Any) -> int:
    found = 0

    def walk(node: Any) -> None:
        nonlocal found
        if isinstance(node, dict):
            if node.get("nodeType") == "ContractDefinition":
                found += 1
            for value in node.values():
                if isinstance(value, (dict, list)):
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                if isinstance(item, (dict, list)):
                    walk(item)

    walk(ast)
    return found


def _placeholder(path: Path, note: str) -> Dict[str, Any]:
    return {"source": str(path), "ast": {"nodes": [], "note": note}}


def _strip_solc_banner(output: str) -> str:
    text = output.lstrip()
    if text.startswith("{"):
        return text
    start = text.find("{")
    return text[start:] if start != -1 else text


def _select_ast(data: Any) -> Any:
    if not isinstance(data, dict):
        return None
    if "sources" in data:
        for _, v in (data.get("sources") or {}).items():
            if isinstance(v, dict):
                return v.get("ast", v)
        return None
    return data


def _failure_message(p: Path, compact_error: str, std_error: str) -> str:
    lines = [
        f"solc could not produce a usable AST for {p}.",
        "",
        "This normally means the pragma does not match the installed solc, or the",
        "file has a compile error. Check with:",
        "    solc --version",
        f"    solc --ast-compact-json {p}",
        "",
    ]
    if compact_error:
        lines += ["--- compact JSON attempt ---", compact_error.strip(), ""]
    if std_error:
        lines += ["--- standard JSON attempt ---", std_error.strip()]
    return "\n".join(lines)


def parse_solidity_to_ast(path: str) -> Dict[str, Any]:
    """
    Obtain the solc AST for a contract.

    Compact JSON is tried first, then standard JSON. When both fail the solc
    error is raised rather than swallowed, because an empty AST silently turns
    every later stage of the pipeline into a no-op.

    Set INVSOL_ALLOW_PLACEHOLDER_AST=1 to keep the older behaviour of returning
    an empty AST, which is only useful when developing without solc installed.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Solidity file not found: {path}")

    solc, reason = select_solc_for(str(p))
    if solc is None:
        if _allow_placeholder():
            return _placeholder(p, "no matching solc; placeholder AST returned")
        raise SolcNotFound(
            f"No usable solc for {p}.\n{reason}\n"
            f"Set SOLC_PATH to force one, or set {ALLOW_PLACEHOLDER_ENV}=1 to "
            "continue with an empty AST."
        )

    compact_error = ""
    try:
        output = _run([solc, "--ast-compact-json", str(p)])
        data = json.loads(_strip_solc_banner(output))
        ast = _select_ast(data)
        if ast is not None and _count_contracts(ast) > 0:
            return {"source": str(p), "ast": ast}
        compact_error = "compact AST contained no ContractDefinition node"
    except (SolcRunError, json.JSONDecodeError) as e:
        compact_error = str(e)

    std_input = {
        "language": "Solidity",
        "sources": {p.name: {"urls": [str(p.resolve())]}},
        "settings": {"outputSelection": {"*": {"*": ["*"], "": ["ast"]}}},
    }
    try:
        raw = subprocess.check_output(
            [solc, "--standard-json"],
            input=json.dumps(std_input).encode(),
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError as e:
        raise SolcRunError(
            _failure_message(p, compact_error, e.output.decode(errors="replace"))
        ) from e

    try:
        data = json.loads(raw.decode(errors="replace"))
    except json.JSONDecodeError as e:
        raise SolcRunError(
            _failure_message(p, compact_error, raw.decode(errors="replace")[:2000])
        ) from e

    fatal = [d for d in (data.get("errors") or []) if (d.get("severity") or "") == "error"]

    ast = None
    for _, src in (data.get("sources") or {}).items():
        if isinstance(src, dict) and "ast" in src:
            ast = src["ast"]
            break

    if ast is not None and _count_contracts(ast) > 0:
        return {"source": str(p), "ast": ast}

    detail = "\n".join(
        d.get("formattedMessage") or d.get("message") or "" for d in fatal
    ).strip()
    if not detail:
        detail = "solc produced no ContractDefinition node for this file."

    if _allow_placeholder():
        return _placeholder(p, "solc produced no usable AST; placeholder returned")

    raise EmptyASTError(_failure_message(p, compact_error, detail))
