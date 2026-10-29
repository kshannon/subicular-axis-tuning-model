"""
Where a session is cut into blocks: pauses, jumps, long tracking gaps and epoch bounds, the margins trimmed beside them, the blocks left. Ported from axis-of-travel-rnn's blocks/cuts.py.
"""

import numpy as np

PAUSE, GAP, JUMP = "pause", "gap", "jump"
INITIAL_STATUS = "auto"

# Not exposed in build_protocol.yaml: how far a stretch edge is trimmed inward beside a cut.
PAUSE_MARGIN_S = 5.0
# The base of the one-way cut -> motion -> register dependency chain, so motion.py and register.py import it
# from here rather than each holding their own copy.
RUNNING_PX_PER_S = 20.0


def inside(frames, epoch):
    """
    True on the frames of the epoch.
    """
    return (frames["frame"] >= epoch["frame_start"]) & (frames["frame"] <= epoch["frame_end"])


def epoch_index(frames, epochs):
    """
    The position in epochs of the epoch holding each frame, minus one for a frame in none.
    """
    index = np.full(len(frames["frame"]), -1)
    for i, epoch in enumerate(epochs):
        index[inside(frames, epoch)] = i
    return index


def runs_of(mask):
    """
    The (first, stop) index pairs of every stretch where the mask is true.
    """
    edges = np.flatnonzero(np.diff(np.concatenate(([False], mask, [False])).astype(np.int8)))
    return list(zip(edges[::2].tolist(), edges[1::2].tolist()))


def pauses(t, pause_step_s):
    """
    True on the first frame after a step in t over pause_step_s.
    """
    return np.concatenate(([False], np.diff(t) > pause_step_s))


def jumps(frames, jump_px, pause_step_s):
    """
    True on the frame whose mashup position moved over jump_px from the frame before within one normal step, never across a pause. This is the only teleport check: a position jump inside one frame step.
    """
    step = np.hypot(np.diff(frames["mashup_x"]), np.diff(frames["mashup_y"]))
    return np.concatenate(([False], (step > jump_px) & (np.diff(frames["t"]) <= pause_step_s)))


def gaps(frames, max_gap_frames):
    """
    True on every frame of a stretch with both lights unfilled for more than max_gap_frames. A short unfilled stretch is a heading-fill or motion-smoothing matter, not a cut.
    """
    unfilled = np.logical_and(frames["unfilled_front"], frames["unfilled_back"])
    gap = np.zeros(len(unfilled), bool)
    for first, stop in runs_of(unfilled):
        if stop - first > max_gap_frames:
            gap[first:stop] = True
    return gap


def cut_adjacent(cut, first, last):
    """
    Whether each stretch sits next to a cut, on the side before it and the side after it, the epoch bounds counting as cuts.
    """
    between = [bool(cut[a + 1:b + 1].any()) for a, b in zip(last[:-1], first[1:])]
    return np.array([True] + between, bool), np.array(between + [True], bool)


def stretches(frames, epoch, max_gap_frames, rate_hz, pause_step_s, jump_px):
    """
    The epoch's stretches as four index arrays, first and last before the margins then after, a vanished stretch having first over last.
    """
    cut = pauses(frames["t"], pause_step_s) | jumps(frames, jump_px, pause_step_s)
    cut_next = np.concatenate((cut[1:], [False]))
    kept = inside(frames, epoch) & ~gaps(frames, max_gap_frames)
    before = np.concatenate(([False], kept[:-1]))
    after = np.concatenate((kept[1:], [False]))
    first = np.flatnonzero(kept & (~before | cut))
    last = np.flatnonzero(kept & (~after | cut_next))
    margin = round(PAUSE_MARGIN_S * rate_hz)
    adjacent_first, adjacent_last = cut_adjacent(cut, first, last)
    return first, last, first + margin * adjacent_first, last - margin * adjacent_last


def cut_epoch(frames, epoch, max_gap_frames, rate_hz, pause_step_s, jump_px):
    """
    The epoch's stretches with the margins trimmed, and the frames trimmed from them as margins, both as 1-based inclusive frame pairs.
    """
    frame, margins = frames["frame"], []
    first, last, trimmed_first, trimmed_last = stretches(frames, epoch, max_gap_frames, rate_hz, pause_step_s, jump_px)
    for a, b, trimmed_a, trimmed_b in zip(first, last, trimmed_first, trimmed_last):
        if trimmed_a > trimmed_b:
            margins.append((int(frame[a]), int(frame[b])))
            continue
        if trimmed_a > a:
            margins.append((int(frame[a]), int(frame[trimmed_a - 1])))
        if trimmed_b < b:
            margins.append((int(frame[trimmed_b + 1]), int(frame[b])))
    kept = trimmed_first <= trimmed_last
    return list(zip(frame[trimmed_first[kept]].tolist(), frame[trimmed_last[kept]].tolist())), margins


def in_ranges(frame, ranges):
    """
    True on the frames inside any of the (first, last) ranges.
    """
    mask = np.zeros(len(frame), bool)
    for a, b in ranges:
        mask |= (frame >= a) & (frame <= b)
    return mask


def frame_counts(frames, epoch, margins, blocks, max_gap_frames):
    """
    How many of the epoch's frames end up in exactly one of block, margin, gap or dropped (a piece shorter than min_block_s), from the margins and blocks already cut.
    """
    frame = frames["frame"]
    total = inside(frames, epoch)
    gap = gaps(frames, max_gap_frames) & total
    margin_mask = in_ranges(frame, margins)
    block_mask = in_ranges(frame, [(b["frame_start"], b["frame_end"]) for b in blocks])
    dropped = total & ~gap & ~margin_mask & ~block_mask
    return {"block": int(block_mask.sum()), "margin": int(margin_mask.sum()), "gap": int(gap.sum()), "dropped": int(dropped.sum())}


def initial_blocks(session_id, epoch, pieces, rate_hz, min_block_s):
    """
    The blocks a stretch list makes, those of at least min_block_s, numbered within the epoch.
    """
    long = [(a, b) for a, b in pieces if b - a + 1 >= min_block_s * rate_hz]
    return [{"block_id": f"{session_id}_{epoch['epoch']}_{i:02d}", "epoch": epoch["epoch"], "environment": epoch["environment"],
             "frame_start": a, "frame_end": b, "status": INITIAL_STATUS}
            for i, (a, b) in enumerate(long, 1)]
