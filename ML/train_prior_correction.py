"""
FraudLens - Label-Free Prior/Quantification Correction
===========================================================
The oracle experiment (train_threshold_correction.py) showed post-43 F1 can
reach ~0.96 with a PERFECT per-step threshold, vs ~0.48 with the best single
global threshold - meaning the model's scores already contain nearly all the
signal, but a fixed threshold can't track a shifting class prior.

This implements a real, established fix that needs NO test-time labels:

  1. Black-Box Shift Estimation (Lipton, Lei, Sun, ICML 2018) - estimate the
     TARGET class prior using only (a) the classifier's confusion matrix on
     a labeled calibration set (our validation split) and (b) the
     classifier's PREDICTED-label distribution on the new (unlabeled) data.
     Solved via a small 2x2 linear system (binary classification).

  2. Saerens-Latinne-Decaestecker prior correction (Neural Computation,
     2002) - given the estimated new prior, re-derive Bayes-consistent
     adjusted scores from the model's original (now-miscalibrated-for-the-
     new-prior) probabilities, then threshold the ADJUSTED scores at the
     natural 0.5 - equivalent to an adaptive per-step threshold, without
     ever looking at the step's true labels.

Because this dataset is static, we ALSO print the true known prior per step
purely as a sanity check on the estimation method itself (not used by the
method) - if the label-free estimate tracks the true collapse-and-recovery
pattern well, that's strong evidence the method is working correctly.
"""
import json
import os

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score, precision_score, recall_score

from data_loader import load_elliptic, add_train_val_split

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs")


def estimate_target_prior_bbse(y_val_true, y_val_pred_hard, y_target_pred_hard):
    """Black-Box Shift Estimation for binary classification.
    C[i,j] = P(predicted=j | true=i) estimated on validation.
    q[j] = P(predicted=j) observed on the target (test) step.
    Solve C^T . pi_hat = q  for pi_hat = [P(true=0), P(true=1)] on target.
    """
    C = np.zeros((2, 2))
    for true_c in [0, 1]:
        mask = y_val_true == true_c
        if mask.sum() == 0:
            C[true_c] = [0.5, 0.5]  # degenerate fallback
            continue
        for pred_c in [0, 1]:
            C[true_c, pred_c] = (y_val_pred_hard[mask] == pred_c).mean()

    q = np.array([(y_target_pred_hard == 0).mean(), (y_target_pred_hard == 1).mean()])

    try:
        pi_hat = np.linalg.solve(C.T, q)
    except np.linalg.LinAlgError:
        pi_hat = np.linalg.lstsq(C.T, q, rcond=None)[0]

    pi_hat = np.clip(pi_hat, 1e-4, 1 - 1e-4)
    pi_hat = pi_hat / pi_hat.sum()
    return pi_hat[1]  # P(true illicit) on target


def shrink_toward_source(estimated_prior, source_prior, n_obs, shrinkage_k=3000.0):
    """Empirical-Bayes-style shrinkage: a prior estimated from very few
    observations (small n_obs) is unreliable, so pull it toward the (much
    more data-backed) source prior. shrinkage_k controls how many
    observations it takes to start trusting the estimate mostly on its own -
    with n_obs << shrinkage_k, the result stays close to source_prior; with
    n_obs >> shrinkage_k, it converges to the raw estimate. This uses ONLY
    the step's sample size (always known), never target labels.

    NOTE: shrinkage_k=3000 (not the original 30) - test time_steps here have
    hundreds to low-thousands of transactions each, not a handful. With
    k=30, weight=n_obs/(n_obs+30) was already ~0.9+ at realistic step sizes,
    so almost no shrinkage was actually happening despite the mechanism
    working correctly on tiny synthetic test data. k=3000 makes shrinkage
    meaningfully bite at the real scale."""
    weight = n_obs / (n_obs + shrinkage_k)
    return weight * estimated_prior + (1 - weight) * source_prior


def saerens_prior_correction(scores, source_prior_pos, target_prior_pos):
    """Adjust probabilities trained under source_prior to be Bayes-consistent
    under an estimated target_prior. Standard prior-correction formula."""
    ratio_pos = target_prior_pos / source_prior_pos
    ratio_neg = (1 - target_prior_pos) / (1 - source_prior_pos)
    numer = scores * ratio_pos
    denom = numer + (1 - scores) * ratio_neg
    return numer / np.clip(denom, 1e-12, None)


def best_f1_threshold(y_true, y_scores, thresholds=None):
    """Same idea as train_threshold_correction.py: find the F1-optimal cutoff
    on validation (source-prior regime, so correction is a no-op there)."""
    if thresholds is None:
        thresholds = np.linspace(0.05, 0.95, 37)
    best_t, best_f1 = 0.5, -1
    for t in thresholds:
        pred = (y_scores >= t).astype(int)
        f1 = f1_score(y_true, pred, zero_division=0)
        if f1 > best_f1:
            best_f1, best_t = f1, t
    return best_t, best_f1


