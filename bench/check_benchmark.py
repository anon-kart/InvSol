"""
Compile every benchmark contract and report the loop facts the AST analyzer
recovers. Run from the InvSol project root:

    python bench/check_benchmark.py
"""

import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONTRACTS = HERE / "contracts"


def main() -> int:
    try:
        from invsol_ast.pipeline import run_pipeline
    except ImportError as e:
        print(f"Cannot import invsol_ast: {e}")
        print("Run this from the InvSol project root with the venv active.")
        return 2

    out_dir = HERE / "ir"
    out_dir.mkdir(exist_ok=True)

    files = sorted(CONTRACTS.glob("*.sol"))
    if not files:
        print(f"No contracts found under {CONTRACTS}")
        return 2

    manifest = {}
    manifest_path = HERE / "manifest.json"
    if manifest_path.exists():
        for entry in json.loads(manifest_path.read_text())["contracts"]:
            manifest[entry["file"]] = entry

    ok = 0
    failed = []
    categories = Counter()
    total_loops = 0
    total_accumulators = 0

    for sol in files:
        try:
            ir = run_pipeline(
                path=str(sol),
                out=str(out_dir / f"{sol.stem}.json"),
                solc_path=None,
                validate=True,
                strict=False,
                dump_ast=None,
            )
        except Exception as e:
            failed.append((sol.name, f"{type(e).__name__}: {str(e).splitlines()[0]}"))
            continue

        contract = ir["contract"]
        loops = [lp for fn in contract["functions"] for lp in (fn.get("loops") or [])]
        accs = [
            a
            for lp in loops
            for a in ((lp.get("body_summary") or {}).get("accumulator_facts") or [])
        ]
        for lp in loops:
            categories[lp.get("category") or "unknown"] += 1

        total_loops += len(loops)
        total_accumulators += len(accs)
        ok += 1

        expected = manifest.get(sol.name, {})
        want = set(expected.get("loop_categories") or [])
        got = {lp.get("category") for lp in loops}
        flag = "" if not want or (want & got) else "  <-- category mismatch"

        print(
            f"{sol.name:24s} fns={len(contract['functions']):3d} "
            f"loops={len(loops):2d} acc={len(accs):2d} "
            f"cats={sorted(c for c in got if c)}{flag}"
        )

    print()
    print(f"compiled {ok}/{len(files)} contracts")
    print(f"loops {total_loops}, accumulator facts {total_accumulators}")
    print(f"loop categories: {dict(categories)}")

    if failed:
        print("\nfailures:")
        for name, msg in failed:
            print(f"  {name}: {msg}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
