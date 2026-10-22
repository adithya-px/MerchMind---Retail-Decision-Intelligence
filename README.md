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
* **Snapshot Design**: Customers are described at cutoffs derived from the data (test cutoff = dataset end − 90 days; training cutoffs step back 30 days from `test cutoff − 90 days`, so no training label window reaches into the test window). Features use only the 90 days before each cutoff; the label uses the 90 days after it.
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

**Label.** At a cutoff date, a customer is *eligible* if they have at least one valid (non-cancelled, non-fee, positive-price) sales invoice in the preceding 90 days. The label is **1** when an eligible customer has **no** valid sales invoice in the 90 days after the cutoff, and **0** otherwise. Eligibility keeps the cohort to customers with recent signal; customers who stop buying before the lookback starts are not scored.

**Validation design (leak-free by construction).** Cutoffs come from the data, never hardcoded:

* Test cutoff = `dataset end − 90 days` (2011-09-10), so its label window ends exactly at the dataset end.
* Training cutoffs step back 30 days at a time from `test cutoff − 90 days`: **2011-06-12** and **2011-05-13**. Their label windows end 2011-09-10 and 2011-08-11, i.e. `cutoff + 90 days <= test cutoff` for every training cutoff. No training label is ever built from the test label period; this is enforced in `derive_cutoffs()` and covered by `test_training_label_windows_never_overlap_the_test_cutoff`.
* The lookback is 90 days so the earliest cutoff still has full feature history (the 60-vs-60 momentum pair reaches 120 days back, still strictly before the cutoff).

All models are fit on the pooled training snapshots and scored **once** on the test cutoff. Decision thresholds — and the choice of the selected model — use a 30% validation split carved out of the *training* cutoffs, then each model is refit on all training snapshots. The test set influences neither a threshold nor a hyperparameter; hyperparameters are fixed (no search) and seeds are fixed.

**Results on the official UCI Online Retail dataset** (test cutoff 2011-09-10, 1,903 eligible customers, 31.0% inactivity rate, 90-day lookback):

| Model | ROC-AUC | PR-AUC | Precision | Recall | F1 | Top-decile lift |
|---|---|---|---|---|---|---|
| Logistic Regression | 0.741 | 0.513 | 0.48 | 0.66 | 0.56 | 1.78× |
| Random Forest *(selected)* | 0.733 | 0.512 | 0.44 | 0.83 | 0.57 | 1.92× |
| XGBoost | 0.725 | 0.510 | 0.45 | 0.71 | 0.55 | 1.83× |
| Decline rule (existing heuristic) | 0.566 | 0.361 | 0.33 | 0.75 | 0.46 | 1.19× |
| Dummy (prior probability) | 0.500 | 0.310 | 0.31 | 1.00 | 0.47 | 0.90× |

Random Forest was selected on **validation** ROC-AUC (0.758 vs 0.756 for logistic regression — a 0.002 gap). On the held-out test cutoff the order reverses: logistic regression edges it by 0.008 ROC-AUC, while the forest keeps the higher F1 (0.57 vs 0.56) and the best top-decile lift (1.92×). On one time split these gaps are noise, and the ensembles add nothing over the simpler linear model — the ranking is effectively as good as a linear score. Every learned model still beats the decline heuristic (0.566). The strongest permutation-importance features are tenure, order count, 90-day spend and recency.

**Spend model.** An XGBoost regressor predicts `log1p(spend in the next 90 days)` from the same snapshot features, purely to weight the outreach list. Against the persistence baseline ("assume they repeat the last 90 days") **it does not win on absolute error**: MAE £882 vs £842 for the baseline (−4.7%). It does rank customers better (Spearman 0.554 vs 0.515). Because the forecast is not more accurate in currency terms, it is used only as a relative ranking weight, and the expected-revenue-at-risk column inherits that weaker assumption.

**Expected revenue at risk.** `P(inactive) × predicted 90-day spend` ranks customers for contact. On the held-out cutoff the total is ~£65.4K of expected revenue at risk, and contacting the top 200 customers covers ~46% of it.

**Limitations.** Only one year of transactions exists, so there are three cutoffs and the metrics come from a single time split; treat the differences between models as indicative. Training labels end before the test window (no overlap), but the training cutoffs are only 30 and 60 days before the test cutoff, so the model learns from a period close to the evaluation period. The model predicts who is likely to go quiet, not what a campaign would change — this is predictive signal, not a causal effect. Customers inactive before the lookback window are outside the cohort. Invoice dates near the dataset end have a shorter observed outcome window than the full 90 days. The pipeline refuses to train when only one outcome class is present or fewer than 50 customers qualify, and the UI states why instead of showing empty charts.

Reproduce the checks with `py -m pytest tests/test_churn_model.py -v` (label construction, no training/test label-window overlap, no leakage from post-cutoff transactions, and graceful degradation for a single class / too few customers).

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