def main():
    data = load_elliptic()
    data = add_train_val_split(data)

    gwf_path = os.path.join(OUT_DIR, "guiltywalker_features.csv")
    if not os.path.exists(gwf_path):
        raise FileNotFoundError(f"{gwf_path} not found - run train_baseline_guiltywalker.py first")
    gwf = pd.read_csv(gwf_path).values
    X = np.concatenate([data.x.numpy(), gwf], axis=1)

    y = data.y.numpy()
    time_steps = data.time_step.numpy()
    train_mask = data.train_mask.numpy()
    val_mask = data.val_mask.numpy()
    test_mask = data.test_mask.numpy()

    # NOTE: class_weight is intentionally NOT balanced here (unlike every other
    # script in this project). Saerens prior correction assumes predict_proba
    # reflects the TRUE empirical training prior (source_prior_pos below) - a
    # class-balanced bootstrap (class_weight="balanced_subsample") breaks that
    # assumption by making the RF's internal calibration act as if trained on
    # a ~50/50 prior, which silently invalidates the correction formula and
    # was the actual cause of the F1=0.000 / 100%-recall-everywhere failure.
    clf = RandomForestClassifier(
        n_estimators=200, max_depth=None,
        n_jobs=-1, random_state=42,
    )
    clf.fit(X[train_mask], y[train_mask])

    source_prior_pos = y[train_mask].mean()
    print(f"Source (train) prior P(illicit): {source_prior_pos:.4f}")

    # Calibration sanity check: does the model's own mean predicted probability
    # on the (unseen-during-fit-eval) validation set roughly match the true
    # source prior? If this is way off (e.g. near 0.5), scores aren't
    # calibrated to source_prior_pos and the correction below will misfire.
    mean_val_score = clf.predict_proba(X[val_mask])[:, 1].mean()
    print(f"Mean predicted P(illicit) on validation: {mean_val_score:.4f} "
          f"(should be roughly in the same ballpark as the source prior above - "
          f"if it's near 0.5 instead, calibration is still off)")

    # validation: used to build the confusion matrix for BBSE, AND to find a
    # non-naive decision cutoff (F1-optimal on validation, where correction is
    # a no-op since target_prior==source_prior there by construction).
    y_val = y[val_mask]
    s_val = clf.predict_proba(X[val_mask])[:, 1]
    y_val_pred_hard = (s_val >= 0.5).astype(int)

    val_threshold, val_f1_at_best = best_f1_threshold(y_val, s_val)
    print(f"Validation-tuned threshold (applied to corrected scores below, "
          f"NOT the naive 0.5): {val_threshold:.3f}")

    y_test = y[test_mask]
    s_test = clf.predict_proba(X[test_mask])[:, 1]
    ts_test = time_steps[test_mask]

    rows = []
    prior_check_rows = []
    for t in sorted(np.unique(ts_test)):
        mask = ts_test == t
        yt, st = y_test[mask], s_test[mask]
        if len(yt) == 0:
            continue

        target_pred_hard = (st >= 0.5).astype(int)
        raw_estimated_prior = estimate_target_prior_bbse(y_val, y_val_pred_hard, target_pred_hard)
        shrink_weight = len(yt) / (len(yt) + 3000.0)
        estimated_prior = shrink_toward_source(raw_estimated_prior, source_prior_pos,
                                                n_obs=len(yt), shrinkage_k=3000.0)
        true_prior = yt.mean()  # sanity-check ONLY, never used by the method itself

        adjusted_scores = saerens_prior_correction(st, source_prior_pos, estimated_prior)
        pred = (adjusted_scores >= val_threshold).astype(int)

        f1 = f1_score(yt, pred, zero_division=0) if yt.sum() > 0 else float("nan")
        prec = precision_score(yt, pred, zero_division=0) if yt.sum() > 0 else float("nan")
        rec = recall_score(yt, pred, zero_division=0) if yt.sum() > 0 else float("nan")

        rows.append({"time_step": int(t), "n_illicit": int(yt.sum()), "n_total": int(len(yt)),
                      "raw_estimated_prior": round(float(raw_estimated_prior), 4),
                      "shrink_weight": round(float(shrink_weight), 3),
                      "estimated_prior": round(float(estimated_prior), 4),
                      "true_prior_SANITY_CHECK_ONLY": round(float(true_prior), 4),
                      "precision": prec, "recall": rec, "f1": f1})
        prior_check_rows.append((int(t), estimated_prior, true_prior))

    df = pd.DataFrame(rows)
    out_csv = os.path.join(OUT_DIR, "prior_correction_comparison.csv")
    df.to_csv(out_csv, index=False)
    print(f"\nSaved -> {out_csv}\n")
    print(df.to_string(index=False))

    # sanity check: does the label-free prior ESTIMATE track the true collapse?
    print("\n--- Sanity check: estimated vs true prior (true is NOT used by the method) ---")
    corr = np.corrcoef([r[1] for r in prior_check_rows], [r[2] for r in prior_check_rows])[0, 1]
    print(f"Correlation between estimated and true prior across test steps: {corr:.3f}")
    print("(Close to 1.0 = the label-free estimation is genuinely tracking the real shift)")

    drift_step = 43
    post = df[df["time_step"] >= drift_step]
    print(f"\nMean F1, steps >= {drift_step} (prior-corrected, label-free): {post['f1'].mean():.4f}")
    print("For reference: default_0.5 was 0.2944, val_tuned was 0.4791, "
          "oracle (cheating, diagnostic) was 0.9621")

    with open(os.path.join(OUT_DIR, "prior_correction_summary.json"), "w") as f:
        json.dump({
            "mean_f1_prior_corrected_post_drift": round(float(post["f1"].mean()), 4),
            "estimated_vs_true_prior_correlation": round(float(corr), 4),
        }, f, indent=2)


if __name__ == "__main__":
    main()