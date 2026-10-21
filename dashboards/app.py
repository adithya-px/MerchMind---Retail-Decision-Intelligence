"""
RetailPulse — Sales Intelligence & Customer Insights Dashboard.
Main entry point orchestrating interactive dataset ingestion (CSV/Excel),
automated data cleaning, ML model training, and cohesive decision intelligence.
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
from src.sales_analytics import (
    filter_data,
    compute_kpis,
    compute_pareto_concentration,
    what_drives_revenue_analysis,
    generate_sales_insights,
)

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
# Modular Page Registry (Maintained for full test compatibility)
# ---------------------------------------------------------
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
@st.cache_data(show_spinner="Ingesting, validating, and cleaning transaction dataset...", max_entries=4)
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


def render_upload_hero_portal():
    """Renders a state-of-the-art onboarding & dataset upload portal."""
    st.markdown(
        """
        <div class="hero-card">
            <div style="display: flex; align-items: center; gap: 14px; margin-bottom: 10px;">
                <span style="font-size: 2.2rem;">🛍️</span>
                <div>
                    <h1 style="margin: 0; font-size: 2.2rem; font-weight: 800; color: #F8FAFC; letter-spacing: -0.02em;">
                        RetailPulse <span style="background: linear-gradient(135deg, #38BDF8 0%, #818CF8 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">Decision Intelligence</span>
                    </h1>
                    <p style="margin: 4px 0 0 0; color: #94A3B8; font-size: 1.05rem;">
                        Enterprise customer analytics: Ingest raw transaction logs, train unsupervised RFM K-Means models,
                        decompose revenue drivers, detect cadence churn risks, and access actionable marketing playbooks.
                    </p>
                </div>
            </div>
            <div style="margin-top: 14px; display: flex; flex-wrap: wrap; gap: 8px;">
                <span class="feature-pill">⚡ Ingestion Pipeline</span>
                <span class="feature-pill">🧠 K-Means Clustering (k=2..8)</span>
                <span class="feature-pill">📈 Driver Decomposition</span>
                <span class="feature-pill">📉 Velocity & Churn Alerts</span>
                <span class="feature-pill">🔍 30-Day Anomaly Detection</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_upload, col_demo = st.columns([1.2, 0.8], gap="large")

    with col_upload:
        st.markdown(
            """
            <div class="upload-box-wrapper">
                <h3 style="margin-top:0; color:#F8FAFC; font-size:1.25rem;">📂 Upload Your Transaction Dataset</h3>
                <p style="color:#94A3B8; font-size:0.875rem; margin-bottom:12px;">
                    Upload any retail sales log in <b>CSV</b> or <b>Excel (.xlsx, .xls)</b> format. The system automatically standardizes headers, validates schemas, isolates return anomalies, and fits ML segmentation models.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        hero_file = st.file_uploader(
            "Select or Drag & Drop transaction dataset",
            type=["csv", "xlsx", "xls"],
            key="hero_main_uploader",
            label_visibility="collapsed",
            help="Accepted formats: .csv, .xlsx, .xls (e.g. Online Retail, Shopify, WooCommerce, SAP/Oracle exports)",
        )
        if hero_file is not None:
            st.session_state["uploaded_file_bytes"] = hero_file.getvalue()
            st.session_state["uploaded_file_name"] = hero_file.name
            st.session_state["use_demo_data"] = False
            st.rerun()

        st.caption("🔒 Processing is performed locally with SHA-256 parquet hash caching.")

    with col_demo:
        st.markdown(
            """
            <div class="upload-box-wrapper">
                <h3 style="margin-top:0; color:#F8FAFC; font-size:1.25rem;">🧪 Benchmark Demonstration</h3>
                <p style="color:#94A3B8; font-size:0.875rem; margin-bottom:14px;">
                    Don't have a dataset file ready? Instantly explore RetailPulse using the industry benchmark <b>UCI Online Retail II</b> dataset.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("🚀 Load Online Retail Benchmark (500k+ rows)", type="primary", width="stretch"):
            st.session_state["use_demo_data"] = True
            st.rerun()

        st.markdown(
            """
            <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(148, 163, 184, 0.12); border-radius: 8px; padding: 10px 14px; margin-top: 12px; font-size: 0.825rem; color: #94A3B8;">
                <b style="color: #38BDF8;">Benchmark Includes:</b><br/>
                • 541,909 raw commercial transactions<br/>
                • 4,372 distinct buyer accounts across 38 countries<br/>
                • Full multi-year seasonality & cancellation records
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # Schema specification
    with st.expander("📋 Expected Dataset Schema & Compatibility Guide", expanded=False):
        st.markdown(
            """
            RetailPulse supports automated column alias standardization. Your CSV or Excel file should contain the following fields:

            | Standard Column | Accepted Aliases | Data Type | Mandatory? | Purpose in Model |
            | :--- | :--- | :--- | :---: | :--- |
            | **Invoice** | `InvoiceNo`, `OrderNumber`, `TransactionID` | String | Yes | Order grouping & frequency calculation |
            | **StockCode** | `ItemCode`, `ProductID`, `SKU` | String | Yes | Catalog & inventory performance |
            | **Description** | `ItemDescription`, `Title`, `ProductName` | String | Optional | Product identification & display |
            | **Quantity** | `Qty`, `ItemQuantity` | Integer | Yes | Volume, returns isolation, and revenue math |
            | **InvoiceDate** | `OrderDate`, `Date`, `Timestamp` | Datetime | Yes | Recency, monthly trends, anomaly baseline |
            | **Price** | `UnitPrice`, `ItemPrice`, `Rate` | Float | Yes | Monetary value calculation ($Q \times P$) |
            | **Customer ID** | `CustomerID`, `ClientID`, `BuyerID` | String/Int | Optional | RFM clustering (missing IDs retained as Guest) |
            | **Country** | `Market`, `Region`, `BillingCountry` | String | Optional | Geographic revenue driver analysis |
            """
        )

    # Architectural highlights
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        st.markdown(
            """
            <div class="feature-card">
                <h4 style="color:#38BDF8; margin-top:0;">🧠 Unsupervised Segmentation</h4>
                <p style="color:#94A3B8; font-size:0.875rem;">
                    Computes customer Recency, Frequency, and Monetary scores. Applies log1p skew transformation and StandardScaler, fitting K-Means across candidate clusters (k=2..8) with Silhouette & Elbow validation.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_f2:
        st.markdown(
            """
            <div class="feature-card">
                <h4 style="color:#818CF8; margin-top:0;">🎯 Revenue Drivers & Pareto</h4>
                <p style="color:#94A3B8; font-size:0.875rem;">
                    Decomposes sales into price-volume mix and identifies the 80/20 customer concentration. Evaluates catalog performance, peak weekday hours, and geographic market contributions.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_f3:
        st.markdown(
            """
            <div class="feature-card">
                <h4 style="color:#34D399; margin-top:0;">📉 Declining Activity & Anomalies</h4>
                <p style="color:#94A3B8; font-size:0.875rem;">
                    Detects customers exhibiting >50% velocity drop and purchase cadence deviations. 30-day rolling Z-score & IQR scans highlight revenue anomalies and return spikes.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def main():
    # Page Configuration & Clean Theming
    st.set_page_config(
        page_title="RetailPulse — Retail Decision Intelligence",
        page_icon="🛍️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Initialize Session State
    if "use_demo_data" not in st.session_state:
        st.session_state["use_demo_data"] = False
    if "uploaded_file_bytes" not in st.session_state:
        st.session_state["uploaded_file_bytes"] = None
    if "uploaded_file_name" not in st.session_state:
        st.session_state["uploaded_file_name"] = None

    # Modern Custom Styling
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
        
        .stApp {
            font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
            background-color: #0B0F19;
            color: #F1F5F9;
        }

        /* Hide Streamlit auto-generated multipage navigation menu */
        [data-testid="stSidebarNav"] {
            display: none !important;
        }

        /* Metric cards styling */
        div[data-testid="stMetric"] {
            background: linear-gradient(135deg, rgba(30, 41, 59, 0.75) 0%, rgba(15, 23, 42, 0.95) 100%);
            border: 1px solid rgba(148, 163, 184, 0.16);
            border-radius: 12px;
            padding: 14px 18px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
            transition: transform 0.15s ease, border-color 0.15s ease;
        }
        div[data-testid="stMetric"]:hover {
            border-color: rgba(56, 189, 248, 0.5);
            transform: translateY(-2px);
        }
        div[data-testid="stMetricLabel"] p {
            color: #94A3B8 !important;
            font-size: 0.825rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        div[data-testid="stMetricValue"] div {
            color: #38BDF8 !important;
            font-weight: 700;
            font-size: 1.55rem !important;
        }

        /* Top Nav Tab Styling */
        div[data-testid="stTabs"] button[role="tab"] {
            font-size: 0.925rem;
            font-weight: 600;
            padding: 8px 16px;
            color: #94A3B8;
            border-radius: 8px 8px 0 0;
            transition: all 0.2s ease;
        }
        div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
            color: #38BDF8 !important;
            border-bottom: 2px solid #38BDF8 !important;
            background: rgba(56, 189, 248, 0.06);
        }

        /* Sidebar Header & Brand */
        section[data-testid="stSidebar"] {
            border-right: 1px solid rgba(148, 163, 184, 0.12);
            background-color: #0F172A;
        }
        .brand-badge {
            display: inline-block;
            background: rgba(56, 189, 248, 0.12);
            color: #38BDF8;
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 700;
            margin-bottom: 6px;
            letter-spacing: 0.05em;
        }

        /* Hero & Portal Styling */
        .hero-card {
            background: linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.85) 100%);
            border: 1px solid rgba(56, 189, 248, 0.25);
            border-radius: 16px;
            padding: 28px 32px;
            box-shadow: 0 12px 35px rgba(0, 0, 0, 0.35);
            margin-bottom: 24px;
        }
        .feature-pill {
            background: rgba(56, 189, 248, 0.1);
            border: 1px solid rgba(56, 189, 248, 0.25);
            color: #38BDF8;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.78rem;
            font-weight: 600;
            display: inline-block;
        }
        .upload-box-wrapper {
            background: rgba(15, 23, 42, 0.5);
            border: 1px solid rgba(148, 163, 184, 0.14);
            border-radius: 12px;
            padding: 18px 20px 8px 20px;
            margin-bottom: 12px;
        }
        .feature-card {
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid rgba(148, 163, 184, 0.14);
            border-radius: 12px;
            padding: 16px 20px;
            height: 100%;
        }
        .telemetry-banner {
            background: linear-gradient(90deg, rgba(16, 185, 129, 0.1) 0%, rgba(56, 189, 248, 0.1) 100%);
            border: 1px solid rgba(56, 189, 248, 0.25);
            border-radius: 10px;
            padding: 10px 16px;
            margin-bottom: 18px;
        }
        .insight-card {
            background: rgba(15, 23, 42, 0.7);
            border-left: 4px solid #38BDF8;
            border-radius: 8px;
            padding: 12px 18px;
            margin-bottom: 16px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ---------------------------------------------------------
    # Resolve Active Dataset Source
    # ---------------------------------------------------------
    file_bytes = st.session_state.get("uploaded_file_bytes")
    file_name = st.session_state.get("uploaded_file_name")
    is_demo = False

    if file_bytes is None and st.session_state.get("use_demo_data", False):
        if os.path.exists(DEFAULT_RAW_CSV):
            file_name = "Online Retail.csv (Demo Benchmark)"
            with open(DEFAULT_RAW_CSV, "rb") as f:
                file_bytes = f.read()
            is_demo = True
        elif os.path.exists(DEFAULT_RAW_EXCEL):
            file_name = "Online Retail.xlsx (Demo Benchmark)"
            with open(DEFAULT_RAW_EXCEL, "rb") as f:
                file_bytes = f.read()
            is_demo = True

    # ---------------------------------------------------------
    # Sidebar: Brand & Dynamic Controls
    # ---------------------------------------------------------
    st.sidebar.markdown('<span class="brand-badge">DECISION INTELLIGENCE</span>', unsafe_allow_html=True)
    st.sidebar.title("🛍️ RetailPulse")
    st.sidebar.caption("Machine Learning & Customer Analytics")
    st.sidebar.markdown("---")

    # If no dataset loaded: show landing uploader
    if file_bytes is None:
        st.sidebar.markdown("### 📁 Dataset Ingestion")
        sidebar_file = st.sidebar.file_uploader(
            "Upload Transaction File",
            type=["csv", "xlsx", "xls"],
            key="sidebar_initial_uploader",
            help="Drop a transaction dataset (.csv, .xlsx, .xls) to train models and view insights.",
        )
        if sidebar_file is not None:
            st.session_state["uploaded_file_bytes"] = sidebar_file.getvalue()
            st.session_state["uploaded_file_name"] = sidebar_file.name
            st.session_state["use_demo_data"] = False
            st.rerun()

        if st.sidebar.button("🧪 Explore with Demo Data", width="stretch"):
            st.session_state["use_demo_data"] = True
            st.rerun()

        # Render Main Upload Hero Portal
        render_upload_hero_portal()
        st.stop()

    # ---------------------------------------------------------
    # Ingest, Validate & Run Cleaning Pipeline
    # ---------------------------------------------------------
    try:
        sales_df, cancellations_df, customer_df, audit_logger, guest_metrics, dataset_hash = get_cleaned_datasets(
            file_bytes, file_name
        )
    except Exception as e:
        st.error(f"❌ Error loading dataset: {e}")
        if st.button("🔄 Reset and Upload New File"):
            st.session_state["uploaded_file_bytes"] = None
            st.session_state["uploaded_file_name"] = None
            st.session_state["use_demo_data"] = False
            st.rerun()
        st.stop()

    # Sidebar: Active Dataset Info & Controls
    st.sidebar.markdown(
        f"""
        <div style="background: rgba(15, 23, 42, 0.85); border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 10px; padding: 12px 14px; margin-bottom: 12px;">
            <div style="color: #38BDF8; font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;">● Active Dataset</div>
            <div style="color: #F8FAFC; font-size: 0.92rem; font-weight: 600; margin: 4px 0; word-break: break-all;">{file_name}</div>
            <div style="color: #94A3B8; font-size: 0.78rem;">{len(file_bytes)/1024/1024:.2f} MB | {len(sales_df):,} sales rows</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_btn1, col_btn2 = st.sidebar.columns(2)
    with col_btn1:
        if st.button("🔄 Switch File", width="stretch", help="Upload a different dataset"):
            st.session_state["uploaded_file_bytes"] = None
            st.session_state["uploaded_file_name"] = None
            st.session_state["use_demo_data"] = False
            st.rerun()
    with col_btn2:
        if not is_demo:
            if st.button("🧪 Use Demo", width="stretch", help="Switch to benchmark Online Retail demo"):
                st.session_state["uploaded_file_bytes"] = None
                st.session_state["uploaded_file_name"] = None
                st.session_state["use_demo_data"] = True
                st.rerun()

    with st.sidebar.expander("📂 Ingest New File", expanded=False):
        quick_file = st.file_uploader(
            "Replace Active Dataset",
            type=["csv", "xlsx", "xls"],
            key="sidebar_replace_uploader",
        )
        if quick_file is not None:
            st.session_state["uploaded_file_bytes"] = quick_file.getvalue()
            st.session_state["uploaded_file_name"] = quick_file.name
            st.session_state["use_demo_data"] = False
            st.rerun()

    # Sidebar: Global Cohort Filters
    with st.sidebar.expander("🔎 Global Cohort Filters", expanded=True):
        min_d = sales_df[COL_DATE].min().date()
        max_d = sales_df[COL_DATE].max().date()
        selected_dates = st.date_input(
            "Date Window",
            value=(min_d, max_d),
            min_value=min_d,
            max_value=max_d,
            help="Filter transactions across all dashboard tabs simultaneously.",
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

        all_countries = ["All"] + sorted(list(sales_df[COL_COUNTRY].dropna().unique()))
        selected_countries = st.multiselect(
            "Market / Country",
            options=all_countries,
            default=["All"],
            help="Select one or more geographic markets.",
        )

    # Apply filters
    filtered_sales_df = filter_data(
        sales_df,
        start_date=pd.to_datetime(start_date) if start_date else None,
        end_date=pd.to_datetime(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1) if end_date else None,
        countries=selected_countries,
    )

    filtered_customer_df = filter_data(
        customer_df,
        start_date=pd.to_datetime(start_date) if start_date else None,
        end_date=pd.to_datetime(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1) if end_date else None,
        countries=selected_countries,
    )

    st.sidebar.caption(
        f"Filtered Volume: **{len(filtered_sales_df):,}** sales | **{len(filtered_customer_df):,}** customer rows"
    )

    # ---------------------------------------------------------
    # Main Dashboard Area: Telemetry & Broad Stats
    # ---------------------------------------------------------
    st.markdown(
        f"""
        <div class="telemetry-banner">
            <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: #10B981; box-shadow: 0 0 8px #10B981;"></span>
                    <span style="font-weight: 600; color: #F8FAFC; font-size: 0.95rem;">Active Dataset: <code style="color: #38BDF8; background: rgba(56, 189, 248, 0.1); padding: 2px 6px; border-radius: 4px;">{file_name}</code></span>
                </div>
                <div style="display: flex; align-items: center; gap: 16px; font-size: 0.825rem; color: #94A3B8;">
                    <span>⚡ Ingestion: <b style="color: #10B981;">Validated ({len(sales_df):,} rows)</b></span>
                    <span>🧠 Segmentation: <b style="color: #38BDF8;">RFM Normalized</b></span>
                    <span>🔍 Returns Isolated: <b style="color: #F59E0B;">{len(cancellations_df):,}</b></span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Broad Stats Ribbon (Top KPIs)
    kpis = compute_kpis(filtered_sales_df)
    _, pareto_share = compute_pareto_concentration(filtered_customer_df)
    drivers = what_drives_revenue_analysis(filtered_sales_df)

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Gross Positive Sales", f"${kpis['total_positive_sales']:,.2f}", help="Total sales value excluding isolated returns.")
    k2.metric("Distinct Orders", f"{kpis['distinct_invoices']:,}", help="Count of unique purchase orders.")
    k3.metric("Identified Buyers", f"{kpis['unique_customers']:,}", help="Count of identified customer accounts.")
    k4.metric("Catalog Products", f"{kpis['distinct_products']:,}", help="Unique merchandise stock items sold.")
    k5.metric("Avg Order Value", f"${kpis['avg_order_value']:,.2f}", help="Positive sales value per distinct order.")
    k6.metric("Return Rate", f"{kpis['cancellation_rate_pct']:.1f}%", help="Percentage of invoice records flagged as returns.")

    # Executive Analytical Findings
    insights = generate_sales_insights(kpis, pareto_share, drivers, guest_metrics)
    if insights:
        with st.expander("💡 Computed Executive Findings & Analytical Insights", expanded=False):
            for insight in insights:
                st.markdown(f"- {insight}")

    st.markdown("---")

    # ---------------------------------------------------------
    # Main Analytical Navigation: 4 Consolidated Workspaces
    # ---------------------------------------------------------
    tab_sales, tab_ml, tab_quality, tab_export = st.tabs([
        "📈 Sales & Revenue Drivers",
        "🧠 Customer Intelligence & Lifecycle (ML)",
        "🔍 Data Quality & Anomalies",
        "📥 Data Exports",
    ])

    with tab_sales:
        sales_page.render(filtered_sales_df, filtered_customer_df, guest_metrics)

    with tab_ml:
        clustering_page.render(filtered_sales_df, filtered_customer_df, guest_metrics)

    with tab_quality:
        sub_anomaly, sub_audit = st.tabs([
            "🚨 Sales Anomaly Detection",
            "📋 Data Cleaning & Return Policies",
        ])
        with sub_anomaly:
            anomaly_page.render(filtered_sales_df, filtered_customer_df, guest_metrics)
        with sub_audit:
            audit_page.render(filtered_sales_df, filtered_customer_df, guest_metrics, audit_logger, cancellations_df)

    with tab_export:
        exports_page.render(filtered_sales_df, filtered_customer_df, guest_metrics)


if __name__ == "__main__":
    main()