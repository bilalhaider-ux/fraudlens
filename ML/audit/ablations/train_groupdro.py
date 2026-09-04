"""
FraudLens - Group DRO: Environment-Invariant Training
=========================================================
Motivation (confirmed empirically): static, naive-adaptive, and recency-
weighted retraining ALL fail to recover after the time_step-43 concept-drift
event. All three share a root cause: they only ever optimize for AVERAGE
performance across the training period (steps 1-29), which lets them quietly
over-fit to whichever sub-period dominates by volume.

Group DRO (Sagawa et al. 2020, "Distributionally Robust Neural Networks for
Group Shift", arXiv:1911.08731) instead splits training into several time-
block "environments" and minimizes the WORST-CASE environment's loss, not
the average. A model trained this way is forced to find patterns that hold
up across multiple different historical regimes, rather than specializing in
whichever one has the most data - the direct mechanism by which it could
generalize better to an entirely unseen future regime (post-43), even though
it has still never seen a single post-43 example.

Trains TWO models for a clean, isolated comparison:
  - erm_mlp:      identical architecture, standard (average-loss) training.
                  Isolates "did switching to a neural net help at all?"
  - groupdro_mlp: same architecture, Group DRO training.
                  Isolates "did the robustness OBJECTIVE specifically help?"

Both are evaluated per-time-step on the untouched test region (35-49), in
the same format as eval_by_timestep.py, so results merge directly into the
existing comparison.
"""
import argparse
import json
import os

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.metrics import f1_score, precision_score, recall_score

from data_loader import load_elliptic, add_train_val_split

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "models")


class MLP(nn.Module):
    def __init__(self, in_dim, hidden=128, num_classes=2, dropout=0.3):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden), nn.ReLU(), nn.Dropout(dropout),
            nn.Linear(hidden, hidden // 2), nn.ReLU(), nn.Dropout(dropout),
            nn.Linear(hidden // 2, num_classes),
        )

    def forward(self, x):
        return self.net(x)


def make_environments(time_steps, train_mask, n_envs=4):
    """Split the TRAIN region into n_envs contiguous time-block environments.
    Returns a tensor of environment ids (same length as time_steps), -1 for
    nodes not in train_mask."""
    train_steps = time_steps[train_mask]
    lo, hi = int(train_steps.min()), int(train_steps.max())
    edges = np.linspace(lo, hi + 1, n_envs + 1)
    env_id = torch.full_like(time_steps, -1)
    for g in range(n_envs):
        in_block = (time_steps >= edges[g]) & (time_steps < edges[g + 1]) & train_mask
        env_id[in_block] = g
    sizes = [int((env_id == g).sum()) for g in range(n_envs)]
    print(f"Environments (time-block boundaries {edges.astype(int).tolist()}): "
          f"sizes={sizes}")
    return env_id


def class_weighted_ce(logits, y, class_weights):
    return F.cross_entropy(logits, y, weight=class_weights, reduction="mean")


def train_erm(model, X, y, class_weights, epochs, lr, weight_decay):
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)
    for epoch in range(1, epochs + 1):
        model.train()
        optimizer.zero_grad()
        logits = model(X)
        loss = class_weighted_ce(logits, y, class_weights)
        loss.backward()
        optimizer.step()
        if epoch % 20 == 0 or epoch == epochs:
            print(f"  [ERM]      epoch {epoch:3d} | loss {loss.item():.4f}")
    return model


def train_groupdro(model, X, y, env_id, class_weights, epochs, lr, weight_decay,
                    dro_step_size=0.01):
    """Sagawa et al. 2020 Group DRO: maintain adversarial group weights q,
    updated each step to upweight whichever group currently has the highest
    loss, then take a gradient step on the q-weighted ("robust") loss."""
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)
    groups = sorted(int(g) for g in torch.unique(env_id) if g >= 0)
    n_groups = len(groups)
    q = torch.ones(n_groups) / n_groups  # adversarial group weights, start uniform

    for epoch in range(1, epochs + 1):
        model.train()
        optimizer.zero_grad()
        logits = model(X)
        per_sample_loss = F.cross_entropy(logits, y, weight=class_weights, reduction="none")

        group_losses = torch.zeros(n_groups)
        for i, g in enumerate(groups):
            mask = env_id == g
            group_losses[i] = per_sample_loss[mask].mean()

        # exponentiated-gradient-ascent update on q (adversary maximizes robust loss)
        with torch.no_grad():
            q = q * torch.exp(dro_step_size * group_losses.detach())
            q = q / q.sum()

        robust_loss = (q * group_losses).sum()
        robust_loss.backward()
        optimizer.step()

        if epoch % 20 == 0 or epoch == epochs:
            gl = group_losses.detach()
            worst_g = groups[int(torch.argmax(gl))]
            print(f"  [GroupDRO] epoch {epoch:3d} | robust_loss {robust_loss.item():.4f} | "
                  f"group_losses={[round(float(l), 3) for l in gl]} | "
                  f"q={[round(float(w), 3) for w in q]} | worst_group={worst_g}")
    return model


@torch.no_grad()
def predict_scores(model, X):
    model.eval()
    return F.softmax(model(X), dim=1)[:, 1].numpy()


