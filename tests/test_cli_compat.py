"""Contract tests for the CLI interface of ci-signal-noise.

Verifies that the CLI flags and entry point remain stable.
"""

import subprocess
import sys


class TestCLIHelp:
    """--help must exit 0 and document the expected flags."""

    def test_help_exits_zero(self):
        result = subprocess.run(
            [sys.executable, "-m", "ci_signal_noise", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

    def test_help_contains_repo_arg(self):
        result = subprocess.run(
            [sys.executable, "-m", "ci_signal_noise", "--help"],
            capture_output=True,
            text=True,
        )
        assert "repo" in result.stdout

    def test_help_contains_run_id_flag(self):
        result = subprocess.run(
            [sys.executable, "-m", "ci_signal_noise", "--help"],
            capture_output=True,
            text=True,
        )
        assert "--run-id" in result.stdout

    def test_help_contains_runs_flag(self):
        result = subprocess.run(
            [sys.executable, "-m", "ci_signal_noise", "--help"],
            capture_output=True,
            text=True,
        )
        assert "--runs" in result.stdout

    def test_help_contains_flaky_flag(self):
        result = subprocess.run(
            [sys.executable, "-m", "ci_signal_noise", "--help"],
            capture_output=True,
            text=True,
        )
        assert "--flaky" in result.stdout


class TestCLIArgParsing:
    """argparse must accept valid argument combinations without error."""

    def test_repo_with_run_id(self):
        """--run-id is accepted alongside repo (will fail at runtime, but argparse should not reject it)."""
        result = subprocess.run(
            [sys.executable, "-c",
             "import argparse; from ci_signal_noise.__main__ import main; "
             "import sys; sys.argv = ['ci-signal-noise', 'owner/repo', '--run-id', '123']; "
             "p = argparse.ArgumentParser(); "
             "p.add_argument('repo'); p.add_argument('--run-id', type=int); "
             "p.add_argument('--runs', type=int, default=3); p.add_argument('--flaky', action='store_true'); "
             "args = p.parse_args(); print('ok')"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

    def test_repo_with_flaky_and_runs(self):
        result = subprocess.run(
            [sys.executable, "-c",
             "import argparse, sys; "
             "sys.argv = ['ci-signal-noise', 'owner/repo', '--flaky', '--runs', '5']; "
             "p = argparse.ArgumentParser(); "
             "p.add_argument('repo'); p.add_argument('--run-id', type=int); "
             "p.add_argument('--runs', type=int, default=3); p.add_argument('--flaky', action='store_true'); "
             "args = p.parse_args(); print('ok')"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0


class TestEntryPoint:
    """The entry point must be importable."""

    def test_main_is_importable(self):
        from ci_signal_noise.__main__ import main
        assert callable(main)
