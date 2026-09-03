# InvSol

Automatic loop invariant synthesis and verification for Solidity smart
contracts. InvSol infers candidate invariants for loops before deployment,
without relying on transaction history, and checks them with an SMT solver.

## Requirements

- Python 3.12
- [Foundry](https://book.getfoundry.sh/) (`forge`)
- `solc` 0.8.26 via `solc-select`
- Java 8 or later, only if you want Daikon (optional)

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

solc-select install 0.8.26
solc-select use 0.8.26

mkdir -p artifacts/foundry_project && cd artifacts/foundry_project
forge init --force --no-commit .
forge install foundry-rs/forge-std
cd ../..
```

### Daikon (optional)

InvSol writes Daikon-format `.decls` and `.dtrace` files on every run. To have
Daikon consume them, download it from <https://plse.cs.washington.edu/daikon/>
and set `DAIKON_JAR=/path/to/daikon.jar`. Without it the translation still
runs; only the inference step is skipped.

## Running

One contract:

```bash
python run_invsol_pipeline.py src/LoopPlayground.sol --refine 1 --fuzz-runs 64
```

The whole benchmark corpus:

```bash
python run_corpus.py --fuzz-runs 16 --refine 1
```

`--quiet` suppresses the Foundry trace dump. `--refine N` sets how many extra
counterexample-guided rounds to run.

## Output

Everything lands in `outputs/`: `ir.json` (loop-aware IR), `loop_traces.json`
and `state_traces.json` (recovered execution state), `relations.json` (inferred
postconditions), `dynamic_invariants.json` (state invariants from the six
templates), `loopsynth_invariants.txt` and `strategy_table.json` (loop
invariants and per-strategy counts), `audit.json` (verification verdicts and
counterexamples), `seeds.json` and `refine_rounds.json` (refinement), and
`daikon/` (translation output). A corpus run also writes
`outputs/corpus/corpus_report.json` and per-contract logs.

## Benchmark corpus

`bench/contracts` holds 23 contracts covering the targeted loop patterns, with
`bench/manifest.json` recording expected properties for each.

`CappedLedger.sol` was added specifically to exercise quantifier
instantiation: it clamps every array element against a stored cap, so a claim
over all elements holds without being implied by the element type. No other
contract in the corpus has that shape, and most quantifier candidates come
from it.

## Tests

```bash
for d in invsol_ast_analyzer testcrafter-mini invsol_postcond_scaffold invsol_audit foundry2daikon; do
  (cd $d && python -m pytest tests/ -q)
done
```

## Layout

| Directory | Component |
| --- | --- |
| `invsol_ast_analyzer/` | Solidity AST analysis and IR construction |
| `testcrafter-mini/` | Test generation, instrumentation, trace recovery |
| `invsol_postcond_scaffold/` | Postcondition inference and state templates |
| `dynamate-sol/` | Mutation-based loop invariant synthesis |
| `invsol_audit/` | SMT encoding, verification, refinement |
| `foundry2daikon/` | Solidity-to-Daikon translation layer |
| `bench/` | Benchmark corpus and manifest |
