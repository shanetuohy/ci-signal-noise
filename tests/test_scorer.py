"""Unit tests for the line classification logic."""

import unittest

from ci_signal_noise.scorer import classify_line, score_lines


class TestClassifyLine(unittest.TestCase):
    """Test individual line classification."""

    # --- Signal lines ---

    def test_test_failure(self):
        self.assertEqual(classify_line("FAIL test_auth.py::test_login - AssertionError"), "signal")

    def test_error_keyword(self):
        self.assertEqual(classify_line("Error: cannot find module 'express'"), "signal")

    def test_exception(self):
        self.assertEqual(classify_line("RuntimeException: null pointer"), "signal")

    def test_traceback(self):
        self.assertEqual(classify_line("Traceback (most recent call last):"), "signal")

    def test_panic(self):
        self.assertEqual(classify_line("panic: runtime error: index out of range"), "signal")

    def test_exit_code(self):
        self.assertEqual(classify_line("Process completed with exit code 1."), "signal")

    def test_build_failure(self):
        self.assertEqual(classify_line("Build failed with 3 errors"), "signal")

    def test_test_summary(self):
        self.assertEqual(classify_line("23 passed, 2 failed, 1 error"), "signal")

    def test_syntax_error(self):
        self.assertEqual(classify_line("SyntaxError: unexpected token"), "signal")

    def test_import_error(self):
        self.assertEqual(classify_line("ImportError: No module named 'foo'"), "signal")

    def test_compilation_error(self):
        self.assertEqual(classify_line("compilation error: undefined variable"), "signal")

    def test_diff_header(self):
        self.assertEqual(classify_line("--- expected"), "signal")

    # --- Noise lines ---

    def test_blank_line(self):
        self.assertEqual(classify_line(""), "noise")

    def test_whitespace_line(self):
        self.assertEqual(classify_line("   \t  "), "noise")

    def test_separator(self):
        self.assertEqual(classify_line("=" * 40), "noise")

    def test_download_progress(self):
        self.assertEqual(classify_line("Downloading pandas-2.0.0.tar.gz (5.2 MB)"), "noise")

    def test_already_satisfied(self):
        self.assertEqual(classify_line("Requirement already satisfied: requests>=2.0"), "noise")

    def test_using_cached(self):
        self.assertEqual(classify_line("  Using cached numpy-1.24.0-cp311.whl"), "noise")

    def test_collecting(self):
        self.assertEqual(classify_line("Collecting flask==2.3.0"), "noise")

    def test_npm_warn(self):
        self.assertEqual(classify_line("npm warn deprecated glob@7.2.3"), "noise")

    def test_added_packages(self):
        self.assertEqual(classify_line("added 150 packages in 12s"), "noise")

    def test_gh_actions_command(self):
        self.assertEqual(classify_line("##[group]Run actions/checkout@v4"), "noise")

    def test_run_prefix(self):
        self.assertEqual(classify_line("Run npm install"), "noise")

    def test_timing_line(self):
        self.assertEqual(classify_line("real\t0m12.345s"), "noise")

    # --- Neutral lines ---

    def test_regular_output(self):
        self.assertEqual(classify_line("Running test suite..."), "neutral")

    def test_code_output(self):
        self.assertEqual(classify_line("  def hello_world():"), "neutral")

    # --- Signal takes priority over noise ---

    def test_error_in_download(self):
        # Contains "error" (signal) and "downloading" (noise) - signal wins
        self.assertEqual(classify_line("Error downloading package foo 5.2 MB"), "signal")

    def test_failure_with_separator(self):
        self.assertEqual(classify_line("FAILED ============"), "signal")


class TestScoreLines(unittest.TestCase):
    """Test scoring aggregation."""

    def test_empty(self):
        result = score_lines([])
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["signal_pct"], 0.0)

    def test_all_signal(self):
        lines = ["Error: bad thing", "FAIL test_foo", "exit code 1"]
        result = score_lines(lines)
        self.assertEqual(result["signal"], 3)
        self.assertEqual(result["signal_pct"], 100.0)

    def test_all_noise(self):
        lines = ["", "========", "Collecting requests"]
        result = score_lines(lines)
        self.assertEqual(result["noise"], 3)
        self.assertEqual(result["signal_pct"], 0.0)

    def test_mixed(self):
        lines = [
            "Collecting requests",        # noise
            "",                            # noise
            "Installing dependencies...",  # noise (matches installing + depend)
            "Error: module not found",     # signal
            "FAIL test_auth",              # signal
        ]
        result = score_lines(lines)
        self.assertEqual(result["signal"], 2)
        self.assertEqual(result["noise"], 3)
        self.assertEqual(result["neutral"], 0)
        self.assertEqual(result["signal_pct"], 40.0)

    def test_all_neutral(self):
        lines = ["hello world", "running suite", "done"]
        result = score_lines(lines)
        self.assertEqual(result["signal_pct"], 50.0)  # no classified lines -> 50%


class TestRealLogFragments(unittest.TestCase):
    """Test with realistic CI log fragments."""

    def test_github_actions_setup(self):
        """Typical GH Actions setup noise should be classified as noise."""
        lines = [
            "##[group]Run actions/checkout@v4",
            "Run npm install",
            "npm warn deprecated inflight@1.0.6",
            "added 342 packages in 8s",
            "",
        ]
        result = score_lines(lines)
        self.assertEqual(result["noise"], 5)

    def test_pytest_failure(self):
        """Pytest failure output should be classified as signal."""
        lines = [
            "FAILED tests/test_auth.py::test_login_expired",
            "AssertionError: expected 200 but got 401",
            "1 failed, 23 passed",
        ]
        result = score_lines(lines)
        # All should be signal (assertion error, failed, summary with failed)
        self.assertEqual(result["signal"], 3)


if __name__ == "__main__":
    unittest.main()
