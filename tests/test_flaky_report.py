"""Unit tests for flaky report formatting."""

from ci_signal_noise.flaky import FlakeReport
from ci_signal_noise.flaky_report import format_flaky_report


class TestFormatFlakyReport:
    """Tests for format_flaky_report()."""

    def _make_report(self, name="test_foo", pass_count=3, fail_count=2,
                     total_runs=5, flake_rate=0.4):
        return FlakeReport(
            test_name=name,
            pass_count=pass_count,
            fail_count=fail_count,
            total_runs=total_runs,
            flake_rate=flake_rate,
            first_seen=0,
            last_seen=total_runs - 1,
        )

    def test_empty_reports(self):
        output = format_flaky_report([], total_runs=5)
        assert "No flaky tests detected" in output
        assert "5 runs analyzed" in output

    def test_single_high_flake(self):
        reports = [self._make_report(flake_rate=0.5)]
        output = format_flaky_report(reports, total_runs=5)
        assert "1 flaky test" in output
        assert "test_foo" in output
        assert "Investigate" in output

    def test_boundary_at_30_percent(self):
        # Exactly 0.3 should trigger "Investigate"
        reports = [self._make_report(flake_rate=0.3)]
        output = format_flaky_report(reports, total_runs=5)
        assert "Investigate" in output

    def test_below_30_percent_no_investigate(self):
        reports = [self._make_report(flake_rate=0.29)]
        output = format_flaky_report(reports, total_runs=5)
        assert "no urgent action" in output
        assert "Investigate" not in output

    def test_long_name_truncated_in_table(self):
        long_name = "test_" + "x" * 100
        reports = [self._make_report(name=long_name, flake_rate=0.5)]
        output = format_flaky_report(reports, total_runs=3)
        # Name width capped at 60; table row uses name[:60]
        truncated = long_name[:60]
        assert truncated in output
        # The table row should not contain the full 105-char name on one line
        table_lines = [l for l in output.splitlines() if "Flake%" not in l and "---" not in l]
        data_lines = [l for l in table_lines if long_name[:60] in l and "Investigate" not in l]
        for line in data_lines:
            assert long_name not in line

    def test_multiple_reports(self):
        reports = [
            self._make_report(name="test_a", flake_rate=0.6),
            self._make_report(name="test_b", flake_rate=0.4),
        ]
        output = format_flaky_report(reports, total_runs=5)
        assert "2 flaky test" in output
        assert "test_a" in output
        assert "test_b" in output

    def test_suggested_actions_limited_to_5(self):
        reports = [
            self._make_report(name=f"test_{i}", flake_rate=0.5)
            for i in range(8)
        ]
        output = format_flaky_report(reports, total_runs=10)
        assert output.count("Investigate") == 5

    def test_flake_percentage_display(self):
        reports = [self._make_report(flake_rate=0.75)]
        output = format_flaky_report(reports, total_runs=4)
        assert "75%" in output
