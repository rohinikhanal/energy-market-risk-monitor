import unittest

import pandas as pd

from src.risk_metrics import (
    expected_shortfall,
    historical_var,
    risk_summary,
    rolling_var_backtest,
    var_breaches,
)


class RiskMetricsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pnl = pd.Series([-100.0, -50.0, 0.0, 25.0, 75.0])

    def test_historical_var_is_positive_loss(self) -> None:
        self.assertAlmostEqual(historical_var(self.pnl, 0.80), 60.0)

    def test_expected_shortfall_is_at_least_var(self) -> None:
        var_value = historical_var(self.pnl, 0.80)
        self.assertGreaterEqual(expected_shortfall(self.pnl, 0.80), var_value)

    def test_var_breach_marks_large_loss(self) -> None:
        result = var_breaches(self.pnl, 60.0)
        self.assertEqual(int(result["breach"].sum()), 1)

    def test_invalid_confidence_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            historical_var(self.pnl, 1.0)

    def test_rolling_backtest_uses_only_previous_observations(self) -> None:
        dated_pnl = pd.Series(
            [-10.0, -20.0, -30.0, -40.0, -100.0],
            index=pd.date_range("2026-01-01", periods=5, freq="D"),
        )

        result = rolling_var_backtest(dated_pnl, confidence=0.80, lookback=3)

        self.assertEqual(len(result), 2)
        self.assertEqual(result.index[0], dated_pnl.index[3])
        self.assertAlmostEqual(
            float(result.iloc[0]["var_eur"]), historical_var(dated_pnl.iloc[:3], 0.80)
        )
        self.assertTrue(bool(result.iloc[0]["breach"]))

    def test_rolling_backtest_returns_no_test_rows_without_history(self) -> None:
        result = rolling_var_backtest(self.pnl, confidence=0.95, lookback=5)
        self.assertTrue(result.empty)

    def test_risk_summary_counts_only_out_of_sample_breaches(self) -> None:
        dated_pnl = pd.Series(
            [-10.0, -20.0, -30.0, -40.0, -100.0],
            index=pd.date_range("2026-01-01", periods=5, freq="D"),
        )
        backtest = rolling_var_backtest(dated_pnl, confidence=0.80, lookback=3)

        summary = risk_summary(dated_pnl, confidence=0.80, lookback=3)

        self.assertEqual(summary["backtest_observations"], 2.0)
        self.assertEqual(summary["breach_count"], float(backtest["breach"].sum()))

    def test_invalid_lookback_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            rolling_var_backtest(self.pnl, lookback=1)


if __name__ == "__main__":
    unittest.main()
