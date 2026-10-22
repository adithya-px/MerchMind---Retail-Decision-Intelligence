"""
Predictive Analytics Engine for MerchMind.

Supervised customer-level models built on a snapshot design:

    cutoff  ----------------  cutoff  ---------------------------  cutoff + 90d
             lookback window            label window
             (features only)        (observed inactivity outcome)

* Features are computed exclusively from the ``lookback_days`` window that ends at
  the cutoff, so no information after the cutoff can leak into a snapshot.
* The label is 1 when an identified customer who purchased inside the lookback
  window has no valid sales invoice in the ``horizon_days`` after the cutoff.
* Cutoffs are always derived from the data: the test cutoff is
  ``dataset_end - horizon_days``; training cutoffs step back ``spacing_days`` at a
  time from ``test_cutoff - horizon_days``, so every training label window ends on
  or before the test cutoff and can never cover the test label period.

A small spend regressor (log1p spend in the horizon window) exists only to
support the expected-revenue-at-risk outreach ranking. Every model uses fixed
hyperparameters and a fixed seed; results are cached with joblib keyed by the
dataset hash so the API stays fast after the first fit.
"""

import hashlib
import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

import joblib
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    mean_absolute_error,
    precision_recall_curve,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.config import (
    COL_COUNTRY,
    COL_CUST,
    COL_DATE,
    COL_INVOICE,
    COL_LINE_REVENUE,
    COL_STOCK,
    PREDICTIVE_CACHE_DIR,
    PREDICTIVE_HORIZON_DAYS,
    PREDICTIVE_LOOKBACK_DAYS,
    PREDICTIVE_MIN_CUSTOMERS,
    PREDICTIVE_N_TRAIN_CUTOFFS,
    PREDICTIVE_OUTREACH_PAYLOAD_LIMIT,
    PREDICTIVE_TRAIN_CUTOFF_SPACING_DAYS,
    PREDICTIVE_VALIDATION_FRACTION,
    RANDOM_SEED,
)

try:  # XGBoost is optional; HistGradientBoosting is a drop-in substitute.
    from xgboost import XGBClassifier, XGBRegressor

    HAS_XGBOOST = True
except Exception:  # pragma: no cover - depends on the local environment
    from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor

    HAS_XGBOOST = False

FEATURE_COLUMNS: List[str] = [
    "log_recency",
    "log_frequency",
    "log_monetary",
    "avg_order_value",
    "tenure_days",
    "median_gap_days",
    "recency_over_gap",
    "spend_ratio_60",
    "orders_ratio_60",
    "distinct_products",
    "return_rate",
    "is_uk",
]

SPEND_EXTRA_COLUMN = "spend_last_90"

# Momentum features compare the last 60 days with the 60 days before that. This
# is still strictly pre-cutoff history, and drive the required-span calculation.
MOMENTUM_WINDOW_DAYS = 60

SNAPSHOT_COLUMNS: List[str] = (
    [COL_CUST] + FEATURE_COLUMNS + ["label", "spend_next_90", SPEND_EXTRA_COLUMN, "cutoff"]
)

BASELINE_MODELS = {"Dummy (prior probability)", "Decline rule (existing heuristic)"}


# ---------------------------------------------------------
# Snapshot construction
# ---------------------------------------------------------
def _empty_snapshot() -> pd.DataFrame:
    frame = pd.DataFrame(columns=SNAPSHOT_COLUMNS)
    frame[COL_CUST] = frame[COL_CUST].astype("object")
    return frame


def normalize_customer_ids(series: pd.Series) -> pd.Series:
    """Match the CustomerID normalisation used by the cleaning pipeline."""

    def _convert(value):
        if pd.isna(value):
            return np.nan
        text = str(value).strip()
        if text in {"", "nan", "None", "NaN"}:
            return np.nan
        try:
            return str(int(float(text)))
        except (TypeError, ValueError):
            return text

    return series.map(_convert)


