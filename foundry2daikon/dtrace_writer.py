"""
dtrace_writer.py

Generates Daikon .dtrace content from parsed TraceRuns.
"""

from model import TraceRun
import logging
import re

# === SETUP LOGGER ===
logging.basicConfig(level=logging.INFO, format="DTRACE_LOG: %(message)s")


def quote_for_daikon_string(val: str) -> str:
    """
    Ensures the value is properly Daikon string-literal quoted.
    Removes existing surrounding quotes if present,
    and escapes any internal quotes.
    """
    val = str(val).strip()
    if val.startswith('"') and val.endswith('"'):
        val = val[1:-1].strip()
    val = val.replace('"', '\\"')
    return f'"{val}"'


def canonicalize_hex_address(val: str) -> str:
    """
    Forces any hashcode-like address to a safe form:
    0x + 40 zeros + last two valid hex digits of the original (or '00' if not valid).
    """
    val = str(val).strip().lower()
    if val.startswith("0x"):
        val = val[2:]

    # Extract last two chars, sanitize to hex
    suffix_raw = val[-2:] if len(val) >= 2 else val
    suffix = re.sub(r'[^0-9a-f]', '0', suffix_raw)
    if len(suffix) < 2:
        suffix = suffix.rjust(2, '0')

    canonical = "0x" + ("0" * 40) + suffix
    return canonical


def generate_dtrace(trace_runs: list[TraceRun], ppt_declared_vars: dict) -> str:
    """
    Given all TraceRuns and the ppt->declared variables mapping,
    generate the Daikon .dtrace file content as a single string.
    """

    logging.info("=================== START generate_dtrace ===================")
    lines = []

    for run_idx, run in enumerate(trace_runs):
        nonce = run.invocation_nonce
        logging.info(f"[RUN {run_idx}] Invocation nonce = {nonce}")

        for ppt_idx, ppt in enumerate(run.program_points):
            ppt_name = ppt.name
            lines.append(f"{ppt_name}")
            logging.info(f"  [PPT {ppt_idx}] Name = {ppt_name}")

            # Synthetic 'this' variable
            lines.append("this")
            lines.append("0x1")
            lines.append("1")
            logging.info("    -> this = 0x1")

            # Synthetic 'this_invocation_nonce'
            lines.append("this_invocation_nonce")
            lines.append(f"{nonce}")
            lines.append("1")
            logging.info(f"    -> this_invocation_nonce = {nonce}")

            # Declared variables for this ppt
            declared_vars = ppt_declared_vars.get(ppt_name, {})
            seen_vars = ppt.variables

            logging.info(f"    -> Declared variables for this PPT ({len(declared_vars)} total):")
            for var_name in sorted(declared_vars.keys()):
                var_type = declared_vars[var_name]
                logging.info(f"       - {var_name}: declared_type={var_type}")

            # Emit values for variables actually declared in this ppt
            logging.info("    -> Emitting values:")
            for var_name in sorted(declared_vars.keys()):
                var_type = declared_vars[var_name]
                lines.append(var_name)

                if var_name in seen_vars:
                    val = seen_vars[var_name].value

                    if var_type == "hashcode":
                        val = canonicalize_hex_address(val)

                    if var_type == "string":
                        formatted_val = quote_for_daikon_string(val)
                    else:
                        formatted_val = str(val)

                    logging.info(f"       - {var_name}: PRESENT -> {formatted_val}")
                    lines.append(formatted_val)
                else:
                    # Proper placeholder by type
                    if var_type == "string":
                        placeholder = '"nonsensical"'
                    elif var_type == "hashcode":
                        placeholder = "0x0"
                    else:
                        placeholder = "nonsensical"
                    logging.info(f"       - {var_name}: MISSING -> {placeholder}")
                    lines.append(placeholder)

                lines.append("1")

            # Blank line between samples
            lines.append("")
            logging.info("    -> END of PPT block\n")

    logging.info("=================== END generate_dtrace ===================")
    return "\n".join(lines).strip() + "\n"
