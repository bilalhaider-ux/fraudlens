"""
FraudLens - Graph Neural Network Models
==========================================
GCN and GAT (GATv2) node classifiers for illicit/licit transaction detection.
Trained on the full graph (transductive), evaluated only on the temporal
test split (time_step 35-49), matching the baseline for a fair comparison.
"""
import argparse
import json
import os

import numpy as np
import torch
import torch.nn.functional as F
from sklearn.metrics import (
    precision_recall_curve, auc, f1_score, roc_auc_score,
    precision_score, recall_score, classification_report
)
from torch_geometric.nn import GCNConv, GATv2Conv

from data_loader import load_elliptic, add_train_val_split
from train_baseline import recall_at_precision

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "models")


class GCN(torch.nn.Module):
    def __init__(self, in_channels, hidden_channels=64, num_classes=2, dropout=0.3):
        super().__init__()
        self.conv1 = GCNConv(in_channels, hidden_channels)
        self.conv2 = GCNConv(hidden_channels, hidden_channels)
        self.lin = torch.nn.Linear(hidden_channels, num_classes)
        self.dropout = dropout

    def forward(self, x, edge_index, return_embedding=False):
        x = self.conv1(x, edge_index).relu()
        x = F.dropout(x, p=self.dropout, training=self.training)
        emb = self.conv2(x, edge_index).relu()
        x = F.dropout(emb, p=self.dropout, training=self.training)
        out = self.lin(x)
        return (out, emb) if return_embedding else out


class GAT(torch.nn.Module):
    def __init__(self, in_channels, hidden_channels=32, heads=4, num_classes=2, dropout=0.3):
        super().__init__()
        self.conv1 = GATv2Conv(in_channels, hidden_channels, heads=heads, dropout=dropout)
        self.conv2 = GATv2Conv(hidden_channels * heads, hidden_channels, heads=1,
                                concat=False, dropout=dropout)
        self.lin = torch.nn.Linear(hidden_channels, num_classes)
        self.dropout = dropout

    def forward(self, x, edge_index, return_embedding=False):
        x = self.conv1(x, edge_index).relu()
        x = F.dropout(x, p=self.dropout, training=self.training)
        emb = self.conv2(x, edge_index).relu()
        out = self.lin(emb)
        return (out, emb) if return_embedding else out


def train(model, data, optimizer, class_weights, device):
    model.train()
    optimizer.zero_grad()
    out = model(data.x, data.edge_index)
    loss = F.cross_entropy(out[data.train_mask], data.y[data.train_mask],
                            weight=class_weights)
    loss.backward()
    optimizer.step()
    return loss.item()


@torch.no_grad()
def evaluate(model, data, mask):
    model.eval()
    out = model(data.x, data.edge_index)
    probs = F.softmax(out, dim=1)[:, 1]  # P(illicit)
    y_true = data.y[mask].cpu().numpy()
    y_scores = probs[mask].cpu().numpy()
    return y_true, y_scores


def compute_metrics(y_true, y_scores, model_name):
    y_pred = (y_scores >= 0.5).astype(int)
    precisions, recalls, _ = precision_recall_curve(y_true, y_scores)
    pr_auc = auc(recalls, precisions)
    roc_auc = roc_auc_score(y_true, y_scores)
    f1 = f1_score(y_true, y_pred)
    recall_95p, thresh_95p = recall_at_precision(y_true, y_scores, 0.95)
    return {
        "model": model_name,
        "pr_auc": round(pr_auc, 4),
        "roc_auc": round(roc_auc, 4),
        "f1_at_0.5": round(f1, 4),
        "precision_at_0.5": round(precision_score(y_true, y_pred, zero_division=0), 4),
        "recall_at_0.5": round(recall_score(y_true, y_pred), 4),
        "recall_at_95pct_precision": round(recall_95p, 4),
    }


