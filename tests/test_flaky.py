"""Tests for flaky test detection."""

from ci_signal_noise.flaky import (
    FlakeReport,
    TestResult,
    detect_flaky_tests,
    extract_test_results,
)
from ci_signal_noise.flaky_report import format_flaky_report


# --- extract_test_results tests ---


class TestPytestParsing:
    def test_passed_prefix(self):
        lines = ["PASSED tests/test_foo.py::test_bar"]
        results = extract_test_results(lines)
        assert len(results) == 1
        assert results[0].name == "tests/test_foo.py::test_bar"
        assert results[0].passed is True

    def test_failed_prefix(self):
        lines = ["FAILED tests/test_foo.py::test_baz"]
        results = extract_test_results(lines)
        assert len(results) == 1
        assert results[0].passed is False

    def test_passed_suffix(self):
        lines = ["tests/test_foo.py::test_bar PASSED"]
        results = extract_test_results(lines)
        assert len(results) == 1
        assert results[0].passed is True

    def test_failed_suffix(self):
        lines = ["tests/test_foo.py::test_baz FAILED"]
        results = extract_test_results(lines)
        assert len(results) == 1
        assert results[0].passed is False

    def test_parametrized(self):
        lines = ["tests/test_math.py::test_add[1-2-3] PASSED"]
        results = extract_test_results(lines)
        assert results[0].name == "tests/test_math.py::test_add[1-2-3]"

    def test_deduplication(self):
        lines = [
            "tests/test_foo.py::test_bar PASSED",
            "tests/test_foo.py::test_bar PASSED",
        ]
        results = extract_test_results(lines)
        assert len(results) == 1


class TestGoTestParsing:
    def test_pass(self):
        lines = ["--- PASS: TestFoo (0.00s)"]
        results = extract_test_results(lines)
        assert len(results) == 1
        assert results[0].name == "TestFoo"
        assert results[0].passed is True

    def test_fail(self):
        lines = ["--- FAIL: TestBar (0.12s)"]
        results = extract_test_results(lines)
        assert len(results) == 1
        assert results[0].name == "TestBar"
        assert results[0].passed is False

    def test_subtest(self):
        lines = ["--- PASS: TestFoo/subcase_one (0.01s)"]
        results = extract_test_results(lines)
        assert results[0].name == "TestFoo/subcase_one"


class TestJestParsing:
    def test_pass_checkmark(self):
        lines = ["    ✓ should render correctly (5 ms)"]
        results = extract_test_results(lines)
        assert len(results) == 1
        assert results[0].passed is True
        assert results[0].name == "should render correctly"

    def test_fail_cross(self):
        lines = ["    ✕ should handle errors (12 ms)"]
        results = extract_test_results(lines)
        assert len(results) == 1
        assert results[0].passed is False

    def test_pass_sqrt(self):
        lines = ["    √ should work on windows"]
        results = extract_test_results(lines)
        assert len(results) == 1
        assert results[0].passed is True

    def test_fail_times(self):
        lines = ["    × should fail on windows"]
        results = extract_test_results(lines)
        assert len(results) == 1
        assert results[0].passed is False

    def test_suite_line_ignored(self):
        lines = ["PASS src/utils.test.js"]
        results = extract_test_results(lines)
        assert len(results) == 0


class TestMixedFormats:
    def test_mixed_log(self):
        lines = [
            "Running tests...",
            "tests/test_foo.py::test_one PASSED",
            "tests/test_foo.py::test_two FAILED",
            "--- PASS: TestGoFunc (0.01s)",
            "    ✓ should render (3 ms)",
            "Some noise line",
        ]
        results = extract_test_results(lines)
        assert len(results) == 4
        names = {r.name for r in results}
        assert "tests/test_foo.py::test_one" in names
        assert "TestGoFunc" in names


# --- detect_flaky_tests tests ---


class TestDetectFlaky:
    def test_no_flakes(self):
        run1 = [TestResult("test_a", True), TestResult("test_b", False)]
        run2 = [TestResult("test_a", True), TestResult("test_b", False)]
        reports = detect_flaky_tests([run1, run2])
        assert len(reports) == 0

    def test_one_flake(self):
        run1 = [TestResult("test_a", True), TestResult("test_b", True)]
        run2 = [TestResult("test_a", True), TestResult("test_b", False)]
        reports = detect_flaky_tests([run1, run2])
        assert len(reports) == 1
        assert reports[0].test_name == "test_b"
        assert reports[0].pass_count == 1
        assert reports[0].fail_count == 1
        assert reports[0].flake_rate == 0.5

    def test_multiple_runs(self):
        runs = [
            [TestResult("test_a", True), TestResult("test_b", True)],
            [TestResult("test_a", False), TestResult("test_b", True)],
            [TestResult("test_a", True), TestResult("test_b", True)],
        ]
        reports = detect_flaky_tests(runs)
        assert len(reports) == 1
        assert reports[0].test_name == "test_a"
        assert reports[0].pass_count == 2
        assert reports[0].fail_count == 1
        assert reports[0].total_runs == 3

    def test_sorted_by_flake_rate(self):
        runs = [
            [TestResult("stable_flake", True), TestResult("worse_flake", True)],
            [TestResult("stable_flake", True), TestResult("worse_flake", False)],
            [TestResult("stable_flake", False), TestResult("worse_flake", False)],
            [TestResult("stable_flake", True), TestResult("worse_flake", True)],
        ]
        reports = detect_flaky_tests(runs)
        assert len(reports) == 2
        # worse_flake: 2 pass, 2 fail = 0.5; stable_flake: 3 pass, 1 fail = 0.25
        assert reports[0].test_name == "worse_flake"
        assert reports[1].test_name == "stable_flake"

    def test_test_missing_from_some_runs(self):
        run1 = [TestResult("test_a", True)]
        run2 = [TestResult("test_a", False), TestResult("test_b", True)]
        reports = detect_flaky_tests([run1, run2])
        assert len(reports) == 1
        assert reports[0].test_name == "test_a"

    def test_empty_runs(self):
        reports = detect_flaky_tests([[], []])
        assert len(reports) == 0


# --- format_flaky_report tests ---


class TestFormatReport:
    def test_no_flakes(self):
        output = format_flaky_report([], total_runs=3)
        assert "No flaky tests" in output

    def test_with_flakes(self):
        reports = [
            FlakeReport("test_a", pass_count=2, fail_count=1, total_runs=3,
                        flake_rate=0.333, first_seen=0, last_seen=2),
        ]
        output = format_flaky_report(reports, total_runs=3)
        assert "test_a" in output
        assert "1 flaky test" in output
        assert "Investigate" in output

    def test_low_flake_no_urgent(self):
        reports = [
            FlakeReport("test_a", pass_count=4, fail_count=1, total_runs=5,
                        flake_rate=0.2, first_seen=0, last_seen=4),
        ]
        output = format_flaky_report(reports, total_runs=5)
        assert "no urgent action" in output
