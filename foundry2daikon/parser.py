"""
parser.py

Parses Foundry fuzz test logs into structured TraceRun objects
with ProgramPoints and VariableInstances.
"""

import re
from model import TraceRun, ProgramPoint, VariableInstance

ALLOWED_FUNCTIONS = {
    "deposit", "withdraw", "transfer", "mint", "burn",
    "buy", "sell", "stake", "unstake", "open", "close",
    "create", "destroy", "update", "approve",
    "accumulateDeposits_basic", "appendMany_basic",
    "bubbleSortLocal_basic", "deposit_basic",
    "fillSequence_basic", "firstGreaterThan_basic",
    "gridDims_basic", "numbersLen_basic", "pushRow_basic",
    "scaledAddToGrid_basic", "sumGridDots_basic",
    "sumNumbersBounded_basic", "sumUnchecked_basic",
    "triangularAccumulate_basic"
}

# === DEFAULT OUTPUT SUFFIX HINTS ===
DEFAULT_OUTPUT_HINT_KEYWORDS = [
    "After", "Result", "New", "Out", "Updated", "Post", "Final", "Sum"
]

# Regex to detect ENTER/EXIT
ENTER_PATTERN = re.compile(r":::ENTER\s*-?\s*(\w+)")
EXIT_PATTERN = re.compile(r":::EXIT\s*-?\s*(\w+)")
FUNC_CALL_PATTERN = re.compile(r'(\w+)::(\w+)\((.*?)\)')

def parse_trace_file(path: str, output_keywords=None) -> list[TraceRun]:
    with open(path, encoding='utf-8') as f:
        text = f.read()
    return parse_trace_text(text, output_keywords=output_keywords)


def parse_trace_text(text: str, output_keywords=None) -> list[TraceRun]:
    """
    Parses the entire Foundry log text into a list of TraceRun objects.
    Supports both classic Bank traces and modern Foundry traces with :::ENTER/EXIT.
    """
    if output_keywords is None or not output_keywords:
        output_keywords = DEFAULT_OUTPUT_HINT_KEYWORDS

    runs = []
    invocation_nonce = 1

    # Split by "Traces:" blocks — each corresponds roughly to a single test
    trace_chunks = text.split("Traces:")
    for chunk in trace_chunks:
        lines = chunk.splitlines()
        if not any(":::" in line for line in lines):
            continue

        current_function = None
        current_contract = None
        program_points = []
        all_emitted_vars = {}

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Detect :::ENTER or :::EXIT
            enter_m = ENTER_PATTERN.search(line)
            exit_m = EXIT_PATTERN.search(line)

            if enter_m:
                fn = enter_m.group(1)
                current_function = fn
                all_emitted_vars = {}
                continue

            if exit_m:
                fn = exit_m.group(1)
                # Flush program points if we have anything
                if current_function and all_emitted_vars:
                    enter_ppt, exit_ppt = make_enter_exit_program_points(
                        current_function,
                        all_emitted_vars,
                        output_keywords,
                        contract_name=current_contract or "Contract"
                    )
                    program_points.append(enter_ppt)
                    program_points.append(exit_ppt)
                current_function = None
                all_emitted_vars = {}
                continue

            # Detect function calls like Bank::deposit(...) or LoopPlayground::fillSequence(...)
            fn_call_match = FUNC_CALL_PATTERN.search(line)
            if fn_call_match:
                current_contract = fn_call_match.group(1)
                function_name = fn_call_match.group(2)

                if current_function and all_emitted_vars:
                    enter_ppt, exit_ppt = make_enter_exit_program_points(
                        current_function,
                        all_emitted_vars,
                        output_keywords,
                        contract_name=current_contract or "Contract"
                    )
                    program_points.append(enter_ppt)
                    program_points.append(exit_ppt)
                    all_emitted_vars = {}

                if is_allowed_function(function_name):
                    current_function = function_name
                else:
                    current_function = None
                continue

            if not current_function:
                continue

            # Match emits (TraceUint / TraceAddress) or Foundry’s log_* style
            emit_match = re.search(r'emit (TraceUint|TraceAddress)\(label: "(.*?)", (val|addr): (.*?)\)', line)
            if not emit_match:
                emit_match = re.search(r'emit log_(string|uint|address)\(val: (.*?)\)', line)

            if emit_match:
                label = ""
                val_raw = ""

                if emit_match.group(1) in ("TraceUint", "TraceAddress"):
                    label = emit_match.group(2)
                    val_raw = emit_match.group(4)
                else:
                    label = "value"
                    val_raw = emit_match.group(2)

                val = clean_val(val_raw)

                if label.lower() == "user":
                    all_emitted_vars[label] = VariableInstance(name=label, type='string', value=val)
                    all_emitted_vars[f"{label}.toString"] = VariableInstance(
                        name=f"{label}.toString", type='string', value=f'"{val}"'
                    )
                else:
                    if looks_like_address(val):
                        all_emitted_vars[label] = VariableInstance(name=label, type='string', value=val)
                        all_emitted_vars[f"{label}.toString"] = VariableInstance(
                            name=f"{label}.toString", type='string', value=f'"{val}"'
                        )
                    else:
                        all_emitted_vars[label] = VariableInstance(name=label, type='int', value=val)
                continue

        # At end of chunk
        if current_function and all_emitted_vars:
            enter_ppt, exit_ppt = make_enter_exit_program_points(
                current_function,
                all_emitted_vars,
                output_keywords,
                contract_name=current_contract or "Contract"
            )
            program_points.append(enter_ppt)
            program_points.append(exit_ppt)

        if program_points:
            runs.append(
                TraceRun(
                    invocation_nonce=invocation_nonce,
                    program_points=program_points
                )
            )
            invocation_nonce += 1

    return runs


def is_allowed_function(function_name: str) -> bool:
    """Accept only functions we explicitly want to track."""
    return function_name in ALLOWED_FUNCTIONS


def is_output_variable(var_name: str, output_keywords: list[str]) -> bool:
    """Determines if a variable name likely indicates an output variable."""
    var_name_lower = var_name.lower()
    return any(keyword.lower() in var_name_lower for keyword in output_keywords)


def make_enter_exit_program_points(function_name: str, all_emitted_vars: dict, output_keywords: list[str], contract_name="Bank") -> tuple[ProgramPoint, ProgramPoint]:
    """Splits the emitted variables into ENTER and EXIT0 ProgramPoints."""
    input_vars = {}
    output_vars = {}

    for var_name, var_instance in all_emitted_vars.items():
        if is_output_variable(var_name, output_keywords):
            output_vars[var_name] = var_instance
        else:
            input_vars[var_name] = var_instance

    enter_ppt = ProgramPoint(
        name=f"{contract_name}.{function_name}(uint256):::ENTER",
        ppt_type="enter",
        variables=input_vars,
    )

    exit_vars = dict(input_vars)
    exit_vars.update(output_vars)

    exit_ppt = ProgramPoint(
        name=f"{contract_name}.{function_name}(uint256):::EXIT0",
        ppt_type="exit",
        variables=exit_vars,
    )

    return enter_ppt, exit_ppt


def clean_val(val_str: str) -> str:
    """Cleans up Foundry's emitted value, stripping any '[...]' annotations."""
    val_str = val_str.strip()
    if '[' in val_str:
        val_str = val_str.split('[')[0].strip()
    return val_str


def looks_like_address(val: str) -> bool:
    """Heuristic to detect if val is an Ethereum-style address."""
    val = val.strip()
    return val.startswith("0x") and len(val) == 42
