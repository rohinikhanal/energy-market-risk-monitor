import unittest

import pandas as pd

from src.risk_metrics import expected_shortfall, historical_var, var_breaches


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


if __name__ == "__main__":
    unittest.main()

