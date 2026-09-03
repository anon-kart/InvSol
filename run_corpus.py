from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent
DRIVER = ROOT / "run_invsol_pipeline.py"

PATTERNS = {
    "loops_instrumented": re.compile(r"\[IN\] Instrumented (\d+) loops"),
    "boundaries": re.compile(r"and (\d+) function boundaries"),
    "loop_runs": re.compile(r"\[IN\] Recovered (\d+) loop runs across (\d+) distinct"),
    "snapshots": re.compile(r"\[DE\] (\d+) call snapshots, (\d+) dynamic invariants"),
    "relations": re.compile(r"\[PC\] Relations: (\d+) across"),
    "checked": re.compile(r"\[SA\] Checked (\d+) invariants: (.+)"),
    "candidates": re.compile(r"\[LS\] Primary pass: \d+ lines with mutation markers, (\d+) candidates"),
    "forge": re.compile(r"\[FX\] status\s+(.+)"),
}

SOLC_ERROR = re.compile(r"^Error \((\d+)\): (.+)$", re.MULTILINE)

FAILURE_MARKERS = (
    ("compile", re.compile(r"Compiler run failed")),
    ("loopsynth parse", re.compile(r"Failed to parse (\S+):")),
    ("no traces", re.compile(r"No loop iterations were observed")),
    ("no methods", re.compile(r"Found 0 methods")),
    ("crashed", re.compile(r"^Traceback \(most recent call last\):", re.MULTILINE)),
)