def build_snapshot(
    customer_df: pd.DataFrame,
    cutoff: Any,
    lookback_days: int = PREDICTIVE_LOOKBACK_DAYS,
    horizon_days: int = PREDICTIVE_HORIZON_DAYS,
    cancellations_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Build one customer snapshot at ``cutoff``.

    Only transactions with ``lookback_start < InvoiceDate <= cutoff`` feed the
    feature columns. Only transactions with ``cutoff < InvoiceDate <= cutoff +
    horizon_days`` feed the label and the future-spend target.
    """
    if customer_df is None or len(customer_df) == 0:
        return _empty_snapshot()

    cutoff = pd.Timestamp(cutoff).normalize()
    df = customer_df[
        [COL_CUST, COL_INVOICE, COL_DATE, COL_LINE_REVENUE, COL_STOCK, COL_COUNTRY]
    ].dropna(subset=[COL_DATE])

    lookback_start = cutoff - pd.Timedelta(days=lookback_days)
    horizon_end = cutoff + pd.Timedelta(days=horizon_days)

    history = df[df[COL_DATE] <= cutoff]
    past = history[history[COL_DATE] > lookback_start]
    if past.empty:
        return _empty_snapshot()

    # --- Invoice level aggregation (one row per order) -------------------
    invoices = (
        past.groupby([COL_CUST, COL_INVOICE], as_index=False)
        .agg(invoice_date=(COL_DATE, "min"), revenue=(COL_LINE_REVENUE, "sum"))
        .sort_values([COL_CUST, "invoice_date"])
    )

    base = invoices.groupby(COL_CUST).agg(
        last_purchase=("invoice_date", "max"),
        frequency=(COL_INVOICE, "nunique"),
        monetary=("revenue", "sum"),
        avg_order_value=("revenue", "mean"),
    )
    base["recency_days"] = (
        cutoff - base["last_purchase"]
    ).dt.total_seconds() / 86400.0

    # Median inter-purchase gap (days between consecutive invoices).
    invoices["prev_date"] = invoices.groupby(COL_CUST)["invoice_date"].shift(1)
    invoices["gap_days"] = (
        invoices["invoice_date"] - invoices["prev_date"]
    ).dt.total_seconds() / 86400.0
    median_gap = (
        invoices.dropna(subset=["gap_days"]).groupby(COL_CUST)["gap_days"].median()
    )
    base["median_gap_days"] = median_gap.reindex(base.index)

    # Tenure counts all history up to the cutoff (still strictly pre-cutoff).
    first_seen = history.groupby(COL_CUST)[COL_DATE].min()
    base["tenure_days"] = (cutoff - first_seen.reindex(base.index)).dt.total_seconds() / 86400.0

    def _window(start_days: int, end_days: int) -> pd.DataFrame:
        start = cutoff - pd.Timedelta(days=start_days)
        end = cutoff - pd.Timedelta(days=end_days)
        return history[(history[COL_DATE] > start) & (history[COL_DATE] <= end)]

    last_60 = _window(MOMENTUM_WINDOW_DAYS, 0)
    prev_60 = _window(2 * MOMENTUM_WINDOW_DAYS, MOMENTUM_WINDOW_DAYS)
    last_90 = _window(PREDICTIVE_HORIZON_DAYS, 0)

    spend_60 = last_60.groupby(COL_CUST)[COL_LINE_REVENUE].sum()
    spend_prev_60 = prev_60.groupby(COL_CUST)[COL_LINE_REVENUE].sum()
    orders_60 = last_60.groupby(COL_CUST)[COL_INVOICE].nunique()
    orders_prev_60 = prev_60.groupby(COL_CUST)[COL_INVOICE].nunique()
    spend_90 = last_90.groupby(COL_CUST)[COL_LINE_REVENUE].sum()

    products = past.groupby(COL_CUST)[COL_STOCK].nunique()
    countries = (
        past.sort_values(COL_DATE).groupby(COL_CUST)[COL_COUNTRY].last()
    )

    # Return rate: cancellation invoices / (sales invoices + cancellation invoices).
    return_rate = pd.Series(0.0, index=base.index, dtype=float)
    if cancellations_df is not None and len(cancellations_df) > 0:
        cancel = cancellations_df[[COL_CUST, COL_INVOICE, COL_DATE]].copy()
        cancel[COL_CUST] = normalize_customer_ids(cancel[COL_CUST])
        cancel = cancel.dropna(subset=[COL_CUST])
        cancel = cancel[
            (cancel[COL_DATE] > lookback_start) & (cancel[COL_DATE] <= cutoff)
        ]
        if not cancel.empty:
            cancel_counts = cancel.groupby(COL_CUST)[COL_INVOICE].nunique()
            cancel_counts = cancel_counts.reindex(base.index).fillna(0.0)
            total = base["frequency"] + cancel_counts
            return_rate = (cancel_counts / total.replace(0, np.nan)).fillna(0.0)

    # --- Label + future spend -------------------------------------------
    future = df[(df[COL_DATE] > cutoff) & (df[COL_DATE] <= horizon_end)]
    future_spend = future.groupby(COL_CUST)[COL_LINE_REVENUE].sum()

    index = base.index
    purchase_in_horizon = index.isin(future.groupby(COL_CUST)[COL_INVOICE].nunique().index)
    label = (~purchase_in_horizon).astype(int)

    # --- Assemble feature frame -----------------------------------------
    gap = base["median_gap_days"]
    global_gap = float(gap.median()) if gap.notna().any() else float(lookback_days)
    if not np.isfinite(global_gap) or global_gap <= 0:
        global_gap = float(lookback_days)
    gap = gap.fillna(global_gap).clip(lower=1.0)

    recency = base["recency_days"].clip(lower=0.0)

    snap = pd.DataFrame(index=index)
    snap["log_recency"] = np.log1p(recency)
    snap["log_frequency"] = np.log1p(base["frequency"].clip(lower=0))
    snap["log_monetary"] = np.log1p(base["monetary"].clip(lower=0))
    snap["avg_order_value"] = base["avg_order_value"].clip(lower=0)
    snap["tenure_days"] = base["tenure_days"].clip(lower=1.0)
    snap["median_gap_days"] = gap
    snap["recency_over_gap"] = (recency / gap).clip(lower=0.0, upper=50.0)
    snap["spend_ratio_60"] = (
        (spend_60.reindex(index).fillna(0.0) + 1.0)
        / (spend_prev_60.reindex(index).fillna(0.0) + 1.0)
    ).clip(lower=0.0, upper=50.0)
    snap["orders_ratio_60"] = (
        (orders_60.reindex(index).fillna(0.0) + 1.0)
        / (orders_prev_60.reindex(index).fillna(0.0) + 1.0)
    ).clip(lower=0.0, upper=50.0)
    snap["distinct_products"] = products.reindex(index).fillna(0).astype(float)
    snap["return_rate"] = return_rate.clip(lower=0.0, upper=1.0)
    snap["is_uk"] = (
        countries.reindex(index).fillna("").astype(str).str.upper() == "UNITED KINGDOM"
    ).astype(float)
    snap["label"] = label.astype(int)
    snap["spend_next_90"] = future_spend.reindex(index).fillna(0.0).clip(lower=0.0)
    snap[SPEND_EXTRA_COLUMN] = spend_90.reindex(index).fillna(0.0).clip(lower=0.0)
    snap["cutoff"] = cutoff

    snap.index.name = COL_CUST
    snap = snap.reset_index()
    return snap[SNAPSHOT_COLUMNS]


def derive_cutoffs(
    customer_df: pd.DataFrame,
    lookback_days: int = PREDICTIVE_LOOKBACK_DAYS,
    horizon_days: int = PREDICTIVE_HORIZON_DAYS,
    n_train_cutoffs: int = PREDICTIVE_N_TRAIN_CUTOFFS,
    spacing_days: int = PREDICTIVE_TRAIN_CUTOFF_SPACING_DAYS,
) -> Dict[str, Any]:
    """
    Derive snapshot cutoffs from the data itself.

    Returns ``{"ok": bool, "reason": str|None, "test_cutoff": Timestamp,
    "train_cutoffs": [Timestamp, ...]}``. Training cutoffs are listed oldest first.

    Guarantee: ``cutoff + horizon_days <= test_cutoff`` for every training cutoff,
    so no training label window overlaps the test label window.
    """
    if customer_df is None or len(customer_df) == 0:
        return {"ok": False, "reason": "No transactions available.", "train_cutoffs": [], "test_cutoff": None}

    dates = pd.to_datetime(customer_df[COL_DATE])
    data_start = dates.min().normalize()
    data_end = dates.max().normalize()
    span_days = int((data_end - data_start).days)

    horizon = pd.Timedelta(days=horizon_days)
    gap_days = spacing_days * max(0, n_train_cutoffs - 1)
    # The momentum features compare the last 60 days with the 60 before it, so a
    # "full" feature history is the wider of the lookback and that 120-day span.
    feature_history_days = max(lookback_days, 2 * MOMENTUM_WINDOW_DAYS)
    required_span = 2 * horizon_days + gap_days + feature_history_days
    if span_days < required_span:
        return {
            "ok": False,
            "reason": (
                f"Dataset spans {span_days} days; the snapshot design needs at least "
                f"{required_span} days ({horizon_days}d test label window + {horizon_days}d "
                f"gap so training labels never overlap it + {gap_days}d between train cutoffs "
                f"+ {feature_history_days}d of feature history)."
            ),
            "train_cutoffs": [],
            "test_cutoff": None,
            "data_start": data_start,
            "data_end": data_end,
            "span_days": span_days,
        }

    test_cutoff = data_end - horizon

    # ------------------------------------------------------------------
    # No temporal leakage: a training snapshot's label window must end at or
    # before the test cutoff. Otherwise its label would be derived from
    # transactions inside the test label window, and the held-out evaluation
    # would be scoring models that already saw the answer.
    # ------------------------------------------------------------------
    latest_train_cutoff = test_cutoff - horizon
    train_cutoffs = sorted(
        latest_train_cutoff - pd.Timedelta(days=spacing_days * i)
        for i in range(n_train_cutoffs)
    )
    # Defence in depth: never return a cutoff whose label window crosses the test cutoff.
    train_cutoffs = [c for c in train_cutoffs if c + horizon <= test_cutoff]

    return {
        "ok": True,
        "reason": None,
        "train_cutoffs": train_cutoffs,
        "test_cutoff": test_cutoff,
        "data_start": data_start,
        "data_end": data_end,
        "span_days": span_days,
    }


def build_all_snapshots(
    customer_df: pd.DataFrame,
    cutoffs: Dict[str, Any],
    lookback_days: int = PREDICTIVE_LOOKBACK_DAYS,
    horizon_days: int = PREDICTIVE_HORIZON_DAYS,
    cancellations_df: Optional[pd.DataFrame] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, List[pd.Timestamp]]:
    """Return (train_snapshots_stacked, test_snapshot, train_cutoffs_used)."""
    frames: List[pd.DataFrame] = []
    used: List[pd.Timestamp] = []
    for cutoff in cutoffs["train_cutoffs"]:
        snap = build_snapshot(
            customer_df,
            cutoff,
            lookback_days=lookback_days,
            horizon_days=horizon_days,
            cancellations_df=cancellations_df,
        )
        if not snap.empty:
            frames.append(snap)
            used.append(pd.Timestamp(cutoff))

    train_df = pd.concat(frames, ignore_index=True) if frames else _empty_snapshot()
    test_df = build_snapshot(
        customer_df,
        cutoffs["test_cutoff"],
        lookback_days=lookback_days,
        horizon_days=horizon_days,
        cancellations_df=cancellations_df,
    )
    return train_df, test_df, used


# ---------------------------------------------------------
# Models
# ---------------------------------------------------------
class DeclineRuleScorer:
    """
    The existing heuristic decline rule expressed as a continuous score so it
    can be compared fairly (AUC/PR) against the learned models.

    Score = max(spend-drop share over the last 60 days vs the prior 60 days,
                cadence lapse beyond 1.5x the typical inter-purchase gap).
    """

    def __init__(self, lapse_reference: float = 1.5):
        self.lapse_reference = lapse_reference
        self.threshold_ = 0.25
        self.classes_ = np.array([0, 1])

    def fit(self, X, y=None):
        return self

    def _frame(self, X) -> pd.DataFrame:
        if isinstance(X, pd.DataFrame):
            return X
        return pd.DataFrame(np.asarray(X, dtype=float), columns=FEATURE_COLUMNS)

    def _score(self, X) -> np.ndarray:
        frame = self._frame(X)
        spend_ratio = np.asarray(frame["spend_ratio_60"], dtype=float)
        lapse_ratio = np.asarray(frame["recency_over_gap"], dtype=float)
        # spend_ratio_60 = (spend_last60 + 1) / (spend_prev60 + 1)
        spend_drop = np.clip(1.0 - spend_ratio, 0.0, 1.0)
        lapse = np.clip((lapse_ratio - self.lapse_reference + 0.5) / 2.0, 0.0, 1.0)
        return np.maximum(spend_drop, lapse)

    def predict_proba(self, X) -> np.ndarray:
        score = self._score(X)
        return np.column_stack([1.0 - score, score])

    def predict(self, X) -> np.ndarray:
        return (self._score(X) >= self.threshold_).astype(int)


def _positive_weight(y: np.ndarray) -> float:
    positives = int((y == 1).sum())
    negatives = int((y == 0).sum())
    if positives == 0:
        return 1.0
    return max(1.0, negatives / positives)


def build_churn_models(y_train: np.ndarray) -> Dict[str, Any]:
    """Fixed-hyperparameter estimators. No search, fixed seed, class weighting."""
    models: Dict[str, Any] = {
        "Dummy (prior probability)": DummyClassifier(strategy="prior", random_state=RANDOM_SEED),
        "Decline rule (existing heuristic)": DeclineRuleScorer(),
        "Logistic Regression": Pipeline(
            [
                ("scale", StandardScaler()),
                (
                    "model",
                    LogisticRegression(
                        C=1.0,
                        max_iter=2000,
                        class_weight="balanced",
                        random_state=RANDOM_SEED,
                    ),
                ),
            ]
        ),
        "Random Forest": RandomForestClassifier(
            n_estimators=300,
            max_depth=8,
            min_samples_leaf=5,
            class_weight="balanced_subsample",
            n_jobs=-1,
            random_state=RANDOM_SEED,
        ),
    }

    if HAS_XGBOOST:
        models["XGBoost"] = XGBClassifier(
            n_estimators=300,
            max_depth=3,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.8,
            scale_pos_weight=_positive_weight(y_train),
            tree_method="hist",
            eval_metric="logloss",
            n_jobs=1,
            random_state=RANDOM_SEED,
        )
    else:
        models["HistGradientBoosting"] = HistGradientBoostingClassifier(
            max_iter=250,
            learning_rate=0.05,
            max_depth=4,
            random_state=RANDOM_SEED,
        )
    return models


def select_threshold(y_true: np.ndarray, y_score: np.ndarray) -> float:
    """Pick the F1-maximising threshold; used on validation data only."""
    if len(np.unique(y_true)) < 2:
        return 0.5
    precision, recall, thresholds = precision_recall_curve(y_true, y_score)
    f1 = 2 * precision * recall / np.clip(precision + recall, 1e-9, None)
    if len(thresholds) == 0:
        return 0.5
    best = int(np.nanargmax(f1[:-1]))
    return float(np.clip(thresholds[best], 0.01, 0.99))


def compute_binary_metrics(y_true: np.ndarray, y_score: np.ndarray, threshold: float) -> Dict[str, Any]:
    """ROC-AUC, PR-AUC, precision/recall/F1 at a threshold, top-decile lift."""
    y_true = np.asarray(y_true, dtype=int)
    y_score = np.asarray(y_score, dtype=float)
    y_pred = (y_score >= threshold).astype(int)

    base_rate = float(y_true.mean()) if len(y_true) else 0.0
    metrics: Dict[str, Any] = {
        "roc_auc": None,
        "pr_auc": None,
        "precision": None,
        "recall": None,
        "f1": None,
        "top_decile_lift": None,
        "base_rate": base_rate,
        "n": int(len(y_true)),
        "positives": int(y_true.sum()),
    }

    if len(y_true) == 0 or len(np.unique(y_true)) < 2:
        return metrics

    metrics["roc_auc"] = float(roc_auc_score(y_true, y_score))
    metrics["pr_auc"] = float(average_precision_score(y_true, y_score))

    tp = int(((y_pred == 1) & (y_true == 1)).sum())
    fp = int(((y_pred == 1) & (y_true == 0)).sum())
    fn = int(((y_pred == 0) & (y_true == 1)).sum())

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    metrics["precision"] = float(precision)
    metrics["recall"] = float(recall)
    metrics["f1"] = float(f1)

    # Top-decile lift: how much richer the highest-scoring 10% is than the base rate.
    k = max(1, int(round(len(y_true) * 0.10)))
    order = np.argsort(-y_score)[:k]
    top_rate = float(y_true[order].mean())
    if base_rate > 0:
        metrics["top_decile_lift"] = float(top_rate / base_rate)

    return metrics


def curve_payload(
    y_true: np.ndarray,
    scores: Dict[str, np.ndarray],
    grid_size: int = 51,
) -> Dict[str, Any]:
    """Interpolate every model's ROC / PR curve onto a shared x grid for charting."""
    grid = np.linspace(0.0, 1.0, grid_size)
    roc_series: Dict[str, List[Optional[float]]] = {}
    pr_series: Dict[str, List[Optional[float]]] = {}

    if len(y_true) == 0 or len(np.unique(y_true)) < 2:
        return {"x": grid.round(4).tolist(), "roc": {}, "pr": {}}

    for name, score in scores.items():
        fpr, tpr, _ = roc_curve(y_true, score)
        roc_series[name] = np.interp(grid, fpr, tpr).round(4).tolist()

        precision, recall, _ = precision_recall_curve(y_true, score)
        order = np.argsort(recall)
        pr_series[name] = np.interp(grid, recall[order], precision[order]).round(4).tolist()

    return {"x": grid.round(4).tolist(), "roc": roc_series, "pr": pr_series}


def _confusion_counts(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, int]:
    if len(y_true) == 0:
        return {"tn": 0, "fp": 0, "fn": 0, "tp": 0}
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)}


