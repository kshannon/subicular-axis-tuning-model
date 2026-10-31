"""
Step through a block dataset, mark stretches of frames and give each block a verdict, run as pixi run block-annotizer.
"""

import argparse
import sys
from pathlib import Path

import matplotlib
import yaml

from scripts.block_annotizer.annotator import KEYS, Annotator
from scripts.block_annotizer.datasets import (environment_counts, list_datasets, pick_dataset, read_csv_rows, read_json,
                                              refuse)
from scripts.block_annotizer.figures import summary
from scripts.block_annotizer.store import Store

REPO_ROOT = Path(__file__).resolve().parents[2]
LOCAL_CONFIG = REPO_ROOT / "configs" / "local.yaml"


def local_config():
    """
    The machine local paths of configs/local.yaml as a dict, empty when the file is absent.
    """
    if not LOCAL_CONFIG.is_file():
        return {}
    return yaml.safe_load(LOCAL_CONFIG.read_text()) or {}


def block_data_root(config):
    """
    The BLOCK_DATA folder named in the config, or exit 2.
    """
    if not config.get("BLOCK_DATA"):
        refuse("configs/local.yaml has no BLOCK_DATA")
    root = Path(str(config["BLOCK_DATA"])).expanduser()
    if not root.is_dir():
        refuse(f"BLOCK_DATA {root} is not a folder")
    return root


def parse_args(argv):
    """
    The command line: a dataset name or prefix, or none to list them, --summary for the pooled figures, --start BLOCK to open at a block.
    """
    parser = argparse.ArgumentParser(prog="block_annotizer",
                                     description="Step through a block dataset, mark stretches and give verdicts.")
    parser.add_argument("dataset", nargs="?", help="a dataset folder name under BLOCK_DATA or its prefix; omitted, list them")
    parser.add_argument("--summary", action="store_true",
                        help="save one pooled occupancy figure per environment under annotations/ and exit")
    parser.add_argument("--start", metavar="BLOCK", help="the block id, prefix or number to open first")
    return parser.parse_args(argv)


def start_index(blocks, start):
    """
    The index of the block named by start, or exit 2.
    """
    ids = [row["block_id"] for row in blocks]
    if start.isdigit() and 1 <= int(start) <= len(ids):
        return int(start) - 1
    hits = [i for i, b in enumerate(ids) if b == start or b.startswith(start)]
    if len(hits) != 1:
        refuse(f"--start {start!r} matches {len(hits)} blocks")
    return hits[0]


def main(argv=None, config=None):
    """
    List the datasets, or open one in the window, or write its summary figures. Returns 0, SystemExit 2 for a bad setup.
    """
    args = parse_args(argv)
    root = block_data_root(local_config() if config is None else config)
    if args.dataset is None:
        list_datasets(root)
        return 0
    run_root = pick_dataset(root, args.dataset)
    blocks = read_csv_rows(run_root / "blocks.csv")
    if not blocks:
        refuse(f"{run_root.name} has no blocks")
    manifest, checks = read_json(run_root / "manifest.json"), read_json(run_root / "checks.json")
    store = Store(run_root)
    if args.summary:
        matplotlib.use("Agg")
        summary(run_root, blocks, manifest, store)
        return 0
    print(f"dataset {run_root.name}: {len(blocks)} blocks  {environment_counts(blocks)}")
    print(f"annotations in {store.folder}")
    print(KEYS)
    annotator = Annotator(run_root, blocks, checks, manifest, store, start_index(blocks, args.start) if args.start else 0)
    annotator.plt.show()
    return 0


if __name__ == "__main__":
    sys.exit(main())
