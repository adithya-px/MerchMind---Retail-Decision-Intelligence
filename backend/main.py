"""
RetailPulse — FastAPI Decision Intelligence Backend.
Exposes high-performance REST APIs for dataset ingestion, sales analytics,
RFM customer segmentation, anomaly detection, audit logs, and CSV exports.
"""

import io
import os
import sys
from pathlib import Path
from typing import Optional, Any

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import numpy as np
import pandas as pd
from fastapi import FastAPI, File, UploadFile, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from src.config import (
    DEFAULT_RAW_CSV,
    DEFAULT_RAW_EXCEL,
    PROCESSED_DATA_DIR,
    COL_COUNTRY,
    COL_DATE,
    COL_CUST,
    COL_INVOICE,
    COL_LINE_REVENUE,
    DEFAULT_K_CLUSTERS,
    RANDOM_SEED,
    DEFAULT_RECENT_WINDOW_DAYS,
    DEFAULT_PRIOR_WINDOW_DAYS,
    MIN_TRANSACTIONS_FOR_DECLINE,
    MIN_PAST_SPEND_FOR_DECLINE,
)
from src.data_loader import load_raw_data
from src.cleaning import run_cleaning_pipeline
from src.sales_analytics import (
    filter_data,
    compute_kpis,
    compute_monthly_trend,
    compute_daily_trend,
    compute_pareto_concentration,
    what_drives_revenue_analysis,
    top_products,
    top_countries_by_revenue,
    compute_weekday_hourly_distribution,
    generate_sales_insights,
)
from src.customer_segmentation import (
    compute_rfm_table,
    fit_kmeans_clustering,
    evaluate_candidate_k,
)
from src.declining_activity import detect_declining_customers
from src.anomaly_detection import detect_sales_anomalies
from src.recommendations import generate_recommendations


# ---------------------------------------------------------
# Application & State
# ---------------------------------------------------------
app = FastAPI(
    title="RetailPulse Decision Intelligence API",
    description="High-performance analytics & ML backend for retail customer intelligence.",
    version="2.0.0",
)

