"""
Registration: the pixel scale, rotation and offset that take a session's track and arena epochs from the camera to the room, and the variant epoch's borrowed transform with its own measured rotation. Ported from axis-of-travel-rnn's blocks/frame.py and room.py.
"""

import numpy as np
from scipy.signal import find_peaks

from . import maze
from .cut import RUNNING_PX_PER_S, inside
from .maze import ARENA, OUTBOUND_PATHS, TRACK
from .motion import led_distance_px, pixel_motion

# Not exposed in build_protocol.yaml: axis-of-travel-rnn's already-debugged registration constants. The three
# heights are confirmed from the paper (Olson 2017) rather than independently measured, see the design docs.
HISTOGRAM_BIN_PX = 2.0
PEAK_SMOOTH_BINS = 5
PEAK_PROMINENCE = 0.1
CAMERA_HEIGHT_M = 2.6
TRACK_HEIGHT_M = 0.2
ARENA_HEIGHT_M = 0.4
EXTENT_PERCENTILES = (1, 99)


def wrapped(angle):
    """
    An angle in radians wrapped to the interval from minus pi to pi.
    """
    return (angle + np.pi) % (2 * np.pi) - np.pi


def rotated(x, y, angle):
    """
    The points rotated counterclockwise by the angle about the origin.
    """
    return x * np.cos(angle) - y * np.sin(angle), x * np.sin(angle) + y * np.cos(angle)


def to_room(x_px, y_px, scale, rotation, offset):
    """
    Pixels to room metres: y negated for the camera flip, divided by the scale, rotated counterclockwise by rotation, then shifted by offset.
    """
    x, y = rotated(x_px / scale, -y_px / scale, rotation)
    return x + offset[0], y + offset[1]


def heading_to_room(head_dir, led_offset_rad, rotation_rad):
    """
    Camera heading to room heading: negated for the y flip, the LED offset taken off so 0 is the direction of travel on average, the rotation added, wrapped.
    """
    return wrapped(-(head_dir - led_offset_rad) + rotation_rad)


def to_metres(frames, epochs, registration):
    """
    The mashup positions in room metres, each epoch under its own registration, NaN outside every epoch.
    """
    x, y = np.full(len(frames["frame"]), np.nan), np.full(len(frames["frame"]), np.nan)
    for epoch in epochs:
        p, here = registration[epoch["epoch"]], inside(frames, epoch)
        x[here], y[here] = to_room(frames["mashup_x"][here], frames["mashup_y"][here], p["scale_px_per_m"], p["rotation_rad"], p["offset_m"])
    return x, y


def moving(frames, epoch):
    """
    True on the frames of the epoch whose smoothed mashup speed is over RUNNING_PX_PER_S.
    """
    speed, _ = pixel_motion(frames)
    return inside(frames, epoch) & (speed > RUNNING_PX_PER_S)


