"""
Unit tests for declining activity detection and heuristic rules.
"""

import pytest
import pandas as pd
from src.declining_activity import detect_declining_customers


@pytest.fixture
def activity_timeline_data():
    """
    Test scenario:
    Reference date: 2021-07-01
    Recent window: 90 days (2021-04-02 to 2021-07-01)
    Prior window: 90 days (2021-01-02 to 2021-04-01)

    Cust 1 (Declining):
      - Prior: spent $300 across 3 orders
      - Recent: spent $0 across 0 orders
    Cust 2 (Stable repeat):
      - Prior: spent $200 across 2 orders
      - Recent: spent $250 across 2 orders
    Cust 3 (Insufficient history):
      - Prior: spent $15 across 1 order (< min_prior_spend and < min_prior_orders)
      - Recent: spent $0
    """
    return pd.DataFrame([
        # Cust 1
        {"CustomerID": "C1", "InvoiceNo": "101", "InvoiceDate": pd.to_datetime("2021-01-15"), "LineRevenue": 100.0},
        {"CustomerID": "C1", "InvoiceNo": "102", "InvoiceDate": pd.to_datetime("2021-02-15"), "LineRevenue": 100.0},
        {"CustomerID": "C1", "InvoiceNo": "103", "InvoiceDate": pd.to_datetime("2021-03-15"), "LineRevenue": 100.0},

        # Cust 2
        {"CustomerID": "C2", "InvoiceNo": "201", "InvoiceDate": pd.to_datetime("2021-01-20"), "LineRevenue": 100.0},
        {"CustomerID": "C2", "InvoiceNo": "202", "InvoiceDate": pd.to_datetime("2021-03-20"), "LineRevenue": 100.0},
        {"CustomerID": "C2", "InvoiceNo": "203", "InvoiceDate": pd.to_datetime("2021-04-20"), "LineRevenue": 125.0},
        {"CustomerID": "C2", "InvoiceNo": "204", "InvoiceDate": pd.to_datetime("2021-05-20"), "LineRevenue": 125.0},

        # Cust 3 (Insufficient history)
        {"CustomerID": "C3", "InvoiceNo": "301", "InvoiceDate": pd.to_datetime("2021-02-01"), "LineRevenue": 15.0},
    ])


def test_detect_declining_customers(activity_timeline_data):
    ref_dt = pd.to_datetime("2021-07-01")
    flagged_df, summary = detect_declining_customers(
        activity_timeline_data,
        recent_window_days=90,
        prior_window_days=90,
        min_prior_orders=2,
        min_prior_spend=50.0,
        reference_date=ref_dt,
    )

    # C1 must be flagged
    assert "C1" in flagged_df["CustomerID"].values
    # C2 must NOT be flagged
    assert "C2" not in flagged_df["CustomerID"].values
    # C3 must be excluded due to insufficient history
    assert "C3" not in flagged_df["CustomerID"].values
    assert summary["excluded_insufficient_history"] >= 1

    c1_row = flagged_df[flagged_df["CustomerID"] == "C1"].iloc[0]
    assert c1_row["PriorSpend"] == 300.0
    assert c1_row["RecentSpend"] == 0.0
    assert c1_row["SpendDrop"] == 300.0
    assert c1_row["SpendDropPct"] == 100.0
