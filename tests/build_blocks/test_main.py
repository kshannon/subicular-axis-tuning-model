"""
The command line: build_protocol.yaml validation, --description required unless --dry-run, and that a real run's committed snapshot matches the BLOCK_DATA folder it describes.
"""

import pytest

import scripts.build_blocks.__main__ as entry


def write_protocol(path, **overrides):
    values = {"rat": "", "conditions": "- baseline\n- rot45\n- rot90", "pause_step_s": 0.5, "jump_px": 40,
              "max_gap_frames": 180, "min_block_s": 10, **overrides}
    conditions = values.pop("conditions")
    text = "\n".join(f"{key}: {value}" for key, value in values.items()) + f"\nconditions:\n{conditions}\n"
    path.write_text(text)
    return path


def test_load_protocol_accepts_a_valid_file(tmp_path):
    path = write_protocol(tmp_path / "build_protocol.yaml")
    protocol = entry.load_protocol(path)
    assert protocol["rat"] == ""
    assert protocol["conditions"] == ("baseline", "rot45", "rot90")
    assert protocol["jump_px"] == 40


def test_load_protocol_refuses_an_unknown_rat(tmp_path):
    path = write_protocol(tmp_path / "build_protocol.yaml", rat="NS99")
    with pytest.raises(SystemExit):
        entry.load_protocol(path)


def test_load_protocol_refuses_an_unknown_condition(tmp_path):
    path = write_protocol(tmp_path / "build_protocol.yaml", conditions="- rot180")
    with pytest.raises(SystemExit):
        entry.load_protocol(path)


def test_load_protocol_refuses_a_non_positive_threshold(tmp_path):
    path = write_protocol(tmp_path / "build_protocol.yaml", jump_px=0)
    with pytest.raises(SystemExit):
        entry.load_protocol(path)


def test_description_required_unless_dry_run():
    with pytest.raises(SystemExit):
        entry.parse_args([])
    args = entry.parse_args(["--dry-run"])
    assert args.description is None


def test_roots_refuses_block_data_inside_transformed(tmp_path):
    transformed = tmp_path / "transformed"
    transformed.mkdir()
    config = {"TRANSFORMED_LAB_DATA": str(transformed), "BLOCK_DATA": str(transformed / "blocks")}
    with pytest.raises(SystemExit):
        entry.roots(config)


def test_dataset_registers_itself_under_its_own_name(tmp_path, monkeypatch, transformed_root, protocol):
    """
    A real build's committed snapshot in docs/datasets_reference/ is named exactly after the BLOCK_DATA folder it describes.
    """
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    monkeypatch.setattr(entry, "REPO_ROOT", repo_root)
    protocol_path = write_protocol(repo_root / "build_protocol.yaml")
    monkeypatch.setattr(entry, "PROTOCOL_PATH", protocol_path)

    block_data = tmp_path / "block_data"
    config = {"TRANSFORMED_LAB_DATA": str(transformed_root), "BLOCK_DATA": str(block_data)}
    code = entry.main(["--description", "test-run"], config=config)

    assert code in (0, 1)
    run_dirs = list(block_data.iterdir())
    assert len(run_dirs) == 1
    run_name = run_dirs[0].name
    assert run_name.endswith("_test-run")
    assert (run_dirs[0] / "blocks.csv").is_file()
    assert (run_dirs[0] / "manifest.json").is_file()

    reference_dir = repo_root / "docs" / "datasets_reference"
    assert (reference_dir / f"{run_name}.yaml").is_file()
    registry_rows = (reference_dir / "datasets.csv").read_text().splitlines()
    assert any(row.startswith(run_name) for row in registry_rows[1:])
