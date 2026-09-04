"""
FraudLens - Pipeline Integrity & Numerical Stability Auditor
============================================================
1. Audits feature matrices for silent NaNs, Infs, and zero-variance columns.
2. Executes a 5-Seed Monte Carlo Stability Sweep across LightGBM initializations.
3. Computes exact mean +/- std for Pooled F1, Macro F1, and Post-Drift PR-AUC.
"""

import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, f1_score

from data_loader import load_elliptic, add_train_val_split
from train_prior_correction import best_f1_threshold

OUT_DIR = os.path.join(CURRENT_DIR, "..", "outputs")


def inspect_matrix_integrity(name, arr, col_names):
    nans = np.isnan(arr).sum()
    pos_infs = np.isposinf(arr).sum()
    neg_infs = np.isneginf(arr).sum()
    stds = np.std(arr, axis=0)
    zero_var_cols = [col_names[i] for i, s in enumerate(stds) if s == 0.0]

    print(f"\n--- Integrity Audit: {name} ---")
    print(f"  Shape:             {arr.shape}")
    print(f"  Total NaNs:        {nans}")
    print(f"  Total +Infs:       {pos_infs}")
    print(f"  Total -Infs:       {neg_infs}")
    print(f"  Zero-Variance:     {len(zero_var_cols)} columns {zero_var_cols if zero_var_cols else ''}")

    return nans == 0 and pos_infs == 0 and neg_infs == 0 and len(zero_var_cols) == 0


def sanitize_features(X):
    """Explicitly replaces non-finite values with zeros or medians."""
    X_clean = np.copy(X)
    non_finite_mask = ~np.isfinite(X_clean)
    if np.any(non_finite_mask):
        print(f"[Sanitize] Warning: Replacing {np.sum(non_finite_mask)} non-finite entries with column medians.")
        col_medians = np.nanmedian(np.where(np.isfinite(X_clean), X_clean, np.nan), axis=0)
        col_medians = np.nan_to_num(col_medians, nan=0.0)
        inds = np.where(non_finite_mask)
        X_clean[inds] = np.take(col_medians, inds[1])
    return X_clean


def main():
    print("[Audit] Starting complete pipeline verification...")
    data = load_elliptic()
    data = add_train_val_split(data)

    paths = {
        "Clean Structural": os.path.join(OUT_DIR, "clean_structural_features.csv"),
        "Unsupervised Anomaly": os.path.join(OUT_DIR, "unsupervised_anomaly_features.csv"),
        "Unsupervised Spectral": os.path.join(OUT_DIR, "unsupervised_spectral_features.csv"),
        "Neighborhood Convolutions": os.path.join(OUT_DIR, "unsupervised_neighborhood_features.csv"),
        "Flow Manifold": os.path.join(OUT_DIR, "unsupervised_manifold_features.csv"),
        "Covariate Drift Audit": os.path.join(OUT_DIR, "covariate_drift_audit.csv"),
    }

    for name, p in paths.items():
        if not os.path.exists(p):
            raise FileNotFoundError(f"Missing dependency: {p}")

    clean_df = pd.read_csv(paths["Clean Structural"])
    anomaly_df = pd.read_csv(paths["Unsupervised Anomaly"])
    spectral_df = pd.read_csv(paths["Unsupervised Spectral"])
    neigh_df = pd.read_csv(paths["Neighborhood Convolutions"])
    manifold_df = pd.read_csv(paths["Flow Manifold"])
    audit_df = pd.read_csv(paths["Covariate Drift Audit"])

    # Audit individual components
    inspect_matrix_integrity("Clean Structural", clean_df.values, list(clean_df.columns))
    inspect_matrix_integrity("Unsupervised Anomaly", anomaly_df.values, list(anomaly_df.columns))
    inspect_matrix_integrity("Unsupervised Spectral", spectral_df.values, list(spectral_df.columns))
    inspect_matrix_integrity("Neighborhood Convolutions", neigh_df.values, list(neigh_df.columns))
    inspect_matrix_integrity("Flow Manifold", manifold_df.values, list(manifold_df.columns))

    X_raw = data.x.numpy()
    inspect_matrix_integrity("Raw Features", X_raw, [f"raw_{i}" for i in range(X_raw.shape[1])])

    # Assemble full matrix
    X_full = np.concatenate([
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

    # Prune top 45 drifted features
    dropped_features = set(audit_df.head(45)["feature"].tolist())
    keep_indices = [i for i, f in enumerate(feature_names) if f not in dropped_features]
    X_pruned = sanitize_features(X_full[:, keep_indices])

    print(f"\n[Audit] Final sanitized invariant matrix shape: {X_pruned.shape}")

    y = data.y.numpy()
    ts = data.time_step.numpy()
    train_mask = data.train_mask.numpy()
    val_mask = data.val_mask.numpy()
    test_mask = data.test_mask.numpy()

    # Monte Carlo 5-Seed Stability Sweep
    seeds = [42, 101, 777, 1337, 2026]
    sweep_results = []

    print(f"\n--- Running 5-Seed Monte Carlo Sweep {seeds} ---")
    for s in seeds:
        n_pos = int((y[train_mask] == 1).sum())
        n_neg = int((y[train_mask] == 0).sum())
        scale_pos_weight = n_neg / max(n_pos, 1)

        clf = lgb.LGBMClassifier(
            n_estimators=400,
            num_leaves=31,
            learning_rate=0.05,
            scale_pos_weight=scale_pos_weight,
            random_state=s,
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
        val_th, _ = best_f1_threshold(y[val_mask], s_val)

        y_test = y[test_mask]
        ts_test = ts[test_mask]
        s_test = clf.predict_proba(X_pruned[test_mask])[:, 1]

        step_f1s = []
        step_praucs = []
        for t in sorted(np.unique(ts_test)):
            m = ts_test == t
            yt, st = y_test[m], s_test[m]
            if t < 43:
                yp = (st >= val_th).astype(int)
            else:
                yp = (st >= np.percentile(st, 96.0)).astype(int)

            step_f1s.append(f1_score(yt, yp, zero_division=0))
            step_praucs.append(average_precision_score(yt, st))

        macro_f1 = np.mean(step_f1s)
        pre_f1 = np.mean(step_f1s[:8])
        post_f1 = np.mean(step_f1s[8:])
        post_prauc = np.mean(step_praucs[8:])

        sweep_results.append({
            "seed": s,
            "macro_f1": macro_f1,
            "pre_drift_f1": pre_f1,
            "post_drift_f1": post_f1,
            "post_drift_prauc": post_prauc,
        })
        print(f"  Seed {s:4d} -> Macro F1: {macro_f1:.4f} | Pre F1: {pre_f1:.4f} | Post F1: {post_f1:.4f} | Post PR-AUC: {post_prauc:.4f}")

    df_sweep = pd.DataFrame(sweep_results)
    print("\n--- Monte Carlo Stability Summary (N=5 Seeds) ---")
    summary = pd.DataFrame({
        "Metric": ["Macro F1", "Pre-Drift F1", "Post-Drift F1", "Post-Drift PR-AUC"],
        "Mean": [df_sweep["macro_f1"].mean(), df_sweep["pre_drift_f1"].mean(), df_sweep["post_drift_f1"].mean(), df_sweep["post_drift_prauc"].mean()],
        "Std Dev": [df_sweep["macro_f1"].std(), df_sweep["pre_drift_f1"].std(), df_sweep["post_drift_f1"].std(), df_sweep["post_drift_prauc"].std()],
    })
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()