import unittest

import pandas as pd

from src.data_quality import quality_score, run_data_quality_checks


class DataQualityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.market = pd.DataFrame(
            {
                "timestamp": pd.to_datetime(
                    ["2026-01-01 00:00", "2026-01-01 00:15", "2026-01-01 00:30"],
                    utc=True,
                ),
                "market_price_eur_mwh": [50.0, 55.0, 52.0],
            }
        )
        self.portfolio = pd.DataFrame(
            {
                "position_id": ["P1"],
                "delivery_time": pd.to_datetime(["2026-01-01 00:15"], utc=True),
                "direction": ["BUY"],
                "volume_mwh": [10.0],
                "trade_price_eur_mwh": [51.0],
            }
        )

    def test_clean_data_passes_core_checks(self) -> None:
        results = run_data_quality_checks(self.market, self.portfolio)
        self.assertEqual(int(results["status"].eq("FAIL").sum()), 0)
        self.assertEqual(quality_score(results), 100.0)

    def test_missing_interval_is_detected(self) -> None:
        broken_market = self.market.drop(index=1)
        results = run_data_quality_checks(broken_market, self.portfolio)
        row = results[results["check"].str.startswith("Complete")].iloc[0]
        self.assertEqual(row["status"], "FAIL")
        self.assertEqual(int(row["failed_records"]), 1)

    def test_duplicate_timestamp_is_detected(self) -> None:
        duplicated = pd.concat([self.market, self.market.iloc[[0]]], ignore_index=True)
        results = run_data_quality_checks(duplicated, self.portfolio)
        row = results[results["check"].eq("Unique timestamps")].iloc[0]
        self.assertEqual(row["status"], "FAIL")

    def test_invalid_direction_is_detected(self) -> None:
        broken_portfolio = self.portfolio.copy()
        broken_portfolio.loc[0, "direction"] = "HOLD"
        results = run_data_quality_checks(self.market, broken_portfolio)
        row = results[results["check"].eq("Valid trade direction")].iloc[0]
        self.assertEqual(row["status"], "FAIL")

    def test_unmatched_position_is_detected(self) -> None:
        broken_portfolio = self.portfolio.copy()
        broken_portfolio.loc[0, "delivery_time"] = pd.Timestamp("2030-01-01", tz="UTC")
        results = run_data_quality_checks(self.market, broken_portfolio)
        row = results[results["category"].eq("Reconciliation")].iloc[0]
        self.assertEqual(row["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()

