"""
Build a dataset: load the transformed tables, build every selected session, write the BLOCK_DATA folder and the committed datasets reference.
"""

import csv
import json
import subprocess
from datetime import datetime, timezone

import numpy as np
import pyarrow.parquet as pq

from . import checks, labels, maze, output, select
from .cut import cut_epoch, epoch_index, frame_counts, in_ranges, initial_blocks, pauses
from .motion import fill, fill_spans, kinematics, led_offset, still
from .output import BLOCKS_FIELDS, CUTS_FIELDS, SESSIONS_FIELDS
from .maze import VARIANT
from .register import ARENA, TRACK, heading_to_room, moving, parameters, to_metres, variant_parameters

FRAME_COLUMNS = ("frame", "t", "front_x", "front_y", "back_x", "back_y", "head_dir", "avg_x", "avg_y",
                  "mashup_x", "mashup_y", "filled_front", "filled_back", "unfilled_front", "unfilled_back")


def read_csv_rows(path):
    """
    A CSV table's rows as a list of plain string dicts.
    """
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def _int(value):
    return None if value in (None, "") else int(value)


def _bool(value):
    return value == "true"


def typed_sessions(rows):
    """
    sessions.csv rows with rate_hz as an int, everything else left as the string the csv holds.
    """
    return [{**row, "rate_hz": int(row["rate_hz"])} for row in rows]


def typed_epochs(rows):
    """
    epochs.csv rows with frame_start and frame_end as ints.
    """
    return [{**row, "frame_start": int(row["frame_start"]), "frame_end": int(row["frame_end"])} for row in rows]


def typed_runs(rows):
    """
    runs.csv rows with the frame, run and path_id columns as ints, duplicate_of as an int or None, clean as a bool.
    """
    return [{**row, "run": int(row["run"]), "path_id": int(row["path_id"]), "frame_start": int(row["frame_start"]),
             "frame_end": int(row["frame_end"]), "duplicate_of": _int(row["duplicate_of"]), "clean": _bool(row["clean"])}
            for row in rows]


def read_frames(path):
    """
    A session's frames parquet as a dict of numpy arrays, only the columns build_blocks needs.
    """
    table = pq.read_table(path, columns=list(FRAME_COLUMNS))
    return {name: table.column(name).to_numpy(zero_copy_only=False) for name in FRAME_COLUMNS}


def load_tables(root):
    """
    The whole TRANSFORMED_LAB_DATA tables, typed, grouped by session_id.
    """
    sessions = typed_sessions(read_csv_rows(root / "sessions.csv"))
    epochs = typed_epochs(read_csv_rows(root / "epochs.csv"))
    runs = typed_runs(read_csv_rows(root / "runs.csv"))
    epochs_by_session, runs_by_session = {}, {}
    for row in epochs:
        epochs_by_session.setdefault(row["session_id"], []).append(row)
    for row in runs:
        runs_by_session.setdefault(row["session_id"], []).append(row)
    return sessions, epochs_by_session, runs_by_session


def block_slice(frame, block):
    """
    The index slice of the block's frames in the session's contiguous frame array.
    """
    first = int(np.searchsorted(frame, block["frame_start"]))
    return slice(first, first + block["frame_end"] - block["frame_start"] + 1)


def in_spans(frame, spans):
    """
    True on the frames inside any of the spans' first and last frames.
    """
    return in_ranges(frame, [(span["first"], span["last"]) for span in spans])


def block_columns(frames, x, y, heading, speed, turn_rate, heading_spans, at, kind, runs, rate_hz):
    """
    A block's arrays over its slice: t from the block start, position and heading in the room, speed and turn rate, the heading fill flags, and the run labels.
    """
    frame, t = frames["frame"][at], frames["t"][at]
    return {"frame": frame.astype(np.int32), "t": t - t[0], "x": x[at], "y": y[at], "heading": heading[at],
            "speed": speed[at], "turn_rate": turn_rate[at],
            "heading_filled": in_spans(frame, heading_spans["filled"]), "heading_held": in_spans(frame, heading_spans["held"]),
            **labels.label_frames(frame, speed[at], kind, runs, rate_hz)}