def _feature_importance(model, X_test: np.ndarray, y_test: np.ndarray) -> List[Dict[str, Any]]:
    """Permutation importance on the test cutoff (only meaningful with both classes)."""
    if len(np.unique(y_test)) < 2:
        return []
    try:
        result = permutation_importance(
            model,
            X_test,
            y_test,
            n_repeats=5,
            random_state=RANDOM_SEED,
            scoring="roc_auc",
            n_jobs=1,
        )
    except Exception:
        return []

    rows = [
        {"feature": name, "importance": float(max(0.0, mean)), "std": float(std)}
        for name, mean, std in zip(FEATURE_COLUMNS, result.importances_mean, result.importances_std)
    ]
    rows.sort(key=lambda r: r["importance"], reverse=True)
    return rows


def evaluate_churn_models(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    feature_columns: Sequence[str] = FEATURE_COLUMNS,
) -> Dict[str, Any]:
    """
    Fit every model on the pooled training snapshots, choose each threshold on a
    validation split carved out of the training cutoffs, then score the held-out
    test cutoff exactly once.
    """
    if train_df.empty or test_df.empty:
        return {
            "leaderboard": [],
            "curves": {"x": [], "roc": {}, "pr": {}},
            "confusion_matrix": {"tn": 0, "fp": 0, "fn": 0, "tp": 0},
            "feature_importance": [],
            "best_model": None,
            "best_threshold": 0.5,
            "warnings": ["No snapshots available for training or testing."],
        }

    warnings: List[str] = []
    X_train_all = train_df[list(feature_columns)].to_numpy(dtype=float)
    y_train_all = train_df["label"].to_numpy(dtype=int)
    X_test = test_df[list(feature_columns)].to_numpy(dtype=float)
    y_test = test_df["label"].to_numpy(dtype=int)

    if not HAS_XGBOOST:
        warnings.append("XGBoost is not installed — HistGradientBoosting was used instead.")

    # Validation split from the training cutoffs only (never the test cutoff).
    stratify = y_train_all if min(np.bincount(y_train_all)) >= 2 else None
    X_fit, X_val, y_fit, y_val = train_test_split(
        X_train_all,
        y_train_all,
        test_size=PREDICTIVE_VALIDATION_FRACTION,
        random_state=RANDOM_SEED,
        stratify=stratify,
    )

    models = build_churn_models(y_fit)
    test_scores: Dict[str, np.ndarray] = {}
    leaderboard: List[Dict[str, Any]] = []
    best: Optional[Tuple[float, str, Any, float]] = None  # (val auc, name, model, threshold)

    for name, model in models.items():
        model.fit(X_fit, y_fit)
        val_score = model.predict_proba(X_val)[:, 1]
        threshold = select_threshold(y_val, val_score)
        if hasattr(model, "threshold_"):
            model.threshold_ = threshold

        val_auc = None
        if len(np.unique(y_val)) > 1:
            val_auc = float(roc_auc_score(y_val, val_score))

        # Refit on all training snapshots before touching the test cutoff.
        model.fit(X_train_all, y_train_all)
        if hasattr(model, "threshold_"):
            model.threshold_ = threshold

        test_score = model.predict_proba(X_test)[:, 1]
        test_scores[name] = test_score

        metrics = compute_binary_metrics(y_test, test_score, threshold)
        leaderboard.append(
            {
                "model": name,
                "is_baseline": name in BASELINE_MODELS,
                "threshold": round(float(threshold), 4),
                "validation_roc_auc": round(val_auc, 4) if val_auc is not None else None,
                "roc_auc": round(metrics["roc_auc"], 4) if metrics["roc_auc"] is not None else None,
                "pr_auc": round(metrics["pr_auc"], 4) if metrics["pr_auc"] is not None else None,
                "precision": round(metrics["precision"], 4) if metrics["precision"] is not None else None,
                "recall": round(metrics["recall"], 4) if metrics["recall"] is not None else None,
                "f1": round(metrics["f1"], 4) if metrics["f1"] is not None else None,
                "top_decile_lift": round(metrics["top_decile_lift"], 3)
                if metrics["top_decile_lift"] is not None
                else None,
            }
        )

        if name not in BASELINE_MODELS and val_auc is not None:
            if best is None or val_auc > best[0]:
                best = (val_auc, name, model, threshold)

    leaderboard.sort(
        key=lambda row: (row["roc_auc"] is not None, row["roc_auc"] or 0.0), reverse=True
    )

    if best is None:
        # Fall back to the best-ranked non-baseline model if validation AUCs were unusable.
        for row in leaderboard:
            if not row["is_baseline"] and row["model"] in models:
                best = (0.0, row["model"], models[row["model"]], row["threshold"])
                break

    best_name = best[1] if best else None
    best_model = best[2] if best else None
    best_threshold = best[3] if best else 0.5

    confusion = {"tn": 0, "fp": 0, "fn": 0, "tp": 0}
    importance: List[Dict[str, Any]] = []
    if best_model is not None:
        y_pred = (test_scores[best_name] >= best_threshold).astype(int)
        confusion = _confusion_counts(y_test, y_pred)
        importance = _feature_importance(best_model, X_test, y_test)

    if len(np.unique(y_test)) < 2:
        warnings.append(
            "The test cutoff contains a single outcome class, so AUC/PR metrics are unavailable."
        )

    return {
        "leaderboard": leaderboard,
        "curves": curve_payload(y_test, test_scores),
        "confusion_matrix": confusion,
        "feature_importance": importance,
        "best_model": best_name,
        "best_threshold": float(best_threshold),
        "warnings": warnings,
        "_test_scores": test_scores,
        "_models": models,
    }


