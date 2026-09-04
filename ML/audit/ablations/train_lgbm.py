"""
FraudLens - LightGBM on the Verified Feature Set (Ablation-Enabled)
==================================================================
Supports command-line ablation of specific feature columns or feature sets
to isolate data leakage and verify feature attribution.
"""

import argparse
import json
import os
import sys

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, precision_score, recall_score

from data_loader import load_elliptic, add_train_val_split
from train_prior_correction import best_f1_threshold

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "models")


def parse_args():
    parser = argparse.ArgumentParser(description="Train LightGBM on Elliptic graph features.")
    parser.add_argument(
        "--drop",
        nargs="+",
        default=[],
        help="Space-separated list of individual feature names to exclude from training.",
    )
    parser.add_argument(
        "--drop-gw",
        action="store_true",
        help="Exclude all GuiltyWalker features.",
    )
    parser.add_argument(
        "--drop-structural",
        action="store_true",
        help="Exclude all structural features.",
    )
    return parser.parse_args()


def per_timestep_f1(y_true, y_pred, time_steps):
    rows = []
    for t in sorted(np.unique(time_steps)):
        mask = time_steps == t
        yt, yp = y_true[mask], y_pred[mask]
        f1 = f1_score(yt, yp, zero_division=0) if yt.sum() > 0 else float("nan")
        prec = precision_score(yt, yp, zero_division=0) if yt.sum() > 0 else float("nan")
        rec = recall_score(yt, yp, zero_division=0) if yt.sum() > 0 else float("nan")
        rows.append({
            "time_step": int(t),
            "n_illicit": int(yt.sum()),
            "precision": prec,
            "recall": rec,
            "f1": f1,
        })
    return pd.DataFrame(rows)


def main():
    args = parse_args()
    os.makedirs(MODEL_DIR, exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)

    data = load_elliptic()
    data = add_train_val_split(data)

    gwf_path = os.path.join(OUT_DIR, "guiltywalker_features.csv")
    struct_path = os.path.join(OUT_DIR, "structural_features.csv")

    feature_blocks = []
    feature_names = []

    X_raw = data.x.numpy()
    feature_blocks.append(X_raw)
    raw_names = [f"raw_{i}" for i in range(X_raw.shape[1])]
    feature_names.extend(raw_names)
    print(f"Raw features loaded: {X_raw.shape[1]}")

    if not args.drop_gw:
        if not os.path.exists(gwf_path):
            raise FileNotFoundError(f"{gwf_path} not found - run train_baseline_guiltywalker.py first")
        gwf_df = pd.read_csv(gwf_path)
        feature_blocks.append(gwf_df.values)
        feature_names.extend(list(gwf_df.columns))
        print(f"GuiltyWalker features loaded: {gwf_df.shape[1]}")
    else:
        print("GuiltyWalker features completely excluded by --drop-gw flag.")

    if not args.drop_structural:
        if not os.path.exists(struct_path):
            raise FileNotFoundError(f"{struct_path} not found - run train_structural.py first")
        struct_df = pd.read_csv(struct_path)
        feature_blocks.append(struct_df.values)
        feature_names.extend(list(struct_df.columns))
        print(f"Structural features loaded: {struct_df.shape[1]}")
    else:
        print("Structural features completely excluded by --drop-structural flag.")

    X_full = np.concatenate(feature_blocks, axis=1)
    df_features = pd.DataFrame(X_full, columns=feature_names)

    if args.drop:
        missing_drops = [f for f in args.drop if f not in df_features.columns]
        if missing_drops:
            print(f"WARNING: The following requested drop features were not found: {missing_drops}")
        valid_drops = [f for f in args.drop if f in df_features.columns]
        if valid_drops:
            print(f"Ablating features: {valid_drops}")
            df_features.drop(columns=valid_drops, inplace=True)

    final_feature_names = list(df_features.columns)
    X = df_features.values
    print(f"Total features entering model: {X.shape[1]}")

    y = data.y.numpy()
    time_steps = data.time_step.numpy()
    train_mask = data.train_mask.numpy()
    val_mask = data.val_mask.numpy()
    test_mask = data.test_mask.numpy()

    n_pos = int((y[train_mask] == 1).sum())
    n_neg = int((y[train_mask] == 0).sum())
    scale_pos_weight = n_neg / max(n_pos, 1)
    print(f"scale_pos_weight: {scale_pos_weight:.2f}")

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

    y_val = y[val_mask]
    s_val = clf.predict_proba(X[val_mask])[:, 1]
    val_threshold, val_f1 = best_f1_threshold(y_val, s_val)
    print(f"Validation-tuned threshold: {val_threshold:.3f} (val F1: {val_f1:.4f})")

    y_test = y[test_mask]
    s_test = clf.predict_proba(X[test_mask])[:, 1]
    ts_test = time_steps[test_mask]
    y_pred = (s_test >= val_threshold).astype(int)

    metrics = {
        "model": "LightGBM (Ablated Evaluation)",
        "val_threshold": round(float(val_threshold), 4),
        "overall_f1": round(float(f1_score(y_test, y_pred, zero_division=0)), 4),
        "overall_precision": round(float(precision_score(y_test, y_pred, zero_division=0)), 4),
        "overall_recall": round(float(recall_score(y_test, y_pred, zero_division=0)), 4),
        "best_iteration": int(clf.best_iteration_ if clf.best_iteration_ is not None else -1),
    }
    print(json.dumps(metrics, indent=2))

    with open(os.path.join(OUT_DIR, "lgbm_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)
    joblib.dump(clf, os.path.join(MODEL_DIR, "lgbm.joblib"))

    pt_df = per_timestep_f1(y_test, y_pred, ts_test)
    pt_df.to_csv(os.path.join(OUT_DIR, "lgbm_per_timestep.csv"), index=False)
    print("\n--- Per-time-step Performance ---")
    print(pt_df.to_string(index=False))

    drift_step = 43
    post = pt_df[pt_df["time_step"] >= drift_step]["f1"].mean()
    print(f"\nMean F1, steps >= {drift_step}: {post:.4f}")

    importances = clf.feature_importances_
    top_idx = np.argsort(importances)[::-1][:15]
    top_features = {final_feature_names[i]: int(importances[i]) for i in top_idx}
    print("\nTop 15 features by importance (LightGBM):")
    print(json.dumps(top_features, indent=2))


if __name__ == "__main__":
    main()