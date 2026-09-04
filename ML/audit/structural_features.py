"""
FraudLens - Structural Graph Features (PageRank / k-core / Community)
==========================================================================
Non-learned, purely topological + "guilt-by-association" features, computed
PER TIME-STEP SUBGRAPH (edges never cross time steps in this dataset, so
each step is naturally its own connected-component-ish subgraph).

Features per node:
  - in_degree, out_degree           (pure topology, no label risk at all)
  - kcore                           (pure topology, no label risk at all)
  - hits_hub, hits_authority        (pure topology, no label risk at all)
  - ppr_illicit                     (personalized PageRank seeded from KNOWN
                                      illicit nodes in the same step - label-
                                      derived, so self-exclusion matters)
  - community_guilt_density         (Louvain, resolution=1.0)

  Louvain community membership is pure topology; the illicit-fraction-of-
  community part is label-derived, so self-exclusion matters for that one.

  NOTE: an earlier version of this file added community_size plus three
  extra community-density variants (low-res, high-res, label-propagation).
  Tested on real data, that version UNDERPERFORMED this simpler one
  (post-drift mean F1 0.576 vs 0.646) - the extra correlated features
  diluted the RF's splits rather than adding signal, especially at the
  lowest-sample steps. Reverted deliberately; kept only the HITS inf/nan
  safety fix discovered along the way (see below), which is an unrelated
  correctness fix worth keeping regardless of feature set.

CRITICAL - self-exclusion (we got burned by this exact mistake with
GuiltyWalker earlier): for ppr_illicit and community_guilt_density, an
ACTUAL illicit node must NEVER see its own label reflected back in its own
feature value. For ppr_illicit this means recomputing personalized PageRank
with a LEAVE-ONE-OUT seed set (illicit nodes minus itself) specifically for
illicit nodes - cheap, since illicit nodes are a small fraction of each
step. For community_guilt_density this means excluding the node itself from
both the numerator (illicit count) and denominator (community size) of its
own community's guilt fraction.
"""
import os
import time

import networkx as nx
import numpy as np
import pandas as pd

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs")

FEATURE_NAMES = ["in_degree", "out_degree", "kcore", "hits_hub", "hits_authority",
                  "ppr_illicit", "community_guilt_density"]


def compute_for_timestep(node_ids, sub_edges, illicit_local_idx, alpha=0.85):
    """node_ids: array of GLOBAL node indices in this time step, in order.
    sub_edges: list of (local_src, local_dst) tuples, LOCAL indices into node_ids.
    illicit_local_idx: set of LOCAL indices (into node_ids) that are known illicit.
    Returns a (len(node_ids), 7) array in FEATURE_NAMES order.
    """
    n = len(node_ids)
    G = nx.DiGraph()
    G.add_nodes_from(range(n))
    G.add_edges_from(sub_edges)

    feats = np.zeros((n, len(FEATURE_NAMES)))

    # --- pure topology, zero label risk ---
    in_deg = dict(G.in_degree())
    out_deg = dict(G.out_degree())
    feats[:, 0] = [in_deg.get(i, 0) for i in range(n)]
    feats[:, 1] = [out_deg.get(i, 0) for i in range(n)]

    UG = G.to_undirected()
    try:
        core = nx.core_number(UG)
        feats[:, 2] = [core.get(i, 0) for i in range(n)]
    except Exception:
        pass  # leave as 0 on any pathological subgraph

    try:
        hubs, auths = nx.hits(G, max_iter=300, tol=1e-8, normalized=True)
        hub_vals = np.array([hubs.get(i, 0.0) for i in range(n)])
        auth_vals = np.array([auths.get(i, 0.0) for i in range(n)])
        # nx.hits can silently return inf/nan on some sparse/degenerate
        # subgraphs (normalization divides by a near-zero sum) WITHOUT
        # raising an exception - sanitize explicitly rather than relying on
        # the try/except to catch it.
        feats[:, 3] = np.nan_to_num(hub_vals, nan=0.0, posinf=0.0, neginf=0.0)
        feats[:, 4] = np.nan_to_num(auth_vals, nan=0.0, posinf=0.0, neginf=0.0)
    except Exception:
        pass  # HITS can also fail to converge and raise on some tiny/degenerate subgraphs

    # --- personalized PageRank seeded from known illicit nodes (label-derived) ---
    if len(illicit_local_idx) > 0 and n > 1:
        full_seed = {i: 1.0 for i in illicit_local_idx}
        try:
            ppr_full = nx.pagerank(G, alpha=alpha, personalization=full_seed,
                                    max_iter=300, tol=1e-8)
        except Exception:
            ppr_full = {i: 0.0 for i in range(n)}
        for i in range(n):
            feats[i, 5] = ppr_full.get(i, 0.0)

        # Leave-one-out correction: illicit nodes must not see their own
        # membership reflected in their own score. Only re-run for the
        # (typically few) illicit nodes in this step.
        for seed_node in illicit_local_idx:
            loo_seed = {i: 1.0 for i in illicit_local_idx if i != seed_node}
            if len(loo_seed) == 0:
                feats[seed_node, 5] = 0.0  # was the ONLY illicit seed - no valid signal
                continue
            try:
                ppr_loo = nx.pagerank(G, alpha=alpha, personalization=loo_seed,
                                       max_iter=300, tol=1e-8)
                feats[seed_node, 5] = ppr_loo.get(seed_node, 0.0)
            except Exception:
                feats[seed_node, 5] = 0.0

    # --- Louvain community guilt density (community = pure topology,
    #     illicit-fraction-of-community = label-derived, needs self-exclusion) ---
    if n > 1 and G.number_of_edges() > 0:
        try:
            communities = nx.algorithms.community.louvain_communities(
                UG, seed=42, resolution=1.0)
        except Exception:
            communities = [set(range(n))]
        node_to_comm = {}
        for comm in communities:
            for node in comm:
                node_to_comm[node] = comm
        for i in range(n):
            comm = node_to_comm.get(i, {i})
            others = comm - {i}
            if len(others) == 0:
                feats[i, 6] = 0.0
                continue
            illicit_in_comm = len(others & illicit_local_idx)
            feats[i, 6] = illicit_in_comm / len(others)

    # Safety net: any remaining inf/nan from ANY of the above (some networkx
    # algorithms can silently produce these on degenerate subgraphs without
    # raising) would otherwise crash RandomForestClassifier.fit() downstream.
    feats = np.nan_to_num(feats, nan=0.0, posinf=0.0, neginf=0.0)
    return feats


