"""
Pass, warn or fail: block level checks that gate whether a block is written, and session level checks that are written alongside regardless. Same add_result shape as transform_lab_data's checks.py.
"""

import numpy as np

from . import maze
from .maze import ARENA, TRACK

# Fail thresholds: a block with these problems is not written.
T_STEP_TOLERANCE_S = 1e-6
ROTATION_MISMATCH_DEG = 10.0  # a variant epoch's measured rotation this far from its tag, see the design docs

# Warn thresholds. axis_agree and led_separation_m come from axis-of-travel-rnn's own already-debugged checks.
# concentration_min, on_track_fraction_min and on_track_tolerance_m are new for this redesign (the viz checker's
# "share of running time actually on the track" panel) and are not calibrated against real data yet, a judgment
# call pending the EDA notebook's first real builds. heading_offset_warn_deg is simplified to "near zero" rather
# than axis-of-travel-rnn's per-rat-median comparison, also a judgment call worth revisiting.
AXIS_AGREE = 0.05
LED_SEPARATION_M = (0.04, 0.08)
CONCENTRATION_MIN = 0.5
HEADING_OFFSET_WARN_DEG = 10.0
ON_TRACK_FRACTION_MIN = 0.5
ON_TRACK_TOLERANCE_M = 0.15
ARENA_EXTENT_RATIO = (0.8, 1.2)


def add_result(results, name, status, detail):
    """
    Add one check's status (pass, warn or fail) and its detail dict to the results.
    """
    results[name] = {"status": status, "detail": detail}


def failed(results):
    """
    The sorted names of the checks that failed.
    """
    return sorted(name for name, result in results.items() if result["status"] == "fail")


def warnings(results):
    """
    The sorted names of the checks that warned.
    """
    return sorted(name for name, result in results.items() if result["status"] == "warn")


def block_fails(columns, rate_hz):
    """
    A block's fail checks: NaN position on a kept frame, an irregular time step. Either means the block is not written.
    """
    results = {}
    missing = int((np.isnan(columns["x"]) | np.isnan(columns["y"])).sum())
    add_result(results, "position_finite", "fail" if missing else "pass", {"n_missing": missing})
    irregular = int((np.abs(np.diff(columns["t"]) - 1 / rate_hz) > T_STEP_TOLERANCE_S).sum())
    add_result(results, "t_step_regular", "fail" if irregular else "pass", {"n_irregular": irregular})
    return results


def overlapping_blocks(blocks):
    """
    Any pair of a session's kept blocks whose frame ranges overlap, a sign of a cutting bug: the whole session is not written when this fails.
    """
    pairs = []
    ordered = sorted(blocks, key=lambda b: b["frame_start"])
    for a, b in zip(ordered, ordered[1:]):
        if b["frame_start"] <= a["frame_end"]:
            pairs.append((a["block_id"], b["block_id"]))
    return bool(pairs), {"pairs": pairs}


def registration_warnings(registration, kind):
    """
    One epoch's own registration warnings: track scale disagreement, LED separation out of range, low rotation concentration, and for the arena its extent ratio.
    """
    results = {}
    if kind == TRACK:
        apart = abs(registration["scale_x_px_per_m"] - registration["scale_y_px_per_m"]) / registration["scale_px_per_m"]
        add_result(results, "axes_agree", "warn" if apart > AXIS_AGREE else "pass", {"fraction_apart": apart})
    low, high = LED_SEPARATION_M
    separation = registration["led_separation_m"]
    add_result(results, "led_separation", "warn" if not low <= separation <= high else "pass", {"led_separation_m": separation})
    concentration = registration["rotation_concentration"]
    add_result(results, "rotation_concentration", "warn" if concentration < CONCENTRATION_MIN else "pass", {"concentration": concentration})
    if kind == ARENA:
        low, high = ARENA_EXTENT_RATIO
        ratio = registration["arena_extent_ratio"]
        add_result(results, "arena_extent_ratio", "warn" if not low <= ratio <= high else "pass", {"ratio": ratio})
    return results


def heading_offset_warning(offset_rad):
    """
    Whether the session's LED offset sits more than HEADING_OFFSET_WARN_DEG from zero.
    """
    results = {}
    degrees = abs(np.degrees(offset_rad))
    add_result(results, "heading_offset", "warn" if degrees > HEADING_OFFSET_WARN_DEG else "pass", {"offset_deg": float(degrees)})
    return results


def on_track_warning(x, y, moving_mask):
    """
    Whether the share of a track epoch's running time within ON_TRACK_TOLERANCE_M of the centreline is under ON_TRACK_FRACTION_MIN.
    """
    if not moving_mask.any():
        fraction = 0.0
    else:
        distance = maze.distance_to_centerline(x[moving_mask], y[moving_mask])
        fraction = float(np.mean(distance <= ON_TRACK_TOLERANCE_M))
    results = {}
    add_result(results, "on_track_fraction", "warn" if fraction < ON_TRACK_FRACTION_MIN else "pass", {"fraction": fraction})
    return results


def rotation_mismatch_fail(maze_deg_measured, nominal_deg):
    """
    Whether a variant epoch's measured rotation sits more than ROTATION_MISMATCH_DEG from its tag. Expected to fire often until the camera field of view question is settled, see the design docs.
    """
    off = abs(maze_deg_measured - nominal_deg)
    return off > ROTATION_MISMATCH_DEG, {"nominal_deg": nominal_deg, "measured_deg": maze_deg_measured, "off_deg": off}
