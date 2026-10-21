"""
Unit tests to verify consistency between dashboard segmentation and exported datasets.
"""

import pytest
import pandas as pd
from src.customer_segmentation import compute_rfm_table, fit_kmeans_clustering
from src.declining_activity import detect_declining_customers


@pytest.fixture
def multi_customer_data():
    records = []
    # 6 customers with distinct profiles
    for i in range(1, 7):
        cust_id = f"C{i}"
        for order_idx in range(1, i + 2):
            records.append({
                "CustomerID": cust_id,
                "InvoiceNo": f"INV_{i}_{order_idx}",
                "InvoiceDate": pd.to_datetime(f"2021-0{min(i, 6)}-{min(order_idx*4, 28)}"),
                "LineRevenue": float(order_idx * 50.0),
            })
    return pd.DataFrame(records)


def test_consistency_of_exported_segments(multi_customer_data):
    rfm_df = compute_rfm_table(multi_customer_data)
    clustered_df, profiles, _ = fit_kmeans_clustering(rfm_df, n_clusters=3, random_state=42)
    declining_df, _ = detect_declining_customers(multi_customer_data)
    declining_ids = set(declining_df["CustomerID"]) if not declining_df.empty else set()

    clustered_df["IsDeclining"] = clustered_df["CustomerID"].isin(declining_ids)

    # Verify no customer lost between RFM, clustering, and export
    assert len(clustered_df) == len(rfm_df)
    assert set(clustered_df["CustomerID"]) == set(rfm_df["CustomerID"])
    assert not clustered_df["SegmentName"].isna().any()
    assert not clustered_df["IsDeclining"].isna().any()
    # Check that Monetary in clustered_df matches sum of LineRevenue in source
    for cust_id in clustered_df["CustomerID"]:
        expected_rev = multi_customer_data[multi_customer_data["CustomerID"] == cust_id]["LineRevenue"].sum()
        actual_rev = clustered_df[clustered_df["CustomerID"] == cust_id]["Monetary"].iloc[0]
        assert actual_rev == expected_rev
