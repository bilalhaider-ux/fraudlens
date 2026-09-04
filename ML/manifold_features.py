"""
FraudLens - Flow-Manifold Density Extraction
============================================
Computes robust Mahalanobis distance and structural flow entropy
in the 8-dimensional SVD subspace per discrete timestep.
Operates on all nodes without label access.

Features generated per node (2 total):
  - mahalanobis_svd: Distance to the robust flow centroid.
  - flow_energy_entropy: Entropy of directional SVD flow coordinates.

Output:
  outputs/unsupervised_manifold_features.csv
"""

import os
import sys
import time

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import numpy as np
import pandas as pd
from sklearn.covariance import MinCovDet

from data_loader import load_elliptic

OUT_DIR = os.path.join(CURRENT_DIR, "..", "outputs")
MANIFOLD_FEATURE_NAMES = ["mahalanobis_svd", "flow_energy_entropy"]


def compute_timestep_manifold(svd_matrix):
    n = svd_matrix.shape[0]
    feats = np.zeros((n, 2), dtype=np.float32)

    # 1. Flow Energy Entropy: -sum(p * log(p)) across SVD component squares
    power = svd_matrix**2 + 1e-12
    norm_power = power / np.sum(power, axis=1, keepdims=True)
    feats[:, 1] = -np.sum(norm_power * np.log(norm_power), axis=1)

    # 2. Robust Mahalanobis Distance in SVD Flow Subspace
    try:
        # Fast Minimum Covariance Determinant for outlier-resistant center
        mcd = MinCovDet(support_fraction=0.8, random_state=42)
        mcd.fit(svd_matrix)
        feats[:, 0] = np.sqrt(np.maximum(mcd.mahalanobis(svd_matrix), 0.0))
    except Exception:
        # Standard standardized Euclidean fallback for degenerate subgraphs
        center = np.median(svd_matrix, axis=0)
        cov_diag = np.var(svd_matrix, axis=0) + 1e-6
        diff = svd_matrix - center
        feats[:, 0] = np.sqrt(np.sum((diff**2) / cov_diag, axis=1))

    return feats


def generate_manifold_features():
    os.makedirs(OUT_DIR, exist_ok=True)
    t0 = time.time()

    data = load_elliptic()
    time_steps = data.time_step.numpy()
    n_nodes = data.num_nodes

    spectral_path = os.path.join(OUT_DIR, "unsupervised_spectral_features.csv")
    if not os.path.exists(spectral_path):
        raise FileNotFoundError(f"Missing {spectral_path}. Run spectral_features.py first.")

    spectral_df = pd.read_csv(spectral_path)
    all_manifold_feats = np.zeros((n_nodes, 2), dtype=np.float32)
    steps = sorted(np.unique(time_steps).tolist())

    for t in steps:
        step_mask = time_steps == t
        node_ids = np.where(step_mask)[0]
        svd_t = spectral_df.values[node_ids]

        step_feats = compute_timestep_manifold(svd_t)
        all_manifold_feats[node_ids] = step_feats

        print(f"[manifold_features] timestep {t:2d}: {len(node_ids):5d} nodes processed ({time.time()-t0:.1f}s)")

    df = pd.DataFrame(all_manifold_feats, columns=MANIFOLD_FEATURE_NAMES)
    out_path = os.path.join(OUT_DIR, "unsupervised_manifold_features.csv")
    df.to_csv(out_path, index=False)
    print(f"\nSaved flow manifold features -> {out_path} ({df.shape})")


if __name__ == "__main__":
    generate_manifold_features()