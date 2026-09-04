"""
FraudLens - Walk-Forward Adaptive Retraining
================================================
Motivation (confirmed empirically via eval_by_timestep.py): EVERY model we
trained - baseline RF, GCN, GAT, both hybrids - collapses to near-zero F1
starting at time_step 43, simultaneously. This is a real concept-drift event:
the post-43 regime is a pattern none of our models have ever seen a single
labeled example of, because training data only covers time_step 1-34.

This script simulates a realistic production scenario: as each time_step in
the test period (35-49) elapses, its TRUE labels become available (an
investigator eventually confirms flagged transactions), and the model
retrains on all labels seen so far before scoring the NEXT time_step. This
is standard "walk-forward" evaluation, used in quant finance for exactly
this reason - it directly measures adaptation speed, not just static accuracy.

Compares:
  - STATIC:  one RF trained once on time_step 1-34, never updated (= the
             existing baseline_rf, re-derived here per-step for a clean
             side-by-side comparison)
  - ADAPTIVE: RF retrained fresh at every test time_step on ALL labels with
             time_step < current_step (expanding window)

Output: outputs/walkforward_comparison.csv + a recovery-speed summary.
"""
import os
import json

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score, precision_score, recall_score

from data_loader import load_elliptic

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs")


def fit_rf(X, y, sample_weight=None):
    clf = RandomForestClassifier(
        n_estimators=200, max_depth=None,
        class_weight="balanced_subsample", n_jobs=-1, random_state=42,
    )
    clf.fit(X, y, sample_weight=sample_weight)
    return clf


def recency_weights(label_time_steps, current_step, half_life=5.0):
    """Exponential recency weighting: a label half_life steps old counts for
    half as much as a label from the current step. Lets a handful of FRESH
    post-drift labels actually move the model, instead of being numerically
    drowned out by thousands of accumulated old-regime labels."""
    age = current_step - label_time_steps
    age = np.clip(age, 0, None)
    decay_rate = np.log(2) / half_life
    return np.exp(-decay_rate * age)


def step_metrics(y_true, y_pred):
    if y_true.sum() == 0:
        return float("nan"), float("nan"), float("nan")
    f1 = f1_score(y_true, y_pred, zero_division=0)
    p = precision_score(y_true, y_pred, zero_division=0)
    r = recall_score(y_true, y_pred, zero_division=0)
    return f1, p, r


def main():
    data = load_elliptic()
    X = data.x.numpy()
    y = data.y.numpy()
    time_steps = data.time_step.numpy()
    labeled = y != 2

    test_steps = sorted(np.unique(time_steps[labeled & data.test_mask.numpy()]))
    print(f"Test time steps: {test_steps}")

    # --- STATIC model: trained once on original train region, never updated ---
    static_train_mask = labeled & (time_steps < test_steps[0])
    static_clf = fit_rf(X[static_train_mask], y[static_train_mask])
    print(f"Static model trained once on {static_train_mask.sum()} labeled nodes "
          f"(time_step < {test_steps[0]})")

    rows = []
    for t in test_steps:
        step_mask = labeled & (time_steps == t)
        if step_mask.sum() == 0:
            continue
        X_t, y_t = X[step_mask], y[step_mask]

        # STATIC prediction at this step
        static_pred = static_clf.predict(X_t)
        f1_s, p_s, r_s = step_metrics(y_t, static_pred)

        # ADAPTIVE (expanding, unweighted): retrain on everything strictly before
        # this step - what we already tested; kept for comparison.
        adaptive_train_mask = labeled & (time_steps < t)
        adaptive_clf = fit_rf(X[adaptive_train_mask], y[adaptive_train_mask])
        adaptive_pred = adaptive_clf.predict(X_t)
        f1_a, p_a, r_a = step_metrics(y_t, adaptive_pred)

        # ADAPTIVE + RECENCY-WEIGHTED: same training pool, but recent labels
        # count far more than old ones, so a handful of fresh post-drift
        # examples can actually shift the model instead of being diluted.
        w = recency_weights(time_steps[adaptive_train_mask], current_step=t, half_life=5.0)
        recency_clf = fit_rf(X[adaptive_train_mask], y[adaptive_train_mask], sample_weight=w)
        recency_pred = recency_clf.predict(X_t)
        f1_rw, p_rw, r_rw = step_metrics(y_t, recency_pred)

        rows.append({
            "time_step": int(t),
            "n_illicit": int(y_t.sum()),
            "static_f1": f1_s, "static_precision": p_s, "static_recall": r_s,
            "adaptive_f1": f1_a, "adaptive_precision": p_a, "adaptive_recall": r_a,
            "recency_f1": f1_rw, "recency_precision": p_rw, "recency_recall": r_rw,
            "adaptive_train_size": int(adaptive_train_mask.sum()),
        })
        print(f"time_step {t:2d} | n_illicit {int(y_t.sum()):3d} | "
              f"STATIC F1 {f1_s:.3f} | ADAPTIVE F1 {f1_a:.3f} | RECENCY-WEIGHTED F1 {f1_rw:.3f} "
              f"(trained on {int(adaptive_train_mask.sum())} labels)")

    df = pd.DataFrame(rows)
    os.makedirs(OUT_DIR, exist_ok=True)
    out_csv = os.path.join(OUT_DIR, "walkforward_comparison.csv")
    df.to_csv(out_csv, index=False)
    print(f"\nSaved -> {out_csv}")

    # Recovery-speed summary: after the known drift point, how many ADAPTIVE
    # steps does it take to get back above a reasonable F1 (e.g. 0.5)?
    drift_step = 43  # from eval_by_timestep.py's cliff detection
    post_drift = df[df["time_step"] >= drift_step].sort_values("time_step")
    recovered = post_drift[post_drift["recency_f1"] >= 0.5]
    print("\n--- Summary ---")
    print(f"Mean F1 static           (steps >= {drift_step}): {post_drift['static_f1'].mean():.3f}")
    print(f"Mean F1 adaptive (naive) (steps >= {drift_step}): {post_drift['adaptive_f1'].mean():.3f}")
    print(f"Mean F1 recency-weighted (steps >= {drift_step}): {post_drift['recency_f1'].mean():.3f}")
    if len(recovered) > 0:
        first_recovery = recovered.iloc[0]["time_step"]
        steps_to_recover = int(first_recovery - drift_step)
        print(f"Recency-weighted model first recovers to F1>=0.5 at time_step {int(first_recovery)} "
              f"({steps_to_recover} step(s) after the drift point).")
    else:
        print("Recency-weighted model did NOT recover to F1>=0.5 within the test period either - "
              "this would point toward the drift being too severe for label-based adaptation alone, "
              "motivating the domain-robust-training stretch goal (train for invariance across "
              "multiple historical sub-periods) as the next thing to try.")

    summary = {
        "drift_step": drift_step,
        "mean_static_f1_post_drift": round(float(post_drift["static_f1"].mean()), 4),
        "mean_adaptive_f1_post_drift": round(float(post_drift["adaptive_f1"].mean()), 4),
        "mean_recency_f1_post_drift": round(float(post_drift["recency_f1"].mean()), 4),
        "recovered": bool(len(recovered) > 0),
    }
    with open(os.path.join(OUT_DIR, "walkforward_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)


if __name__ == "__main__":
    main()