def per_timestep_table(y_true, y_scores, time_steps, model_name, threshold=0.5):
    rows = []
    y_pred = (y_scores >= threshold).astype(int)
    for t in sorted(np.unique(time_steps)):
        mask = time_steps == t
        yt, yp = y_true[mask], y_pred[mask]
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


def main(n_envs=4, epochs=150, lr=0.01, weight_decay=1e-4, dro_step_size=0.01, hidden=128,
         feature_set="raw"):
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(MODEL_DIR, exist_ok=True)
    torch.manual_seed(42)
    np.random.seed(42)

    data = load_elliptic()
    data = add_train_val_split(data)  # train: steps<30, val: 30-34, test: 35-49 (untouched)

    if feature_set == "hybrid":
        emb_path = os.path.join(OUT_DIR, "gcn_embeddings.npy")
        if not os.path.exists(emb_path):
            raise FileNotFoundError(
                "feature_set='hybrid' requires outputs/gcn_embeddings.npy - "
                "run train_gnn.py --model gcn first."
            )
        embeddings = np.load(emb_path)
        X_all = np.concatenate([data.x.numpy(), embeddings], axis=1)
        X_all = torch.tensor(X_all, dtype=torch.float)
    else:
        X_all = data.x

    y = data.y
    time_steps = data.time_step
    train_mask = data.train_mask
    val_mask = data.val_mask
    test_mask = data.test_mask

    env_id = make_environments(time_steps, train_mask, n_envs=n_envs)

    X_train, y_train = X_all[train_mask], y[train_mask]
    env_train = env_id[train_mask]

    n_pos = int((y_train == 1).sum())
    n_neg = int((y_train == 0).sum())
    class_weights = torch.tensor([1.0, max(n_neg / max(n_pos, 1), 1.0)], dtype=torch.float)
    print(f"Class weights (licit, illicit): {class_weights.tolist()}")
    print(f"Train: {int(train_mask.sum())} | Val: {int(val_mask.sum())} | "
          f"Test: {int(test_mask.sum())} (test untouched until final eval)\n")

    in_dim = X_all.size(1)

    # --- ERM baseline (same architecture, standard training) ---
    print("Training ERM-MLP (ablation baseline)...")
    erm_model = MLP(in_dim, hidden=hidden)
    erm_model = train_erm(erm_model, X_train, y_train, class_weights, epochs, lr, weight_decay)

    # --- Group DRO model ---
    print("\nTraining Group-DRO-MLP...")
    dro_model = MLP(in_dim, hidden=hidden)
    dro_model = train_groupdro(dro_model, X_train, y_train, env_train, class_weights,
                                epochs, lr, weight_decay, dro_step_size=dro_step_size)

    # --- Validation sanity check (steps 30-34, not test) ---
    print("\n--- Validation check (steps 30-34, not the final test set) ---")
    for name, model in [("erm_mlp", erm_model), ("groupdro_mlp", dro_model)]:
        y_val_true = y[val_mask].numpy()
        y_val_scores = predict_scores(model, X_all[val_mask])
        y_val_pred = (y_val_scores >= 0.5).astype(int)
        f1 = f1_score(y_val_true, y_val_pred, zero_division=0)
        print(f"  {name}: val F1 = {f1:.4f}")

    # --- Final test evaluation (35-49), touched exactly once, per-timestep ---
    y_test_true = y[test_mask].numpy()
    ts_test = time_steps[test_mask].numpy()

    all_rows = []
    for name, model in [("erm_mlp", erm_model), ("groupdro_mlp", dro_model)]:
        y_scores = predict_scores(model, X_all[test_mask])
        all_rows += per_timestep_table(y_test_true, y_scores, ts_test, name)
        torch.save(model.state_dict(), os.path.join(MODEL_DIR, f"{name}.pt"))

    df = pd.DataFrame(all_rows)
    out_csv = os.path.join(OUT_DIR, "groupdro_comparison.csv")
    df.to_csv(out_csv, index=False)
    print(f"\nSaved -> {out_csv}\n")
    print(df.pivot(index="time_step", columns="model", values="f1").round(3).to_string())

    # summary vs. the drift point already established
    drift_step = 43
    post_drift = df[df["time_step"] >= drift_step]
    summary = {}
    for name in ["erm_mlp", "groupdro_mlp"]:
        mean_f1 = post_drift[post_drift["model"] == name]["f1"].mean()
        summary[name] = round(float(mean_f1), 4) if not np.isnan(mean_f1) else None
    print(f"\n--- Summary (mean F1, steps >= {drift_step}) ---")
    print(json.dumps(summary, indent=2))
    print("\nFor reference, from the previous walk-forward experiment: "
          "static=0.086, naive-adaptive=0.015, recency-weighted=0.030")

    with open(os.path.join(OUT_DIR, "groupdro_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n_envs", type=int, default=4)
    parser.add_argument("--epochs", type=int, default=150)
    parser.add_argument("--lr", type=float, default=0.01)
    parser.add_argument("--dro_step_size", type=float, default=1.0)
    parser.add_argument("--hidden", type=int, default=128)
    parser.add_argument("--features", choices=["raw", "hybrid"], default="raw")
    args = parser.parse_args()
    main(n_envs=args.n_envs, epochs=args.epochs, lr=args.lr,
         dro_step_size=args.dro_step_size, hidden=args.hidden, feature_set=args.features)