"""
Sales analytics and revenue intelligence engine for MerchMind.
Decoupled pure computational module for KPIs, trends, Pareto concentration,
revenue drivers, and dynamically generated findings.
"""

from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np

from src.config import (
    COL_INVOICE,
    COL_STOCK,
    COL_DESC,
    COL_QTY,
    COL_DATE,
    COL_PRICE,
    COL_CUST,
    COL_COUNTRY,
    COL_LINE_REVENUE,
    COL_IS_GUEST,
    GUEST_CUSTOMER_LABEL,
)


def filter_data(
    df: pd.DataFrame,
    start_date: Optional[pd.Timestamp] = None,
    end_date: Optional[pd.Timestamp] = None,
    countries: Optional[List[str]] = None,
    products: Optional[List[str]] = None,
) -> pd.DataFrame:
    """Filter sales dataset uniformly across dates, countries, and products."""
    filtered = df.copy()

    if start_date is not None:
        filtered = filtered[filtered[COL_DATE] >= pd.to_datetime(start_date)]
    if end_date is not None:
        filtered = filtered[filtered[COL_DATE] <= pd.to_datetime(end_date)]
    if countries and "All" not in countries:
        filtered = filtered[filtered[COL_COUNTRY].isin(countries)]
    if products and "All" not in products:
        filtered = filtered[filtered[COL_STOCK].isin(products) | filtered[COL_DESC].isin(products)]

    return filtered


