"""
Smoke tests for dashboard pages and registry to verify headless execution without exceptions.
"""

import pytest
import pandas as pd
from dashboards.app import PAGES
from src.cleaning import CleaningAuditLogger
from src.config import GUEST_CUSTOMER_LABEL


@pytest.fixture
def mock_dashboard_data():
    sales_df = pd.DataFrame([
        {"InvoiceNo": "1", "StockCode": "A", "Description": "Prod A", "Quantity": 2, "UnitPrice": 10.0, "LineRevenue": 20.0, "CustomerID": "101", "Country": "UK", "InvoiceDate": pd.to_datetime("2021-01-05"), "YearMonth": "2021-01", "Date": "2021-01-05", "DayOfWeek": "Tuesday", "Hour": 10, "IsGuest": False},
        {"InvoiceNo": "2", "StockCode": "B", "Description": "Prod B", "Quantity": 1, "UnitPrice": 30.0, "LineRevenue": 30.0, "CustomerID": "102", "Country": "France", "InvoiceDate": pd.to_datetime("2021-01-10"), "YearMonth": "2021-01", "Date": "2021-01-10", "DayOfWeek": "Sunday", "Hour": 14, "IsGuest": False},
        {"InvoiceNo": "3", "StockCode": "C", "Description": "Prod C", "Quantity": 5, "UnitPrice": 10.0, "LineRevenue": 50.0, "CustomerID": "103", "Country": "Germany", "InvoiceDate": pd.to_datetime("2021-02-15"), "YearMonth": "2021-02", "Date": "2021-02-15", "DayOfWeek": "Monday", "Hour": 9, "IsGuest": False},
        {"InvoiceNo": "4", "StockCode": "A", "Description": "Prod A", "Quantity": 2, "UnitPrice": 10.0, "LineRevenue": 20.0, "CustomerID": "104", "Country": "UK", "InvoiceDate": pd.to_datetime("2021-03-01"), "YearMonth": "2021-03", "Date": "2021-03-01", "DayOfWeek": "Monday", "Hour": 11, "IsGuest": False},
        {"InvoiceNo": "5", "StockCode": "B", "Description": "Prod B", "Quantity": 1, "UnitPrice": 15.0, "LineRevenue": 15.0, "CustomerID": GUEST_CUSTOMER_LABEL, "Country": "UK", "InvoiceDate": pd.to_datetime("2021-03-05"), "YearMonth": "2021-03", "Date": "2021-03-05", "DayOfWeek": "Friday", "Hour": 12, "IsGuest": True},
    ])
    customer_df = sales_df[~sales_df["IsGuest"]].copy()
    cancellations_df = pd.DataFrame([
        {"InvoiceNo": "C01", "StockCode": "A", "Description": "Prod A", "Quantity": -1, "UnitPrice": 10.0, "LineRevenue": -10.0, "CustomerID": "101", "Country": "UK", "InvoiceDate": pd.to_datetime("2021-01-06")},
    ])
    logger = CleaningAuditLogger()
    logger.log_step(1, "Raw Ingestion", "Load", "Test", 5, 0, 5)
    guest_metrics = {
        "total_sales_value": 135.0,
        "guest_sales_value": 15.0,
        "guest_revenue_share_pct": 11.1,
        "total_sales_rows": 5,
        "guest_rows": 1,
        "guest_row_share_pct": 20.0,
        "identified_customers_count": 4,
        "total_cancellations_count": 1,
        "cancellations_value": 10.0,
    }
    return sales_df, customer_df, cancellations_df, logger, guest_metrics


def test_page_registry_entries():
    assert len(PAGES) >= 8
    expected_pages = [
        "📊 Executive Overview",
        "📈 Sales & Revenue Drivers",
        "🧠 Customer Intelligence (RFM + K-Means)",
        "📉 Declining-Activity Detection",
        "💡 Strategic Recommendations",
        "🔍 Sales Anomaly Detection",
        "📋 Data Quality & Audit Log",
        "📥 Filtered Data Exports",
    ]
    for page in expected_pages:
        assert page in PAGES


def test_all_pages_dispatch_without_exception(mock_dashboard_data):
    sales_df, customer_df, cancellations_df, logger, guest_metrics = mock_dashboard_data
    # Execute every registered page function to verify no runtime syntax or logic crashes
    for page_name, render_func in PAGES.items():
        try:
            render_func(sales_df, customer_df, guest_metrics, logger, cancellations_df)
        except Exception as e:
            pytest.fail(f"Page '{page_name}' failed to render: {e}")
