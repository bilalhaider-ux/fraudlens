"""
FraudLens - Unsupervised 1-Hop Structural Message Passing
=========================================================
Extracts localized graph convolutions across directed payment edges
per discrete timestep. Captures multi-hop fan-in / fan-out flow
patterns without labels or transductive cross-step leakage.

Features generated per node (8 total):
  - neigh_in_mean_in_deg, neigh_in_mean_out_deg, neigh_in_mean_kcore
  - neigh_in_max_out_deg (peeling hub feeder detection)
  - neigh_out_mean_in_deg, neigh_out_mean_out_deg, neigh_out_mean_kcore
  - neigh_out_max_in_deg (consolidation sink detection)

Output:
  outputs/unsupervised_neighborhood_features.csv
"""

import os
import sys
import time

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import networkx as nx
import numpy as np
import pandas as pd
import scipy.sparse as sp

from data_loader import load_elliptic

OUT_DIR = os.path.join(CURRENT_DIR, "..", "outputs")
NEIGHBORHOOD_FEATURE_NAMES = [
    "neigh_in_mean_in_deg",
    "neigh_in_mean_out_deg",
    "neigh_in_mean_kcore",
    "neigh_in_max_out_deg",
    "neigh_out_mean_in_deg",
    "neigh_out_mean_out_deg",
    "neigh_out_mean_kcore",
    "neigh_out_max_in_deg",
]


def compute_timestep_neighborhood(node_ids, sub_edges):
    n = len(node_ids)
    feats = np.zeros((n, 8), dtype=np.float32)

    if len(sub_edges) == 0:
        return feats

    src_nodes = np.array([e[0] for e in sub_edges], dtype=np.int32)
    dst_nodes = np.array([e[1] for e in sub_edges], dtype=np.int32)
    vals = np.ones(len(sub_edges), dtype=np.float32)

    A = sp.csr_matrix((vals, (src_nodes, dst_nodes)), shape=(n, n), dtype=np.float32)

    out_deg = np.array(A.sum(axis=1), dtype=np.float32).flatten()
    in_deg = np.array(A.sum(axis=0), dtype=np.float32).flatten()

    # Undirected k-core degeneracy
    G_undir = nx.Graph()
    G_undir.add_nodes_from(range(n))
    G_undir.add_edges_from(sub_edges)
    try:
        core_dict = nx.core_number(G_undir)
        kcore = np.array([core_dict.get(i, 0) for i in range(n)], dtype=np.float32)
    except Exception:
        kcore = np.zeros(n, dtype=np.float32)

    X_base = np.column_stack([in_deg, out_deg, kcore])

    # 1. In-Neighbor Mean Aggregation: (A^T * X_base) / in_deg
    in_sum = A.transpose().dot(X_base)
    in_divisor = np.maximum(in_deg[:, None], 1.0)
    feats[:, 0:3] = in_sum / in_divisor

    # 2. In-Neighbor Max Out-Degree (feeder hub tracking)
    in_max_out = np.zeros(n, dtype=np.float32)
    np.maximum.at(in_max_out, dst_nodes, out_deg[src_nodes])
    feats[:, 3] = in_max_out

    # 3. Out-Neighbor Mean Aggregation: (A * X_base) / out_deg
    out_sum = A.dot(X_base)
    out_divisor = np.maximum(out_deg[:, None], 1.0)
    feats[:, 4:7] = out_sum / out_divisor

    # 4. Out-Neighbor Max In-Degree (consolidation sink tracking)
    out_max_in = np.zeros(n, dtype=np.float32)
    np.maximum.at(out_max_in, src_nodes, in_deg[dst_nodes])
    feats[:, 7] = out_max_in

    return feats


def generate_neighborhood_features():
    os.makedirs(OUT_DIR, exist_ok=True)
    t0 = time.time()

    data = load_elliptic()
    edge_index = data.edge_index.numpy()
    time_steps = data.time_step.numpy()
    n_nodes = data.num_nodes

    all_neigh_feats = np.zeros((n_nodes, 8), dtype=np.float32)
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

        step_feats = compute_timestep_neighborhood(node_ids, sub_edges)
        all_neigh_feats[node_ids] = step_feats

        print(f"[neighborhood_features] timestep {t:2d}: {len(node_ids):5d} nodes, {len(sub_edges):5d} edges ({time.time()-t0:.1f}s)")

    df = pd.DataFrame(all_neigh_feats, columns=NEIGHBORHOOD_FEATURE_NAMES)
    out_path = os.path.join(OUT_DIR, "unsupervised_neighborhood_features.csv")
    df.to_csv(out_path, index=False)
    print(f"\nSaved neighborhood features -> {out_path} ({df.shape})")


if __name__ == "__main__":
    generate_neighborhood_features()