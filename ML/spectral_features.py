"""
FraudLens - Unsupervised Spectral Graph SVD Extraction
======================================================
Factorizes discrete time-step graph topology via Truncated SVD on
degree-normalized adjacency matrices. Captures source (fan-out) and
sink (fan-in) network coordinates across all labeled and unlabeled nodes.

Zero label access. 100% leak-free.

Features generated per node (8 total):
  - svd_src_0 to svd_src_3: Source-flow singular vectors
  - svd_dst_0 to svd_dst_3: Sink-flow singular vectors

Output:
  outputs/unsupervised_spectral_features.csv
"""

import os
import sys
import time

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import numpy as np
import pandas as pd
import scipy.sparse as sp
from sklearn.decomposition import TruncatedSVD

from data_loader import load_elliptic

OUT_DIR = os.path.join(CURRENT_DIR, "..", "outputs")
SPECTRAL_FEATURE_NAMES = [f"svd_src_{i}" for i in range(4)] + [f"svd_dst_{i}" for i in range(4)]


def compute_timestep_spectral(node_ids, sub_edges, n_components=4):
    n = len(node_ids)
    feats = np.zeros((n, n_components * 2), dtype=np.float32)

    if len(sub_edges) == 0 or n <= n_components:
        return feats

    src_nodes = [e[0] for e in sub_edges]
    dst_nodes = [e[1] for e in sub_edges]
    vals = np.ones(len(sub_edges), dtype=np.float32)

    A = sp.csr_matrix((vals, (src_nodes, dst_nodes)), shape=(n, n), dtype=np.float32)

    # Degree normalization: D_out^(-1/2) * A * D_in^(-1/2)
    out_deg = np.array(A.sum(axis=1)).flatten()
    in_deg = np.array(A.sum(axis=0)).flatten()

    out_inv_sqrt = np.power(np.maximum(out_deg, 1.0), -0.5)
    in_inv_sqrt = np.power(np.maximum(in_deg, 1.0), -0.5)

    D_out_inv = sp.diags(out_inv_sqrt)
    D_in_inv = sp.diags(in_inv_sqrt)

    A_norm = D_out_inv.dot(A).dot(D_in_inv)

    # 1. Source structural roles
    k = min(n_components, min(A_norm.shape) - 1)
    if k > 0:
        svd_src = TruncatedSVD(n_components=k, random_state=42, algorithm="randomized")
        U = svd_src.fit_transform(A_norm)
        feats[:, :k] = U

    # 2. Sink / consolidation structural roles
    A_norm_T = A_norm.transpose().tocsr()
    k_t = min(n_components, min(A_norm_T.shape) - 1)
    if k_t > 0:
        svd_dst = TruncatedSVD(n_components=k_t, random_state=42, algorithm="randomized")
        V = svd_dst.fit_transform(A_norm_T)
        feats[:, n_components:n_components + k_t] = V

    return feats


def generate_spectral_features():
    os.makedirs(OUT_DIR, exist_ok=True)
    t0 = time.time()

    data = load_elliptic()
    edge_index = data.edge_index.numpy()
    time_steps = data.time_step.numpy()
    n_nodes = data.num_nodes

    all_spectral_feats = np.zeros((n_nodes, 8), dtype=np.float32)
    steps = sorted(np.unique(time_steps).tolist())
    src, dst = edge_index[0], edge_index[1]

    for t in steps:
        step_mask = time_steps == t
        node_ids = np.where(step_mask)[0]
        node_id_set = set(node_ids.tolist())
        global_to_local = {g: i for i, g in enumerate(node_ids)}

        sub_edges = []
        for s, d in zip(src.tolist(), dst.tolist()):
            if s in node_id_set and d in node_id_set:
                sub_edges.append((global_to_local[s], global_to_local[d]))

        step_feats = compute_timestep_spectral(node_ids, sub_edges, n_components=4)
        all_spectral_feats[node_ids] = step_feats

        print(f"[spectral_features] timestep {t:2d}: {len(node_ids):5d} nodes, {len(sub_edges):5d} edges ({time.time()-t0:.1f}s)")

    df = pd.DataFrame(all_spectral_feats, columns=SPECTRAL_FEATURE_NAMES)
    out_path = os.path.join(OUT_DIR, "unsupervised_spectral_features.csv")
    df.to_csv(out_path, index=False)
    print(f"\nSaved spectral graph features -> {out_path} ({df.shape})")


if __name__ == "__main__":
    generate_spectral_features()