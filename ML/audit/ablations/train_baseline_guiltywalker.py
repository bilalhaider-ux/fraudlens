"""
FraudLens - Baseline + GuiltyWalker Features
================================================
Adds GuiltyWalker graph-distance-to-illicit features (see guilty_walker.py)
to the original 165 raw features, retrains RF, and evaluates - with special
attention to time_step 43-49, where the original paper (Oliveira et al.,
KDD 2021) reports a 10-16 percentage point F1 improvement from these
features alone.

Usage:
    python train_baseline_guiltywalker.py
    python train_baseline_guiltywalker.py --k_walks 50 --max_attempts 200  # closer to paper's fidelity, slower
    python train_baseline_guiltywalker.py --k_walks 15 --max_attempts 60   # faster, rougher
"""
import argparse
import json
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    precision_recall_curve, auc, f1_score, roc_auc_score,
    precision_score, recall_score, classification_report
)

from data_loader import load_elliptic
from train_baseline import recall_at_precision
from guilty_walker import compute_guiltywalker_features, FEATURE_NAMES

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "models")


def per_timestep_f1(y_true, y_pred, time_steps):
    rows = []
    for t in sorted(np.unique(time_steps)):
        mask = time_steps == t
        yt, yp = y_true[mask], y_pred[mask]
        if yt.sum() == 0:
            f1 = float("nan")
        else:
            f1 = f1_score(yt, yp, zero_division=0)
        rows.append({"time_step": int(t), "n_illicit": int(yt.sum()), "f1": f1})
    return pd.DataFrame(rows)


def main(k_walks=30, max_attempts=120, max_walk_steps=60, cache=True):
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(MODEL_DIR, exist_ok=True)
    data = load_elliptic()

    n_nodes = data.num_nodes
    edge_index = data.edge_index.numpy()
    y = data.y.numpy()
    time_steps = data.time_step.numpy()

    gw_cache_path = os.path.join(OUT_DIR, "guiltywalker_features.csv")
    if cache and os.path.exists(gw_cache_path):
        print(f"Loading cached GuiltyWalker features from {gw_cache_path} "
              f"(delete this file to recompute)")
        gw_df = pd.read_csv(gw_cache_path)
    else:
        print("Computing GuiltyWalker features (this is the slow part - "
              "progress prints every 20,000 nodes)...")
        gw_df = compute_guiltywalker_features(
            edge_index, y, n_nodes,
            k_walks=k_walks, max_attempts_per_node=max_attempts,
            max_walk_steps=max_walk_steps,
        )
        gw_df.to_csv(gw_cache_path, index=False)
        print(f"Cached -> {gw_cache_path}")

    X_raw = data.x.numpy()
    X_hybrid = np.concatenate([X_raw, gw_df.values], axis=1)
    print(f"Raw features: {X_raw.shape[1]}, GuiltyWalker features: {gw_df.shape[1]}, "
          f"combined (AF+GWF): {X_hybrid.shape[1]}")

    train_mask = data.train_mask.numpy()
    test_mask = data.test_mask.numpy()

    X_train, y_train = X_hybrid[train_mask], y[train_mask]
    X_test, y_test = X_hybrid[test_mask], y[test_mask]
    ts_test = time_steps[test_mask]

    clf = RandomForestClassifier(
        n_estimators=200, max_depth=None,
        class_weight="balanced_subsample", n_jobs=-1, random_state=42,
    )
    clf.fit(X_train, y_train)

    y_scores = clf.predict_proba(X_test)[:, 1]
    y_pred = (y_scores >= 0.5).astype(int)

    precisions, recalls, _ = precision_recall_curve(y_test, y_scores)
    pr_auc = auc(recalls, precisions)
    roc_auc = roc_auc_score(y_test, y_scores)
    f1 = f1_score(y_test, y_pred)
    recall_95p, _ = recall_at_precision(y_test, y_scores, 0.95)

    metrics = {
        "model": "RandomForest (AF + GuiltyWalker features)",
        "pr_auc": round(pr_auc, 4),
        "roc_auc": round(roc_auc, 4),
        "f1_at_0.5": round(f1, 4),
        "precision_at_0.5": round(precision_score(y_test, y_pred), 4),
        "recall_at_0.5": round(recall_score(y_test, y_pred), 4),
        "recall_at_95pct_precision": round(recall_95p, 4),
        "n_train": int(train_mask.sum()),
        "n_test": int(test_mask.sum()),
    }
    print(json.dumps(metrics, indent=2))
    print("\n" + classification_report(y_test, y_pred, target_names=["licit", "illicit"]))

    with open(os.path.join(OUT_DIR, "baseline_guiltywalker_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)
    joblib.dump(clf, os.path.join(MODEL_DIR, "baseline_guiltywalker_rf.joblib"))

    # --- The real test: per-timestep, specifically 43-49 ---
    pt_df = per_timestep_f1(y_test, y_pred, ts_test)
    pt_df.to_csv(os.path.join(OUT_DIR, "guiltywalker_per_timestep.csv"), index=False)

    print("\n--- Per-time-step F1 (AF + GuiltyWalker) ---")
    print(pt_df.to_string(index=False))

    drift_step = 43
    post_drift_mean = pt_df[pt_df["time_step"] >= drift_step]["f1"].mean()
    print(f"\nMean F1, steps >= {drift_step} (AF + GuiltyWalker): {post_drift_mean:.4f}")

    baseline_path = os.path.join(OUT_DIR, "per_timestep_breakdown.csv")
    if os.path.exists(baseline_path):
        base_df = pd.read_csv(baseline_path)
        base_rf = base_df[base_df["model"] == "baseline_rf"]
        base_post = base_rf[base_rf["time_step"] >= drift_step]["f1"].mean()
        print(f"Mean F1, steps >= {drift_step} (plain baseline_rf, from earlier run): "
              f"{base_post:.4f}")
        delta = (post_drift_mean - base_post) * 100
        print(f"\n{'='*60}")
        print(f"DELTA in steps >= {drift_step}: {delta:+.1f} percentage points F1")
        print(f"(Published GuiltyWalker result on the original setup: +10 to +16 points)")
        print(f"{'='*60}")
    else:
        print("\n(outputs/per_timestep_breakdown.csv not found - run eval_by_timestep.py "
              "first if you want the direct delta printed here)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--k_walks", type=int, default=30,
                         help="Target number of successful walks per node (paper used 100; "
                              "lower is faster, rougher features)")
    parser.add_argument("--max_attempts", type=int, default=120,
                         help="Cap on total walk attempts per node before giving up")
    parser.add_argument("--max_walk_steps", type=int, default=60,
                         help="Cap on steps per individual walk attempt")
    parser.add_argument("--no_cache", action="store_true",
                         help="Force recomputing GuiltyWalker features even if cached")
    args = parser.parse_args()
    main(k_walks=args.k_walks, max_attempts=args.max_attempts,
         max_walk_steps=args.max_walk_steps, cache=not args.no_cache)
