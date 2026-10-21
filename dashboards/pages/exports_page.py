"""
Data Exports & Usability Dashboard Page.
Provides filter-synchronized CSV downloads for:
1. Cleaned positive transactions
2. Customer RFM + Cluster Segments + Declining Flag
3. Daily/Monthly Sales Summary
"""

import streamlit as st
import pandas as pd

from src.customer_segmentation import compute_rfm_table, fit_kmeans_clustering
from src.declining_activity import detect_declining_customers
from src.sales_analytics import compute_monthly_trend, compute_daily_trend, compute_kpis
from src.config import DEFAULT_K_CLUSTERS, RANDOM_SEED


def render(sales_df: pd.DataFrame, customer_df: pd.DataFrame, guest_metrics: dict) -> None:
    st.title("📥 Filtered Data Exports")
    st.caption("Export business-ready CSV datasets synchronized strictly with active dashboard filters.")

    if sales_df.empty:
        st.warning("No data available to export under active filter parameters.")
        return

    st.markdown("All exported datasets reflect current sidebar filters (Date Range, Country, and Catalog selection).")

    # 1. Cleaned Transactions CSV
    st.subheader("1. Cleaned Transactions Export")
    st.caption(f"{len(sales_df):,} rows matching active filters.")
    csv_tx = sales_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Download Cleaned Transactions (CSV)",
        data=csv_tx,
        file_name="retailpulse_cleaned_transactions.csv",
        mime="text/csv",
        key="btn_dl_tx",
    )

    st.markdown("---")

    # 2. Customer RFM + Segmentation + Declining Flag CSV
    st.subheader("2. Customer Intelligence & Segments Export")
    if not customer_df.empty:
        rfm_df = compute_rfm_table(customer_df)
        if len(rfm_df) >= DEFAULT_K_CLUSTERS:
            clustered_df, _, _ = fit_kmeans_clustering(rfm_df, n_clusters=DEFAULT_K_CLUSTERS, random_state=RANDOM_SEED)
        else:
            clustered_df = rfm_df.copy()
            clustered_df["Cluster"] = 0
            clustered_df["SegmentName"] = "Cohort"

        declining_df, _ = detect_declining_customers(customer_df)
        declining_ids = set(declining_df["CustomerID"]) if not declining_df.empty else set()

        clustered_df["IsDeclining"] = clustered_df["CustomerID"].isin(declining_ids)
        export_cust = clustered_df[[
            "CustomerID", "SegmentName", "Recency", "Frequency", "Monetary",
            "AvgOrderValue", "IsDeclining", "FirstPurchase", "LastPurchase"
        ]].copy()

        st.caption(f"{len(export_cust):,} identified customer profiles with segment assignments and decline status.")
        csv_cust = export_cust.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Download Customer RFM & Segments (CSV)",
            data=csv_cust,
            file_name="retailpulse_customer_segments.csv",
            mime="text/csv",
            key="btn_dl_cust",
        )
    else:
        st.info("No identified customer profiles available in current filter selection.")

    st.markdown("---")

    # 3. Aggregated Sales Summary CSV
    st.subheader("3. Aggregated Monthly & Daily Sales Summary")
    monthly = compute_monthly_trend(sales_df)
    csv_monthly = monthly.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Download Monthly Aggregation Summary (CSV)",
        data=csv_monthly,
        file_name="retailpulse_monthly_sales_summary.csv",
        mime="text/csv",
        key="btn_dl_monthly",
    )
