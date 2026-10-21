"""
RetailPulse — Sales Intelligence & Customer Insights Dashboard.
Main entry point orchestrating data ingestion, pipeline caching,
global sidebar filters, and modular page dispatching.
"""

import os
import sys
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
import pandas as pd

from src.config import (
    DEFAULT_RAW_CSV,
    DEFAULT_RAW_EXCEL,
    PROCESSED_DATA_DIR,
    COL_COUNTRY,
    COL_DATE,
)
from src.data_loader import load_raw_data
from src.cleaning import run_cleaning_pipeline
from src.sales_analytics import filter_data

# Page modules
from dashboards.pages import (
    overview_page,
    sales_page,
    clustering_page,
    declining_page,
    recommendations_page,
    anomaly_page,
    audit_page,
    exports_page,
)

# ---------------------------------------------------------
# Modular Page Registry
# ---------------------------------------------------------
# To add a new page: add one page module in dashboards/pages/ and one line below!
PAGES = {
    "📊 Executive Overview": lambda s, c, g, a, can: overview_page.render(s, c, g),
    "📈 Sales & Revenue Drivers": lambda s, c, g, a, can: sales_page.render(s, c, g),
    "🧠 Customer Intelligence (RFM + K-Means)": lambda s, c, g, a, can: clustering_page.render(s, c, g),
    "📉 Declining-Activity Detection": lambda s, c, g, a, can: declining_page.render(s, c, g),
    "💡 Strategic Recommendations": lambda s, c, g, a, can: recommendations_page.render(s, c, g),
    "🔍 Sales Anomaly Detection": lambda s, c, g, a, can: anomaly_page.render(s, c, g),
    "📋 Data Quality & Audit Log": lambda s, c, g, a, can: audit_page.render(s, c, g, a, can),
    "📥 Filtered Data Exports": lambda s, c, g, a, can: exports_page.render(s, c, g),
}


# ---------------------------------------------------------
# Cached Ingestion & Cleaning Pipeline
# ---------------------------------------------------------
@st.cache_data(show_spinner="Loading and cleaning transaction dataset...", max_entries=4)
def get_cleaned_datasets(source_file_bytes: bytes, file_name: str):
    """Parses raw input (CSV/Excel), caches Parquet by hash, runs cleaning pipeline."""
    raw_df, f_hash = load_raw_data(
        source_file_bytes,
        file_name=file_name,
        use_cache=True,
        processed_dir=PROCESSED_DATA_DIR,
    )
    sales_df, cancellations_df, customer_df, audit_logger, guest_metrics = run_cleaning_pipeline(raw_df)
    return sales_df, cancellations_df, customer_df, audit_logger, guest_metrics, f_hash


def main():
    # Page Configuration & Styling
    st.set_page_config(
        page_title="RetailPulse — Sales Intelligence & Customer Insights",
        page_icon="🛍️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }
        .stApp {
            background-color: #0B0F19;
            color: #F3F4F6;
        }
        div[data-testid="stMetric"] {
            background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 16px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
        }
        div[data-testid="stMetricLabel"] p {
            color: #94A3B8 !important;
            font-weight: 500;
            font-size: 0.875rem;
        }
        div[data-testid="stMetricValue"] div {
            color: #F8FAFC !important;
            font-weight: 700;
        }
        section[data-testid="stSidebar"] {
            background-color: #0F172A;
            border-right: 1px solid #1E293B;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Sidebar Controls & File Upload
    st.sidebar.title("🛍️ RetailPulse")
    st.sidebar.caption("Sales Intelligence & Customer Insights")

    # Dataset Source Selection
    st.sidebar.markdown("### 📁 Dataset Source")
    uploaded_file = st.sidebar.file_uploader(
        "Upload Excel (.xlsx) or CSV",
        type=["csv", "xlsx", "xls"],
        help="Support official UCI Online Retail Excel (.xlsx) and CSV exports.",
    )

    file_bytes = None
    file_name = None

    if uploaded_file is not None:
        file_bytes = uploaded_file.getvalue()
        file_name = uploaded_file.name
    else:
        # Fallback to local default files
        if os.path.exists(DEFAULT_RAW_CSV):
            file_name = "Online Retail.csv"
            with open(DEFAULT_RAW_CSV, "rb") as f:
                file_bytes = f.read()
        elif os.path.exists(DEFAULT_RAW_EXCEL):
            file_name = "Online Retail.xlsx"
            with open(DEFAULT_RAW_EXCEL, "rb") as f:
                file_bytes = f.read()

    if file_bytes is None:
        st.error("No dataset available! Please upload an Excel or CSV file in the sidebar to begin.")
        st.stop()

    # Execute Pipeline
    try:
        sales_df, cancellations_df, customer_df, audit_logger, guest_metrics, dataset_hash = get_cleaned_datasets(
            file_bytes, file_name
        )
    except Exception as e:
        st.error(f"❌ Error ingesting dataset: {e}")
        st.stop()

    st.sidebar.success(f"Loaded: `{file_name}` (ID: `{dataset_hash}`)")

    # Global Unified Filters
    st.sidebar.markdown("### 🔎 Unified Filters")

    # Date range filter
    min_d = sales_df[COL_DATE].min().date()
    max_d = sales_df[COL_DATE].max().date()
    selected_dates = st.sidebar.date_input(
        "Date Range",
        value=(min_d, max_d),
        min_value=min_d,
        max_value=max_d,
    )

    start_date = None
    end_date = None
    if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
        start_date, end_date = selected_dates
    elif isinstance(selected_dates, tuple) and len(selected_dates) == 1:
        start_date = selected_dates[0]
        end_date = max_d
    else:
        start_date, end_date = min_d, max_d

    # Country filter
    all_countries = ["All"] + sorted(list(sales_df[COL_COUNTRY].dropna().unique()))
    selected_countries = st.sidebar.multiselect(
        "Countries",
        options=all_countries,
        default=["All"],
    )

    # Apply global filters uniformly
    filtered_sales_df = filter_data(
        sales_df,
        start_date=pd.to_datetime(start_date) if start_date else None,
        end_date=pd.to_datetime(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1) if end_date else None,
        countries=selected_countries,
    )

    # Apply identical filters to customer cohort
    filtered_customer_df = filter_data(
        customer_df,
        start_date=pd.to_datetime(start_date) if start_date else None,
        end_date=pd.to_datetime(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1) if end_date else None,
        countries=selected_countries,
    )

    st.sidebar.markdown("---")

    # Navigation Selection
    st.sidebar.markdown("### 🧭 Navigation")
    selected_page_name = st.sidebar.radio(
        "Select Section",
        list(PAGES.keys()),
        index=0,
    )

    # Page Dispatch
    page_render_func = PAGES[selected_page_name]
    page_render_func(
        filtered_sales_df,
        filtered_customer_df,
        guest_metrics,
        audit_logger,
        cancellations_df,
    )


if __name__ == "__main__":
    main()