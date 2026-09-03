"""
main.py

CLI entry point for converting Foundry fuzz test execution traces
into Daikon-compatible .decls and .dtrace files, or a single combined file.
"""

import argparse
import sys
import logging
from pathlib import Path

from parser import parse_trace_file
from decls_writer import generate_decls
from dtrace_writer import generate_dtrace

# === SETUP LOGGER ===
logging.basicConfig(
    level=logging.INFO,
    format="MAIN_LOG: %(message)s"
)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(
        description="Convert Foundry fuzz test execution traces to Daikon .decls and .dtrace files, or a single combined file."
    )
    parser.add_argument(
        "input",
        help="Path to Foundry test log file containing execution traces."
    )
    parser.add_argument(
        "--decls", "-d",
        default="contract.decls",
        help="Output path for generated .decls file (default: contract.decls)"
    )
    parser.add_argument(
        "--dtrace", "-t",
        default="contract.dtrace",
        help="Output path for generated .dtrace file (default: contract.dtrace)"
    )
    parser.add_argument(
        "--combined", "-c",
        default=None,
        help="Optional path for writing a single combined .dtrace file"
    )

    args = parser.parse_args()

    logger.info("=================== Starting main() ===================")
    logger.info(f"Input trace file: {args.input}")
    logger.info(f"Output decls file: {args.decls}")
    logger.info(f"Output dtrace file: {args.dtrace}")
    if args.combined:
        logger.info(f"Output combined file: {args.combined}")

    # === Read and parse ===
    logger.info("Reading Foundry execution traces...")
    try:
        trace_runs = parse_trace_file(args.input)
    except Exception as e:
        logger.error(f"Failed to parse trace file: {e}")
        sys.exit(1)

    logger.info(f"Parsed {len(trace_runs)} fuzz runs successfully.")
    if not trace_runs:
        logger.warning("No runs parsed! Exiting.")
        sys.exit(1)

    # === Generate .decls content ===
    try:
        logger.info("Generating .decls content...")
        decls_content, ppt_declared_vars = generate_decls(trace_runs)
        logger.info(f"Generated .decls content size: {len(decls_content)} characters")
        logger.info(f"Number of Ppt entries in .decls: {len(ppt_declared_vars)}")
        for ppt_name in ppt_declared_vars:
            logger.info(f" - Declared variables for {ppt_name}: {list(ppt_declared_vars[ppt_name].keys())}")
    except Exception as e:
        logger.error(f"Failed to generate .decls content: {e}")
        sys.exit(1)

    # === Generate .dtrace content ===
    try:
        logger.info("Generating .dtrace content...")
        dtrace_content = generate_dtrace(trace_runs, ppt_declared_vars)
        logger.info(f"Generated .dtrace content size: {len(dtrace_content)} characters")
    except Exception as e:
        logger.error(f"Failed to generate .dtrace content: {e}")
        sys.exit(1)

    # === Write outputs ===
    if args.combined:
        combined_path = Path(args.combined)
        logger.info(f"Writing single combined file: {combined_path}")
        combined_content = decls_content + "\n" + dtrace_content
        try:
            with open(combined_path, "w", encoding="utf-8") as f:
                f.write(combined_content)
            logger.info(f"✅ Combined file written successfully: {combined_path}")
            logger.info(f"File size: {combined_path.stat().st_size} bytes")
        except Exception as e:
            logger.error(f"Failed to write combined file: {e}")
            sys.exit(1)
    else:
        # Write separate .decls file
        decls_path = Path(args.decls)
        logger.info(f"Writing .decls file: {decls_path}")
        try:
            with open(decls_path, "w", encoding="utf-8") as f:
                f.write(decls_content)
            logger.info(f"✅ Decls file written successfully: {decls_path}")
            logger.info(f"File size: {decls_path.stat().st_size} bytes")
        except Exception as e:
            logger.error(f"Failed to write .decls file: {e}")
            sys.exit(1)

        # Write separate .dtrace file
        dtrace_path = Path(args.dtrace)
        logger.info(f"Writing .dtrace file: {dtrace_path}")
        try:
            with open(dtrace_path, "w", encoding="utf-8") as f:
                f.write(dtrace_content)
            logger.info(f"✅ Dtrace file written successfully: {dtrace_path}")
            logger.info(f"File size: {dtrace_path.stat().st_size} bytes")
        except Exception as e:
            logger.error(f"Failed to write .dtrace file: {e}")
            sys.exit(1)

    logger.info("=================== Done! ===================")

if __name__ == "__main__":
    main()
