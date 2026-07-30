"""ci-signal-noise: Score CI signal vs noise ratio from GitHub Actions logs."""

from .flaky import FlakeReport, TestResult, detect_flaky_tests, extract_test_results
from .scorer import classify_line, score_lines

__all__ = [
    "classify_line",
    "score_lines",
    "TestResult",
    "FlakeReport",
    "extract_test_results",
    "detect_flaky_tests",
]
