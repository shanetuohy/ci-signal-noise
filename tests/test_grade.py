"""Tests for grading, noise source analysis, and JSON output."""

import json
import unittest
from unittest.mock import patch

from ci_signal_noise.scorer import grade_score, top_noise_sources


class TestGradeScore(unittest.TestCase):
    """Test letter grade assignment from signal percentages."""

    def test_grade_a(self):
        grade, label = grade_score(85.0)
        self.assertEqual(grade, "A")
        self.assertIn("Excellent", label)

    def test_grade_a_boundary(self):
        self.assertEqual(grade_score(80.0)[0], "A")

    def test_grade_b(self):
        self.assertEqual(grade_score(65.0)[0], "B")

    def test_grade_b_boundary(self):
        self.assertEqual(grade_score(60.0)[0], "B")

    def test_grade_c(self):
        self.assertEqual(grade_score(50.0)[0], "C")

    def test_grade_c_boundary(self):
        self.assertEqual(grade_score(40.0)[0], "C")

    def test_grade_d(self):
        self.assertEqual(grade_score(30.0)[0], "D")

    def test_grade_d_boundary(self):
        self.assertEqual(grade_score(20.0)[0], "D")

    def test_grade_f(self):
        grade, label = grade_score(10.0)
        self.assertEqual(grade, "F")
        self.assertIn("noise", label.lower())

    def test_grade_f_zero(self):
        self.assertEqual(grade_score(0.0)[0], "F")

    def test_grade_a_perfect(self):
        self.assertEqual(grade_score(100.0)[0], "A")


class TestTopNoiseSources(unittest.TestCase):
    """Test noise source categorization."""

    def test_empty_input(self):
        self.assertEqual(top_noise_sources([]), [])

    def test_no_noise(self):
        lines = ["Error: something broke", "FAIL test_foo"]
        self.assertEqual(top_noise_sources(lines), [])

    def test_blank_lines_detected(self):
        lines = ["", "  ", "", "hello world"]
        sources = top_noise_sources(lines)
        categories = [cat for cat, _ in sources]
        self.assertIn("blank lines", categories)

    def test_dependency_resolution(self):
        lines = [
            "Collecting flask==2.3.0",
            "Requirement already satisfied: requests>=2.0",
            "Using cached numpy-1.24.0.whl",
            "Resolving dependencies...",
        ]
        sources = top_noise_sources(lines)
        categories = [cat for cat, _ in sources]
        self.assertIn("dependency resolution", categories)

    def test_download_progress(self):
        lines = [
            "Downloading pandas-2.0.0.tar.gz (5.2 MB)",
            "Fetching package metadata...",
        ]
        sources = top_noise_sources(lines)
        categories = [cat for cat, _ in sources]
        self.assertIn("download progress", categories)

    def test_limit_respected(self):
        lines = [
            "",  # blank
            "========",  # separator
            "Collecting foo",  # dependency
            "Downloading bar 1 MB",  # download
            "Run npm install",  # setup
            "real\t0m12s",  # timing
            "npm warn deprecated",  # package manager
        ]
        sources = top_noise_sources(lines, limit=3)
        self.assertLessEqual(len(sources), 3)

    def test_counts_are_correct(self):
        lines = ["", "", "", "Collecting foo", "Collecting bar"]
        sources = top_noise_sources(lines)
        source_dict = dict(sources)
        self.assertEqual(source_dict["blank lines"], 3)
        self.assertEqual(source_dict["dependency resolution"], 2)

    def test_sorted_by_count(self):
        lines = ["", "", "", "Collecting foo"]
        sources = top_noise_sources(lines)
        self.assertEqual(sources[0][0], "blank lines")
        self.assertEqual(sources[0][1], 3)

    def test_signal_lines_excluded(self):
        # "Error downloading package 5 MB" matches signal (error) so should not appear as noise
        lines = ["Error downloading package 5 MB"]
        sources = top_noise_sources(lines)
        self.assertEqual(sources, [])


class TestFormatReportWithGrade(unittest.TestCase):
    """Test that format_report includes grade and noise recommendations."""

    def test_report_includes_grade(self):
        from ci_signal_noise.report import format_report

        run_info = {"databaseId": 1, "displayTitle": "test", "conclusion": "failure"}
        job_scores = {"build": {"signal": 5, "noise": 15, "neutral": 0, "total": 20, "signal_pct": 25.0}}
        overall = {"signal": 5, "noise": 15, "neutral": 0, "total": 20, "signal_pct": 25.0}
        report = format_report(run_info, job_scores, overall)
        self.assertIn("Grade: D", report)

    def test_report_includes_noise_sources(self):
        from ci_signal_noise.report import format_report

        run_info = {"databaseId": 1, "displayTitle": "test", "conclusion": "failure"}
        job_scores = {"build": {"signal": 1, "noise": 3, "neutral": 0, "total": 4, "signal_pct": 25.0}}
        overall = {"signal": 1, "noise": 3, "neutral": 0, "total": 4, "signal_pct": 25.0}
        log_lines = ["", "", "Collecting foo", "Error: bad thing"]
        report = format_report(run_info, job_scores, overall, log_lines=log_lines)
        self.assertIn("Top noise sources", report)
        self.assertIn("blank lines", report)


class TestMultiRunSummaryWithGrade(unittest.TestCase):
    """Test that multi-run summary includes grades."""

    def test_summary_includes_grade(self):
        from ci_signal_noise.report import format_multi_run_summary

        run_reports = [
            ({"databaseId": 1, "displayTitle": "run 1", "conclusion": "success"},
             {"signal_pct": 85.0}),
            ({"databaseId": 2, "displayTitle": "run 2", "conclusion": "failure"},
             {"signal_pct": 15.0}),
        ]
        summary = format_multi_run_summary(run_reports)
        self.assertIn("Grade", summary)
        self.assertIn("A", summary)
        self.assertIn("F", summary)


class TestJsonOutput(unittest.TestCase):
    """Test --json flag produces valid JSON with grade and noise sources."""

    @patch("ci_signal_noise.__main__.list_runs")
    @patch("ci_signal_noise.__main__.download_run_logs")
    def test_json_output_structure(self, mock_logs, mock_runs):
        mock_runs.return_value = [
            {"databaseId": 42, "displayTitle": "test PR", "conclusion": "failure", "workflowName": "CI"}
        ]
        mock_logs.return_value = {
            "build": [
                "Error: module not found",
                "",
                "",
                "Collecting requests",
                "npm warn deprecated glob@7",
            ]
        }

        import io
        from ci_signal_noise.__main__ import main

        with patch("sys.argv", ["ci-signal-noise", "owner/repo", "--json", "--runs", "1"]):
            captured = io.StringIO()
            with patch("sys.stdout", captured):
                main()

        output = json.loads(captured.getvalue())
        self.assertIn("runs", output)
        run = output["runs"][0]
        self.assertEqual(run["run_id"], 42)
        self.assertIn("grade", run)
        self.assertIn("grade_label", run)
        self.assertIn("top_noise_sources", run)
        self.assertIn("overall", run)
        self.assertIn("jobs", run)
        self.assertIsInstance(run["top_noise_sources"], list)
        if run["top_noise_sources"]:
            self.assertIn("category", run["top_noise_sources"][0])
            self.assertIn("count", run["top_noise_sources"][0])


if __name__ == "__main__":
    unittest.main()
