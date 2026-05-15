"""Unit tests for report formatting functions."""

import unittest

from ci_signal_noise.report import format_report, format_multi_run_summary


class TestFormatReport(unittest.TestCase):
    """Tests for format_report()."""

    def _make_run_info(self, **overrides):
        info = {
            "displayTitle": "Fix auth bug",
            "databaseId": 12345,
            "conclusion": "failure",
            "workflowName": "CI",
        }
        info.update(overrides)
        return info

    def _make_scores(self, signal=5, noise=10, neutral=3, total=18, signal_pct=27.8):
        return {
            "signal": signal,
            "noise": noise,
            "neutral": neutral,
            "total": total,
            "signal_pct": signal_pct,
        }

    def test_basic_output(self):
        run_info = self._make_run_info()
        job_scores = {"build": self._make_scores()}
        overall = self._make_scores()
        result = format_report(run_info, job_scores, overall)
        assert "Run #12345: Fix auth bug" in result
        assert "Workflow: CI" in result
        assert "Conclusion: failure" in result
        assert "27.8%" in result

    def test_multiple_jobs_sorted(self):
        run_info = self._make_run_info()
        job_scores = {
            "z-lint": self._make_scores(signal_pct=10.0),
            "a-build": self._make_scores(signal_pct=90.0),
        }
        overall = self._make_scores()
        result = format_report(run_info, job_scores, overall)
        # Jobs should be sorted alphabetically
        a_pos = result.index("a-build")
        z_pos = result.index("z-lint")
        assert a_pos < z_pos

    def test_empty_job_scores(self):
        run_info = self._make_run_info()
        job_scores = {}
        overall = self._make_scores(signal=0, noise=0, neutral=0, total=0, signal_pct=0.0)
        result = format_report(run_info, job_scores, overall)
        assert "Run #12345" in result
        assert "0.0% signal" in result

    def test_zero_percent_signal(self):
        run_info = self._make_run_info()
        job_scores = {"build": self._make_scores(signal=0, signal_pct=0.0)}
        overall = self._make_scores(signal=0, signal_pct=0.0)
        result = format_report(run_info, job_scores, overall)
        assert "0.0%" in result

    def test_100_percent_signal(self):
        run_info = self._make_run_info()
        job_scores = {"build": self._make_scores(signal=10, signal_pct=100.0)}
        overall = self._make_scores(signal=10, signal_pct=100.0)
        result = format_report(run_info, job_scores, overall)
        assert "100.0%" in result

    def test_long_job_name_truncated(self):
        run_info = self._make_run_info()
        long_name = "a" * 80
        job_scores = {long_name: self._make_scores()}
        overall = self._make_scores()
        result = format_report(run_info, job_scores, overall)
        # Name should be truncated to 50 chars
        assert "a" * 50 in result
        assert "a" * 51 not in result

    def test_missing_run_info_keys(self):
        run_info = {}
        job_scores = {"test": self._make_scores()}
        overall = self._make_scores()
        result = format_report(run_info, job_scores, overall)
        assert "Run #?: unknown" in result

    def test_no_workflow_skips_workflow_line(self):
        run_info = self._make_run_info(workflowName="")
        job_scores = {"test": self._make_scores()}
        overall = self._make_scores()
        result = format_report(run_info, job_scores, overall)
        assert "Workflow:" not in result


class TestFormatMultiRunSummary(unittest.TestCase):
    """Tests for format_multi_run_summary()."""

    def test_empty_reports(self):
        result = format_multi_run_summary([])
        assert result == "No runs to report."

    def test_single_run(self):
        run_info = {"databaseId": 100, "conclusion": "success", "displayTitle": "Deploy"}
        overall = {"signal_pct": 15.5}
        result = format_multi_run_summary([(run_info, overall)])
        assert "100" in result
        assert "15.5%" in result
        assert "success" in result
        assert "Deploy" in result

    def test_multiple_runs(self):
        reports = [
            ({"databaseId": 1, "conclusion": "failure", "displayTitle": "A"}, {"signal_pct": 80.0}),
            ({"databaseId": 2, "conclusion": "success", "displayTitle": "B"}, {"signal_pct": 5.0}),
        ]
        result = format_multi_run_summary(reports)
        assert "80.0%" in result
        assert "5.0%" in result

    def test_long_title_truncated(self):
        long_title = "x" * 100
        run_info = {"databaseId": 1, "conclusion": "success", "displayTitle": long_title}
        overall = {"signal_pct": 50.0}
        result = format_multi_run_summary([(run_info, overall)])
        # Title truncated to 60 chars
        assert "x" * 60 in result
        assert "x" * 61 not in result

    def test_missing_conclusion(self):
        run_info = {"databaseId": 1, "displayTitle": "Test"}
        overall = {"signal_pct": 0.0}
        result = format_multi_run_summary([(run_info, overall)])
        assert "?" in result

    def test_none_conclusion(self):
        run_info = {"databaseId": 1, "conclusion": None, "displayTitle": "Test"}
        overall = {"signal_pct": 0.0}
        result = format_multi_run_summary([(run_info, overall)])
        assert "?" in result


if __name__ == "__main__":
    unittest.main()
