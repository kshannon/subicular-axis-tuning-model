"""
Fixtures for the block builder's tests: real TRANSFORMED_LAB_DATA tables, made by running the real transform_lab_data orchestrator over synthetic MATLAB sessions, not a second synthetic data generator.
"""

import pytest

import scripts.build_blocks.__main__ as entry
from scripts.transform_lab_data import readers
from scripts.transform_lab_data.orchestrator import Orchestrator

from tests.transform_lab_data.synthetic_mat import example_session, session_names, write_session


@pytest.fixture(autouse=True)
def no_local_config(monkeypatch):
    """
    Make reading configs/local.yaml an error, so every test passes its own config.
    """
    def refuse(*args, **kwargs):
        raise AssertionError("a test read configs/local.yaml; pass config instead")
    monkeypatch.setattr(entry, "local_config", refuse)


@pytest.fixture
def lab_root(tmp_path):
    """
    Three sessions: NS14 standard (in scope), NS14 under muscimol (out by protocol), JL1 (out, a different rat's folder).
    """
    root = tmp_path / "lab"
    write_session(root / "NS14Data", example_session(), session_names("NS14", 1, "021915", "001"), "classic")
    write_session(root / "NS14Data", example_session("bilatmusc"), session_names("NS14", 2, "021915", "002", tag="bilatmusc"), "classic")
    write_session(root / "JL1HPCData", example_session(), session_names("JL1", 1, "071514", "001"), "classic")
    return root


@pytest.fixture
def transformed_root(tmp_path, lab_root):
    """
    TRANSFORMED_LAB_DATA's real tables, built by the real transform_lab_data converter over lab_root.
    """
    root = tmp_path / "transformed"
    found, skipped = readers.catalog(lab_root)
    sessions = readers.select(found, only=None, sample=None)
    Orchestrator(root).run(sessions, skipped, {"only": None, "sample": None})
    return root


@pytest.fixture
def protocol():
    """
    A build_protocol.yaml dict loose enough to build the fixture's synthetic session.
    """
    return {"rat": "", "conditions": ("baseline", "rot45", "rot90"), "pause_step_s": 0.5, "jump_px": 40,
            "max_gap_frames": 180, "min_block_s": 1.0}
