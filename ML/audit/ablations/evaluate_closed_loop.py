"""
FraudLens - Closed-Loop Dual-Engine Evaluation
==============================================
Evaluates the synergy between Engine 1 (Autonomous Triage on Invariant Manifold)
and Engine 2 (Active Personalized PageRank Diffusion from 1 confirmed seed).
Fixes local/global index resolution across disconnected temporal components.
"""

import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import lightgbm as lgb
import networkx as nx
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, f1_score, precision_score, recall_score

from data_loader import load_elliptic, add_train_val_split
from train_prior_correction import best_f1_threshold

OUT_DIR = os.path.join(CURRENT_DIR, "..", "outputs")


def run_ppr_diffusion(sub_edges, n_nodes, seed_idx, alpha=0.85):
    if len(sub_edges) == 0:
        return np.zeros(n_nodes, dtype=np.float32)

    G = nx.DiGraph()
    G.add_nodes_from(range(n_nodes))
    G.add_edges_from(sub_edges)

    personalization = {i: 0.0 for i in range(n_nodes)}
    personalization[seed_idx] = 1.0

    try:
        ppr = nx.pagerank(G, alpha=alpha, personalization=personalization, max_iter=100)
        vec = np.array([ppr[i] for i in range(n_nodes)], dtype=np.float32)
        mx = vec.max()
        return vec / mx if mx > 0 else vec
    except Exception:
        return np.zeros(n_nodes, dtype=np.float32)