FRONTEND_ORIGINS = [
    origin for origin in [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        os.environ.get("FRONTEND_ORIGIN", ""),
    ]
    if origin
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def json_safe(obj: Any) -> Any:
    """Convert numpy/pandas values into JSON-serializable Python types."""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return {str(k): json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [json_safe(v) for v in obj]
    if isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        value = float(obj)
        if np.isnan(value) or np.isinf(value):
            return None
        return value
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    if isinstance(obj, (pd.Timedelta,)):
        return str(obj)
    try:
        if pd.isna(obj):
            return None
    except (ValueError, TypeError):
        pass
    if hasattr(obj, "item") and not isinstance(obj, (bytes, str)):
        try:
            return json_safe(obj.item())
        except (ValueError, AttributeError):
            pass
    return obj


def ok(payload: Any) -> JSONResponse:
    return JSONResponse(content=json_safe(payload))


class DataStore:
    def __init__(self):
        self.raw_bytes: Optional[bytes] = None
        self.filename: Optional[str] = None
        self.file_hash: Optional[str] = None
        self.sales_df: Optional[pd.DataFrame] = None
        self.cancellations_df: Optional[pd.DataFrame] = None
        self.customer_df: Optional[pd.DataFrame] = None
        self.audit_logger = None
        self.guest_metrics: Optional[dict] = None
        self.is_demo: bool = False

    def load_bytes(self, file_bytes: bytes, filename: str, is_demo: bool = False):
        raw_df, f_hash = load_raw_data(
            file_bytes,
            file_name=filename,
            use_cache=True,
            processed_dir=PROCESSED_DATA_DIR,
        )
        sales_df, cancellations_df, customer_df, audit_logger, guest_metrics = run_cleaning_pipeline(raw_df)
        
        self.raw_bytes = file_bytes
        self.filename = filename
        self.file_hash = f_hash
        self.sales_df = sales_df
        self.cancellations_df = cancellations_df
        self.customer_df = customer_df
        self.audit_logger = audit_logger
        self.guest_metrics = guest_metrics
        self.is_demo = is_demo

    def is_loaded(self) -> bool:
        return self.sales_df is not None and not self.sales_df.empty


STORE = DataStore()


def get_active_store() -> DataStore:
    return STORE


def require_loaded() -> DataStore:
    store = get_active_store()
    if not store.is_loaded():
        raise HTTPException(
            status_code=400,
            detail="No active dataset loaded. Upload a CSV/XLSX file or load the benchmark dataset.",
        )
    return store


def apply_cohort_filters(
    sales_df: pd.DataFrame,
    customer_df: pd.DataFrame,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    countries: Optional[str] = None,
):
    s_dt = pd.to_datetime(start_date) if start_date else None
    e_dt = pd.to_datetime(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1) if end_date else None
    
    country_list = None
    if countries and countries != "All":
        country_list = [c.strip() for c in countries.split(",") if c.strip()]
        if "All" in country_list:
            country_list = None

    filtered_sales = filter_data(sales_df, start_date=s_dt, end_date=e_dt, countries=country_list)
    filtered_customer = filter_data(customer_df, start_date=s_dt, end_date=e_dt, countries=country_list)
    return filtered_sales, filtered_customer


# ---------------------------------------------------------
# Health & Dataset Management Endpoints
# ---------------------------------------------------------
@app.get("/api/health")
def health_check():
    return ok({"status": "healthy", "service": "RetailPulse API", "version": "2.0.0"})


@app.get("/api/dataset/status")
def dataset_status():
    store = get_active_store()
    if not store.is_loaded():
        return {
            "loaded": False,
            "filename": None,
            "hash": None,
            "sales_rows": 0,
            "customer_rows": 0,
            "cancellations_rows": 0,
            "min_date": None,
            "max_date": None,
            "countries": [],
            "is_demo": False,
        }

    min_d = str(store.sales_df[COL_DATE].min().date())
    max_d = str(store.sales_df[COL_DATE].max().date())
    countries = ["All"] + sorted([str(c) for c in store.sales_df[COL_COUNTRY].dropna().unique()])

    return {
        "loaded": True,
        "filename": store.filename,
        "hash": store.file_hash,
        "sales_rows": len(store.sales_df),
        "customer_rows": len(store.customer_df),
        "cancellations_rows": len(store.cancellations_df),
        "min_date": min_d,
        "max_date": max_d,
        "countries": countries,
        "is_demo": store.is_demo,
    }


@app.post("/api/dataset/upload")
async def upload_dataset(file: UploadFile = File(...)):
    if not file.filename.lower().endswith((".csv", ".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Invalid file format. Upload .csv, .xlsx, or .xls file.")

    content = await file.read()
    try:
        STORE.load_bytes(content, file.filename, is_demo=False)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to ingest and clean dataset: {str(e)}")

    return dataset_status()


@app.post("/api/dataset/demo")
def load_demo_dataset():
    if os.path.exists(DEFAULT_RAW_CSV):
        with open(DEFAULT_RAW_CSV, "rb") as f:
            STORE.load_bytes(f.read(), "Online Retail.csv (Demo Benchmark)", is_demo=True)
    elif os.path.exists(DEFAULT_RAW_EXCEL):
        with open(DEFAULT_RAW_EXCEL, "rb") as f:
            STORE.load_bytes(f.read(), "Online Retail.xlsx (Demo Benchmark)", is_demo=True)
    else:
        raise HTTPException(status_code=404, detail="Default benchmark dataset file not found on disk.")

    return dataset_status()


@app.post("/api/dataset/reset")
def reset_dataset():
    global STORE
    STORE = DataStore()
    return {"loaded": False, "message": "Dataset reset successfully."}


# ---------------------------------------------------------
# Executive Overview & KPI Endpoints
# ---------------------------------------------------------
@app.get("/api/overview")
def get_executive_overview(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    countries: Optional[str] = None,
):
    store = require_loaded()

    filtered_sales, filtered_customer = apply_cohort_filters(
        store.sales_df, store.customer_df, start_date, end_date, countries
    )

    kpis = compute_kpis(filtered_sales)
    _, pareto_share = compute_pareto_concentration(filtered_customer)
    drivers = what_drives_revenue_analysis(filtered_sales)
    insights = generate_sales_insights(kpis, pareto_share, drivers, store.guest_metrics)

    monthly_df = compute_monthly_trend(filtered_sales)
    monthly_series = []
    if not monthly_df.empty:
        monthly_df = monthly_df.fillna(0.0)
        for _, row in monthly_df.iterrows():
            monthly_series.append({
                "YearMonth": str(row["YearMonth"]),
                "PositiveSales": round(float(row["PositiveSales"]), 2),
                "Orders": int(row["Orders"]),
                "MoM_Growth_Pct": round(float(row["MoM_Growth_Pct"]), 1),
            })

    daily_df = compute_daily_trend(filtered_sales)
    daily_series = []
    if not daily_df.empty:
        daily_df = daily_df.fillna(0.0)
        for _, row in daily_df.iterrows():
            daily_series.append({
                "Date": str(row["Date"]),
                "PositiveSales": round(float(row["PositiveSales"]), 2),
                "Orders": int(row.get("Orders", 0)),
            })

    return ok({
        "kpis": kpis,
        "insights": insights,
        "pareto_share": pareto_share,
        "drivers": drivers,
        "monthly_trend": monthly_series,
        "daily_trend": daily_series,
        "filtered_volume": {
            "sales_rows": len(filtered_sales),
            "customer_rows": len(filtered_customer),
        },
    })


# ---------------------------------------------------------
# Sales Drivers & Catalog Analytics
# ---------------------------------------------------------
@app.get("/api/sales")
def get_sales_analytics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    countries: Optional[str] = None,
):
    store = require_loaded()

    filtered_sales, filtered_customer = apply_cohort_filters(
        store.sales_df, store.customer_df, start_date, end_date, countries
    )

    drivers = what_drives_revenue_analysis(filtered_sales)
    pareto_curve, pareto_share = compute_pareto_concentration(filtered_customer)

    # Format Pareto Curve (sample 50 points for smooth charting)
    pareto_points = []
    if not pareto_curve.empty:
        step = max(1, len(pareto_curve) // 50)
        sample = pareto_curve.iloc[::step].copy()
        if len(sample) == 0 or sample.iloc[-1]["CustomerPercentile"] < 100:
            sample = pd.concat([sample, pareto_curve.iloc[[-1]]])
        for _, row in sample.iterrows():
            pareto_points.append({
                "customer_pct": round(float(row["CustomerPercentile"]), 1),
                "revenue_pct": round(float(row["CumulativeSharePct"]), 1),
            })

    # Catalog & Country Breakdown
    top_rev_products = top_products(filtered_sales, by="LineRevenue", top_n=10).to_dict(orient="records")
    top_qty_products = top_products(filtered_sales, by="Quantity", top_n=10).to_dict(orient="records")
    country_breakdown = top_countries_by_revenue(filtered_sales, top_n=12).to_dict(orient="records")

    daily_df = compute_daily_trend(filtered_sales)
    daily_series = []
    if not daily_df.empty:
        for _, row in daily_df.fillna(0.0).iterrows():
            daily_series.append({
                "Date": str(row["Date"]),
                "PositiveSales": round(float(row["PositiveSales"]), 2),
                "Orders": int(row.get("Orders", 0)),
            })

    hourly_trend = []
    if not filtered_sales.empty and "Hour" in filtered_sales.columns:
        hourly = (
            filtered_sales.groupby("Hour")[COL_LINE_REVENUE]
            .sum()
            .reset_index()
            .sort_values("Hour")
        )
        hourly_trend = [
            {"hour": int(row["Hour"]), "revenue": round(float(row[COL_LINE_REVENUE]), 2)}
            for _, row in hourly.iterrows()
        ]

    dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    dow_trend = []
    if not filtered_sales.empty and "DayOfWeek" in filtered_sales.columns:
        dow = filtered_sales.groupby("DayOfWeek")[COL_LINE_REVENUE].sum()
        for day in dow_order:
            if day in dow.index:
                dow_trend.append({"day": day, "revenue": round(float(dow[day]), 2)})

    top_customers = []
    if not filtered_customer.empty:
        cust = (
            filtered_customer.groupby(COL_CUST)
            .agg(revenue=(COL_LINE_REVENUE, "sum"), orders=(COL_INVOICE, "nunique"))
            .reset_index()
            .sort_values("revenue", ascending=False)
            .head(10)
        )
        top_customers = [
            {
                "customer_id": str(row[COL_CUST]),
                "revenue": round(float(row["revenue"]), 2),
                "orders": int(row["orders"]),
            }
            for _, row in cust.iterrows()
        ]

    heatmap_records = []
    heatmap_df = compute_weekday_hourly_distribution(filtered_sales)
    if not heatmap_df.empty:
        long_df = heatmap_df.stack().reset_index()
        long_df.columns = ["DayOfWeek", "Hour", "PositiveSales"]
        heatmap_records = [
            {
                "DayOfWeek": str(row["DayOfWeek"]),
                "Hour": int(row["Hour"]),
                "PositiveSales": round(float(row["PositiveSales"]), 2),
            }
            for _, row in long_df.iterrows()
        ]

    return ok({
        "drivers": drivers,
        "pareto": {
            "top_20_share_pct": round(float(pareto_share), 2),
            "curve": pareto_points,
        },
        "top_products_revenue": top_rev_products,
        "top_products_quantity": top_qty_products,
        "country_breakdown": country_breakdown,
        "daily_trend": daily_series,
        "hourly_trend": hourly_trend,
        "dow_trend": dow_trend,
        "top_customers": top_customers,
        "demand_timing": heatmap_records,
    })


# ---------------------------------------------------------
# Customer Segmentation (RFM + K-Means)
# ---------------------------------------------------------
@app.get("/api/customer-segments")
def get_customer_segments(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    countries: Optional[str] = None,
    k: int = Query(DEFAULT_K_CLUSTERS, ge=2, le=8),
    reference_date: Optional[str] = None,
):
    store = require_loaded()

    _, filtered_customer = apply_cohort_filters(
        store.sales_df, store.customer_df, start_date, end_date, countries
    )

    if filtered_customer.empty:
        raise HTTPException(status_code=400, detail="No identified customers available under active filters.")

    ref_dt = pd.to_datetime(reference_date) if reference_date else None
    rfm_df = compute_rfm_table(filtered_customer, reference_date=ref_dt)

    if len(rfm_df) < k:
        raise HTTPException(status_code=400, detail=f"Insufficient customers ({len(rfm_df)}) to fit {k} clusters.")

    clustered_df, profiles, metadata = fit_kmeans_clustering(rfm_df, n_clusters=k, random_state=RANDOM_SEED)

    # Convert profiles to clean dict list
    profiles_list = profiles.to_dict(orient="records")

    # Sample PCA points for 2D visualization (up to 600 points)
    sample_df = clustered_df.sample(min(600, len(clustered_df)), random_state=RANDOM_SEED) if len(clustered_df) > 600 else clustered_df
    pca_points = []
    for _, row in sample_df.iterrows():
        pca_points.append({
            "CustomerID": str(row["CustomerID"]),
            "PCA1": round(float(row["PCA1"]), 3),
            "PCA2": round(float(row["PCA2"]), 3),
            "SegmentName": str(row["SegmentName"]),
            "Recency": float(row["Recency"]),
            "Frequency": int(row["Frequency"]),
            "Monetary": round(float(row["Monetary"]), 2),
        })

    # Customer cohort sample (top 100 by spend)
    cohort_sample = []
    top_cohort = clustered_df.sort_values(by="Monetary", ascending=False).head(100)
    for _, row in top_cohort.iterrows():
        cohort_sample.append({
            "CustomerID": str(row["CustomerID"]),
            "SegmentName": str(row["SegmentName"]),
            "Recency": float(row["Recency"]),
            "Frequency": int(row["Frequency"]),
            "Monetary": round(float(row["Monetary"]), 2),
            "AvgOrderValue": round(float(row["AvgOrderValue"]), 2),
            "FirstPurchase": str(row["FirstPurchase"].date()) if pd.notna(row["FirstPurchase"]) else "",
            "LastPurchase": str(row["LastPurchase"].date()) if pd.notna(row["LastPurchase"]) else "",
        })

    return ok({
        "metadata": metadata,
        "profiles": profiles_list,
        "pca_points": pca_points,
        "cohort_sample": cohort_sample,
    })


@app.get("/api/model-diagnostics")
def get_model_diagnostics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    countries: Optional[str] = None,
):
    store = require_loaded()

    _, filtered_customer = apply_cohort_filters(
        store.sales_df, store.customer_df, start_date, end_date, countries
    )

    if filtered_customer.empty:
        raise HTTPException(status_code=400, detail="No customer records available.")

    rfm_df = compute_rfm_table(filtered_customer)
    eval_df, best_k = evaluate_candidate_k(rfm_df)

    eval_records = []
    for _, row in eval_df.iterrows():
        eval_records.append({
            "k": int(row["k"]),
            "Inertia": round(float(row["Inertia"]), 1),
            "SilhouetteScore": round(float(row["SilhouetteScore"]), 3),
        })

    return ok({
        "evaluations": eval_records,
        "best_k": best_k,
    })


# ---------------------------------------------------------
# Declining Activity & Retention Playbooks
# ---------------------------------------------------------
@app.get("/api/declining-customers")
def get_declining_customers(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    countries: Optional[str] = None,
    recent_window_days: int = Query(DEFAULT_RECENT_WINDOW_DAYS, ge=15, le=180),
    prior_window_days: int = Query(DEFAULT_PRIOR_WINDOW_DAYS, ge=30, le=365),
    min_prior_orders: int = Query(MIN_TRANSACTIONS_FOR_DECLINE, ge=1, le=10),
    min_prior_spend: float = Query(MIN_PAST_SPEND_FOR_DECLINE, ge=10.0, le=1000.0),
):
    store = require_loaded()

    _, filtered_customer = apply_cohort_filters(
        store.sales_df, store.customer_df, start_date, end_date, countries
    )

    declining_df, summary = detect_declining_customers(
        filtered_customer,
        recent_window_days=recent_window_days,
        prior_window_days=prior_window_days,
        min_prior_orders=min_prior_orders,
        min_prior_spend=min_prior_spend,
    )

    flagged_list = []
    if not declining_df.empty:
        for _, row in declining_df.head(100).iterrows():
            cadence = row.get("MedianCadenceDays", 0.0)
            flagged_list.append({
                "CustomerID": str(row["CustomerID"]),
                "RecentSpend": round(float(row.get("RecentSpend", 0.0) or 0.0), 2),
                "PriorSpend": round(float(row.get("PriorSpend", 0.0) or 0.0), 2),
                "SpendDrop": round(float(row.get("SpendDrop", 0.0) or 0.0), 2),
                "VelocityDropPct": round(float(row.get("SpendDropPct", 0.0) or 0.0), 1),
                "DaysSinceLastPurchase": float(row.get("DaysSinceLastPurchase", 0.0) or 0.0),
                "AvgInterPurchaseDays": round(float(cadence) if pd.notna(cadence) else 0.0, 1),
                "Reason": str(row.get("DeclineReason", "Velocity drop")),
            })

    return ok({
        "summary": summary,
        "flagged_accounts": flagged_list,
    })


@app.get("/api/recommendations")
def get_strategic_recommendations(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    countries: Optional[str] = None,
    k: int = Query(DEFAULT_K_CLUSTERS, ge=2, le=8),
):
    store = require_loaded()

    _, filtered_customer = apply_cohort_filters(
        store.sales_df, store.customer_df, start_date, end_date, countries
    )

    rfm_df = compute_rfm_table(filtered_customer)
    if len(rfm_df) < k:
        raise HTTPException(status_code=400, detail="Insufficient customer volume.")

    _, profiles, _ = fit_kmeans_clustering(rfm_df, n_clusters=k, random_state=RANDOM_SEED)
    _, dec_summary = detect_declining_customers(filtered_customer)

    playbooks = generate_recommendations(profiles, dec_summary)
    return ok({"playbooks": playbooks})


# ---------------------------------------------------------
# Anomaly Detection & Audit Log
# ---------------------------------------------------------
@app.get("/api/anomalies")
def get_anomalies(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    countries: Optional[str] = None,
    window: int = Query(14, ge=7, le=90),
    threshold: float = Query(2.5, ge=1.0, le=5.0),
):
    store = require_loaded()

    filtered_sales, _ = apply_cohort_filters(
        store.sales_df, store.customer_df, start_date, end_date, countries
    )

    daily_df, summary = detect_sales_anomalies(
        filtered_sales,
        window_days=window,
        multiplier=threshold,
    )

    daily_chart = []
    anomaly_events = []
    if not daily_df.empty:
        daily_df = daily_df.fillna(0.0)
        for _, row in daily_df.iterrows():
            item = {
                "Date": str(row["Date"]),
                "Sales": round(float(row["PositiveSales"]), 2),
                "Baseline": round(float(row["Baseline"]), 2) if "Baseline" in row else 0.0,
                "LowerBound": round(float(row["LowerBound"]), 2) if "LowerBound" in row else 0.0,
                "UpperBound": round(float(row["UpperBound"]), 2) if "UpperBound" in row else 0.0,
                "IsAnomaly": bool(row["IsAnomaly"]),
                "AnomalyType": str(row["AnomalyType"]),
            }
            daily_chart.append(item)
            if row["IsAnomaly"]:
                anomaly_events.append(item)

    return ok({
        "summary": summary,
        "total_anomalies": len(anomaly_events),
        "anomalies": anomaly_events,
        "daily_series": daily_chart,
    })


@app.get("/api/audit-log")
def get_audit_log():
    store = require_loaded()

    audit_records = []
    if store.audit_logger:
        audit_df = store.audit_logger.to_dataframe()
        audit_records = audit_df.to_dict(orient="records")

    cancellations_summary = {
        "total_cancellations": len(store.cancellations_df),
        "total_negative_value": round(float(store.cancellations_df["LineRevenue"].sum()), 2)
        if "LineRevenue" in store.cancellations_df.columns
        else 0.0,
    }

    return ok({
        "audit_trail": audit_records,
        "guest_metrics": store.guest_metrics,
        "cancellations_summary": cancellations_summary,
    })


# ---------------------------------------------------------
# Filter-Synchronized CSV Exports
# ---------------------------------------------------------
@app.get("/api/export/{export_type}")
def export_csv(
    export_type: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    countries: Optional[str] = None,
    k: int = Query(DEFAULT_K_CLUSTERS, ge=2, le=8),
):
    store = require_loaded()

    filtered_sales, filtered_customer = apply_cohort_filters(
        store.sales_df, store.customer_df, start_date, end_date, countries
    )

    stream = io.StringIO()

    if export_type == "sales":
        filtered_sales.to_csv(stream, index=False)
        filename = "retailpulse_filtered_sales.csv"
    elif export_type == "monthly":
        compute_monthly_trend(filtered_sales).to_csv(stream, index=False)
        filename = "retailpulse_monthly_sales.csv"
    elif export_type == "segments":
        rfm_df = compute_rfm_table(filtered_customer)
        if len(rfm_df) < k:
            raise HTTPException(status_code=400, detail=f"Insufficient customers ({len(rfm_df)}) to export {k} clusters.")
        clustered_df, _, _ = fit_kmeans_clustering(rfm_df, n_clusters=k, random_state=RANDOM_SEED)
        clustered_df.to_csv(stream, index=False)
        filename = f"retailpulse_customer_segments_k{k}.csv"
    elif export_type == "declining":
        declining_df, _ = detect_declining_customers(filtered_customer)
        declining_df.to_csv(stream, index=False)
        filename = "retailpulse_declining_accounts.csv"
    elif export_type == "anomalies":
        daily_df, _ = detect_sales_anomalies(filtered_sales)
        anomalies_df = daily_df[daily_df["IsAnomaly"]] if not daily_df.empty else pd.DataFrame()
        anomalies_df.to_csv(stream, index=False)
        filename = "retailpulse_sales_anomalies.csv"
    else:
        raise HTTPException(status_code=400, detail=f"Invalid export type: {export_type}")

    stream.seek(0)
    return StreamingResponse(
        iter([stream.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
