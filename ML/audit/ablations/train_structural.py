"""
FraudLens - AF + GuiltyWalker + Structural Graph Features
==============================================================
Adds the non-learned structural features (k-core, HITS, personalized
PageRank, Louvain community guilt-density - see structural_features.py) on
top of the current best model (raw features + GuiltyWalker), using the
same validation-tuned threshold approach that's currently the best
legitimate result (post-43 mean F1 = 0.4791).

Usage:
    python train_structural.py
"""
import json
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score, precision_score, recall_score

from data_loader import load_elliptic, add_train_val_split
from structural_features import compute_structural_features
from train_prior_correction import best_f1_threshold

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "models")


def per_timestep_f1(y_true, y_pred, time_steps):
    rows = []
    for t in sorted(np.unique(time_steps)):
        mask = time_steps == t
        yt, yp = y_true[mask], y_pred[mask]
        f1 = f1_score(yt, yp, zero_division=0) if yt.sum() > 0 else float("nan")
        prec = precision_score(yt, yp, zero_division=0) if yt.sum() > 0 else float("nan")
        rec = recall_score(yt, yp, zero_division=0) if yt.sum() > 0 else float("nan")
        rows.append({"time_step": int(t), "n_illicit": int(yt.sum()),
                      "precision": prec, "recall": rec, "f1": f1})
    return pd.DataFrame(rows)


def main(cache=True):
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(MODEL_DIR, exist_ok=True)
    data = load_elliptic()
    data = add_train_val_split(data)

    n_nodes = data.num_nodes
    edge_index = data.edge_index.numpy()
    y = data.y.numpy()
    time_steps = data.time_step.numpy()

    struct_cache = os.path.join(OUT_DIR, "structural_features.csv")
    if cache and os.path.exists(struct_cache):
        print(f"Loading cached structural features from {struct_cache} "
              f"(delete this file to recompute)")
        struct_df = pd.read_csv(struct_cache)
    else:
        print("Computing structural features (k-core, HITS, PPR, community) "
              "per time-step subgraph...")
        struct_df = compute_structural_features(edge_index, y, time_steps, n_nodes)
        struct_df.to_csv(struct_cache, index=False)
        print(f"Cached -> {struct_cache}")

    gwf_path = os.path.join(OUT_DIR, "guiltywalker_features.csv")
    if not os.path.exists(gwf_path):
        raise FileNotFoundError(f"{gwf_path} not found - run train_baseline_guiltywalker.py first")
    gwf_df = pd.read_csv(gwf_path)

    X_raw = data.x.numpy()
    X = np.concatenate([X_raw, gwf_df.values, struct_df.values], axis=1)
    print(f"Raw: {X_raw.shape[1]}, GuiltyWalker: {gwf_df.shape[1]}, "
          f"Structural: {struct_df.shape[1]}, combined: {X.shape[1]}")

    train_mask = data.train_mask.numpy()
    val_mask = data.val_mask.numpy()
    test_mask = data.test_mask.numpy()

    clf = RandomForestClassifier(
        n_estimators=200, max_depth=None,
        class_weight="balanced_subsample", n_jobs=-1, random_state=42,
    )
    clf.fit(X[train_mask], y[train_mask])

    # validation-tuned threshold - same approach as our current best model
    y_val, s_val = y[val_mask], clf.predict_proba(X[val_mask])[:, 1]
    val_threshold, val_f1 = best_f1_threshold(y_val, s_val)
    print(f"Validation-tuned threshold: {val_threshold:.3f} (val F1: {val_f1:.4f})")

    y_test = y[test_mask]
    s_test = clf.predict_proba(X[test_mask])[:, 1]
    ts_test = time_steps[test_mask]
    y_pred = (s_test >= val_threshold).astype(int)

    overall_f1 = f1_score(y_test, y_pred)
    metrics = {
        "model": "RF (AF + GuiltyWalker + Structural features, val-tuned threshold)",
        "val_threshold": round(float(val_threshold), 4),
        "overall_f1": round(float(overall_f1), 4),
        "overall_precision": round(float(precision_score(y_test, y_pred)), 4),
        "overall_recall": round(float(recall_score(y_test, y_pred)), 4),
    }
    print(json.dumps(metrics, indent=2))

    with open(os.path.join(OUT_DIR, "structural_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)
    joblib.dump(clf, os.path.join(MODEL_DIR, "structural_rf.joblib"))

    pt_df = per_timestep_f1(y_test, y_pred, ts_test)
    pt_df.to_csv(os.path.join(OUT_DIR, "structural_per_timestep.csv"), index=False)
    print("\n--- Per-time-step (AF + GuiltyWalker + Structural, val-tuned threshold) ---")
    print(pt_df.to_string(index=False))

    drift_step = 43
    post = pt_df[pt_df["time_step"] >= drift_step]["f1"].mean()
    print(f"\nMean F1, steps >= {drift_step}: {post:.4f}")
    print("For reference: default_0.5 (AF+GWF only) was 0.2944, "
          "val_tuned (AF+GWF only) was 0.4791, "
          "prior-correction (AF+GWF only) was 0.3171, "
          "oracle (cheating, diagnostic ceiling) was 0.9621")

    if post > 0.4791:
        print(f"\n{'='*60}")
        print(f"NEW BEST: structural features improved on val_tuned by "
              f"{(post - 0.4791) * 100:+.1f} percentage points")
        print(f"{'='*60}")
    else:
        print(f"\nDid not beat the current best (0.4791) - delta: "
              f"{(post - 0.4791) * 100:+.1f} percentage points")

    # feature importance - which structural features actually mattered?
    feat_names = (list(range(X_raw.shape[1])) + list(gwf_df.columns) + list(struct_df.columns))
    importances = clf.feature_importances_
    struct_start = X_raw.shape[1] + gwf_df.shape[1]
    struct_importance = {name: round(float(importances[struct_start + i]), 5)
                          for i, name in enumerate(struct_df.columns)}
    print("\nStructural feature importances:")
    print(json.dumps(struct_importance, indent=2))


if __name__ == "__main__":
    main()
