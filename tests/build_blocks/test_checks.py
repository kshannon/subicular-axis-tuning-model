"""
Checks: the fail checks that keep a block from being written, the warn checks that flag one without dropping it, and the variant rotation mismatch.
"""

import numpy as np

from scripts.build_blocks import checks


def good_columns(n=60, rate_hz=60):
    t = np.arange(n) / rate_hz
    return {"x": np.linspace(0, 1, n), "y": np.linspace(0, 1, n), "t": t}


def test_block_fails_passes_on_good_columns():
    results = checks.block_fails(good_columns(), 60)
    assert checks.failed(results) == []


def test_block_fails_on_missing_position():
    columns = good_columns()
    columns["x"][5] = np.nan
    results = checks.block_fails(columns, 60)
    assert "position_finite" in checks.failed(results)


def test_block_fails_on_irregular_time_step():
    columns = good_columns()
    columns["t"][10] += 1.0
    results = checks.block_fails(columns, 60)
    assert "t_step_regular" in checks.failed(results)


def test_overlapping_blocks_detects_an_overlap():
    blocks = [{"block_id": "a", "frame_start": 1, "frame_end": 100}, {"block_id": "b", "frame_start": 50, "frame_end": 150}]
    overlap, detail = checks.overlapping_blocks(blocks)
    assert overlap
    assert detail["pairs"] == [("a", "b")]


def test_overlapping_blocks_passes_on_disjoint_blocks():
    blocks = [{"block_id": "a", "frame_start": 1, "frame_end": 100}, {"block_id": "b", "frame_start": 101, "frame_end": 150}]
    overlap, _ = checks.overlapping_blocks(blocks)
    assert not overlap


def registration(scale=100.0, scale_x=100.0, scale_y=100.0, led=0.05, concentration=0.9):
    return {"scale_px_per_m": scale, "scale_x_px_per_m": scale_x, "scale_y_px_per_m": scale_y,
            "led_separation_m": led, "rotation_concentration": concentration}


def test_registration_warnings_pass_on_good_values():
    results = checks.registration_warnings(registration(), "track")
    assert checks.warnings(results) == []


def test_axes_disagree_warns():
    results = checks.registration_warnings(registration(scale_x=100.0, scale_y=130.0), "track")
    assert "axes_agree" in checks.warnings(results)


def test_led_separation_out_of_range_warns():
    results = checks.registration_warnings(registration(led=0.2), "track")
    assert "led_separation" in checks.warnings(results)


def test_low_concentration_warns():
    results = checks.registration_warnings(registration(concentration=0.1), "track")
    assert "rotation_concentration" in checks.warnings(results)


def test_arena_extent_ratio_warns_only_for_arena():
    entry = {**registration(), "arena_extent_ratio": 2.0}
    assert "arena_extent_ratio" in checks.warnings(checks.registration_warnings(entry, "arena"))
    assert "arena_extent_ratio" not in checks.registration_warnings(entry, "track")


def test_heading_offset_warning():
    assert checks.heading_offset_warning(0.0)["heading_offset"]["status"] == "pass"
    assert checks.heading_offset_warning(np.radians(20))["heading_offset"]["status"] == "warn"


def test_rotation_mismatch_fails_far_from_tag_not_near_zero():
    mismatch, detail = checks.rotation_mismatch_fail(maze_deg_measured=0.3, nominal_deg=90.0)
    assert mismatch
    assert detail["off_deg"] > 80


def test_rotation_mismatch_passes_close_to_tag():
    mismatch, _ = checks.rotation_mismatch_fail(maze_deg_measured=91.5, nominal_deg=90.0)
    assert not mismatch
