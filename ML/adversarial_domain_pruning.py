"""
FraudLens - Adversarial Covariate Shift Auditing and Pruning
===========================================================
Identifies and eliminates features undergoing extreme distribution
shift post-timestep 43 via domain classification and Kolmogorov-Smirnov
divergence testing. Retrains LightGBM on the invariant feature manifold.
"""

import json
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.stats import ks_2samp
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from data_loader import load_elliptic, add_train_val_split
from train_prior_correction import best_f1_threshold

OUT_DIR = os.path.join(CURRENT_DIR, "..", "outputs")
MODEL_DIR = os.path.join(CURRENT_DIR, "..", "models")


def per_timestep_metrics(y_true, y_pred, y_scores, time_steps):
    rows = []
    for t in sorted(np.unique(time_steps)):
        mask = time_steps == t
        yt, yp, ys = y_true[mask], y_pred[mask], y_scores[mask]
        n_ill = int(yt.sum())

        f1 = f1_score(yt, yp, zero_division=0) if n_ill > 0 else float("nan")
        prec = precision_score(yt, yp, zero_division=0) if n_ill > 0 else float("nan")
        rec = recall_score(yt, yp, zero_division=0) if n_ill > 0 else float("nan")
        pr_auc = average_precision_score(yt, ys) if n_ill > 0 else float("nan")

        rows.append({
            "timestep": int(t),
            "n_illicit": n_ill,
            "total_nodes": int(mask.sum()),
            "pr_auc": round(float(pr_auc), 4),
            "precision": round(float(prec), 4),
            "recall": round(float(rec), 4),
            "f1": round(float(f1), 4),
        })
    return pd.DataFrame(rows)