def compute_structural_features(edge_index, y, time_steps, n_nodes, progress=True,
                                 reference_illicit_mask=None):
    """
    reference_illicit_mask: optional boolean array (n_nodes,). If given, ONLY
        nodes where this mask is True count as "known illicit" for
        ppr_illicit seeding and community_guilt_density's illicit-fraction
        calculation - e.g. pass a TRAIN-ONLY mask so no test-period node's
        label (self or other) contributes to any feature. If None (default),
        falls back to y==1 globally (train+test) for backward compatibility -
        NOT a strict zero-test-knowledge setting.
    """
    t0 = time.time()
    if reference_illicit_mask is not None:
        illicit_global = set(np.where(np.asarray(reference_illicit_mask, dtype=bool))[0].tolist())
        print("[structural_features] STRICT MODE: reference illicit set restricted "
              "to the provided mask (e.g. train-only).")
    else:
        illicit_global = set(np.where(y == 1)[0].tolist())
        print("[structural_features] WARNING: no reference_illicit_mask provided - "
              "using ALL known illicit labels (train+test). NOT strict zero-test-knowledge.")

    # group global node indices by time_step
    steps = sorted(np.unique(time_steps).tolist())
    all_feats = np.zeros((n_nodes, len(FEATURE_NAMES)))

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

        illicit_local_idx = {global_to_local[g] for g in node_ids.tolist()
                              if g in illicit_global}

        step_feats = compute_for_timestep(node_ids, sub_edges, illicit_local_idx)
        all_feats[node_ids] = step_feats

        if progress:
            print(f"[structural_features] time_step {t}: {len(node_ids)} nodes, "
                  f"{len(sub_edges)} edges, {len(illicit_local_idx)} known illicit "
                  f"({time.time()-t0:.1f}s elapsed)")

    print(f"[structural_features] done in {time.time()-t0:.1f}s")
    return pd.DataFrame(all_feats, columns=FEATURE_NAMES)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from data_loader import load_elliptic

    data = load_elliptic()
    df = compute_structural_features(data.edge_index.numpy(), data.y.numpy(),
                                      data.time_step.numpy(), data.num_nodes)
    print(df.describe())
    os.makedirs(OUT_DIR, exist_ok=True)
    df.to_csv(os.path.join(OUT_DIR, "structural_features_smoketest.csv"), index=False)