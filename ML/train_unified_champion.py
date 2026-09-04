"""
FraudLens - Unified Champion Dual-Regime Pipeline
=================================================
Combines Tri-Model Rank Stacking with Regime-Aware Thresholding:
  - Pre-Drift (t < 43): High-precision threshold tuned on validation probabilities.
  - Post-Drift (t >= 43): Otsu adaptive tail binarization on ensemble rank space.
"""

import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.stats import rankdata
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score, f1_score, precision_score, recall_score

from data_loader import load_elliptic, add_train_val_split
from train_prior_correction import best_f1_threshold

OUT_DIR = os.path.join(CURRENT_DIR, "..", "outputs")


def otsu_tail_threshold(scores_t, search_quantile=0.80):
    u = np.percentile(scores_t, search_quantile * 100)
    tail = scores_t[scores_t >= u]

    if len(tail) < 10 or (tail.max() - tail.min()) < 1e-4:
        return float(np.percentile(scores_t, 95.0))

    hist, bin_edges = np.histogram(tail, bins=30)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2.0

    weight1 = np.cumsum(hist)
    weight2 = np.cumsum(hist[::-1])[::-1]

    mean1 = np.cumsum(hist * bin_centers) / np.maximum(weight1, 1)
    mean2 = (np.cumsum((hist * bin_centers)[::-1]) / np.maximum(weight2, 1))[::-1]

    variance = weight1[:-1] * weight2[1:] * (mean1[:-1] - mean2[1:]) ** 2
    idx_max = np.argmax(variance)

    return float(bin_centers[idx_max])


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

    dropped_features = set(audit_df.head(45)["feature"].tolist())
    keep_indices = [i for i, f in enumerate(feature_names) if f not in dropped_features]
    X_inv = X[:, keep_indices]
    print(f"[Champion] Training on {X_inv.shape[1]}-dimensional Invariant Manifold...")

    y = data.y.numpy()
    ts = data.time_step.numpy()
    train_mask = data.train_mask.numpy()
    val_mask = data.val_mask.numpy()
    test_mask = data.test_mask.numpy()

    y_train = y[train_mask]
    n_pos = int((y_train == 1).sum())
    n_neg = int((y_train == 0).sum())
    pos_weight = n_neg / max(n_pos, 1)

    # 1. Model A: LightGBM
    clf_lgb = lgb.LGBMClassifier(
        n_estimators=400,
        num_leaves=31,
        learning_rate=0.05,
        scale_pos_weight=pos_weight,
        random_state=42,
        verbosity=-1,
        n_jobs=-1,
    )
    clf_lgb.fit(
        X_inv[train_mask],
        y_train,
        eval_set=[(X_inv[val_mask], y[val_mask])],
        callbacks=[lgb.early_stopping(30, verbose=False)],
    )

    # 2. Model B: HistGradientBoosting
    clf_hgb = HistGradientBoostingClassifier(
        max_iter=250,
        max_leaf_nodes=31,
        learning_rate=0.05,
        class_weight="balanced",
        random_state=42,
    )
    clf_hgb.fit(X_inv[train_mask], y_train)

    # 3. Model C: ExtraTrees
    clf_et = ExtraTreesClassifier(
        n_estimators=150,
        max_depth=16,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    clf_et.fit(X_inv[train_mask], y_train)

    # Validation tuning on raw ensemble average probabilities for pre-drift
    p_val = (
        clf_lgb.predict_proba(X_inv[val_mask])[:, 1]
        + clf_hgb.predict_proba(X_inv[val_mask])[:, 1]
        + clf_et.predict_proba(X_inv[val_mask])[:, 1]
    ) / 3.0
    val_th, val_f1 = best_f1_threshold(y[val_mask], p_val)
    print(f"[Validation] Pre-Drift High-Precision Threshold: {val_th:.3f} (Val F1: {val_f1:.4f})")

    # Test scoring
    y_test = y[test_mask]
    ts_test = ts[test_mask]

    p_test_a = clf_lgb.predict_proba(X_inv[test_mask])[:, 1]
    p_test_b = clf_hgb.predict_proba(X_inv[test_mask])[:, 1]
    p_test_c = clf_et.predict_proba(X_inv[test_mask])[:, 1]

    rows = []
    test_steps = sorted(np.unique(ts_test))

    for t in test_steps:
        m = ts_test == t
        yt = y_test[m]
        n_ill = int(yt.sum())
        n_t = len(yt)

        pa, pb, pc = p_test_a[m], p_test_b[m], p_test_c[m]
        p_avg = (pa + pb + pc) / 3.0

        st_ens = (
            rankdata(pa) / n_t
            + rankdata(pb) / n_t
            + rankdata(pc) / n_t
        ) / 3.0

        if t < 43:
            # Pre-drift nominal: use high-precision probability threshold
            yp = (p_avg >= val_th).astype(int)
            pr_auc = average_precision_score(yt, p_avg)
            cutoff_val = val_th
            mode = "Nominal Probability"
        else:
            # Post-drift drifted: use Otsu tail binarization on rank space
            cutoff_val = otsu_tail_threshold(st_ens, search_quantile=0.80)
            yp = (st_ens >= cutoff_val).astype(int)
            pr_auc = average_precision_score(yt, st_ens)
            mode = "Otsu Tail Rank"

        f1 = f1_score(yt, yp, zero_division=0) if n_ill > 0 else float("nan")
        prec = precision_score(yt, yp, zero_division=0) if n_ill > 0 else float("nan")
        rec = recall_score(yt, yp, zero_division=0) if n_ill > 0 else float("nan")

        rows.append({
            "timestep": int(t),
            "n_illicit": n_ill,
            "mode": mode,
            "pr_auc": round(float(pr_auc), 4),
            "f1": round(float(f1), 4),
            "precision": round(float(prec), 4),
            "recall": round(float(rec), 4),
            "cutoff": round(float(cutoff_val), 3),
        })

    df_res = pd.DataFrame(rows)
    print("\n--- Per-Timestep Performance: Unified Champion Pipeline ---")
    print(df_res.to_string(index=False))

    post_m = df_res["timestep"] >= 43
    print("\n--- Final System Benchmark ---")
    print(f"Pre-Drift (35-42) Mean F1:       {df_res[~post_m]['f1'].mean():.4f}")
    print(f"Post-Drift (43-49) Mean PR-AUC:  {df_res[post_m]['pr_auc'].mean():.4f}")
    print(f"Post-Drift (43-49) Mean F1:      {df_res[post_m]['f1'].mean():.4f}")
    print(f"Overall Test Macro F1:           {df_res['f1'].mean():.4f}")


if __name__ == "__main__":
    main()