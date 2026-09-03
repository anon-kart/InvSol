import pytest

from testcrafter.instrument.loop_probe import (
    add_console_import,
    build_edits,
    instrument,
)
from testcrafter.instrument.loop_trace import parse_lines, summarise

BLOCK_SOURCE = """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract Demo {
    uint256[] public values;

    function total() external view returns (uint256 acc) {
        for (uint256 i = 0; i < values.length; i++) {
            acc += values[i];
        }
    }
}
"""

BRACELESS_SOURCE = """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract Demo {
    uint256[] public values;

    function copy(uint256 n) external view returns (uint256 s) {
        for (uint256 i = 0; i < n; i++) s += values[i];
    }
}
"""


def _ir(source, loop_head, body_marker, body_is_block, fn, carried):
    start = source.index(loop_head)
    if body_is_block:
        body_start = source.index("{", start)
        end = source.index("}", source.index(body_marker)) + 1
        body_len = end - body_start
    else:
        body_start = source.index(body_marker)
        body_len = len(body_marker)
        end = body_start + body_len
    return {
        "contract": {
            "name": "Demo",
            "functions": [
                {
                    "name": fn,
                    "loops": [
                        {
                            "loop_id": f"Demo.{fn}#loop0",
                            "category": "dynamic",
                            "depth": 0,
                            "src": f"{start}:{end - start}:0",
                            "body_src": f"{body_start}:{body_len}:0",
                            "body_is_block": body_is_block,
                            "body_summary": {
                                "indices": ["i"],
                                "carried_vars": [carried],
                                "declared_vars": [],
                                "carried_types": {carried: "uint256", "i": "uint256"},
                            },
                        }
                    ],
                }
            ],
        }
    }


class TestInstrumentation:
    def test_block_body_gets_all_three_probes(self):
        ir = _ir(BLOCK_SOURCE, "for (uint256 i", "acc += values[i];", True, "total", "acc")
        out, probes = instrument(BLOCK_SOURCE, ir)
        assert out.count("LOOP_ENTER Demo.total#loop0") == 1
        assert out.count("LOOP_ITER Demo.total#loop0") == 1
        assert out.count("LOOP_EXIT Demo.total#loop0") == 1
        assert len(probes) == 1

    def test_counter_is_declared_before_the_loop(self):
        ir = _ir(BLOCK_SOURCE, "for (uint256 i", "acc += values[i];", True, "total", "acc")
        out, probes = instrument(BLOCK_SOURCE, ir)
        counter = probes[0]["counter"]
        assert f"uint256 {counter} = 0;" in out
        assert out.index(f"uint256 {counter} = 0;") < out.index("for (uint256 i")

    def test_original_statement_is_preserved(self):
        ir = _ir(BLOCK_SOURCE, "for (uint256 i", "acc += values[i];", True, "total", "acc")
        out, _ = instrument(BLOCK_SOURCE, ir)
        assert "acc += values[i];" in out

    def test_braceless_body_is_wrapped_in_braces(self):
        ir = _ir(BRACELESS_SOURCE, "for (uint256 i", "s += values[i];", False, "copy", "s")
        out, _ = instrument(BRACELESS_SOURCE, ir)
        assert "for (uint256 i = 0; i < n; i++) {" in out
        assert "s += values[i];" in out
        assert out.count("LOOP_ITER Demo.copy#loop0") == 1

    def test_console_import_added_once(self):
        ir = _ir(BLOCK_SOURCE, "for (uint256 i", "acc += values[i];", True, "total", "acc")
        out, _ = instrument(BLOCK_SOURCE, ir)
        assert out.count('import {console} from "forge-std/console.sol";') == 1
        assert add_console_import(out).count("forge-std/console.sol") == 1

    def test_watched_variables_exclude_body_declarations(self):
        ir = _ir(BLOCK_SOURCE, "for (uint256 i", "acc += values[i];", True, "total", "acc")
        ir["contract"]["functions"][0]["loops"][0]["body_summary"]["declared_vars"] = ["acc"]
        _, probes = instrument(BLOCK_SOURCE, ir)
        assert probes[0]["watched"] == []

    def test_loop_without_source_span_is_skipped(self):
        ir = _ir(BLOCK_SOURCE, "for (uint256 i", "acc += values[i];", True, "total", "acc")
        ir["contract"]["functions"][0]["loops"][0]["src"] = ""
        edits, probes = build_edits(BLOCK_SOURCE, [
            {**ir["contract"]["functions"][0]["loops"][0], "_contract": "Demo", "_function": "total"}
        ])
        assert edits == []
        assert probes == []


