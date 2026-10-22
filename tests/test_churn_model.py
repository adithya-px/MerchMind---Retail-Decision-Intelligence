"""
Tests for the predictive churn layer: label construction, leakage safety, and
graceful degradation. These are the three checks the model's validity depends on.
"""

import numpy as np
import pandas as pd
import pytest

from src.churn_model import (
    FEATURE_COLUMNS,
    build_all_snapshots,
    build_snapshot,
    derive_cutoffs,
    run_predictive_pipeline,
)


def _frame(rows):
    return pd.DataFrame(
        rows,
        columns=[
            "CustomerID",
            "InvoiceNo",
            "InvoiceDate",
            "LineRevenue",
            "StockCode",
            "Country",
        ],
    )


def _expand(customers, dates, amount=100.0, start_invoice=1000):
    """One invoice per (customer, date) pair, unique invoice numbers."""
    rows = []
    invoice = start_invoice
    for customer in customers:
        for date in dates:
            rows.append(
                [customer, str(invoice), pd.Timestamp(date), amount, "SKU1", "United Kingdom"]
            )
            invoice += 1
    return rows


def test_label_construction_on_hand_made_example():
    """
    Cutoff 2021-09-01, lookback 180d (from 2021-03-05), horizon 90d (to 2021-11-30).
    A: bought in lookback, nothing afterwards          -> label 1
    B: bought in lookback, bought 2021-09-20 (in horizon) -> label 0
    C: bought in lookback, bought exactly 2021-11-30 (last horizon day) -> label 0
    D: last purchase 2021-01-10, before the lookback   -> not in the snapshot
    E: first purchase 2021-10-01, after the cutoff     -> not in the snapshot
    """
    df = _frame(
        [
            ["A", "A1", pd.Timestamp("2021-04-10"), 100.0, "SKU1", "United Kingdom"],
            ["A", "A2", pd.Timestamp("2021-08-01"), 50.0, "SKU2", "United Kingdom"],
            ["B", "B1", pd.Timestamp("2021-05-01"), 200.0, "SKU1", "United Kingdom"],
            ["B", "B2", pd.Timestamp("2021-09-20"), 80.0, "SKU1", "United Kingdom"],
            ["C", "C1", pd.Timestamp("2021-04-15"), 60.0, "SKU3", "Germany"],
            ["C", "C2", pd.Timestamp("2021-11-30"), 40.0, "SKU3", "Germany"],
            ["D", "D1", pd.Timestamp("2021-01-10"), 500.0, "SKU1", "United Kingdom"],
            ["E", "E1", pd.Timestamp("2021-10-01"), 70.0, "SKU1", "United Kingdom"],
        ]
    )

    snapshot = build_snapshot(df, "2021-09-01", lookback_days=180, horizon_days=90)
    snapshot = snapshot.set_index("CustomerID")

    assert set(snapshot.index) == {"A", "B", "C"}
    assert snapshot.loc["A", "label"] == 1
    assert snapshot.loc["B", "label"] == 0
    assert snapshot.loc["C", "label"] == 0

    # Future spend is the horizon-window target, not lifetime spend.
    assert snapshot.loc["A", "spend_next_90"] == pytest.approx(0.0)
    assert snapshot.loc["B", "spend_next_90"] == pytest.approx(80.0)
    assert snapshot.loc["C", "spend_next_90"] == pytest.approx(40.0)

    # Lookback features must ignore the horizon purchase.
    assert snapshot.loc["B", "log_monetary"] == pytest.approx(np.log1p(200.0))
    assert snapshot.loc["B", "log_frequency"] == pytest.approx(np.log1p(1.0))
    assert snapshot.loc["A", "log_frequency"] == pytest.approx(np.log1p(2.0))
    assert snapshot.loc["A", "is_uk"] == pytest.approx(1.0)
    assert snapshot.loc["C", "is_uk"] == pytest.approx(0.0)


