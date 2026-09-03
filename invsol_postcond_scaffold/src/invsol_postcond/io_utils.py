from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Union

PathLike = Union[str, Path]

__all__ = [
    "read_json",
    "read_text",
    "load_json",   # aliases for backward-compat
    "load_text",
    "ensure_file",
    "as_path",
    "write_text"
]


def as_path(p: PathLike) -> Path:
    return p if isinstance(p, Path) else Path(p)


def ensure_file(p: PathLike) -> Path:
    path = as_path(p)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if not path.is_file():
        raise IsADirectoryError(f"Expected a file, got a directory: {path}")
    return path


def read_text(p: PathLike, encoding: str = "utf-8") -> str:
    path = ensure_file(p)
    return path.read_text(encoding=encoding)


def read_json(p: PathLike, encoding: str = "utf-8") -> Dict[str, Any]:
    raw = read_text(p, encoding=encoding)
    return json.loads(raw)


# --- Aliases for compatibility with __init__.py imports ---

def load_text(p: PathLike, encoding: str = "utf-8") -> str:
    return read_text(p, encoding=encoding)


def load_json(p: PathLike, encoding: str = "utf-8") -> Dict[str, Any]:
    return read_json(p, encoding=encoding)


def write_text(path: Any, text: str):
    """
    Simple text writer used by CLI for annotated .sol output or .info export.
    Automatically creates parent directories if they don't exist.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
