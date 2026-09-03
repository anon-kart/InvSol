# InvSol Postcondition Inference (Mini Project)

This is a scaffold for a **Postcondition Inference Module** that consumes:
1. **AST Analyzer IR** (JSON, as produced by your InvSol AST Analyzer), and
2. **TestCrafter / Foundry logs** (text, `-vvvv` traces).

It proposes **postconditions** for functions (e.g., `mint`, `burn`, `transfer`) and, when available,
**loop postconditions** (e.g., `acc_post == sum(arr)`, bounds, monotonicity).

> All files are placeholders with TODOs; fill them out incrementally.

## Quickstart

```bash
# (Recommended) in a fresh virtual env
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Smoke test
pytest
# Or run the CLI help
python -m invsol_postcond.cli --help
```

## Project Layout

```
invsol_postcond/
├─ README.md
├─ requirements.txt
├─ pyproject.toml
├─ .gitignore
├─ src/
│  └─ invsol_postcond/
│     ├─ __init__.py
│     ├─ models.py
│     ├─ ast_ir.py
│     ├─ logs_parser.py
│     ├─ inference.py
│     ├─ validators.py
│     ├─ io_utils.py
│     └─ cli.py
├─ examples/
│  ├─ ir/
│  │  └─ SimpleToken.ast.json
│  └─ logs/
│     └─ SimpleToken_foundry_sample.txt
├─ tests/
│  └─ test_smoke.py
└─ scripts/
   └─ run_example.sh
```

## Workflow

1. Place IR JSON under `examples/ir/` and Foundry logs under `examples/logs/`.
2. Run the CLI to infer postconditions:
   ```bash
   python -m invsol_postcond.cli       --ir examples/ir/SimpleToken.ast.json       --logs examples/logs/SimpleToken_foundry_sample.txt       --out /tmp/postconditions.json
   ```
3. Open the emitted JSON and iterate on rules/validators.
