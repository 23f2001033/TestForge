"""Subprocess pytest and coverage runner."""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path


@dataclass(frozen=True)
class RunResult:
    ok: bool
    passed: int
    failed: int
    errors: int
    coverage: float | None
    stdout: str
    stderr: str
    returncode: int

    @property
    def summary(self) -> str:
        parts = []
        if self.passed:
            parts.append(f"{self.passed} passed")
        if self.failed:
            parts.append(f"{self.failed} failed")
        if self.errors:
            parts.append(f"{self.errors} errors")
        return ", ".join(parts) or "no tests"


def run_pytest(
    workdir: str | Path,
    package_parent: str | Path | None = None,
    timeout: int = 30,
    with_coverage: bool = True,
    package_name: str = "legacy_repo",
) -> RunResult:
    """Run pytest in a subprocess and parse pass/fail/error counts."""
    cwd = Path(workdir).resolve()
    command = [sys.executable, "-m", "pytest", "tests", "-q"]
    coverage_available = find_spec("pytest_cov") is not None
    if with_coverage and coverage_available:
        command.extend([f"--cov={package_name}", "--cov-report=term-missing"])

    env = None
    if package_parent is not None:
        env = dict(__import__("os").environ)
        parent = str(Path(package_parent).resolve())
        current = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = parent if not current else f"{parent}{__import__('os').pathsep}{current}"

    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return RunResult(
            ok=False,
            passed=0,
            failed=0,
            errors=1,
            coverage=None,
            stdout=exc.stdout or "",
            stderr=(exc.stderr or "") + f"\nTimed out after {timeout}s",
            returncode=124,
        )

    stdout = completed.stdout
    stderr = completed.stderr
    passed, failed, errors = _parse_counts(stdout + "\n" + stderr)
    coverage = _parse_coverage(stdout)
    ok = completed.returncode == 0 and failed == 0 and errors == 0
    return RunResult(
        ok=ok,
        passed=passed,
        failed=failed,
        errors=errors,
        coverage=coverage,
        stdout=stdout,
        stderr=stderr,
        returncode=completed.returncode,
    )


def _parse_counts(output: str) -> tuple[int, int, int]:
    passed = failed = errors = 0
    for pattern, name in [
        (r"(\d+)\s+passed", "passed"),
        (r"(\d+)\s+failed", "failed"),
        (r"(\d+)\s+errors?", "errors"),
        (r"(\d+)\s+error", "errors"),
    ]:
        matches = re.findall(pattern, output)
        if not matches:
            continue
        value = int(matches[-1])
        if name == "passed":
            passed = value
        elif name == "failed":
            failed = value
        else:
            errors = value
    return passed, failed, errors


def _parse_coverage(output: str) -> float | None:
    total_lines = [line for line in output.splitlines() if line.strip().startswith("TOTAL")]
    if not total_lines:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)%", total_lines[-1])
    return float(match.group(1)) if match else None
