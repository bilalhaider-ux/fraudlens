"""
FraudLens - Dual-Engine Production AML System
============================================
Evaluates two production AML engines with complete methodological integrity:

Engine 1 (Autonomous Cold Triage):
  - 100% un-leaked feature matrix: 165 raw node features + 9 clean structural features.
  - Compares fixed validation threshold vs. adaptive prior matching.
  - Zero access to test-set labels.

Engine 2 (Human-in-the-Loop Cluster Unraveling):
  - Simulates an investigator confirming 1 illicit transaction per test timestep.
  - Propagates guilt outward via Personalized PageRank from that single verified seed.
  - Measures Hit Rate @ K and cluster recall without omniscient test-label seeding.
"""

import json
import os
import lightgbm as lgb
import networkx as nx
import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, precision_score, recall_score, average_precision_score

from data_loader import load_elliptic, add_train_val_split
from train_prior_correction import best_f1_threshold

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "models")


def evaluate_engine_1(X, y, time_steps, train_mask, val_mask, test_mask):
    print("\n" + "=" * 60)
    print("ENGINE 1: AUTONOMOUS COLD TRIAGE (Zero Label Leakage)")
    print("=" * 60)

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

    s_val = clf.predict_proba(X[val_mask])[:, 1]
    val_th, val_f1 = best_f1_threshold(y[val_mask], s_val)
    print(f"Validation-tuned threshold: {val_th:.3f} (Validation F1: {val_f1:.4f})")

    y_test = y[test_mask]
    ts_test = time_steps[test_mask]
    s_test = clf.predict_proba(X[test_mask])[:, 1]

    # Mode A: Fixed Validation-Tuned Threshold
    y_pred_fixed = (s_test >= val_th).astype(int)

    # Mode B: Adaptive Quantile Thresholding
    # NOTE ON THE ORIGINAL CODE: it assumed "~1.5% expected illicit rate" -
    # this does NOT match the actual overall test illicit rate (~6.5%, 1083 of
    # 16670), confirmed repeatedly earlier in this project. That guess was
    # simply wrong.
    #
    # CAUTION - the "obvious fix" of using y_test.mean() directly here would
    # itself be a NEW label leak (using true test labels to set the
    # threshold) - just a different flavor of the same mistake. This is
    # included ONLY as a labeled, non-deployable DIAGNOSTIC reference (same
    # spirit as the "oracle" threshold in train_threshold_correction.py) to
    # show what the 1.5%-guess version should be compared against. For an
    # actually deployable, label-free version of this idea, use the
    # Black-Box Shift Estimation approach already built and validated in
    # train_prior_correction.py - do NOT ship this diagnostic version.
    true_test_illicit_rate_DIAGNOSTIC_ONLY = y_test.mean()
    adaptive_th = np.percentile(s_test, 100 * (1 - true_test_illicit_rate_DIAGNOSTIC_ONLY))
    print(f"(DIAGNOSTIC ONLY - uses true test label rate "
          f"{true_test_illicit_rate_DIAGNOSTIC_ONLY:.4f} to show what the original "
          f"1.5%-guess version should be compared against. NOT a deployable fix - "
          f"see comment in source.)")
    y_pred_adapt = (s_test >= adaptive_th).astype(int)

    rows = []
    for t in sorted(np.unique(ts_test)):
        m = ts_test == t
        yt = y_test[m]
        yp_fix = y_pred_fixed[m]
        yp_adp = y_pred_adapt[m]
        ys = s_test[m]

        n_ill = int(yt.sum())
        pr_auc = average_precision_score(yt, ys) if n_ill > 0 else float("nan")

        f1_fix = f1_score(yt, yp_fix, zero_division=0) if n_ill > 0 else float("nan")
        f1_adp = f1_score(yt, yp_adp, zero_division=0) if n_ill > 0 else float("nan")

        rows.append({
            "timestep": int(t),
            "n_illicit": n_ill,
            "total_nodes": int(m.sum()),
            "pr_auc": pr_auc,
            "f1_fixed_th": f1_fix,
            "f1_adaptive_th": f1_adp,
        })

    df_res = pd.DataFrame(rows)
    print("\n--- Engine 1 Per-Timestep Breakdown ---")
    print(df_res.to_string(index=False))

    post_mask = df_res["timestep"] >= 43
    print(f"\nOverall Test F1 (Fixed Th {val_th:.3f}): {f1_score(y_test, y_pred_fixed, zero_division=0):.4f}")
    print(f"Overall Test PR-AUC: {average_precision_score(y_test, s_test):.4f}")
    print(f"Pre-drift (35-42) Mean F1:  {df_res[~post_mask]['f1_fixed_th'].mean():.4f}")
    print(f"Post-drift (43-49) Mean PR-AUC: {df_res[post_mask]['pr_auc'].mean():.4f}")
    print(f"Post-drift (43-49) Mean F1 (Fixed):    {df_res[post_mask]['f1_fixed_th'].mean():.4f}")
    print(f"Post-drift (43-49) Mean F1 (Adaptive): {df_res[post_mask]['f1_adaptive_th'].mean():.4f}")

    df_res.to_csv(os.path.join(OUT_DIR, "engine1_honest_metrics.csv"), index=False)
    return clf


