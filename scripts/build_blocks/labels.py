"""
The labels of a block's frames: run, path_id and clean from the lab's runs, then phase and trip from the runs, the speed and the block's kind. Ported from axis-of-travel-rnn's blocks/labels.py.
"""

import numpy as np

from .cut import runs_of
from .maze import ARENA, OUTBOUND_PATHS, RETURN_PATHS
from .motion import RUNNING_FLOOR_M_PER_S

PHASES = ("outbound", "dwell", "return", "pause", "forage")
OUTBOUND, DWELL, RETURN, PAUSE, FORAGE = PHASES
PHASE_DTYPE = "U8"
DTYPES = {"run": np.int32, "path_id": np.int16, "clean": bool, "trip": np.int32}

# Not exposed in build_protocol.yaml: how slow and how long inside a run counts as a pause (the animal is
# tracked normally throughout, this is a label, never a cut).
PAUSE_MIN_S = 1.0


def runs_in(frame, runs):
    """
    The runs touching the block's frames, duplicates skipped, in start order.
    """
    first, last = frame[0], frame[-1]
    inside = [r for r in runs if r["duplicate_of"] is None and r["frame_start"] <= last and r["frame_end"] >= first]
    return sorted(inside, key=lambda r: r["frame_start"])


def painted(frame, runs, key):
    """
    One run field per frame, 0 outside any run, a later run overwriting an earlier one where they overlap.
    """
    values = np.zeros(len(frame), DTYPES[key])
    for r in runs:
        values[(frame >= r["frame_start"]) & (frame <= r["frame_end"])] = r[key]
    return values


def paused_frames(run, speed, rate_hz):
    """
    True on every frame of a stretch inside one run with speed under RUNNING_FLOOR_M_PER_S for over PAUSE_MIN_S.
    """
    paused, slow = np.zeros(len(run), bool), speed < RUNNING_FLOOR_M_PER_S
    for number in np.unique(run[run > 0]):
        for first, stop in runs_of(slow & (run == number)):
            if stop - first > PAUSE_MIN_S * rate_hz:
                paused[first:stop] = True
    return paused


def phases(run, path_id, paused, forage):
    """
    The phase per frame: outbound or return inside a run by its path, pause over a slow stretch inside a run, forage in the arena, dwell elsewhere (at a reward site, or between runs). Dwells are a label, never a cut: the animal is tracked normally while it eats.
    """
    phase = np.full(len(run), DWELL, PHASE_DTYPE)
    phase[(run > 0) & np.isin(path_id, OUTBOUND_PATHS)] = OUTBOUND
    phase[(run > 0) & np.isin(path_id, RETURN_PATHS)] = RETURN
    phase[paused] = PAUSE
    phase[forage] = FORAGE
    return phase


def returned(start, next_start, runs, last):
    """
    Whether the trip opening at this outbound start has a return run starting before the next outbound start and ending by the block's last frame.
    """
    return any(r["path_id"] in RETURN_PATHS and start < r["frame_start"] < next_start and r["frame_end"] <= last for r in runs)


def trips(frame, runs, forage):
    """
    The trip per frame, counted through the block from each outbound start to the next, negative unless its outbound and return runs both lie inside the block, 0 in the arena.
    """
    starts = [r["frame_start"] for r in runs if r["path_id"] in OUTBOUND_PATHS and r["frame_start"] >= frame[0]]
    leading = int(not starts or starts[0] > frame[0])
    number = np.searchsorted(starts, frame, side="right") + leading
    complete = [False] * leading + [returned(start, next_start, runs, frame[-1]) for start, next_start in zip(starts, starts[1:] + [np.inf])]
    trip = np.where(np.array(complete)[number - 1], number, -number).astype(DTYPES["trip"])
    trip[forage] = 0
    return trip


def label_frames(frame, speed, kind, runs, rate_hz):
    """
    The labels over the block's frames, their speed in m/s and the block's kind, as a dict of arrays: phase, trip, run, path_id and clean.
    """
    forage = np.full(len(frame), kind == ARENA)
    inside = runs_in(frame, runs)
    run, path_id = painted(frame, inside, "run"), painted(frame, inside, "path_id")
    return {"phase": phases(run, path_id, paused_frames(run, speed, rate_hz), forage), "trip": trips(frame, inside, forage),
            "run": run, "path_id": path_id, "clean": painted(frame, inside, "clean")}
