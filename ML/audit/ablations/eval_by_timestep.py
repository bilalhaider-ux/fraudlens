"""
FraudLens - Per-Time-Step Diagnostic
=======================================
Breaks down test-set performance (time_step 35-49) by INDIVIDUAL time step,
for every model we've trained, to check for concept drift: does performance
fall off a cliff at some specific point in time, rather than degrading evenly?

This is the evidence-gathering step before committing to a drift-aware
model. Run this AFTER:
    python train_baseline.py
    python train_gnn.py --model gcn --epochs 150
    python train_gnn.py --model gat --epochs 150
    python train_hybrid.py --embeddings gcn
    python train_hybrid.py --embeddings gat

Outputs:
    outputs/per_timestep_breakdown.csv   - one row per (model, time_step)
    Prints a summary flagging the step where each model's F1 drops sharply.
"""
import os
import json

import joblib
import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from sklearn.metrics import f1_score, precision_score, recall_score

from data_loader import load_elliptic
from train_gnn import GCN, GAT

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "models")


def get_time_step_for_pyg(data):
    """The official PyG loader drops time_step from the final Data object in
    older code paths; data_loader._load_via_pyg() re-attaches it. This is a
    defensive re-check in case someone runs this against a data.pt cached
    before that fix - fail loudly rather than silently misaligning rows."""
    if not hasattr(data, "time_step"):
        raise AttributeError(
            "data.time_step missing. Delete data/elliptic_pyg/processed/ and "
            "re-run data_loader.py to force a fresh, time_step-aware load."
        )
    return data.time_step


def rf_scores(clf, X):
    return clf.predict_proba(X)[:, 1]


@torch.no_grad()
def gnn_scores(model, data):
    model.eval()
    out = model(data.x, data.edge_index)
    return F.softmax(out, dim=1)[:, 1].cpu().numpy()


def per_timestep_table(y_true, y_scores, time_steps, model_name, threshold=0.5):
    rows = []
    y_pred = (y_scores >= threshold).astype(int)
    for t in sorted(np.unique(time_steps)):
        mask = time_steps == t
        yt, yp, ys = y_true[mask], y_pred[mask], y_scores[mask]
        n_illicit = int(yt.sum())
        if n_illicit == 0:
            f1 = precision = recall = float("nan")
        else:
            f1 = f1_score(yt, yp, zero_division=0)
            precision = precision_score(yt, yp, zero_division=0)
            recall = recall_score(yt, yp, zero_division=0)
        rows.append({
            "model": model_name, "time_step": int(t), "n_nodes": int(mask.sum()),
            "n_illicit": n_illicit, "precision": precision, "recall": recall, "f1": f1,
        })
    return rows


def flag_cliff(df, model_name, drop_threshold=0.25):
    sub = df[df["model"] == model_name].sort_values("time_step")
    f1s = sub["f1"].values
    steps = sub["time_step"].values
    for i in range(1, len(f1s)):
        if np.isnan(f1s[i]) or np.isnan(f1s[i - 1]):
            continue
        if f1s[i - 1] - f1s[i] >= drop_threshold:
            print(f"  [{model_name}] F1 drop of {f1s[i-1]-f1s[i]:.2f} between "
                  f"time_step {steps[i-1]} (F1={f1s[i-1]:.2f}) and "
                  f"time_step {steps[i]} (F1={f1s[i]:.2f})")
            return int(steps[i])
    print(f"  [{model_name}] No single-step cliff >= {drop_threshold} found "
          f"(may still show gradual drift - check the CSV).")
    return None


def main():
    data = load_elliptic()
    time_steps = get_time_step_for_pyg(data).numpy()
    test_mask = data.test_mask.numpy()
    y = data.y.numpy()

    y_test = y[test_mask]
    ts_test = time_steps[test_mask]
    X_raw = data.x.numpy()

    all_rows = []

    # --- RF baseline ---
    baseline_path = os.path.join(MODEL_DIR, "baseline_rf.joblib")
    if os.path.exists(baseline_path):
        clf = joblib.load(baseline_path)
        scores = rf_scores(clf, X_raw[test_mask])
        all_rows += per_timestep_table(y_test, scores, ts_test, "baseline_rf")
    else:
        print("Skipping baseline_rf (models/baseline_rf.joblib not found - "
              "run train_baseline.py first)")

    # --- GCN / GAT ---
    in_channels = data.x.size(1)
    for model_type, cls, hidden in [("gcn", GCN, 64), ("gat", GAT, 16)]:
        model_path = os.path.join(MODEL_DIR, f"{model_type}.pt")
        if os.path.exists(model_path):
            if model_type == "gcn":
                model = cls(in_channels, hidden_channels=64)
            else:
                model = cls(in_channels, hidden_channels=16)
            model.load_state_dict(torch.load(model_path, map_location="cpu"))
            scores_full = gnn_scores(model, data)
            all_rows += per_timestep_table(y_test, scores_full[test_mask], ts_test, model_type)
        else:
            print(f"Skipping {model_type} (models/{model_type}.pt not found - "
                  f"run train_gnn.py --model {model_type} first)")

    # --- Hybrid models ---
    for emb_name in ["gcn", "gat"]:
        hybrid_path = os.path.join(MODEL_DIR, f"hybrid_{emb_name}_rf.joblib")
        emb_path = os.path.join(OUT_DIR, f"{emb_name}_embeddings.npy")
        if os.path.exists(hybrid_path) and os.path.exists(emb_path):
            clf = joblib.load(hybrid_path)
            embeddings = np.load(emb_path)
            X_hybrid = np.concatenate([X_raw, embeddings], axis=1)
            scores = rf_scores(clf, X_hybrid[test_mask])
            all_rows += per_timestep_table(y_test, scores, ts_test, f"hybrid_{emb_name}")
        else:
            print(f"Skipping hybrid_{emb_name} (missing model or embeddings - "
                  f"run train_hybrid.py --embeddings {emb_name} first)")

    if not all_rows:
        print("No trained models found. Run the training scripts first.")
        return

    df = pd.DataFrame(all_rows)
    os.makedirs(OUT_DIR, exist_ok=True)
    out_csv = os.path.join(OUT_DIR, "per_timestep_breakdown.csv")
    df.to_csv(out_csv, index=False)
    print(f"\nSaved -> {out_csv}\n")

    print(df.pivot(index="time_step", columns="model", values="f1").round(3).to_string())

    print("\n--- Cliff detection (F1 drop >= 0.25 between consecutive time steps) ---")
    for model_name in df["model"].unique():
        flag_cliff(df, model_name)


if __name__ == "__main__":
    main()
