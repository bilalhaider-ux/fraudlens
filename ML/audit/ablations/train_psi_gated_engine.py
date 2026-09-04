"""
FraudLens - 193-Feature Pipeline with PSI-Gated Dual-Regime Thresholding
=======================================================================
Combines all 193 clean features. Employs Population Stability Index (PSI)
to detect stream distribution collapse and route between Nominal
high-precision cutoffs and Drift-Adaptive EVT tail cutoffs.
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
from scipy.stats import genpareto
from sklearn.metrics import average_precision_score, f1_score, precision_score, recall_score

from data_loader import load_elliptic, add_train_val_split
from train_prior_correction import best_f1_threshold

OUT_DIR = os.path.join(CURRENT_DIR, "..", "outputs")
MODEL_DIR = os.path.join(CURRENT_DIR, "..", "models")
MODEL_PATH = os.path.join(MODEL_DIR, "lgbm.joblib")


def compute_psi(reference_scores, target_scores, num_buckets=10, eps=1e-4):
    """
    Computes Population Stability Index (PSI) between validation
    reference probability distributions and target timestep stream.
    """
    quantiles = np.linspace(0, 100, num_buckets + 1)
    bins = np.percentile(reference_scores, quantiles)
    bins[0] = -np.inf
    bins[-1] = np.inf

    ref_counts, _ = np.histogram(reference_scores, bins=bins)
    target_counts, _ = np.histogram(target_scores, bins=bins)

    ref_pct = (ref_counts + eps) / (len(reference_scores) + eps * num_buckets)
    target_pct = (target_counts + eps) / (len(target_scores) + eps * num_buckets)

    psi_val = np.sum((target_pct - ref_pct) * np.log(target_pct / ref_pct))
    return float(psi_val)


def fit_evt_threshold(scores_t, base_percentile=90.0, target_tail_prob=0.04):
    u = np.percentile(scores_t, base_percentile)
    excesses = scores_t[scores_t > u] - u

    if len(excesses) < 20:
        return float(np.percentile(scores_t, 100 * (1 - target_tail_prob)))

    try:
        c, loc, scale = genpareto.fit(excesses, floc=0)
        p_u = len(excesses) / len(scores_t)
        if target_tail_prob >= p_u:
            return float(u)
        q = target_tail_prob / p_u
        if abs(c) < 1e-4:
            x_q = -scale * np.log(q)
        else:
            x_q = (scale / c) * (np.power(q, -c) - 1.0)
        return float(np.clip(u + x_q, 0.05, 0.95))
    except Exception:
        return float(np.percentile(scores_t, 100 * (1 - target_tail_prob)))


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
    print(f"Total Feature Space: {X.shape[1]} (Raw: 165, Graph: 9, Anomaly: 3, SVD: 8, Convolutions: 8)")

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
        X[train_mask],
        y[train_mask],
        eval_set=[(X[val_mask], y[val_mask])],
        callbacks=[lgb.early_stopping(30, verbose=False)],
    )

    joblib.dump(clf, MODEL_PATH)

    s_val = clf.predict_proba(X[val_mask])[:, 1]
    val_th, val_f1 = best_f1_threshold(y[val_mask], s_val)
    print(f"Validation Optimal Static Threshold: {val_th:.3f} (Val F1: {val_f1:.4f})")

    y_test = y[test_mask]
    ts_test = ts[test_mask]
    s_test = clf.predict_proba(X[test_mask])[:, 1]

    rows = []
    test_steps = sorted(np.unique(ts_test))

    all_pred_static = []
    all_pred_gated = []

    for t in test_steps:
        m = ts_test == t
        yt, st = y_test[m], s_test[m]
        n_ill = int(yt.sum())

        psi_t = compute_psi(s_val, st)

        # PSI-Gated Threshold Policy
        if psi_t < 0.25:
            regime = "Nominal"
            active_th = val_th
        else:
            regime = "Drifted"
            active_th = fit_evt_threshold(st, base_percentile=90.0, target_tail_prob=0.04)

        yp_stat = (st >= val_th).astype(int)
        yp_gate = (st >= active_th).astype(int)

        all_pred_static.extend(yp_stat)
        all_pred_gated.extend(yp_gate)

        f1_stat = f1_score(yt, yp_stat, zero_division=0) if n_ill > 0 else float("nan")
        f1_gate = f1_score(yt, yp_gate, zero_division=0) if n_ill > 0 else float("nan")
        rec_gate = recall_score(yt, yp_gate, zero_division=0) if n_ill > 0 else float("nan")
        pr_auc = average_precision_score(yt, st) if n_ill > 0 else float("nan")

        rows.append({
            "timestep": int(t),
            "n_illicit": n_ill,
            "psi": round(psi_t, 3),
            "regime": regime,
            "cutoff": round(float(active_th), 3),
            "pr_auc": round(float(pr_auc), 4),
            "f1_static": round(float(f1_stat), 4),
            "f1_gated": round(float(f1_gate), 4),
            "recall_gated": round(float(rec_gate), 4),
        })

    df_res = pd.DataFrame(rows)
    print("\n--- Per-Timestep Performance: Static vs. PSI-Gated Dual-Regime ---")
    print(df_res.to_string(index=False))

    post_mask = df_res["timestep"] >= 43
    print("\n--- Final System Benchmark ---")
    print(f"Overall Test Pooled F1 (Static):    {f1_score(y_test, all_pred_static, zero_division=0):.4f}")
    print(f"Overall Test Pooled F1 (PSI-Gated): {f1_score(y_test, all_pred_gated, zero_division=0):.4f}")
    print(f"Overall Test Macro F1 (Static):     {df_res['f1_static'].mean():.4f}")
    print(f"Overall Test Macro F1 (PSI-Gated):  {df_res['f1_gated'].mean():.4f}")
    print(f"Pre-Drift (35-42) Mean F1:          {df_res[~post_mask]['f1_gated'].mean():.4f}")
    print(f"Post-Drift (43-49) Mean PR-AUC:     {df_res[post_mask]['pr_auc'].mean():.4f}")
    print(f"Post-Drift (43-49) Mean F1:         {df_res[post_mask]['f1_gated'].mean():.4f}")

    # Inspect splits of the new neighborhood features
    importances = clf.feature_importances_
    neigh_splits = {name: int(importances[feature_names.index(name)]) for name in neigh_df.columns}
    print("\nNeighborhood Convolution Feature Splits:")
    print(json.dumps(neigh_splits, indent=2))


if __name__ == "__main__":
    main()