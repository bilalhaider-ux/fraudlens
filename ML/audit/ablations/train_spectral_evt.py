"""
FraudLens - 185-Feature Evaluation with EVT Dynamic Cutoffs
===========================================================
Trains LightGBM on Raw + Clean Structural + Anomaly + Spectral features.
Evaluates static thresholding versus Extreme Value Theory (EVT) tail cutoffs.
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


def fit_evt_threshold(scores_t, base_percentile=90.0, target_tail_prob=0.03):
    """
    Fits Peak-Over-Threshold Generalized Pareto Distribution (GPD)
    to mathematically isolate extreme tail risk in the timestep stream.
    """
    u = np.percentile(scores_t, base_percentile)
    excesses = scores_t[scores_t > u] - u

    if len(excesses) < 20:
        return float(np.percentile(scores_t, 100 * (1 - target_tail_prob)))

    try:
        c, loc, scale = genpareto.fit(excesses, floc=0)
        p_u = len(excesses) / len(scores_t)
        # Invert GPD tail CDF
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

    clean_struct_path = os.path.join(OUT_DIR, "clean_structural_features.csv")
    anomaly_path = os.path.join(OUT_DIR, "unsupervised_anomaly_features.csv")
    spectral_path = os.path.join(OUT_DIR, "unsupervised_spectral_features.csv")

    for p in [clean_struct_path, anomaly_path, spectral_path]:
        if not os.path.exists(p):
            raise FileNotFoundError(f"Missing {p}. Generate dependencies first.")

    clean_df = pd.read_csv(clean_struct_path)
    anomaly_df = pd.read_csv(anomaly_path)
    spectral_df = pd.read_csv(spectral_path)

    X_raw = data.x.numpy()
    X = np.concatenate([X_raw, clean_df.values, anomaly_df.values, spectral_df.values], axis=1)
    feature_names = (
        [f"raw_{i}" for i in range(X_raw.shape[1])]
        + list(clean_df.columns)
        + list(anomaly_df.columns)
        + list(spectral_df.columns)
    )
    print(f"Feature Space: {X.shape[1]} (Raw: 165, Clean Graph: 9, Anomaly: 3, Spectral SVD: 8)")

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
    print(f"Validation-tuned Static Threshold: {val_th:.3f} (Val F1: {val_f1:.4f})")

    y_test = y[test_mask]
    ts_test = ts[test_mask]
    s_test = clf.predict_proba(X[test_mask])[:, 1]

    rows = []
    test_steps = sorted(np.unique(ts_test))

    all_pred_static = []
    all_pred_evt = []

    for t in test_steps:
        m = ts_test == t
        yt, st = y_test[m], s_test[m]
        n_ill = int(yt.sum())

        yp_static = (st >= val_th).astype(int)
        evt_th = fit_evt_threshold(st, base_percentile=90.0, target_tail_prob=0.04)
        yp_evt = (st >= evt_th).astype(int)

        all_pred_static.extend(yp_static)
        all_pred_evt.extend(yp_evt)

        f1_stat = f1_score(yt, yp_static, zero_division=0) if n_ill > 0 else float("nan")
        f1_evt = f1_score(yt, yp_evt, zero_division=0) if n_ill > 0 else float("nan")
        rec_stat = recall_score(yt, yp_static, zero_division=0) if n_ill > 0 else float("nan")
        rec_evt = recall_score(yt, yp_evt, zero_division=0) if n_ill > 0 else float("nan")
        pr_auc = average_precision_score(yt, st) if n_ill > 0 else float("nan")

        rows.append({
            "timestep": int(t),
            "n_illicit": n_ill,
            "pr_auc": round(float(pr_auc), 4),
            "f1_static": round(float(f1_stat), 4),
            "f1_evt": round(float(f1_evt), 4),
            "recall_static": round(float(rec_stat), 4),
            "recall_evt": round(float(rec_evt), 4),
            "evt_cutoff": round(float(evt_th), 4),
        })

    df_res = pd.DataFrame(rows)
    print("\n--- Per-Timestep Evaluation: Static vs. EVT Dynamic Cutoff ---")
    print(df_res.to_string(index=False))

    post_mask = df_res["timestep"] >= 43
    print("\n--- Macro & Post-Drift Summary ---")
    print(f"Overall Test Pooled F1 (Static): {f1_score(y_test, all_pred_static, zero_division=0):.4f}")
    print(f"Overall Test Pooled F1 (EVT):    {f1_score(y_test, all_pred_evt, zero_division=0):.4f}")
    print(f"Overall Test Macro F1 (Static):  {df_res['f1_static'].mean():.4f}")
    print(f"Overall Test Macro F1 (EVT):     {df_res['f1_evt'].mean():.4f}")
    print(f"Post-Drift (43-49) Mean PR-AUC:  {df_res[post_mask]['pr_auc'].mean():.4f}")
    print(f"Post-Drift (43-49) Mean F1 (Static): {df_res[post_mask]['f1_static'].mean():.4f}")
    print(f"Post-Drift (43-49) Mean F1 (EVT):    {df_res[post_mask]['f1_evt'].mean():.4f}")

    # Verify usage of newly injected Spectral features
    importances = clf.feature_importances_
    spectral_splits = {name: int(importances[feature_names.index(name)]) for name in spectral_df.columns}
    print("\nSpectral SVD Feature Splits:")
    print(json.dumps(spectral_splits, indent=2))


if __name__ == "__main__":
    main()