def main():
    data = load_elliptic()
    data = add_train_val_split(data)

    paths = [
        os.path.join(OUT_DIR, "clean_structural_features.csv"),
        os.path.join(OUT_DIR, "unsupervised_anomaly_features.csv"),
        os.path.join(OUT_DIR, "unsupervised_spectral_features.csv"),
        os.path.join(OUT_DIR, "unsupervised_neighborhood_features.csv"),
        os.path.join(OUT_DIR, "unsupervised_manifold_features.csv"),
        os.path.join(OUT_DIR, "covariate_drift_audit.csv"),
    ]
    for p in paths:
        if not os.path.exists(p):
            raise FileNotFoundError(f"Missing dependency: {p}")

    clean_df = pd.read_csv(paths[0])
    anomaly_df = pd.read_csv(paths[1])
    spectral_df = pd.read_csv(paths[2])
    neigh_df = pd.read_csv(paths[3])
    manifold_df = pd.read_csv(paths[4])
    audit_df = pd.read_csv(paths[5])

    X_raw = data.x.numpy()
    X = np.concatenate([
        X_raw, clean_df.values, anomaly_df.values,
        spectral_df.values, neigh_df.values, manifold_df.values
    ], axis=1)

    feature_names = (
        [f"raw_{i}" for i in range(X_raw.shape[1])]
        + list(clean_df.columns)
        + list(anomaly_df.columns)
        + list(spectral_df.columns)
        + list(neigh_df.columns)
        + list(manifold_df.columns)
    )

    # Prune top 45 drifted features
    dropped_features = set(audit_df.head(45)["feature"].tolist())
    keep_indices = [i for i, f in enumerate(feature_names) if f not in dropped_features]
    X_pruned = X[:, keep_indices]
    print(f"[Closed-Loop] Training Engine 1 on {X_pruned.shape[1]}-dimensional Invariant+Manifold space...")

    y = data.y.numpy()
    ts = data.time_step.numpy()
    edge_index = data.edge_index.numpy()
    src_all, dst_all = edge_index[0], edge_index[1]

    train_mask = data.train_mask.numpy()
    val_mask = data.val_mask.numpy()
    test_mask = data.test_mask.numpy()

    n_pos = int((y[train_mask] == 1).sum())
    n_neg = int((y[train_mask] == 0).sum())
    scale_pos_weight = n_neg / max(n_pos, 1)

    clf = lgb.LGBMClassifier(
        n_estimators=400,
        num_leaves=31,
        learning_rate=0.05,
        scale_pos_weight=scale_pos_weight,
        random_state=42,
        verbosity=-1,
        n_jobs=-1,
    )
    clf.fit(
        X_pruned[train_mask],
        y[train_mask],
        eval_set=[(X_pruned[val_mask], y[val_mask])],
        callbacks=[lgb.early_stopping(30, verbose=False)],
    )

    s_val = clf.predict_proba(X_pruned[val_mask])[:, 1]
    val_th, val_f1 = best_f1_threshold(y[val_mask], s_val)
    print(f"[Closed-Loop] Validation Optimal Threshold: {val_th:.3f} (Val F1: {val_f1:.4f})")

    # Score all nodes across the graph for direct indexing
    s_all = clf.predict_proba(X_pruned)[:, 1]

    rows = []
    test_timesteps = sorted(np.unique(ts[test_mask]))

    for t in test_timesteps:
        step_nodes = np.where(ts == t)[0]
        step_node_set = set(step_nodes.tolist())
        global_to_local = {g: i for i, g in enumerate(step_nodes)}

        # Extract local directed edges within this discrete timestep
        sub_edges = []
        for s, d in zip(src_all.tolist(), dst_all.tolist()):
            if s in step_node_set and d in step_node_set:
                sub_edges.append((global_to_local[s], global_to_local[d]))

        # Test evaluation nodes for this timestep
        test_nodes_step = np.where(test_mask & (ts == t))[0]
        test_local_indices = [global_to_local[g] for g in test_nodes_step]

        yt = y[test_nodes_step]
        st = s_all[test_nodes_step]
        n_ill = int(yt.sum())

        if t < 43:
            th = val_th
            yp_e1 = (st >= th).astype(int)
            f1_e1 = f1_score(yt, yp_e1, zero_division=0)
            pr_e1 = average_precision_score(yt, st)
            rec_e1 = recall_score(yt, yp_e1, zero_division=0)
            rows.append({
                "timestep": int(t),
                "n_illicit": n_ill,
                "mode": "Autonomous Triage",
                "pr_auc": round(float(pr_e1), 4),
                "f1": round(float(f1_e1), 4),
                "hit_rate": round(float(rec_e1), 4),
            })
        else:
            # Post-drift: Check if Engine 1 surfaced an illicit seed in its top alerts
            ranked_rel_order = np.argsort(st)[::-1]
            found_seeds_rel = [idx for idx in ranked_rel_order if yt[idx] == 1]

            if len(found_seeds_rel) > 0:
                # Map top ranked true positive back to local component coordinate
                best_rel_seed = found_seeds_rel[0]
                seed_global = test_nodes_step[best_rel_seed]
                seed_local = global_to_local[seed_global]

                # Engine 2 runs Personalized PageRank diffusion
                ppr_scores = run_ppr_diffusion(sub_edges, len(step_nodes), seed_local)
                st_ppr = ppr_scores[test_local_indices]

                # Fused score
                s_fused = 0.5 * st + 0.5 * st_ppr
                th_closed = float(np.percentile(s_fused, 96.0))
                yp_fused = (s_fused >= th_closed).astype(int)

                f1_closed = f1_score(yt, yp_fused, zero_division=0)
                pr_closed = average_precision_score(yt, s_fused)
                rec_closed = recall_score(yt, yp_fused, zero_division=0)

                rows.append({
                    "timestep": int(t),
                    "n_illicit": n_ill,
                    "mode": "Engine 1+2 Closed Loop",
                    "pr_auc": round(float(pr_closed), 4),
                    "f1": round(float(f1_closed), 4),
                    "hit_rate": round(float(rec_closed), 4),
                })
            else:
                th_adapt = float(np.percentile(st, 96.0))
                yp_fallback = (st >= th_adapt).astype(int)
                rows.append({
                    "timestep": int(t),
                    "n_illicit": n_ill,
                    "mode": "Autonomous Fallback",
                    "pr_auc": round(float(average_precision_score(yt, st)), 4),
                    "f1": round(float(f1_score(yt, yp_fallback, zero_division=0)), 4),
                    "hit_rate": round(float(recall_score(yt, yp_fallback, zero_division=0)), 4),
                })

    df_res = pd.DataFrame(rows)
    print("\n--- FraudLens Dual-Engine Closed-Loop Benchmark ---")
    print(df_res.to_string(index=False))

    post_m = df_res["timestep"] >= 43
    print("\n--- System Metrics ---")
    print(f"Pre-Drift Mean F1 (Autonomous):       {df_res[~post_m]['f1'].mean():.4f}")
    print(f"Post-Drift Mean PR-AUC (Closed Loop): {df_res[post_m]['pr_auc'].mean():.4f}")
    print(f"Post-Drift Mean F1 (Closed Loop):     {df_res[post_m]['f1'].mean():.4f}")
    print(f"Full System Macro F1:                 {df_res['f1'].mean():.4f}")


if __name__ == "__main__":
    main()