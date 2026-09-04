"""
FraudLens - STRICT Zero-Test-Knowledge Feature Evaluation
==============================================================
Direct empirical test of the critique that community_guilt_density,
ppr_illicit, and GuiltyWalker's walk-target search all use OTHER
test-period nodes' true labels (not just the node's own) - a real gap
between "self-excluded" and genuinely "zero test-period label knowledge."

This rebuilds BOTH feature sets using ONLY time_step<35 (train-period)
known-illicit nodes as the reference set for "known illicit" - no
test-period node, self or otherwise, can ever contribute to ANY other
node's feature. This is the same zero-knowledge standard the baseline
RF/GCN/GAT results are already held to.

IMPORTANT STRUCTURAL CAVEAT TO WATCH FOR: this dataset's edges NEVER cross
time steps (each time step is its own disconnected subgraph). That means a
TEST-period node's backward walk / PPR / community can ONLY ever reach
OTHER TEST-period nodes in the same subgraph - it is structurally
IMPOSSIBLE for a test-period node to reach a train-period node at all. If
that's true, restricting the reference set to train-only will make these
features completely UNINFORMATIVE (constant fill values) for the entire
test set, not just weaker - this script will reveal whether that's exactly
what happens.
"""
import json
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score, precision_score, recall_score

from data_loader import load_elliptic, add_train_val_split
from guilty_walker import compute_guiltywalker_features
from structural_features import compute_structural_features
from train_prior_correction import best_f1_threshold

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "models")


def per_timestep_f1(y_true, y_pred, time_steps):
    rows = []
    for t in sorted(np.unique(time_steps)):
        mask = time_steps == t
        yt, yp = y_true[mask], y_pred[mask]
        f1 = f1_score(yt, yp, zero_division=0) if yt.sum() > 0 else float("nan")
        rows.append({"time_step": int(t), "n_illicit": int(yt.sum()), "f1": f1})
    return pd.DataFrame(rows)