def centroid(counts, centres, at):
    """
    The mean position of the counts in the PEAK_SMOOTH_BINS bins centred on this one.
    """
    window = slice(at - PEAK_SMOOTH_BINS // 2, at + PEAK_SMOOTH_BINS // 2 + 1)
    return float(np.average(centres[window], weights=counts[window]))


def outer_peaks(values):
    """
    The first and the last peak of the histogram of these values, each placed at the centroid of its smoothing bins.
    """
    size = HISTOGRAM_BIN_PX
    edges = np.arange(values.min() - PEAK_SMOOTH_BINS * size, values.max() + PEAK_SMOOTH_BINS * size + size, size)
    counts, _ = np.histogram(values, edges)
    smooth = np.convolve(counts, np.ones(PEAK_SMOOTH_BINS) / PEAK_SMOOTH_BINS, mode="same")
    peaks, _ = find_peaks(smooth, prominence=PEAK_PROMINENCE * smooth.max())
    centres = edges[:-1] + size / 2
    return centroid(counts, centres, peaks[0]), centroid(counts, centres, peaks[-1])


def peak_span(values):
    """
    The distance between the first and the last peak of the histogram of these values.
    """
    low, high = outer_peaks(values)
    return high - low


def running_axes(frames, epoch, rotation):
    """
    The running frames of the epoch in pixels along the room axes, x to the east and y to the north, the camera's y flipped and the track rotation taken out.
    """
    here = moving(frames, epoch)
    return rotated(frames["mashup_x"][here], -frames["mashup_y"][here], rotation)


def track_scale(axes):
    """
    Pixels per metre of the track: the mean of the two axis estimates, the span of the outermost occupancy peaks of the running frames along each room axis (the perimeter return corridors) over the perimeter's extent, and then each.
    """
    extent_x, extent_y = maze.perimeter_extent()
    scale_x, scale_y = float(peak_span(axes[0]) / extent_x), float(peak_span(axes[1]) / extent_y)
    return (scale_x + scale_y) / 2, scale_x, scale_y


def start_offset_measured(axes, start_px, rotation, scale):
    """
    The distance in metres along the room's y axis from the start site up to the bottom outer corridor peak of the running frames, at the track scale, positive when the start lies above that corridor.
    """
    _, start_y = rotated(start_px[0], -start_px[1], rotation)
    return float((start_y - outer_peaks(axes[1])[0]) / scale)


def arena_scale(track_scale_px_per_m):
    """
    Pixels per metre of the arena: the track scale times the parallax ratio, the arena floor being nearer the camera.
    """
    return track_scale_px_per_m * (CAMERA_HEIGHT_M - TRACK_HEIGHT_M) / (CAMERA_HEIGHT_M - ARENA_HEIGHT_M)


def extent_ratio(frames, epoch, scale):
    """
    The occupancy extent of the epoch's running frames between EXTENT_PERCENTILES, in metres at the scale, over the arena's own diameter: 1 when the rat covers it.
    """
    here = moving(frames, epoch)
    low, high = np.nanpercentile([frames["mashup_x"][here], frames["mashup_y"][here]], EXTENT_PERCENTILES, axis=1)
    return float(np.mean(high - low) / scale / maze.ARENA_DIAMETER)


def median_px(frames, numbers):
    """
    The median mashup position in pixels over these 1-based frame numbers, as a list.
    """
    at = np.searchsorted(frames["frame"], numbers)
    return np.nanmedian(np.column_stack([frames["mashup_x"][at], frames["mashup_y"][at]]), axis=0).tolist()


def sites_px(frames, runs, epoch_name):
    """
    The start site and the goals in pixels: the median position at this epoch's outbound runs' first frame and at their last.
    """
    outbound = [r for r in runs if r["epoch"] == epoch_name and r["path_id"] in OUTBOUND_PATHS]
    return median_px(frames, [r["frame_start"] for r in outbound]), median_px(frames, [r["frame_end"] for r in outbound])


def track_rotation(frames, epoch, runs):
    """
    The counterclockwise rotation that lays this epoch's corridors along the room axes with the start below the goals, the four-fold concentration of the running directions, and the start site and goals in pixels found along the way. Takes any epoch with its own labelled outbound runs, including a rotated variant: it discovers whatever angle the behaviour implies, it does not assume 0, 45 or 90 degrees.
    """
    speed, direction = pixel_motion(frames)
    running = inside(frames, epoch) & (speed > RUNNING_PX_PER_S) & np.isfinite(direction)
    z = np.exp(4j * -direction[running]).mean()
    start, goals = sites_px(frames, runs, epoch["epoch"])
    candidates = -np.angle(z) / 4 + np.arange(4) * np.pi / 2
    best = max(candidates, key=lambda angle: rotated(goals[0] - start[0], -(goals[1] - start[1]), angle)[1])
    return float(wrapped(best)), float(np.abs(z)), start, goals


def goal_match_errors(frames, runs, epoch_name, scale, rotation, offset):
    """
    For each of this epoch's own outbound path ids, the distance in metres from its measured end site to the nearest of the paper's four goals, and whether two path ids claim the same nearest goal (a sign a registration is mirrored, since nothing else catches that).
    """
    ends = {}
    for path_id in OUTBOUND_PATHS:
        outbound = [r for r in runs if r["epoch"] == epoch_name and r["path_id"] == path_id]
        if outbound:
            ends[path_id] = median_px(frames, [r["frame_end"] for r in outbound])
    goals_m = np.array([maze.REWARD_SITES[name] for name in maze.GOAL_NAMES])
    errors, nearest = {}, {}
    for path_id, end_px in ends.items():
        end_m = np.array(to_room(end_px[0], end_px[1], scale, rotation, offset))
        distances = np.linalg.norm(goals_m - end_m, axis=1)
        errors[path_id] = float(distances.min())
        nearest[path_id] = maze.GOAL_NAMES[int(np.argmin(distances))]
    collided = len(set(nearest.values())) < len(nearest)
    return errors, collided


def parameters(frames, epochs, runs):
    """
    The registration of a session's track and arena epochs (condition baseline): per kind the scale, LED separation, rotation, offset, and for the track its two axis estimates and measured start offset, for the arena its extent ratio. The variant epoch is registered separately, see variant_parameters.
    """
    track = next(e for e in epochs if e["epoch"] == TRACK)
    rotation, concentration, start_px, goals_px = track_rotation(frames, track, runs)
    axes = running_axes(frames, track, rotation)
    scale, scale_x, scale_y = track_scale(axes)
    scales = {TRACK: scale, ARENA: arena_scale(scale)}
    found = {"start_px": start_px, "goals_px": goals_px}
    for epoch in epochs:
        kind = epoch["epoch"]
        if kind == TRACK:
            anchor_px, anchor_m = np.array(start_px), np.array(maze.REWARD_SITES["start"])
        else:
            here = inside(frames, epoch)
            anchor_px = np.nanmedian([frames["mashup_x"][here], frames["mashup_y"][here]], axis=1)
            anchor_m = np.array(maze.ROOM) / 2
        offset = anchor_m - np.array(to_room(anchor_px[0], anchor_px[1], scales[kind], rotation, (0.0, 0.0)))
        entry = {"scale_px_per_m": scales[kind], "led_separation_m": led_distance_px(frames, epoch) / scales[kind],
                 "rotation_rad": rotation, "rotation_concentration": concentration, "offset_m": offset.tolist()}
        if kind == ARENA:
            entry["arena_extent_ratio"] = extent_ratio(frames, epoch, scales[kind])
        found[kind] = entry
    found[TRACK].update(scale_x_px_per_m=scale_x, scale_y_px_per_m=scale_y,
                        start_offset_measured_m=start_offset_measured(axes, start_px, rotation, scale))
    return found


def variant_parameters(frames, variant_epoch, runs, track_registration):
    """
    The variant (rotated) epoch's registration: the baseline track's own scale, rotation and offset borrowed verbatim (the camera did not move), plus this epoch's own measured rotation (never used to register it, only logged) and how far it sits from the track's, in degrees, for the fail check. Never undoes the rotation: a variant epoch registered this way still plots rotated.
    """
    borrowed = {"scale_px_per_m": track_registration["scale_px_per_m"], "rotation_rad": track_registration["rotation_rad"],
                "rotation_concentration": track_registration["rotation_concentration"], "offset_m": track_registration["offset_m"]}
    borrowed["led_separation_m"] = led_distance_px(frames, variant_epoch) / borrowed["scale_px_per_m"]
    own_rotation, own_concentration, _, _ = track_rotation(frames, variant_epoch, runs)
    borrowed["maze_deg_measured"] = float(np.degrees(wrapped(own_rotation - track_registration["rotation_rad"])))
    borrowed["own_rotation_concentration"] = own_concentration
    return borrowed
