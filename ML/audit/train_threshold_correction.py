"""
FraudLens - Threshold Correction (Prior-Shift Fix)
=======================================================
Motivation: recent research on this exact dataset (Maganti 2026) shows the
time_step-43 collapse is primarily a LABEL-PRIOR shift, not a feature shift -
the true illicit rate crashes from ~11.6% (train) to as low as 0.3% (step 46),
while feature distributions barely move. A classifier calibrated at a fixed
0.5 threshold for an 11% prior will almost never fire once the true rate
drops 39x - this is a plausible mechanical explanation for F1=0.000 at
several post-drift steps, separate from whether real predictive signal
exists at all.

Retrains the AF+GuiltyWalker RF on a strict train/val split (val is NEVER
used for anything except threshold tuning), then evaluates two things on
the untouched test set (35-49):

  1. VALIDATION-TUNED THRESHOLD (deployable): a single global threshold
     chosen to maximize F1 on validation (steps 30-34) - a fair, honest,
     production-realistic method requiring no test-time information.

  2. ORACLE PER-STEP THRESHOLD (diagnostic only, NOT deployable): the best
     possible threshold chosen using each test step's OWN true labels.
     This is cheating on purpose - it's a ceiling, not a method - to answer
     "how much of the remaining gap is a threshold problem vs a genuine
     no-signal problem?" If oracle-threshold F1 is still near 0 at some
     step, that step has a real information problem thresholding can't fix.
     If oracle-threshold F1 is high but validation-threshold F1 isn't,
     that's a calibration problem worth solving further.
"""
import json
import os

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score, precision_score, recall_score

from data_loader import load_elliptic, add_train_val_split

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs")


def best_f1_threshold(y_true, y_scores, thresholds=None):
    if thresholds is None:
        thresholds = np.linspace(0.05, 0.95, 37)
    best_t, best_f1 = 0.5, -1
    for t in thresholds:
        pred = (y_scores >= t).astype(int)
        f1 = f1_score(y_true, pred, zero_division=0)
        if f1 > best_f1:
            best_f1, best_t = f1, t
    return best_t, best_f1


def per_timestep_eval(y_true, y_scores, time_steps, threshold_fn, label):
    """threshold_fn(t, yt, ys) -> threshold to use for this step's predictions."""
    rows = []
    for t in sorted(np.unique(time_steps)):
        mask = time_steps == t
        yt, ys = y_true[mask], y_scores[mask]
        thresh = threshold_fn(t, yt, ys)
        pred = (ys >= thresh).astype(int)
        f1 = f1_score(yt, pred, zero_division=0) if yt.sum() > 0 else float("nan")
        prec = precision_score(yt, pred, zero_division=0) if yt.sum() > 0 else float("nan")
        rec = recall_score(yt, pred, zero_division=0) if yt.sum() > 0 else float("nan")
        rows.append({"model": label, "time_step": int(t), "n_illicit": int(yt.sum()),
                      "threshold_used": round(float(thresh), 3),
                      "precision": prec, "recall": rec, "f1": f1})
    return pd.DataFrame(rows)


