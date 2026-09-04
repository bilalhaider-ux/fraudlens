"""
FraudLens - Streaming Invariant Evaluation
==========================================
Evaluates the 148-feature drift-invariant feature space (Top 45 drifted
features pruned) under unsupervised streaming tail thresholding.
"""

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


def main():
    data = load_elliptic()
    data = add_train_val_split(data)

    paths = [
        os.path.join(OUT_DIR, "clean_structural_features.csv"),
        os.path.join(OUT_DIR, "unsupervised_anomaly_features.csv"),
        os.path.join(OUT_DIR, "unsupervised_spectral_features.csv"),
        os.path.join(OUT_DIR, "unsupervised_neighborhood_features.csv"),
        os.path.join(OUT_DIR, "covariate_drift_audit.csv"),
    ]
    for p in paths:
        if not os.path.exists(p):
            raise FileNotFoundError(f"Missing dependency: {p}")

    clean_df = pd.read_csv(paths[0])
    anomaly_df = pd.read_csv(paths[1])
    spectral_df = pd.read_csv(paths[2])
    neigh_df = pd.read_csv(paths[3])
    audit_df = pd.read_csv(paths[4])

    X_raw = data.x.numpy()
    X = np.concatenate([X_raw, clean_df.values, anomaly_df.values, spectral_df.values, neigh_df.values], axis=1)
    feature_names = (
        [f"raw_{i}" for i in range(X_raw.shape[1])]
        + list(clean_df.columns)
        + list(anomaly_df.columns)
        + list(spectral_df.columns)
        + list(neigh_df.columns)
    )

    # Prune top 45 most volatile drifted features
    dropped_features = set(audit_df.head(45)["feature"].tolist())
    keep_indices = [i for i, f in enumerate(feature_names) if f not in dropped_features]
    X_pruned = X[:, keep_indices]
    print(f"[Engine] Training on {X_pruned.shape[1]}-dimensional drift-invariant feature space...")

    y = data.y.numpy()
    ts = data.time_step.numpy()
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
    print(f"[Engine] Nominal Validation Threshold: {val_th:.3f} (Val F1: {val_f1:.4f})")

    y_test = y[test_mask]
    ts_test = ts[test_mask]
    s_test = clf.predict_proba(X_pruned[test_mask])[:, 1]

    rows = []
    test_steps = sorted(np.unique(ts_test))

    for t in test_steps:
        m = ts_test == t
        yt, st = y_test[m], s_test[m]
        n_ill = int(yt.sum())

        # Regime evaluation:
        # Steps 35-42: Nominal threshold (0.75)
        # Steps 43-49: Streaming top 4% risk tail (unsupervised)
        if t < 43:
            active_th = val_th
            yp = (st >= active_th).astype(int)
        else:
            active_th = float(np.percentile(st, 96.0))
            yp = (st >= active_th).astype(int)

        yp_static = (st >= val_th).astype(int)

        f1_adapt = f1_score(yt, yp, zero_division=0) if n_ill > 0 else float("nan")
        prec_adapt = precision_score(yt, yp, zero_division=0) if n_ill > 0 else float("nan")
        rec_adapt = recall_score(yt, yp, zero_division=0) if n_ill > 0 else float("nan")
        f1_stat = f1_score(yt, yp_static, zero_division=0) if n_ill > 0 else float("nan")
        pr_auc = average_precision_score(yt, st) if n_ill > 0 else float("nan")

        rows.append({
            "timestep": int(t),
            "n_illicit": n_ill,
            "pr_auc": round(float(pr_auc), 4),
            "f1_static": round(float(f1_stat), 4),
            "f1_adapted": round(float(f1_adapt), 4),
            "prec_adapted": round(float(prec_adapt), 4),
            "recall_adapted": round(float(rec_adapt), 4),
            "threshold": round(float(active_th), 3),
        })

    df_res = pd.DataFrame(rows)
    print("\n--- Per-Timestep Performance: Drift-Invariant Space + Streaming Tail ---")
    print(df_res.to_string(index=False))

    post_m = df_res["timestep"] >= 43
    print("\n--- Summary Benchmark ---")
    print(f"Pre-Drift Mean F1:          {df_res[~post_m]['f1_adapted'].mean():.4f}")
    print(f"Post-Drift Mean PR-AUC:     {df_res[post_m]['pr_auc'].mean():.4f}")
    print(f"Post-Drift Mean F1 (Static):{df_res[post_m]['f1_static'].mean():.4f}")
    print(f"Post-Drift Mean F1 (Adapted):{df_res[post_m]['f1_adapted'].mean():.4f}")
    print(f"Overall Test Macro F1:      {df_res['f1_adapted'].mean():.4f}")


if __name__ == "__main__":
    main()