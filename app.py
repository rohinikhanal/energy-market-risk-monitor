"""Streamlit interface for the Energy Market Risk Monitor."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from src.config import DEFAULT_MARKET_PATH, DEFAULT_PORTFOLIO_PATH
from src.data_loader import (
    prepare_market_data,
    prepare_portfolio_data,
    read_market_data,
    read_portfolio_data,
)
from src.data_quality import (
    overall_quality_status,
    quality_score,
    run_data_quality_checks,
)
from src.demo_data import inject_quality_issues, write_demo_data
from src.portfolio import calculate_daily_pnl, portfolio_summary, value_positions
from src.reporting import build_markdown_report
from src.risk_metrics import risk_summary, rolling_var_backtest
from src.stress_testing import run_price_stress_tests


VAR_LOOKBACK_DAYS = 90


st.set_page_config(
    page_title="Energy Market Risk Monitor",
    page_icon="⚡",
    layout="wide",
)

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.6rem; padding-bottom: 2rem;}
    [data-testid="stMetric"] {
        background: white;
        border: 1px solid #dbe4f0;
        border-radius: 10px;
        padding: 14px;
        box-shadow: 0 2px 8px rgba(24, 48, 80, 0.05);
    }
    .small-note {color: #5f6f82; font-size: 0.9rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_default_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    write_demo_data()
    return read_market_data(DEFAULT_MARKET_PATH), read_portfolio_data(DEFAULT_PORTFOLIO_PATH)


def money(value: float) -> str:
    if pd.isna(value):
        return "N/A"
    return f"-€{abs(value):,.0f}" if value < 0 else f"€{value:,.0f}"


def status_icon(status: str) -> str:
    return {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}.get(status, "ℹ️")


st.title("⚡ Energy Market Risk Monitor")
st.caption(
    "Auditable portfolio valuation, historical risk measurement, stress testing, "
    "and data-quality monitoring for quarter-hourly electricity-market data."
)

with st.sidebar:
    st.header("Analysis settings")
    data_mode = st.radio("Data source", ["Bundled demonstration", "Upload CSV files"])
    confidence = st.select_slider(
        "Risk confidence level", options=[0.90, 0.95, 0.975, 0.99], value=0.95
    )
    shock = st.slider("Proportional stress", 0.10, 0.60, 0.30, 0.05)
    inject_issues = st.toggle(
        "Inject controlled data errors",
        value=False,
        help="Introduces a missing interval, duplicate, null price, invalid volume, "
        "invalid direction and unmatched position to demonstrate the controls.",
    )

    if data_mode == "Upload CSV files":
        market_upload = st.file_uploader("Market-price CSV", type="csv")
        portfolio_upload = st.file_uploader("Portfolio CSV", type="csv")
    else:
        market_upload = portfolio_upload = None

    st.divider()
    st.caption("Educational project — not a live trading or investment system.")

try:
    if data_mode == "Upload CSV files":
        if market_upload is None or portfolio_upload is None:
            st.info("Upload both CSV files to start the analysis. Sample schemas are in the README.")
            st.stop()
        raw_market = read_market_data(market_upload)
        raw_portfolio = read_portfolio_data(portfolio_upload)
    else:
        raw_market, raw_portfolio = load_default_data()

    if inject_issues:
        raw_market, raw_portfolio = inject_quality_issues(raw_market, raw_portfolio)

    quality_results = run_data_quality_checks(raw_market, raw_portfolio)
    score = quality_score(quality_results)
    overall_status = overall_quality_status(quality_results)

    market = prepare_market_data(raw_market)
    portfolio = prepare_portfolio_data(raw_portfolio)
    valued = value_positions(portfolio, market)
    daily_pnl = calculate_daily_pnl(valued)
    portfolio_metrics = portfolio_summary(valued)
    risk_metrics = risk_summary(daily_pnl, confidence, VAR_LOOKBACK_DAYS)
    breach_data = rolling_var_backtest(daily_pnl, confidence, VAR_LOOKBACK_DAYS)
    stress_results = run_price_stress_tests(valued, shock)
except (ValueError, KeyError, pd.errors.ParserError) as error:
    st.error(f"The analysis could not run: {error}")
    st.stop()


overview_tab, portfolio_tab, risk_tab, quality_tab, methodology_tab = st.tabs(
    ["Executive overview", "Portfolio & P&L", "Risk & stress", "Data quality", "Methodology"]
)

with overview_tab:
    metric_columns = st.columns(4)
    metric_columns[0].metric("Portfolio P&L", money(portfolio_metrics["portfolio_pnl_eur"]))
    metric_columns[1].metric("Gross exposure", money(portfolio_metrics["gross_exposure_eur"]))
    metric_columns[2].metric(
        f"1-day Historical VaR ({confidence:.1%})",
        money(risk_metrics["historical_var_eur"]),
        help=f"Next-day loss estimate using the latest {VAR_LOOKBACK_DAYS} daily P&L observations.",
    )
    metric_columns[3].metric(
        "1-day Expected Shortfall",
        money(risk_metrics["expected_shortfall_eur"]),
        help=f"Average tail loss from the same {VAR_LOOKBACK_DAYS}-day estimation window.",
    )
    st.caption(
        f"VaR and Expected Shortfall are next-day estimates from a {VAR_LOOKBACK_DAYS}-day "
        "rolling window. Stress loss covers every loaded position across the full delivery "
        "horizon, so it is not directly comparable with one-day VaR."
    )

    left, right = st.columns([1.6, 1])
    with left:
        st.subheader("Daily portfolio P&L")
        st.line_chart(daily_pnl, color="#2F80ED", height=330)
    with right:
        st.subheader("Management attention")
        st.metric(
            "Data quality score",
            f"{status_icon(overall_status)} {score:.0f}/100",
            help="PASS=1, WARN=0.5 and FAIL=0, averaged across all controls.",
        )
        failed = quality_results[quality_results["status"].eq("FAIL")]
        if failed.empty:
            st.success("No failed data controls.")
        else:
            for row in failed.head(5).itertuples():
                st.error(f"{row.check}: {row.details}")
        if not stress_results.empty:
            worst = stress_results.sort_values("change_vs_base_eur").iloc[0]
            st.warning(
                f"Most adverse full-horizon stress: **{worst['scenario']}**  \n"
                f"Change versus base: **{money(worst['change_vs_base_eur'])}**"
            )

    report = build_markdown_report(
        portfolio_metrics,
        risk_metrics,
        quality_results,
        score,
        overall_status,
        stress_results,
        confidence,
    )
    st.download_button(
        "Download management risk report",
        data=report,
        file_name="energy_market_risk_report.md",
        mime="text/markdown",
    )

with portfolio_tab:
    st.subheader("Portfolio composition and valuation")
    summary_columns = st.columns(4)
    summary_columns[0].metric("Positions", f"{int(portfolio_metrics['position_count']):,}")
    summary_columns[1].metric("Matched prices", f"{portfolio_metrics['price_coverage_pct']:.1f}%")
    summary_columns[2].metric("Net volume", f"{portfolio_metrics['net_volume_mwh']:,.1f} MWh")
    summary_columns[3].metric("Mean daily P&L", money(risk_metrics["mean_pnl_eur"]))

    left, right = st.columns(2)
    with left:
        st.markdown("#### Quarter-hourly market price")
        price_chart = market.set_index("timestamp")["market_price_eur_mwh"]
        st.line_chart(price_chart, color="#18A999", height=300)
    with right:
        st.markdown("#### P&L by trade direction")
        direction_pnl = valued.groupby("direction")["pnl_eur"].sum().to_frame()
        st.bar_chart(direction_pnl, color="#2F80ED", height=300)

    display_columns = [
        "position_id",
        "delivery_time",
        "direction",
        "volume_mwh",
        "trade_price_eur_mwh",
        "market_price_eur_mwh",
        "pnl_eur",
    ]
    st.dataframe(
        valued[display_columns].sort_values("delivery_time", ascending=False),
        width="stretch",
        hide_index=True,
        column_config={
            "trade_price_eur_mwh": st.column_config.NumberColumn(format="€ %.2f"),
            "market_price_eur_mwh": st.column_config.NumberColumn(format="€ %.2f"),
            "pnl_eur": st.column_config.NumberColumn(format="€ %.2f"),
        },
    )

with risk_tab:
    st.subheader("Rolling out-of-sample 1-day VaR backtest")
    st.caption(
        f"Each test day's VaR is estimated from only the previous {VAR_LOOKBACK_DAYS} "
        "daily P&L observations. The realized test-day P&L is then classified as a "
        "breach or non-breach before the window moves forward."
    )
    risk_columns = st.columns(4)
    risk_columns[0].metric(
        "Out-of-sample test days", f"{int(risk_metrics['backtest_observations'])}"
    )
    risk_columns[1].metric("VaR breaches", f"{int(risk_metrics['breach_count'])}")
    risk_columns[2].metric(
        "Observed breach rate",
        f"{risk_metrics['breach_rate_pct']:.2f}%"
        if pd.notna(risk_metrics["breach_rate_pct"])
        else "N/A",
    )
    risk_columns[3].metric(
        "Expected breach rate", f"{risk_metrics['expected_breach_rate_pct']:.2f}%"
    )
    if pd.notna(risk_metrics["breach_rate_pct"]):
        if risk_metrics["breach_rate_pct"] > risk_metrics["expected_breach_rate_pct"]:
            st.warning(
                "The observed breach rate is above the confidence-level expectation. "
                "This is a model-monitoring signal, not by itself a formal rejection; "
                "coverage and independence tests are listed as the next extension."
            )
        else:
            st.success(
                "The observed breach rate is at or below the confidence-level expectation."
            )

    left, right = st.columns(2)
    with left:
        st.markdown("#### Realized P&L versus forecast VaR limit")
        if breach_data.empty:
            st.info(
                f"At least {VAR_LOOKBACK_DAYS + 1} daily P&L observations are required "
                "for an out-of-sample backtest."
            )
        else:
            st.line_chart(breach_data[["pnl_eur", "var_limit_eur"]], height=320)
    with right:
        st.markdown("#### Full daily P&L distribution")
        if not daily_pnl.empty:
            counts, edges = np.histogram(daily_pnl, bins=25)
            histogram = pd.DataFrame(
                {"observations": counts},
                index=pd.Index(np.round((edges[:-1] + edges[1:]) / 2, 0), name="P&L bin"),
            )
            st.bar_chart(histogram, color="#7B61FF", height=320)

    st.markdown("#### Deterministic stress tests — full portfolio delivery horizon")
    st.caption(
        "Each scenario simultaneously revalues all loaded delivery positions. These losses "
        "represent the full portfolio delivery horizon, not a one-day risk forecast."
    )
    stress_display = stress_results.copy()
    st.dataframe(
        stress_display,
        width="stretch",
        hide_index=True,
        column_config={
            "portfolio_pnl_eur": st.column_config.NumberColumn(format="€ %.2f"),
            "change_vs_base_eur": st.column_config.NumberColumn(format="€ %.2f"),
        },
    )

with quality_tab:
    st.subheader("Control results and reconciliation")
    quality_columns = st.columns(4)
    quality_columns[0].metric("Overall status", f"{status_icon(overall_status)} {overall_status}")
    quality_columns[1].metric("Quality score", f"{score:.1f}/100")
    quality_columns[2].metric(
        "Failed controls", int(quality_results["status"].eq("FAIL").sum())
    )
    quality_columns[3].metric(
        "Warnings", int(quality_results["status"].eq("WARN").sum())
    )

    status_filter = st.multiselect(
        "Filter status", ["PASS", "WARN", "FAIL"], default=["PASS", "WARN", "FAIL"]
    )
    filtered_quality = quality_results[quality_results["status"].isin(status_filter)].copy()
    filtered_quality["status"] = filtered_quality["status"].map(
        lambda value: f"{status_icon(value)} {value}"
    )
    st.dataframe(filtered_quality, width="stretch", hide_index=True)

    st.info(
        "Turn on **Inject controlled data errors** in the sidebar to demonstrate "
        "how missing intervals, duplicates, invalid positions and reconciliation breaks are detected."
    )

with methodology_tab:
    st.subheader("Methodology, assumptions and model limitations")
    st.markdown(
        f"""
        **Portfolio valuation**

        - BUY positions use positive signed volume and SELL positions use negative signed volume.
        - Position P&L = signed volume × (market price − trade price).
        - Positions are matched to market prices using the exact UTC delivery timestamp.

        **Risk metrics**

        - Historical VaR at {confidence:.1%} is a **one-day forecast** estimated from the immediately preceding {VAR_LOOKBACK_DAYS} daily P&L observations.
        - Expected Shortfall uses the same trailing window and is the average loss at or beyond VaR.
        - The backtest is rolling and out of sample: estimate from days t-{VAR_LOOKBACK_DAYS} to t-1, observe day t, record breach/no breach, then advance one day.
        - A breach occurs when realized daily P&L is lower than that day's negative VaR forecast.

        **Stress-test horizon**

        - Deterministic scenarios revalue every loaded position across the **full portfolio delivery horizon**.
        - Full-horizon stress loss and one-day VaR answer different questions and must not be compared as equivalent exposure measures.

        **Data-quality score**

        - PASS contributes 1, WARN contributes 0.5 and FAIL contributes 0.
        - The displayed score is the average across all controls multiplied by 100.

        **Limitations**

        - The bundled prices and positions are synthetic, not live market data.
        - Historical simulation assumes the observed P&L distribution is informative about risk.
        - A {VAR_LOOKBACK_DAYS}-day window gives limited tail observations at high confidence levels.
        - Stress scenarios are deterministic and do not assign probabilities.
        - The project does not include liquidity risk, transaction costs, collateral or settlement.
        - Results must not be used for trading, investment or regulatory reporting.
        """
    )
