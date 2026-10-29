"""
Registration: the pixel-to-metre round trip at 0, 45 and 90 degrees, and that a rotated variant epoch's measured rotation is never silently reported as zero.
"""

import math

import numpy as np
import pytest

from scripts.build_blocks import register
from scripts.build_blocks.register import TRACK

from .synthetic import to_pixels, track_and_variant


@pytest.mark.parametrize("rotation", [0.0, math.pi / 4, math.pi / 2])
def test_to_room_round_trips_pixels(rotation):
    """
    A room point converted to pixels at a scale, rotation and offset and back comes back unchanged, at 0, 45 and 90 degrees.
    """
    scale, offset = 150.0, (0.3, -0.2)
    room_x, room_y = 0.42, 0.91
    px, py = to_pixels(room_x, room_y, scale, rotation, offset)
    back_x, back_y = register.to_room(px, py, scale, rotation, offset)
    assert back_x == pytest.approx(room_x, abs=1e-6)
    assert back_y == pytest.approx(room_y, abs=1e-6)


@pytest.mark.parametrize("rotation", [0.0, math.pi / 4, math.pi / 2])
def test_track_rotation_recovers_the_true_rotation(rotation):
    """
    track_rotation on a session run at a known true pixel rotation recovers that rotation, not just its sign-ambiguous four-fold candidate.
    """
    frames, runs, track_epoch, _ = track_and_variant(rotation_track=rotation, rotation_variant=rotation)
    recovered, concentration, _, _ = register.track_rotation(frames, track_epoch, runs)
    assert concentration > 0.6
    assert abs(register.wrapped(recovered - rotation)) < math.radians(3)


def test_track_scale_recovers_the_true_scale():
    """
    track_scale on a session run at a known true pixel scale recovers a scale within a loose tolerance (an estimate from a smoothed histogram, not an exact fit).
    """
    scale_true = 150.0
    frames, runs, track_epoch, _ = track_and_variant(scale=scale_true)
    rotation, _, _, _ = register.track_rotation(frames, track_epoch, runs)
    axes = register.running_axes(frames, track_epoch, rotation)
    scale, scale_x, scale_y = register.track_scale(axes)
    assert scale == pytest.approx(scale_true, rel=0.2)


def test_variant_rotation_90_is_not_reported_as_zero():
    """
    A rot90 variant epoch's measured rotation comes back near 90 degrees, never silently near zero: the core claim behind the rotation-mismatch check.
    """
    frames, runs, track_epoch, variant_epoch = track_and_variant(rotation_track=0.0, rotation_variant=math.pi / 2)
    baseline = register.parameters(frames, [track_epoch], runs)
    variant = register.variant_parameters(frames, variant_epoch, runs, baseline[TRACK])
    assert abs(variant["maze_deg_measured"]) > 45
    assert variant["maze_deg_measured"] == pytest.approx(90.0, abs=5.0)


def test_variant_borrows_the_track_transform_not_its_own():
    """
    A variant epoch's scale, rotation and offset for registering positions are the track's own, borrowed verbatim, never re-derived from the variant's own frames.
    """
    frames, runs, track_epoch, variant_epoch = track_and_variant(rotation_track=0.0, rotation_variant=math.pi / 2)
    baseline = register.parameters(frames, [track_epoch], runs)
    variant = register.variant_parameters(frames, variant_epoch, runs, baseline[TRACK])
    assert variant["scale_px_per_m"] == baseline[TRACK]["scale_px_per_m"]
    assert variant["rotation_rad"] == baseline[TRACK]["rotation_rad"]
    assert variant["offset_m"] == baseline[TRACK]["offset_m"]


def test_variant_plots_rotated_not_corrected():
    """
    Both epochs run the same physical route, but a rot90 variant's borrowed (unrotated) registration should show its occupancy turned on its side relative to the track's own: the manipulation is preserved, not undone. A true 90 degree rotation swaps a bounding box's width and height regardless of where the pivot is.
    """
    frames, runs, track_epoch, variant_epoch = track_and_variant(rotation_track=0.0, rotation_variant=math.pi / 2)
    baseline = register.parameters(frames, [track_epoch], runs)
    registration = {TRACK: baseline[TRACK], "variant": register.variant_parameters(frames, variant_epoch, runs, baseline[TRACK])}
    x, y = register.to_metres(frames, [track_epoch, variant_epoch], registration)
    on_track, on_variant = register.inside(frames, track_epoch), register.inside(frames, variant_epoch)
    track_width, track_height = np.nanmax(x[on_track]) - np.nanmin(x[on_track]), np.nanmax(y[on_track]) - np.nanmin(y[on_track])
    variant_width, variant_height = np.nanmax(x[on_variant]) - np.nanmin(x[on_variant]), np.nanmax(y[on_variant]) - np.nanmin(y[on_variant])
    assert variant_width == pytest.approx(track_height, rel=0.15)
    assert variant_height == pytest.approx(track_width, rel=0.15)
