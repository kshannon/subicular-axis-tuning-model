"""
Motion: the smoothed pixel speed and direction registration reads, the LED separation, heading fills, and speed, direction and turn rate in metres from Savitzky-Golay derivatives. Ported from axis-of-travel-rnn's blocks/kinematics.py and heading.py.
"""

import numpy as np
from scipy.signal import savgol_filter

from .cut import RUNNING_PX_PER_S, inside, pauses, runs_of

# Not exposed in build_protocol.yaml: axis-of-travel-rnn's already-debugged motion and heading-fill constants.
SPEED_SMOOTH_FRAMES = 6
SMOOTH_WINDOW_S = 0.15
SMOOTH_ORDER = 2
HEADING_FILL_S = 3.0
RUNNING_FLOOR_M_PER_S = 0.03
NOMINAL_LED_SEPARATION_M = 0.05

SPAN_KEYS = ("lost", "filled", "held")
LOST, FILLED, HELD = SPAN_KEYS
OVER_LIMIT = "over the fill limit of {limit:g} s"
HAS_PAUSE = "contains a pause"
AT_START = "touches the start of the recording"
AT_END = "touches the end of the recording"
NO_SIDE = "no measured heading on either side"
ARC = "along the shortest arc"
STILL = "the rat was still"


def smoothed(steps):
    """
    A per-step series as a per-frame series, the first frame repeating the second, averaged over SPEED_SMOOTH_FRAMES frames.
    """
    kernel = np.ones(SPEED_SMOOTH_FRAMES) / SPEED_SMOOTH_FRAMES
    return np.convolve(np.concatenate([steps[:1], steps]), kernel, mode="same")


def pixel_motion(frames):
    """
    The smoothed speed in px/s and the direction of the smoothed velocity in camera coordinates (y down), from the mashup positions.
    """
    dt, dx, dy = np.diff(frames["t"]), np.diff(frames["mashup_x"]), np.diff(frames["mashup_y"])
    return smoothed(np.hypot(dx, dy) / dt), np.arctan2(smoothed(dy / dt), smoothed(dx / dt))


def led_distance_px(frames, epoch):
    """
    The median distance in pixels between the two LEDs over the epoch's frames with both lights.
    """
    here = inside(frames, epoch)
    return float(np.nanmedian(np.hypot(frames["front_x"][here] - frames["back_x"][here], frames["front_y"][here] - frames["back_y"][here])))


def smooth_window(rate_hz):
    """
    SMOOTH_WINDOW_S as an odd number of samples at the rate.
    """
    return round(SMOOTH_WINDOW_S * rate_hz) // 2 * 2 + 1


def derivative(values, rate_hz):
    """
    The first derivative per second of the Savitzky-Golay fit over smooth_window samples of order SMOOTH_ORDER.
    """
    return savgol_filter(values, smooth_window(rate_hz), SMOOTH_ORDER, deriv=1, delta=1 / rate_hz)


def split_at_breaks(mask, breaks):
    """
    The (first, stop) index pairs of every stretch where the mask is true, split where a break starts a new one.
    """
    found = []
    for first, stop in runs_of(mask):
        edges = [first, *(np.flatnonzero(breaks[first + 1:stop]) + first + 1).tolist(), stop]
        found += list(zip(edges[:-1], edges[1:]))
    return found


def kinematics(x, y, heading, breaks, rate_hz):
    """
    Speed in m/s, the direction of motion and the turn rate in rad/s per frame, NaN where the position or heading is missing or its stretch, split at the breaks, is shorter than the window.
    """
    window = smooth_window(rate_hz)
    speed, motion, turn_rate = (np.full(len(x), np.nan) for _ in range(3))
    for first, stop in split_at_breaks(np.isfinite(x) & np.isfinite(y), breaks):
        if stop - first >= window:
            dx, dy = derivative(x[first:stop], rate_hz), derivative(y[first:stop], rate_hz)
            speed[first:stop], motion[first:stop] = np.hypot(dx, dy), np.arctan2(dy, dx)
    for first, stop in split_at_breaks(np.isfinite(heading), breaks):
        if stop - first >= window:
            turn_rate[first:stop] = derivative(np.unwrap(heading[first:stop]), rate_hz)
    return speed, motion, turn_rate