def main():
    data = load_elliptic()
    data = add_train_val_split(data)  # train: steps<30, val: 30-34, test: 35-49 (untouched)

    gwf_path = os.path.join(OUT_DIR, "guiltywalker_features.csv")
    if not os.path.exists(gwf_path):
        raise FileNotFoundError(f"{gwf_path} not found - run train_baseline_guiltywalker.py first")
    gwf = pd.read_csv(gwf_path).values
    X_raw = data.x.numpy()
    X = np.concatenate([X_raw, gwf], axis=1)

    y = data.y.numpy()
    time_steps = data.time_step.numpy()
    train_mask = data.train_mask.numpy()
    val_mask = data.val_mask.numpy()
    test_mask = data.test_mask.numpy()

    print(f"Train: {train_mask.sum()} | Val: {val_mask.sum()} | Test: {test_mask.sum()}")

    clf = RandomForestClassifier(
        n_estimators=200, max_depth=None,
        class_weight="balanced_subsample", n_jobs=-1, random_state=42,
    )
    clf.fit(X[train_mask], y[train_mask])

    # --- Tune threshold on VAL only (never touches test) ---
    y_val, s_val = y[val_mask], clf.predict_proba(X[val_mask])[:, 1]
    val_threshold, val_f1_at_best = best_f1_threshold(y_val, s_val)
    print(f"\nValidation-tuned global threshold: {val_threshold:.3f} "
          f"(val F1 at this threshold: {val_f1_at_best:.4f}; default 0.5 val F1: "
          f"{f1_score(y_val, (s_val>=0.5).astype(int), zero_division=0):.4f})")

    # --- Final test evaluation (touched once per method) ---
    y_test, s_test, ts_test = y[test_mask], clf.predict_proba(X[test_mask])[:, 1], time_steps[test_mask]

    default_df = per_timestep_eval(y_test, s_test, ts_test,
                                    lambda t, yt, ys: 0.5, "default_0.5")
    tuned_df = per_timestep_eval(y_test, s_test, ts_test,
                                  lambda t, yt, ys: val_threshold, "val_tuned")
    # Oracle: cheats using each step's OWN true labels - diagnostic ceiling only
    oracle_df = per_timestep_eval(
        y_test, s_test, ts_test,
        lambda t, yt, ys: best_f1_threshold(yt, ys)[0] if yt.sum() > 0 else 0.5,
        "oracle_per_step_DIAGNOSTIC_ONLY",
    )

    all_df = pd.concat([default_df, tuned_df, oracle_df], ignore_index=True)
    out_csv = os.path.join(OUT_DIR, "threshold_correction_comparison.csv")
    all_df.to_csv(out_csv, index=False)
    print(f"\nSaved -> {out_csv}\n")

    pivot = all_df.pivot(index="time_step", columns="model", values="f1")
    pivot = pivot[["default_0.5", "val_tuned", "oracle_per_step_DIAGNOSTIC_ONLY"]]
    print(pivot.round(3).to_string())

    drift_step = 43
    print(f"\n--- Mean F1, steps >= {drift_step} ---")
    for label in ["default_0.5", "val_tuned", "oracle_per_step_DIAGNOSTIC_ONLY"]:
        m = all_df[(all_df["model"] == label) & (all_df["time_step"] >= drift_step)]["f1"].mean()
        print(f"  {label}: {m:.4f}")

    print("\nHow to read this:")
    print("  - If val_tuned clearly beats default_0.5: real, deployable win - threshold")
    print("    miscalibration was masking genuine signal. Ship this.")
    print("  - If oracle is much higher than val_tuned: there IS more signal available,")
    print("    but a single global threshold can't reach it - worth a smarter per-step or")
    print("    adaptive threshold strategy (e.g. estimated-prior correction) next.")
    print("  - If oracle itself is still near 0 at a step: that step has a genuine")
    print("    no-signal problem no threshold can fix - stop tuning, focus elsewhere.")

    with open(os.path.join(OUT_DIR, "threshold_correction_summary.json"), "w") as f:
        json.dump({
            "val_tuned_threshold": round(float(val_threshold), 4),
            "mean_f1_default_post_drift": round(float(
                all_df[(all_df["model"] == "default_0.5") & (all_df["time_step"] >= drift_step)]["f1"].mean()), 4),
            "mean_f1_val_tuned_post_drift": round(float(
                all_df[(all_df["model"] == "val_tuned") & (all_df["time_step"] >= drift_step)]["f1"].mean()), 4),
            "mean_f1_oracle_post_drift": round(float(
                all_df[(all_df["model"] == "oracle_per_step_DIAGNOSTIC_ONLY") & (all_df["time_step"] >= drift_step)]["f1"].mean()), 4),
        }, f, indent=2)


if __name__ == "__main__":
    main()
