"""
FraudLens - Sprint 2: Bayesian Prior Calibration & Dynamic Adaptation
=====================================================================
Adjusts prediction probabilities using unsupervised Bayesian log-odds
correction to counter the post-drift class prior collapse.
Zero test labels are accessed or leaked.
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
from scipy.special import expit, logit
from sklearn.metrics import average_precision_score, f1_score, precision_score, recall_score

from data_loader import load_elliptic, add_train_val_split
from train_prior_correction import best_f1_threshold

OUT_DIR = os.path.join(CURRENT_DIR, "..", "outputs")
MODEL_DIR = os.path.join(CURRENT_DIR, "..", "models")


def estimate_unsupervised_prior(scores_t, pi_0, shrinkage_k=500):
    """
    Estimates test timestep prior without labels using the mean score
    with Empirical Bayes shrinkage toward the source prior pi_0.
    """
    n_t = len(scores_t)
    raw_mean = float(np.mean(scores_t))
    # Empirical Bayes shrinkage: pulls small sample estimates back to pi_0
    shrunk_prior = (n_t * raw_mean + shrinkage_k * pi_0) / (n_t + shrinkage_k)
    return np.clip(shrunk_prior, 1e-4, 1 - 1e-4)


def bayesian_log_odds_adjustment(scores, pi_0, pi_t):
    """
    Shifts predicted probabilities using Bayes' rule under label-prior shift:
    logit(p_t) = logit(p_0) + log(pi_t / (1 - pi_t)) - log(pi_0 / (1 - pi_0))
    """
    eps = 1e-7
    s_clipped = np.clip(scores, eps, 1 - eps)
    log_odds_orig = logit(s_clipped)
    prior_shift = np.log(pi_t / (1 - pi_t)) - np.log(pi_0 / (1 - pi_0))
    return expit(log_odds_orig + prior_shift)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(MODEL_DIR, exist_ok=True)

    data = load_elliptic()
    data = add_train_val_split(data)

    clean_struct_path = os.path.join(OUT_DIR, "clean_structural_features.csv")
    anomaly_path = os.path.join(OUT_DIR, "unsupervised_anomaly_features.csv")

    clean_df = pd.read_csv(clean_struct_path)
    anomaly_df = pd.read_csv(anomaly_path)

    X_raw = data.x.numpy()
    X = np.concatenate([X_raw, clean_df.values, anomaly_df.values], axis=1)
    y = data.y.numpy()
    time_steps = data.time_step.numpy()

    train_mask = data.train_mask.numpy()
    val_mask = data.val_mask.numpy()
    test_mask = data.test_mask.numpy()

    pi_0 = float((y[train_mask] == 1).sum() / train_mask.sum())
    print(f"Source Training Illicit Prior (pi_0): {pi_0:.4f}")

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
    print(f"Validation-tuned threshold: {val_th:.3f} (Val F1: {val_f1:.4f})")

    y_test = y[test_mask]
    ts_test = time_steps[test_mask]
    s_test = clf.predict_proba(X[test_mask])[:, 1]

    # Evaluate across timesteps
    rows = []
    test_timesteps = sorted(np.unique(ts_test))

    all_pred_static = []
    all_pred_bayes = []
    all_pred_quantile = []

    for t in test_timesteps:
        m = ts_test == t
        yt = y_test[m]
        st = s_test[m]
        n_ill = int(yt.sum())

        # Unsupervised prior estimation for timestep t
        pi_t_hat = estimate_unsupervised_prior(st, pi_0)

        # 1. Static Threshold
        yp_static = (st >= val_th).astype(int)

        # 2. Bayesian Log-Odds Adjusted Probability
        st_bayes = bayesian_log_odds_adjustment(st, pi_0, pi_t_hat)
        # Decision boundary under calibrated probabilities (0.5 Bayes optimal)
        yp_bayes = (st_bayes >= 0.5).astype(int)

        # 3. Dynamic Quantile Matching (match top pi_t_hat fraction)
        q_th = np.percentile(st, 100 * (1 - pi_t_hat))
        yp_quant = (st >= q_th).astype(int)

        all_pred_static.extend(yp_static)
        all_pred_bayes.extend(yp_bayes)
        all_pred_quantile.extend(yp_quant)

        f1_static = f1_score(yt, yp_static, zero_division=0) if n_ill > 0 else float("nan")
        f1_bayes = f1_score(yt, yp_bayes, zero_division=0) if n_ill > 0 else float("nan")
        f1_quant = f1_score(yt, yp_quant, zero_division=0) if n_ill > 0 else float("nan")
        pr_auc = average_precision_score(yt, st) if n_ill > 0 else float("nan")

        rows.append({
            "timestep": int(t),
            "n_illicit": n_ill,
            "est_prior": round(float(pi_t_hat), 4),
            "pr_auc": round(float(pr_auc), 4),
            "f1_static": round(float(f1_static), 4),
            "f1_bayes": round(float(f1_bayes), 4),
            "f1_quantile": round(float(f1_quant), 4),
        })

    df_res = pd.DataFrame(rows)
    print("\n--- Per-Timestep Performance: Static vs. Bayesian vs. Quantile ---")
    print(df_res.to_string(index=False))

    post_mask = df_res["timestep"] >= 43
    print("\n--- Summary Performance Comparison ---")
    print(f"Overall Test Pooled F1 (Static):   {f1_score(y_test, all_pred_static, zero_division=0):.4f}")
    print(f"Overall Test Pooled F1 (Bayes):    {f1_score(y_test, all_pred_bayes, zero_division=0):.4f}")
    print(f"Overall Test Pooled F1 (Quantile): {f1_score(y_test, all_pred_quantile, zero_division=0):.4f}")
    print(f"Overall Test Macro F1 (Static):    {df_res['f1_static'].mean():.4f}")
    print(f"Overall Test Macro F1 (Bayes):     {df_res['f1_bayes'].mean():.4f}")
    print(f"Overall Test Macro F1 (Quantile):  {df_res['f1_quantile'].mean():.4f}")
    print(f"Post-Drift (43-49) Mean F1 (Static):   {df_res[post_mask]['f1_static'].mean():.4f}")
    print(f"Post-Drift (43-49) Mean F1 (Bayes):    {df_res[post_mask]['f1_bayes'].mean():.4f}")
    print(f"Post-Drift (43-49) Mean F1 (Quantile): {df_res[post_mask]['f1_quantile'].mean():.4f}")

    df_res.to_csv(os.path.join(OUT_DIR, "sprint2_prior_adaptation_metrics.csv"), index=False)


if __name__ == "__main__":
    main()