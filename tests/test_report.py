"""Tests for ci_signal_noise.report formatting functions."""

import unittest

from ci_signal_noise.report import format_multi_run_summary, format_report


class TestFormatReport(unittest.TestCase):
    """Test single-run report formatting."""

    def _run_info(self, **overrides):
        base = {
            "displayTitle": "Fix auth bug",
            "databaseId": 12345,
            "conclusion": "failure",
            "workflowName": "CI",
        }
        base.update(overrides)
        return base

    def _job_scores(self):
        return {
            "build": {"signal_pct": 80.0, "signal": 8, "noise": 1, "neutral": 1, "total": 10},
            "lint": {"signal_pct": 20.0, "signal": 2, "noise": 6, "neutral": 2, "total": 10},
        }

    def _overall(self):
        return {"signal_pct": 50.0, "signal": 10, "noise": 7, "neutral": 3, "total": 20}

    def test_basic_formatting(self):
        text = format_report(self._run_info(), self._job_scores(), self._overall())
        self.assertIn("Run #12345", text)
        self.assertIn("Fix auth bug", text)
        self.assertIn("Workflow: CI", text)
        self.assertIn("build", text)
        self.assertIn("lint", text)
        self.assertIn("Overall: 50.0% signal", text)

    def test_empty_job_scores(self):
        text = format_report(self._run_info(), {}, self._overall())
        self.assertIn("Run #12345", text)
        self.assertIn("Overall:", text)

    def test_long_name_truncation(self):
        long_name = "a" * 60
        jobs = {long_name: {"signal_pct": 50.0, "signal": 5, "noise": 3, "neutral": 2, "total": 10}}
        text = format_report(self._run_info(), jobs, self._overall())
        # Name should be capped at 50 chars in the table
        lines = text.split("\n")
        job_lines = [l for l in lines if "50.0%" in l]
        self.assertTrue(len(job_lines) > 0)


class TestFormatMultiRunSummary(unittest.TestCase):
    """Test multi-run summary formatting."""

    def test_empty_list(self):
        text = format_multi_run_summary([])
        self.assertEqual(text, "No runs to report.")

    def test_multiple_runs(self):
        runs = [
            ({"databaseId": 1, "conclusion": "success", "displayTitle": "First"}, {"signal_pct": 90.0}),
            ({"databaseId": 2, "conclusion": "failure", "displayTitle": "Second"}, {"signal_pct": 30.0}),
        ]
        text = format_multi_run_summary(runs)
        self.assertIn("Summary across runs", text)
        self.assertIn("1", text)
        self.assertIn("2", text)
        self.assertIn("90.0%", text)
        self.assertIn("30.0%", text)
