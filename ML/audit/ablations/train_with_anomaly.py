"""
FraudLens - LightGBM Evaluation with Unsupervised Anomaly Injection
==================================================================
Evaluates performance lift of unsupervised time-step anomaly features
combined with raw node attributes and clean structural topology.
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
from sklearn.metrics import average_precision_score, f1_score, precision_score, recall_score

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
            "pr_auc": pr_auc,
            "precision": prec,
            "recall": rec,
            "f1": f1,
        })
    return pd.DataFrame(rows)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(MODEL_DIR, exist_ok=True)

    data = load_elliptic()
    data = add_train_val_split(data)

    clean_struct_path = os.path.join(OUT_DIR, "clean_structural_features.csv")
    anomaly_path = os.path.join(OUT_DIR, "unsupervised_anomaly_features.csv")

    for p in [clean_struct_path, anomaly_path]:
        if not os.path.exists(p):
            raise FileNotFoundError(f"Missing {p}. Generate dependencies first.")

    clean_df = pd.read_csv(clean_struct_path)
    anomaly_df = pd.read_csv(anomaly_path)

    X_raw = data.x.numpy()
    X = np.concatenate([X_raw, clean_df.values, anomaly_df.values], axis=1)
    feature_names = (
        [f"raw_{i}" for i in range(X_raw.shape[1])]
        + list(clean_df.columns)
        + list(anomaly_df.columns)
    )
    print(f"Total features entering model: {X.shape[1]} (Raw: {X_raw.shape[1]}, Clean Graph: {clean_df.shape[1]}, Anomaly: {anomaly_df.shape[1]})")

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

    s_val = clf.predict_proba(X[val_mask])[:, 1]
    val_th, val_f1 = best_f1_threshold(y[val_mask], s_val)
    print(f"Validation-tuned threshold: {val_th:.3f} (Validation F1: {val_f1:.4f})")

    y_test = y[test_mask]
    ts_test = time_steps[test_mask]
    s_test = clf.predict_proba(X[test_mask])[:, 1]
    y_pred = (s_test >= val_th).astype(int)

    df_res = per_timestep_metrics(y_test, y_pred, s_test, ts_test)
    print("\n--- Per-Timestep Performance with Anomaly Injection ---")
    print(df_res.to_string(index=False))

    post_mask = df_res["timestep"] >= 43
    print(f"\nOverall Test Pooled F1: {f1_score(y_test, y_pred, zero_division=0):.4f}")
    print(f"Overall Test Macro F1:  {df_res['f1'].mean():.4f}")
    print(f"Overall Test PR-AUC:    {average_precision_score(y_test, s_test):.4f}")
    print(f"Pre-drift (35-42) Mean F1:  {df_res[~post_mask]['f1'].mean():.4f}")
    print(f"Post-drift (43-49) Mean PR-AUC: {df_res[post_mask]['pr_auc'].mean():.4f}")
    print(f"Post-drift (43-49) Mean F1:    {df_res[post_mask]['f1'].mean():.4f}")

    # Inspect Feature Importance to see if anomaly signals are utilized
    importances = clf.feature_importances_
    top_idx = np.argsort(importances)[::-1][:20]
    top_features = {feature_names[i]: int(importances[i]) for i in top_idx}
    print("\nTop 20 Features by Importance:")
    print(json.dumps(top_features, indent=2))

    # Check rank of our new anomaly features specifically
    anomaly_ranks = {name: int(importances[feature_names.index(name)]) for name in anomaly_df.columns}
    print("\nAnomaly Feature Splits:")
    print(json.dumps(anomaly_ranks, indent=2))


if __name__ == "__main__":
    main()