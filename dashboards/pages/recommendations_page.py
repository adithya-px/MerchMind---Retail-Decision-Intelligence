"""
Strategic Marketing Recommendations Dashboard Page.
Renders segment-specific playbooks directly linked to computed cluster centroids.
Features explicit causal-effect disclaimers.
"""

import streamlit as st
import pandas as pd

from src.customer_segmentation import compute_rfm_table, fit_kmeans_clustering
from src.declining_activity import detect_declining_customers
from src.recommendations import generate_recommendations
from src.config import DEFAULT_K_CLUSTERS, RANDOM_SEED


def render(sales_df: pd.DataFrame, customer_df: pd.DataFrame, guest_metrics: dict) -> None:
    st.title("💡 Strategic Recommendations")
    st.caption("Actionable marketing playbooks, retention incentives, and lifecycle interventions.")

    if customer_df.empty:
        st.warning("No identified customer data available.")
        return

    # Scientific and commercial disclaimer
    st.info(
        "📋 **Disclaimer**: The recommendations below are **heuristic business strategies** "
        "derived from observed customer cluster profiles and purchasing patterns. "
        "They do NOT constitute validated causal treatments or guaranteed lift figures. "
        "Teams should validate these initiatives using randomized A/B test experiments before full rollout."
    )

    # Compute models for recommendation input
    rfm_df = compute_rfm_table(customer_df)
    if len(rfm_df) < DEFAULT_K_CLUSTERS:
        st.warning("Insufficient customer volume to compute segment recommendations.")
        return

    _, profiles, _ = fit_kmeans_clustering(rfm_df, n_clusters=DEFAULT_K_CLUSTERS, random_state=RANDOM_SEED)
    _, dec_summary = detect_declining_customers(customer_df)

    playbooks = generate_recommendations(profiles, dec_summary)

    for item in playbooks:
        with st.container():
            st.markdown(f"### 🏷️ Segment: **{item['segment_name']}**")
            st.markdown(f"**Focus Strategy**: `{item['strategy_type']}`")

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Customer Size", f"{item['customer_count']:,}")
            c2.metric("Revenue Contribution", f"{item['revenue_share_pct']:.1f}%")
            c3.metric("Avg Order Frequency", f"{item['avg_frequency']:.1f} orders")
            c4.metric("Avg Monetary Spend", f"${item['avg_monetary']:,.2f}")

            st.markdown(f"**Strategic Objective**: {item['objective']}")
            st.markdown("**Recommended Marketing Actions**:")
            for action in item["actions"]:
                st.markdown(f"- {action}")

            st.markdown("---")
