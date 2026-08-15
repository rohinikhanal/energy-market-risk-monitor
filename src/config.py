"""Project-wide configuration values."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_MARKET_PATH = DATA_DIR / "market_prices.csv"
DEFAULT_PORTFOLIO_PATH = DATA_DIR / "portfolio.csv"

MARKET_REQUIRED_COLUMNS = {"timestamp", "market_price_eur_mwh"}
PORTFOLIO_REQUIRED_COLUMNS = {
    "position_id",
    "delivery_time",
    "direction",
    "volume_mwh",
    "trade_price_eur_mwh",
}

