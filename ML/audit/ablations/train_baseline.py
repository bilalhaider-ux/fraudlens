"""
FraudLens - Baseline Model
============================
Random Forest on node features ONLY (ignores graph structure entirely).
This is the benchmark the GNN must beat to justify using graph structure at all.

Uses the same temporal train/test split as the GNN for a fair comparison.
"""
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

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "models")


def recall_at_precision(y_true, y_scores, target_precision=0.95):
    """What recall do we get if we demand >= target_precision?
    This is the operationally meaningful number: 'catch X% of fraud while
    keeping false positives below (1 - target_precision)'."""
    precisions, recalls, thresholds = precision_recall_curve(y_true, y_scores)
    # precision_recall_curve returns arrays 1 longer than thresholds; align
    mask = precisions[:-1] >= target_precision
    if not mask.any():
        return 0.0, None
    best_recall = recalls[:-1][mask].max()
    best_idx = np.where(mask)[0][np.argmax(recalls[:-1][mask])]
    return float(best_recall), float(thresholds[best_idx])


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(MODEL_DIR, exist_ok=True)
    data = load_elliptic()

    X = data.x.numpy()
    y = data.y.numpy()

    train_mask = data.train_mask.numpy()
    test_mask = data.test_mask.numpy()

    X_train, y_train = X[train_mask], y[train_mask]
    X_test, y_test = X[test_mask], y[test_mask]

    print(f"Train: {X_train.shape}, illicit={y_train.sum()} ({y_train.mean():.2%})")
    print(f"Test:  {X_test.shape}, illicit={y_test.sum()} ({y_test.mean():.2%})")

    clf = RandomForestClassifier(
        n_estimators=200,
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
    recall_at_95p, thresh_95p = recall_at_precision(y_test, y_scores, 0.95)

    metrics = {
        "model": "RandomForest (baseline, features only)",
        "pr_auc": round(pr_auc, 4),
        "roc_auc": round(roc_auc, 4),
        "f1_at_0.5": round(f1, 4),
        "precision_at_0.5": round(precision_score(y_test, y_pred), 4),
        "recall_at_0.5": round(recall_score(y_test, y_pred), 4),
        "recall_at_95pct_precision": round(recall_at_95p, 4),
        "n_train": int(train_mask.sum()),
        "n_test": int(test_mask.sum()),
    }

    print(json.dumps(metrics, indent=2))
    print("\n" + classification_report(y_test, y_pred, target_names=["licit", "illicit"]))

    with open(os.path.join(OUT_DIR, "baseline_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)

    joblib.dump(clf, os.path.join(MODEL_DIR, "baseline_rf.joblib"))
    print(f"Saved model -> models/baseline_rf.joblib")

    # feature importances -> used later as an explainability fallback if GNNExplainer is too slow
    importances = clf.feature_importances_
    top_idx = np.argsort(importances)[::-1][:15]
    top_features = {f"f_{i}": round(float(importances[i]), 5) for i in top_idx}
    with open(os.path.join(OUT_DIR, "baseline_feature_importance.json"), "w") as f:
        json.dump(top_features, f, indent=2)
    print("\nTop 15 features by importance:", json.dumps(top_features, indent=2))


if __name__ == "__main__":
    main()