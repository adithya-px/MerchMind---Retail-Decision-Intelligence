"""
API tests for MerchMind FastAPI endpoints.
Uses an uploaded real transaction CSV (not dashboard mock numbers).
"""

import io
import pytest
from fastapi.testclient import TestClient

from backend import main as backend_main
from backend.main import app, DataStore


def build_sample_csv() -> bytes:
    """Construct a schema-valid retail file with distinct RFM cohorts for k=4 clustering."""
    header = "InvoiceNo,StockCode,Description,Quantity,InvoiceDate,UnitPrice,CustomerID,Country"
    rows = [header]

    def add(invoice, stock, desc, qty, date, price, customer, country):
        rows.append(f"{invoice},{stock},{desc},{qty},{date},{price},{customer},{country}")

    # Champions: recent, frequent, high monetary
    for i, customer in enumerate((101, 102, 103)):
        for n, date in enumerate(("2011-05-02 09:00:00", "2011-05-20 11:00:00", "2011-06-10 14:00:00", "2011-06-28 10:00:00")):
            add(f"51{customer}{n}", "85123A", "WHITE HEART T-LIGHT", 20 + i, date, 12.50, customer, "United Kingdom")

    # Loyal / moderate: medium recency and spend
    for i, customer in enumerate((104, 105, 106)):
        for n, date in enumerate(("2011-04-05 10:00:00", "2011-05-15 12:00:00", "2011-06-18 16:00:00")):
            add(f"52{customer}{n}", "71053", "WHITE METAL LANTERN", 6 + i, date, 3.39, customer, "France")

    # At-risk: historically valuable, last purchase is old
    for i, customer in enumerate((107, 108, 109)):
        for n, date in enumerate(("2011-01-08 09:00:00", "2011-01-22 11:00:00", "2011-02-04 13:00:00")):
            add(f"53{customer}{n}", "84406B", "CREAM CUPID HEARTS", 15 + i, date, 8.00, customer, "Germany")

    # Inactive / low-value: few cheap old orders
    for i, customer in enumerate((110, 111, 112)):
        add(f"54{customer}0", "84029G", "KNITTED UNION FLAG HOT WATER BOTTLE", 1, "2011-01-12 10:00:00", 1.25, customer, "United Kingdom")
        if i == 0:
            add(f"54{customer}1", "21730", "GLASS STAR FROSTED T-LIGHT HOLDER", 1, "2011-02-01 09:00:00", 1.25, customer, "United Kingdom")

    add("599001", "21730", "GLASS STAR FROSTED T-LIGHT HOLDER", 24, "2011-05-15 08:30:00", 4.25, "", "United Kingdom")
    add("C500001", "85123A", "WHITE HEART T-LIGHT", -2, "2011-03-15 12:00:00", 2.55, 101, "United Kingdom")
    add("599999", "85123A", "WHITE HEART T-LIGHT", 80, "2011-05-01 10:00:00", 2.55, 101, "United Kingdom")
    return "\n".join(rows).encode("utf-8")


@pytest.fixture
def client():
    backend_main.STORE = DataStore()
    with TestClient(app) as test_client:
        yield test_client
    backend_main.STORE = DataStore()


@pytest.fixture
def loaded_client(client):
    response = client.post(
        "/api/dataset/upload",
        files={"file": ("sample_retail.csv", io.BytesIO(build_sample_csv()), "text/csv")},
    )
    assert response.status_code == 200, response.text
    assert response.json()["loaded"] is True
    return client


def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_dataset_status_empty_until_upload(client):
    response = client.get("/api/dataset/status")
    assert response.status_code == 200
    assert response.json()["loaded"] is False


def test_overview_requires_dataset(client):
    response = client.get("/api/overview")
    assert response.status_code == 400


def test_upload_rejects_invalid_extension(client):
    response = client.post(
        "/api/dataset/upload",
        files={"file": ("notes.txt", b"not a dataset", "text/plain")},
    )
    assert response.status_code == 400


def test_overview_endpoint(loaded_client):
    response = loaded_client.get("/api/overview")
    assert response.status_code == 200
    data = response.json()
    assert data["kpis"]["total_positive_sales"] > 0
    assert data["kpis"]["distinct_invoices"] > 0
    assert "monthly_trend" in data
    assert "daily_trend" in data
    assert data["insights"]


def test_sales_analytics_endpoint(loaded_client):
    response = loaded_client.get("/api/sales")
    assert response.status_code == 200
    data = response.json()
    assert data["top_products_revenue"]
    assert data["country_breakdown"]
    assert "pareto" in data
    assert data["hourly_trend"] or data["dow_trend"]


def test_country_filter_changes_kpis(loaded_client):
    all_kpis = loaded_client.get("/api/overview").json()["kpis"]
    uk = loaded_client.get("/api/overview?countries=United Kingdom").json()["kpis"]
    assert uk["total_positive_sales"] <= all_kpis["total_positive_sales"]
    assert uk["total_positive_sales"] > 0


def test_customer_segments_endpoint(loaded_client):
    response = loaded_client.get("/api/customer-segments?k=4")
    assert response.status_code == 200
    data = response.json()
    assert len(data["profiles"]) == 4
    assert data["pca_points"]
    assert data["cohort_sample"]
    assert data["metadata"]["n_clusters"] == 4


def test_model_diagnostics_endpoint(loaded_client):
    response = loaded_client.get("/api/model-diagnostics")
    assert response.status_code == 200
    data = response.json()
    assert len(data["evaluations"]) >= 2
    assert data["best_k"] >= 2


def test_declining_customers_endpoint(loaded_client):
    response = loaded_client.get("/api/declining-customers")
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert "flagged_accounts" in data


def test_recommendations_endpoint(loaded_client):
    response = loaded_client.get("/api/recommendations?k=4")
    assert response.status_code == 200
    data = response.json()
    assert data["playbooks"]
    assert data["playbooks"][0]["actions"]


def test_anomalies_endpoint(loaded_client):
    response = loaded_client.get("/api/anomalies")
    assert response.status_code == 200
    data = response.json()
    assert "total_anomalies" in data
    assert "daily_series" in data


def test_audit_log_endpoint(loaded_client):
    response = loaded_client.get("/api/audit-log")
    assert response.status_code == 200
    data = response.json()
    assert data["audit_trail"]
    assert "guest_metrics" in data


def test_csv_export_endpoint(loaded_client):
    response = loaded_client.get("/api/export/sales")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "InvoiceNo" in response.text


def test_monthly_export_endpoint(loaded_client):
    response = loaded_client.get("/api/export/monthly")
    assert response.status_code == 200
    assert "PositiveSales" in response.text
