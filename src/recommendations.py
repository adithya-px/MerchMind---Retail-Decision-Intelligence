"""
Strategic Marketing Recommendations Engine for RetailPulse.
Generates segment-specific marketing and retention strategies derived directly
from computed cluster metrics and activity trends.
Disclaimed clearly as heuristic observational strategies, not validated causal effects.
"""

from typing import List, Dict, Any
import pandas as pd


def generate_recommendations(
    cluster_profiles: pd.DataFrame,
    declining_summary: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Constructs actionable segment playbooks based on empirical cluster profiles.
    """
    recommendations = []

    for _, row in cluster_profiles.iterrows():
        segment_name = row["SegmentName"]
        r = row["Recency_mean"]
        f = row["Frequency_mean"]
        m = row["Monetary_mean"]
        cust_count = int(row["CustomerCount"])
        rev_share = row["RevenueSharePct"]

        # Dynamic strategy mapping
        if "Champion" in segment_name:
            strategy_type = "VIP Retention & Brand Advocacy"
            actions = [
                "Invite to exclusive VIP tier with early access to new catalog arrivals.",
                "Implement referral rewards to leverage their high brand affinity.",
                "Offer premium customer support or a dedicated concierge contact.",
                "Avoid heavy discounting; prioritize recognition, appreciation, and premium bundles.",
            ]
            objective = "Maximize lifetime loyalty and advocacy without degrading price perception."
        elif "Loyal" in segment_name:
            strategy_type = "AOV Expansion & Cross-Selling"
            actions = [
                "Recommend related product categories (cross-sell) based on past purchase history.",
                "Introduce tiered volume discounts (e.g., 'Spend $100, get free shipping / $15 off').",
                "Enroll in milestone-based loyalty rewards to gamify repeat purchasing.",
                "Solicit product reviews and feedback on recently ordered items.",
            ]
            objective = "Increase average basket size while sustaining high order frequency."
        elif "Promising" in segment_name or "New" in segment_name:
            strategy_type = "Onboarding & Habituation"
            actions = [
                "Deliver a welcoming onboarding email sequence with brand highlights and product care guides.",
                "Offer a limited-time incentive on their next purchase (second-order incentive within 30 days).",
                "Highlight top customer favorites and trending products from complementary collections.",
                "Provide quick customer satisfaction surveys to catch any initial fulfillment friction.",
            ]
            objective = "Secure the critical second and third repeat purchase to build retention habits."
        elif "Risk" in segment_name:
            strategy_type = "Targeted Win-Back & Churn Prevention"
            actions = [
                "Trigger personalized 'We Miss You' re-engagement campaigns with tailored discount incentives.",
                "Send brief exit/feedback surveys inquiring why their purchasing frequency tapered off.",
                "Highlight popular new arrivals introduced since their last order date.",
                "Test urgency-driven promotions (e.g., promotional credits expiring in 14 days).",
            ]
            objective = "Reactivate lapsed relationships before customer moves into permanently lost status."
        else:  # Inactive / Hibernating
            strategy_type = "Low-Cost Clearance Reactivation"
            actions = [
                "Include in major seasonal sales, annual clearance events, or holiday promotions.",
                "Rely on low-cost automated email/SMS channels; suppress expensive direct mail or ad spend.",
                "Purge or suppress unresponsive contacts after 12+ months to preserve sender email reputation.",
                "Offer steep liquidation discounts on overstock merchandise to test responsiveness.",
            ]
            objective = "Extract residual value at minimal operational and marketing cost."

        recommendations.append({
            "segment_name": segment_name,
            "strategy_type": strategy_type,
            "customer_count": cust_count,
            "revenue_share_pct": rev_share,
            "avg_recency": r,
            "avg_frequency": f,
            "avg_monetary": m,
            "objective": objective,
            "actions": actions,
        })

    return recommendations