def block_row(block, columns, session_row, registration_entry, rate_hz):
    """
    A block's row of blocks.csv: the block and its session, its runs and trips, the seconds of heading lost, filled and held, and the registration it was built under.
    """
    run, trip, clean = columns["run"], columns["trip"], columns["clean"]
    n_frames = len(columns["frame"])
    return {
        "block_id": block["block_id"], "session_id": session_row["session_id"], "subject_id": session_row["subject_id"],
        "protocol": session_row["protocol"], "environment": block["environment"], "epoch": block["epoch"],
        "frame_start": block["frame_start"], "frame_end": block["frame_end"], "n_frames": n_frames,
        "duration_s": n_frames / rate_hz, "rate_hz": rate_hz,
        "n_runs": len(np.unique(run[run > 0])), "n_clean_runs": len(np.unique(run[(run > 0) & clean])),
        "n_trips": len(np.unique(np.abs(trip[trip != 0]))), "n_complete_trips": len(np.unique(trip[trip > 0])),
        "heading_lost_s": float(np.isnan(columns["heading"]).sum() / rate_hz),
        "heading_filled_s": float(columns["heading_filled"].sum() / rate_hz),
        "heading_held_s": float(columns["heading_held"].sum() / rate_hz),
        "scale_px_per_m": registration_entry["scale_px_per_m"], "rotation_rad": registration_entry["rotation_rad"],
        "maze_deg_measured": registration_entry.get("maze_deg_measured"), "verdict": "ok",
    }


def commit_hash(repo_root):
    """
    The repository's current commit hash, or "unknown" when git is unavailable.
    """
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_root, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def input_manifest_timestamp(transformed_root):
    """
    TRANSFORMED_LAB_DATA's own manifest.json run timestamp, or None when there is none.
    """
    path = transformed_root / "manifest.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text()).get("run", {}).get("timestamp")


def build_session(session_row, epochs, runs, frames, protocol):
    """
    A session's kept blocks (each a row and arrays) and its registration and checks, or None with a reason when it cannot be registered or its blocks overlap.
    """
    rate_hz = session_row["rate_hz"]
    selected_epochs = select.select_epochs(epochs)
    track_epoch = next((e for e in selected_epochs if e["epoch"] == TRACK), None)
    if track_epoch is None:
        return None, {"reason": "no track epoch selected"}
    baseline = [e for e in selected_epochs if e["epoch"] in (TRACK, ARENA)]
    variant_epoch = next((e for e in selected_epochs if e["epoch"] == VARIANT), None)

    registration = parameters(frames, baseline, runs)
    if variant_epoch is not None:
        registration[VARIANT] = variant_parameters(frames, variant_epoch, runs, registration[TRACK])

    offset_rad, _, _ = led_offset(frames)
    rotation = registration[TRACK]["rotation_rad"]
    x, y = to_metres(frames, selected_epochs, registration)
    still_frames = still(frames, selected_epochs)
    filled_heading, fills = fill(frames["head_dir"], frames["t"], still_frames, rate_hz, protocol["pause_step_s"])
    heading = heading_to_room(filled_heading, offset_rad, rotation)
    epoch_idx = epoch_index(frames, selected_epochs)
    breaks = pauses(frames["t"], protocol["pause_step_s"]) | np.concatenate(([False], np.diff(epoch_idx) != 0))
    speed, motion_direction, turn_rate = kinematics(x, y, heading, breaks, rate_hz)
    heading_spans = fill_spans(frames["frame"], fills, rate_hz)

    session_checks = {kind: checks.registration_warnings(registration[kind], kind) for kind in (e["epoch"] for e in baseline)}
    session_checks["heading"] = checks.heading_offset_warning(offset_rad)
    session_checks["on_track"] = checks.on_track_warning(x, y, moving(frames, track_epoch))

    blocks, cut_counts, skipped = [], {}, []
    for epoch in selected_epochs:
        kind = epoch["epoch"]
        pieces, margins = cut_epoch(frames, epoch, protocol["max_gap_frames"], rate_hz, protocol["pause_step_s"], protocol["jump_px"])
        epoch_blocks = initial_blocks(session_row["session_id"], epoch, pieces, rate_hz, protocol["min_block_s"])
        cut_counts[kind] = frame_counts(frames, epoch, margins, epoch_blocks, protocol["max_gap_frames"])
        for block in epoch_blocks:
            at = block_slice(frames["frame"], block)
            columns = block_columns(frames, x, y, heading, speed, turn_rate, heading_spans, at, kind, runs, rate_hz)
            fail_results = checks.block_fails(columns, rate_hz)
            if checks.failed(fail_results):
                skipped.append({"block_id": block["block_id"], "reason": checks.failed(fail_results)})
                continue
            if kind == VARIANT:
                mismatch, detail = checks.rotation_mismatch_fail(registration[VARIANT]["maze_deg_measured"], maze.NOMINAL_ROTATION_DEG[epoch["condition"]])
                if mismatch:
                    skipped.append({"block_id": block["block_id"], "reason": ["rotation_mismatch"], "detail": detail})
                    continue
            blocks.append({"row": block_row(block, columns, session_row, registration[kind], rate_hz), "columns": columns})

    overlap, overlap_detail = checks.overlapping_blocks([b["row"] for b in blocks])
    if overlap:
        return None, {"reason": "overlapping blocks", "detail": overlap_detail}

    return blocks, {"registration": registration, "checks": session_checks, "cut_counts": cut_counts, "skipped_blocks": skipped}


