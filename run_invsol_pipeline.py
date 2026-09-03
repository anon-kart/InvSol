import argparse
import os
import re
import sys
import shutil
import subprocess
import json
import glob
from pathlib import Path
from typing import Dict, List, Optional, Set

# ----------------------------
#  AST analysis front-end
# ----------------------------
from invsol_ast.pipeline import run_pipeline as run_ast_pipeline
from invsol_ast.utils.solc_select import read_pragma

# ----------------------------
#  TestCrafter integration
# ----------------------------
from testcrafter.config import load_config
from testcrafter.ast_bridge.adapter import load_contract_model
from testcrafter.synthesis.harness_generator import generate_harness
from testcrafter.synthesis.fuzz_plan import plan_for_model
from testcrafter.synthesis.loop_harness import generate_loop_harness
from testcrafter.instrument.loop_probe import instrument as instrument_loops
from testcrafter.instrument.combined import instrument as instrument_all
from testcrafter.instrument.loop_trace import parse_lines, summarise
from testcrafter.instrument.state_trace import parse_lines as parse_state_lines
from testcrafter.instrument.state_trace import summarise as summarise_state
from testcrafter.run.forge_runner import run_forge_test, write_trace, describe

# ----------------------------
#  Postcondition inference
# ----------------------------
from invsol_postcond.io_utils import read_json, read_text, write_text
from invsol_postcond.ast_ir import parse_ast_ir
from invsol_postcond.inference import infer_all
from invsol_postcond.models import InferenceResult

# ✅ LoopSynth theory exporters (T*.sol + T*.info)
from invsol_postcond.theory_exporter import render_theory_sol, render_theory_info
from invsol_postcond.relational import observations_from_summary, derive_for_contract
from invsol_postcond.relational import element_values
from invsol_postcond.templates import explore as explore_dynamic, tally as tally_templates

# ----------------------------
#  Static Code Auditor and refinement
# ----------------------------
from invsol_audit.auditor import audit_contract, summarise as summarise_verdicts
from invsol_audit.auditor import VERDICT_REFUTED, z3_available
from invsol_audit.auditor import audit_contract_invariants
from invsol_audit.refine import (
    RoundSummary,
    has_converged,
    inject_seed_tests,
    priority_functions,
    render_seed_tests,
    seeds_from_verdicts,
)


# ============================================================
#  Utilities: transform InferenceResult into JSON
# ============================================================
def _result_to_dict(r: InferenceResult) -> Dict:
    """Turn a single InferenceResult into a plain dict."""
    return {
        "function": r.function,
        "candidates": [
            {
                **({"expr": getattr(c, "expr", None)} if getattr(c, "expr", None) else {}),
                **(
                    {"description": getattr(c, "description", None)}
                    if getattr(c, "description", None)
                    else {}
                ),
                "holds": getattr(c, "holds", True),
                "falsifying_runs": list(getattr(c, "falsifying_runs", [])),
                "origin": getattr(c, "origin", "ast"),
                "support": getattr(c, "support", 0),
                "scope": getattr(c, "scope", "function"),
                "loop_idx": getattr(c, "loop_idx", None),
            }
            for c in r.candidates
        ],
    }


def _results_as_json(results: List[InferenceResult], pretty: bool = True) -> str:
    """Serialize a collection of inference results to JSON."""
    payload = [_result_to_dict(r) for r in results]
    return json.dumps(payload, indent=2 if pretty else None)


# ============================================================
#  Locate the dynamate-sol root folder
# ============================================================
def _resolve_dynamate_root() -> Path:
    """
    Try to identify the base directory of the dynamate-sol checkout.

    Priority:
      1) Environment variable DYNAMATE_SOL_ROOT
      2) ./dynamate-sol/dynamate-sol
      3) ./dynamate-sol
      4) ~/Desktop/InvSol/dynamate-sol/dynamate-sol
      5) ~/dynamate-sol
    """
    env = os.environ.get("DYNAMATE_SOL_ROOT")
    if env:
        candidate = Path(env).expanduser().resolve()
        if candidate.exists():
            return candidate

    cwd = Path.cwd()
    guesses = [
        cwd / "dynamate-sol" / "dynamate-sol",
        cwd / "dynamate-sol",
        Path.home() / "Desktop" / "InvSol" / "dynamate-sol" / "dynamate-sol",
        Path.home() / "dynamate-sol",
    ]

    for g in guesses:
        if g.exists():
            return g

    # last resort: first guess, even if it might not exist
    return guesses[0]


DAIKON_TIMEOUT = 300


