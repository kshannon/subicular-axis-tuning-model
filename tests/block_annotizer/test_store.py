"""
The annotizer's invariants: it writes only its sidecar folder, and the RatInABox triple T is really turned.
"""

import hashlib

import numpy as np

from scripts.block_annotizer import environments
from scripts.block_annotizer.store import ANNOTATIONS_DIR, Store


def digest(folder):
    """
    Every file under folder except the annotations folder, with its sha256.
    """
    return {p.relative_to(folder): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in folder.rglob("*") if p.is_file() and ANNOTATIONS_DIR not in p.parts}


def test_store_touches_nothing_but_its_own_folder(tmp_path):
    run_root = tmp_path / "2026-01-01T000000Z_x"
    (run_root / "frames").mkdir(parents=True)
    (run_root / "blocks.csv").write_text("block_id,verdict\nb_track_01,ok\n")
    (run_root / "frames" / "b_track_01.parquet").write_bytes(b"parquet")
    (run_root / "manifest.json").write_text("{}")
    before = digest(run_root)
    store = Store(run_root)
    row = {"block_id": "b_track_01", "session_id": "b", "environment": "triple_t"}
    first = store.add(row, 10, 20, 0.1, 0.2, "tracking", "")
    second = store.add(row, 30, 40, 0.3, 0.4, "dwell", "")
    store.drop_last("b_track_01")
    third = store.add(row, 50, 60, 0.5, 0.6, "jump", "")
    store.set_verdict("b_track_01", "exclude", "why")
    store.add_dataset_note("a note")
    assert digest(run_root) == before
    assert (first["annotation_id"], second["annotation_id"], third["annotation_id"]) == ("b_track_01_a01", "b_track_01_a02", "b_track_01_a02")
    assert [a["annotation_id"] for a in Store(run_root).for_block("b_track_01")] == ["b_track_01_a01", "b_track_01_a02"]


def test_rotated_triple_t_is_turned_by_the_nominal_angle():
    def size(env):
        x0, x1, y0, y1 = env.extent
        return x1 - x0, y1 - y0
    width, height = size(environments.triple_t(0.0))
    assert np.isclose(width, 1.60) and np.isclose(height, 1.25)
    turned_width, turned_height = size(environments.triple_t(90.0))
    assert np.isclose(turned_width, height) and np.isclose(turned_height, width)
    assert environments.triple_t(0.0).reward_sites.keys() == {"start", "g_ee", "g_ew", "g_ww", "g_we"}
    assert np.allclose(size(environments.arena()), 0.6, atol=0.01)