NESTED_TRACE = """
[INVSOL] LOOP_ENTER T.f#loop0
[INVSOL] ENTER_VAR T.f#loop0 total: 0
[INVSOL] LOOP_ITER T.f#loop0 1
[INVSOL] ITER_IDX T.f#loop0 i: 1
[INVSOL] LOOP_ENTER T.f#loop1
[INVSOL] LOOP_ITER T.f#loop1 1
[INVSOL] ITER_VAR T.f#loop1 total: 0
[INVSOL] LOOP_EXIT T.f#loop1 1
[INVSOL] EXIT_VAR T.f#loop1 total: 1
[INVSOL] LOOP_ITER T.f#loop0 2
[INVSOL] LOOP_ENTER T.f#loop1
[INVSOL] LOOP_ITER T.f#loop1 1
[INVSOL] LOOP_ITER T.f#loop1 2
[INVSOL] LOOP_EXIT T.f#loop1 2
[INVSOL] EXIT_VAR T.f#loop1 total: 4
[INVSOL] LOOP_EXIT T.f#loop0 2
[INVSOL] EXIT_VAR T.f#loop0 total: 4
"""


class TestTraceParsing:
    def test_inner_loop_yields_one_run_per_outer_iteration(self):
        runs = parse_lines(NESTED_TRACE.splitlines())
        inner = [r for r in runs if r.loop_id == "T.f#loop1"]
        assert len(inner) == 2
        assert [r.trip_count for r in inner] == [1, 2]

    def test_variable_names_lose_the_trailing_colon(self):
        runs = parse_lines(NESTED_TRACE.splitlines())
        outer = [r for r in runs if r.loop_id == "T.f#loop0"][0]
        assert "total" in outer.entry
        assert not any(k.endswith(":") for k in outer.entry)

    def test_exit_values_are_captured_after_loop_exit(self):
        runs = parse_lines(NESTED_TRACE.splitlines())
        outer = [r for r in runs if r.loop_id == "T.f#loop0"][0]
        assert outer.exit == {"total": "4"}

    def test_iteration_values_attach_to_the_right_iteration(self):
        runs = parse_lines(NESTED_TRACE.splitlines())
        outer = [r for r in runs if r.loop_id == "T.f#loop0"][0]
        assert outer.iterations[0].values["i"] == "1"

    def test_summary_groups_runs_by_loop(self):
        runs = parse_lines(NESTED_TRACE.splitlines())
        loops = {lp["loop_id"]: lp for lp in summarise(runs)["loops"]}
        assert loops["T.f#loop1"]["runs"] == 2
        assert loops["T.f#loop1"]["max_trip_count"] == 2
        assert loops["T.f#loop0"]["runs"] == 1

    def test_lines_without_the_marker_are_ignored(self):
        noise = ["random forge output", "  [12345] Harness::test()", "no marker here"]
        assert parse_lines(noise) == []


BRACELESS_NO_SEMI = """// SPDX-License-Identifier: MIT
pragma solidity 0.8.19;

contract Demo {
    uint256[] public numbers;

    function copy(uint256 n) external view returns (uint256[] memory arr) {
        arr = new uint256[](n);
        for (uint256 i = 0; i < n; i++) arr[i] = numbers[i];
    }
}
"""


class TestStatementTerminator:
    @staticmethod
    def _instrument(statement):
        start = BRACELESS_NO_SEMI.index("for (uint256 i")
        body_start = BRACELESS_NO_SEMI.index(statement)
        end = body_start + len(statement)
        ir = {
            "contract": {
                "name": "Demo",
                "functions": [
                    {
                        "name": "copy",
                        "loops": [
                            {
                                "loop_id": "Demo.copy#loop0",
                                "category": "simple",
                                "depth": 0,
                                "src": f"{start}:{end - start}:0",
                                "body_src": f"{body_start}:{len(statement)}:0",
                                "body_is_block": False,
                                "body_summary": {
                                    "indices": ["i"],
                                    "carried_vars": [],
                                    "declared_vars": [],
                                    "carried_types": {"i": "uint256"},
                                },
                            }
                        ],
                    }
                ],
            }
        }
        return instrument(BRACELESS_NO_SEMI, ir)[0]

    def test_span_without_semicolon_still_produces_one(self):
        out = self._instrument("arr[i] = numbers[i]")
        assert "arr[i] = numbers[i];" in out

    def test_span_without_semicolon_leaves_no_stray_terminator(self):
        out = self._instrument("arr[i] = numbers[i]")
        assert "};" not in out.replace("\n", "").replace(" ", "")

    def test_span_including_semicolon_is_not_doubled(self):
        out = self._instrument("arr[i] = numbers[i];")
        assert ";;" not in out

    def test_braces_stay_balanced_either_way(self):
        for statement in ("arr[i] = numbers[i]", "arr[i] = numbers[i];"):
            out = self._instrument(statement)
            assert out.count("{") == out.count("}")