def build_dataset(transformed_root, block_data_root, description, protocol_path, repo_root,
                   sessions, epochs_by_session, runs_by_session, protocol):
    """
    Build every selected session, write its own timestamped BLOCK_DATA folder and the committed datasets reference, and return the run name and its manifest.
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    run_name = f"{timestamp}_{description}"
    run_root = block_data_root / run_name

    blocks_rows, sessions_rows, cuts_rows, checks_by_session, failed = [], [], [], {}, {}
    for session_row in sessions:
        session_id = session_row["session_id"]
        epochs, runs = epochs_by_session.get(session_id, []), runs_by_session.get(session_id, [])
        frames = read_frames(transformed_root / "frames" / f"{session_id}.parquet")
        blocks, info = build_session(session_row, epochs, runs, frames, protocol)
        if blocks is None:
            failed[session_id] = info["reason"]
            continue
        checks_by_session[session_id] = {"warnings": info["checks"], "cut_counts": info["cut_counts"],
                                          "skipped_blocks": info["skipped_blocks"], "registration": info["registration"]}
        for epoch_name, counts in info["cut_counts"].items():
            cuts_rows.append({"session_id": session_id, "epoch": epoch_name, **counts})
        for block in blocks:
            blocks_rows.append(block["row"])
            output.write_block_parquet(block["columns"], run_root / "frames" / f"{block['row']['block_id']}.parquet")
        sessions_rows.append({"session_id": session_id, "subject_id": session_row["subject_id"],
                              "protocol": session_row["protocol"], "rate_hz": session_row["rate_hz"],
                              "n_blocks": len(blocks), "verdict": "ok"})

    output.write_csv_rows(blocks_rows, BLOCKS_FIELDS, run_root / "blocks.csv")
    output.write_csv_rows(sessions_rows, SESSIONS_FIELDS, run_root / "sessions.csv")
    output.write_csv_rows(cuts_rows, CUTS_FIELDS, run_root / "cuts.csv")
    output.write_json(checks_by_session, run_root / "checks.json")

    parquet_paths = list((run_root / "frames").glob("*.parquet")) if blocks_rows else []
    fingerprint = output.content_hash(run_root / "blocks.csv", parquet_paths)
    manifest = {
        "run_name": run_name, "git_commit": commit_hash(repo_root), "protocol": {**protocol, "conditions": list(protocol["conditions"])},
        "input_manifest_timestamp": input_manifest_timestamp(transformed_root),
        "counts": {"sessions_selected": len(sessions), "sessions_built": len(sessions_rows), "sessions_failed": len(failed),
                   "blocks_written": len(blocks_rows)},
        "failed": failed, "content_hash": fingerprint,
    }
    output.write_json(manifest, run_root / "manifest.json")

    registry_row = {"name": run_name, "timestamp": timestamp, "commit": manifest["git_commit"], "description": description,
                    "n_sessions": len(sessions_rows), "n_blocks": len(blocks_rows), "content_hash": fingerprint}
    output.write_dataset_reference(repo_root, run_name, protocol_path.read_text(), registry_row)
    return run_name, manifest
