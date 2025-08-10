"""
decls_writer.py

Generates Daikon .decls content from parsed TraceRuns.
"""

from collections import defaultdict
from model import TraceRun
import logging

# === SETUP LOGGER ===
logging.basicConfig(level=logging.INFO, format="DECLS_LOG: %(message)s")


def most_permissive_type(types: set) -> str:
    if "string" in types:
        return "string"
    if "hashcode" in types:
        return "hashcode"
    return "int"


def generate_decls(trace_runs: list[TraceRun]) -> tuple[str, dict]:
    """
    Returns:
      - The .decls file content as a single string
      - A dict mapping ppt_name -> {var_name -> type}, for use in dtrace writing
    """

    logging.info("=================== START generate_decls ===================")

    # 1. Track variables and their types *per PPT*
    ppt_var_types = defaultdict(lambda: defaultdict(set))  # ppt_name -> var_name -> set of types

    logging.info("[STEP 1] Collecting variables and types PER PPT")
    for run in trace_runs:
        logging.info(f"  RUN nonce={run.invocation_nonce}")
        for ppt in run.program_points:
            logging.info(f"    PPT: {ppt.name}")
            for var in ppt.variables.values():
                # Distinguish user vs user.toString properly
                if var.name.lower() == "user":
                    var_type = "hashcode"  # treat as unquoted 0x address
                elif var.name.lower().endswith(".tostring"):
                    var_type = "string"    # treat as quoted string
                else:
                    var_type = var.type
                ppt_var_types[ppt.name][var.name].add(var_type)
                logging.info(f"      VAR: {var.name}   TYPE SEEN: {var_type}")

    logging.info("\n[INFO] Collected raw types PER PPT:")
    for ppt_name, var_map in sorted(ppt_var_types.items()):
        logging.info(f"  - {ppt_name}")
        for var_name, types in sorted(var_map.items()):
            logging.info(f"      * {var_name}: {sorted(types)}")

    # 2. Resolve most-permissive type for each variable IN ITS PPT
    ppt_declared_vars = {}
    logging.info("\n[STEP 2] Resolving most-permissive types PER PPT")
    for ppt_name, var_map in ppt_var_types.items():
        ppt_declared_vars[ppt_name] = {}
        logging.info(f"  PPT: {ppt_name}")
        for var_name, types in var_map.items():
            chosen = most_permissive_type(types)
            ppt_declared_vars[ppt_name][var_name] = chosen
            logging.info(f"    - {var_name}: chosen_type={chosen}")

    # 3. Emit .decls content
    logging.info("\n[STEP 3] Writing .decls text")
    lines = []
    lines.append("decl-version 2.0")
    lines.append("var-comparability none")
    lines.append("")  # Blank line after header

    for ppt_name in sorted(ppt_declared_vars.keys()):
        lines.append(f"ppt {ppt_name}")
        if ppt_name.endswith(":::ENTER"):
            lines.append("ppt-type enter")
        elif ppt_name.endswith(":::EXIT") or ppt_name.endswith(":::EXIT0"):
            lines.append("ppt-type exit")
        else:
            lines.append("ppt-type unknown")

        # Always include synthetic variables
        lines.append("variable this")
        lines.append("  var-kind variable")
        lines.append("  dec-type Bank")
        lines.append("  rep-type hashcode")
        lines.append("  flags is_param non_null")
        lines.append("  comparability 0")

        lines.append("variable this_invocation_nonce")
        lines.append("  var-kind variable")
        lines.append("  dec-type long")
        lines.append("  rep-type int")
        lines.append("  comparability 0")

        # Actual variables for this ppt only
        for var_name, var_type in sorted(ppt_declared_vars[ppt_name].items()):
            if ".toString" in var_name:
                enclosing = var_name.split(".")[0]
                lines.append(f"variable {var_name}")
                lines.append("  var-kind function toString()")
                lines.append(f"  enclosing-var {enclosing}")
                lines.append("  dec-type java.lang.String")
                lines.append("  rep-type java.lang.String")
                lines.append(f"  function-args {enclosing}")
                lines.append("  flags synthetic to_string")
                lines.append("  comparability 0")
            else:
                lines.append(f"variable {var_name}")
                lines.append("  var-kind variable")
                if var_type == "int":
                    lines.append("  dec-type long")
                    lines.append("  rep-type int")
                elif var_type == "hashcode":
                    lines.append("  dec-type java.lang.String")
                    lines.append("  rep-type hashcode")
                else:
                    lines.append("  dec-type java.lang.String")
                    lines.append("  rep-type java.lang.String")
                lines.append("  comparability 0")

        lines.append("")  # Blank line between ppts

    logging.info("\n=================== END generate_decls ===================")
    return "\n".join(lines), ppt_declared_vars