def run_domain_adversarial_audit(X, time_steps, feature_names):
    """
    FIXED: the original version fit domain_clf on X_domain then evaluated
    (predict_proba + AUC) on that SAME X_domain - a classic train/eval-on-
    training-data mistake. A 100-tree, 31-leaf LightGBM model will report
    near-perfect separation on almost any two groups when evaluated on data
    it was fit on, real shift or not - this alone plausibly explains the
    AUC=1.0000 result without needing genuine covariate shift at that
    severity (independent research earlier in this project found the real
    feature-level shift is smooth/continuous, not a clean discontinuity).

    Fix: use out-of-fold predictions from k-fold cross-validation, so the
    AUC and feature importances reflect genuine held-out separability, not
    memorization.
    """
    from sklearn.model_selection import cross_val_predict, StratifiedKFold

    pre_mask = time_steps < 35
    post_mask = time_steps >= 43

    idx_pre = np.where(pre_mask)[0]
    idx_post = np.where(post_mask)[0]

    rng = np.random.default_rng(42)
    idx_pre_sampled = rng.choice(idx_pre, size=len(idx_post), replace=False)

    domain_idx = np.concatenate([idx_pre_sampled, idx_post])
    d_labels = np.concatenate([np.zeros(len(idx_pre_sampled)), np.ones(len(idx_post))])

    X_domain = X[domain_idx]

    domain_clf = lgb.LGBMClassifier(
        n_estimators=100,
        num_leaves=31,
        learning_rate=0.05,
        random_state=42,
        verbosity=-1,
        n_jobs=-1,
    )

    # Held-out predictions via 5-fold CV - each example scored only by a
    # model that never saw it during training.
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    domain_preds_oof = cross_val_predict(
        domain_clf, X_domain, d_labels, cv=cv, method="predict_proba", n_jobs=-1
    )[:, 1]
    domain_auc_oof = roc_auc_score(d_labels, domain_preds_oof)
    print(f"[Audit] Adversarial Domain Discriminator ROC-AUC "
          f"(5-fold CV, HELD-OUT, not train-evaluated): {domain_auc_oof:.4f}")

    # Also report the original (flawed) same-data number for direct comparison,
    # clearly labeled, so the gap between them is visible rather than hidden.
    domain_clf.fit(X_domain, d_labels)
    domain_preds_traineval = domain_clf.predict_proba(X_domain)[:, 1]
    domain_auc_traineval = roc_auc_score(d_labels, domain_preds_traineval)
    print(f"[Audit] (For comparison) ROC-AUC evaluated on TRAINING data "
          f"(the original, flawed method): {domain_auc_traineval:.4f}")
    print(f"[Audit] Gap between the two: {domain_auc_traineval - domain_auc_oof:.4f} "
          f"- a large gap confirms the original number was overfitting, not real shift.")

    # Feature importances from the full-data fit (used only for ranking which
    # features to prune, not for the AUC claim itself - importances aren't
    # subject to the same train/eval leakage issue since we're not scoring
    # held-out accuracy with them here, just ranking).
    importances = domain_clf.feature_importances_

    ks_stats = []
    for j in range(X.shape[1]):
        stat, _ = ks_2samp(X[pre_mask, j], X[post_mask, j])
        ks_stats.append(stat)
    ks_stats = np.array(ks_stats)

    audit_df = pd.DataFrame({
        "feature": feature_names,
        "domain_splits": importances,
        "ks_stat": ks_stats,
    }).sort_values(by=["domain_splits", "ks_stat"], ascending=[False, False])

    return audit_df, domain_auc_oof, domain_auc_traineval


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(MODEL_DIR, exist_ok=True)

    data = load_elliptic()
    data = add_train_val_split(data)

    paths = [
        os.path.join(OUT_DIR, "clean_structural_features.csv"),
        os.path.join(OUT_DIR, "unsupervised_anomaly_features.csv"),
        os.path.join(OUT_DIR, "unsupervised_spectral_features.csv"),
        os.path.join(OUT_DIR, "unsupervised_neighborhood_features.csv"),
    ]
    for p in paths:
        if not os.path.exists(p):
            raise FileNotFoundError(f"Missing dependency: {p}")

    clean_df = pd.read_csv(paths[0])
    anomaly_df = pd.read_csv(paths[1])
    spectral_df = pd.read_csv(paths[2])
    neigh_df = pd.read_csv(paths[3])

    X_raw = data.x.numpy()
    X = np.concatenate([X_raw, clean_df.values, anomaly_df.values, spectral_df.values, neigh_df.values], axis=1)
    feature_names = (
        [f"raw_{i}" for i in range(X_raw.shape[1])]
        + list(clean_df.columns)
        + list(anomaly_df.columns)
        + list(spectral_df.columns)
        + list(neigh_df.columns)
    )

    y = data.y.numpy()
    time_steps = data.time_step.numpy()
    train_mask = data.train_mask.numpy()
    val_mask = data.val_mask.numpy()
    test_mask = data.test_mask.numpy()

    # Step 1: Run Domain Adversarial Audit
    audit_df, domain_auc_oof, domain_auc_traineval = run_domain_adversarial_audit(
        X, time_steps, feature_names)
    audit_path = os.path.join(OUT_DIR, "covariate_drift_audit.csv")
    audit_df.to_csv(audit_path, index=False)
    print(f"[Audit] Full covariate drift audit saved -> {audit_path}")
    print("\nTop 15 Most Drifted Features (Driving Domain Separation):")
    print(audit_df.head(15).to_string(index=False))

    # Step 2: Test multiple pruning cutoffs (Drop Top 10, 25, 40 most drifted features)
    prune_levels = [0, 15, 30, 45]
    summary_records = []

    for k in prune_levels:
        if k == 0:
            active_features = feature_names
            keep_indices = np.arange(X.shape[1])
        else:
            dropped_features = set(audit_df.head(k)["feature"].tolist())
            keep_indices = [i for i, f in enumerate(feature_names) if f not in dropped_features]
            active_features = [feature_names[i] for i in keep_indices]

        X_sub = X[:, keep_indices]

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
            X_sub[train_mask],
            y[train_mask],
            eval_set=[(X_sub[val_mask], y[val_mask])],
            callbacks=[lgb.early_stopping(30, verbose=False)],
        )

        s_val = clf.predict_proba(X_sub[val_mask])[:, 1]
        val_th, val_f1 = best_f1_threshold(y[val_mask], s_val)

        y_test = y[test_mask]
        ts_test = time_steps[test_mask]
        s_test = clf.predict_proba(X_sub[test_mask])[:, 1]
        y_pred = (s_test >= val_th).astype(int)

        df_metrics = per_timestep_metrics(y_test, y_pred, s_test, ts_test)
        post_m = df_metrics["timestep"] >= 43

        pooled_f1 = f1_score(y_test, y_pred, zero_division=0)
        macro_f1 = df_metrics["f1"].mean()
        pre_f1 = df_metrics[~post_m]["f1"].mean()
        post_f1 = df_metrics[post_m]["f1"].mean()
        post_pr_auc = df_metrics[post_m]["pr_auc"].mean()

        summary_records.append({
            "pruned_features": k,
            "remaining_dim": len(active_features),
            "val_threshold": round(float(val_th), 3),
            "pooled_f1": round(float(pooled_f1), 4),
            "macro_f1": round(float(macro_f1), 4),
            "pre_drift_f1": round(float(pre_f1), 4),
            "post_drift_f1": round(float(post_f1), 4),
            "post_drift_pr_auc": round(float(post_pr_auc), 4),
        })

        if k == 30:
            print(f"\n--- Per-Timestep Breakdown for Prune Level K={k} ---")
            print(df_metrics.to_string(index=False))

    summary_df = pd.DataFrame(summary_records)
    print("\n--- Adversarial Pruning Comparison Summary ---")
    print(summary_df.to_string(index=False))
    summary_df.to_csv(os.path.join(OUT_DIR, "adversarial_pruning_summary.csv"), index=False)


if __name__ == "__main__":
    main()