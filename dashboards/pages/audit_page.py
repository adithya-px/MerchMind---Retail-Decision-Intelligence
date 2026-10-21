"""
Data Quality & Cleaning Audit Dashboard Page.
Renders transparent step-by-step pipeline audit records, return/cancellation segregation,
non-product exclusion policies, and guest customer revenue impact analysis.
"""

import streamlit as st
import pandas as pd
import plotly.express as px

from src.cleaning import CleaningAuditLogger
from src.config import NON_PRODUCT_STOCK_CODES


def render(
    sales_df: pd.DataFrame,
    customer_df: pd.DataFrame,
    guest_metrics: dict,
    audit_logger: CleaningAuditLogger,
    cancellations_df: pd.DataFrame,
) -> None:
    st.title("📋 Data Quality & Cleaning Audit")
    st.caption("Complete transparency into data cleaning rules, exclusions, and financial integrity checks.")

    # 1. Pipeline Summary KPIs
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Clean Sales Records", f"{len(sales_df):,}", help="Verified positive sales transactions.")
    c2.metric("Isolated Cancellations/Returns", f"{len(cancellations_df):,}", help="Segregated return transactions.")
    c3.metric(
        "Guest Revenue Share",
        f"{guest_metrics.get('guest_revenue_share_pct', 0.0):.2f}%",
        help="Percentage of positive sales value attributed to anonymous guest checkouts.",
    )
    c4.metric(
        "Guest Volume Share",
        f"{guest_metrics.get('guest_row_share_pct', 0.0):.2f}%",
        help="Percentage of line item transactions without an identified CustomerID.",
    )

    st.markdown("---")

    # 2. Step-by-Step Audit Log Table
    st.subheader("📜 Pipeline Audit Log")
    st.markdown(
        "Every row dropped, transformed, or isolated is tracked with an explicit business justification to prevent silent loss of data."
    )

    if audit_logger:
        log_df = audit_logger.to_dataframe()
        st.dataframe(
            log_df.style.format({
                "Rows Before": "{:,}",
                "Rows Affected": "{:,}",
                "Rows After": "{:,}",
            }),
            width="stretch",
        )
    else:
        st.info("Audit log unavailable.")

    st.markdown("---")

    # 3. Handling Policies Deep Dive
    col_guest, col_returns = st.columns(2)

    with col_guest:
        st.subheader("👤 Missing CustomerID Policy")
        st.markdown(
            f"""
            * **Policy**: Unidentified customer checkouts are **RETAINED** for sales analytics (labeled as `Guest / Unidentified`)
              and **EXCLUDED** from customer-level RFM and K-Means segmentation.
            * **Financial Impact**:
              - Total Guest Sales Value: **${guest_metrics.get('guest_sales_value', 0.0):,.2f}**
              - Revenue Share Affected: **{guest_metrics.get('guest_revenue_share_pct', 0.0):.2f}%**
              - Transaction Rows: **{guest_metrics.get('guest_rows', 0):,}** ({guest_metrics.get('guest_row_share_pct', 0.0):.2f}%)
            * **Rationale**: Silently dropping guest transactions would materially understate overall retail sales and distort channel volume.
            """
        )

    with col_returns:
        st.subheader("↩️ Cancellations & Returns Policy")
        st.markdown(
            f"""
            * **Policy**: Transactions with `InvoiceNo` starting with `'C'` or negative quantities are segregated into a dedicated returns dataset.
            * **Metrics Reported**:
              - Total Return Transactions: **{guest_metrics.get('total_cancellations_count', 0):,}**
              - Total Return Value: **${guest_metrics.get('cancellations_value', 0.0):,.2f}**
            * **Accounting Rationale**: Returns are not netted into product-level gross volume to prevent metric confusion. We report **positive sales value** as our headline sales metric.
            """
        )

    st.markdown("---")

    # 4. Non-Product Code Exclusions
    with st.expander("📦 Excluded Non-Product Stock Codes Policy", expanded=False):
        st.markdown(
            """
            Transactions with non-product stock codes or non-positive prices (`<= $0.00`) are excluded from merchandise analytics:
            """
        )
        st.write(sorted(list(NON_PRODUCT_STOCK_CODES)))
