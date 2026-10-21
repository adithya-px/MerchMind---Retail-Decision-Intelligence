# RetailPulse — Sales Intelligence & Customer Insights Dashboard

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B.svg)](https://streamlit.io/)
[![Scikit-Learn](https://img.shields.io/badge/scikit--learn-ML-F7931E.svg)](https://scikit-learn.org/)
[![Tests](https://img.shields.io/badge/pytest-Passing-brightgreen.svg)](https://docs.pytest.org/)

RetailPulse is an end-to-end data science, business intelligence, and customer analytics application designed for retail operators. It bridges raw transaction records, machine learning clustering, and actionable marketing intelligence through a fast, modular Streamlit dashboard.

---

## 🌟 Key Features

### 1. Robust Ingestion & Cached Cleaning Pipeline (Feature A)
* **Flexible Ingestion**: Ingests official UCI Online Retail `.xlsx` and `.csv` files via drag-and-drop file upload or automatic local fallback.
* **Hash-Keyed Caching**: SHA-256 fingerprinting caches derived `.parquet` copies in `data/processed/`, eliminating slow repeated Excel loading while ensuring updated files never return stale results.
* **Non-Destructive Audit Log**: Every dropped or segregated record is tracked with row counts and an explicit business reason. Never silently drops data.
* **Return & Cancellation Segregation**: Orders with `InvoiceNo` starting with `'C'` or negative quantities are isolated into a dedicated returns dataset. Reported separately to avoid metric distortion; gross metrics are termed **positive sales value**.
* **Guest Customer Retention**: Transactions with missing `CustomerID` are **retained** for sales analytics (labeled as `Guest / Unidentified`) and excluded only from customer-level clustering. Reports the exact share of revenue and volume affected.
* **Non-Product Code Filtering**: Excludes postage (`POST`, `DOT`), manual adjustments (`M`), bank fees (`BANK CHARGES`), and discounts (`D`) from merchandise sales.

### 2. Sales Analytics & Revenue Drivers (Feature A)
* **Executive KPI Cards**: Positive Sales Value, Distinct Invoices, Unique Customers, Distinct Products, Average Order Value (AOV).
* **"What Drives Revenue" Contribution Analysis**:
  * Top 10 products revenue share (%)
  * Dominant geographic market share (%)
  * Month-over-Month (MoM) growth decomposition highlighting expanding vs contracting products.
* **Pareto Concentration Curve**: Measures cumulative customer share vs cumulative sales value (e.g., top 20% accounts generating ~75% of sales).
* **Demand Timing Patterns**: Interactive weekday-by-hour sales intensity heatmap.
* **Computed Executive Insights**: Automated natural-language findings generated strictly from computed metrics—never hardcoded.

### 3. Customer Intelligence via RFM + K-Means (Feature B)
* **Empirical RFM Metrics**:
  * **Recency**: Days since last order relative to Reference Date (default: latest transaction date + 1 day).
  * **Frequency**: Count of distinct valid orders (`InvoiceNo`), not line rows.
  * **Monetary**: Total positive sales value.
* **Mathematical Skew Normalization**: `log1p` transformation followed by `StandardScaler` to prevent extreme revenue outliers ("whales") from collapsing clustering geometry.
* **Defensible Model Selection**: Evaluates candidate $k \in [2, 8]$ using both Inertia (Elbow Method) and **Silhouette Scores**.
* **Profile-Based Centroid Labeling**: Inspects empirical cluster centroids ($R, F, M$) before assigning descriptive archetype names (*Champions*, *Loyal Customers*, *Promising High-Spenders*, *At Risk*, *Inactive*).
* **2D PCA Visualization**: Dimensionality reduction with explained variance ratios for interactive cluster exploration.
* **Educational Disclosure**: Explains the unsupervised nature of K-Means and clarifies that silhouette scores quantify geometric separation, not profitability or causal prediction.

### 4. Declining-Activity Detection (Feature B2)
* **Heuristic Drop Detection**: Evaluates accounts across equal-length baseline windows (default: 90-day recent vs 90-day prior):
  1. **Monetary/Volume Drop**: Flagged if spend dropped $\ge 40\%$ or orders ceased.
  2. **Cadence Lapse**: Flagged if days since last purchase exceeds $1.5\times$ customer's own historical median inter-purchase gap.
* **Exclusion Governance**: Accounts with fewer than 2 prior orders or $<\$50$ spend are excluded to avoid false alarms on one-time buyers.
* **Ranked Re-Engagement Table**: Sorted by absolute revenue lost ($) with documented decline drivers. Prominently labeled as a heuristic indicator, not a predictive churn model.

### 5. Profile-Derived Strategic Recommendations
* **Segment Marketing Playbooks**: Dynamic marketing interventions tailored to computed cluster profiles (VIP loyalty benefits, onboarding second-order incentives, targeted win-backs, clearance sales).
* **Observational Disclaimer**: Explicitly caveats recommendations as heuristic strategies requiring randomized A/B test validation.

### 6. Sales Anomaly Detection (Optional Module)
* **Rolling Baseline Envelope**: 14-day rolling median baseline with IQR boundary thresholds.
* **Surge & Drop Alerts**: Distinguishes volume spikes from sudden demand plunges with clear operational investigation guidance.

### 7. Filtered Data Exports (Feature C)
* **Synchronized CSV Downloads**: Exports match the active sidebar filters (Date Range, Country):
  1. Cleaned positive transactions (`.csv`)
  2. Customer RFM + Segment Names + Declining Flag (`.csv`)
  3. Monthly and Daily Sales Summary (`.csv`)

---

## 🏛️ Architecture & Modular Extensibility

Data processing and machine learning algorithms are completely decoupled from Streamlit UI rendering. Dashboard pages are independent modules registered in a single dictionary in `dashboards/app.py`.

```text
RetailPulse_Project/
│
├── src/
│   ├── __init__.py
│   ├── config.py                 # Central configurations, column schemas, constants, seeds
│   ├── data_loader.py            # CSV/Excel ingestion, column standardization, Parquet caching
│   ├── cleaning.py               # 7-stage audit-logged cleaning pipeline & guest retention
│   ├── sales_analytics.py        # KPIs, Pareto concentration, revenue drivers, computed insights
│   ├── customer_segmentation.py  # RFM table, log1p, K-Means (k=2-8), Silhouette, 2D PCA
│   ├── declining_activity.py     # Spend drop & inter-purchase cadence lapse detection
│   ├── recommendations.py        # Segment marketing playbooks & causal disclaimers
│   └── anomaly_detection.py      # Rolling baseline & IQR daily sales anomaly detection
│
├── dashboards/
│   ├── app.py                    # Main Streamlit router, unified filters, file upload
│   └── pages/
│       ├── __init__.py
│       ├── overview_page.py        # Executive KPI cards & sales trends
│       ├── sales_page.py           # Revenue drivers, Pareto curve, catalog & geo analytics
│       ├── clustering_page.py      # RFM clustering, k evaluation, PCA 2D, educational guide
│       ├── declining_page.py       # Heuristic declining-activity re-engagement list
│       ├── recommendations_page.py # Profile-derived marketing playbooks
│       ├── anomaly_page.py         # Daily sales anomaly envelope
│       ├── audit_page.py           # Step-by-step cleaning audit log & guest metrics
│       └── exports_page.py         # Filter-synchronized CSV downloads
│
├── tests/
│   ├── test_cleaning.py          # Data validation, return segregation, guest retention
│   ├── test_data_loader.py       # File hashing, Excel/CSV loaders, schema checks
│   ├── test_sales_analytics.py   # Hand-checkable KPIs, filtering, Pareto concentration
│   ├── test_rfm_clustering.py    # Known RFM example, few-customer edge cases, KMeans
│   ├── test_declining_activity.py# Known activity timeline drop & cadence rules
│   ├── test_exports_consistency.py # Cross-pipeline segment attribute consistency
│   ├── test_anomaly_detection.py # Rolling baseline surge/drop detection
│   └── test_dashboard_smoke.py   # Headless smoke test across all registered pages
│
├── data/
│   ├── raw/                      # Raw UCI Online Retail datasets (.csv, .xlsx)
│   ├── cleaned/                  # Legacy preprocessed datasets
│   └── processed/                # Gitignored hash-keyed Parquet cache
│
├── requirements.txt              # Production & development dependencies
└── README.md                     # Comprehensive documentation
```

### Adding a New Dashboard Page
To add a new view to the dashboard:
1. Create `dashboards/pages/my_new_page.py` with standard `render(sales_df, customer_df, guest_metrics, audit_logger, cancellations_df)`.
2. Register it in `dashboards/app.py` inside `PAGES`:
   ```python
   "✨ My New Page": lambda s, c, g, a, can: my_new_page.render(s, c, g),
   ```

---

## 📊 Dataset Information

* **Source**: Official UCI Machine Learning Repository — [Online Retail Dataset](https://archive.ics.uci.edu/dataset/352/online+retail).
* **Attributes**: `InvoiceNo`, `StockCode`, `Description`, `Quantity`, `InvoiceDate`, `UnitPrice`, `CustomerID`, `Country`.
* **Coverage**: Transactions from a UK-based registered non-store online retail firm specializing in unique gift-ware between 2010 and 2011.

---

## 🚀 Getting Started

### 1. Prerequisites
* Python 3.10+ (tested on Python 3.13 and Python 3.14)
* Virtual environment (recommended)

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/your-username/RetailPulse-Customer-Analytics-Dashboard.git
cd RetailPulse-Customer-Analytics-Dashboard

# Install required dependencies
py -m pip install -r requirements.txt
# (or on Linux/macOS: pip install -r requirements.txt)
```

### 3. Run the Streamlit Dashboard
```bash
# Launch dashboard
py -m streamlit run dashboards/app.py
# (or on Linux/macOS: streamlit run dashboards/app.py)
```
Open your browser at `http://localhost:8501`.

### 4. Running the Test Suite
The repository includes **28 deterministic unit and smoke tests** covering hand-checkable mathematical calculations, schema validation, return isolation, guest customer retention, RFM frequency and recency rules, candidate $k$ evaluations, and regression tests:
```bash
py -m pytest -v
# (or on Linux/macOS: pytest -v)
```

---

## 🛡️ Limitations & Scientific Governance
1. **Observational Segmentation**: K-Means clustering groups customers by natural geometry in normalized log-space $(\log(R), \log(F), \log(M))$; clusters are descriptive behavioral segments, not predictive churn forecasts or permanent assignments.
2. **Silhouette Score**: Quantifies geometric cluster separation and compactness relative to nearest neighbors. A higher score does not directly imply higher customer lifetime value, profitability, or brand loyalty.
3. **Heuristic Activity Decline**: Decline indicators flag deviations from historical velocity and inter-purchase cadence. External macro factors (such as gift-buying seasonality, inventory stockouts, or offline shopping) can trigger flags without genuine customer attrition.
4. **Marketing Playbooks**: Recommended interventions represent industry best practices for each behavioral profile. All interventions should be measured against randomized holdout control groups (A/B testing) before full commercial rollout.
5. **Guest / Anonymous Checkout Retention**: Guest orders lack persistent `CustomerID` identifiers and are kept strictly for sales analytics and KPI tracking; they are excluded from customer-level RFM clustering to prevent grouping unrelated anonymous shoppers into artificial centroids.
