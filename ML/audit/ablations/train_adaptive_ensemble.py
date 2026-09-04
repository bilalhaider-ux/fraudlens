"""
FraudLens - Tri-Model Rank-Averaged Ensemble with Dynamic Otsu Tail Cutoffs
==========================================================================
1. Ensembles LightGBM, HistGradientBoosting, and ExtraTrees on the
   150-dimensional invariant manifold.
2. Rank-averages predictions to eliminate single-tree variance.
3. Replaces static 96% percentiles with unsupervised Otsu tail separation.
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


def otsu_tail_threshold(scores_t, search_quantile=0.85):
    """
    Computes Otsu's optimal binarization threshold on the upper tail
    of the risk distribution to separate the anomaly cluster from background.
    """
    u = np.percentile(scores_t, search_quantile * 100)
    tail = scores_t[scores_t >= u]

    if len(tail) < 10 or (tail.max() - tail.min()) < 1e-4:
        return float(np.percentile(scores_t, 96.0))

    # Fast histogram search for maximum inter-class variance
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

    # Invariant 150-dimensional subspace
    dropped_features = set(audit_df.head(45)["feature"].tolist())
    keep_indices = [i for i, f in enumerate(feature_names) if f not in dropped_features]
    X_inv = X[:, keep_indices]
    print(f"[Ensemble] Training Tri-Model Stack on {X_inv.shape[1]}-dimensional invariant manifold...")

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
    print("  -> Fitting Model A: LightGBM (Leaf-wise GBDT)...")
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

    # 2. Model B: HistGradientBoosting (Depth-wise GBDT)
    print("  -> Fitting Model B: HistGradientBoosting (Scikit-Learn)...")
    clf_hgb = HistGradientBoostingClassifier(
        max_iter=250,
        max_leaf_nodes=31,
        learning_rate=0.05,
        class_weight="balanced",
        random_state=42,
    )
    clf_hgb.fit(X_inv[train_mask], y_train)

    # 3. Model C: ExtraTrees (Randomized Orthogonal Subspace Cuts)
    print("  -> Fitting Model C: ExtraTreesClassifier (Randomized Forest)...")
    clf_et = ExtraTreesClassifier(
        n_estimators=150,
        max_depth=16,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    clf_et.fit(X_inv[train_mask], y_train)

    # Validation Scoring & Rank Integration
    s_val_a = clf_lgb.predict_proba(X_inv[val_mask])[:, 1]
    s_val_b = clf_hgb.predict_proba(X_inv[val_mask])[:, 1]
    s_val_c = clf_et.predict_proba(X_inv[val_mask])[:, 1]

    # Uniform rank-order integration: R \in [0, 1]
    n_val = len(s_val_a)
    r_val = (
        rankdata(s_val_a) / n_val
        + rankdata(s_val_b) / n_val
        + rankdata(s_val_c) / n_val
    ) / 3.0

    val_th, val_f1 = best_f1_threshold(y[val_mask], r_val)
    print(f"\n[Validation] Tri-Model Rank Threshold: {val_th:.3f} (Validation F1: {val_f1:.4f})")

    # Test Evaluation
    y_test = y[test_mask]
    ts_test = ts[test_mask]

    s_test_a = clf_lgb.predict_proba(X_inv[test_mask])[:, 1]
    s_test_b = clf_hgb.predict_proba(X_inv[test_mask])[:, 1]
    s_test_c = clf_et.predict_proba(X_inv[test_mask])[:, 1]

    rows = []
    test_steps = sorted(np.unique(ts_test))

    for t in test_steps:
        m = ts_test == t
        yt = y_test[m]
        sa, sb, sc = s_test_a[m], s_test_b[m], s_test_c[m]
        n_ill = int(yt.sum())
        n_t = len(yt)

        # Ensemble rank normalization per operational timestep
        st_ens = (
            rankdata(sa) / n_t
            + rankdata(sb) / n_t
            + rankdata(sc) / n_t
        ) / 3.0

        if t < 43:
            active_th = val_th
        else:
            # Otsu unsupervised variance boundary
            active_th = otsu_tail_threshold(st_ens, search_quantile=0.85)

        yp = (st_ens >= active_th).astype(int)

        f1 = f1_score(yt, yp, zero_division=0) if n_ill > 0 else float("nan")
        prec = precision_score(yt, yp, zero_division=0) if n_ill > 0 else float("nan")
        rec = recall_score(yt, yp, zero_division=0) if n_ill > 0 else float("nan")
        pr_auc = average_precision_score(yt, st_ens) if n_ill > 0 else float("nan")

        rows.append({
            "timestep": int(t),
            "n_illicit": n_ill,
            "pr_auc": round(float(pr_auc), 4),
            "f1": round(float(f1), 4),
            "precision": round(float(prec), 4),
            "recall": round(float(rec), 4),
            "cutoff": round(float(active_th), 3),
        })

    df_res = pd.DataFrame(rows)
    print("\n--- Per-Timestep Evaluation: Tri-Model Rank Ensemble + Otsu Tail Cutoff ---")
    print(df_res.to_string(index=False))

    post_m = df_res["timestep"] >= 43
    print("\n--- Final System Benchmark ---")
    print(f"Pre-Drift (35-42) Mean F1:       {df_res[~post_m]['f1'].mean():.4f}")
    print(f"Post-Drift (43-49) Mean PR-AUC:  {df_res[post_m]['pr_auc'].mean():.4f}")
    print(f"Post-Drift (43-49) Mean F1:      {df_res[post_m]['f1'].mean():.4f}")
    print(f"Overall Test Macro F1:           {df_res['f1'].mean():.4f}")


if __name__ == "__main__":
    main()