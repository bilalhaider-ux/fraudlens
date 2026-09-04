"""
FraudLens - Honest Inference Diagnostic & Threshold Calibration
================================================================
Evaluates LightGBM with pure features, sanitizes graph metrics,
and tests dynamic thresholding across the timestep 43 drift boundary.
"""

import json
import os
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, precision_score, recall_score

from data_loader import load_elliptic, add_train_val_split

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs")


def evaluate_threshold(y_true, scores, threshold):
    preds = (scores >= threshold).astype(int)
    return {
        "precision": precision_score(y_true, preds, zero_division=0),
        "recall": recall_score(y_true, preds, zero_division=0),
        "f1": f1_score(y_true, preds, zero_division=0),
    }


def main():
    data = load_elliptic()
    data = add_train_val_split(data)

    X = data.x.numpy()
    y = data.y.numpy()
    time_steps = data.time_step.numpy()

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
        X[train_mask],
        y[train_mask],
        eval_set=[(X[val_mask], y[val_mask])],
        callbacks=[lgb.early_stopping(30, verbose=False)],
    )

    y_test = y[test_mask]
    ts_test = time_steps[test_mask]
    s_test = clf.predict_proba(X[test_mask])[:, 1]

    print("\n--- Post-Drift Score Distributions (Timesteps 43-49) ---")
    post_mask = ts_test >= 43
    y_post = y_test[post_mask]
    s_post = s_test[post_mask]

    print(f"Post-43 Illicit Node Probabilities: Mean={s_post[y_post == 1].mean():.3f}, "
          f"Median={np.median(s_post[y_post == 1]):.3f}, Max={s_post[y_post == 1].max():.3f}")
    print(f"Post-43 Licit Node Probabilities:   Mean={s_post[y_post == 0].mean():.3f}, "
          f"Median={np.median(s_post[y_post == 0]):.3f}, Max={s_post[y_post == 0].max():.3f}")

    print("\n--- Post-Drift Metric Sensitivity to Threshold ---")
    for th in [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.875]:
        res = evaluate_threshold(y_post, s_post, th)
        print(f"Threshold {th:.3f} -> Precision: {res['precision']:.4f} | "
              f"Recall: {res['recall']:.4f} | F1: {res['f1']:.4f}")


if __name__ == "__main__":
    main()