# ---------------------------------------------------------
# Spend model (only feeds expected revenue at risk)
# ---------------------------------------------------------
def _build_spend_regressor():
    if HAS_XGBOOST:
        return XGBRegressor(
            n_estimators=300,
            max_depth=3,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.8,
            tree_method="hist",
            n_jobs=1,
            random_state=RANDOM_SEED,
        )
    return HistGradientBoostingRegressor(
        max_iter=250, learning_rate=0.05, max_depth=4, random_state=RANDOM_SEED
    )


def evaluate_spend_model(train_df: pd.DataFrame, test_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Predict log1p(spend in the next 90 days) vs a persistence baseline
    ("same as the last 90 days"). Reported with MAE and Spearman correlation.
    """
    empty = {
        "model": None,
        "mae_log": None,
        "mae_currency": None,
        "baseline_mae_currency": None,
        "spearman": None,
        "baseline_spearman": None,
        "skill_vs_baseline_pct": None,
    }
    if train_df.empty or test_df.empty:
        return empty

    columns = list(FEATURE_COLUMNS) + [SPEND_EXTRA_COLUMN]
    X_train = train_df[columns].to_numpy(dtype=float)
    y_train = np.log1p(train_df["spend_next_90"].to_numpy(dtype=float))
    X_test = test_df[columns].to_numpy(dtype=float)
    actual = test_df["spend_next_90"].to_numpy(dtype=float)
    baseline = test_df[SPEND_EXTRA_COLUMN].to_numpy(dtype=float)

    regressor = _build_spend_regressor()
    regressor.fit(X_train, y_train)
    pred_log = regressor.predict(X_test)
    pred = np.clip(np.expm1(pred_log), 0.0, None)

    mae_currency = float(mean_absolute_error(actual, pred))
    baseline_mae = float(mean_absolute_error(actual, baseline))

    spearman = None
    baseline_spearman = None
    if len(actual) > 2 and np.std(actual) > 0:
        try:
            spearman = float(spearmanr(pred, actual).correlation)
        except Exception:
            spearman = None
        try:
            baseline_spearman = float(spearmanr(baseline, actual).correlation)
        except Exception:
            baseline_spearman = None

    skill = None
    if baseline_mae > 0:
        skill = float((1.0 - mae_currency / baseline_mae) * 100.0)

    return {
        "model": "XGBoost regressor" if HAS_XGBOOST else "HistGradientBoosting regressor",
        "mae_log": float(mean_absolute_error(np.log1p(actual), pred_log)),
        "mae_currency": mae_currency,
        "baseline_mae_currency": baseline_mae,
        "spearman": spearman,
        "baseline_spearman": baseline_spearman,
        "skill_vs_baseline_pct": skill,
        "_predicted_spend": pred,
    }


# ---------------------------------------------------------
# Full pipeline + cache
# ---------------------------------------------------------
def _empty_result(message: str) -> Dict[str, Any]:
    return {
        "status": "insufficient_data",
        "message": message,
        "meta": {},
        "leaderboard": [],
        "curves": {"x": [], "roc": {}, "pr": {}},
        "confusion_matrix": {"tn": 0, "fp": 0, "fn": 0, "tp": 0},
        "feature_importance": [],
        "spend_model": {},
        "outreach": {"customers": [], "total_customers": 0, "total_expected_at_risk": 0.0},
        "warnings": [],
    }


def build_outreach_table(
    test_df: pd.DataFrame,
    churn_scores: np.ndarray,
    predicted_spend: np.ndarray,
) -> pd.DataFrame:
    """Expected revenue at risk = P(inactive) x predicted spend in the next 90 days."""
    frame = pd.DataFrame(
        {
            COL_CUST: test_df[COL_CUST].astype(str).to_numpy(),
            "churn_probability": np.asarray(churn_scores, dtype=float),
            "predicted_spend_90d": np.asarray(predicted_spend, dtype=float),
            "recent_spend_90d": test_df[SPEND_EXTRA_COLUMN].to_numpy(dtype=float),
            "lookback_monetary": np.expm1(test_df["log_monetary"].to_numpy(dtype=float)),
            "recency_days": np.expm1(test_df["log_recency"].to_numpy(dtype=float)),
            "orders_lookback": np.expm1(test_df["log_frequency"].to_numpy(dtype=float)),
        }
    )
    frame["orders_lookback"] = frame["orders_lookback"].round().astype(int)
    frame["recency_days"] = frame["recency_days"].round(1)
    frame["predicted_spend_90d"] = frame["predicted_spend_90d"].round(2)
    frame["recent_spend_90d"] = frame["recent_spend_90d"].round(2)
    frame["lookback_monetary"] = frame["lookback_monetary"].round(2)
    frame["churn_probability"] = frame["churn_probability"].round(4)
    frame["expected_revenue_at_risk"] = (
        frame["churn_probability"] * frame["predicted_spend_90d"]
    ).round(2)
    frame = frame.sort_values("expected_revenue_at_risk", ascending=False).reset_index(drop=True)

    total = float(frame["expected_revenue_at_risk"].sum())
    if total > 0:
        frame["cumulative_share_pct"] = (
            frame["expected_revenue_at_risk"].cumsum() / total * 100.0
        ).round(2)
    else:
        frame["cumulative_share_pct"] = 0.0
    frame["rank"] = np.arange(1, len(frame) + 1)
    return frame


def _cache_key(dataset_key: str, params: Dict[str, Any]) -> str:
    raw = "|".join(f"{k}={params[k]}" for k in sorted(params))
    digest = hashlib.sha256(f"{dataset_key}|{raw}|v2".encode("utf-8")).hexdigest()[:24]
    return digest


def run_predictive_pipeline(
    customer_df: pd.DataFrame,
    dataset_key: str,
    cancellations_df: Optional[pd.DataFrame] = None,
    use_cache: bool = True,
    lookback_days: int = PREDICTIVE_LOOKBACK_DAYS,
    horizon_days: int = PREDICTIVE_HORIZON_DAYS,
    n_train_cutoffs: int = PREDICTIVE_N_TRAIN_CUTOFFS,
    spacing_days: int = PREDICTIVE_TRAIN_CUTOFF_SPACING_DAYS,
) -> Dict[str, Any]:
    """
    End-to-end predictive payload: snapshots -> churn leaderboard -> spend model
    -> outreach ranking. Cached by dataset hash + hyperparameters.
    """
    if customer_df is None or len(customer_df) == 0:
        return _empty_result("No identified-customer transactions are loaded.")

    params = {
        "lookback": lookback_days,
        "horizon": horizon_days,
        "n_train": n_train_cutoffs,
        "spacing": spacing_days,
        "seed": RANDOM_SEED,
    }
    cache_path = os.path.join(PREDICTIVE_CACHE_DIR, f"predictive_{_cache_key(dataset_key, params)}.joblib")

    if use_cache and os.path.exists(cache_path):
        try:
            cached = joblib.load(cache_path)
            if isinstance(cached, dict) and cached.get("status") == "ok":
                cached.setdefault("meta", {})["from_cache"] = True
                return cached
        except Exception:
            pass  # Corrupt cache: refit.

    cutoffs = derive_cutoffs(
        customer_df,
        lookback_days=lookback_days,
        horizon_days=horizon_days,
        n_train_cutoffs=n_train_cutoffs,
        spacing_days=spacing_days,
    )
    if not cutoffs["ok"]:
        return _empty_result(cutoffs["reason"])

    train_df, test_df, used_train_cutoffs = build_all_snapshots(
        customer_df,
        cutoffs,
        lookback_days=lookback_days,
        horizon_days=horizon_days,
        cancellations_df=cancellations_df,
    )

    if len(test_df) < PREDICTIVE_MIN_CUSTOMERS or len(train_df) < PREDICTIVE_MIN_CUSTOMERS:
        return _empty_result(
            f"Only {len(test_df)} customers qualify at the test cutoff "
            f"({len(train_df)} across training cutoffs); at least "
            f"{PREDICTIVE_MIN_CUSTOMERS} are required for a stable evaluation."
        )

    if int(train_df["label"].nunique()) < 2:
        only = int(train_df["label"].iloc[0])
        outcome = "stopped buying" if only == 1 else "kept buying"
        return _empty_result(
            f"Every customer in the training snapshots {outcome} in the label window, so there is "
            "only one outcome class and a classifier cannot be trained or scored."
        )

    churn = evaluate_churn_models(train_df, test_df)
    spend = evaluate_spend_model(train_df, test_df)

    best_name = churn["best_model"]
    if best_name is None or best_name not in churn["_test_scores"]:
        return _empty_result("No churn model could be fitted on the available snapshots.")

    churn_scores = churn["_test_scores"][best_name]
    predicted_spend = spend.pop("_predicted_spend", np.zeros(len(test_df)))
    outreach_df = build_outreach_table(test_df, churn_scores, predicted_spend)

    total_at_risk = float(outreach_df["expected_revenue_at_risk"].sum())
    outreach_records = outreach_df.head(PREDICTIVE_OUTREACH_PAYLOAD_LIMIT).copy()
    for column in [
        "churn_probability",
        "predicted_spend_90d",
        "recent_spend_90d",
        "lookback_monetary",
        "recency_days",
        "expected_revenue_at_risk",
        "cumulative_share_pct",
    ]:
        outreach_records[column] = outreach_records[column].astype(float).round(4)
    outreach_records["orders_lookback"] = outreach_records["orders_lookback"].astype(int)

    warnings = list(churn["warnings"])
    if len(outreach_df) > PREDICTIVE_OUTREACH_PAYLOAD_LIMIT:
        warnings.append(
            f"The API payload lists the top {PREDICTIVE_OUTREACH_PAYLOAD_LIMIT} customers; "
            f"the CSV export contains all {len(outreach_df)}."
        )

    payload: Dict[str, Any] = {
        "status": "ok",
        "message": None,
        "meta": {
            "dataset_end": str(cutoffs["data_end"].date()),
            "dataset_start": str(cutoffs["data_start"].date()),
            "span_days": cutoffs["span_days"],
            "test_cutoff": str(pd.Timestamp(cutoffs["test_cutoff"]).date()),
            "train_cutoffs": [str(pd.Timestamp(c).date()) for c in used_train_cutoffs],
            "lookback_days": lookback_days,
            "horizon_days": horizon_days,
            "validation_fraction": PREDICTIVE_VALIDATION_FRACTION,
            "n_train_snapshots": int(len(train_df)),
            "n_test_customers": int(len(test_df)),
            "test_churn_rate": float(test_df["label"].mean()),
            "train_churn_rate": float(train_df["label"].mean()),
            "best_model": best_name,
            "best_threshold": float(churn["best_threshold"]),
            "feature_count": len(FEATURE_COLUMNS),
            "from_cache": False,
        },
        "leaderboard": churn["leaderboard"],
        "curves": churn["curves"],
        "confusion_matrix": churn["confusion_matrix"],
        "feature_importance": churn["feature_importance"],
        "spend_model": spend,
        "outreach": {
            "customers": outreach_records.to_dict(orient="records"),
            "total_customers": int(len(outreach_df)),
            "total_expected_at_risk": total_at_risk,
            "mean_churn_probability": float(np.mean(churn_scores)),
            "predicted_spend_total": float(np.sum(predicted_spend)),
        },
        "warnings": warnings,
        "_outreach_full": outreach_df,
    }

    try:
        os.makedirs(PREDICTIVE_CACHE_DIR, exist_ok=True)
        joblib.dump(payload, cache_path)
    except Exception:
        pass  # Caching is an optimisation; never fail the request because of it.

    return payload


def get_cached_pipeline(
    customer_df: pd.DataFrame,
    dataset_key: str,
    cancellations_df: Optional[pd.DataFrame] = None,
    use_cache: bool = True,
) -> Dict[str, Any]:
    """Cached payload for API use (drops the private full outreach frame)."""
    payload = run_predictive_pipeline(
        customer_df,
        dataset_key=dataset_key,
        cancellations_df=cancellations_df,
        use_cache=use_cache,
    )
    payload.pop("_outreach_full", None)
    return payload


def get_outreach_dataframe(
    customer_df: pd.DataFrame,
    dataset_key: str,
    cancellations_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """Full ranked outreach table (all customers) for CSV export."""
    payload = run_predictive_pipeline(
        customer_df,
        dataset_key=dataset_key,
        cancellations_df=cancellations_df,
        use_cache=True,
    )
    frame = payload.get("_outreach_full")
    if frame is None or not isinstance(frame, pd.DataFrame):
        return pd.DataFrame()
    return frame
