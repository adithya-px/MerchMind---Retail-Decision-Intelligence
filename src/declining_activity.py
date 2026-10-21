"""
Declining-Activity Detection Engine for RetailPulse.
Heuristically flags customers whose purchasing cadence or monetary spend has dropped
relative to their prior baseline window, and ranks them for marketing re-engagement.
Clearly designated as a heuristic indicator, not a predictive churn model.
"""

from typing import Dict, Any, Tuple, Optional
import pandas as pd
import numpy as np

from src.config import (
    COL_INVOICE,
    COL_DATE,
    COL_CUST,
    COL_LINE_REVENUE,
    DEFAULT_RECENT_WINDOW_DAYS,
    DEFAULT_PRIOR_WINDOW_DAYS,
    MIN_TRANSACTIONS_FOR_DECLINE,
    MIN_PAST_SPEND_FOR_DECLINE,
    GUEST_CUSTOMER_LABEL,
)


def detect_declining_customers(
    customer_df: pd.DataFrame,
    recent_window_days: int = DEFAULT_RECENT_WINDOW_DAYS,
    prior_window_days: int = DEFAULT_PRIOR_WINDOW_DAYS,
    min_prior_orders: int = MIN_TRANSACTIONS_FOR_DECLINE,
    min_prior_spend: float = MIN_PAST_SPEND_FOR_DECLINE,
    reference_date: Optional[pd.Timestamp] = None,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Identifies previously active customers whose activity is declining.

    Two heuristic mechanisms:
    1. Spend / Order Drop: spend in recent window dropped significantly vs prior window of equal length.
    2. Cadence Lapse: recency exceeds 1.5x customer's historical median inter-purchase gap.

    Customers with insufficient history (< min_prior_orders or < min_prior_spend)
    are explicitly excluded from decline flagging.

    Returns:
        (ranked_reengage_df, summary_metrics)
    """
    if customer_df.empty:
        return pd.DataFrame(), {
            "total_evaluated": 0,
            "flagged_declining": 0,
            "excluded_insufficient_history": 0,
            "revenue_at_risk": 0.0,
        }

    clean = customer_df[customer_df[COL_CUST] != GUEST_CUSTOMER_LABEL].copy()
    if clean.empty:
        return pd.DataFrame(), {
            "total_evaluated": 0,
            "flagged_declining": 0,
            "excluded_insufficient_history": 0,
            "revenue_at_risk": 0.0,
        }

    max_dt = clean[COL_DATE].max()
    ref_dt = pd.to_datetime(reference_date) if reference_date is not None else (max_dt + pd.Timedelta(days=1))

    # Time boundaries
    recent_start = ref_dt - pd.Timedelta(days=recent_window_days)
    prior_start = recent_start - pd.Timedelta(days=prior_window_days)

    # 1. Split transactions by window
    recent_tx = clean[(clean[COL_DATE] >= recent_start) & (clean[COL_DATE] <= ref_dt)]
    prior_tx = clean[(clean[COL_DATE] >= prior_start) & (clean[COL_DATE] < recent_start)]

    recent_summary = (
        recent_tx.groupby(COL_CUST)
        .agg(
            RecentSpend=(COL_LINE_REVENUE, "sum"),
            RecentOrders=(COL_INVOICE, "nunique"),
            LastRecentDate=(COL_DATE, "max"),
        )
    )

    prior_summary = (
        prior_tx.groupby(COL_CUST)
        .agg(
            PriorSpend=(COL_LINE_REVENUE, "sum"),
            PriorOrders=(COL_INVOICE, "nunique"),
            LastPriorDate=(COL_DATE, "max"),
        )
    )

    # Overall customer lifetime stats for cadence analysis
    all_cust_orders = (
        clean.groupby([COL_CUST, COL_INVOICE])[COL_DATE]
        .min()
        .reset_index()
        .sort_values([COL_CUST, COL_DATE])
    )

    # Inter-purchase gap calculation
    all_cust_orders["PrevOrderDate"] = all_cust_orders.groupby(COL_CUST)[COL_DATE].shift(1)
    all_cust_orders["DaysBetweenOrders"] = (all_cust_orders[COL_DATE] - all_cust_orders["PrevOrderDate"]).dt.days

    cadence_summary = (
        all_cust_orders.groupby(COL_CUST)
        .agg(
            MedianCadenceDays=("DaysBetweenOrders", "median"),
            TotalLifetimeOrders=(COL_INVOICE, "nunique"),
            LastOverallPurchase=(COL_DATE, "max"),
        )
    )

    # Merge windows
    merged = cadence_summary.join(prior_summary, how="left").join(recent_summary, how="left")
    merged["PriorSpend"] = merged["PriorSpend"].fillna(0.0)
    merged["PriorOrders"] = merged["PriorOrders"].fillna(0).astype(int)
    merged["RecentSpend"] = merged["RecentSpend"].fillna(0.0)
    merged["RecentOrders"] = merged["RecentOrders"].fillna(0).astype(int)
    merged["DaysSinceLastPurchase"] = (ref_dt - merged["LastOverallPurchase"]).dt.days.clip(lower=0)

    # Exclusions: Must have established activity in the prior window
    has_sufficient_history = (
        (merged["PriorOrders"] >= min_prior_orders)
        & (merged["PriorSpend"] >= min_prior_spend)
    )

    excluded_count = int((~has_sufficient_history).sum())
    eligible = merged[has_sufficient_history].copy()

    # Drop calculations
    eligible["SpendDrop"] = eligible["PriorSpend"] - eligible["RecentSpend"]
    eligible["SpendDropPct"] = (
        (eligible["SpendDrop"] / eligible["PriorSpend"]) * 100.0
    ).clip(lower=0.0, upper=100.0)
    eligible["OrderDrop"] = eligible["PriorOrders"] - eligible["RecentOrders"]

    # Cadence lapse condition
    cadence_lapsed = (
        eligible["MedianCadenceDays"].notna()
        & (eligible["MedianCadenceDays"] > 0)
        & (eligible["DaysSinceLastPurchase"] > (1.5 * eligible["MedianCadenceDays"]))
    )

    # Monetary drop condition (>= 40% drop in spend)
    monetary_declining = eligible["SpendDropPct"] >= 40.0

    eligible["IsDeclining"] = monetary_declining | cadence_lapsed

    # Rationalization reason
    def assign_decline_reason(row):
        reasons = []
        if row["RecentOrders"] == 0:
            reasons.append("Zero orders in recent window")
        elif row["SpendDropPct"] >= 50.0:
            reasons.append(f"Spend dropped {row['SpendDropPct']:.0f}%")
        if pd.notna(row["MedianCadenceDays"]) and row["DaysSinceLastPurchase"] > (1.5 * row["MedianCadenceDays"]):
            reasons.append(
                f"Lapsed cadence ({row['DaysSinceLastPurchase']}d vs typical {row['MedianCadenceDays']:.0f}d gap)"
            )
        return " & ".join(reasons) if reasons else "Slight order/spend slowdown"

    eligible["DeclineReason"] = eligible.apply(assign_decline_reason, axis=1)

    flagged_df = (
        eligible[eligible["IsDeclining"]]
        .sort_values(by=["SpendDrop", "PriorSpend"], ascending=False)
        .reset_index()
    )

    summary_metrics = {
        "total_evaluated": len(merged),
        "eligible_customers": len(eligible),
        "excluded_insufficient_history": excluded_count,
        "flagged_declining": len(flagged_df),
        "revenue_at_risk": float(flagged_df["SpendDrop"].sum()),
        "avg_drop_pct": float(flagged_df["SpendDropPct"].mean()) if len(flagged_df) > 0 else 0.0,
    }

    return flagged_df, summary_metrics
