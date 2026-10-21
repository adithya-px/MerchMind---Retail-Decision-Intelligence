"""
Customer Intelligence Engine for RetailPulse: RFM Analysis & K-Means Clustering.
Implements log1p skew transform, standard scaling, elbow and silhouette candidate
evaluation (k=2-8), PCA 2D dimensionality reduction, and profile-based segmentation.
"""

from typing import Dict, Any, Tuple, Optional, List
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.decomposition import PCA

from src.config import (
    COL_INVOICE,
    COL_DATE,
    COL_CUST,
    COL_LINE_REVENUE,
    RANDOM_SEED,
    DEFAULT_K_CLUSTERS,
    CANDIDATE_K_RANGE,
    GUEST_CUSTOMER_LABEL,
)


def compute_rfm_table(
    customer_df: pd.DataFrame,
    reference_date: Optional[pd.Timestamp] = None,
) -> pd.DataFrame:
    """
    Computes Customer-level Recency, Frequency, and Monetary metrics.
    Reference date defaults to (latest transaction date + 1 day).
    Frequency is distinct valid orders (InvoiceNo), Monetary is positive sales value.
    """
    if customer_df.empty:
        return pd.DataFrame(
            columns=["CustomerID", "Recency", "Frequency", "Monetary", "AvgOrderValue", "CustomerLifespanDays", "FirstPurchase", "LastPurchase"]
        )

    # Exclude guest customers
    clean_cust = customer_df[customer_df[COL_CUST] != GUEST_CUSTOMER_LABEL].copy()
    if clean_cust.empty:
        return pd.DataFrame(
            columns=["CustomerID", "Recency", "Frequency", "Monetary", "AvgOrderValue", "CustomerLifespanDays", "FirstPurchase", "LastPurchase"]
        )

    # Filter to transactions with positive monetary value
    clean_cust = clean_cust[clean_cust[COL_LINE_REVENUE] > 0]
    if clean_cust.empty:
        return pd.DataFrame(
            columns=["CustomerID", "Recency", "Frequency", "Monetary", "AvgOrderValue", "CustomerLifespanDays", "FirstPurchase", "LastPurchase"]
        )

    max_dataset_date = clean_cust[COL_DATE].max()
    ref_dt = pd.to_datetime(reference_date) if reference_date is not None else (max_dataset_date + pd.Timedelta(days=1))

    rfm = (
        clean_cust.groupby(COL_CUST)
        .agg(
            LastPurchase=(COL_DATE, "max"),
            FirstPurchase=(COL_DATE, "min"),
            Frequency=(COL_INVOICE, "nunique"),
            Monetary=(COL_LINE_REVENUE, "sum"),
        )
        .reset_index()
    )

    # Only retain customers with positive monetary spend and positive frequency
    rfm = rfm[(rfm["Monetary"] > 0) & (rfm["Frequency"] > 0)].copy()

    rfm["Recency"] = (ref_dt - rfm["LastPurchase"]).dt.days.clip(lower=0)
    rfm["AvgOrderValue"] = rfm["Monetary"] / rfm["Frequency"]
    rfm["CustomerLifespanDays"] = (rfm["LastPurchase"] - rfm["FirstPurchase"]).dt.days.clip(lower=0)

    return rfm


def evaluate_candidate_k(
    rfm_df: pd.DataFrame,
    k_range: Tuple[int, int] = CANDIDATE_K_RANGE,
    random_state: int = RANDOM_SEED,
) -> Tuple[pd.DataFrame, int]:
    """
    Evaluates candidate cluster counts across k_range using Elbow (SSE) and Silhouette Score.
    Returns (evaluation_df, recommended_best_k).
    """
    if len(rfm_df) < k_range[0]:
        raise ValueError(f"Need at least {k_range[0]} unique customers to perform clustering evaluation.")

    # Skew mitigation: log1p transform followed by StandardScaler
    features = np.log1p(rfm_df[["Recency", "Frequency", "Monetary"]].values)
    scaler = StandardScaler()
    scaled = scaler.fit_transform(features)

    max_k = min(k_range[1], len(rfm_df) - 1)
    results = []

    for k in range(k_range[0], max_k + 1):
        km = KMeans(n_clusters=k, random_state=random_state, n_init=10)
        labels = km.fit_predict(scaled)
        score = silhouette_score(scaled, labels)
        results.append({
            "k": k,
            "Inertia": float(km.inertia_),
            "SilhouetteScore": float(score),
        })

    eval_df = pd.DataFrame(results)
    best_k = int(eval_df.loc[eval_df["SilhouetteScore"].idxmax()]["k"])
    return eval_df, best_k


