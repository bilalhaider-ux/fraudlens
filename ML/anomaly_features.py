"""
FraudLens - Unsupervised Time-Step Anomaly Extraction
======================================================
Computes purely unsupervised, local outlier scores per time-step.
Operates on all nodes (labeled and unlabeled). Zero label access.

Features generated per node (3 total):
  1. iforest_score: Isolation Forest anomaly score (normalized).
  2. pca_recon_err: Mean squared error of 10-component PCA reconstruction.
  3. dist_centroid: Standardized Euclidean distance to the time-step median.

Outputs:
  outputs/unsupervised_anomaly_features.csv
"""

import os
import sys
import time

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler

from data_loader import load_elliptic

OUT_DIR = os.path.join(CURRENT_DIR, "..", "outputs")
ANOMALY_FEATURE_NAMES = ["iforest_score", "pca_recon_err", "dist_centroid"]


def extract_timestep_anomalies(X_t):
    n = X_t.shape[0]
    feats = np.zeros((n, 3), dtype=np.float64)

    # Robust scaling per timestep to normalize across extreme bitcoin transaction spikes
    scaler = RobustScaler()
    X_scaled = scaler.fit_transform(X_t)

    # 1. Isolation Forest (Isolation depth)
    iso = IsolationForest(
        n_estimators=100,
        max_samples=min(256, n),
        contamination="auto",
        random_state=42,
        n_jobs=-1,
    )
    iso.fit(X_scaled)
    # score_samples returns negative anomaly score: lower means more abnormal
    feats[:, 0] = -iso.score_samples(X_scaled)

    # 2. PCA Subspace Reconstruction Error
    n_comp = min(10, n - 1, X_t.shape[1])
    pca = PCA(n_components=n_comp, random_state=42)
    X_proj = pca.fit_transform(X_scaled)
    X_recon = pca.inverse_transform(X_proj)
    feats[:, 1] = np.mean((X_scaled - X_recon) ** 2, axis=1)

    # 3. Distance to Time-Step Median Centroid
    median_vec = np.median(X_scaled, axis=0)
    feats[:, 2] = np.linalg.norm(X_scaled - median_vec, axis=1)

    return feats


def generate_anomaly_features():
    os.makedirs(OUT_DIR, exist_ok=True)
    t0 = time.time()

    data = load_elliptic()
    clean_struct_path = os.path.join(OUT_DIR, "clean_structural_features.csv")
    if not os.path.exists(clean_struct_path):
        raise FileNotFoundError(
            f"Missing {clean_struct_path}. Run clean_structural_features.py first."
        )

    clean_df = pd.read_csv(clean_struct_path)
    X_full = np.concatenate([data.x.numpy(), clean_df.values], axis=1)
    time_steps = data.time_step.numpy()
    n_nodes = data.num_nodes

    all_anomaly_feats = np.zeros((n_nodes, 3), dtype=np.float64)
    steps = sorted(np.unique(time_steps).tolist())

    for t in steps:
        step_mask = time_steps == t
        node_ids = np.where(step_mask)[0]
        X_t = X_full[node_ids]

        step_feats = extract_timestep_anomalies(X_t)
        all_anomaly_feats[node_ids] = step_feats

        print(f"[anomaly_features] timestep {t:2d}: {len(node_ids):5d} nodes processed ({time.time()-t0:.1f}s)")

    df = pd.DataFrame(all_anomaly_feats, columns=ANOMALY_FEATURE_NAMES)
    out_path = os.path.join(OUT_DIR, "unsupervised_anomaly_features.csv")
    df.to_csv(out_path, index=False)
    print(f"\nSaved unsupervised anomaly features -> {out_path} ({df.shape})")
    print(df.describe().T[["mean", "std", "min", "max"]])


if __name__ == "__main__":
    generate_anomaly_features()