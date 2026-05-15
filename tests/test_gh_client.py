"""Unit tests for gh_client module with subprocess mocking."""

import json
import subprocess
import unittest
from unittest.mock import patch, MagicMock

from ci_signal_noise.gh_client import _run_gh, list_runs, download_run_logs


class TestRunGh(unittest.TestCase):
    """Tests for _run_gh()."""

    @patch("ci_signal_noise.gh_client.subprocess.run")
    def test_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="output\n", stderr="")
        result = _run_gh("run", "list")
        assert result == "output\n"
        mock_run.assert_called_once_with(
            ["gh", "run", "list"],
            capture_output=True,
            text=True,
            timeout=120,
        )

    @patch("ci_signal_noise.gh_client.subprocess.run")
    def test_failure_raises(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="not found")
        with self.assertRaises(RuntimeError) as ctx:
            _run_gh("run", "view", "999")
        assert "not found" in str(ctx.exception)

    @patch("ci_signal_noise.gh_client.subprocess.run")
    def test_timeout_propagates(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="gh", timeout=120)
        with self.assertRaises(subprocess.TimeoutExpired):
            _run_gh("run", "view", "123", timeout=120)

    @patch("ci_signal_noise.gh_client.subprocess.run")
    def test_custom_timeout(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        _run_gh("api", "/repos", timeout=60)
        mock_run.assert_called_once_with(
            ["gh", "api", "/repos"],
            capture_output=True,
            text=True,
            timeout=60,
        )


class TestListRuns(unittest.TestCase):
    """Tests for list_runs()."""

    @patch("ci_signal_noise.gh_client._run_gh")
    def test_returns_parsed_json(self, mock_gh):
        runs = [{"databaseId": 1, "conclusion": "success"}]
        mock_gh.return_value = json.dumps(runs)
        result = list_runs("owner/repo", limit=3)
        assert result == runs
        mock_gh.assert_called_once()
        args = mock_gh.call_args[0]
        assert "--limit" in args
        assert "3" in args
        assert "owner/repo" in args

    @patch("ci_signal_noise.gh_client._run_gh")
    def test_default_limit(self, mock_gh):
        mock_gh.return_value = "[]"
        list_runs("owner/repo")
        args = mock_gh.call_args[0]
        assert "5" in args

    @patch("ci_signal_noise.gh_client._run_gh")
    def test_propagates_error(self, mock_gh):
        mock_gh.side_effect = RuntimeError("gh failed")
        with self.assertRaises(RuntimeError):
            list_runs("owner/repo")


class TestDownloadRunLogs(unittest.TestCase):
    """Tests for download_run_logs()."""

    @patch("ci_signal_noise.gh_client._run_gh")
    def test_parses_tab_format(self, mock_gh):
        mock_gh.return_value = (
            "build\tSetup\tInstalling deps\n"
            "build\tSetup\tDone\n"
            "test\tRun\tFAILED test_foo\n"
        )
        result = download_run_logs("owner/repo", 123)
        assert "build" in result
        assert "test" in result
        assert result["build"] == ["Installing deps", "Done"]
        assert result["test"] == ["FAILED test_foo"]

    @patch("ci_signal_noise.gh_client._run_gh")
    def test_unmatched_lines_go_to_unknown(self, mock_gh):
        mock_gh.return_value = "no tabs here\nanother bare line\n"
        result = download_run_logs("owner/repo", 456)
        assert "unknown" in result
        assert len(result["unknown"]) == 2

    @patch("ci_signal_noise.gh_client._run_gh")
    def test_empty_log(self, mock_gh):
        mock_gh.return_value = ""
        result = download_run_logs("owner/repo", 789)
        assert result == {}

    @patch("ci_signal_noise.gh_client._run_gh")
    def test_mixed_matched_and_unmatched(self, mock_gh):
        mock_gh.return_value = (
            "job1\tstep1\tline1\n"
            "bare line\n"
            "job1\tstep2\tline2\n"
        )
        result = download_run_logs("owner/repo", 100)
        assert result["job1"] == ["line1", "line2"]
        assert result["unknown"] == ["bare line"]


if __name__ == "__main__":
    unittest.main()
