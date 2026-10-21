"""
Unit tests for sales anomaly detection engine.
"""

import pytest
import pandas as pd
from src.anomaly_detection import detect_sales_anomalies


def test_detect_sales_anomalies():
    # 20 days of steady sales ~ 100, day 15 has sudden spike of 1000
    dates = pd.date_range("2021-01-01", periods=20, freq="D")
    records = []
    for d in dates:
        rev = 1000.0 if d.day == 15 else 100.0
        records.append({
            "InvoiceDate": d,
            "Date": d.date(),
            "InvoiceNo": f"INV_{d.day}",
            "LineRevenue": rev,
        })
    df = pd.DataFrame(records)

    anomaly_df, summary = detect_sales_anomalies(df, window_days=7, multiplier=2.0)
    assert not anomaly_df.empty
    assert summary["surge_count"] >= 1
    # Day 15 must be flagged as Surge
    spike_row = anomaly_df[anomaly_df["Date"] == pd.to_datetime("2021-01-15").date()].iloc[0]
    assert spike_row["IsAnomaly"] == True
    assert "Surge" in spike_row["AnomalyType"]
