"""
FraudLens - Clean Structural Graph Features (100% Unsupervised)
===============================================================
Computes purely topological graph features per time-step subgraph.
Zero label dependency: data.y is never accessed or passed into any
subgraph algorithm. Edge topologies and node degrees only.

Features generated per node (9 total):
  1. in_degree: Number of incoming transactions.
  2. out_degree: Number of outgoing transactions.
  3. total_degree: in_degree + out_degree.
  4. degree_ratio: (in_degree - out_degree) / (total_degree + 1e-5).
  5. kcore: Maximal subgraph core degeneracy (undirected).
  6. hits_hub: Kleinberg HITS hub score.
  7. hits_authority: Kleinberg HITS authority score.
  8. pagerank_unsupervised: Uniform Personalized PageRank (damping 0.85).
  9. clustering_coefficient: Local clustering coefficient (undirected).

Outputs:
  outputs/clean_structural_features.csv
"""

import os
import time
import networkx as nx
import numpy as np
import pandas as pd

from data_loader import load_elliptic

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs")

CLEAN_FEATURE_NAMES = [
    "in_degree",
    "out_degree",
    "total_degree",
    "degree_ratio",
    "kcore",
    "hits_hub",
    "hits_authority",
    "pagerank_unsupervised",
    "clustering_coefficient",
]


def compute_clean_timestep_features(node_ids, sub_edges, alpha=0.85):
    n = len(node_ids)
    G = nx.DiGraph()
    G.add_nodes_from(range(n))
    G.add_edges_from(sub_edges)

    feats = np.zeros((n, len(CLEAN_FEATURE_NAMES)), dtype=np.float64)

    # Degrees
    in_deg = dict(G.in_degree())
    out_deg = dict(G.out_degree())
    in_arr = np.array([in_deg.get(i, 0) for i in range(n)], dtype=np.float64)
    out_arr = np.array([out_deg.get(i, 0) for i in range(n)], dtype=np.float64)
    tot_arr = in_arr + out_arr
    ratio_arr = (in_arr - out_arr) / (tot_arr + 1e-5)

    feats[:, 0] = in_arr
    feats[:, 1] = out_arr
    feats[:, 2] = tot_arr
    feats[:, 3] = ratio_arr

    # Undirected conversions for topology
    UG = G.to_undirected()

    # K-Core
    try:
        core = nx.core_number(UG)
        feats[:, 4] = [core.get(i, 0) for i in range(n)]
    except Exception:
        feats[:, 4] = 0.0

    # HITS
    try:
        hubs, auths = nx.hits(G, max_iter=300, tol=1e-8, normalized=True)
        h_vals = np.array([hubs.get(i, 0.0) for i in range(n)])
        a_vals = np.array([auths.get(i, 0.0) for i in range(n)])
        feats[:, 5] = np.nan_to_num(h_vals, nan=0.0, posinf=0.0, neginf=0.0)
        feats[:, 6] = np.nan_to_num(a_vals, nan=0.0, posinf=0.0, neginf=0.0)
    except Exception:
        feats[:, 5] = 0.0
        feats[:, 6] = 0.0

    # PageRank (Uniform / Completely Unsupervised)
    try:
        pr = nx.pagerank(G, alpha=alpha, max_iter=300, tol=1e-8)
        feats[:, 7] = [pr.get(i, 0.0) for i in range(n)]
    except Exception:
        feats[:, 7] = 0.0

    # Local Clustering Coefficient
    try:
        clust = nx.clustering(UG)
        feats[:, 8] = [clust.get(i, 0.0) for i in range(n)]
    except Exception:
        feats[:, 8] = 0.0

    feats = np.nan_to_num(feats, nan=0.0, posinf=0.0, neginf=0.0)
    return feats


def generate_clean_features():
    os.makedirs(OUT_DIR, exist_ok=True)
    t0 = time.time()

    data = load_elliptic()
    edge_index = data.edge_index.numpy()
    time_steps = data.time_step.numpy()
    n_nodes = data.num_nodes

    all_feats = np.zeros((n_nodes, len(CLEAN_FEATURE_NAMES)), dtype=np.float64)
    steps = sorted(np.unique(time_steps).tolist())
    src, dst = edge_index[0], edge_index[1]

    for t in steps:
        step_mask = time_steps == t
        node_ids = np.where(step_mask)[0]
        global_to_local = {g: i for i, g in enumerate(node_ids)}
        node_id_set = set(node_ids.tolist())

        sub_edges = []
        for s, d in zip(src.tolist(), dst.tolist()):
            if s in node_id_set and d in node_id_set:
                sub_edges.append((global_to_local[s], global_to_local[d]))

        step_feats = compute_clean_timestep_features(node_ids, sub_edges)
        all_feats[node_ids] = step_feats

        print(f"[clean_structural] timestep {t:2d}: {len(node_ids):5d} nodes, "
              f"{len(sub_edges):5d} edges ({time.time()-t0:.1f}s)")

    df = pd.DataFrame(all_feats, columns=CLEAN_FEATURE_NAMES)
    out_path = os.path.join(OUT_DIR, "clean_structural_features.csv")
    df.to_csv(out_path, index=False)
    print(f"\nSaved 100% clean structural features -> {out_path} ({df.shape})")
    print(df.describe().T[["mean", "std", "min", "max"]])


if __name__ == "__main__":
    generate_clean_features()