def compute_kpis(
    df: pd.DataFrame,
    cancellations_df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """Calculate core sales performance metrics."""
    if df.empty:
        return {
            "total_positive_sales": 0.0,
            "distinct_invoices": 0,
            "unique_customers": 0,
            "distinct_products": 0,
            "avg_order_value": 0.0,
            "total_quantity": 0,
            "guest_orders": 0,
            "cancellation_rate_pct": 0.0,
        }

    total_sales = float(df[COL_LINE_REVENUE].sum())
    distinct_invoices = int(df[COL_INVOICE].nunique())

    # Non-guest distinct customers
    id_cust_mask = df[COL_CUST] != GUEST_CUSTOMER_LABEL
    unique_customers = int(df.loc[id_cust_mask, COL_CUST].nunique())

    distinct_products = int(df[COL_STOCK].nunique())
    avg_order_value = (total_sales / distinct_invoices) if distinct_invoices > 0 else 0.0
    total_quantity = int(df[COL_QTY].sum())
    guest_orders = int(df.loc[~id_cust_mask, COL_INVOICE].nunique())

    cancellation_rate_pct = 0.0
    if cancellations_df is not None and not cancellations_df.empty:
        cancelled_invoices = int(cancellations_df[COL_INVOICE].nunique()) if COL_INVOICE in cancellations_df.columns else 0
        total_order_count = distinct_invoices + cancelled_invoices
        cancellation_rate_pct = (cancelled_invoices / total_order_count * 100.0) if total_order_count > 0 else 0.0

    return {
        "total_positive_sales": total_sales,
        "distinct_invoices": distinct_invoices,
        "unique_customers": unique_customers,
        "distinct_products": distinct_products,
        "avg_order_value": avg_order_value,
        "total_quantity": total_quantity,
        "guest_orders": guest_orders,
        "cancellation_rate_pct": cancellation_rate_pct,
    }


def compute_monthly_trend(df: pd.DataFrame) -> pd.DataFrame:
    """Monthly positive sales value, order counts, and MoM growth rate."""
    if df.empty:
        return pd.DataFrame(columns=["YearMonth", "PositiveSales", "Orders", "MoM_Growth_Pct"])

    monthly = (
        df.groupby("YearMonth")
        .agg(
            PositiveSales=(COL_LINE_REVENUE, "sum"),
            Orders=(COL_INVOICE, "nunique"),
        )
        .reset_index()
        .sort_values("YearMonth")
    )
    monthly["MoM_Growth_Pct"] = monthly["PositiveSales"].pct_change() * 100.0
    return monthly


def compute_daily_trend(df: pd.DataFrame) -> pd.DataFrame:
    """Daily positive sales value and order volume."""
    if df.empty:
        return pd.DataFrame(columns=["Date", "PositiveSales", "Orders"])

    daily = (
        df.groupby("Date")
        .agg(
            PositiveSales=(COL_LINE_REVENUE, "sum"),
            Orders=(COL_INVOICE, "nunique"),
        )
        .reset_index()
        .sort_values("Date")
    )
    return daily


def top_products(
    df: pd.DataFrame,
    by: str = "LineRevenue",
    top_n: int = 10,
) -> pd.DataFrame:
    """Top products by revenue or quantity."""
    if df.empty:
        return pd.DataFrame(columns=["Description", "StockCode", "Value"])

    agg_col = COL_LINE_REVENUE if by == "LineRevenue" else COL_QTY
    top = (
        df.groupby(["StockCode", "Description"])[agg_col]
        .sum()
        .reset_index()
        .sort_values(by=agg_col, ascending=False)
        .head(top_n)
    )
    top.rename(columns={agg_col: "Value"}, inplace=True)
    return top


def top_countries_by_revenue(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Geographic breakdown of positive sales value and share."""
    if df.empty:
        return pd.DataFrame(columns=["Country", "PositiveSales", "SharePct"])

    total_sales = df[COL_LINE_REVENUE].sum()
    country_sales = (
        df.groupby(COL_COUNTRY)[COL_LINE_REVENUE]
        .sum()
        .reset_index()
        .rename(columns={COL_LINE_REVENUE: "PositiveSales"})
        .sort_values(by="PositiveSales", ascending=False)
        .head(top_n)
    )
    country_sales["SharePct"] = (
        (country_sales["PositiveSales"] / total_sales * 100.0) if total_sales > 0 else 0.0
    )
    return country_sales


def compute_order_values(df: pd.DataFrame) -> pd.Series:
    """Compute aggregate value per distinct invoice order."""
    if df.empty:
        return pd.Series(dtype=float)
    return df.groupby(COL_INVOICE)[COL_LINE_REVENUE].sum()


def compute_pareto_concentration(customer_df: pd.DataFrame) -> Tuple[pd.DataFrame, float]:
    """
    Computes cumulative customer revenue concentration (Pareto principle).
    Returns (pareto_df, top_20_pct_revenue_share).
    """
    if customer_df.empty:
        return pd.DataFrame(), 0.0

    cust_revenue = (
        customer_df.groupby(COL_CUST)[COL_LINE_REVENUE]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )
    total_revenue = cust_revenue[COL_LINE_REVENUE].sum()
    if total_revenue <= 0:
        return pd.DataFrame(), 0.0

    cust_revenue["CumulativeRevenue"] = cust_revenue[COL_LINE_REVENUE].cumsum()
    cust_revenue["CumulativeSharePct"] = (cust_revenue["CumulativeRevenue"] / total_revenue) * 100.0
    cust_revenue["CustomerPercentile"] = ((cust_revenue.index + 1) / len(cust_revenue)) * 100.0

    # Top 20% customers revenue share
    top_20_cutoff = int(np.ceil(0.20 * len(cust_revenue)))
    top_20_share = float(cust_revenue.iloc[min(top_20_cutoff - 1, len(cust_revenue) - 1)]["CumulativeSharePct"])

    return cust_revenue, top_20_share


def compute_weekday_hourly_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """Pivot table of sales volume by day of week and hour."""
    if df.empty:
        return pd.DataFrame()

    ordered_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    pivot = (
        df.groupby(["DayOfWeek", "Hour"])[COL_LINE_REVENUE]
        .sum()
        .unstack(fill_value=0)
    )
    # Reindex days that exist
    present_days = [d for d in ordered_days if d in pivot.index]
    return pivot.reindex(present_days)


def what_drives_revenue_analysis(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Detailed contribution analysis:
    - Share of revenue from top 10 products
    - Share from top country
    - Month-over-month drivers (latest month vs previous month change decomposition)
    """
    if df.empty:
        return {
            "top_10_product_share": 0.0,
            "top_country": "N/A",
            "top_country_share": 0.0,
            "mom_delta": 0.0,
            "mom_pct_change": 0.0,
            "latest_month": "N/A",
            "prior_month": "N/A",
            "growing_products": [],
            "declining_products": [],
        }

    total_sales = float(df[COL_LINE_REVENUE].sum())

    # Top 10 products share
    top_10_prod_rev = float(df.groupby(COL_STOCK)[COL_LINE_REVENUE].sum().nlargest(10).sum())
    top_10_share = (top_10_prod_rev / total_sales * 100.0) if total_sales > 0 else 0.0

    # Country share
    country_totals = df.groupby(COL_COUNTRY)[COL_LINE_REVENUE].sum()
    top_country = str(country_totals.idxmax()) if not country_totals.empty else "N/A"
    top_country_share = (float(country_totals.max()) / total_sales * 100.0) if total_sales > 0 else 0.0

    # MoM drivers
    monthly = compute_monthly_trend(df)
    mom_delta = 0.0
    mom_pct = 0.0
    latest_m = "N/A"
    prior_m = "N/A"
    growing_products = []
    declining_products = []

    if len(monthly) >= 2:
        latest_row = monthly.iloc[-1]
        prior_row = monthly.iloc[-2]
        latest_m = str(latest_row["YearMonth"])
        prior_m = str(prior_row["YearMonth"])
        mom_delta = float(latest_row["PositiveSales"] - prior_row["PositiveSales"])
        mom_pct = float(latest_row["MoM_Growth_Pct"])

        # Compare product movements between latest 2 months
        p_latest = df[df["YearMonth"] == latest_m].groupby(COL_DESC)[COL_LINE_REVENUE].sum()
        p_prior = df[df["YearMonth"] == prior_m].groupby(COL_DESC)[COL_LINE_REVENUE].sum()
        p_diff = (p_latest.subtract(p_prior, fill_value=0)).sort_values(ascending=False)

        growing_products = [
            {"product": idx, "delta": float(val)}
            for idx, val in p_diff.head(3).items()
            if val > 0
        ]
        declining_products = [
            {"product": idx, "delta": float(val)}
            for idx, val in p_diff.tail(3).items()
            if val < 0
        ]

    return {
        "top_10_product_share": top_10_share,
        "top_country": top_country,
        "top_country_share": top_country_share,
        "mom_delta": mom_delta,
        "mom_pct_change": mom_pct,
        "latest_month": latest_m,
        "prior_month": prior_m,
        "growing_products": growing_products,
        "declining_products": declining_products,
    }


def generate_sales_insights(
    kpis: Dict[str, Any],
    pareto_share: float,
    drivers: Dict[str, Any],
    guest_metrics: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """Dynamically generates executive insights strictly derived from computed numbers."""
    insights = []

    # 1. Total Volume & Order Value
    insights.append(
        f"**Revenue Benchmark**: Generated **${kpis['total_positive_sales']:,.2f}** in positive sales value "
        f"across **{kpis['distinct_invoices']:,}** orders, yielding an Average Order Value (AOV) of **${kpis['avg_order_value']:,.2f}**."
    )

    # 2. Pareto Customer Concentration
    if pareto_share > 0:
        insights.append(
            f"**Customer Concentration (Pareto)**: The top 20% of identified customers generate **{pareto_share:.1f}%** "
            f"of total tracked customer revenue, indicating high revenue dependence on key accounts."
        )

    # 3. Product & Country Concentration
    insights.append(
        f"**Catalog & Geography Exposure**: The top 10 products account for **{drivers['top_10_product_share']:.1f}%** "
        f"of total positive sales. Geographically, **{drivers['top_country']}** dominates with **{drivers['top_country_share']:.1f}%** of sales."
    )

    # 4. MoM Trajectory
    if drivers["latest_month"] != "N/A" and drivers["prior_month"] != "N/A":
        direction = "expanded" if drivers["mom_delta"] >= 0 else "contracted"
        insights.append(
            f"**Recent Momentum**: Between {drivers['prior_month']} and {drivers['latest_month']}, monthly sales {direction} by "
            f"**${abs(drivers['mom_delta']):,.2f}** ({drivers['mom_pct_change']:+.1f}%)."
        )

    # 5. Guest Checkout Impact
    if guest_metrics and guest_metrics.get("guest_revenue_share_pct", 0) > 0:
        insights.append(
            f"**Guest Account Opportunity**: Unidentified / guest checkouts represent **{guest_metrics['guest_revenue_share_pct']:.1f}%** "
            f"of gross positive sales (${guest_metrics['guest_sales_value']:,.2f}). Implementing an account signup incentive could capture these buyer profiles."
        )

    return insights
