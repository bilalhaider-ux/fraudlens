"""
FraudLens - Covariate Density Ratio Reweighting & Stochastic Subspace Engine
===========================================================================
Applies bounded importance weighting w(x) = P_post(x) / P_pre(x) to align
training risk minimization with the post-drift operational manifold.
Enforces stochastic subspace partitioning to eliminate greedy root bias.
"""

import json
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, f1_score, precision_score, recall_score

from data_loader import load_elliptic, add_train_val_split
from train_prior_correction import best_f1_threshold

OUT_DIR = os.path.join(CURRENT_DIR, "..", "outputs")
MODEL_DIR = os.path.join(CURRENT_DIR, "..", "models")


def estimate_density_ratios(X_train, X_post, max_weight=5.0, min_weight=0.2):
    """
    Trains a regularized domain discriminator to estimate smooth density
    ratios w(x) = P_post(x) / P_pre(x) without gradient explosion.
    """
    n_train = len(X_train)
    n_post = len(X_post)

    X_dom = np.concatenate([X_train, X_post], axis=0)
    y_dom = np.concatenate([np.zeros(n_train), np.ones(n_post)], axis=0)

    # Regularized domain discriminator (shallow depth prevents AUC=1.0 overconfidence)
    dom_clf = lgb.LGBMClassifier(
        n_estimators=60,
        max_depth=3,
        num_leaves=7,
        learning_rate=0.03,
        colsample_bytree=0.6,
        subsample=0.8,
        subsample_freq=1,
        random_state=42,
        verbosity=-1,
        n_jobs=-1,
    )
    dom_clf.fit(X_dom, y_dom)

    # Predict propensity P(D = post | X) on training transactions
    p_post = dom_clf.predict_proba(X_train)[:, 1]
    p_post = np.clip(p_post, 0.02, 0.98)

    # Density ratio: (p / (1 - p)) * (N_pre / N_post)
    base_ratio = n_train / max(n_post, 1)
    raw_weights = (p_post / (1.0 - p_post)) * (1.0 / base_ratio)

    # Normalize mean to 1.0 and clip extreme tails
    weights = raw_weights / np.mean(raw_weights)
    weights = np.clip(weights, min_weight, max_weight)
    return weights


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

    # Retain invariant 150-dimensional subspace
    dropped_features = set(audit_df.head(45)["feature"].tolist())
    keep_indices = [i for i, f in enumerate(feature_names) if f not in dropped_features]
    X_pruned = X[:, keep_indices]

    y = data.y.numpy()
    ts = data.time_step.numpy()
    train_mask = data.train_mask.numpy()
    val_mask = data.val_mask.numpy()
    test_mask = data.test_mask.numpy()

    # Post-drift unlabeled covariate target (steps >= 43)
    post_unlabeled_mask = ts >= 43
    X_train_labeled = X_pruned[train_mask]
    X_post_target = X_pruned[post_unlabeled_mask]

    print(f"[Reweight] Computing density ratio weights between train ({len(X_train_labeled)}) and post-drift ({len(X_post_target)})...")
    density_weights = estimate_density_ratios(X_train_labeled, X_post_target)
    print(f"  -> Density weights min: {density_weights.min():.3f}, max: {density_weights.max():.3f}, mean: {density_weights.mean():.3f}")

    # Combine density ratio weights with class imbalance weights
    y_train = y[train_mask]
    n_pos = int((y_train == 1).sum())
    n_neg = int((y_train == 0).sum())
    class_ratio = n_neg / max(n_pos, 1)

    instance_weights = np.copy(density_weights)
    instance_weights[y_train == 1] *= class_ratio

    # LightGBM with Stochastic Subspace Bagging
    clf = lgb.LGBMClassifier(
        n_estimators=500,
        num_leaves=31,
        learning_rate=0.04,
        colsample_bytree=0.70,  # Forces trees to explore non-dominant features
        subsample=0.80,         # Enables true stochastic bagging
        subsample_freq=1,
        random_state=42,
        verbosity=-1,
        n_jobs=-1,
    )

    clf.fit(
        X_train_labeled,
        y_train,
        sample_weight=instance_weights,
        eval_set=[(X_pruned[val_mask], y[val_mask])],
        callbacks=[lgb.early_stopping(35, verbose=False)],
    )

    s_val = clf.predict_proba(X_pruned[val_mask])[:, 1]
    val_th, val_f1 = best_f1_threshold(y[val_mask], s_val)
    print(f"[Reweight] Validation-Tuned Base Threshold: {val_th:.3f} (Val F1: {val_f1:.4f})")

    y_test = y[test_mask]
    ts_test = ts[test_mask]
    s_test = clf.predict_proba(X_pruned[test_mask])[:, 1]

    rows = []
    test_steps = sorted(np.unique(ts_test))

    for t in test_steps:
        m = ts_test == t
        yt, st = y_test[m], s_test[m]
        n_ill = int(yt.sum())

        if t < 43:
            active_th = val_th
        else:
            active_th = float(np.percentile(st, 96.0))

        yp = (st >= active_th).astype(int)

        f1 = f1_score(yt, yp, zero_division=0) if n_ill > 0 else float("nan")
        prec = precision_score(yt, yp, zero_division=0) if n_ill > 0 else float("nan")
        rec = recall_score(yt, yp, zero_division=0) if n_ill > 0 else float("nan")
        pr_auc = average_precision_score(yt, st) if n_ill > 0 else float("nan")

        rows.append({
            "timestep": int(t),
            "n_illicit": n_ill,
            "pr_auc": round(float(pr_auc), 4),
            "f1": round(float(f1), 4),
            "precision": round(float(prec), 4),
            "recall": round(float(rec), 4),
            "threshold": round(float(active_th), 3),
        })

    df_res = pd.DataFrame(rows)
    print("\n--- Per-Timestep Performance: Covariate Reweighted + Stochastic Subspace ---")
    print(df_res.to_string(index=False))

    post_m = df_res["timestep"] >= 43
    print("\n--- Benchmark Summary ---")
    print(f"Pre-Drift (35-42) Mean F1:   {df_res[~post_m]['f1'].mean():.4f}")
    print(f"Post-Drift (43-49) Mean PR-AUC: {df_res[post_m]['pr_auc'].mean():.4f}")
    print(f"Post-Drift (43-49) Mean F1:     {df_res[post_m]['f1'].mean():.4f}")
    print(f"Overall Test Macro F1:          {df_res['f1'].mean():.4f}")


if __name__ == "__main__":
    main()