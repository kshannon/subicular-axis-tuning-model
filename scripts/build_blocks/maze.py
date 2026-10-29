"""
The paper's apparatus as plain data: the triple-T's outbound centreline and reward sites, the arena's extent. No walls, no returns, no config file.
"""

import numpy as np

# Olson, Tongprasearth and Nitz (2017): the room frame, the track's envelope and corridor width, the four run
# segments (turns at 0.51, 0.87 and 1.18 m of a 1.40 m total), the arena's diameter placed above the track centre.
ROOM = (1.8, 1.8)
CORRIDOR_WIDTH = 0.08
ENVELOPE = (1.60, 1.25)
RUN_SEGMENTS = (0.51, 0.36, 0.31, 0.22)
ARENA_DIAMETER = 0.6

# The package's shared vocabulary, defined once here since every other module either imports maze or sits below
# it: the three epoch kinds, the lab's outbound and return path ids, and the nominal rotation a tag promises.
TRACK, ARENA, VARIANT = "track", "arena", "variant"
OUTBOUND_PATHS = (1, 2, 3, 4)
RETURN_PATHS = (9, 10)
NOMINAL_ROTATION_DEG = {"rot45": 45.0, "rot90": 90.0}


def _centerline_and_sites():
    """
    The outbound centreline segments and the reward sites (start plus the four goals), built once from the constants above.
    """
    w = CORRIDOR_WIDTH
    l1, l2, l3, l4 = RUN_SEGMENTS
    ex, ey = ENVELOPE
    cx = ROOM[0] / 2.0
    x0, y0 = (ROOM[0] - ex) / 2.0, (ROOM[1] - ey) / 2.0
    start = (cx, y0 + w / 2.0)
    t1 = (cx, start[1] + l1)
    ce, cw = (cx + l2, t1[1]), (cx - l2, t1[1])
    ue, uw = (ce[0], t1[1] + l3), (cw[0], t1[1] + l3)
    goals = {
        "g_ee": (ce[0] + l4, ue[1]), "g_ew": (ce[0] - l4, ue[1]),
        "g_ww": (cw[0] - l4, ue[1]), "g_we": (cw[0] + l4, ue[1]),
    }
    centerline = [
        {"p0": start, "p1": t1}, {"p0": t1, "p1": ce}, {"p0": t1, "p1": cw},
        {"p0": ce, "p1": ue}, {"p0": cw, "p1": uw},
        {"p0": ue, "p1": goals["g_ee"]}, {"p0": ue, "p1": goals["g_ew"]},
        {"p0": uw, "p1": goals["g_ww"]}, {"p0": uw, "p1": goals["g_we"]},
    ]
    return centerline, {"start": start, **goals}


CENTERLINE, REWARD_SITES = _centerline_and_sites()
GOAL_NAMES = ("g_ee", "g_ew", "g_ww", "g_we")


def centerline_extent():
    """
    The (x, y) extent in metres of the outbound centreline's bounding box, what the track scale is measured against.
    """
    xs = [p[0] for seg in CENTERLINE for p in (seg["p0"], seg["p1"])]
    ys = [p[1] for seg in CENTERLINE for p in (seg["p0"], seg["p1"])]
    return max(xs) - min(xs), max(ys) - min(ys)


def distance_to_centerline(x, y):
    """
    Each point's distance in metres to the nearest outbound centreline segment, the "share of running time actually on the track" check's input.
    """
    best = np.full(len(x), np.inf)
    for seg in CENTERLINE:
        (x0, y0), (x1, y1) = seg["p0"], seg["p1"]
        dx, dy = x1 - x0, y1 - y0
        length_sq = dx * dx + dy * dy
        t = np.clip(((x - x0) * dx + (y - y0) * dy) / length_sq, 0.0, 1.0)
        near_x, near_y = x0 + t * dx, y0 + t * dy
        best = np.minimum(best, np.hypot(x - near_x, y - near_y))
    return best
