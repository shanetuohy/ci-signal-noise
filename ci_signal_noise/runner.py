"""Run a test command multiple times locally and detect flaky tests."""

import subprocess

from .flaky import FlakeReport, TestResult, detect_flaky_tests, extract_test_results


def run_tests_once(cmd: str, cwd: str) -> list[str]:
    """Execute test command and return stdout+stderr lines."""
    result = subprocess.run(
        cmd,
        shell=True,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    # Combine stdout and stderr — test frameworks write to both
    output = result.stdout + "\n" + result.stderr
    return output.splitlines()


def run_and_collect(
    cmd: str,
    cwd: str,
    iterations: int = 5,
) -> list[list[TestResult]]:
    """Run test command N times and collect parsed results per run."""
    all_results: list[list[TestResult]] = []
    for i in range(iterations):
        lines = run_tests_once(cmd, cwd)
        results = extract_test_results(lines)
        all_results.append(results)
    return all_results


def analyze_local(
    cmd: str,
    cwd: str,
    iterations: int = 5,
) -> list[FlakeReport]:
    """Run tests multiple times locally and return flake reports."""
    runs_results = run_and_collect(cmd, cwd, iterations)
    return detect_flaky_tests(runs_results)
