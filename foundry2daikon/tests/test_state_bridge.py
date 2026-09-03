import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from state_bridge import flatten, to_trace_runs, write_daikon_files


class Snapshot:
    def __init__(self, values=None, elements=None, mappings=None):
        self.values = values or {}
        self.elements = elements or {}
        self.mappings = mappings or {}


class Call:
    def __init__(self, function, pre, post):
        self.function = function
        self.pre = pre
        self.post = post


def a_call():
    pre = Snapshot(
        {"total": 0, "u_age": 30, "u_balance": 5},
        {"holders": {0: "0xaaa"}},
        {"balances": {"0xaaa": 0}},
    )
    post = Snapshot(
        {"total": 100, "u_age": 30, "u_balance": 105},
        {"holders": {0: "0xaaa", 1: "0xbbb"}},
        {"balances": {"0xaaa": 100}},
    )
    return Call("deposit", pre, post)


class TestFlattening:
    def test_a_struct_field_is_its_own_variable(self):
        # Section 3.4.1: a struct u with fields age and balance becomes
        # u_age and u_balance.
        flat = flatten(a_call().post)
        assert flat["u_age"] == "30"
        assert flat["u_balance"] == "105"

    def test_an_array_becomes_a_length_and_its_elements(self):
        flat = flatten(a_call().post)
        assert flat["holders_length"] == "2"
        assert flat["holders[0]"] == "0xaaa"
        assert flat["holders[1]"] == "0xbbb"

    def test_a_mapping_becomes_the_keys_that_were_touched(self):
        assert flatten(a_call().post)["balances[0xaaa]"] == "100"

    def test_a_recorded_length_wins_over_the_element_count(self):
        # The probe only records the first few elements, so the length it
        # logged is the real one and the element count is not.
        snapshot = Snapshot({"xs_length": 40}, {"xs": {0: "1", 1: "2"}})
        assert flatten(snapshot)["xs_length"] == "40"


class TestProgramPoints:
    def test_a_call_becomes_an_entry_and_an_exit(self):
        runs = to_trace_runs([a_call()], "Bank")
        assert [p.name for p in runs[0].program_points] == [
            "Bank.deposit():::ENTER",
            "Bank.deposit():::EXIT1",
        ]

    def test_each_call_gets_its_own_nonce(self):
        runs = to_trace_runs([a_call(), a_call()], "Bank")
        assert [r.invocation_nonce for r in runs] == [1, 2]

    def test_addresses_are_typed_as_hashcodes(self):
        exit_point = to_trace_runs([a_call()], "Bank")[0].program_points[1]
        assert exit_point.variables["holders[0]"].type == "hashcode"
        assert exit_point.variables["total"].type == "int"

    def test_a_call_without_a_name_is_skipped(self):
        assert to_trace_runs([Call("", Snapshot(), Snapshot())], "Bank") == []


class TestFiles:
    def test_both_files_are_written(self, tmp_path=None):
        import tempfile

        directory = tmp_path or tempfile.mkdtemp()
        decls, dtrace = write_daikon_files([a_call()], "Bank", directory)
        assert decls.name == "Bank.decls"
        assert dtrace.name == "Bank.dtrace"
        assert "ppt Bank.deposit():::ENTER" in decls.read_text()
        assert "Bank.deposit():::EXIT1" in dtrace.read_text()

    def test_nothing_to_translate_returns_none(self):
        import tempfile

        assert write_daikon_files([], "Bank", tempfile.mkdtemp()) is None