NON_ASCII_NESTED = """// SPDX-License-Identifier: MIT
pragma solidity 0.8.19;

contract T {
    function tri(uint256 n) external pure returns (uint256 total) {
        // pure + loops \u2192 easy target
        for (uint256 i = 1; i <= n; i++) {
            for (uint256 j = 1; j <= i; j++) {
                total += j;
            }
        }
    }
}
"""


def _nested_ir(source):
    data = source.encode("utf-8")
    ob = data.index(b"for (uint256 i")
    ib = data.index(b"for (uint256 j")
    obb = data.index(b"{", ob)
    ibb = data.index(b"{", ib)
    ie = data.index(b"            }", ibb) + len(b"            }")
    oe = data.index(b"        }", ie) + len(b"        }")
    return {
        "contract": {
            "name": "T",
            "functions": [
                {
                    "name": "tri",
                    "loops": [
                        {
                            "loop_id": "T.tri#loop0",
                            "category": "nested",
                            "depth": 0,
                            "src": f"{ob}:{oe - ob}:0",
                            "body_src": f"{obb}:{oe - obb}:0",
                            "body_is_block": True,
                            "body_summary": {
                                "indices": ["i"],
                                "carried_vars": [],
                                "declared_vars": [],
                                "carried_types": {"i": "uint256"},
                            },
                        },
                        {
                            "loop_id": "T.tri#loop1",
                            "category": "nested",
                            "depth": 1,
                            "src": f"{ib}:{ie - ib}:0",
                            "body_src": f"{ibb}:{ie - ibb}:0",
                            "body_is_block": True,
                            "body_summary": {
                                "indices": ["j"],
                                "carried_vars": ["total"],
                                "declared_vars": [],
                                "carried_types": {"total": "uint256", "j": "uint256"},
                            },
                        },
                    ],
                }
            ],
        }
    }


class TestByteOffsets:
    def test_source_index_is_identity_for_ascii(self):
        from testcrafter.instrument.loop_probe import SourceIndex

        index = SourceIndex("contract A { }")
        assert index.char_offset(5) == 5

    def test_source_index_accounts_for_multibyte_characters(self):
        from testcrafter.instrument.loop_probe import SourceIndex

        source = "// \u2192 x"
        index = SourceIndex(source)
        byte_pos = source.encode("utf-8").index(b"x")
        char_pos = source.index("x")
        assert byte_pos != char_pos
        assert index.char_offset(byte_pos) == char_pos

    def test_non_ascii_source_does_not_corrupt_the_loop_header(self):
        out, _ = instrument(NON_ASCII_NESTED, _nested_ir(NON_ASCII_NESTED))
        assert out.count("for (uint256 i") == 1
        assert out.count("for (uint256 j") == 1
        assert "fouint256" not in out

    def test_non_ascii_source_keeps_braces_balanced(self):
        out, _ = instrument(NON_ASCII_NESTED, _nested_ir(NON_ASCII_NESTED))
        assert out.count("{") == out.count("}")

    def test_nested_loops_each_get_their_own_counter(self):
        out, probes = instrument(NON_ASCII_NESTED, _nested_ir(NON_ASCII_NESTED))
        counters = {p["counter"] for p in probes}
        assert len(counters) == 2
        for counter in counters:
            assert f"uint256 {counter} = 0;" in out

    def test_inner_probes_sit_inside_the_outer_loop(self):
        out, _ = instrument(NON_ASCII_NESTED, _nested_ir(NON_ASCII_NESTED))
        outer_enter = out.index("LOOP_ENTER T.tri#loop0")
        inner_enter = out.index("LOOP_ENTER T.tri#loop1")
        outer_exit = out.index("LOOP_EXIT T.tri#loop0")
        assert outer_enter < inner_enter < outer_exit


INIT_SCOPED_INDEX = """// SPDX-License-Identifier: MIT
pragma solidity 0.8.19;

contract D {
    uint256[] public numbers;

    function sumUnchecked(uint256 n) external view returns (uint256 s) {
        for (uint256 i = 0; i < n; ) {
            unchecked { s += numbers[i]; i++; }
        }
    }
}
"""


