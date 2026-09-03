from testcrafter.instrument.state_probe import build_edits, instrument

SOURCE = """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Bank {
    uint256 public total;
    address[] public holders;
    mapping(address => uint256) public balances;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
        total += msg.value;
    }

    function firstOver(uint256 x) external returns (uint256) {
        for (uint256 i = 0; i < holders.length; i++) {
            if (balances[holders[i]] > x) {
                return i;
            }
        }
        return holders.length;
    }

    function shortcut(uint256 x) external returns (uint256) {
        if (x > total) return x;
        return total;
    }

    function peek() external view returns (uint256) {
        return total;
    }
}
"""


def span_of(marker, closing):
    start = SOURCE.index("{", SOURCE.index(marker))
    end = SOURCE.index(closing) + len(closing)
    return f"{start}:{end - start}:0"


def return_span(snippet):
    start = SOURCE.index(snippet)
    return f"{start}:{len(snippet)}:0"


STATE = {
    "variables": [
        {"name": "total", "type": "uint256"},
        {"name": "holders", "type": "address[]"},
        {"name": "balances", "type": "mapping(address => uint256)"},
    ],
    "mappings": [{"name": "balances", "key": "address", "value": "uint256"}],
}


def ir_with(functions):
    return {"contract": {"name": "Bank", "state": STATE, "functions": functions}}


DEPOSIT = {
    "name": "deposit",
    "visibility": "external",
    "mutability": "payable",
    "body_src": span_of("function deposit", "total += msg.value;\n    }"),
    "return_srcs": [],
    "storage_writes": [
        {"var": "balances", "key": "msg.sender"},
        {"var": "total", "key": None},
    ],
}

SHORTCUT = {
    "name": "shortcut",
    "visibility": "external",
    "mutability": "nonpayable",
    "body_src": span_of("function shortcut", "return total;\n    }"),
    "return_srcs": [return_span("return x;"), return_span("return total;")],
    "storage_reads": [{"var": "total", "key": None}],
}

PEEK = {
    "name": "peek",
    "visibility": "external",
    "mutability": "view",
    "body_src": span_of("function peek", "return total;\n    }\n}"),
    "return_srcs": [],
}


def test_entry_and_exit_snapshots_are_emitted():
    out, probes = instrument(SOURCE, ir_with([DEPOSIT]))

    assert "[INVSOL] STATE_ENTER deposit" in out
    assert "[INVSOL] STATE_EXIT deposit" in out
    assert probes[0]["exit_points"] == 1


def test_scalars_arrays_and_mapping_keys_are_all_logged():
    out, _ = instrument(SOURCE, ir_with([DEPOSIT]))

    assert '"[INVSOL] VAR deposit total", uint256(total)' in out
    assert '"[INVSOL] VAR deposit holders_length", holders.length' in out
    assert '"[INVSOL] ELEM deposit holders", _p, holders[_p]' in out
    assert '"[INVSOL] KEY deposit balances", msg.sender' in out


def test_mapping_entries_come_from_observed_keys():
    _, probes = instrument(SOURCE, ir_with([DEPOSIT]))
    assert probes[0]["mapping_keys"] == [
        {"name": "balances", "key": "msg.sender", "value_type": "uint256"}
    ]


def test_a_return_that_is_a_braceless_branch_body_is_left_alone():
    _, probes = instrument(SOURCE, ir_with([SHORTCUT]))

    # `if (x > total) return x;` cannot take a statement in front of it.
    assert probes[0]["skipped_returns"] == 1
    assert probes[0]["exit_points"] == 2


def test_read_only_functions_are_not_instrumented():
    edits, probes = build_edits(SOURCE, ir_with([PEEK]))
    assert edits == []
    assert probes == []


def test_braces_stay_balanced():
    out, _ = instrument(SOURCE, ir_with([DEPOSIT, SHORTCUT]))
    assert out.count("{") == out.count("}")


def test_nothing_to_do_leaves_the_source_untouched():
    out, probes = instrument(SOURCE, ir_with([]))
    assert out == SOURCE
    assert probes == []


