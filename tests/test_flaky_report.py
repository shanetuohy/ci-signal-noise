"""Tests for ci_signal_noise.flaky_report formatting."""

import unittest

from ci_signal_noise.flaky import FlakeReport
from ci_signal_noise.flaky_report import format_flaky_report


class TestFormatFlakyReport(unittest.TestCase):
    """Test flaky test report formatting."""

    def _report(self, name="test_login", pass_count=7, fail_count=3,
                total_runs=10, flake_rate=0.3):
        return FlakeReport(
            test_name=name,
            pass_count=pass_count,
            fail_count=fail_count,
            total_runs=total_runs,
            flake_rate=flake_rate,
            first_seen=0,
            last_seen=9,
        )

    def test_empty_reports(self):
        text = format_flaky_report([], total_runs=10)
        self.assertIn("No flaky tests detected", text)
        self.assertIn("10 runs", text)

    def test_normal_reports(self):
        reports = [
            self._report("test_auth", flake_rate=0.2, pass_count=8, fail_count=2),
            self._report("test_db", flake_rate=0.1, pass_count=9, fail_count=1),
        ]
        text = format_flaky_report(reports, total_runs=10)
        self.assertIn("2 flaky test(s)", text)
        self.assertIn("test_auth", text)
        self.assertIn("test_db", text)
        # Low flake rates -> monitoring message
        self.assertIn("monitor", text)

    def test_high_flake_suggested_actions(self):
        reports = [self._report("test_flaky_one", flake_rate=0.5, pass_count=5, fail_count=5)]
        text = format_flaky_report(reports, total_runs=10)
        self.assertIn("Suggested actions", text)
        self.assertIn("Investigate", text)
        self.assertIn("test_flaky_one", text)