def assign_interpretable_labels(profiles: pd.DataFrame) -> Dict[int, Dict[str, Any]]:
    """
    Inspects centroid metrics (R, F, M) across clusters and assigns stable,
    human-readable, distinct business segment names.
    Ranks clusters deterministically so archetype labels remain clean and meaningful across any k.
    """
    label_map = {}
    k = len(profiles)

    if k == 0:
        return label_map

    # Fallback for single cluster
    if k == 1:
        cluster_id = profiles.index[0]
        r = profiles.loc[cluster_id, "Recency_mean"]
        f = profiles.loc[cluster_id, "Frequency_mean"]
        m = profiles.loc[cluster_id, "Monetary_mean"]
        label_map[cluster_id] = {
            "name": "General Cohort",
            "description": f"Recency avg {r:.0f}d, Frequency avg {f:.1f} orders, Monetary avg ${m:,.0f}",
        }
        return label_map

    r_med = profiles["Recency_mean"].median()
    f_med = profiles["Frequency_mean"].median()
    m_med = profiles["Monetary_mean"].median()

    # Pre-rank clusters by overall customer value score:
    # High Monetary (50%), High Frequency (30%), Low Recency (20%)
    r_max = profiles["Recency_mean"].max() or 1.0
    f_max = profiles["Frequency_mean"].max() or 1.0
    m_max = profiles["Monetary_mean"].max() or 1.0

    scores = {}
    for cluster_id, row in profiles.iterrows():
        r_score = 1.0 - (row["Recency_mean"] / (r_max * 1.05))
        f_score = row["Frequency_mean"] / f_max
        m_score = row["Monetary_mean"] / m_max
        scores[cluster_id] = (0.50 * m_score) + (0.30 * f_score) + (0.20 * r_score)

    ranked_clusters = sorted(scores.keys(), key=lambda c: scores[c], reverse=True)

    # Curated archetype pools depending on cluster count k
    if k == 2:
        tier_names = ["Champions & Core Buyers", "Hibernating / Inactive"]
        tier_map = dict(zip(ranked_clusters, tier_names))
    elif k == 3:
        tier_names = ["Champions", "Promising / Moderate Buyers", "Hibernating / Inactive"]
        tier_map = dict(zip(ranked_clusters, tier_names))
    elif k == 4:
        # Standard RFM 4-cluster archetypes
        tier_map = {}
        used_labels = set()
        for c in ranked_clusters:
            row = profiles.loc[c]
            r = row["Recency_mean"]
            f = row["Frequency_mean"]
            m = row["Monetary_mean"]

            if r <= r_med and f >= f_med and m >= m_med:
                candidate = "Champions"
            elif r <= r_med and f < f_med:
                candidate = "Recent New Customers"
            elif r > r_med and (f >= f_med or m >= m_med):
                candidate = "At Risk / Slipping"
            elif r > r_med and f < f_med and m < m_med:
                candidate = "Hibernating / Inactive"
            elif r <= r_med:
                candidate = "Loyal Customers"
            else:
                candidate = "At Risk / Slipping"

            if candidate in used_labels:
                # Disambiguate with rank-based archetype
                rank_pos = ranked_clusters.index(c)
                fallback_names = ["Champions", "Loyal Customers", "Recent New Customers", "Hibernating / Inactive"]
                candidate = fallback_names[rank_pos] if rank_pos < len(fallback_names) else f"Cohort {c}"

            used_labels.add(candidate)
            tier_map[c] = candidate
    elif k == 5:
        tier_names = [
            "Champions",
            "Loyal Customers",
            "Recent New Customers",
            "At Risk / Slipping",
            "Hibernating / Inactive",
        ]
        tier_map = dict(zip(ranked_clusters, tier_names))
    else:
        # For k >= 6: Rank-based descriptive tier naming
        tier_names = [
            "Champions (Top Tier)",
            "High-Value Core",
            "Moderate Active",
            "Recent New Customers",
            "At Risk / Slipping",
            "Hibernating / Inactive",
            "Lapsed Low-Value",
            "Dormant",
        ]
        tier_map = {}
        for idx, c in enumerate(ranked_clusters):
            tier_map[c] = tier_names[idx] if idx < len(tier_names) else f"Cluster {c}"

    for cluster_id, row in profiles.iterrows():
        r = row["Recency_mean"]
        f = row["Frequency_mean"]
        m = row["Monetary_mean"]
        name = tier_map.get(cluster_id, f"Cluster {cluster_id}")
        label_map[cluster_id] = {
            "name": name,
            "description": f"Recency avg {r:.0f}d, Frequency avg {f:.1f} orders, Monetary avg ${m:,.0f}",
        }

    return label_map