def _daikon_jar() -> Optional[str]:
    """Where Daikon lives, if it is installed at all."""
    candidate = os.environ.get("DAIKON_JAR") or os.environ.get("DAIKONDIR")
    if candidate:
        path = candidate
        if os.path.isdir(path):
            path = os.path.join(path, "daikon.jar")
        if os.path.exists(path):
            return path
    for guess in ("/usr/share/java/daikon.jar", os.path.expanduser("~/daikon/daikon.jar")):
        if os.path.exists(guess):
            return guess
    return None


def _run_daikon(state_calls, contract_base: str, project_root: str) -> None:
    """
    Translate the observed states into Daikon's format and, if Daikon is
    installed, run it over them.

    The translation is always performed, because the .decls and .dtrace pair is
    the Solidity-to-Daikon layer described in Section 3.4.1 and is useful on its
    own. Running the engine needs a jar this project does not ship, so its
    absence is reported rather than treated as a failure.
    """
    bridge_dir = os.path.join(project_root, "foundry2daikon")
    if bridge_dir not in sys.path:
        sys.path.insert(0, bridge_dir)

    out_dir = os.path.join(project_root, "outputs", "daikon")
    try:
        from state_bridge import write_daikon_files

        written = write_daikon_files(state_calls, contract_base, out_dir)
    except Exception as exc:
        print(f"[DK] Could not write the Daikon files: {exc}")
        return

    if not written:
        print("[DK] No call snapshots, nothing to translate")
        return

    decls_path, dtrace_path = written
    print(f"[DK] Wrote {decls_path.name} and {dtrace_path.name} -> {out_dir}")

    jar = _daikon_jar()
    if not jar:
        print(
            "[DK] Daikon is not installed, so only the translation ran. "
            "Set DAIKON_JAR to enable inference."
        )
        return

    inv_path = os.path.join(out_dir, f"{contract_base}.inv.gz")
    command = [
        "java", "-cp", jar, "daikon.Daikon",
        "--no_text_output", "-o", inv_path,
        str(decls_path), str(dtrace_path),
    ]
    try:
        proc = subprocess.run(
            command, capture_output=True, text=True, timeout=DAIKON_TIMEOUT
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"[DK] Daikon did not run: {exc}")
        return

    if proc.returncode != 0:
        print(f"[DK] Daikon exited {proc.returncode}")
        print((proc.stderr or proc.stdout or "").strip()[:400])
        return

    printed = subprocess.run(
        ["java", "-cp", jar, "daikon.PrintInvariants", inv_path],
        capture_output=True, text=True, timeout=DAIKON_TIMEOUT,
    )
    text = printed.stdout or ""
    out_txt = os.path.join(out_dir, f"{contract_base}.daikon.txt")
    write_text(out_txt, text)
    kept = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.startswith("=") and ":::" not in line
    ]
    print(f"[DK] Daikon reported {len(kept)} invariants -> {out_txt}")


def _seed_key(seed) -> tuple:
    """Identity of a seed, so the same failure is not replayed twice."""
    return (
        seed.function,
        seed.loop_id,
        seed.invariant,
        tuple(sorted(seed.arguments.items())),
        tuple(sorted((r.var, r.target, r.nested) for r in seed.shape)),
    )


def _snapshot_round(paths: List[str], rounds_dir: str, round_index: int) -> None:
    """Keep each round's artifacts so a later round cannot destroy an earlier one."""
    target = os.path.join(rounds_dir, f"round_{round_index}")
    os.makedirs(target, exist_ok=True)
    for path in paths:
        if os.path.exists(path):
            shutil.copyfile(path, os.path.join(target, os.path.basename(path)))


def _restore_round(paths: List[str], rounds_dir: str, round_index: int) -> None:
    source = os.path.join(rounds_dir, f"round_{round_index}")
    for path in paths:
        saved = os.path.join(source, os.path.basename(path))
        if os.path.exists(saved):
            shutil.copyfile(saved, path)


