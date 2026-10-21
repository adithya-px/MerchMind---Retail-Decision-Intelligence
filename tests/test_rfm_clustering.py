"""
Unit tests for RFM calculations, K-Means clustering, and edge case handling.
"""

import pytest
import pandas as pd
import numpy as np

from src.customer_segmentation import (
    compute_rfm_table,
    evaluate_candidate_k,
    fit_kmeans_clustering,
    assign_interpretable_labels,
)
from src.config import GUEST_CUSTOMER_LABEL


@pytest.fixture
def known_customer_data():
    """
    Known dataset:
    Cust 101: 2 orders (Invoice 1 on 2021-01-01 of 50, Invoice 2 on 2021-01-10 of 70). Total = 120, freq = 2.
    Cust 102: 1 order (Invoice 3 on 2021-01-05 of 40). Total = 40, freq = 1.
    Cust 103: 3 orders (Invoice 4 on 2021-01-02 of 100, Invoice 5 on 2021-01-08 of 150, Invoice 6 on 2021-01-12 of 200). Total = 450, freq = 3.
    Cust 104: 1 order (Invoice 7 on 2021-01-01 of 20). Total = 20, freq = 1.
    Reference date: 2021-01-13 (1 day after 2021-01-12)
    """
    return pd.DataFrame([
        {"CustomerID": "101", "InvoiceNo": "1", "InvoiceDate": pd.to_datetime("2021-01-01"), "LineRevenue": 50.0},
        {"CustomerID": "101", "InvoiceNo": "2", "InvoiceDate": pd.to_datetime("2021-01-10"), "LineRevenue": 70.0},
        {"CustomerID": "102", "InvoiceNo": "3", "InvoiceDate": pd.to_datetime("2021-01-05"), "LineRevenue": 40.0},
        {"CustomerID": "103", "InvoiceNo": "4", "InvoiceDate": pd.to_datetime("2021-01-02"), "LineRevenue": 100.0},
        {"CustomerID": "103", "InvoiceNo": "5", "InvoiceDate": pd.to_datetime("2021-01-08"), "LineRevenue": 150.0},
        {"CustomerID": "103", "InvoiceNo": "6", "InvoiceDate": pd.to_datetime("2021-01-12"), "LineRevenue": 200.0},
        {"CustomerID": "104", "InvoiceNo": "7", "InvoiceDate": pd.to_datetime("2021-01-01"), "LineRevenue": 20.0},
        {"CustomerID": GUEST_CUSTOMER_LABEL, "InvoiceNo": "8", "InvoiceDate": pd.to_datetime("2021-01-12"), "LineRevenue": 500.0},
    ])


def test_compute_rfm_on_known_example(known_customer_data):
    ref_date = pd.to_datetime("2021-01-13")
    rfm = compute_rfm_table(known_customer_data, reference_date=ref_date)

    # Guest should be excluded
    assert GUEST_CUSTOMER_LABEL not in rfm["CustomerID"].values
    assert len(rfm) == 4

    # Cust 103: last order on 2021-01-12 -> Recency = 1 day, Frequency = 3, Monetary = 450
    c103 = rfm[rfm["CustomerID"] == "103"].iloc[0]
    assert c103["Recency"] == 1
    assert c103["Frequency"] == 3
    assert c103["Monetary"] == 450.0

    # Cust 101: last order on 2021-01-10 -> Recency = 3 days, Frequency = 2, Monetary = 120
    c101 = rfm[rfm["CustomerID"] == "101"].iloc[0]
    assert c101["Recency"] == 3
    assert c101["Frequency"] == 2
    assert c101["Monetary"] == 120.0


def test_compute_rfm_distinct_invoice_frequency():
    """Verify that multiple line items in the same Invoice count as 1 order frequency."""
    multi_line_data = pd.DataFrame([
        {"CustomerID": "201", "InvoiceNo": "INV-100", "InvoiceDate": pd.to_datetime("2021-05-01"), "LineRevenue": 15.0},
        {"CustomerID": "201", "InvoiceNo": "INV-100", "InvoiceDate": pd.to_datetime("2021-05-01"), "LineRevenue": 25.0},
        {"CustomerID": "201", "InvoiceNo": "INV-100", "InvoiceDate": pd.to_datetime("2021-05-01"), "LineRevenue": 10.0},
        {"CustomerID": "201", "InvoiceNo": "INV-101", "InvoiceDate": pd.to_datetime("2021-05-05"), "LineRevenue": 50.0},
    ])
    rfm = compute_rfm_table(multi_line_data, reference_date=pd.to_datetime("2021-05-06"))
    assert len(rfm) == 1
    row = rfm.iloc[0]
    # 4 rows across 2 distinct invoices -> Frequency must be 2, Monetary must be 100
    assert row["Frequency"] == 2
    assert row["Monetary"] == 100.0
    assert row["Recency"] == 1