GRID_SOURCE = """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Grid {
    uint256[][] public cells;
    mapping(address => Entry) public entries;

    struct Entry {
        uint256 a;
        uint256 b;
    }

    function touch(uint256 v) external {
        cells[0][0] = v;
        entries[msg.sender].a = v;
    }
}
"""


def grid_ir():
    start = GRID_SOURCE.index("{", GRID_SOURCE.index("function touch"))
    end = GRID_SOURCE.index("entries[msg.sender].a = v;") + len(
        "entries[msg.sender].a = v;\n    }"
    )
    return {
        "contract": {
            "name": "Grid",
            "state": {
                "variables": [
                    {"name": "cells", "type": "uint256[][]"},
                ],
                "mappings": [
                    {"name": "entries", "key": "address", "value": "struct Entry"}
                ],
            },
            "functions": [
                {
                    "name": "touch",
                    "visibility": "external",
                    "mutability": "nonpayable",
                    "body_src": f"{start}:{end - start}:0",
                    "return_srcs": [],
                    "storage_writes": [
                        {"var": "cells", "key": "0"},
                        {"var": "entries", "key": "msg.sender"},
                    ],
                }
            ],
        }
    }


def test_a_nested_array_logs_only_its_length():
    out, _ = instrument(GRID_SOURCE, grid_ir())

    assert '"[INVSOL] VAR touch cells_length", cells.length' in out
    # cells[_p] is a uint256[], so casting it to uint256 would not compile.
    assert "uint256(cells[_p])" not in out
    assert "[INVSOL] ELEM touch cells" not in out


def test_a_mapping_to_a_struct_is_not_logged():
    out, probes = instrument(GRID_SOURCE, grid_ir())

    assert probes[0]["mapping_keys"] == []
    assert "[INVSOL] KEY touch entries" not in out


HASH_SOURCE = """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract HashChain {
    bytes32 public root;
    bytes32[] public nodes;

    function setRoot(bytes32 root_) external {
        root = root_;
    }
}
"""


def hash_ir():
    start = HASH_SOURCE.index("{", HASH_SOURCE.index("function setRoot"))
    end = HASH_SOURCE.index("root = root_;") + len("root = root_;\n    }")
    return {
        "contract": {
            "name": "HashChain",
            "state": {
                "variables": [
                    {"name": "root", "type": "bytes32"},
                    {"name": "nodes", "type": "bytes32[]"},
                ],
                "mappings": [],
            },
            "functions": [
                {
                    "name": "setRoot",
                    "visibility": "external",
                    "mutability": "nonpayable",
                    "body_src": f"{start}:{end - start}:0",
                    "return_srcs": [],
                    "storage_writes": [{"var": "root", "key": None}],
                }
            ],
        }
    }


def test_bytes32_is_widened_so_console_log_has_an_overload():
    out, _ = instrument(HASH_SOURCE, hash_ir())

    # forge-std has no console.log(string, bytes32).
    assert '"[INVSOL] VAR setRoot root", uint256(root)' in out
    assert '"[INVSOL] VAR setRoot root", root)' not in out


def test_a_bytes32_array_logs_widened_elements():
    out, _ = instrument(HASH_SOURCE, hash_ir())
    assert "uint256(nodes[_p])" in out


VESTING_SOURCE = """// SPDX-License-Identifier: MIT
pragma solidity 0.8.19;

contract TokenVesting {
    struct Schedule {
        uint256 start;
        uint256 amountPerInterval;
        address beneficiary;
    }

    mapping(address => Schedule) public schedules;
    uint256 public totalVested;

    function grant(address account, uint256 amount) external {
        schedules[account].start = amount;
        totalVested += amount;
    }
}
"""


