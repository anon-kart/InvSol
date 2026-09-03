from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional

DEFAULT_TIMEOUT = 600
DEFAULT_FUZZ_RUNS = 64


@dataclass
class ForgeResult:
    returncode: int
    output: str
    duration: float
    timed_out: bool
    command: List[str]

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.timed_out


def find_forge() -> Optional[str]:
    return os.environ.get("FORGE_PATH") or shutil.which("forge")


def run_forge_test(
    project_dir: str,
    *,
    verbosity: int = 4,
    fuzz_runs: int = DEFAULT_FUZZ_RUNS,
    timeout: int = DEFAULT_TIMEOUT,
    match_test: Optional[str] = None,
    match_contract: Optional[str] = None,
    on_line: Optional[Callable[[str], None]] = None,
    quiet: bool = False,
) -> ForgeResult:
    """
    Run forge test and capture the trace without going silent.

    Output is streamed line by line rather than buffered, and the run is killed
    once the timeout elapses. A blind subprocess call with no timeout cannot be
    told apart from a crash, which is the failure mode this avoids.

    The whole process group is signalled on timeout, because forge spawns
    workers that would otherwise survive the parent.
    """
    forge = find_forge()
    if forge is None:
        raise FileNotFoundError(
            "forge was not found on PATH. Install Foundry or set FORGE_PATH."
        )

    cmd = [forge, "test", f"-{'v' * max(1, verbosity)}", "--fuzz-runs", str(fuzz_runs)]
    if match_test:
        cmd += ["--match-test", match_test]
    if match_contract:
        cmd += ["--match-contract", match_contract]

    started = time.monotonic()
    collected: List[str] = []
    timed_out = False

    popen_kwargs = {
        "cwd": project_dir,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT,
        "text": True,
        "bufsize": 1,
    }
    if os.name == "posix":
        popen_kwargs["preexec_fn"] = os.setsid

    proc = subprocess.Popen(cmd, **popen_kwargs)

    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            collected.append(line)
            if on_line is not None:
                on_line(line.rstrip("\n"))
            elif not quiet:
                sys.stdout.write(line)
                sys.stdout.flush()

            if time.monotonic() - started > timeout:
                timed_out = True
                _terminate(proc)
                break
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        timed_out = True
        _terminate(proc)
    except KeyboardInterrupt:
        _terminate(proc)
        raise
    finally:
        if proc.stdout is not None:
            proc.stdout.close()

    duration = time.monotonic() - started
    return ForgeResult(
        returncode=proc.returncode if proc.returncode is not None else -1,
        output="".join(collected),
        duration=duration,
        timed_out=timed_out,
        command=cmd,
    )


def _terminate(proc: subprocess.Popen) -> None:
    """
    Stop the run and everything it started.

    The group is signalled rather than the direct child, and the follow-up kill
    is unconditional: a shell wrapper can exit on SIGTERM while the commands it
    spawned keep running, so checking the leader alone leaves orphans behind.
    """
    group = None
    if os.name == "posix":
        try:
            group = os.getpgid(proc.pid)
        except (ProcessLookupError, PermissionError):
            group = None

    if proc.poll() is None:
        try:
            if group is not None:
                os.killpg(group, signal.SIGTERM)
            else:
                proc.terminate()
        except (ProcessLookupError, PermissionError):
            pass
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass

    if group is not None:
        try:
            os.killpg(group, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
    elif proc.poll() is None:
        try:
            proc.kill()
        except (ProcessLookupError, PermissionError):
            pass


def write_trace(result: ForgeResult, path: str) -> str:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(result.output, encoding="utf-8")
    return str(out)


def describe(result: ForgeResult) -> str:
    lines = [
        f"command   {' '.join(result.command)}",
        f"exit      {result.returncode}",
        f"duration  {result.duration:.1f}s",
    ]
    if result.timed_out:
        lines.append("status    timed out, output is partial")
    elif result.returncode != 0:
        lines.append("status    forge reported failing tests")
    else:
        lines.append("status    ok")
    return "\n".join(lines)
