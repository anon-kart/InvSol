"""
parser.py

Parses Foundry fuzz test logs into structured TraceRun objects
with ProgramPoints and VariableInstances.
"""

import re
from model import TraceRun, ProgramPoint, VariableInstance

ALLOWED_FUNCTIONS = {"deposit", "withdraw", "transfer", "mint", "burn",
    "buy", "sell", "stake", "unstake", "open", "close",
    "create", "destroy", "update", "approve"}

# === DEFAULT OUTPUT SUFFIX HINTS ===
DEFAULT_OUTPUT_HINT_KEYWORDS = [
    "After", "Result", "New", "Out", "Updated", "Post", "Final"
]

def parse_trace_file(path: str, output_keywords=None) -> list[TraceRun]:
    with open(path, encoding='utf-8') as f:
        text = f.read()
    return parse_trace_text(text, output_keywords=output_keywords)

def parse_trace_text(text: str, output_keywords=None) -> list[TraceRun]:
    """
    Parses the entire Foundry log text into a list of TraceRun objects.
    """
    if output_keywords is None or not output_keywords:
        output_keywords = DEFAULT_OUTPUT_HINT_KEYWORDS

    runs = []
    chunks = re.split(r"Ran 1 test for", text)
    invocation_nonce = 1

    for chunk in chunks:
        if "Traces:" not in chunk:
            continue

        lines = chunk.splitlines()
        program_points = []
        current_function = None
        all_emitted_vars = {}

        in_traces_block = False

        for line in lines:
            if 'Traces:' in line:
                in_traces_block = True
                continue

            if not in_traces_block:
                continue

            line = line.strip()

            # Detect ANY function call like Bank::something(...)
            fn_call_match = re.search(r'Bank::(\w+)\((.*?)\)', line)
            if fn_call_match:
                function_name = fn_call_match.group(1)

                # If previous function and variables exist, flush them
                if current_function and all_emitted_vars:
                    # SPLIT into ENTER and EXIT0 program points
                    enter_ppt, exit_ppt = make_enter_exit_program_points(
                        current_function,
                        all_emitted_vars,
                        output_keywords
                    )
                    program_points.append(enter_ppt)
                    program_points.append(exit_ppt)
                    all_emitted_vars = {}

                # Decide if we want to track this function
                if is_allowed_function(function_name):
                    current_function = function_name
                else:
                    current_function = None
                continue

            if not current_function:
                continue  # Only record variables for allowed program points

            # Match emits (TraceUint or TraceAddress)
            emit_match = re.search(r'emit (TraceUint|TraceAddress)\(label: "(.*?)", (val|addr): (.*?)\)', line)
            if emit_match:
                _kind = emit_match.group(1)
                label = emit_match.group(2)
                val_raw = emit_match.group(4)
                val = clean_val(val_raw)

                # ------------- ENFORCE "user" IS ALWAYS STRING ----------------
                if label.lower() == "user":
                    all_emitted_vars[label] = VariableInstance(name=label, type='string', value=val)
                    all_emitted_vars[f"{label}.toString"] = VariableInstance(
                        name=f"{label}.toString",
                        type='string',
                        value=f'"{val}"'
                    )
                else:
                    # auto-detect other addresses vs ints
                    if looks_like_address(val):
                        all_emitted_vars[label] = VariableInstance(name=label, type='string', value=val)
                        all_emitted_vars[f"{label}.toString"] = VariableInstance(
                            name=f"{label}.toString",
                            type='string',
                            value=f'"{val}"'
                        )
                    else:
                        all_emitted_vars[label] = VariableInstance(name=label, type='int', value=val)
                continue

        if current_function:
            if all_emitted_vars:
                # Only emit if we actually saw any Trace emits
                enter_ppt, exit_ppt = make_enter_exit_program_points(
                    current_function,
                    all_emitted_vars,
                    output_keywords
                )
                program_points.append(enter_ppt)
                program_points.append(exit_ppt)
            # else: skip this call entirely


        # Store TraceRun if we have any program points
        if program_points:
            runs.append(TraceRun(
                invocation_nonce=invocation_nonce,
                program_points=program_points
            ))
            invocation_nonce += 1

    return runs

def is_allowed_function(function_name: str) -> bool:
    """
    Accept only functions we explicitly want to track.
    """
    return function_name in ALLOWED_FUNCTIONS

def is_output_variable(var_name: str, output_keywords: list[str]) -> bool:
    """
    Determines if a variable name likely indicates an output variable.
    """
    var_name_lower = var_name.lower()
    return any(keyword.lower() in var_name_lower for keyword in output_keywords)

def make_enter_exit_program_points(function_name: str, all_emitted_vars: dict, output_keywords: list[str]) -> tuple[ProgramPoint, ProgramPoint]:
    """
    Splits the emitted variables into ENTER and EXIT0 ProgramPoints.
    """
    input_vars = {}
    output_vars = {}

    for var_name, var_instance in all_emitted_vars.items():
        if is_output_variable(var_name, output_keywords):
            output_vars[var_name] = var_instance
        else:
            input_vars[var_name] = var_instance

    # Build ENTER point (inputs only)
    enter_ppt = ProgramPoint(
        name=f"Bank.{function_name}(uint256):::ENTER",
        ppt_type="enter",
        variables=input_vars
    )

    # Build EXIT0 point (inputs + outputs)
    exit_vars = dict(input_vars)
    exit_vars.update(output_vars)

    exit_ppt = ProgramPoint(
        name=f"Bank.{function_name}(uint256):::EXIT0",
        ppt_type="exit",
        variables=exit_vars
    )

    return enter_ppt, exit_ppt

def clean_val(val_str: str) -> str:
    """
    Cleans up Foundry's emitted value, stripping any '[...]' annotations.
    E.g. '12345 [1.23e4]' -> '12345'
    """
    val_str = val_str.strip()
    if '[' in val_str:
        val_str = val_str.split('[')[0].strip()
    return val_str

def looks_like_address(val: str) -> bool:
    """
    Heuristic to detect if val is an Ethereum-style address.
    """
    val = val.strip()
    return val.startswith("0x") and len(val) == 42
