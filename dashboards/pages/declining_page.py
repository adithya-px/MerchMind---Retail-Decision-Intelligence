"""
Declining-Activity Detection Dashboard Page.
Renders heuristic indicators of customer activity drop-offs, inter-purchase cadence
lapses, ranked re-engagement lists, and explicit disclosures.
"""

import streamlit as st
import plotly.express as px
import pandas as pd

from src.declining_activity import detect_declining_customers
from src.config import (
    DEFAULT_RECENT_WINDOW_DAYS,
    DEFAULT_PRIOR_WINDOW_DAYS,
    MIN_TRANSACTIONS_FOR_DECLINE,
    MIN_PAST_SPEND_FOR_DECLINE,
)


def render(sales_df: pd.DataFrame, customer_df: pd.DataFrame, guest_metrics: dict, show_title: bool = True) -> None:
    if show_title:
        st.title("📉 Declining-Activity Detection")
        st.caption("Identify previously engaged accounts exhibiting sharp spend drops or lapsed purchase cadence.")

    if customer_df.empty:
        st.warning("No identified customer transactions available.")
        return

    # Methodological disclosure banner
    st.info(
        "ℹ️ **Methodology Note**: This analysis computes **heuristic activity indicators**, "
        "not a black-box churn forecast. It benchmarks recent purchasing velocity against each customer's own baseline and gap cadence."
    )

    # Window selection controls
    with st.expander("⚙️ Detection Window Parameters & Sensitivity", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        recent_win = c1.slider("Recent Window (days)", min_value=30, max_value=180, value=DEFAULT_RECENT_WINDOW_DAYS, step=15)
        prior_win = c2.slider("Prior Window (days)", min_value=30, max_value=180, value=DEFAULT_PRIOR_WINDOW_DAYS, step=15)
        min_orders = c3.number_input("Min Prior Orders to Qualify", min_value=1, max_value=10, value=MIN_TRANSACTIONS_FOR_DECLINE)
        min_spend = c4.number_input("Min Prior Spend ($)", min_value=10.0, max_value=500.0, value=MIN_PAST_SPEND_FOR_DECLINE, step=10.0)

    # Run detection
    declining_df, summary = detect_declining_customers(
        customer_df,
        recent_window_days=recent_win,
        prior_window_days=prior_win,
        min_prior_orders=min_orders,
        min_prior_spend=min_spend,
    )

    # Summary metric cards
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Flagged Accounts", f"{summary['flagged_declining']:,}", help="Previously active accounts with significant spend drop or lapsed cadence.")
    c2.metric("Revenue at Risk", f"${summary['revenue_at_risk']:,.2f}", help="Total drop in positive spend across flagged accounts.")
    c3.metric("Eligible Cohort", f"{summary['eligible_customers']:,}", help="Accounts meeting minimum baseline history threshold.")
    c4.metric(
        "Excluded (New / Light)",
        f"{summary['excluded_insufficient_history']:,}",
        help="Accounts with fewer than minimum orders or spend in the prior baseline window.",
    )

    st.markdown("---")

    # Visualizing drop distribution
    if not declining_df.empty:
        col_chart, col_reasons = st.columns([2, 1])

        with col_chart:
            st.subheader("Distribution of Drop Severity")
            fig_drop = px.histogram(
                declining_df,
                x="SpendDropPct",
                nbins=20,
                labels={"SpendDropPct": "Spend Drop Percentage (%)"},
                title="Customer Spend Reduction Severity",
            )
            fig_drop.update_traces(marker_color="#EF4444")
            fig_drop.update_layout(
                yaxis_title="Customer Count",
                template="plotly_dark",
                margin=dict(l=20, r=20, t=40, b=20),
            )
            st.plotly_chart(fig_drop, width="stretch")

        with col_reasons:
            st.subheader("Primary Decline Drivers")
            reason_counts = declining_df["DeclineReason"].value_counts().head(5)
            for reason, cnt in reason_counts.items():
                st.markdown(f"• **{reason}**: `{cnt:,}` accounts")

        st.markdown("---")

        # Ranked Re-Engagement Table
        st.subheader("🎯 Priority Accounts to Re-Engage")
        st.caption(
            "Ranked by absolute past revenue lost (Spend Drop). Excludes accounts with insufficient historical transactions."
        )

        display_cols = [
            "CustomerID", "LastOverallPurchase", "PriorSpend", "RecentSpend",
            "SpendDrop", "SpendDropPct", "PriorOrders", "RecentOrders",
            "MedianCadenceDays", "DaysSinceLastPurchase", "DeclineReason"
        ]
        reengage_table = declining_df[display_cols].copy()

        st.dataframe(
            reengage_table.style.format({
                "PriorSpend": "${:,.2f}",
                "RecentSpend": "${:,.2f}",
                "SpendDrop": "${:,.2f}",
                "SpendDropPct": "{:.0f}%",
                "PriorOrders": "{:d}",
                "RecentOrders": "{:d}",
                "MedianCadenceDays": lambda d: f"{d:.0f} days" if pd.notna(d) else "N/A",
                "DaysSinceLastPurchase": "{:d} days",
                "LastOverallPurchase": lambda d: d.strftime("%Y-%m-%d") if pd.notna(d) else "",
            }),
            width="stretch",
            height=400,
        )
    else:
        st.success("No customers qualify as declining under current threshold parameters.")
