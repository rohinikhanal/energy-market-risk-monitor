# Energy Market Risk Monitor

An auditable Python and Streamlit application for portfolio valuation, historical
risk measurement, deterministic stress testing, and data-quality monitoring using
quarter-hourly electricity-market data.

This is a compact portfolio project designed to demonstrate the complete analytical
workflow expected in quantitative risk, commodity trading, and data-analyst roles:

`market data + positions -> controls -> valuation -> risk -> exceptions -> management report`

The bundled data is deterministic and synthetic. No confidential employer data is
included.

## What the application demonstrates

- Quarter-hourly electricity-price ingestion and UTC timestamp handling.
- A synthetic portfolio of BUY and SELL electricity positions.
- Position-level mark-to-market valuation and daily P&L aggregation.
- Historical Value at Risk and Expected Shortfall.
- VaR-breach monitoring and deterministic price-stress scenarios.
- Data-quality checks for missing intervals, duplicates, nulls, invalid positions,
  extreme prices, large price changes, and unmatched delivery periods.
- A transparent data-quality score and management exception view.
- Downloadable Markdown risk report.
- Automated tests covering risk calculations, portfolio valuation, stress testing,
  data controls, and reconciliation.

## Dashboard pages

1. **Executive overview** — key exposure, P&L, risk, data quality, and management alerts.
2. **Portfolio & P&L** — market prices, direction-level P&L, and position details.
3. **Risk & stress** — VaR, Expected Shortfall, breaches, P&L distribution, and shocks.
4. **Data quality** — control status, failure counts, warnings, and reconciliation.
5. **Methodology** — formulas, assumptions, scoring rules, and limitations.

## Quick start on Windows

For the quickest start, double-click `START_DASHBOARD.bat`. On its first run it
creates an isolated environment, installs the required packages, and opens the
dashboard. Subsequent starts reuse the environment.

Alternatively, open PowerShell in this folder and run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
streamlit run app.py
```

Streamlit normally opens the application at `http://localhost:8501`.

The bundled CSV files are already included. To regenerate them deterministically:

```powershell
python scripts\generate_demo_data.py
```

Run the automated tests with no additional testing package:

```powershell
python -m unittest discover -s tests -v
```

## Demonstrating the controls

Use the sidebar switch **Inject controlled data errors**. It adds:

- one missing quarter-hour interval;
- one duplicate timestamp;
- one null market price;
- one negative position volume;
- one invalid trade direction; and
- one position with no matching market price.

The raw errors are recorded in the control results. Invalid rows are removed only
after the controls run, allowing the rest of the dashboard to continue safely.

## Uploading your own CSV files

### Market-price schema

```csv
timestamp,market_price_eur_mwh
2026-01-01T00:00:00+00:00,76.25
2026-01-01T00:15:00+00:00,73.10
```

### Portfolio schema

```csv
position_id,delivery_time,direction,volume_mwh,trade_price_eur_mwh
POS-00001,2026-01-01T00:00:00+00:00,BUY,25.0,71.50
POS-00002,2026-01-01T00:15:00+00:00,SELL,18.0,75.20
```

`direction` must be `BUY` or `SELL`. Volumes must be positive. Timestamps are
normalized to UTC and positions are matched to exact delivery intervals.

## Methodology

### Mark-to-market P&L

BUY positions receive positive signed volume; SELL positions receive negative signed
volume.

```text
position P&L = signed volume × (market price − trade price)
```

### Historical Value at Risk

Daily position P&L is aggregated by UTC delivery date. Loss is defined as negative
P&L. Historical VaR is the selected quantile of the observed loss distribution and is
reported as a positive amount.

### Expected Shortfall

Expected Shortfall is the mean observed loss at or beyond historical VaR.

### Quality score

- PASS = 1
- WARN = 0.5
- FAIL = 0

The overall score is the average contribution across controls multiplied by 100. A
single failed control sets the overall status to FAIL, even when the numerical score
remains relatively high.

## Project structure

```text
energy-market-risk-monitor/
├── app.py
├── requirements.txt
├── README.md
├── data/
│   ├── market_prices.csv
│   └── portfolio.csv
├── scripts/
│   └── generate_demo_data.py
├── src/
│   ├── config.py
│   ├── data_loader.py
│   ├── data_quality.py
│   ├── demo_data.py
│   ├── portfolio.py
│   ├── reporting.py
│   ├── risk_metrics.py
│   └── stress_testing.py
└── tests/
    ├── test_data_quality.py
    ├── test_portfolio_and_stress.py
    └── test_risk_metrics.py
```

## Important limitations

- The bundled market prices and positions are synthetic.
- Historical simulation does not predict future losses.
- Exact timestamp matching is intentionally strict and highlights operational breaks.
- Stress scenarios do not have probabilities.
- Liquidity, transaction costs, collateral, credit, operational settlement, and model
  risk capital are outside the first version.
- This project is educational and must not be used for trading, investment decisions,
  production risk limits, or regulatory reporting.

## Extension roadmap

The MVP has deliberate extension points:

1. Replace bundled CSV prices with SMARD or ENTSO-E ingestion.
2. Add PostgreSQL and versioned SQL transformations.
3. Add historical VaR backtesting tests and asymmetric-tail models.
4. Reconcile positions from two simulated ETRM source systems.
5. Introduce exception ownership, review, sign-off, and audit history.
6. Add V2G fleet constraints and stochastic charging optimization.
7. Containerize and deploy the dashboard.
8. Add source-linked AI management summaries with human approval.

## Suggested interview explanation

> I built an end-to-end energy risk monitoring application that validates
> quarter-hourly market data, reconciles positions to prices, calculates portfolio
> P&L, VaR and Expected Shortfall, performs transparent stress testing, and turns
> failed controls into a management-ready exception view.

## License

MIT License. See `LICENSE`.
