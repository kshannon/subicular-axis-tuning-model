"""
Cutting: every selected frame ends up in exactly one of block, margin, gap or dropped, and a pause, a jump and a long tracking gap each cut where expected.
"""

import numpy as np
import pytest

from scripts.build_blocks import cut

RATE_HZ = 60
N = 3000
PAUSE_STEP_S = 0.5
JUMP_PX = 40.0
MAX_GAP_FRAMES = 30
MIN_BLOCK_S = 1.0


@pytest.fixture
def frames_and_epoch():
    """
    A 3000 frame epoch with one pause (frame 1001), one jump (frame 2001) and one 60 frame tracking gap (frames 401 to 460).
    """
    rng = np.random.default_rng(0)
    frame = np.arange(1, N + 1, dtype=np.int64)
    t = frame / RATE_HZ
    t[1000:] += 2.0  # a pause well over PAUSE_STEP_S
    walk = np.cumsum(rng.normal(0, 0.5, N))
    mashup_x = 300 + walk
    mashup_x[2000:] += 200.0  # a single frame jump well over JUMP_PX
    mashup_y = np.full(N, 200.0)
    unfilled = np.zeros(N, bool)
    unfilled[400:460] = True  # longer than MAX_GAP_FRAMES
    frames = {"frame": frame, "t": t, "mashup_x": mashup_x, "mashup_y": mashup_y,
              "unfilled_front": unfilled.copy(), "unfilled_back": unfilled.copy()}
    epoch = {"epoch": "track", "environment": "triple_t", "condition": "baseline", "frame_start": 1, "frame_end": N}
    return frames, epoch


def test_pause_and_jump_are_found(frames_and_epoch):
    frames, _ = frames_and_epoch
    assert frames["frame"][cut.pauses(frames["t"], PAUSE_STEP_S)][0] == 1001
    assert frames["frame"][cut.jumps(frames, JUMP_PX, PAUSE_STEP_S)][0] == 2001


def test_gap_is_the_whole_unfilled_stretch(frames_and_epoch):
    frames, _ = frames_and_epoch
    gap = cut.gaps(frames, MAX_GAP_FRAMES)
    assert int(gap.sum()) == 60
    assert frames["frame"][gap][0] == 401 and frames["frame"][gap][-1] == 460


def test_frame_counts_partition_every_frame(frames_and_epoch):
    """
    block, margin, gap and dropped are mutually exclusive and together cover every one of the epoch's frames.
    """
    frames, epoch = frames_and_epoch
    pieces, margins = cut.cut_epoch(frames, epoch, MAX_GAP_FRAMES, RATE_HZ, PAUSE_STEP_S, JUMP_PX)
    blocks = cut.initial_blocks("s1", epoch, pieces, RATE_HZ, MIN_BLOCK_S)
    counts = cut.frame_counts(frames, epoch, margins, blocks, MAX_GAP_FRAMES)
    assert sum(counts.values()) == N
    assert counts["gap"] == 60
    assert counts["block"] > 0
    assert counts["margin"] > 0


def test_short_pieces_are_dropped_not_built():
    """
    A piece left over after the epoch-boundary margins, but still shorter than min_block_s, is counted as dropped, not written as a block.
    """
    n = 2000
    frame = np.arange(1, n + 1, dtype=np.int64)
    t = frame / RATE_HZ
    frames = {"frame": frame, "t": t, "mashup_x": np.full(n, 0.0), "mashup_y": np.full(n, 0.0),
              "unfilled_front": np.zeros(n, bool), "unfilled_back": np.zeros(n, bool)}
    epoch = {"epoch": "track", "environment": "triple_t", "condition": "baseline", "frame_start": 1, "frame_end": n}
    pieces, margins = cut.cut_epoch(frames, epoch, MAX_GAP_FRAMES, RATE_HZ, PAUSE_STEP_S, JUMP_PX)
    assert pieces == [(301, 1700)]  # the epoch's two boundary margins (PAUSE_MARGIN_S, 300 frames each) trimmed in
    blocks = cut.initial_blocks("s1", epoch, pieces, RATE_HZ, min_block_s=1000.0)
    assert blocks == []
    counts = cut.frame_counts(frames, epoch, margins, blocks, MAX_GAP_FRAMES)
    assert counts["block"] == 0
    assert counts["margin"] == 600
    assert counts["dropped"] == 1400
    assert sum(counts.values()) == n