def led_offset(frames):
    """
    The circular mean (rad) and concentration r of head_dir minus the motion direction over running frames in camera coordinates, and their count: the light bar's mounting angle.
    """
    speed, direction = pixel_motion(frames)
    heading = frames["head_dir"]
    running = (speed > RUNNING_PX_PER_S) & np.isfinite(heading) & np.isfinite(direction)
    z = np.exp(1j * (heading[running] - direction[running])).sum() / max(running.sum(), 1)
    return float(np.angle(z)), float(np.abs(z)), int(running.sum())


def steady_speed(frames):
    """
    The mashup speed in px/s averaged over the steps that do not cross a light switch, where the mashup moves without the rat.
    """
    step = np.hypot(np.diff(frames["mashup_x"]), np.diff(frames["mashup_y"])) / np.diff(frames["t"])
    front, back = frames["unfilled_front"], frames["unfilled_back"]
    kept = ~((front[1:] != front[:-1]) | (back[1:] != back[:-1]))
    return smoothed(np.where(kept, step, 0.0)) / smoothed(kept.astype(float))


def still(frames, epochs):
    """
    True on a frame of one of the epochs whose steady speed is under RUNNING_FLOOR_M_PER_S at the epoch's nominal scale, its LED distance over NOMINAL_LED_SEPARATION_M.
    """
    speed = steady_speed(frames)
    floor_px = np.full(len(speed), np.nan)
    for epoch in epochs:
        floor_px[inside(frames, epoch)] = RUNNING_FLOOR_M_PER_S * led_distance_px(frames, epoch) / NOMINAL_LED_SEPARATION_M
    return speed < floor_px


def unfillable(first, stop, length, pause):
    """
    Why the gap from index first to stop cannot be filled whatever the rat does, none when it can: it touches an end of the recording or holds a pause.
    """
    if first == 0 and stop == length:
        return NO_SIDE
    if first == 0:
        return AT_START
    if stop == length:
        return AT_END
    return HAS_PAUSE if pause[first:stop + 1].any() else None


def fill(heading, t, still_frames, rate_hz, pause_step_s):
    """
    The heading with its NaN gaps free of pauses filled, up to HEADING_FILL_S along the shortest arc and longer ones by the last heading while the rat is still throughout, and for every gap its (first, stop) indices, span key and reason.
    """
    filled, found = heading.copy(), []
    pause = pauses(t, pause_step_s)
    longest = round(HEADING_FILL_S * rate_hz)
    for first, stop in runs_of(np.isnan(heading)):
        reason = unfillable(first, stop, len(heading), pause)
        if reason:
            found.append((first, stop, LOST, reason))
            continue
        start = heading[first - 1]
        if stop - first > longest:
            if still_frames[first:stop].all():
                filled[first:stop] = start
                found.append((first, stop, HELD, STILL))
            else:
                found.append((first, stop, LOST, OVER_LIMIT.format(limit=HEADING_FILL_S)))
            continue
        turn = (heading[stop] - start + np.pi) % (2 * np.pi) - np.pi
        fraction = np.arange(1, stop - first + 1) / (stop - first + 1)
        filled[first:stop] = (start + turn * fraction + np.pi) % (2 * np.pi) - np.pi
        found.append((first, stop, FILLED, ARC))
    return filled, found


def fill_spans(frame, found, rate_hz):
    """
    The spans of the gaps fill found, by key lost, filled and held: each the first and last lab frame, the seconds and the reason.
    """
    spans = {key: [] for key in SPAN_KEYS}
    for first, stop, key, reason in found:
        spans[key].append({"first": int(frame[first]), "last": int(frame[stop - 1]), "seconds": float((stop - first) / rate_hz), "reason": reason})
    return spans
