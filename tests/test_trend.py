"""Tests for trend analysis across multiple CI runs."""

import unittest

from ci_signal_noise.scorer import trend_score
from ci_signal_noise.report import format_trend_summary, format_multi_run_summary


class TestTrendScore(unittest.TestCase):

    def test_improving_trend(self):
        result = trend_score([30.0, 45.0, 60.0])
        self.assertEqual(result["direction"], "improving")
        self.assertEqual(result["arrow"], "\u2191")
        self.assertAlmostEqual(result["delta"], 30.0)
        self.assertEqual(result["per_run_deltas"], [15.0, 15.0])

    def test_degrading_trend(self):
        result = trend_score([80.0, 60.0, 40.0])
        self.assertEqual(result["direction"], "degrading")
        self.assertEqual(result["arrow"], "\u2193")
        self.assertAlmostEqual(result["delta"], -40.0)
        self.assertEqual(result["per_run_deltas"], [-20.0, -20.0])

    def test_stable_trend(self):
        result = trend_score([50.0, 50.5, 50.2])
        self.assertEqual(result["direction"], "stable")
        self.assertEqual(result["arrow"], "\u2192")
        self.assertAlmostEqual(result["delta"], 0.2)

    def test_single_run_no_trend(self):
        result = trend_score([75.0])
        self.assertEqual(result["direction"], "stable")
        self.assertEqual(result["arrow"], "\u2192")
        self.assertAlmostEqual(result["delta"], 0.0)
        self.assertEqual(result["per_run_deltas"], [])

    def test_empty_list(self):
        result = trend_score([])
        self.assertEqual(result["direction"], "stable")
        self.assertEqual(result["delta"], 0.0)
        self.assertEqual(result["per_run_deltas"], [])

    def test_two_runs_equal(self):
        result = trend_score([42.0, 42.0])
        self.assertEqual(result["direction"], "stable")
        self.assertAlmostEqual(result["delta"], 0.0)

    def test_boundary_just_below_threshold(self):
        # delta of 0.9 should be stable (< 1.0)
        result = trend_score([50.0, 50.9])
        self.assertEqual(result["direction"], "stable")

    def test_boundary_at_threshold(self):
        # delta of exactly 1.0 should be improving
        result = trend_score([50.0, 51.0])
        self.assertEqual(result["direction"], "improving")

    def test_per_run_deltas_mixed(self):
        result = trend_score([30.0, 50.0, 40.0, 60.0])
        self.assertEqual(result["per_run_deltas"], [20.0, -10.0, 20.0])
        self.assertEqual(result["direction"], "improving")
        self.assertAlmostEqual(result["delta"], 30.0)


class TestFormatTrendSummary(unittest.TestCase):

    def test_improving(self):
        trend = {"direction": "improving", "arrow": "\u2191", "delta": 15.0, "per_run_deltas": [15.0]}
        result = format_trend_summary(trend)
        self.assertIn("\u2191", result)
        self.assertIn("improving", result)
        self.assertIn("+15.0%", result)

    def test_degrading(self):
        trend = {"direction": "degrading", "arrow": "\u2193", "delta": -10.0, "per_run_deltas": [-10.0]}
        result = format_trend_summary(trend)
        self.assertIn("\u2193", result)
        self.assertIn("degrading", result)
        self.assertIn("-10.0%", result)

    def test_stable(self):
        trend = {"direction": "stable", "arrow": "\u2192", "delta": 0.0, "per_run_deltas": []}
        result = format_trend_summary(trend)
        self.assertIn("\u2192", result)
        self.assertIn("stable", result)


class TestMultiRunSummaryWithTrend(unittest.TestCase):

    def _make_run(self, run_id, pct, conclusion="success"):
        run_info = {"databaseId": run_id, "displayTitle": f"Run {run_id}", "conclusion": conclusion}
        overall = {"signal_pct": pct, "signal": 10, "noise": 5, "neutral": 3, "total": 18}
        return (run_info, overall)

    def test_includes_trend_line(self):
        runs = [self._make_run(1, 30.0), self._make_run(2, 50.0)]
        trend = {"direction": "improving", "arrow": "\u2191", "delta": 20.0, "per_run_deltas": [20.0]}
        result = format_multi_run_summary(runs, trend=trend)
        self.assertIn("Trend:", result)
        self.assertIn("\u2191", result)
        self.assertIn("improving", result)

    def test_includes_per_run_deltas(self):
        runs = [self._make_run(1, 30.0), self._make_run(2, 50.0), self._make_run(3, 45.0)]
        trend = {"direction": "improving", "arrow": "\u2191", "delta": 15.0, "per_run_deltas": [20.0, -5.0]}
        result = format_multi_run_summary(runs, trend=trend)
        self.assertIn("+20.0%", result)
        self.assertIn("-5.0%", result)

    def test_no_trend_when_none(self):
        runs = [self._make_run(1, 30.0), self._make_run(2, 50.0)]
        result = format_multi_run_summary(runs)
        self.assertNotIn("Trend:", result)

    def test_empty_runs(self):
        result = format_multi_run_summary([])
        self.assertEqual(result, "No runs to report.")


if __name__ == "__main__":
    unittest.main()