def test_features_do_not_leak_from_after_the_cutoff():
    cutoff = pd.Timestamp("2021-09-01")
    base_rows = _expand(
        ["A", "B", "C", "D"],
        [
            "2021-04-02 10:00",
            "2021-05-15 11:00",
            "2021-07-01 09:30",
            "2021-08-20 16:00",
        ],
    )
    base_rows += _expand(["B"], ["2021-09-20 12:00"], amount=90.0, start_invoice=5000)
    baseline_df = _frame(base_rows)

    snapshot_before = build_snapshot(baseline_df, cutoff)

    # Rewrite everything after the cutoff: bigger baskets, more orders, new customers.
    after_mask = baseline_df["InvoiceDate"] > cutoff
    mutated = baseline_df.copy()
    mutated.loc[after_mask, "LineRevenue"] = mutated.loc[after_mask, "LineRevenue"] * 25.0
    mutated.loc[after_mask, "InvoiceNo"] = "X" + mutated.loc[after_mask, "InvoiceNo"]

    extra_rows = _expand(
        ["B", "Z"],
        ["2021-09-05 09:00", "2021-09-25 09:00", "2021-10-30 09:00"],
        amount=9999.0,
        start_invoice=9000,
    )
    mutated_df = pd.concat([mutated, _frame(extra_rows)], ignore_index=True)

    snapshot_after = build_snapshot(mutated_df, cutoff)

    assert list(snapshot_before["CustomerID"]) == list(snapshot_after["CustomerID"])
    assert "Z" not in set(snapshot_after["CustomerID"])  # post-cutoff-only customer is excluded

    np.testing.assert_allclose(
        snapshot_before[FEATURE_COLUMNS].to_numpy(dtype=float),
        snapshot_after[FEATURE_COLUMNS].to_numpy(dtype=float),
        rtol=0,
        atol=0,
        err_msg="Features changed when post-cutoff transactions were altered (leakage).",
    )


def _long_history_frame(customers, include_horizon_purchase=True):
    rows = []
    for index, customer in enumerate(customers):
        rows += _expand(
            [customer],
            ["2019-12-01", "2020-06-01", "2020-08-01", "2020-10-01", "2020-11-10"],
            start_invoice=1000 + index * 10,
        )
        if include_horizon_purchase:
            rows += _expand([customer], ["2020-12-20"], start_invoice=8000 + index * 10)
    return _frame(rows)


def test_training_label_windows_never_overlap_the_test_cutoff():
    """
    Regression guard for temporal leakage: every training snapshot's 90-day label
    window must end on or before the test cutoff, otherwise the training labels
    are built from the very period the test set is meant to be held out from.
    """
    df = _long_history_frame([f"C{i:03d}" for i in range(20)], include_horizon_purchase=True)

    cutoffs = derive_cutoffs(
        df, lookback_days=90, horizon_days=90, n_train_cutoffs=2, spacing_days=30
    )
    assert cutoffs["ok"]

    test_cutoff = cutoffs["test_cutoff"]
    horizon = pd.Timedelta(days=90)
    assert len(cutoffs["train_cutoffs"]) == 2

    for cutoff in cutoffs["train_cutoffs"]:
        assert cutoff + horizon <= test_cutoff, (
            f"training label window for {cutoff} extends into the test label window"
        )

    # Latest training cutoff sits exactly one horizon before the test cutoff.
    assert cutoffs["train_cutoffs"][-1] == test_cutoff - horizon
    # The earlier cutoff steps back another 30 days.
    assert (cutoffs["train_cutoffs"][-1] - cutoffs["train_cutoffs"][0]).days == 30
    # A shortened lookback still leaves every cutoff with full feature history.
    for cutoff in cutoffs["train_cutoffs"]:
        assert cutoff - pd.Timedelta(days=90) >= cutoffs["data_start"]

    # The snapshots actually built agree with those cutoffs.
    train_df, test_df, used = build_all_snapshots(df, cutoffs, lookback_days=90, horizon_days=90)
    assert set(pd.to_datetime(train_df["cutoff"]).unique()) <= set(used)
    for cutoff in pd.to_datetime(train_df["cutoff"]).unique():
        assert cutoff + horizon <= pd.Timestamp(test_df["cutoff"].iloc[0])


def test_single_outcome_class_is_handled_gracefully():
    # 60 customers, all of whom buy again inside the label window -> every label is 0.
    df = _long_history_frame([f"C{i:03d}" for i in range(60)], include_horizon_purchase=True)

    result = run_predictive_pipeline(df, dataset_key="test-single-class", use_cache=False)

    assert result["status"] == "insufficient_data"
    assert "one outcome class" in result["message"]
    assert result["leaderboard"] == []
    assert result["outreach"]["customers"] == []


def test_too_few_customers_is_handled_gracefully():
    df = _long_history_frame(["C1", "C2", "C3"], include_horizon_purchase=False)

    result = run_predictive_pipeline(df, dataset_key="test-too-few", use_cache=False)

    assert result["status"] == "insufficient_data"
    assert "required for a stable evaluation" in result["message"]
    assert result["meta"] == {}


def test_empty_input_returns_empty_snapshot():
    empty = pd.DataFrame(
        columns=["CustomerID", "InvoiceNo", "InvoiceDate", "LineRevenue", "StockCode", "Country"]
    )
    snapshot = build_snapshot(empty, "2021-09-01")
    assert snapshot.empty
    assert list(snapshot.columns) == ["CustomerID"] + FEATURE_COLUMNS + [
        "label",
        "spend_next_90",
        "spend_last_90",
        "cutoff",
    ]

    result = run_predictive_pipeline(empty, dataset_key="test-empty", use_cache=False)
    assert result["status"] == "insufficient_data"