def vesting_ir():
    start = VESTING_SOURCE.index("{", VESTING_SOURCE.index("function grant"))
    end = VESTING_SOURCE.index("totalVested += amount;") + len(
        "totalVested += amount;\n    }"
    )
    return {
        "contract": {
            "name": "TokenVesting",
            "state": {
                "variables": [
                    {"name": "schedules", "type": "mapping(address => struct TokenVesting.Schedule)"},
                    {"name": "totalVested", "type": "uint256"},
                ],
                "mappings": [
                    {"name": "schedules", "key": "address", "value": "struct TokenVesting.Schedule"}
                ],
                "structs": [
                    {
                        "contract": "TokenVesting",
                        "name": "Schedule",
                        "fields": [
                            {"name": "start", "type": "uint256"},
                            {"name": "amountPerInterval", "type": "uint256"},
                            {"name": "beneficiary", "type": "address"},
                        ],
                    }
                ],
            },
            "functions": [
                {
                    "name": "grant",
                    "visibility": "external",
                    "mutability": "nonpayable",
                    "body_src": f"{start}:{end - start}:0",
                    "return_srcs": [],
                    "storage_writes": [
                        {"var": "schedules", "key": "account"},
                        {"var": "totalVested", "key": None},
                    ],
                }
            ],
        }
    }


def test_each_struct_field_is_logged_under_a_flattened_name():
    out, _ = instrument(VESTING_SOURCE, vesting_ir())
    assert '"[INVSOL] FIELD grant schedules_start", account' in out
    assert '"[INVSOL] FIELD grant schedules_amountPerInterval", account' in out


def test_an_address_field_is_logged_without_a_numeric_cast(self=None):
    out, _ = instrument(VESTING_SOURCE, vesting_ir())
    assert "schedules[account].beneficiary)" in out
    assert "uint256(schedules[account].beneficiary)" not in out


def test_the_touched_struct_key_is_recorded():
    _, probes = instrument(VESTING_SOURCE, vesting_ir())
    assert probes[0]["struct_keys"] == [{"name": "schedules", "key": "account"}]


def test_a_struct_valued_mapping_is_not_logged_as_a_scalar():
    out, probes = instrument(VESTING_SOURCE, vesting_ir())
    # uint256(schedules[account]) would not compile.
    assert "[INVSOL] KEY grant schedules" not in out
    assert probes[0]["mapping_keys"] == []


def test_struct_instrumentation_keeps_braces_balanced():
    out, _ = instrument(VESTING_SOURCE, vesting_ir())
    assert out.count("{") == out.count("}")


ESCROW_SOURCE = """// SPDX-License-Identifier: MIT
pragma solidity 0.8.19;

contract Escrow {
    address[] public beneficiaries;
    uint256[] public amounts;
    mapping(address => uint256) public owed;

    function release() external {
        for (uint256 i = 0; i < beneficiaries.length; i++) {
            owed[beneficiaries[i]] = 0;
        }
    }
}
"""


def escrow_ir():
    start = ESCROW_SOURCE.index("{", ESCROW_SOURCE.index("function release"))
    end = ESCROW_SOURCE.index("}\n}", start) + 1
    return {
        "contract": {
            "name": "Escrow",
            "state": {
                "variables": [
                    {"name": "beneficiaries", "type": "address[]"},
                    {"name": "amounts", "type": "uint256[]"},
                    {"name": "owed", "type": "mapping(address => uint256)"},
                ],
                "mappings": [{"name": "owed", "key": "address", "value": "uint256"}],
                "structs": [],
            },
            "functions": [
                {
                    "name": "release",
                    "visibility": "external",
                    "mutability": "nonpayable",
                    "body_src": f"{start}:{end - start}:0",
                    "return_srcs": [],
                    "storage_writes": [{"var": "owed", "key": "beneficiaries[i]"}],
                }
            ],
        }
    }


def test_a_key_the_contract_stores_is_walked():
    # owed[beneficiaries[i]] is written inside a loop, so the key expression
    # is not in scope at the function boundary. The array holding the keys is.
    out, _ = instrument(ESCROW_SOURCE, escrow_ir())
    assert "for (uint256 _m = 0; _m < beneficiaries.length && _m < 8; _m++)" in out
    assert '"[INVSOL] KEY release owed", beneficiaries[_m]' in out


def test_only_an_array_matching_the_key_type_is_used():
    # amounts is uint256[], so owed[amounts[_m]] would not type-check.
    out, _ = instrument(ESCROW_SOURCE, escrow_ir())
    assert "owed[amounts[_m]]" not in out


def test_walking_keys_keeps_braces_balanced():
    out, _ = instrument(ESCROW_SOURCE, escrow_ir())
    assert out.count("{") == out.count("}")
