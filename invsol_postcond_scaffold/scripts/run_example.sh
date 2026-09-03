#!/usr/bin/env bash
set -euo pipefail
python -m invsol_postcond.cli \  --ir examples/ir/SimpleToken.ast.json \  --logs examples/logs/SimpleToken_foundry_sample.txt \  --out /tmp/postconditions.json
