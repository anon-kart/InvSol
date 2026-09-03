from __future__ import annotations

from typing import Any, Dict, Optional

VALUE_TRANSFER_MEMBERS = {"transfer", "send"}
LOW_LEVEL_MEMBERS = {"call", "delegatecall", "staticcall", "callcode"}

BUILTIN_GLOBALS = {"msg", "block", "tx", "abi", "type"}

BUILTIN_MEMBERS = {
    "length",
    "push",
    "pop",
    "balance",
    "code",
    "codehash",
    "selector",
    "sender",
    "value",
    "data",
    "sig",
    "origin",
    "gasprice",
    "timestamp",
    "number",
    "difficulty",
    "prevrandao",
    "coinbase",
    "chainid",
    "gaslimit",
    "basefee",
    "encode",
    "encodePacked",
    "encodeWithSelector",
    "encodeWithSignature",
    "decode",
    "wrap",
    "unwrap",
    "min",
    "max",
    "creationCode",
    "runtimeCode",
    "interfaceId",
    "name",
}

_KIND_EXTERNAL = "external"
_KIND_TRANSFER = "transfer"
_KIND_LOW_LEVEL = "low_level"
_KIND_DELEGATECALL = "delegatecall"
_KIND_STATICCALL = "staticcall"
_KIND_INTERNAL = "internal"
_KIND_BUILTIN = "builtin"
_KIND_CAST = "cast"


def _type_string(node: Optional[Dict[str, Any]]) -> str:
    return ((node or {}).get("typeDescriptions") or {}).get("typeString") or ""


def _root_identifier(node: Optional[Dict[str, Any]]) -> str:
    if not isinstance(node, dict):
        return ""
    nt = node.get("nodeType")
    if nt == "Identifier":
        return node.get("name") or ""
    if nt == "IndexAccess":
        return _root_identifier(node.get("baseExpression"))
    if nt == "MemberAccess":
        return _root_identifier(node.get("expression"))
    if nt == "FunctionCall":
        if (node.get("kind") or "") == "typeConversion":
            args = node.get("arguments") or []
            if args:
                return _root_identifier(args[0])
        return _root_identifier(node.get("expression"))
    return ""


def _is_address_like(type_string: str) -> bool:
    """
    True only for a single account handle. An array or mapping of addresses is
    a container, so calls on it (push, pop) stay inside the contract.
    """
    t = type_string.strip()
    if not t:
        return False
    head = t.split(" ")[0]
    if "[" in head or head.startswith("mapping"):
        return False
    return head == "address" or head == "address payable" or t.startswith("contract ")


def classify_call(fc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Classify a FunctionCall node.

    Returns a record with:
        kind      one of external, transfer, low_level, delegatecall, staticcall,
                  internal, builtin, cast
        callee    the invoked member or function name
        receiver  rendered receiver expression for member calls, otherwise ""
        external  True when the call can hand control to another account
    """
    empty = {"kind": _KIND_INTERNAL, "callee": "", "receiver": "", "external": False}
    if not isinstance(fc, dict) or fc.get("nodeType") != "FunctionCall":
        return empty

    if (fc.get("kind") or "") == "typeConversion":
        return {"kind": _KIND_CAST, "callee": "", "receiver": "", "external": False}

    expr = fc.get("expression") or {}
    nt = expr.get("nodeType")

    if nt == "Identifier":
        return {
            "kind": _KIND_INTERNAL,
            "callee": expr.get("name") or "",
            "receiver": "",
            "external": False,
        }

    if nt != "MemberAccess":
        return empty

    member = expr.get("memberName") or ""
    base = expr.get("expression") or {}
    base_root = _root_identifier(base)
    base_type = _type_string(base)

    if base_root in BUILTIN_GLOBALS:
        return {
            "kind": _KIND_BUILTIN,
            "callee": member,
            "receiver": base_root,
            "external": False,
        }

    if member in VALUE_TRANSFER_MEMBERS and _is_address_like(base_type):
        return {
            "kind": _KIND_TRANSFER,
            "callee": member,
            "receiver": base_root,
            "external": True,
        }

    if member == "delegatecall":
        return {
            "kind": _KIND_DELEGATECALL,
            "callee": member,
            "receiver": base_root,
            "external": True,
        }

    if member == "staticcall":
        return {
            "kind": _KIND_STATICCALL,
            "callee": member,
            "receiver": base_root,
            "external": False,
        }

    if member in LOW_LEVEL_MEMBERS:
        return {
            "kind": _KIND_LOW_LEVEL,
            "callee": member,
            "receiver": base_root,
            "external": True,
        }

    if member in BUILTIN_MEMBERS and not _is_address_like(base_type):
        return {
            "kind": _KIND_BUILTIN,
            "callee": member,
            "receiver": base_root,
            "external": False,
        }

    if _is_address_like(base_type):
        return {
            "kind": _KIND_EXTERNAL,
            "callee": member,
            "receiver": base_root,
            "external": True,
        }

    if base_type.startswith("library "):
        return {
            "kind": _KIND_INTERNAL,
            "callee": member,
            "receiver": base_root,
            "external": False,
        }

    if base_root == "this":
        return {
            "kind": _KIND_EXTERNAL,
            "callee": member,
            "receiver": base_root,
            "external": True,
        }

    if base_type:
        return {
            "kind": _KIND_INTERNAL,
            "callee": member,
            "receiver": base_root,
            "external": False,
        }

    return {
        "kind": _KIND_EXTERNAL,
        "callee": member,
        "receiver": base_root,
        "external": True,
    }


def is_external_call(fc: Dict[str, Any]) -> bool:
    return bool(classify_call(fc).get("external"))
