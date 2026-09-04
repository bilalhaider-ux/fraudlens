"""
FraudLens - Sprint 3: Self-Contained TreeSHAP Feature Attribution Exporter
==========================================================================
Fits the 177-feature clean anomaly model, updates models/lgbm.joblib,
synchronizes outputs/ui_data/alerts.json, and exports exact local TreeSHAP
attributions for Screen 3 (Node Explainability).
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
import shap

from data_loader import load_elliptic, add_train_val_split

OUT_DIR = os.path.join(CURRENT_DIR, "..", "outputs")
UI_DIR = os.path.join(OUT_DIR, "ui_data")
MODEL_DIR = os.path.join(CURRENT_DIR, "..", "models")
MODEL_PATH = os.path.join(MODEL_DIR, "lgbm.joblib")


def main():
    os.makedirs(UI_DIR, exist_ok=True)
    os.makedirs(MODEL_DIR, exist_ok=True)
    print("[SHAP] Loading dataset and feature dependencies...")

    data = load_elliptic()
    data = add_train_val_split(data)

    clean_struct_path = os.path.join(OUT_DIR, "clean_structural_features.csv")
    anomaly_path = os.path.join(OUT_DIR, "unsupervised_anomaly_features.csv")

    for p in [clean_struct_path, anomaly_path]:
        if not os.path.exists(p):
            raise FileNotFoundError(f"Missing {p}. Ensure clean_structural_features.py and anomaly_features.py were run.")

    clean_df = pd.read_csv(clean_struct_path)
    anomaly_df = pd.read_csv(anomaly_path)

    X_raw = data.x.numpy()
    X = np.concatenate([X_raw, clean_df.values, anomaly_df.values], axis=1)
    feature_names = (
        [f"raw_{i}" for i in range(X_raw.shape[1])]
        + list(clean_df.columns)
        + list(anomaly_df.columns)
    )

    y = data.y.numpy()
    ts = data.time_step.numpy()
    train_mask = data.train_mask.numpy()
    val_mask = data.val_mask.numpy()
    test_mask = data.test_mask.numpy()

    print(f"[SHAP] Synchronizing production model with all {X.shape[1]} features...")
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

    # Save the synchronized 177-feature model artifact
    joblib.dump(clf, MODEL_PATH)
    print(f"[SHAP] Saved synchronized 177-feature model to {MODEL_PATH}")

    # Synchronize alerts.json to match the 177-feature predictions
    test_indices = np.where(test_mask)[0]
    scores = clf.predict_proba(X)[:, 1]
    test_scores = scores[test_indices]

    top_k_rel = np.argsort(test_scores)[::-1][:50]
    top_global_ids = test_indices[top_k_rel]

    alerts = []
    for idx, g_idx in enumerate(top_global_ids):
        alerts.append({
            "node_id": int(g_idx),
            "timestep": int(ts[g_idx]),
            "risk_score": round(float(test_scores[top_k_rel[idx]]), 4),
            "true_label": int(y[g_idx]),
        })

    with open(os.path.join(UI_DIR, "alerts.json"), "w") as f:
        json.dump(alerts, f, indent=2)
    print("  -> Synchronized outputs/ui_data/alerts.json with top 50 alerts")

    # Compute TreeSHAP values for prioritized alerts
    print(f"[SHAP] Computing TreeSHAP values for {len(top_global_ids)} prioritized alerts...")
    X_target = X[top_global_ids]

    explainer = shap.TreeExplainer(clf)
    shap_raw = explainer.shap_values(X_target)

    # Handle shape variations across SHAP versions
    if isinstance(shap_raw, list):
        vals = shap_raw[1] if len(shap_raw) > 1 else shap_raw[0]
    elif hasattr(shap_raw, "values"):
        vals = shap_raw.values
    else:
        vals = shap_raw

    exp_val = explainer.expected_value
    if isinstance(exp_val, (list, np.ndarray)):
        base_val = float(exp_val[1] if len(exp_val) > 1 else exp_val[0])
    else:
        base_val = float(exp_val)

    explanations = {}
    for idx, node_id in enumerate(top_global_ids):
        node_shap = vals[idx]
        node_feat_vals = X_target[idx]

        sorted_indices = np.argsort(np.abs(node_shap))[::-1]

        top_drivers = []
        for f_idx in sorted_indices[:8]:
            attr_val = float(node_shap[f_idx])
            raw_val = float(node_feat_vals[f_idx])
            name = feature_names[f_idx]

            top_drivers.append({
                "feature": name,
                "shap_value": round(attr_val, 4),
                "feature_value": round(raw_val, 4),
                "impact": "increases_risk" if attr_val > 0 else "decreases_risk",
            })

        explanations[str(node_id)] = {
            "node_id": int(node_id),
            "base_value": round(base_val, 4),
            "top_drivers": top_drivers,
        }

    out_file = os.path.join(UI_DIR, "node_explanations.json")
    with open(out_file, "w") as f:
        json.dump(explanations, f, indent=2)

    print(f"[SHAP] Successfully exported explanations for {len(explanations)} nodes -> {out_file}")


if __name__ == "__main__":
    main()