def _collect_strategy_table(loopsynth_out_dir: Path, out_json: Path) -> None:
    """
    Gather the per-strategy candidate counts LoopSynth wrote for each method.

    This is the candidate side of Table IX. The verified side comes from the
    Static Code Auditor, which currently checks relations rather than
    LoopSynth output, so the two are reported separately.
    """
    files = sorted(glob.glob(str(loopsynth_out_dir / "*.strategies.json")))
    per_method: Dict[str, Dict] = {}
    totals: Dict[str, int] = {}

    for fname in files:
        try:
            with open(fname, "r", encoding="utf-8") as handle:
                record = json.load(handle)
        except (OSError, ValueError) as exc:
            print(f"[LS] Could not read {fname}: {exc}")
            continue

        method = record.get("method") or Path(fname).stem
        strategies = record.get("strategies") or {}
        per_method[method] = {
            name: {"raw": body.get("raw", 0), "candidates": body.get("candidates", 0)}
            for name, body in strategies.items()
        }
        for name, body in strategies.items():
            totals[name] = totals.get(name, 0) + int(body.get("candidates", 0))

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(
        json.dumps({"totals": totals, "per_method": per_method}, indent=2),
        encoding="utf-8",
    )

    if totals:
        print("[LS] Candidates by mutation strategy:")
        for name in sorted(totals):
            print(f"[LS]   {name:28s} {totals[name]}")
        empty = [name for name, count in totals.items() if count == 0]
        if empty:
            print(
                "[LS] No candidates from: "
                + ", ".join(sorted(empty))
                + ". These strategies need quantified or conditional "
                "postconditions, which the inference stage does not emit yet."
            )
    else:
        print(f"[LS] No strategy tallies found under {loopsynth_out_dir}")


