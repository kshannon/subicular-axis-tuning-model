"""
Synthetic frames and runs for register.py's tests: a rat running the maze's real outbound route, placed in pixels by the known inverse of register.to_room, so a test can assert the true rotation and scale come back out.
"""

import numpy as np

from scripts.build_blocks import maze
from scripts.build_blocks.register import rotated

OUTBOUND_PATH, RETURN_PATH = 1, 9


def to_pixels(x_room, y_room, scale, rotation, offset):
    """
    The inverse of register.to_room: room metres to camera pixels at this scale, rotation and offset.
    """
    xu, yu = rotated(x_room - offset[0], y_room - offset[1], -rotation)
    return xu * scale, -yu * scale


def _route_waypoints(side):
    """
    The real outbound route to one side's outer goal (start, the first T, the second junction, the goal), four segments, two of each axis. Alternating east and west trips covers the full centreline extent track_scale measures against, not just one side of it.
    """
    t1 = maze.CENTERLINE[0]["p1"]
    cross, up, goal = (1, 3, "g_ee") if side == "east" else (2, 4, "g_ww")
    return [maze.REWARD_SITES["start"], t1, maze.CENTERLINE[cross]["p1"], maze.CENTERLINE[up]["p1"], maze.REWARD_SITES[goal]]


def _route_positions(waypoints, frames_per_segment, dwell_frames):
    """
    The route's waypoints walked at a constant frames-per-segment pace, then held at the final waypoint for dwell_frames: a real rat pauses at a reward site or the start, which is what gives track_scale's peak finding a real density peak to find at each extreme.
    """
    xs, ys = [], []
    fraction = (np.arange(frames_per_segment) + 1) / frames_per_segment
    for a, b in zip(waypoints, waypoints[1:]):
        xs.append(a[0] + (b[0] - a[0]) * fraction)
        ys.append(a[1] + (b[1] - a[1]) * fraction)
    xs.append(np.full(dwell_frames, waypoints[-1][0]))
    ys.append(np.full(dwell_frames, waypoints[-1][1]))
    return np.concatenate(xs), np.concatenate(ys)


def oscillating_epoch(epoch_name, environment, condition, start_frame, rotation, scale=200.0, offset=(0.0, 0.0),
                       rate_hz=60, trips=6, frames_per_segment=15, dwell_frames=20):
    """
    One epoch's frames and runs: the rat running out and back, alternating the east and west outbound routes so both room axes are fully covered, pausing at each end, at the given true pixel rotation and scale, labelled outbound (path 1) and return (path 9) runs.
    """
    legs_per_trip, frames_per_leg = 2, frames_per_segment * 4 + dwell_frames
    legs = trips * legs_per_trip
    n = legs * frames_per_leg
    frame = np.arange(start_frame, start_frame + n, dtype=np.int64)
    room_x, room_y, runs = [], [], []
    for leg in range(legs):
        waypoints = _route_waypoints("east" if (leg // legs_per_trip) % 2 == 0 else "west")
        here = waypoints if leg % 2 == 0 else waypoints[::-1]
        x, y = _route_positions(here, frames_per_segment, dwell_frames)
        room_x.append(x)
        room_y.append(y)
        runs.append({"epoch": epoch_name, "path_id": OUTBOUND_PATH if leg % 2 == 0 else RETURN_PATH,
                     "frame_start": int(frame[leg * frames_per_leg]), "frame_end": int(frame[(leg + 1) * frames_per_leg - 1]),
                     "duplicate_of": None, "clean": True})
    room_x, room_y = np.concatenate(room_x), np.concatenate(room_y)
    mashup_x, mashup_y = to_pixels(room_x, room_y, scale, rotation, offset)
    frames = {
        "frame": frame, "t": frame / rate_hz, "mashup_x": mashup_x, "mashup_y": mashup_y,
        "front_x": mashup_x + 3, "front_y": mashup_y, "back_x": mashup_x - 3, "back_y": mashup_y,
        "head_dir": np.zeros(n), "unfilled_front": np.zeros(n, bool), "unfilled_back": np.zeros(n, bool),
        "filled_front": np.zeros(n, bool), "filled_back": np.zeros(n, bool),
    }
    epoch = {"epoch": epoch_name, "environment": environment, "condition": condition,
             "frame_start": int(frame[0]), "frame_end": int(frame[-1])}
    return frames, runs, epoch


def merge_frames(parts):
    """
    Several epochs' frame dicts concatenated into one session's worth, keys taken from the first part.
    """
    return {key: np.concatenate([p[key] for p in parts]) for key in parts[0]}


def track_and_variant(rotation_track=0.0, rotation_variant=np.pi / 2, variant_environment="triple_t_rot90",
                       variant_condition="rot90", scale=200.0, rate_hz=60, trips=6, frames_per_segment=15, dwell_frames=20):
    """
    A session's track epoch (baseline) and a variant epoch right after it, at their own true rotations but the same scale and offset (the camera does not move).
    """
    track_frames, track_runs, track_epoch = oscillating_epoch(
        "track", "triple_t", "baseline", 1, rotation_track, scale, rate_hz=rate_hz, trips=trips,
        frames_per_segment=frames_per_segment, dwell_frames=dwell_frames)
    variant_frames, variant_runs, variant_epoch = oscillating_epoch(
        "variant", variant_environment, variant_condition, track_epoch["frame_end"] + 1, rotation_variant, scale,
        rate_hz=rate_hz, trips=trips, frames_per_segment=frames_per_segment, dwell_frames=dwell_frames)
    frames = merge_frames([track_frames, variant_frames])
    return frames, track_runs + variant_runs, track_epoch, variant_epoch
