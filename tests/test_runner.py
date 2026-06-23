"""Tests for the local test runner module."""

from unittest.mock import patch

from ci_signal_noise.flaky import FlakeReport, TestResult
from ci_signal_noise.runner import analyze_local, run_and_collect, run_tests_once


PYTEST_OUTPUT_PASS = """\
============================= test session starts ==============================
collected 3 items

tests/test_foo.py::test_add PASSED
tests/test_foo.py::test_sub PASSED
tests/test_foo.py::test_mul PASSED

============================== 3 passed in 0.02s ===============================
"""

PYTEST_OUTPUT_MIXED = """\
============================= test session starts ==============================
collected 3 items

tests/test_foo.py::test_add PASSED
tests/test_foo.py::test_sub FAILED
tests/test_foo.py::test_mul PASSED

============================== 1 failed, 2 passed in 0.03s ====================
"""

PYTEST_OUTPUT_EMPTY = """\
============================= test session starts ==============================
collected 0 items

============================== no tests ran in 0.00s ===========================
"""


class TestRunTestsOnce:
    def test_captures_output(self):
        with patch("ci_signal_noise.runner.subprocess.run") as mock_run:
            mock_run.return_value.stdout = "line1\nline2"
            mock_run.return_value.stderr = "err1"
            lines = run_tests_once("pytest", "/tmp")
            assert "line1" in lines
            assert "line2" in lines
            assert "err1" in lines
            mock_run.assert_called_once()

    def test_passes_cwd(self):
        with patch("ci_signal_noise.runner.subprocess.run") as mock_run:
            mock_run.return_value.stdout = ""
            mock_run.return_value.stderr = ""
            run_tests_once("pytest -v", "/my/project")
            call_kwargs = mock_run.call_args
            assert call_kwargs.kwargs["cwd"] == "/my/project"


class TestRunAndCollect:
    def test_parses_pytest_output(self):
        with patch("ci_signal_noise.runner.run_tests_once") as mock_run:
            mock_run.return_value = PYTEST_OUTPUT_PASS.splitlines()
            results = run_and_collect("pytest", "/tmp", iterations=1)
            assert len(results) == 1
            assert len(results[0]) == 3
            assert all(r.passed for r in results[0])

    def test_multiple_iterations(self):
        with patch("ci_signal_noise.runner.run_tests_once") as mock_run:
            mock_run.return_value = PYTEST_OUTPUT_PASS.splitlines()
            results = run_and_collect("pytest", "/tmp", iterations=3)
            assert len(results) == 3
            assert mock_run.call_count == 3

    def test_empty_output(self):
        with patch("ci_signal_noise.runner.run_tests_once") as mock_run:
            mock_run.return_value = PYTEST_OUTPUT_EMPTY.splitlines()
            results = run_and_collect("pytest", "/tmp", iterations=2)
            assert len(results) == 2
            assert all(len(r) == 0 for r in results)

    def test_no_output(self):
        with patch("ci_signal_noise.runner.run_tests_once") as mock_run:
            mock_run.return_value = []
            results = run_and_collect("pytest", "/tmp", iterations=1)
            assert len(results) == 1
            assert results[0] == []


class TestAnalyzeLocal:
    def test_detects_flaky(self):
        """A test that passes in run 1 but fails in run 2 is flaky."""
        with patch("ci_signal_noise.runner.run_tests_once") as mock_run:
            mock_run.side_effect = [
                PYTEST_OUTPUT_PASS.splitlines(),
                PYTEST_OUTPUT_MIXED.splitlines(),
            ]
            reports = analyze_local("pytest", "/tmp", iterations=2)
            assert len(reports) == 1
            assert reports[0].test_name == "tests/test_foo.py::test_sub"
            assert reports[0].pass_count == 1
            assert reports[0].fail_count == 1

    def test_no_flakes_when_consistent(self):
        with patch("ci_signal_noise.runner.run_tests_once") as mock_run:
            mock_run.return_value = PYTEST_OUTPUT_PASS.splitlines()
            reports = analyze_local("pytest", "/tmp", iterations=3)
            assert reports == []

    def test_command_failure_still_parses(self):
        """Even if the command exits non-zero, we still parse output."""
        with patch("ci_signal_noise.runner.run_tests_once") as mock_run:
            mock_run.return_value = PYTEST_OUTPUT_MIXED.splitlines()
            reports = analyze_local("pytest", "/tmp", iterations=2)
            # All runs identical — no flakes
            assert reports == []
