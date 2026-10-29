"""
Labels: outbound and return phases from the lab's runs, a slow stretch inside a run is a pause (never a cut), dwell everywhere else, including while the animal eats at a goal.
"""

import numpy as np

from scripts.build_blocks import labels

RATE_HZ = 10


def test_label_frames_phases_and_pauses():
    frame = np.arange(1, 101)
    speed = np.full(100, 0.5)
    speed[14:30] = 0.0  # 16 frames of stillness inside run 1, over PAUSE_MIN_S at this rate
    runs = [
        {"run": 1, "path_id": 1, "frame_start": 1, "frame_end": 40, "duplicate_of": None, "clean": True},
        {"run": 2, "path_id": 9, "frame_start": 60, "frame_end": 90, "duplicate_of": None, "clean": True},
    ]
    found = labels.label_frames(frame, speed, "track", runs, RATE_HZ)

    assert set(found["phase"][0:14]) == {"outbound"}
    assert set(found["phase"][14:30]) == {"pause"}
    assert set(found["phase"][30:40]) == {"outbound"}
    assert set(found["phase"][40:59]) == {"dwell"}
    assert set(found["phase"][59:90]) == {"return"}
    assert set(found["phase"][90:100]) == {"dwell"}
    assert (found["run"][0:40] == 1).all()
    assert (found["path_id"][0:40] == 1).all()
    assert (found["clean"][0:40]).all()


def test_eating_at_a_goal_is_a_dwell_not_a_cut():
    """
    A long still stretch outside any run (eating at a goal) is labelled dwell, not pause: pauses only apply inside a run.
    """
    frame = np.arange(1, 51)
    speed = np.zeros(50)
    found = labels.label_frames(frame, speed, "track", [], RATE_HZ)
    assert set(found["phase"]) == {"dwell"}


def test_arena_is_forage_outside_any_run():
    frame = np.arange(1, 21)
    speed = np.full(20, 0.5)
    found = labels.label_frames(frame, speed, "arena", [], RATE_HZ)
    assert set(found["phase"]) == {"forage"}
