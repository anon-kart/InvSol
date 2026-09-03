# tests/test_loop_scoping.py
import json
from invsol_postcond.ast_ir import parse_ast_ir
from invsol_postcond.inference import infer_postconditions

EXAMPLE_IR = {
  "contract": {
    "name": "C",
    "solidity_version": "0.8.30",
    "functions": [
      {
        "contract": "C",
        "name": "f",
        "requires": [],
        "reads": [], "writes": [], "storage_reads": [], "storage_writes": [],
        "loops": [
          {
            "type": "for",
            "bounds": {"index": "i", "lower": "0", "upper": "n", "inclusive_upper": False},
            "body_summary": {"indices": ["i"], "accumulators": ["s"], "has_external_call_in_loop": False},
            "init": "i = 0",
            "guard": "(i < n)",
            "update": "(i++)"
          }
        ]
      },
      {
        "contract": "C",
        "name": "g",
        "requires": [],
        "reads": [], "writes": [], "storage_reads": [], "storage_writes": [],
        "loops": []
      }
    ]
  }
}

def test_scopes_and_loop_idx():
    c = parse_ast_ir(EXAMPLE_IR)
    res = infer_postconditions(c, traces=None)

    by_fn = {r.function: r for r in res}
    f_cands = by_fn["f"].candidates
    g_cands = by_fn["g"].candidates

    # f has 1 loop: every loop-bound/post is scope=="loop" and loop_idx==0
    loop_facts = [c for c in f_cands if getattr(c, "scope", "function") == "loop"]
    assert len(loop_facts) > 0
    assert all(c.loop_idx == 0 for c in loop_facts)

    # function-scope facts still exist for f (NoStateWrites/NoExternalCalls)
    fn_facts = [c for c in f_cands if getattr(c, "scope", "function") == "function"]
    assert len(fn_facts) > 0

    # g has zero loops: no loop-scoped facts
    assert all(getattr(c, "scope", "function") == "function" for c in g_cands)

def test_accumulator_normalization_and_headers():
    c = parse_ast_ir(EXAMPLE_IR)
    res = infer_postconditions(c, traces=None)
    f = [r for r in res if r.function == "f"][0]

    exprs = [c.expr for c in f.candidates]
    # normalized accumulator
    assert "Accumulator(sum:s)" in exprs
    # guard/update present
    assert "Guard((i < n))" in exprs
    assert "Update((i++))" in exprs
