from testcrafter.instrument.combined import instrument
from testcrafter.instrument.state_probe import build_edits as state_edits

SOURCE = """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Bank {
    uint256 public total;
    uint256[] public amounts;

    function sumAll(uint256 limit) external returns (uint256 s) {
        for (uint256 i = 0; i < limit; i++) {
            s += amounts[i];
        }
        total = s;
    }
}
"""

# The same file with a non-ASCII character in a comment before the contract.
# solc counts bytes and Python counts characters, so every later offset moves.
WIDE = SOURCE.replace(
    "contract Bank {",
    "// sums amounts \u2192 total\ncontract Bank {",
)


def body_span(text, marker, closing):
    start = text.index("{", text.index(marker))
    end = text.index(closing) + len(closing)
    return start, end - start


def ir_for(text):
    start, length = body_span(text, "function sumAll", "total = s;\n    }")
    byte_start = len(text[:start].encode("utf-8"))
    byte_length = len(text[start : start + length].encode("utf-8"))

    loop_start = text.index("for (uint256 i")
    loop_end = text.index("}", text.index("s += amounts[i];")) + 1
    loop_body_start = text.index("{", loop_start)

    def as_src(begin, end):
        return "{}:{}:0".format(
            len(text[:begin].encode("utf-8")),
            len(text[begin:end].encode("utf-8")),
        )

    return {
        "contract": {
            "name": "Bank",
            "state": {
                "variables": [
                    {"name": "total", "type": "uint256"},
                    {"name": "amounts", "type": "uint256[]"},
                ],
                "mappings": [],
            },
            "functions": [
                {
                    "name": "sumAll",
                    "visibility": "external",
                    "mutability": "nonpayable",
                    "body_src": f"{byte_start}:{byte_length}:0",
                    "return_srcs": [],
                    "storage_writes": [{"var": "total", "key": None}],
                    "loops": [
                        {
                            "loop_id": "Bank.sumAll#loop0",
                            "src": as_src(loop_start, loop_end),
                            "body_src": as_src(loop_body_start, loop_end),
                            "body_is_block": True,
                            "category": "simple",
                            "depth": 0,
                            "body_summary": {"indices": ["i"], "carried_types": {}},
                        }
                    ],
                }
            ],
        }
    }


def test_both_probe_kinds_appear():
    out, manifest = instrument(SOURCE, ir_for(SOURCE))

    assert "[INVSOL] LOOP_ENTER Bank.sumAll#loop0" in out
    assert "[INVSOL] STATE_ENTER sumAll" in out
    assert "[INVSOL] STATE_EXIT sumAll" in out
    assert len(manifest["loops"]) == 1
    assert len(manifest["state"]) == 1


def test_combined_output_still_balances():
    out, _ = instrument(SOURCE, ir_for(SOURCE))
    assert out.count("{") == out.count("}")


def test_state_probe_lands_at_the_body_brace_with_wide_characters():
    edits, _ = state_edits(WIDE, ir_for(WIDE))
    assert edits, "expected a state probe"
    first = min(edits, key=lambda e: e.offset)
    assert WIDE[first.offset - 1] == "{"


def test_wide_characters_do_not_corrupt_the_combined_output():
    out, _ = instrument(WIDE, ir_for(WIDE))
    assert out.count("{") == out.count("}")
    assert "[INVSOL] STATE_ENTER sumAll" in out
    assert "\u2192" in out


def test_probes_can_be_turned_off():
    out, manifest = instrument(SOURCE, ir_for(SOURCE), state=False)
    assert "[INVSOL] STATE_ENTER" not in out
    assert "[INVSOL] LOOP_ENTER" in out
    assert manifest["state"] == []
