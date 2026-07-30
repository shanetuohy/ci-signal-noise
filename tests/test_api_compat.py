"""Contract tests that lock down the public API surface of ci-signal-noise.

These tests verify function signatures, return types, and dataclass fields
so that breaking changes are caught before they reach consumers.
"""

import dataclasses

from ci_signal_noise import (
    FlakeReport,
    TestResult,
    classify_line,
    detect_flaky_tests,
    extract_test_results,
    score_lines,
)


# --- score_lines() contract ---

class TestScoreLinesContract:
    """score_lines() must always return a dict with the expected keys."""

    REQUIRED_KEYS = {"signal", "noise", "neutral", "total", "signal_pct"}

    def test_return_keys_present(self):
        result = score_lines(["some line"])
        assert set(result.keys()) == self.REQUIRED_KEYS

    def test_return_keys_empty_input(self):
        result = score_lines([])
        assert set(result.keys()) == self.REQUIRED_KEYS

    def test_counts_are_ints(self):
        result = score_lines(["FAILED test_foo"])
        for key in ("signal", "noise", "neutral", "total"):
            assert isinstance(result[key], int), f"{key} should be int"

    def test_signal_pct_is_float(self):
        result = score_lines(["hello"])
        assert isinstance(result["signal_pct"], float)


# --- classify_line() contract ---

class TestClassifyLineContract:
    """classify_line() must return one of the three allowed labels."""

    ALLOWED = {"signal", "noise", "neutral"}

    def test_returns_allowed_label(self):
        for line in ["FAILED foo", "", "just a log line"]:
            result = classify_line(line)
            assert result in self.ALLOWED, f"Got {result!r} for {line!r}"

    def test_return_type_is_str(self):
        assert isinstance(classify_line("anything"), str)


# --- TestResult dataclass contract ---

class TestTestResultContract:
    """TestResult must have the expected fields with the expected types."""

    EXPECTED_FIELDS = {"name": str, "passed": bool}

    def test_fields_exist(self):
        fields = {f.name: f.type for f in dataclasses.fields(TestResult)}
        for name in self.EXPECTED_FIELDS:
            assert name in fields, f"Missing field: {name}"

    def test_is_dataclass(self):
        assert dataclasses.is_dataclass(TestResult)

    def test_instantiation(self):
        tr = TestResult(name="test_foo", passed=True)
        assert tr.name == "test_foo"
        assert tr.passed is True


# --- FlakeReport dataclass contract ---

class TestFlakeReportContract:
    """FlakeReport must have the expected fields."""

    EXPECTED_FIELDS = {
        "test_name": str,
        "pass_count": int,
        "fail_count": int,
        "total_runs": int,
        "flake_rate": float,
        "first_seen": int,
        "last_seen": int,
    }

    def test_fields_exist(self):
        fields = {f.name: f.type for f in dataclasses.fields(FlakeReport)}
        for name in self.EXPECTED_FIELDS:
            assert name in fields, f"Missing field: {name}"

    def test_is_dataclass(self):
        assert dataclasses.is_dataclass(FlakeReport)

    def test_instantiation(self):
        fr = FlakeReport(
            test_name="test_x",
            pass_count=2,
            fail_count=1,
            total_runs=3,
            flake_rate=0.333,
            first_seen=0,
            last_seen=2,
        )
        assert fr.test_name == "test_x"
        assert fr.flake_rate == 0.333


# --- extract_test_results() contract ---

class TestExtractTestResultsContract:
    """extract_test_results() must return list[TestResult]."""

    def test_returns_list(self):
        result = extract_test_results(["PASSED tests/test_foo.py::test_bar"])
        assert isinstance(result, list)

    def test_elements_are_test_results(self):
        result = extract_test_results(["PASSED tests/test_foo.py::test_bar"])
        assert len(result) > 0
        assert isinstance(result[0], TestResult)

    def test_empty_input_returns_empty_list(self):
        assert extract_test_results([]) == []


# --- detect_flaky_tests() contract ---

class TestDetectFlakyTestsContract:
    """detect_flaky_tests() must return list[FlakeReport]."""

    def test_returns_list(self):
        runs = [
            [TestResult("test_a", True)],
            [TestResult("test_a", False)],
        ]
        result = detect_flaky_tests(runs)
        assert isinstance(result, list)

    def test_elements_are_flake_reports(self):
        runs = [
            [TestResult("test_a", True)],
            [TestResult("test_a", False)],
        ]
        result = detect_flaky_tests(runs)
        assert len(result) > 0
        assert isinstance(result[0], FlakeReport)

    def test_no_flakes_returns_empty(self):
        runs = [
            [TestResult("test_a", True)],
            [TestResult("test_a", True)],
        ]
        assert detect_flaky_tests(runs) == []
