"""Parse test results from CI log lines and detect flaky tests."""

import re
from dataclasses import dataclass, field


@dataclass
class TestResult:
    """A single test's pass/fail status from one run."""

    name: str
    passed: bool


@dataclass
class FlakeReport:
    """Flakiness report for a single test."""

    test_name: str
    pass_count: int
    fail_count: int
    total_runs: int
    flake_rate: float
    first_seen: int  # run index (0-based)
    last_seen: int  # run index (0-based)


# --- Pytest patterns ---
# "PASSED tests/test_foo.py::test_bar" or "tests/test_foo.py::test_bar PASSED"
_PYTEST_RESULT = re.compile(
    r"(?:^|\s)(PASSED|FAILED)\s+([\w/.\-]+::[\w\[\]\-]+)"
    r"|"
    r"([\w/.\-]+::[\w\[\]\-]+)\s+(PASSED|FAILED)"
)

# --- Go test patterns ---
# "--- PASS: TestFoo (0.00s)" or "--- FAIL: TestFoo (0.00s)"
_GO_TEST_RESULT = re.compile(
    r"---\s+(PASS|FAIL):\s+([\w/]+)\s+\("
)

# --- Jest patterns ---
# "  ✓ should do something (5 ms)" or "  ✕ should do something (5 ms)"
# "  √ should do something" or "  × should do something"
_JEST_PASS = re.compile(r"^\s+[✓√]\s+(.+?)(?:\s+\(\d+\s*m?s\))?\s*$")
_JEST_FAIL = re.compile(r"^\s+[✕×✗]\s+(.+?)(?:\s+\(\d+\s*m?s\))?\s*$")

# Jest "PASS src/foo.test.js" / "FAIL src/foo.test.js" (suite-level, skip these)
_JEST_SUITE = re.compile(r"^\s*(PASS|FAIL)\s+\S+\.(test|spec)\.(js|ts|jsx|tsx)")


def extract_test_results(lines: list[str]) -> list[TestResult]:
    """Parse CI log lines and extract individual test results.

    Supports pytest, go test, and jest output formats.
    """
    results: list[TestResult] = []
    seen: set[str] = set()

    for line in lines:
        result = _parse_line(line)
        if result and result.name not in seen:
            results.append(result)
            seen.add(result.name)

    return results


def _parse_line(line: str) -> TestResult | None:
    """Try to parse a single line as a test result."""
    stripped = line.rstrip("\n")

    # Skip jest suite-level lines
    if _JEST_SUITE.match(stripped):
        return None

    # Pytest
    m = _PYTEST_RESULT.search(stripped)
    if m:
        if m.group(1):  # "PASSED/FAILED name"
            return TestResult(name=m.group(2), passed=m.group(1) == "PASSED")
        else:  # "name PASSED/FAILED"
            return TestResult(name=m.group(3), passed=m.group(4) == "PASSED")

    # Go test
    m = _GO_TEST_RESULT.search(stripped)
    if m:
        return TestResult(name=m.group(2), passed=m.group(1) == "PASS")

    # Jest pass (needs leading whitespace, so match before stripping)
    m = _JEST_PASS.match(stripped)
    if m:
        return TestResult(name=m.group(1).strip(), passed=True)

    # Jest fail
    m = _JEST_FAIL.match(stripped)
    if m:
        return TestResult(name=m.group(1).strip(), passed=False)

    return None


def detect_flaky_tests(runs_results: list[list[TestResult]]) -> list[FlakeReport]:
    """Compare test results across runs and identify flaky tests.

    A test is flaky if it has both passes and failures across different runs.

    Args:
        runs_results: list of test results per run (one list per run).

    Returns:
        List of FlakeReport for tests that flipped between pass/fail,
        sorted by flake_rate descending.
    """
    # Aggregate per test: {name: {run_idx: passed}}
    test_runs: dict[str, dict[int, bool]] = {}

    for run_idx, results in enumerate(runs_results):
        for tr in results:
            test_runs.setdefault(tr.name, {})[run_idx] = tr.passed

    reports: list[FlakeReport] = []
    total_runs = len(runs_results)

    for test_name, run_map in test_runs.items():
        pass_count = sum(1 for v in run_map.values() if v)
        fail_count = sum(1 for v in run_map.values() if not v)

        # Only flaky if it has both passes and failures
        if pass_count > 0 and fail_count > 0:
            indices = sorted(run_map.keys())
            flake_rate = round(min(pass_count, fail_count) / len(run_map), 3)
            reports.append(FlakeReport(
                test_name=test_name,
                pass_count=pass_count,
                fail_count=fail_count,
                total_runs=len(run_map),
                flake_rate=flake_rate,
                first_seen=indices[0],
                last_seen=indices[-1],
            ))

    reports.sort(key=lambda r: r.flake_rate, reverse=True)
    return reports
