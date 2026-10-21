"""
Customer Intelligence & K-Means Clustering Page.
Features RFM calculation, log1p feature transformation, Elbow & Silhouette evaluation,
PCA 2D projection, cluster profile cards, filterable customer cohorts,
and an educational walkthrough of K-Means limitations arranged in focused sub-tabs.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np

from src.customer_segmentation import (
    compute_rfm_table,
    evaluate_candidate_k,
    fit_kmeans_clustering,
)
from src.config import DEFAULT_K_CLUSTERS, RANDOM_SEED
from dashboards.pages import declining_page, recommendations_page


def render(sales_df: pd.DataFrame, customer_df: pd.DataFrame, guest_metrics: dict) -> None:
    st.title("🧠 Customer Intelligence (RFM + K-Means)")
    st.caption("Behavioral customer segmentation, optimal k evaluation, and multidimensional customer profiling.")

    if customer_df.empty:
        st.warning("No identified customer transactions available for clustering under the current filters.")
        return

    # Reference Date Selector & Model Controls
    max_date = customer_df["InvoiceDate"].max().date()
    default_ref = max_date + pd.Timedelta(days=1)
    
    col_ref, col_k = st.columns([2, 2])
    with col_ref:
        ref_date = st.date_input(
            "Reference Date (for Recency calculation)",
            value=default_ref,
            help="Defaults to latest valid transaction date + 1 day.",
        )

    # Compute RFM
    rfm_df = compute_rfm_table(customer_df, reference_date=pd.to_datetime(ref_date))
    n_cust = len(rfm_df)

    if n_cust < 3:
        st.error(f"Need at least 3 identified customers to perform clustering. Current cohort size: {n_cust}")
        return

    # Candidate k evaluation
    with col_k:
        selected_k = st.slider(
            "Select Number of Clusters (k)",
            min_value=2,
            max_value=min(8, n_cust - 1),
            value=min(4, n_cust - 1),
            help="Defensible cluster selection. Use the Diagnostics tab below to inspect optimal silhouette scores.",
        )

    # Fit Model & Train Live
    clustered_df, profiles, metadata = fit_kmeans_clustering(
        rfm_df,
        n_clusters=selected_k,
        random_state=RANDOM_SEED,
    )

    # High-level Diagnostic KPI cards
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Silhouette Score", f"{metadata['silhouette_score']:.3f}", help="Separation metric: ranges [-1, 1]. >0.4 indicates solid separation.")
    c2.metric("Customers Clustered", f"{n_cust:,}")
    c3.metric("PCA 2D Variance", f"{metadata['total_pca_variance_pct']:.1f}%", help="Percentage of RFM feature variance captured in 2D.")
    c4.metric("Active Clusters", f"{selected_k}")
    st.markdown("---")

    # Sub-tabs for model analysis and customer drilldown
    sub_clusters, sub_diagnostics, sub_declining, sub_playbooks, sub_cohort = st.tabs([
        "👥 Segment Profiles & 2D Projection",
        "🔬 Model Diagnostics (Elbow & Silhouette)",
        "📉 Declining & Churn Risks",
        "💡 Strategic Retention Playbooks",
        "📋 Customer Cohort Explorer",
    ])

    with sub_clusters:
        # 1. 2D PCA Visualization
        st.subheader("🗺️ 2D PCA Cluster Projection")
        fig_pca = px.scatter(
            clustered_df,
            x="PCA1",
            y="PCA2",
            color="SegmentName",
            hover_data=["CustomerID", "Recency", "Frequency", "Monetary"],
            labels={"PCA1": "Principal Component 1 (Size/Volume)", "PCA2": "Principal Component 2 (Recency/Timing)"},
            title=f"K-Means Customer Segments (k={selected_k}, PCA Projection)",
        )
        fig_pca.update_layout(template="plotly_dark", margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_pca, width="stretch")

        # 2. Segment Distribution & Revenue Contribution
        col_dist, col_rev = st.columns(2)
        with col_dist:
            st.subheader("Customer Distribution by Segment")
            fig_cust_share = px.pie(
                profiles,
                names="SegmentName",
                values="CustomerCount",
                hole=0.4,
                title="Share of Total Customers",
            )
            fig_cust_share.update_layout(template="plotly_dark", margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_cust_share, width="stretch")

        with col_rev:
            st.subheader("Revenue Contribution by Segment")
            fig_rev_share = px.bar(
                profiles.sort_values("RevenueSharePct", ascending=False),
                x="RevenueSharePct",
                y="SegmentName",
                orientation="h",
                labels={"RevenueSharePct": "Revenue Share (%)", "SegmentName": "Segment"},
                title="Share of Positive Sales Value",
            )
            fig_rev_share.update_traces(marker_color="#F59E0B")
            fig_rev_share.update_layout(template="plotly_dark", margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_rev_share, width="stretch")

        # 3. Cluster Profile Centroid Table
        st.subheader("📊 Empirical Cluster Profiles")
        st.caption("Centroid metrics (mean and median) for Recency (days), Frequency (orders), and Monetary ($).")
        display_profiles = profiles[[
            "SegmentName", "CustomerCount", "CustomerSharePct", "RevenueSharePct",
            "Recency_mean", "Frequency_mean", "Monetary_mean", "Description"
        ]].copy()
        st.dataframe(
            display_profiles.style.format({
                "CustomerCount": "{:,}",
                "CustomerSharePct": "{:.1f}%",
                "RevenueSharePct": "{:.1f}%",
                "Recency_mean": "{:.0f} days",
                "Frequency_mean": "{:.1f} orders",
                "Monetary_mean": "${:,.2f}",
            }),
            width="stretch",
        )

    with sub_diagnostics:
        st.subheader("Candidate k Evaluation (Elbow & Silhouette)")
        st.markdown(
            """
            To defensibly select the number of clusters $k$, we evaluate candidates across $k \\in [2, 8]$:
            1. **Inertia (Elbow Method)**: Sum of squared distances to cluster centroids (measures internal compactness).
            2. **Silhouette Score**: Ratio of intra-cluster distance to nearest neighbor cluster distance (measures geometric separation).
            """
        )
        try:
            eval_df, best_stat_k = evaluate_candidate_k(rfm_df)
            col_eval_chart, col_eval_tab = st.columns([2, 1])
            with col_eval_chart:
                fig_eval = go.Figure()
                fig_eval.add_trace(go.Scatter(
                    x=eval_df["k"],
                    y=eval_df["SilhouetteScore"],
                    mode="lines+markers",
                    name="Silhouette Score",
                    line=dict(color="#10B981", width=3),
                ))
                fig_eval.update_layout(
                    title="Silhouette Score Across Candidate k",
                    xaxis_title="Number of Clusters (k)",
                    yaxis_title="Mean Silhouette Score",
                    template="plotly_dark",
                    margin=dict(l=20, r=20, t=40, b=20),
                )
                st.plotly_chart(fig_eval, width="stretch")
            with col_eval_tab:
                st.dataframe(eval_df.style.format({"Inertia": "{:,.1f}", "SilhouetteScore": "{:.3f}"}), width="stretch")
                st.info(f"Statistically optimal geometric separation is at **k = {best_stat_k}**.")
        except Exception as e:
            st.warning(f"Evaluation skipped: {e}")

        st.markdown("---")
        st.markdown(
            r"""
            ### Educational Disclosure & Limitations
            * **Unsupervised Geometry**: K-Means groups customers based purely on mathematical distance in normalized $(\log(R), \log(F), \log(M))$ space. There are no labeled ground-truth targets.
            * **Silhouette Meaning**: Measures geometric separation, not customer profitability or brand affinity.
            * **Why Skew Transformation (log1p)**: Mitigates right-skewed whale transactions that would otherwise distort cluster centroids.
            """
        )

    with sub_declining:
        declining_page.render(sales_df, customer_df, guest_metrics, show_title=False)

    with sub_playbooks:
        recommendations_page.render(sales_df, customer_df, guest_metrics, show_title=False)

    with sub_cohort:
        st.subheader("🔍 Explore Customer Cohorts")
        filter_seg = st.selectbox("Filter by Segment", ["All Segments"] + list(profiles["SegmentName"].unique()))
        table_view = clustered_df[["CustomerID", "SegmentName", "Recency", "Frequency", "Monetary", "AvgOrderValue", "FirstPurchase", "LastPurchase"]].copy()
        if filter_seg != "All Segments":
            table_view = table_view[table_view["SegmentName"] == filter_seg]

        st.dataframe(
            table_view.sort_values(by="Monetary", ascending=False).style.format({
                "Monetary": "${:,.2f}",
                "AvgOrderValue": "${:,.2f}",
                "Recency": "{:.0f} d",
                "Frequency": "{:.0f}",
                "FirstPurchase": lambda d: d.strftime("%Y-%m-%d") if pd.notna(d) else "",
                "LastPurchase": lambda d: d.strftime("%Y-%m-%d") if pd.notna(d) else "",
            }),
            width="stretch",
            height=380,
        )