def _init_scoped_ir(source):
    data = source.encode("utf-8")
    start = data.index(b"for (uint256 i")
    body_start = data.index(b"{", start)
    end = data.index(b"        }", body_start) + len(b"        }")
    return {
        "contract": {
            "name": "D",
            "functions": [
                {
                    "name": "sumUnchecked",
                    "loops": [
                        {
                            "loop_id": "D.sumUnchecked#loop0",
                            "category": "simple",
                            "depth": 0,
                            "src": f"{start}:{end - start}:0",
                            "body_src": f"{body_start}:{end - body_start}:0",
                            "body_is_block": True,
                            "body_summary": {
                                "indices": ["i"],
                                "carried_vars": ["i", "s"],
                                "declared_vars": [],
                                "carried_types": {"i": "uint256", "s": "uint256"},
                            },
                        }
                    ],
                }
            ],
        }
    }


class TestVariableScope:
    def test_index_declared_in_init_is_not_logged_outside_the_loop(self):
        out, _ = instrument(INIT_SCOPED_INDEX, _init_scoped_ir(INIT_SCOPED_INDEX))
        for line in out.splitlines():
            if "ENTER_VAR" in line or "EXIT_VAR" in line:
                assert "loop0 i" not in line

    def test_index_is_still_logged_inside_the_loop(self):
        out, _ = instrument(INIT_SCOPED_INDEX, _init_scoped_ir(INIT_SCOPED_INDEX))
        assert "ITER_IDX D.sumUnchecked#loop0 i" in out

    def test_function_scoped_variable_is_watched_throughout(self):
        out, probes = instrument(INIT_SCOPED_INDEX, _init_scoped_ir(INIT_SCOPED_INDEX))
        assert [w["name"] for w in probes[0]["watched"]] == ["s"]
        assert "ENTER_VAR D.sumUnchecked#loop0 s" in out
        assert "EXIT_VAR D.sumUnchecked#loop0 s" in out

    def test_index_is_not_logged_twice_per_iteration(self):
        out, _ = instrument(INIT_SCOPED_INDEX, _init_scoped_ir(INIT_SCOPED_INDEX))
        assert out.count("D.sumUnchecked#loop0 i\"") == 1

    def test_unchecked_block_body_is_preserved(self):
        out, _ = instrument(INIT_SCOPED_INDEX, _init_scoped_ir(INIT_SCOPED_INDEX))
        assert "unchecked { s += numbers[i]; i++; }" in out


VERBOSE_FORGE_TRACE = """
  [INVSOL] LOOP_ENTER T.f#loop0
    |- [0] console::log("[INVSOL] LOOP_ENTER T.f#loop0") [staticcall]
  [INVSOL] ENTER_VAR T.f#loop0 total 0
    |- [0] console::log("[INVSOL] ENTER_VAR T.f#loop0 total", 0) [staticcall]
  [INVSOL] LOOP_ITER T.f#loop0 1
    |- [0] console::log("[INVSOL] LOOP_ITER T.f#loop0", 1) [staticcall]
  [INVSOL] ITER_VAR T.f#loop0 total 5
    |- [0] console::log("[INVSOL] ITER_VAR T.f#loop0 total", 5) [staticcall]
  [INVSOL] LOOP_EXIT T.f#loop0 1
    |- [0] console::log("[INVSOL] LOOP_EXIT T.f#loop0", 1) [staticcall]
  [INVSOL] EXIT_VAR T.f#loop0 total 5
    |- [0] console::log("[INVSOL] EXIT_VAR T.f#loop0 total", 5) [staticcall]
"""


class TestVerboseTraceEchoes:
    def test_echoed_call_does_not_duplicate_the_run(self):
        runs = parse_lines(VERBOSE_FORGE_TRACE.splitlines())
        assert len(runs) == 1

    def test_loop_id_has_no_quote_or_paren_suffix(self):
        runs = parse_lines(VERBOSE_FORGE_TRACE.splitlines())
        assert runs[0].loop_id == "T.f#loop0"

    def test_variable_names_have_no_quote_or_comma_suffix(self):
        runs = parse_lines(VERBOSE_FORGE_TRACE.splitlines())
        assert set(runs[0].entry) == {"total"}
        assert set(runs[0].exit) == {"total"}

    def test_trip_count_is_not_doubled(self):
        runs = parse_lines(VERBOSE_FORGE_TRACE.splitlines())
        assert runs[0].trip_count == 1
        assert len(runs[0].iterations) == 1

    def test_summary_reports_one_loop(self):
        summary = summarise(parse_lines(VERBOSE_FORGE_TRACE.splitlines()))
        assert len(summary["loops"]) == 1
        assert summary["loops"][0]["observed_vars"] == ["total"]