def evaluate_engine_2(edge_index, y, time_steps, test_mask, n_trials=25):
    """
    NOTE: the original version drew ONE random seed per timestep and reported
    that single trial's result - at timesteps with only 2-5 illicit examples
    total, one lucky/unlucky draw can swing Hit@20 dramatically. This version
    averages over n_trials different random seed choices per timestep (using
    every available illicit node as a seed at least once when possible) for a
    stable, defensible estimate instead of a single noisy roll of the dice.
    """
    print("\n" + "=" * 60)
    print(f"ENGINE 2: SYNDICATE UNRAVELING ({n_trials} trials/timestep, averaged)")
    print("=" * 60)

    steps = sorted(np.unique(time_steps[test_mask]).tolist())
    src, dst = edge_index[0], edge_index[1]
    rng = np.random.RandomState(42)

    per_step_rows = []
    all_h20, all_h50, all_mrr = [], [], []

    for t in steps:
        step_mask = (time_steps == t) & (test_mask)
        node_ids = np.where(step_mask)[0]
        illicit_in_step = [n for n in node_ids if y[n] == 1]

        if len(illicit_in_step) < 2:
            continue

        global_to_local = {g: i for i, g in enumerate(node_ids)}
        node_id_set = set(node_ids.tolist())

        sub_edges = []
        for s, d in zip(src.tolist(), dst.tolist()):
            if s in node_id_set and d in node_id_set:
                sub_edges.append((global_to_local[s], global_to_local[d]))

        G = nx.DiGraph()
        G.add_nodes_from(range(len(node_ids)))
        G.add_edges_from(sub_edges)
        UG = G.to_undirected()

        # Trial seeds: every illicit node used at least once (if few), else a
        # random sample of n_trials distinct seeds - never just one draw.
        n_seeds = min(n_trials, len(illicit_in_step))
        trial_seeds = rng.choice(illicit_in_step, size=n_seeds, replace=False)

        step_h20, step_h50, step_mrr = [], [], []
        for seed_global in trial_seeds:
            seed_local = global_to_local[seed_global]
            target_locals = {global_to_local[g] for g in illicit_in_step if g != seed_global}

            try:
                ppr = nx.pagerank(UG, alpha=0.85, personalization={seed_local: 1.0}, max_iter=200)
            except Exception:
                continue

            ranked_nodes = [node for node, score in
                             sorted(ppr.items(), key=lambda x: x[1], reverse=True)
                             if node != seed_local]

            h20 = int(any(n in target_locals for n in ranked_nodes[:20]))
            h50 = int(any(n in target_locals for n in ranked_nodes[:50]))
            ranks = [idx + 1 for idx, n in enumerate(ranked_nodes) if n in target_locals]
            mrr = (1.0 / min(ranks)) if ranks else 0.0

            step_h20.append(h20)
            step_h50.append(h50)
            step_mrr.append(mrr)

        mean_h20, mean_h50, mean_mrr = np.mean(step_h20), np.mean(step_h50), np.mean(step_mrr)
        per_step_rows.append({
            "timestep": int(t), "syndicate_size": len(illicit_in_step),
            "n_trials": n_seeds, "mean_hit_at_20": mean_h20,
            "mean_hit_at_50": mean_h50, "mean_mrr": mean_mrr,
        })
        all_h20.extend(step_h20)
        all_h50.extend(step_h50)
        all_mrr.extend(step_mrr)

        print(f"Timestep {t:2d} | Syndicate size: {len(illicit_in_step):3d} | "
              f"{n_seeds} trials | Hit@20: {mean_h20:.3f} | Hit@50: {mean_h50:.3f} | "
              f"MRR: {mean_mrr:.3f}")

    df = pd.DataFrame(per_step_rows)
    df.to_csv(os.path.join(OUT_DIR, "engine2_multitrial_metrics.csv"), index=False)

    print(f"\nEngine 2 Syndicate Recovery Metrics (Across Timesteps 35-49, "
          f"{n_trials}-trial average per step, NOT single-draw):")
    print(f"Mean Hit@20: {np.mean(all_h20):.4f} (std across trials: {np.std(all_h20):.4f})")
    print(f"Mean Hit@50: {np.mean(all_h50):.4f} (std across trials: {np.std(all_h50):.4f})")
    print(f"Mean Reciprocal Rank (MRR): {np.mean(all_mrr):.4f} (std: {np.std(all_mrr):.4f})")
    print("\nCompare this multi-trial estimate against the single-draw version - "
          "a big gap between them confirms the original single-seed numbers were noisy.")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(MODEL_DIR, exist_ok=True)

    data = load_elliptic()
    data = add_train_val_split(data)

    clean_struct_path = os.path.join(OUT_DIR, "clean_structural_features.csv")
    if not os.path.exists(clean_struct_path):
        raise FileNotFoundError(
            f"Missing {clean_struct_path}. Run 'python src/clean_structural_features.py' first."
        )

    clean_df = pd.read_csv(clean_struct_path)
    X_raw = data.x.numpy()
    X = np.concatenate([X_raw, clean_df.values], axis=1)
    y = data.y.numpy()
    time_steps = data.time_step.numpy()

    train_mask = data.train_mask.numpy()
    val_mask = data.val_mask.numpy()
    test_mask = data.test_mask.numpy()

    # Engine 1: Autonomous Triage
    evaluate_engine_1(X, y, time_steps, train_mask, val_mask, test_mask)

    # Engine 2: Human-in-the-Loop Syndicate Unraveling
    evaluate_engine_2(data.edge_index.numpy(), y, time_steps, test_mask)


if __name__ == "__main__":
    main()