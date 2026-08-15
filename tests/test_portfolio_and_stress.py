import unittest

import pandas as pd

from src.portfolio import calculate_daily_pnl, value_positions
from src.stress_testing import run_price_stress_tests


class PortfolioAndStressTests(unittest.TestCase):
    def setUp(self) -> None:
        timestamps = pd.to_datetime(
            ["2026-01-01 00:00", "2026-01-01 00:15"], utc=True
        )
        self.market = pd.DataFrame(
            {"timestamp": timestamps, "market_price_eur_mwh": [60.0, 40.0]}
        )
        self.positions = pd.DataFrame(
            {
                "position_id": ["BUY-1", "SELL-1"],
                "delivery_time": timestamps,
                "direction": ["BUY", "SELL"],
                "volume_mwh": [10.0, 5.0],
                "trade_price_eur_mwh": [50.0, 50.0],
            }
        )

    def test_buy_and_sell_pnl_signs(self) -> None:
        valued = value_positions(self.positions, self.market)
        self.assertEqual(valued.loc[0, "pnl_eur"], 100.0)
        self.assertEqual(valued.loc[1, "pnl_eur"], 50.0)

    def test_daily_pnl_aggregates_positions(self) -> None:
        valued = value_positions(self.positions, self.market)
        daily = calculate_daily_pnl(valued)
        self.assertEqual(float(daily.iloc[0]), 150.0)

    def test_stress_table_contains_base_and_shocks(self) -> None:
        valued = value_positions(self.positions, self.market)
        stress = run_price_stress_tests(valued, 0.30)
        self.assertIn("Base market", set(stress["scenario"]))
        self.assertGreaterEqual(len(stress), 5)


if __name__ == "__main__":
    unittest.main()

