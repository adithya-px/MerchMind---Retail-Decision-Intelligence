"""
Executive Overview Dashboard Page.
Renders high-level sales KPIs, monthly/daily positive sales trajectories,
and automated data-derived executive insights.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from src.sales_analytics import (
    compute_kpis,
    compute_monthly_trend,
    compute_daily_trend,
    compute_pareto_concentration,
    what_drives_revenue_analysis,
    generate_sales_insights,
)


def render(sales_df: pd.DataFrame, customer_df: pd.DataFrame, guest_metrics: dict) -> None:
    st.title("📊 Executive Overview")
    st.caption("Strategic high-level performance indicators and sales trajectories.")

    if sales_df.empty:
        st.warning("No transaction records match the active filter criteria.")
        return

    # Compute metrics
    kpis = compute_kpis(sales_df)
    _, pareto_share = compute_pareto_concentration(customer_df)
    drivers = what_drives_revenue_analysis(sales_df)

    # 1. KPI Cards Row
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Positive Sales Value", f"${kpis['total_positive_sales']:,.2f}", help="Total value of positive sales transactions (returns isolated).")
    c2.metric("Distinct Invoices", f"{kpis['distinct_invoices']:,}", help="Count of unique purchase orders.")
    c3.metric("Unique Customers", f"{kpis['unique_customers']:,}", help="Count of identified distinct buyer accounts.")
    c4.metric("Distinct Products", f"{kpis['distinct_products']:,}", help="Unique merchandise stock items sold.")
    c5.metric("Average Order Value", f"${kpis['avg_order_value']:,.2f}", help="Positive sales value per distinct order.")

    st.markdown("---")

    # 2. Executive Insights Section (Derives strictly from computed data)
    st.subheader("💡 Computed Executive Findings")
    insights = generate_sales_insights(kpis, pareto_share, drivers, guest_metrics)
    for insight in insights:
        st.markdown(f"- {insight}")

    st.markdown("---")

    # 3. Monthly & Daily Positive Sales Trends
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Monthly Positive Sales")
        monthly = compute_monthly_trend(sales_df)
        if not monthly.empty:
            fig_month = px.line(
                monthly,
                x="YearMonth",
                y="PositiveSales",
                markers=True,
                labels={"YearMonth": "Month", "PositiveSales": "Sales Value ($)"},
                title="Monthly Positive Sales Value",
            )
            fig_month.update_traces(line_color="#4F46E5", marker=dict(size=8, color="#818CF8"))
            fig_month.update_layout(template="plotly_dark", margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_month, width="stretch")
        else:
            st.info("Insufficient monthly data.")

    with col_right:
        st.subheader("Daily Sales Trajectory")
        daily = compute_daily_trend(sales_df)
        if not daily.empty:
            fig_day = px.area(
                daily,
                x="Date",
                y="PositiveSales",
                labels={"Date": "Date", "PositiveSales": "Daily Sales ($)"},
                title="Daily Positive Sales Trend",
            )
            fig_day.update_traces(line_color="#06B6D4", fillcolor="rgba(6, 182, 212, 0.2)")
            fig_day.update_layout(template="plotly_dark", margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_day, width="stretch")
        else:
            st.info("Insufficient daily data.")
