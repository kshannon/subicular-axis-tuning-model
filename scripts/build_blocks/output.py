"""
Write a build: one parquet per block, the csv tables, the manifest and checks in its own BLOCK_DATA folder, plus the committed registry row and protocol snapshot in docs/datasets_reference/.
"""

import csv
import hashlib
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

BLOCKS_FIELDS = ("block_id", "session_id", "subject_id", "protocol", "environment", "epoch", "frame_start", "frame_end",
                  "n_frames", "duration_s", "rate_hz", "n_runs", "n_clean_runs", "n_trips", "n_complete_trips",
                  "heading_lost_s", "heading_filled_s", "heading_held_s", "scale_px_per_m", "rotation_rad",
                  "maze_deg_measured", "verdict")
SESSIONS_FIELDS = ("session_id", "subject_id", "protocol", "rate_hz", "n_blocks", "verdict")
CUTS_FIELDS = ("session_id", "epoch", "block", "margin", "gap", "dropped")
REGISTRY_FIELDS = ("name", "timestamp", "commit", "description", "n_sessions", "n_blocks", "content_hash")


def write_csv_rows(rows, fields, path):
    """
    rows written as a CSV with this header, creating the parent folders. An empty table still gets the header.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_block_parquet(columns, path):
    """
    A block's per-frame arrays as a Parquet file, creating the parent folders.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.table({name: list(values) for name, values in columns.items()}), path)


def write_json(obj, path):
    """
    obj as sorted, indented json with a trailing newline, creating the parent folders.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, default=str) + "\n")


def content_hash(blocks_csv_path, parquet_paths):
    """
    sha256 over blocks.csv then every block parquet, in path order: the dataset's fingerprint.
    """
    digest = hashlib.sha256()
    digest.update(blocks_csv_path.read_bytes())
    for path in sorted(parquet_paths):
        digest.update(path.read_bytes())
    return digest.hexdigest()


def write_dataset_reference(repo_root, run_name, protocol_text, registry_row):
    """
    The committed docs/datasets_reference/: a verbatim snapshot of build_protocol.yaml named after this run, and its row appended to datasets.csv (written fresh with a header the first time).
    """
    reference_dir = repo_root / "docs" / "datasets_reference"
    reference_dir.mkdir(parents=True, exist_ok=True)
    (reference_dir / f"{run_name}.yaml").write_text(protocol_text)
    registry_path = reference_dir / "datasets.csv"
    is_new = not registry_path.is_file()
    with open(registry_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=REGISTRY_FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerow(registry_row)
