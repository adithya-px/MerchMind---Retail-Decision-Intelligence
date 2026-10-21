"""
Daily Sales Anomaly Detection Engine for RetailPulse.
Computes daily positive sales baseline using rolling statistics (median and IQR / z-score),
flags surges and sudden drops, and provides clear business interpretation.
"""

from typing import Dict, Any, Tuple
import pandas as pd
import numpy as np

from src.sales_analytics import compute_daily_trend


def detect_sales_anomalies(
    df: pd.DataFrame,
    window_days: int = 14,
    multiplier: float = 2.5,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Detects daily sales volume anomalies using a rolling baseline.

    Parameters:
        df: Positive sales transaction dataframe.
        window_days: Rolling window length in days for baseline.
        multiplier: IQR or sigma multiplier for upper/lower bounds.

    Returns:
        (anomaly_df, summary_metrics)
    """
    daily = compute_daily_trend(df)
    if len(daily) < 7:
        return pd.DataFrame(), {
            "total_days": len(daily),
            "surge_count": 0,
            "drop_count": 0,
            "total_anomalies": 0,
        }

    daily = daily.sort_values("Date").reset_index(drop=True)

    # Rolling median and IQR to be robust against prior outliers
    rolling_median = daily["PositiveSales"].rolling(window=window_days, min_periods=3, center=False).median()
    rolling_q25 = daily["PositiveSales"].rolling(window=window_days, min_periods=3, center=False).quantile(0.25)
    rolling_q75 = daily["PositiveSales"].rolling(window=window_days, min_periods=3, center=False).quantile(0.75)
    rolling_iqr = rolling_q75 - rolling_q25

    daily["Baseline"] = rolling_median.bfill()
    daily["UpperBound"] = (daily["Baseline"] + multiplier * rolling_iqr).bfill()
    daily["LowerBound"] = (daily["Baseline"] - multiplier * rolling_iqr).clip(lower=0).bfill()

    is_surge = daily["PositiveSales"] > daily["UpperBound"]
    is_drop = (daily["PositiveSales"] < daily["LowerBound"]) & (daily["PositiveSales"] > 0)

    daily["IsAnomaly"] = is_surge | is_drop
    daily["AnomalyType"] = np.where(is_surge, "Surge (Spike)", np.where(is_drop, "Drop (Plunge)", "Normal"))

    surge_count = int(is_surge.sum())
    drop_count = int(is_drop.sum())

    summary = {
        "total_days": len(daily),
        "surge_count": surge_count,
        "drop_count": drop_count,
        "total_anomalies": surge_count + drop_count,
    }

    return daily, summary
