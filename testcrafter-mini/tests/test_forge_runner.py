import os
import stat
import subprocess
import time

import pytest

from testcrafter.run.forge_runner import (
    ForgeResult,
    describe,
    run_forge_test,
    write_trace,
)


def _fake_forge(tmp_path, script):
    path = tmp_path / "forge"
    path.write_text("#!/bin/bash\n" + script)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    os.environ["FORGE_PATH"] = str(path)
    return str(path)


@pytest.fixture(autouse=True)
def _clear_env():
    yield
    os.environ.pop("FORGE_PATH", None)


class TestRunner:
    def test_successful_run_is_reported_ok(self, tmp_path):
        _fake_forge(tmp_path, "echo done\nexit 0\n")
        result = run_forge_test(str(tmp_path), timeout=10, quiet=True)
        assert result.ok is True
        assert result.returncode == 0
        assert "done" in result.output

    def test_failing_run_is_not_ok(self, tmp_path):
        _fake_forge(tmp_path, "echo boom\nexit 1\n")
        result = run_forge_test(str(tmp_path), timeout=10, quiet=True)
        assert result.ok is False
        assert result.timed_out is False

    def test_timeout_is_flagged_and_partial_output_kept(self, tmp_path):
        _fake_forge(tmp_path, 'for i in 1 2 3 4 5 6 7 8 9; do echo "line $i"; sleep 0.4; done\n')
        result = run_forge_test(str(tmp_path), timeout=1, quiet=True)
        assert result.timed_out is True
        assert result.ok is False
        assert "line 1" in result.output

    def test_lines_are_delivered_while_running(self, tmp_path):
        _fake_forge(tmp_path, 'for i in 1 2 3; do echo "line $i"; sleep 0.2; done\n')
        seen = []
        run_forge_test(str(tmp_path), timeout=10, on_line=seen.append)
        assert seen == ["line 1", "line 2", "line 3"]

    def test_missing_forge_raises(self, tmp_path):
        os.environ["FORGE_PATH"] = str(tmp_path / "definitely-not-here")
        with pytest.raises(Exception):
            run_forge_test(str(tmp_path), timeout=5, quiet=True)

    def test_fuzz_runs_and_filters_reach_the_command(self, tmp_path):
        _fake_forge(tmp_path, "echo ok\n")
        result = run_forge_test(
            str(tmp_path),
            timeout=10,
            fuzz_runs=32,
            match_contract="Demo",
            quiet=True,
        )
        assert "--fuzz-runs" in result.command
        assert "32" in result.command
        assert "--match-contract" in result.command

    def test_trace_is_written_to_disk(self, tmp_path):
        _fake_forge(tmp_path, "echo hello\n")
        result = run_forge_test(str(tmp_path), timeout=10, quiet=True)
        out = write_trace(result, str(tmp_path / "nested" / "trace.txt"))
        assert os.path.exists(out)
        assert "hello" in open(out).read()

    def test_describe_mentions_timeout(self):
        result = ForgeResult(
            returncode=-15, output="", duration=1.0, timed_out=True, command=["forge"]
        )
        assert "timed out" in describe(result)
