"""
FraudLens - Combined Model: Raw + GuiltyWalker + GCN embeddings
====================================================================
The richest feature set available: original 165 features (AF) + 9
GuiltyWalker graph-distance-to-illicit features (GWF) + 64-dim learned GCN
embeddings. Neither the original Elliptic paper nor GuiltyWalker combined
topological-distance features with learned GNN embeddings - this is a novel
combination for this dataset.

Requires, in order:
    python train_gnn.py --model gcn --epochs 150          -> outputs/gcn_embeddings.npy
    python train_baseline_guiltywalker.py                  -> outputs/guiltywalker_features.csv
    python train_combined.py
"""
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

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "models")


def per_timestep_f1(y_true, y_pred, time_steps):
    rows = []
    for t in sorted(np.unique(time_steps)):
        mask = time_steps == t
        yt, yp = y_true[mask], y_pred[mask]
        f1 = f1_score(yt, yp, zero_division=0) if yt.sum() > 0 else float("nan")
        rows.append({"time_step": int(t), "n_illicit": int(yt.sum()), "f1": f1})
    return pd.DataFrame(rows)


def main():
    os.makedirs(MODEL_DIR, exist_ok=True)
    data = load_elliptic()

    gwf_path = os.path.join(OUT_DIR, "guiltywalker_features.csv")
    emb_path = os.path.join(OUT_DIR, "gcn_embeddings.npy")
    for p, hint in [(gwf_path, "run train_baseline_guiltywalker.py first"),
                    (emb_path, "run train_gnn.py --model gcn first")]:
        if not os.path.exists(p):
            raise FileNotFoundError(f"{p} not found - {hint}")

    X_raw = data.x.numpy()
    gwf = pd.read_csv(gwf_path).values
    gcn_emb = np.load(emb_path)

    X_combined = np.concatenate([X_raw, gwf, gcn_emb], axis=1)
    print(f"Raw: {X_raw.shape[1]}, GuiltyWalker: {gwf.shape[1]}, GCN embeddings: {gcn_emb.shape[1]}, "
          f"combined: {X_combined.shape[1]}")

    y = data.y.numpy()
    time_steps = data.time_step.numpy()
    train_mask = data.train_mask.numpy()
    test_mask = data.test_mask.numpy()

    X_train, y_train = X_combined[train_mask], y[train_mask]
    X_test, y_test = X_combined[test_mask], y[test_mask]
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
        "model": "RandomForest (AF + GuiltyWalker + GCN embeddings)",
        "pr_auc": round(pr_auc, 4), "roc_auc": round(roc_auc, 4),
        "f1_at_0.5": round(f1, 4),
        "precision_at_0.5": round(precision_score(y_test, y_pred), 4),
        "recall_at_0.5": round(recall_score(y_test, y_pred), 4),
        "recall_at_95pct_precision": round(recall_95p, 4),
        "n_train": int(train_mask.sum()), "n_test": int(test_mask.sum()),
    }
    print(json.dumps(metrics, indent=2))
    print("\n" + classification_report(y_test, y_pred, target_names=["licit", "illicit"]))

    with open(os.path.join(OUT_DIR, "combined_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)
    joblib.dump(clf, os.path.join(MODEL_DIR, "combined_rf.joblib"))

    pt_df = per_timestep_f1(y_test, y_pred, ts_test)
    pt_df.to_csv(os.path.join(OUT_DIR, "combined_per_timestep.csv"), index=False)
    print("\n--- Per-time-step F1 (AF + GuiltyWalker + GCN embeddings) ---")
    print(pt_df.to_string(index=False))

    drift_step = 43
    combined_post = pt_df[pt_df["time_step"] >= drift_step]["f1"].mean()
    print(f"\nMean F1, steps >= {drift_step} (combined): {combined_post:.4f}")

    gw_path = os.path.join(OUT_DIR, "guiltywalker_per_timestep.csv")
    if os.path.exists(gw_path):
        gw_df = pd.read_csv(gw_path)
        gw_post = gw_df[gw_df["time_step"] >= drift_step]["f1"].mean()
        print(f"Mean F1, steps >= {drift_step} (AF + GuiltyWalker only, from earlier run): "
              f"{gw_post:.4f}")
        print(f"Delta from adding GCN embeddings on top of GuiltyWalker: "
              f"{(combined_post - gw_post) * 100:+.1f} percentage points")

    baseline_path = os.path.join(OUT_DIR, "per_timestep_breakdown.csv")
    if os.path.exists(baseline_path):
        base_df = pd.read_csv(baseline_path)
        base_rf = base_df[base_df["model"] == "baseline_rf"]
        base_post = base_rf[base_rf["time_step"] >= drift_step]["f1"].mean()
        print(f"Mean F1, steps >= {drift_step} (plain baseline_rf): {base_post:.4f}")
        print(f"Total delta vs plain baseline: {(combined_post - base_post) * 100:+.1f} points")


if __name__ == "__main__":
    main()