def run(model_type="gcn", epochs=150, lr=0.01, weight_decay=5e-4, hidden=64, seed=42):
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(MODEL_DIR, exist_ok=True)
    torch.manual_seed(seed)
    np.random.seed(seed)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    data = load_elliptic()
    data = add_train_val_split(data)  # carves val out of TRAIN only; test_mask untouched
    data = data.to(device)

    n_train_pos = int((data.y[data.train_mask] == 1).sum())
    n_train_neg = int((data.y[data.train_mask] == 0).sum())
    # inverse-frequency class weights to counter the ~2% illicit imbalance
    w_licit = 1.0
    w_illicit = max(n_train_neg / max(n_train_pos, 1), 1.0)
    class_weights = torch.tensor([w_licit, w_illicit], dtype=torch.float, device=device)
    print(f"Class weights (licit, illicit): {class_weights.tolist()}")

    in_channels = data.x.size(1)
    if model_type == "gcn":
        model = GCN(in_channels, hidden_channels=hidden).to(device)
    elif model_type == "gat":
        model = GAT(in_channels, hidden_channels=max(hidden // 4, 8)).to(device)
    else:
        raise ValueError(f"Unknown model_type: {model_type}")

    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)

    print(f"Train: {int(data.train_mask.sum())} | Val: {int(data.val_mask.sum())} | "
          f"Test: {int(data.test_mask.sum())} (test never used for checkpoint selection)")

    best_val_pr_auc = -1
    best_state = None
    for epoch in range(1, epochs + 1):
        loss = train(model, data, optimizer, class_weights, device)
        if epoch % 10 == 0 or epoch == epochs:
            # Model SELECTION happens on VAL only - test set is never peeked at here.
            y_val, s_val = evaluate(model, data, data.val_mask)
            if len(np.unique(y_val)) > 1:
                m_val = compute_metrics(y_val, s_val, model_type.upper())
                print(f"Epoch {epoch:3d} | loss {loss:.4f} | "
                      f"VAL PR-AUC {m_val['pr_auc']:.4f} | VAL ROC-AUC {m_val['roc_auc']:.4f} | "
                      f"VAL F1 {m_val['f1_at_0.5']:.4f}")
                if m_val["pr_auc"] > best_val_pr_auc:
                    best_val_pr_auc = m_val["pr_auc"]
                    best_state = {k: v.clone() for k, v in model.state_dict().items()}

    if best_state is not None:
        model.load_state_dict(best_state)

    # Test set touched EXACTLY ONCE, after the checkpoint is already frozen.
    y_true, y_scores = evaluate(model, data, data.test_mask)
    final_metrics = compute_metrics(y_true, y_scores, f"{model_type.upper()} (val-selected checkpoint)")
    final_metrics["best_val_pr_auc"] = round(best_val_pr_auc, 4)
    final_metrics["n_train"] = int(data.train_mask.sum())
    final_metrics["n_val"] = int(data.val_mask.sum())
    final_metrics["n_test"] = int(data.test_mask.sum())
    print("\nFINAL (test set, evaluated once):", json.dumps(final_metrics, indent=2))
    print(classification_report(y_true, (y_scores >= 0.5).astype(int),
                                 target_names=["licit", "illicit"], zero_division=0))

    with open(os.path.join(OUT_DIR, f"{model_type}_metrics.json"), "w") as f:
        json.dump(final_metrics, f, indent=2)
    torch.save(model.state_dict(), os.path.join(MODEL_DIR, f"{model_type}.pt"))

    # Save embeddings for ALL nodes (used by train_hybrid.py) - inference mode,
    # no dropout, single forward pass over the whole graph.
    model.eval()
    with torch.no_grad():
        _, emb = model(data.x, data.edge_index, return_embedding=True)
    np.save(os.path.join(OUT_DIR, f"{model_type}_embeddings.npy"), emb.cpu().numpy())
    print(f"Saved node embeddings: {emb.shape} -> outputs/{model_type}_embeddings.npy")

    return final_metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=["gcn", "gat"], default="gcn")
    parser.add_argument("--epochs", type=int, default=150)
    parser.add_argument("--lr", type=float, default=0.01)
    parser.add_argument("--hidden", type=int, default=64)
    args = parser.parse_args()
    run(model_type=args.model, epochs=args.epochs, lr=args.lr, hidden=args.hidden)
