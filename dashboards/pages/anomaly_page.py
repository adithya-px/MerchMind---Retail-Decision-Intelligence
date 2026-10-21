"""
Sales Anomaly Detection Dashboard Page.
Renders daily revenue baseline with rolling IQR bounds and anomaly flags.
Explicitly clarifies that anomalies require business context investigation and
are not proof of fraud or malfunction.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from src.anomaly_detection import detect_sales_anomalies


def render(sales_df: pd.DataFrame, customer_df: pd.DataFrame, guest_metrics: dict) -> None:
    st.title("🔍 Sales Anomaly Detection")
    st.caption("Rolling baseline outlier detection for daily positive sales volume.")

    if sales_df.empty:
        st.warning("No sales transactions available.")
        return

    # Methodological Caveat
    st.warning(
        "🔎 **Investigation Notice**: Detected anomalies reflect statistically significant deviations "
        "from the local rolling baseline (e.g. promotional spikes, flash sales, catalog updates, "
        "or logging disruptions). **They do NOT constitute evidence of fraud, breach, or error.**"
    )

    c_win, c_sens = st.columns(2)
    with c_win:
        win_size = st.slider("Rolling Baseline Window (Days)", min_value=7, max_value=30, value=14, step=1)
    with c_sens:
        sens = st.slider("Outlier Multiplier (IQR threshold)", min_value=1.5, max_value=4.0, value=2.5, step=0.25)

    anomaly_df, summary = detect_sales_anomalies(sales_df, window_days=win_size, multiplier=sens)

    if anomaly_df.empty:
        st.info("Insufficient daily history for rolling anomaly detection.")
        return

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Analyzed Days", f"{summary['total_days']:,}")
    m2.metric("Total Anomalies Flagged", f"{summary['total_anomalies']:,}")
    m3.metric("Spikes (Surges)", f"{summary['surge_count']:,}")
    m4.metric("Drops (Plunges)", f"{summary['drop_count']:,}")

    st.markdown("---")

    # Time-series Plot with Upper/Lower Bound Bands and Anomaly Markers
    st.subheader("Daily Sales Baseline & Anomaly Envelope")
    fig = go.Figure()

    # Upper and Lower bound fill
    fig.add_trace(go.Scatter(
        x=anomaly_df["Date"],
        y=anomaly_df["UpperBound"],
        mode="lines",
        line=dict(color="rgba(148, 163, 184, 0.2)", width=1),
        name="Upper Bound",
        showlegend=False,
    ))
    fig.add_trace(go.Scatter(
        x=anomaly_df["Date"],
        y=anomaly_df["LowerBound"],
        mode="lines",
        line=dict(color="rgba(148, 163, 184, 0.2)", width=1),
        fill="tonexty",
        fillcolor="rgba(148, 163, 184, 0.1)",
        name="Expected Normal Range",
    ))

    # Baseline Median
    fig.add_trace(go.Scatter(
        x=anomaly_df["Date"],
        y=anomaly_df["Baseline"],
        mode="lines",
        line=dict(color="#38BDF8", dash="dash", width=1.5),
        name="Rolling Median Baseline",
    ))

    # Actual Sales
    fig.add_trace(go.Scatter(
        x=anomaly_df["Date"],
        y=anomaly_df["PositiveSales"],
        mode="lines",
        line=dict(color="#818CF8", width=2),
        name="Daily Positive Sales",
    ))

    # Anomalies
    anomalies_only = anomaly_df[anomaly_df["IsAnomaly"]]
    if not anomalies_only.empty:
        fig.add_trace(go.Scatter(
            x=anomalies_only["Date"],
            y=anomalies_only["PositiveSales"],
            mode="markers",
            marker=dict(color="#EF4444", size=10, symbol="diamond"),
            name="Anomaly Flag",
            text=anomalies_only["AnomalyType"],
        ))

    fig.update_layout(
        template="plotly_dark",
        xaxis_title="Date",
        yaxis_title="Sales Value ($)",
        margin=dict(l=20, r=20, t=40, b=20),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Anomaly Detail Table
    if not anomalies_only.empty:
        st.subheader("Flagged Anomaly Event Log")
        display_tbl = anomalies_only[["Date", "PositiveSales", "Baseline", "LowerBound", "UpperBound", "AnomalyType", "Orders"]].copy()
        st.dataframe(
            display_tbl.sort_values("Date", ascending=False).style.format({
                "PositiveSales": "${:,.2f}",
                "Baseline": "${:,.2f}",
                "LowerBound": "${:,.2f}",
                "UpperBound": "${:,.2f}",
                "Orders": "{:,}",
                "Date": lambda d: d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d),
            }),
            use_container_width=True,
        )
