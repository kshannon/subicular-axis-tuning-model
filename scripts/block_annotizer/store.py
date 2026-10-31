"""
The annotations folder of one dataset, written beside the data and never into it, since the manifest's content hash covers the dataset's own files.
"""

import csv
import getpass
import json
from datetime import datetime, timezone

from scripts.block_annotizer.datasets import read_csv_rows, read_json

ANNOTATIONS_DIR = "annotations"
ANNOTATIONS_CSV = "annotations.csv"   # one row per marked stretch of frames
NOTES_JSON = "notes.json"             # one entry per block looked at, keyed by block_id
NOTES_MD = "notes.md"                 # dated free text about the dataset as a whole
ANNOTATION_FIELDS = ("annotation_id", "block_id", "session_id", "environment", "frame_start", "frame_end",
                     "t_start", "t_end", "tag", "note", "author", "created")
VERDICTS = ("ok", "exclude", "unsure")


def now():
    """
    The current UTC time as an ISO string to the second.
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Store:
    """
    The annotations folder of one dataset: annotations.csv, notes.json and notes.md, each written on every change.
    """

    def __init__(self, run_root):
        self.folder = run_root / ANNOTATIONS_DIR
        self.folder.mkdir(exist_ok=True)
        self.csv_path = self.folder / ANNOTATIONS_CSV
        self.json_path = self.folder / NOTES_JSON
        self.md_path = self.folder / NOTES_MD
        self.annotations = read_csv_rows(self.csv_path) if self.csv_path.is_file() else []
        self.notes = read_json(self.json_path)
        self.author = getpass.getuser()
        if not self.md_path.is_file():
            self.md_path.write_text(f"# Notes on {run_root.name}\n\n")

    def for_block(self, block_id):
        """
        This block's annotations in the order they were made.
        """
        return [a for a in self.annotations if a["block_id"] == block_id]

    def add(self, row, frame_start, frame_end, t_start, t_end, tag, note):
        """
        Append one marked stretch for the block in row and write the csv.
        """
        numbers = [int(a["annotation_id"].rsplit("_a", 1)[1]) for a in self.for_block(row["block_id"])]
        annotation = {
            "annotation_id": f"{row['block_id']}_a{max(numbers, default=0) + 1:02d}", "block_id": row["block_id"],
            "session_id": row["session_id"], "environment": row["environment"],
            "frame_start": int(frame_start), "frame_end": int(frame_end), "t_start": f"{t_start:.3f}",
            "t_end": f"{t_end:.3f}", "tag": tag, "note": note, "author": self.author, "created": now()}
        self.annotations.append(annotation)
        self.write_csv()
        return annotation

    def drop_last(self, block_id):
        """
        Remove the block's most recent annotation and write the csv, returning it, or None when there is none.
        """
        mine = self.for_block(block_id)
        if not mine:
            return None
        self.annotations.remove(mine[-1])
        self.write_csv()
        return mine[-1]

    def write_csv(self):
        with open(self.csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=ANNOTATION_FIELDS)
            writer.writeheader()
            writer.writerows(self.annotations)

    def set_verdict(self, block_id, verdict, note):
        """
        Record the block's verdict and note and write notes.json.
        """
        self.notes[block_id] = {"verdict": verdict, "note": note, "author": self.author, "updated": now()}
        self.json_path.write_text(json.dumps(self.notes, indent=2, sort_keys=True) + "\n")

    def add_dataset_note(self, text):
        """
        Append a dated line to notes.md.
        """
        with open(self.md_path, "a") as f:
            f.write(f"- {now()} {self.author}: {text}\n")
