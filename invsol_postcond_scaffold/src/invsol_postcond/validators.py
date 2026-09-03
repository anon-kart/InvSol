# src/invsol_postcond/validators.py
from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple, Union

from .io_utils import as_path, ensure_file
from .models import ContractIR

PathLike = Union[str, Path]

__all__ = ["ValidationError", "validate_paths", "validate_inputs"]


class ValidationError(Exception):
    """Raised when input arguments fail validation."""


def _check_readable(p: Path) -> None:
    try:
        with p.open("rb"):
            pass
    except Exception as e:
        raise ValidationError(f"File not readable: {p} ({e})") from e


def validate_paths(ir_path: PathLike, logs_path: Optional[PathLike] = None) -> Tuple[Path, Optional[Path]]:
    """
    Normalize & validate the IR json path and (optionally) logs text path.
    Returns (ir_path, logs_path) where logs_path can be None.
    """
    # ---- IR (required) ----
    ir = as_path(ir_path)
    ir = ensure_file(ir)

    if ir.suffix.lower() not in {".json"}:
        raise ValidationError(f"IR path should be a .json file: {ir}")

    _check_readable(ir)

    # ---- Logs (optional) ----
    if logs_path is None:
        return ir, None

    logs = as_path(logs_path)
    logs = ensure_file(logs)

    if logs.suffix.lower() not in {".txt", ".log", ".logs"}:
        raise ValidationError(f"Logs path should be a .txt/.log/.logs file: {logs}")

    _check_readable(logs)

    return ir, logs


def validate_inputs(contract: Optional[ContractIR], logs_text: Optional[str]) -> None:
    """
    Sanity-check already loaded/parsed inputs.
    Raises ValidationError on problems.

    Note: logs_text may be None or empty when logs are omitted.
    """
    if contract is None:
        raise ValidationError("Contract IR object is None (IR parsing likely failed).")

    if not isinstance(contract, ContractIR):
        raise ValidationError(f"Contract IR has unexpected type: {type(contract)!r}")

    if not contract.name:
        raise ValidationError("Contract IR has no name.")

    if not contract.functions or len(contract.functions) == 0:
        raise ValidationError("Contract IR has no functions parsed.")

    # logs_text is optional now; no validation error for None/empty
    if logs_text is not None and not isinstance(logs_text, str):
        raise ValidationError(f"Logs text has unexpected type: {type(logs_text)!r}")
