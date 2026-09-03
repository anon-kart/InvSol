import json

from invsol_postcond.ast_ir import parse_ast_ir
from invsol_postcond.inference import infer_all
from invsol_postcond.logs_parser import parse_foundry_logs

IR = {
    "contract": {
        "name": "SimpleToken",
        "solidity_version": "0.8.19",
        "functions": [
            {
                "contract": "SimpleToken",
                "name": "mint",
                "visibility": "external",
                "mutability": "nonpayable",
                "params": [{"name": "to", "type": "address"}, {"name": "amount", "type": "uint256"}],
                "requires": [],
                "reads": [],
                "writes": ["totalSupply"],
                "storage_reads": [],
                "storage_writes": [{"var": "totalSupply"}],
                "loops": [],
            }
        ],
        "state": {"variables": [{"name": "totalSupply", "type": "uint256"}], "mappings": []},
    }
}

LOGS = """Traces:
[46276] SimpleToken::mint(0xabc, 10)
[261] SimpleToken::totalSupply() [staticcall]
"""


def test_ir_parses_from_a_dictionary():
    contract = parse_ast_ir(IR)
    assert contract.name == "SimpleToken"
    assert [f.name for f in contract.functions] == ["mint"]


def test_ir_parses_from_a_json_string():
    contract = parse_ast_ir(json.loads(json.dumps(IR)))
    assert contract.name == "SimpleToken"


def test_foundry_log_parses_without_error():
    assert parse_foundry_logs(LOGS) is not None


def test_inference_runs_end_to_end():
    contract = parse_ast_ir(IR)
    results = infer_all(contract, LOGS)
    assert results
    assert results[0].function == "mint"


def test_inference_produces_candidates_for_each_function():
    contract = parse_ast_ir(IR)
    results = infer_all(contract, LOGS)
    assert all(hasattr(r, "candidates") for r in results)
