from __future__ import annotations
from typing import List
from .models import ContractIR

def render_theory_info(contract: ContractIR, *, contract_name: str) -> str:
    """
    Minimal .info companion file for LoopSynth theory contracts.
    gp.py's read_contract() expects T<name>.sol AND T<name>.info.
    """

    lines: List[str] = []
    lines.append("== Contract ==")
    lines.append(f"T{contract_name}")
    lines.append("")

    # If gp expects sections for bool predicates, we can list placeholders.
    # Many forks accept empty, but the file must exist.
    lines.append("== Predicates ==")
    lines.append("// auto-generated")
    lines.append("")
    return "\n".join(lines)

