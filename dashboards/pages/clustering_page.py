"""
Customer Intelligence & K-Means Clustering Page.
Features RFM calculation, log1p feature transformation, Elbow & Silhouette evaluation,
PCA 2D projection, cluster profile cards, filterable customer cohorts,
and an educational walkthrough of K-Means limitations.
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


def render(sales_df: pd.DataFrame, customer_df: pd.DataFrame, guest_metrics: dict) -> None:
    st.title("🧠 Customer Intelligence (RFM + K-Means)")
    st.caption("Unsupervised behavioral clustering, optimal k evaluation, and multidimensional customer profiling.")

    if customer_df.empty:
        st.warning("No identified customer transactions available for clustering under the current filters.")
        return

    # Reference Date Selector
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

    # Diagnostic & Candidate k Evaluation
    with st.expander("🔬 Model Diagnostics: Candidate k Evaluation (Elbow & Silhouette)", expanded=False):
        st.markdown(
            """
            To defensibly select the number of clusters $k$, we evaluate candidates across $k \\in [2, 8]$ using:
            1. **Inertia (Elbow Method)**: Sum of squared distances to cluster centroids (measures internal compactness).
            2. **Silhouette Score**: Ratio of intra-cluster distance to nearest neighbor cluster distance (measures separation).
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
                    title="Silhouette Score across candidate k",
                    xaxis_title="Number of Clusters (k)",
                    yaxis_title="Mean Silhouette Score",
                    template="plotly_dark",
                    margin=dict(l=20, r=20, t=40, b=20),
                )
                st.plotly_chart(fig_eval, use_container_width=True)
            with col_eval_tab:
                st.dataframe(eval_df.style.format({"Inertia": "{:,.1f}", "SilhouetteScore": "{:.3f}"}), use_container_width=True)
                st.info(f"Statistically optimal separation peak is at **k = {best_stat_k}**.")
        except Exception as e:
            st.warning(f"Evaluation skipped: {e}")
            best_stat_k = DEFAULT_K_CLUSTERS

    with col_k:
        selected_k = st.slider(
            "Select Number of Clusters (k)",
            min_value=2,
            max_value=min(8, n_cust - 1),
            value=min(best_stat_k, 5),
            help="Choose k defensibly. While statistical silhouette selects optimal separation, commercial utility often favors 4–5 distinct actionable segments.",
        )

    # Fit Model
    clustered_df, profiles, metadata = fit_kmeans_clustering(
        rfm_df,
        n_clusters=selected_k,
        random_state=RANDOM_SEED,
    )

    # Model Diagnostics Summary
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Silhouette Score", f"{metadata['silhouette_score']:.3f}", help="Separation metric: ranges [-1, 1]. >0.4 indicates solid separation.")
    c2.metric("Total Customers Clustered", f"{n_cust:,}")
    c3.metric("PCA 2D Variance Explained", f"{metadata['total_pca_variance_pct']:.1f}%", help="Percentage of RFM feature variance captured in the 2D visualization.")
    c4.metric("Clusters Formed", f"{selected_k}")

    st.markdown("---")

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
    st.plotly_chart(fig_pca, use_container_width=True)

    st.markdown("---")

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
        st.plotly_chart(fig_cust_share, use_container_width=True)

    with col_rev:
        st.subheader("Revenue Contribution by Segment")
        fig_rev_share = px.bar(
            profiles.sort_values("RevenueSharePct", ascending=False),
            x="RevenueSharePct",
            y="SegmentName",
            orientation="h",
            labels={"RevenueSharePct": "Revenue Share (%)", "SegmentName": "Segment"},
            title="Share of Identified Positive Sales Value",
        )
        fig_rev_share.update_traces(marker_color="#F59E0B")
        fig_rev_share.update_layout(template="plotly_dark", margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_rev_share, use_container_width=True)

    st.markdown("---")

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
        use_container_width=True,
    )

    st.markdown("---")

    # 4. Filterable Customer Cohort Table
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
        use_container_width=True,
        height=350,
    )

    st.markdown("---")

    # 5. Methodological Walkthrough & Limitations Note
    with st.expander("ℹ️ Understanding K-Means, Silhouette, and Inherent Limitations", expanded=False):
        st.markdown(
            """
            ### Educational Guide: Unsupervised Clustering & Evaluation
            
            * **Unsupervised Learning**: K-Means groups customers based purely on natural geometric similarity in the transformed $(\\log(R), \\log(F), \\log(M))$ feature space. Unlike supervised learning, there are no ground-truth 'labels' or historical target outcomes.
            * **What Silhouette Score Measures**: The Silhouette coefficient assesses **cluster separation and compactness**. A higher score indicates that clusters are well-isolated from one another. **Crucially, it does NOT measure profitability, customer satisfaction, or future predictive accuracy.**
            * **Why Skew Transformation (log1p) is Essential**: E-commerce RFM metrics suffer from heavy right skew (a few whales generate immense revenue and order hundreds of times). Standard K-Means assumes spherical clusters; without logarithmic transformation, extreme outliers distort cluster centroids and crush the vast majority of normal customers into a single massive cluster.
            * **Limitations**:
              - K-Means is sensitive to initialization and initial centroid seeds (we enforce a fixed `random_state=42` for reproducibility).
              - Standard K-Means assumes roughly equal cluster variances and spherical boundaries.
              - Segment definitions are observational snapshots in time, not static destinies.
            """
        )
