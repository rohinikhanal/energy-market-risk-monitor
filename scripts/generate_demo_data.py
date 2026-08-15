"""Generate or refresh the bundled demonstration CSV files."""

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.demo_data import write_demo_data  # noqa: E402


if __name__ == "__main__":
    market_path, portfolio_path = write_demo_data(overwrite=True)
    print(f"Created {market_path}")
    print(f"Created {portfolio_path}")