def main(cache=True):
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(MODEL_DIR, exist_ok=True)
    data = load_elliptic()
    data = add_train_val_split(data)

    n_nodes = data.num_nodes
    edge_index = data.edge_index.numpy()
    y = data.y.numpy()
    time_steps = data.time_step.numpy()

    # STRICT reference: only nodes with time_step < 35 (the paper's original
    # train region) may ever be used as a "known illicit" reference for ANY
    # other node's feature - not even other test-period nodes.
    train_region_mask = time_steps < 35
    reference_mask = train_region_mask & (y == 1)
    print(f"Strict reference set: {reference_mask.sum()} illicit nodes, "
          f"ALL from time_step < 35. Zero test-period nodes included.")

    gwf_cache = os.path.join(OUT_DIR, "strict_guiltywalker_features.csv")
    if cache and os.path.exists(gwf_cache):
        print(f"Loading cached strict GuiltyWalker features from {gwf_cache}")
        gwf_df = pd.read_csv(gwf_cache)
    else:
        gwf_df = compute_guiltywalker_features(
            edge_index, y, n_nodes, k_walks=30, max_attempts_per_node=120,
            max_walk_steps=60, reference_illicit_mask=reference_mask,
        )
        gwf_df.to_csv(gwf_cache, index=False)

    struct_cache = os.path.join(OUT_DIR, "strict_structural_features.csv")
    if cache and os.path.exists(struct_cache):
        print(f"Loading cached strict structural features from {struct_cache}")
        struct_df = pd.read_csv(struct_cache)
    else:
        struct_df = compute_structural_features(
            edge_index, y, time_steps, n_nodes, reference_illicit_mask=reference_mask,
        )
        struct_df.to_csv(struct_cache, index=False)

    # --- Sanity check: are these features actually non-constant on the test set? ---
    test_mask = data.test_mask.numpy()
    print("\n--- Sanity check: feature variance on TEST set only ---")
    for name, df in [("GuiltyWalker", gwf_df), ("Structural", struct_df)]:
        test_std = df.values[test_mask].std(axis=0)
        n_constant = int((test_std < 1e-9).sum())
        print(f"{name}: {n_constant}/{df.shape[1]} columns are CONSTANT "
              f"(zero variance) on the test set")
        if n_constant == df.shape[1]:
            print(f"  -> {name} carries ZERO information for test-period nodes "
                  f"under strict train-only reference. This would CONFIRM the "
                  f"structural caveat above: these graph-local features cannot "
                  f"see across the train/test boundary at all, by construction "
                  f"of this dataset (no cross-time-step edges).")

    X_raw = data.x.numpy()
    X_full = np.concatenate([X_raw, gwf_df.values, struct_df.values], axis=1)
    print(f"\nRaw: {X_raw.shape[1]}, strict GWF: {gwf_df.shape[1]}, "
          f"strict Structural: {struct_df.shape[1]}, combined (with constants): {X_full.shape[1]}")

    # Drop any column that's constant on the TEST set - these can't just be
    # "ignored" by a tree model; a feature that varied during training and
    # then becomes a single identical constant for 100% of test examples can
    # actively mislead a trained model (routes every test example down
    # whatever branch that fill value happened to land in during training),
    # which is a plausible explanation for scores WORSE than a raw-only
    # baseline, not just "no extra help."
    combined_df = pd.concat([pd.DataFrame(gwf_df.values, columns=gwf_df.columns),
                              pd.DataFrame(struct_df.values, columns=struct_df.columns)], axis=1)
    test_std = combined_df.values[test_mask].std(axis=0)
    keep_cols = test_std > 1e-9
    dropped_cols = combined_df.columns[~keep_cols].tolist()
    print(f"Dropping {len(dropped_cols)} test-constant columns: {dropped_cols}")

    X = np.concatenate([X_raw, combined_df.values[:, keep_cols]], axis=1)
    print(f"Combined (test-constant columns dropped): {X.shape[1]}")

    train_mask = data.train_mask.numpy()
    val_mask = data.val_mask.numpy()

    clf = RandomForestClassifier(
        n_estimators=200, max_depth=None,
        class_weight="balanced_subsample", n_jobs=-1, random_state=42,
    )
    clf.fit(X[train_mask], y[train_mask])

    y_val, s_val = y[val_mask], clf.predict_proba(X[val_mask])[:, 1]
    val_threshold, val_f1 = best_f1_threshold(y_val, s_val)
    print(f"Validation-tuned threshold: {val_threshold:.3f} (val F1: {val_f1:.4f})")

    y_test = y[test_mask]
    s_test = clf.predict_proba(X[test_mask])[:, 1]
    ts_test = time_steps[test_mask]
    y_pred = (s_test >= val_threshold).astype(int)

    overall_f1 = f1_score(y_test, y_pred)
    print(json.dumps({
        "model": "RF, STRICT train-only reference (raw + strict GWF + strict structural)",
        "val_threshold": round(float(val_threshold), 4),
        "overall_f1": round(float(overall_f1), 4),
    }, indent=2))

    pt_df = per_timestep_f1(y_test, y_pred, ts_test)
    print("\n--- Per-time-step F1 (STRICT, train-only reference) ---")
    print(pt_df.to_string(index=False))

    drift_step = 43
    post = pt_df[pt_df["time_step"] >= drift_step]["f1"].mean()
    print(f"\nMean F1, steps >= {drift_step} (STRICT): {post:.4f}")
    print("For reference: raw-only RF baseline was 0.086, "
          "non-strict GuiltyWalker+structural (uses test-period other-node "
          "labels) was 0.742")

    with open(os.path.join(OUT_DIR, "strict_summary.json"), "w") as f:
        json.dump({"mean_f1_post_drift_strict": round(float(post), 4)}, f, indent=2)


if __name__ == "__main__":
    main()