def fit_kmeans_clustering(
    rfm_df: pd.DataFrame,
    n_clusters: int = DEFAULT_K_CLUSTERS,
    random_state: int = RANDOM_SEED,
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """
    Fits K-Means on log1p + scaled RFM features.
    Computes PCA 2D coordinates for interactive scatter plotting.
    Inspects cluster centroids to generate stable data-driven segment descriptions.

    Returns:
        clustered_rfm: Dataframe with Cluster, SegmentName, PCA1, PCA2.
        cluster_profiles: Summary metrics per cluster.
        metadata: Model diagnostic metadata (silhouette score, inertia, PCA explained variance).
    """
    if len(rfm_df) < n_clusters:
        raise ValueError(
            f"Cannot fit {n_clusters} clusters with only {len(rfm_df)} customers! "
            f"Please reduce cluster count or adjust filter criteria."
        )

    res = rfm_df.copy()

    # Feature transformation
    raw_feats = res[["Recency", "Frequency", "Monetary"]].values
    log_feats = np.log1p(raw_feats)
    scaler = StandardScaler()
    scaled_feats = scaler.fit_transform(log_feats)

    # KMeans fitting
    km = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10)
    clusters = km.fit_predict(scaled_feats)
    res["Cluster"] = clusters

    # Silhouette validation
    sil_score = float(silhouette_score(scaled_feats, clusters)) if len(res) > n_clusters else 0.0

    # 2D PCA for visual inspection
    pca = PCA(n_components=2, random_state=random_state)
    pca_coords = pca.fit_transform(scaled_feats)
    res["PCA1"] = pca_coords[:, 0]
    res["PCA2"] = pca_coords[:, 1]
    var_explained = [float(v) for v in pca.explained_variance_ratio_]

    # Cluster profiles
    total_rev = res["Monetary"].sum()
    profiles = (
        res.groupby("Cluster")
        .agg(
            CustomerCount=("CustomerID", "count"),
            Recency_mean=("Recency", "mean"),
            Recency_median=("Recency", "median"),
            Frequency_mean=("Frequency", "mean"),
            Frequency_median=("Frequency", "median"),
            Monetary_mean=("Monetary", "mean"),
            Monetary_median=("Monetary", "median"),
            Monetary_sum=("Monetary", "sum"),
        )
    )
    profiles["RevenueSharePct"] = (profiles["Monetary_sum"] / total_rev * 100.0) if total_rev > 0 else 0.0
    profiles["CustomerSharePct"] = (profiles["CustomerCount"] / len(res) * 100.0)

    # Label clusters deterministically after inspecting profile centroids
    label_info = assign_interpretable_labels(profiles)
    res["SegmentName"] = res["Cluster"].map(lambda c: label_info[c]["name"])
    profiles["SegmentName"] = profiles.index.map(lambda c: label_info[c]["name"])
    profiles["Description"] = profiles.index.map(lambda c: label_info[c]["description"])

    metadata = {
        "n_clusters": n_clusters,
        "silhouette_score": sil_score,
        "inertia": float(km.inertia_),
        "pca_variance_explained": var_explained,
        "total_pca_variance_pct": sum(var_explained) * 100.0,
        "label_info": label_info,
    }

    return res, profiles.reset_index(), metadata