def run_one(contract: Path, fuzz_runs: int, refine: int, timeout: int) -> Dict[str, Any]:
    """
    Run the pipeline on one contract and pull the headline numbers out.

    Everything is captured rather than streamed, because the point is the table
    at the end, not the narration. A contract that crashes or hangs is recorded
    as such instead of stopping the sweep.
    """
    # No --quiet here. The whole point of a per-contract log is to explain a
    # failure, and --quiet is what hides the compiler output that explains it.
    command = [
        sys.executable,
        str(DRIVER),
        str(contract),
        "--refine",
        str(refine),
        "--fuzz-runs",
        str(fuzz_runs),
    ]

    record: Dict[str, Any] = {"contract": contract.name, "failures": []}

    try:
        proc = subprocess.run(
            command,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        record["status"] = "timeout"
        record["failures"].append(f"exceeded {timeout}s")
        return record
    except OSError as exc:
        record["status"] = "error"
        record["failures"].append(str(exc))
        return record

    output = (proc.stdout or "") + (proc.stderr or "")
    record["exit_code"] = proc.returncode
    if proc.returncode != 0:
        record["failures"].append(f"driver exit {proc.returncode}")

    crash = re.search(r"^(\w+(?:\.\w+)*Error): (.+)$", output, re.MULTILINE)
    if crash:
        record["exception"] = f"{crash.group(1)}: {crash.group(2)[:120]}"

    for label, pattern in FAILURE_MARKERS:
        if pattern.search(output):
            record["failures"].append(label)

    forge = PATTERNS["forge"].search(output)
    record["forge"] = forge.group(1).strip() if forge else "not run"

    # A stage that never ran and a stage that ran and found nothing are
    # different outcomes. Missing stays None so the table can show it.
    for key in ("loops_instrumented", "boundaries", "relations", "candidates"):
        found = PATTERNS[key].search(output)
        record[key] = int(found.group(1)) if found else None
    if record["candidates"] is None and "[LS] Running LoopSynth" not in output:
        record["failures"].append("loopsynth never ran")

    runs = PATTERNS["loop_runs"].search(output)
    record["loop_runs"] = int(runs.group(1)) if runs else 0
    record["distinct_loops"] = int(runs.group(2)) if runs else 0

    snapshots = PATTERNS["snapshots"].search(output)
    record["snapshots"] = int(snapshots.group(1)) if snapshots else 0
    record["dynamic_invariants"] = int(snapshots.group(2)) if snapshots else 0

    checked = PATTERNS["checked"].search(output)
    record["checked"] = int(checked.group(1)) if checked else 0
    record["verdicts"] = checked.group(2).strip() if checked else ""

    for path, key in (
        (ROOT / "outputs" / "strategy_table.json", "strategies"),
        (ROOT / "outputs" / "dynamic_invariants.json", "templates"),
    ):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                loaded = json.load(handle)
            record[key] = loaded.get("totals") or loaded.get("tally") or {}
        except (OSError, ValueError):
            record[key] = {}

    # Keep the distinct solc diagnostics so the summary can group contracts
    # that fail for the same reason.
    record["solc_errors"] = sorted(
        {f"{code}: {text.strip()}" for code, text in SOLC_ERROR.findall(output)}
    )

    record["status"] = "ok" if not record["failures"] else "failed"
    record["output"] = output
    return record


def write_report(records: List[Dict[str, Any]], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    slim = [{k: v for k, v in r.items() if k != "output"} for r in records]
    (out_dir / "corpus_report.json").write_text(
        json.dumps(slim, indent=2), encoding="utf-8"
    )

    logs = out_dir / "logs"
    logs.mkdir(exist_ok=True)
    for record in records:
        if "output" in record:
            (logs / f"{record['contract']}.log").write_text(
                record["output"], encoding="utf-8"
            )


def _cell(value: Any, width: int) -> str:
    """Render a missing measurement as a dash, not as zero."""
    return ("-" if value is None else str(value)).rjust(width)


def print_table(records: List[Dict[str, Any]]) -> None:
    header = f"{'contract':26s} {'forge':10s} {'loops':>6s} {'snaps':>6s} {'dyn':>4s} {'rel':>4s} {'cand':>5s}  notes"
    print(header)
    print("-" * len(header))
    for record in records:
        print(
            f"{record['contract']:26s} "
            f"{record.get('forge', '-')[:10]:10s} "
            f"{record.get('distinct_loops', 0):6d} "
            f"{record.get('snapshots', 0):6d} "
            f"{record.get('dynamic_invariants', 0):4d} "
            f"{_cell(record.get('relations'), 4)} "
            f"{_cell(record.get('candidates'), 5)}  "
            + ", ".join(record.get("failures") or [])
        )


def print_totals(records: List[Dict[str, Any]]) -> None:
    ok = [r for r in records if r.get("status") == "ok"]
    print(f"\n{len(ok)} of {len(records)} contracts ran cleanly")

    templates: Dict[str, int] = {}
    strategies: Dict[str, int] = {}
    for record in records:
        for name, count in (record.get("templates") or {}).items():
            templates[name] = templates.get(name, 0) + int(count)
        for name, count in (record.get("strategies") or {}).items():
            strategies[name] = strategies.get(name, 0) + int(count)

    if templates:
        print("\ndynamic invariants by template")
        for name in sorted(templates):
            print(f"  {name:28s} {templates[name]}")
    if strategies:
        print("\nloop invariant candidates by strategy")
        for name in sorted(strategies):
            print(f"  {name:28s} {strategies[name]}")

    failures: Dict[str, List[str]] = {}
    for record in records:
        for reason in record.get("failures") or []:
            failures.setdefault(reason, []).append(record["contract"])
    if failures:
        print("\nfailures")
        for reason in sorted(failures):
            print(f"  {reason:16s} {', '.join(failures[reason])}")

    errors: Dict[str, List[str]] = {}
    for record in records:
        for message in record.get("solc_errors") or []:
            errors.setdefault(message, []).append(record["contract"])
    crashes = {r["contract"]: r["exception"] for r in records if r.get("exception")}
    if crashes:
        print("\nexceptions")
        for contract in sorted(crashes):
            print(f"  {contract:24s} {crashes[contract]}")

    if errors:
        print("\ncompiler errors, grouped")
        for message in sorted(errors, key=lambda m: (-len(errors[m]), m)):
            print(f"  [{len(errors[message])}] {message[:110]}")
            print(f"      {', '.join(errors[message])}")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Run the InvSol pipeline over the benchmark corpus."
    )
    ap.add_argument("--contracts", default="bench/contracts")
    ap.add_argument("--out", default="outputs/corpus")
    ap.add_argument("--fuzz-runs", type=int, default=32)
    ap.add_argument("--refine", type=int, default=1)
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--only", default="", help="substring filter on the file name")
    args = ap.parse_args()

    contracts = sorted((ROOT / args.contracts).glob("*.sol"))
    if args.only:
        contracts = [c for c in contracts if args.only.lower() in c.name.lower()]
    if not contracts:
        print(f"No contracts found under {args.contracts}")
        return

    records: List[Dict[str, Any]] = []
    for position, contract in enumerate(contracts, start=1):
        print(f"[{position}/{len(contracts)}] {contract.name}", flush=True)
        records.append(run_one(contract, args.fuzz_runs, args.refine, args.timeout))

    out_dir = ROOT / args.out
    write_report(records, out_dir)
    print()
    print_table(records)
    print_totals(records)
    print(f"\nReport: {out_dir / 'corpus_report.json'}")
    print(f"Logs:   {out_dir / 'logs'}")


if __name__ == "__main__":
    main()