# ============================================================
#  Collect invariants from LoopSynth text outputs
# ============================================================
def _collect_loopsynth_invariants(loopsynth_out_dir: Path, out_txt: Path) -> None:
    """
    Parse all LoopSynth iteration files and extract candidate invariants.

    We first look for lines tagged with:
        [MUTATION] ...
        [RAW MUTATION] ...

    If none are found, we do a simple fallback heuristic over plain lines.
    """
    loopsynth_out_dir = loopsynth_out_dir.resolve()
    out_txt = out_txt.resolve()

    pattern = str(loopsynth_out_dir / "*.iteration_*.v*.txt")
    files = sorted(glob.glob(pattern))

    print(
        f"[LS] Collecting invariants from {len(files)} LoopSynth files matching *.iteration_*.v*.txt"
    )

    all_candidates: Set[str] = set()
    mutation_lines = 0

    MUT_TOK = "[MUTATION]"
    RAW_TOK = "[RAW MUTATION]"

    # main pass: look for explicit mutation markers
    for fname in files:
        with open(fname, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s:
                    continue

                # Only accepted mutations count. A [RAW MUTATION] line is the
                # candidate before filtering, so reading those as well would
                # put every rejected form back into the result.
                if MUT_TOK not in s:
                    continue
                tag = MUT_TOK

                mutation_lines += 1
                expr = _clean_candidate(s.split(tag, 1)[1].strip())
                if expr and not _is_trivial_candidate(expr):
                    all_candidates.add(expr)

    print(
        f"[LS] Primary pass: {mutation_lines} lines with mutation markers, {len(all_candidates)} candidates."
    )

    if mutation_lines == 0:
        raw_lines = 0
        for fname in files:
            with open(fname, "r", encoding="utf-8") as f:
                for line in f:
                    s = line.strip()
                    if RAW_TOK not in s:
                        continue
                    raw_lines += 1
                    expr = _clean_candidate(s.split(RAW_TOK, 1)[1].strip())
                    if expr and not _is_trivial_candidate(expr):
                        all_candidates.add(expr)
        if raw_lines:
            print(
                f"[LS] No accepted mutations; fell back to {raw_lines} raw lines. "
                "Every candidate was rejected by the filter in gp.py."
            )

    # fallback heuristic if absolutely nothing was seen
    if mutation_lines == 0 and not all_candidates:
        print("[LS] No [MUTATION] markers found — falling back to heuristic line filter.")
        allowed_chars = set(
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_()[]<>!=&|+\\-*/:;,. '"
        )
        for fname in files:
            with open(fname, "r", encoding="utf-8") as f:
                for line in f:
                    s = line.strip()
                    if not s:
                        continue
                    if s.startswith("["):
                        continue
                    if not all(ch in allowed_chars for ch in s):
                        continue
                    if not any(op in s for op in ("<", ">", "<=", ">=", "==", "!=", "&&", "||")):
                        continue
                    all_candidates.add(s)

    out_txt.parent.mkdir(parents=True, exist_ok=True)
    with open(out_txt, "w", encoding="utf-8") as f:
        for inv in sorted(all_candidates):
            f.write(inv + "\n")

    print(f"[LS] Wrote {len(all_candidates)} invariants → {out_txt}")


# ============================================================
#  LoopSynth driver (gp.py integration)
# ============================================================
def run_loopsynth(
    contract_base: str,
    theory_sol_path: Path,
    contract_sol_path: Path,
    ir_path: Optional[str] = None,
) -> Path:
    """
    Invoke gp.py (LoopSynth) on the given contract and theory file (T*.sol),
    and summarize the resulting invariants under outputs/loopsynth_invariants.txt.
    """
    theory_sol_path = Path(theory_sol_path).resolve()
    contract_sol_path = Path(contract_sol_path).resolve()
    project_root = Path.cwd().resolve()

    dyn_root = _resolve_dynamate_root()
    gp_py = dyn_root / "ginpink-sol" / "gp.py"

    # gp.py reads theories from a fixed directory. Keep it configurable so the
    # pipeline does not depend on one developer's home directory.
    # Default inside the project so a fresh checkout is self-contained. The
    # override stays for anyone with an existing dynamate-sol tree elsewhere.
    theories_dir = Path(
        os.environ.get(
            "INVSOL_THEORIES_DIR",
            str(Path(project_root) / "outputs" / "theories"),
        )
    )
    theories_dir.mkdir(parents=True, exist_ok=True)

    if not gp_py.exists():
        print("[LS-ERROR] LoopSynth gp.py not found at", gp_py)
        return project_root / "outputs" / "loopsynth"

    print(f"[LS] Using LoopSynth gp.py at {gp_py}")
    print(f"[LS] Using LoopSynth theories at {theories_dir}")

    # Copy the Solidity contract to where gp.py looks for it
    sol_dest = theories_dir / f"{contract_base}.sol"
    print(f"[LS] Copying Solidity contract → {sol_dest}")
    try:
        shutil.copyfile(contract_sol_path, sol_dest)
    except Exception as e:
        print(f"[LS-ERROR] Failed copying .sol file: {e}")

    # Copy the generated theory Solidity file as T<Contract>.sol
    theory_dest = theories_dir / f"T{contract_base}.sol"
    print(f"[LS] Copying theory → {theory_sol_path} → {theory_dest}")
    try:
        shutil.copyfile(theory_sol_path, theory_dest)
    except Exception as e:
        print(f"[LS-ERROR] Failed copying theory file: {e}")

    # ✅ ALSO copy companion .info file because gp.py expects it for T*.sol
    theory_info_src = (Path.cwd() / "outputs" / f"T{contract_base}.info").resolve()
    theory_info_dest = theories_dir / f"T{contract_base}.info"
    print(f"[LS] Copying theory info → {theory_info_src} → {theory_info_dest}")
    try:
        shutil.copyfile(theory_info_src, theory_info_dest)
    except Exception as e:
        print(f"[LS-ERROR] Failed copying theory info file: {e}")

    # Prepare the directory where gp.py will write iteration files
    loopsynth_out_dir = project_root / "outputs" / "loopsynth"
    loopsynth_out_dir.mkdir(parents=True, exist_ok=True)

    # Clean everything the previous contract left here. The strategy tallies
    # and tracker pickles are named after the method, not the contract, so a
    # leftover file from an earlier run is counted again and inflates Table IX.
    stale = 0
    for pattern in ("*.iteration_*.v*.txt", "*.strategies.json", "*.pkl"):
        for f in loopsynth_out_dir.glob(pattern):
            try:
                f.unlink()
                stale += 1
            except OSError:
                pass
    if stale:
        print(f"[LS] Removed {stale} files from a previous run")

    # Command line for gp.py
    cmd = [
        sys.executable,
        str(gp_py),
        "-T",
        str(theories_dir),
        contract_base,
    ]

    # Hand LoopSynth the loop-bearing methods the analyzer already found, so it
    # does not have to re-parse the contract with a parser that fails on some
    # modern syntax.
    if not ir_path:
        print("[LS] No IR path given, LoopSynth will parse the contract itself")
    try:
        model = read_json(ir_path) if ir_path else {}
        ir_contract = model.get("contract") or model
        with_loops = [
            fn.get("name")
            for fn in ir_contract.get("functions") or []
            if fn.get("loops") and fn.get("name") and not fn.get("synthetic")
        ]
        sidecar = Path(theories_dir) / f"{contract_base}.methods.json"
        sidecar.write_text(
            json.dumps({contract_base: with_loops}, indent=2), encoding="utf-8"
        )
        print(f"[LS] Wrote {len(with_loops)} loop methods -> {sidecar}")
    except (OSError, ValueError, KeyError) as exc:
        print(f"[LS] Could not write the method sidecar: {exc}")

    print("[LS] Running LoopSynth...")
    proc = subprocess.run(cmd, cwd=loopsynth_out_dir)
    print(f"[LS] LoopSynth exit code: {proc.returncode}")

    invariants_txt = project_root / "outputs" / "loopsynth_invariants.txt"
    _collect_loopsynth_invariants(loopsynth_out_dir, invariants_txt)
    _collect_strategy_table(
        loopsynth_out_dir, project_root / "outputs" / "strategy_table.json"
    )

    return loopsynth_out_dir


# ============================================================
#  Orchestrate the full InvSol pipeline
# ============================================================


NODE_WRAPPER_RE = re.compile(r"^[A-Za-z_]\w*\((.*)\)$", re.S)
TRIVIAL_RE = re.compile(r"^\s*-?\d+\s*(==|<=|>=|<|>|!=)\s*-?\d+\s*$")


def _clean_candidate(expr: str) -> str:
    """
    Strip an AST node wrapper left on a mutation.

    A candidate printed as BinaryExpression(i <= n) is the node's repr, not
    Solidity, and cannot be handed to a solver or written into a contract.
    """
    text = (expr or "").strip()
    for _ in range(3):
        match = NODE_WRAPPER_RE.match(text)
        if not match:
            break
        inner = match.group(1).strip()
        if not inner or inner == text:
            break
        text = inner
    return text


def _is_trivial_candidate(expr: str) -> bool:
    """
    Drop candidates that compare two constants.

    A relation such as 0 == 1 or -1 <= 2 carries no information about the
    contract and only inflates the candidate count.
    """
    text = (expr or "").strip()
    if not text:
        return True
    if TRIVIAL_RE.match(text):
        return True
    return not re.search(r"[A-Za-z_]", text)


def _clear_stale_artifacts(foundry_project_dir: str, contract_base: str, contract_path: str) -> None:
    """
    Remove generated files left by a previous contract.

    Foundry compiles everything under test/ and src/, so a harness from an
    earlier run still refers to a contract that is no longer there, and the
    whole project fails to build before any test executes.
    """
    keep_sol = os.path.basename(contract_path)
    test_dir = os.path.join(foundry_project_dir, "test")
    src_dir = os.path.join(foundry_project_dir, "src")

    for path in glob.glob(os.path.join(test_dir, "*_Harness.t.sol")) + glob.glob(
        os.path.join(test_dir, "*_LoopHarness.t.sol")
    ):
        stem = os.path.basename(path).split("_Harness")[0].split("_LoopHarness")[0]
        if stem != contract_base:
            os.remove(path)

    for path in glob.glob(os.path.join(src_dir, "*.sol")):
        name = os.path.basename(path)
        if name == keep_sol or name == "Counter.sol":
            continue
        if os.path.exists(os.path.join(test_dir, f"{name[:-4]}_Harness.t.sol")):
            continue
        os.remove(path)


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Run the InvSol pipeline on one contract.")
    ap.add_argument("contract")
    ap.add_argument("--timeout", type=int, default=600, help="seconds allowed for forge test")
    ap.add_argument("--fuzz-runs", type=int, default=64)
    ap.add_argument("--no-instrument", action="store_true", help="skip loop probes")
    ap.add_argument(
        "--no-state-probes",
        action="store_true",
        help="skip function-boundary state probes",
    )
    ap.add_argument("--skip-loopsynth", action="store_true")
    ap.add_argument("--quiet", action="store_true", help="do not echo forge output")
    ap.add_argument(
        "--refine",
        type=int,
        default=0,
        help="extra rounds of counterexample-guided fuzzing after the first pass",
    )
    ap.add_argument(
        "--legacy-harness",
        action="store_true",
        help="also emit the template-based harness (assumes ERC20-like shapes)",
    )
    return ap.parse_args()


def main() -> None:
    args = _parse_args()
    contract_path = os.path.abspath(args.contract)

    project_root = os.path.abspath(".")
    ir_out_path = os.path.join(project_root, "outputs", "ir.json")
    config_path = os.path.join(project_root, "data", "config.json")
    foundry_project_dir = os.path.join(project_root, "artifacts", "foundry_project")
    contract_import_path = f"src/{os.path.basename(contract_path)}"
    traces_out_path = os.path.join(project_root, "outputs", "foundry_traces.txt")

    postconds_json_path = os.path.join(project_root, "outputs", "postconditions.json")

    contract_base = os.path.splitext(os.path.basename(contract_path))[0]
    theory_sol_out_path = os.path.join(project_root, "outputs", f"T{contract_base}.sol")
    theory_info_out_path = os.path.join(project_root, "outputs", f"T{contract_base}.info")

    loopsynth_invariants_path = os.path.join(project_root, "outputs", "loopsynth_invariants.txt")

    os.makedirs(os.path.dirname(ir_out_path), exist_ok=True)
    os.makedirs(os.path.dirname(traces_out_path), exist_ok=True)

    # 1) AST → intermediate representation
    print(f"[AST] Analyzing {contract_path}")
    run_ast_pipeline(
        path=contract_path,
        out=ir_out_path,
        solc_path=None,
        validate=True,
        strict=False,
        dump_ast=None,
    )

    # 2) TestCrafter: build harness from IR
    print("[TC] Loading IR model")
    cfg = load_config(config_path)
    cfg["foundry_project_dir"] = foundry_project_dir
    cfg["contract_import_path"] = contract_import_path

    model = load_contract_model(ir_out_path)
    model["name"] = contract_base
    model["pragma"] = read_pragma(contract_path)

    if args.legacy_harness:
        print("[TC] Generating template harness...")
        harness_path = generate_harness(model, cfg)
        print(f"[TC] Harness at: {harness_path}")

    # 3) Record the fuzzing plan derived from requires, loop guards and modifiers
    plans = plan_for_model(read_json(ir_out_path))
    write_text(
        os.path.join(project_root, "outputs", "fuzz_plans.json"),
        json.dumps([p.to_dict() for p in plans], indent=2),
    )
    gated = sum(1 for p in plans if p.caller_role)
    bounded = sum(1 for p in plans if p.bounds)
    print(f"[TC] Fuzz plans: {len(plans)} functions, {gated} access gated, {bounded} with bounds")

    loop_harness_src = generate_loop_harness(
        {**read_json(ir_out_path), "pragma": model["pragma"]},
        contract_name=contract_base,
        import_path=contract_import_path,
    )
    loop_harness_path = os.path.join(
        foundry_project_dir, "test", f"{contract_base}_LoopHarness.t.sol"
    )
    os.makedirs(os.path.dirname(loop_harness_path), exist_ok=True)
    _clear_stale_artifacts(foundry_project_dir, contract_base, contract_path)
    write_text(loop_harness_path, loop_harness_src)
    tests_emitted = loop_harness_src.count("function testFuzz_")
    print(f"[TC] Loop harness: {tests_emitted} tests -> {loop_harness_path}")

    # 4) Place the contract in the Foundry project, adding loop probes first
    foundry_src_dir = os.path.join(foundry_project_dir, "src")
    os.makedirs(foundry_src_dir, exist_ok=True)
    target_sol = os.path.join(foundry_src_dir, os.path.basename(contract_path))

    if args.no_instrument:
        shutil.copyfile(contract_path, target_sol)
        print("[IN] Loop instrumentation disabled")
    else:
        source = read_text(contract_path)
        probed, manifest = instrument_all(
            source,
            read_json(ir_out_path),
            state=not args.no_state_probes,
        )
        write_text(target_sol, probed)
        write_text(
            os.path.join(project_root, "outputs", "loop_probes.json"),
            json.dumps(manifest["loops"], indent=2),
        )
        write_text(
            os.path.join(project_root, "outputs", "state_probes.json"),
            json.dumps(manifest["state"], indent=2),
        )
        print(
            f"[IN] Instrumented {len(manifest['loops'])} loops and "
            f"{len(manifest['state'])} function boundaries -> {target_sol}"
        )
        if manifest["dropped_state_edits"]:
            print(
                f"[IN] {manifest['dropped_state_edits']} state probes dropped "
                "where a loop rewrite covered the same span"
            )
        skipped = sum(p.get("skipped_returns", 0) for p in manifest["state"])
        if skipped:
            print(
                f"[IN] {skipped} returns left uninstrumented because they are "
                "the whole body of a brace-less branch"
            )

    # 5) Rounds of fuzzing, inference and verification
    audit_path = os.path.join(project_root, "outputs", "audit.json")
    seeds_path = os.path.join(project_root, "outputs", "seeds.json")
    rounds_path = os.path.join(project_root, "outputs", "refine_rounds.json")

    history: List[RoundSummary] = []
    seed_lines: List[str] = []
    seen_seeds: Set[tuple] = set()
    relations = {}
    rounds_dir = os.path.join(project_root, "outputs", "rounds")
    best_round = None
    best_score = None

    round_artifacts = [
        os.path.join(project_root, "outputs", name)
        for name in (
            "relations.json",
            "postconditions.json",
            "loop_traces.json",
            "audit.json",
            "seeds.json",
            "foundry_traces.txt",
            f"T{contract_base}.sol",
            f"T{contract_base}.info",
        )
    ]

    if args.refine and not z3_available():
        print("[RF] z3 is not installed, so no candidate can be refuted and no "
              "seed can be produced. Install it with: pip install z3-solver")

    for round_index in range(args.refine + 1):
        print(f"[RD] Round {round_index}")

        if seed_lines:
            seeded = inject_seed_tests(
                generate_loop_harness(
                    {**read_json(ir_out_path), "pragma": model["pragma"]},
                    contract_name=contract_base,
                    import_path=contract_import_path,
                ),
                seed_lines,
            )
            _clear_stale_artifacts(foundry_project_dir, contract_base, contract_path)
            write_text(loop_harness_path, seeded)
            print(f"[RD] Harness carries {len(seed_lines)} seed lines")

        # 5) Run forge, streaming output under a timeout
        print("[FX] Running forge test...")
        try:
            result = run_forge_test(
                foundry_project_dir,
                verbosity=4,
                fuzz_runs=args.fuzz_runs,
                timeout=args.timeout,
                quiet=args.quiet,
            )
        except FileNotFoundError as e:
            print(f"[ERROR] {e}")
            sys.exit(1)

        write_trace(result, traces_out_path)
        print("[FX] " + describe(result).replace("\n", "\n[FX] "))

        if result.timed_out:
            print(
                "[FX] The run was cut short, so traces are partial. "
                "Raise --timeout or lower --fuzz-runs."
            )

        # 6) Rebuild per-iteration loop state from the trace
        runs = parse_lines(result.output.splitlines())
        loop_summary = summarise(runs)
        write_text(
            os.path.join(project_root, "outputs", "loop_traces.json"),
            json.dumps(loop_summary, indent=2),
        )
        observed = len(loop_summary["loops"])
        print(f"[IN] Recovered {len(runs)} loop runs across {observed} distinct loops")

        # Dynamic Invariant Explorer: mine the function-boundary snapshots
        state_calls = parse_state_lines(result.output.splitlines())
        write_text(
            os.path.join(project_root, "outputs", "state_traces.json"),
            json.dumps(summarise_state(state_calls), indent=2),
        )
        dynamic = explore_dynamic(state_calls, read_json(ir_out_path))
        write_text(
            os.path.join(project_root, "outputs", "dynamic_invariants.json"),
            json.dumps(
                {
                    "tally": tally_templates(dynamic),
                    "invariants": [d.to_dict() for d in dynamic],
                },
                indent=2,
            ),
        )
        print(
            f"[DE] {len(state_calls)} call snapshots, {len(dynamic)} dynamic invariants"
        )
        _run_daikon(state_calls, contract_base, project_root)
        for template, count in sorted(tally_templates(dynamic).items()):
            print(f"[DE]   {template:28s} {count}")
        if observed == 0 and not args.no_instrument:
            print(
                "[IN] No loop iterations were observed. The generated tests may be "
                "reverting before the loops execute."
            )

        # 7) Postcondition inference + export theory file (+ required .info)
        print("[PC] Running postcondition inference...")
        ir_json = read_json(ir_out_path)
        contract_ir = parse_ast_ir(ir_json)
        logs_text = read_text(traces_out_path)
        results = infer_all(contract_ir, logs_text)

        # Array contents from the state probes are the only evidence for a
        # claim about every element, so they are passed alongside the loop
        # traces rather than inferred from them.
        relations = derive_for_contract(
            read_json(ir_out_path),
            observations_from_summary(loop_summary),
            element_values(state_calls),
        )
        write_text(
            os.path.join(project_root, "outputs", "relations.json"),
            json.dumps({fn: [r.to_dict() for r in rs] for fn, rs in relations.items()}, indent=2),
        )
        relation_count = sum(len(v) for v in relations.values())
        loop_scoped = sum(1 for rs in relations.values() for r in rs if r.scope == "loop")
        print(
            f"[PC] Relations: {relation_count} across {len(relations)} functions "
            f"({loop_scoped} loop-scoped)"
        )

        write_text(postconds_json_path, _results_as_json(results, pretty=True))

        print("[PC] Exporting LoopSynth theory (T*.sol)...")
        theory_sol_src = render_theory_sol(
            contract_ir, results, contract_name=contract_base, relations=relations
        )
        write_text(theory_sol_out_path, theory_sol_src)
        print(f"[PC] Wrote theory file → {theory_sol_out_path}")

        # ✅ REQUIRED CHANGE: write T<Contract>.info using render_theory_info()
        theory_info_src = render_theory_info(
            contract_ir, results, contract_name=contract_base, relations=relations
        )
        write_text(theory_info_out_path, theory_info_src)
        print(f"[PC] Wrote theory info file → {theory_info_out_path}")


        # Verify the candidates and turn refutations into seeds for the next round
        ir_for_audit = read_json(ir_out_path)
        relations_json = {
            fn: [r.to_dict() for r in rs] for fn, rs in relations.items()
        }
        verdicts = audit_contract(ir_for_audit, relations_json)
        report = {
            "summary": summarise_verdicts(verdicts),
            "verdicts": [v.to_dict() for v in verdicts],
        }
        # Cross-function check: a contract-level invariant only stands if no
        # function can break it, so each is checked at every function boundary.
        contract_level = sorted({d.expr for d in dynamic if d.scope == "contract"})
        cross = audit_contract_invariants(ir_for_audit, contract_level)
        if cross:
            report["cross_function"] = [v.to_dict() for v in cross]
            preserved = sum(1 for v in cross if v.status == "verified")
            checkable = {
                v.invariant for v in cross if v.status != "unsupported"
            }
            established = sorted(
                inv
                for inv in checkable
                if all(v.status == "verified" for v in cross if v.invariant == inv)
            )
            skipped = len(contract_level) - len(checkable)
            report["contract_invariants"] = established
            print(
                f"[XF] {len(checkable)} checkable of {len(contract_level)} "
                f"contract invariants: {preserved} function checks preserved, "
                f"{len(established)} hold contract-wide"
                + (f", {skipped} outside the fragment" if skipped else "")
            )

        # Written after the cross-function results are attached, or they would
        # not reach the file.
        write_text(audit_path, json.dumps(report, indent=2))

        counts = report["summary"]["counts"]
        refuted = counts.get(VERDICT_REFUTED, 0)
        print(
            f"[SA] Checked {report['summary']['checked']} invariants: "
            + ", ".join(f"{k} {v}" for k, v in sorted(counts.items()))
        )

        seeds = seeds_from_verdicts(ir_for_audit, verdicts)
        priority = priority_functions(verdicts, ir_for_audit)
        write_text(
            seeds_path,
            json.dumps(
                {"seeds": [s.to_dict() for s in seeds], "priority": priority},
                indent=2,
            ),
        )

        # Compare whole seeds, not individual lines. Two rounds that rediscover
        # the same failure render tests that share most of their text, and
        # dropping the shared lines would leave a fragment that cannot compile.
        fresh_seeds = [s for s in seeds if _seed_key(s) not in seen_seeds]
        for seed in fresh_seeds:
            seen_seeds.add(_seed_key(seed))
        fresh = render_seed_tests(fresh_seeds, ir_for_audit, round_index=round_index)

        for seed in seeds:
            for request in seed.shape:
                print(
                    f"[RF] shape {request.symbol} = {request.target} via {request.var}"
                )
        print(f"[RF] {len(seeds)} seeds, {len(fresh_seeds)} not seen before")

        history.append(
            RoundSummary(
                round_index=round_index,
                checked=report["summary"]["checked"],
                verified=counts.get("verified", 0),
                refuted=refuted,
                new_seeds=len(fresh_seeds),
                priority=priority,
            )
        )
        write_text(
            rounds_path, json.dumps([h.to_dict() for h in history], indent=2)
        )

        usable = not result.timed_out and result.returncode == 0 and observed > 0
        score = (counts.get("verified", 0), observed)
        if usable and (best_score is None or score > best_score):
            best_score, best_round = score, round_index
        _snapshot_round(round_artifacts, rounds_dir, round_index)

        if not usable:
            print(
                f"[RD] Round {round_index} produced no usable traces "
                f"(forge exit {result.returncode}, {observed} loops observed). "
                "Refinement stops here rather than carrying a broken harness forward."
            )
            break

        if round_index == args.refine:
            break
        if has_converged(history):
            print("[RD] No further refinement is possible; stopping early")
            break

        seed_lines.extend(fresh)

    if best_round is not None:
        _restore_round(round_artifacts, rounds_dir, best_round)
        print(
            f"[RD] Keeping round {best_round} "
            f"({best_score[0]} verified, {best_score[1]} loops observed)"
        )
    else:
        print("[RD] No round produced usable traces")

    # 8) LoopSynth on the exported theory
    if args.skip_loopsynth:
        print("[LS] Skipped")
    else:
        print("[LS] Running LoopSynth...")
        _ = run_loopsynth(
            contract_base,
            Path(theory_sol_out_path),
            Path(contract_path),
            ir_path=ir_out_path,
        )

    print(f"[DONE] Pipeline complete. Invariants → {loopsynth_invariants_path}")


if __name__ == "__main__":
    main()

