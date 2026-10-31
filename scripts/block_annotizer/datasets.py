"""
Find and read a block dataset: the dataset folders under BLOCK_DATA, a dataset's csv and json files, one block's frames, and the environment vocabulary of blocks.csv.
"""

import csv
import json
import sys
from collections import Counter

import pandas as pd

# The transformer's vocabulary for the environment column of blocks.csv.
ARENA_ENVIRONMENT = "open_arena"
ENVIRONMENT_WORDS = {ARENA_ENVIRONMENT: "open arena", "triple_t": "triple T", "triple_t_rot45": "triple T rotated 45",
                     "triple_t_rot90": "triple T rotated 90"}
ENVIRONMENT_ROTATION_DEG = {"triple_t_rot45": 45.0, "triple_t_rot90": 90.0}


def refuse(message):
    """
    Print a configuration problem to stderr and exit 2.
    """
    print(f"block_annotizer: {message}", file=sys.stderr)
    raise SystemExit(2)


def read_csv_rows(path):
    """
    A csv file as a list of dicts of strings.
    """
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def read_json(path):
    """
    A json file as a dict, empty when absent.
    """
    return json.loads(path.read_text()) if path.is_file() else {}


def datasets(root):
    """
    The dataset folders under root, newest first by name.
    """
    return sorted((p for p in root.iterdir() if (p / "blocks.csv").is_file()), key=lambda p: p.name, reverse=True)


def pick_dataset(root, name):
    """
    The one dataset folder named name or starting with it, or exit 2 listing what is there.
    """
    found = datasets(root)
    matches = [p for p in found if p.name == name] or [p for p in found if p.name.startswith(name)]
    if len(matches) != 1:
        refuse(f"{name!r} matches {len(matches)} datasets, have: " + ", ".join(p.name for p in found))
    return matches[0]


def environment_counts(blocks):
    """
    The blocks per environment as one line of text.
    """
    counts = Counter(row["environment"] for row in blocks)
    return "  ".join(f"{env} {n}" for env, n in sorted(counts.items()))


def list_datasets(root):
    """
    Print every dataset under root with its block counts.
    """
    found = datasets(root)
    if not found:
        print(f"no datasets under {root}")
    for path in found:
        blocks = read_csv_rows(path / "blocks.csv")
        print(f"{path.name}  {len(blocks)} blocks  {environment_counts(blocks)}")


def read_block(run_root, block_id):
    """
    One block's frames as a DataFrame.
    """
    return pd.read_parquet(run_root / "frames" / f"{block_id}.parquet")