def test_compute_rfm_default_reference_date():
    """Verify default reference date calculation: max(InvoiceDate) + 1 day."""
    data = pd.DataFrame([
        {"CustomerID": "301", "InvoiceNo": "INV-1", "InvoiceDate": pd.to_datetime("2021-06-10 10:00:00"), "LineRevenue": 50.0},
        {"CustomerID": "302", "InvoiceNo": "INV-2", "InvoiceDate": pd.to_datetime("2021-06-15 15:00:00"), "LineRevenue": 80.0},
    ])
    rfm = compute_rfm_table(data)
    # Max date is 2021-06-15 15:00:00 -> default ref is 2021-06-16 15:00:00
    c302 = rfm[rfm["CustomerID"] == "302"].iloc[0]
    c301 = rfm[rfm["CustomerID"] == "301"].iloc[0]
    assert c302["Recency"] == 1
    assert c301["Recency"] == 6


def test_compute_rfm_positive_monetary_filtering():
    """Verify zero and negative monetary transactions are strictly excluded."""
    data = pd.DataFrame([
        {"CustomerID": "401", "InvoiceNo": "INV-1", "InvoiceDate": pd.to_datetime("2021-07-01"), "LineRevenue": 100.0},
        {"CustomerID": "402", "InvoiceNo": "INV-2", "InvoiceDate": pd.to_datetime("2021-07-01"), "LineRevenue": 0.0},
        {"CustomerID": "403", "InvoiceNo": "INV-3", "InvoiceDate": pd.to_datetime("2021-07-01"), "LineRevenue": -50.0},
    ])
    rfm = compute_rfm_table(data)
    # Only customer 401 has positive monetary spend
    assert len(rfm) == 1
    assert rfm.iloc[0]["CustomerID"] == "401"
    assert rfm.iloc[0]["Monetary"] == 100.0


def test_kmeans_with_too_few_unique_customers(known_customer_data):
    ref_date = pd.to_datetime("2021-01-13")
    rfm = compute_rfm_table(known_customer_data, reference_date=ref_date)
    # 4 customers, request 6 clusters -> should raise ValueError with actionable error message
    with pytest.raises(ValueError, match="Cannot fit 6 clusters with only 4 customers"):
        fit_kmeans_clustering(rfm, n_clusters=6)


def test_fit_kmeans_clustering_outputs(known_customer_data):
    ref_date = pd.to_datetime("2021-01-13")
    rfm = compute_rfm_table(known_customer_data, reference_date=ref_date)
    clustered, profiles, meta = fit_kmeans_clustering(rfm, n_clusters=2, random_state=42)

    assert "Cluster" in clustered.columns
    assert "SegmentName" in clustered.columns
    assert "PCA1" in clustered.columns
    assert "PCA2" in clustered.columns
    assert len(profiles) == 2
    assert meta["n_clusters"] == 2
    assert -1.0 <= meta["silhouette_score"] <= 1.0


def test_evaluate_candidate_k():
    """Verify evaluation of candidate k clusters across range."""
    # Synthesize small cohort of 10 customers
    np.random.seed(42)
    rfm = pd.DataFrame({
        "CustomerID": [str(i) for i in range(10)],
        "Recency": np.random.randint(1, 100, size=10),
        "Frequency": np.random.randint(1, 20, size=10),
        "Monetary": np.random.uniform(20.0, 1000.0, size=10),
    })
    eval_df, best_k = evaluate_candidate_k(rfm, k_range=(2, 5))
    assert len(eval_df) == 4
    assert list(eval_df["k"]) == [2, 3, 4, 5]
    assert "Inertia" in eval_df.columns
    assert "SilhouetteScore" in eval_df.columns
    assert best_k in [2, 3, 4, 5]


def test_stable_human_readable_segment_mapping():
    """Verify distinct, human-readable segment names across candidate k counts."""
    np.random.seed(42)
    rfm = pd.DataFrame({
        "CustomerID": [str(i) for i in range(30)],
        "Recency": np.random.randint(1, 200, size=30),
        "Frequency": np.random.randint(1, 30, size=30),
        "Monetary": np.random.uniform(50.0, 5000.0, size=30),
    })
    for k in [2, 3, 4, 5]:
        clustered, profiles, meta = fit_kmeans_clustering(rfm, n_clusters=k, random_state=42)
        names = profiles["SegmentName"].tolist()
        # Verify no duplicate segment names
        assert len(names) == len(set(names))
        # Verify no empty or null names
        for n in names:
            assert isinstance(n, str) and len(n) > 0
            assert "nan" not in n.lower()
