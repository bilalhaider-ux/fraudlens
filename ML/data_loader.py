"""
FraudLens - Data Loader
========================
Loads the Elliptic Bitcoin Dataset as a PyTorch Geometric graph.

Tries, in order:
  1. The official PyG auto-download (torch_geometric.datasets.EllipticBitcoinDataset)
  2. Manually-placed Kaggle CSVs in data/elliptic_raw/

Label convention (matches the official PyG loader):
  y = 0  -> licit
  y = 1  -> illicit
  y = 2  -> unknown / unlabeled

data.train_mask / data.test_mask follow the paper's temporal split:
  train: time_step 1-34 (labeled only)
  test:  time_step 35-49 (labeled only)

MANUAL SETUP (if the auto-download fails, e.g. data.pyg.org is unreachable):
  1. Go to: https://www.kaggle.com/datasets/ellipticco/elliptic-data-set
     (or run: kaggle datasets download -d ellipticco/elliptic-data-set)
  2. Unzip into: data/elliptic_raw/
     You should end up with these three files directly inside that folder:
       - elliptic_txs_features.csv
       - elliptic_txs_classes.csv
       - elliptic_txs_edgelist.csv
  3. Re-run this script / your training script - it will pick them up automatically.
"""
import os
import torch
import pandas as pd
from torch_geometric.data import Data

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "elliptic_raw")
PYG_ROOT = os.path.join(os.path.dirname(__file__), "..", "data", "elliptic_pyg")


def _load_via_pyg():
    from torch_geometric.datasets import EllipticBitcoinDataset
    dataset = EllipticBitcoinDataset(root=PYG_ROOT)
    data = dataset[0]
    print(f"[data_loader] Loaded via official PyG downloader. "
          f"nodes={data.num_nodes}, edges={data.num_edges}")

    # The official loader gives train_mask/test_mask but drops time_step.
    # Re-read it from the already-downloaded raw CSV (same row order as node
    # index, since the loader builds node indices directly from that file's
    # row order) so we can carve a validation split out of TRAIN only,
    # without ever touching how test_mask was defined.
    raw_feat_path = os.path.join(PYG_ROOT, "raw", "elliptic_txs_features.csv")
    if os.path.exists(raw_feat_path):
        time_step_col = pd.read_csv(raw_feat_path, header=None, usecols=[1])
        data.time_step = torch.from_numpy(time_step_col[1].values.copy())
    else:
        print("[data_loader] Warning: raw feature CSV not found for time_step "
              "reconstruction; train/val split by time will be unavailable.")
    return data


def _load_via_manual_csv():
    feat_path = os.path.join(RAW_DIR, "elliptic_txs_features.csv")
    class_path = os.path.join(RAW_DIR, "elliptic_txs_classes.csv")
    edge_path = os.path.join(RAW_DIR, "elliptic_txs_edgelist.csv")

    for p in (feat_path, class_path, edge_path):
        if not os.path.exists(p):
            raise FileNotFoundError(
                f"[data_loader] Missing {p}.\n"
                "See the MANUAL SETUP instructions at the top of src/data_loader.py."
            )

    feat_df = pd.read_csv(feat_path, header=None)
    edge_df = pd.read_csv(edge_path)
    class_df = pd.read_csv(class_path)

    feat_df = feat_df.rename(columns={0: "txId", 1: "time_step"})

    x = torch.from_numpy(feat_df.loc[:, 2:].values).to(torch.float)

    # Same convention as the official PyG loader: 0=licit, 1=illicit, 2=unknown
    mapping = {"unknown": 2, "1": 1, "2": 0}
    class_df["class"] = class_df["class"].astype(str).map(mapping)
    y = torch.from_numpy(class_df["class"].values.copy())

    id_map = {tx: i for i, tx in enumerate(feat_df["txId"].values)}
    edge_df["txId1"] = edge_df["txId1"].map(id_map)
    edge_df["txId2"] = edge_df["txId2"].map(id_map)
    edge_index = torch.from_numpy(edge_df.values).t().contiguous()

    time_step = torch.from_numpy(feat_df["time_step"].values.copy())
    train_mask = (time_step < 35) & (y != 2)
    test_mask = (time_step >= 35) & (y != 2)

    data = Data(x=x, edge_index=edge_index, y=y,
                train_mask=train_mask, test_mask=test_mask)
    data.time_step = time_step  # kept (unlike official loader) for demo/visualization use
    print(f"[data_loader] Loaded via manual CSVs. "
          f"nodes={data.num_nodes}, edges={data.num_edges}")
    return data


def add_train_val_split(data, val_start=30, test_start=35):
    """
    Splits the paper's original TRAIN region (time_step < test_start) into a
    smaller train set and a validation set, purely for honest model/checkpoint
    selection. data.test_mask (time_step >= test_start) is NEVER touched here -
    it must only be evaluated once, at the very end.

        train: time_step 1..(val_start-1)
        val:   time_step val_start..(test_start-1)
        test:  time_step test_start..49   (unchanged, from the original loader)

    Requires data.time_step to be present (see _load_via_pyg / _load_via_manual_csv).
    """
    if not hasattr(data, "time_step"):
        raise AttributeError(
            "data.time_step is not available, cannot build a val split. "
            "This should not happen - check data_loader for both load paths."
        )
    labeled = data.y != 2
    ts = data.time_step
    data.train_mask = labeled & (ts < val_start)
    data.val_mask = labeled & (ts >= val_start) & (ts < test_start)
    # data.test_mask left as-is (already time_step >= test_start, labeled)
    return data


def load_elliptic():
    """Returns a torch_geometric.data.Data object with x, edge_index, y, train_mask, test_mask."""
    try:
        return _load_via_pyg()
    except Exception as e:
        print(f"[data_loader] Official PyG download failed ({type(e).__name__}: {e}). "
              f"Trying manual CSVs...")
        return _load_via_manual_csv()


if __name__ == "__main__":
    data = load_elliptic()
    print(data)
    print(f"Train labeled nodes: {int(data.train_mask.sum())}, "
          f"Test labeled nodes: {int(data.test_mask.sum())}")
    illicit_frac_train = (data.y[data.train_mask] == 1).float().mean().item()
    illicit_frac_test = (data.y[data.test_mask] == 1).float().mean().item()
    print(f"Illicit fraction — train: {illicit_frac_train:.3%}, test: {illicit_frac_test:.3%}")
