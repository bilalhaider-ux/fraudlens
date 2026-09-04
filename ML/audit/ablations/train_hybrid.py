"""
FraudLens - Hybrid Model (GNN embeddings + raw features -> RF)
==================================================================
Motivation: on the Elliptic dataset, a vanilla GCN/GAT typically underperforms
a Random Forest on raw features alone (this is a documented finding in the
original paper, Weber et al. 2019 - not a bug in your code). Their strongest
result came from combining the two: use the GNN purely as a feature extractor
(its learned embeddings capture graph-structural context that the 165 raw
features don't), concatenate those embeddings with the original raw features,
and train a Random Forest / Gradient Boosting classifier on the combined
vector.

Run train_gnn.py first (for whichever model - gcn or gat) so that
outputs/<model>_embeddings.npy exists, then run this script.

Usage:
    python train_gnn.py --model gcn --epochs 150
    python train_hybrid.py --embeddings gcn
"""
import argparse
import json
import os
import joblib

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    precision_recall_curve, auc, f1_score, roc_auc_score,
    precision_score, recall_score, classification_report
)

from data_loader import load_elliptic
from train_baseline import recall_at_precision

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "models")


def main(embeddings_name="gcn"):
    os.makedirs(MODEL_DIR, exist_ok=True)
    data = load_elliptic()
    emb_path = os.path.join(OUT_DIR, f"{embeddings_name}_embeddings.npy")
    if not os.path.exists(emb_path):
        raise FileNotFoundError(
            f"{emb_path} not found. Run `python train_gnn.py --model {embeddings_name}` first."
        )
    embeddings = np.load(emb_path)

    X_raw = data.x.numpy()
    y = data.y.numpy()
    # NOTE: we intentionally use load_elliptic() directly (not add_train_val_split),
    # so train_mask here is the FULL original train region (time_step 1-34) -
    # same data the RF baseline saw, for a fair apples-to-apples comparison.
    # This is safe from leakage: the embeddings were computed via unsupervised
    # message-passing over the graph structure only, never using test labels.
    train_mask = data.train_mask.numpy()
    test_mask = data.test_mask.numpy()

    X_hybrid = np.concatenate([X_raw, embeddings], axis=1)
    print(f"Raw features: {X_raw.shape[1]}, embedding dims: {embeddings.shape[1]}, "
          f"hybrid: {X_hybrid.shape[1]}")

    X_train, y_train = X_hybrid[train_mask], y[train_mask]
    X_test, y_test = X_hybrid[test_mask], y[test_mask]
    print(f"Train: {X_train.shape}, illicit={y_train.sum()} ({y_train.mean():.2%})")
    print(f"Test:  {X_test.shape}, illicit={y_test.sum()} ({y_test.mean():.2%})")

    clf = RandomForestClassifier(
        n_estimators=300,
        max_depth=None,
        class_weight="balanced_subsample",
        n_jobs=-1,
        random_state=42,
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
        "model": f"Hybrid RF ({embeddings_name.upper()} embeddings + raw features)",
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

    with open(os.path.join(OUT_DIR, f"hybrid_{embeddings_name}_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)

    joblib.dump(clf, os.path.join(MODEL_DIR, f"hybrid_{embeddings_name}_rf.joblib"))
    print(f"Saved model -> models/hybrid_{embeddings_name}_rf.joblib")

    # compare against the plain baseline if it's already been run
    baseline_path = os.path.join(OUT_DIR, "baseline_metrics.json")
    if os.path.exists(baseline_path):
        with open(baseline_path) as f:
            baseline = json.load(f)
        print("\n--- Comparison vs plain RF baseline ---")
        for k in ["pr_auc", "roc_auc", "f1_at_0.5", "recall_at_95pct_precision"]:
            print(f"  {k}: baseline={baseline.get(k)} -> hybrid={metrics.get(k)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--embeddings", choices=["gcn", "gat"], default="gcn",
                         help="Which trained model's saved embeddings to use")
    args = parser.parse_args()
    main(embeddings_name=args.embeddings)