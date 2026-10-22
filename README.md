# MerchMind — Sales Intelligence & Customer Insights Dashboard

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-Vite-61DAFB.svg)](https://react.dev/)
[![Scikit-Learn](https://img.shields.io/badge/scikit--learn-ML-F7931E.svg)](https://scikit-learn.org/)
[![Tests](https://img.shields.io/badge/pytest-Passing-brightgreen.svg)](https://docs.pytest.org/)

MerchMind is an end-to-end data science, business intelligence, and customer analytics application designed for retail operators. It bridges raw transaction records, machine learning clustering, and actionable marketing intelligence through a React frontend and FastAPI backend. Analytics and ML code live in `src/` and is reused by the API — it is not rewritten in the UI.

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

### 7. Predictive Analytics — Churn Model & Outreach Ranking
* **Snapshot Design**: Customers are described at cutoffs derived from the data (test cutoff = dataset end − 90 days, two training cutoffs 30 days apart before it). Features use only the 180 days before each cutoff; the label uses the 90 days after it.
* **Honest Evaluation**: Dummy, the existing decline heuristic, Logistic Regression, Random Forest, and XGBoost are scored on the same held-out future cutoff with ROC-AUC, PR-AUC, precision/recall/F1 at a validation-chosen threshold, and top-decile lift.
* **Expected Revenue at Risk**: `P(inactive) × predicted 90-day spend`, ranked into a contact list with a list-size slider, coverage share, and CSV export.
* **Cached Fits**: A fitted pipeline is cached with joblib per dataset hash, so the tab loads in well under a second after the first fit.

### 8. Filtered Data Exports (Feature C)
* **Synchronized CSV Downloads**: Exports match the active sidebar filters (Date Range, Country):
  1. Cleaned positive transactions (`.csv`)
  2. Customer RFM + Segment Names + Declining Flag (`.csv`)
  3. Monthly and Daily Sales Summary (`.csv`)
  4. Predictive outreach priority list with churn probability, predicted spend and expected revenue at risk (`.csv`)

---

## 🏛️ Architecture & Modular Extensibility

Data processing and machine learning stay in `src/`. FastAPI exposes those functions as REST endpoints. React components fetch JSON and render charts; they do not invent metrics.

```text
MerchMind_Project/
│
├── src/                          # Reused analytics + ML (unchanged calculation core)
├── backend/main.py               # FastAPI REST API (upload, analytics, exports)
├── frontend/                     # React + Vite + Tailwind + Recharts
├── tests/                        # Analytics unit tests + API endpoint tests
├── data/raw/                     # Optional UCI Online Retail CSV/XLSX for the demo loader
├── requirements.txt
└── README.md
```

REST endpoints: `/api/dataset/upload`, `/api/dataset/status`, `/api/overview`, `/api/sales`, `/api/customer-segments`, `/api/model-diagnostics`, `/api/declining-customers`, `/api/predictive`, `/api/recommendations`, `/api/anomalies`, `/api/audit-log`, `/api/export/{sales|monthly|segments|declining|anomalies|outreach}`.

---

## 🔮 Predictive Analytics — Method, Validation & Real Results

The **Predictive** tab is a supervised layer, not a re-labelled heuristic. Code lives in `src/churn_model.py`.

**Label.** At a cutoff date, a customer is *eligible* if they have at least one valid (non-cancelled, non-fee, positive-price) sales invoice in the preceding 180 days. The label is **1** when an eligible customer has **no** valid sales invoice in the 90 days after the cutoff, and **0** otherwise. Eligibility keeps the cohort to customers with recent signal; customers who stop buying before the lookback starts are not scored.

**Validation design.** Cutoffs come from the data, never hardcoded: the test cutoff is `dataset end − 90 days` (so its label window ends exactly at the dataset end) and two training cutoffs sit 30 and 60 days before it. All models are fit on the pooled training snapshots and scored **once** on the test cutoff. Decision thresholds are chosen by F1 on a 30% validation split carved out of the *training* cutoffs, then each model is refit on all training snapshots — the test set never influences a threshold or a hyperparameter. Hyperparameters are fixed (no search); seeds are fixed.

**Results on the official UCI Online Retail dataset** (test cutoff 2011-09-10, 2,783 eligible customers, 38.2% inactivity rate):

| Model | ROC-AUC | PR-AUC | Precision | Recall | F1 | Top-decile lift |
|---|---|---|---|---|---|---|
| Random Forest | 0.758 | 0.621 | 0.52 | 0.86 | 0.64 | 1.85× |
| XGBoost | 0.754 | 0.620 | 0.52 | 0.84 | 0.64 | 1.78× |
| Logistic Regression | 0.739 | 0.585 | 0.53 | 0.80 | 0.63 | 1.66× |
| Decline rule (existing heuristic) | 0.617 | 0.476 | 0.42 | 0.79 | 0.55 | 1.40× |
| Dummy (prior probability) | 0.500 | 0.382 | 0.38 | 1.00 | 0.55 | 0.89× |

Random Forest is the selected model (threshold 0.38) and beats the decline heuristic by ~0.14 ROC-AUC. It beats logistic regression by only 0.019 ROC-AUC and ~0.005 F1 — on a single time split that is a statistical tie, so the README does not claim the ensemble is necessary. The strongest permutation-importance features are tenure, 180-day spend, order count and distinct products.

**Spend model.** An XGBoost regressor predicts `log1p(spend in the next 90 days)` from the same snapshot features, purely to weight the outreach list. Against the persistence baseline ("assume they repeat the last 90 days") it improves MAE from £679 to £630 (+7.3%) and Spearman correlation from 0.441 to 0.575. That is a modest edge, which is why it is used as a ranking weight rather than reported as a revenue forecast.

**Expected revenue at risk.** `P(inactive) × predicted 90-day spend` ranks customers for contact. On the held-out cutoff the total is ~£95.5K of expected revenue at risk, and contacting the top 200 customers covers ~49% of it.

**Limitations.** Only one year of transactions exists, so there are three cutoffs and the metrics come from a single time split; treat the differences between models as indicative. The model predicts who is likely to go quiet, not what a campaign would change — this is predictive signal, not a causal effect. Customers inactive before the lookback window are outside the cohort. Invoice dates near the dataset end have a shorter observed outcome window than the full 90 days. The pipeline refuses to train when only one outcome class is present or fewer than 50 customers qualify, and the UI states why instead of showing empty charts.

Reproduce the checks with `py -m pytest tests/test_churn_model.py -v` (label construction, no-leakage from post-cutoff transactions, and graceful degradation for a single class / too few customers).

---

## 📊 Dataset Information

* **Source**: Official UCI Machine Learning Repository — [Online Retail Dataset](https://archive.ics.uci.edu/dataset/352/online+retail).
* **Attributes**: `InvoiceNo`, `StockCode`, `Description`, `Quantity`, `InvoiceDate`, `UnitPrice`, `CustomerID`, `Country`.
* **Coverage**: Transactions from a UK-based registered non-store online retail firm specializing in unique gift-ware between 2010 and 2011.

---

## 🚀 Getting Started

### 1. Prerequisites
* Python 3.10+
* Node.js 20+
* Virtual environment (recommended)

### 2. Backend
```bash
git clone https://github.com/your-username/MerchMind---Retail-Decision-Intelligence.git
cd MerchMind---Retail-Decision-Intelligence

py -m pip install -r requirements.txt
# Linux/macOS: pip install -r requirements.txt

# From the project root so `src` and `backend` import correctly
py -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Optional: place `Online Retail.csv` or `Online Retail.xlsx` in `data/raw/` to enable **Load demo dataset** in the UI. That loader uses the real file on disk, not fabricated KPIs.

### 3. Frontend
In a second terminal:
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173`. Vite proxies `/api` to `http://127.0.0.1:8000`. To call the API on another origin, set `VITE_API_URL` (for example `http://127.0.0.1:8000`) and keep CORS origins in `backend/main.py` in sync. Extra origins can be passed with `FRONTEND_ORIGIN`.

Upload a CSV/XLSX with columns `InvoiceNo, StockCode, Description, Quantity, InvoiceDate, UnitPrice, CustomerID, Country`. Every chart and KPI is computed from that loaded file (or from the selected on-disk benchmark file).

### 4. Tests
```bash
py -m pytest -v
```
Analytics tests cover cleaning, KPIs, RFM/K-Means, declining activity, anomalies, and the predictive snapshot layer (label construction, leakage, graceful degradation). `tests/test_api.py` uploads a schema-valid transaction CSV and asserts overview, sales, segments, exports, and related endpoints.

---

## 🛡️ Limitations & Scientific Governance
1. **Observational Segmentation**: K-Means clustering groups customers by natural geometry in normalized log-space $(\log(R), \log(F), \log(M))$; clusters are descriptive behavioral segments, not predictive churn forecasts or permanent assignments.
2. **Silhouette Score**: Quantifies geometric cluster separation and compactness relative to nearest neighbors. A higher score does not directly imply higher customer lifetime value, profitability, or brand loyalty.
3. **Heuristic Activity Decline**: Decline indicators flag deviations from historical velocity and inter-purchase cadence. External macro factors (such as gift-buying seasonality, inventory stockouts, or offline shopping) can trigger flags without genuine customer attrition.
4. **Marketing Playbooks**: Recommended interventions represent industry best practices for each behavioral profile. All interventions should be measured against randomized holdout control groups (A/B testing) before full commercial rollout.
5. **Guest / Anonymous Checkout Retention**: Guest orders lack persistent `CustomerID` identifiers and are kept strictly for sales analytics and KPI tracking; they are excluded from customer-level RFM clustering to prevent grouping unrelated anonymous shoppers into artificial centroids.
