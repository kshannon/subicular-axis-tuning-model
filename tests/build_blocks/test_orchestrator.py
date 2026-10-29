"""
Integration: build_blocks against real transform_lab_data output. Muscimol and a different rat's session are never selected; the in scope session registers and cuts without crashing, and its cut counts still partition every frame.
"""

from scripts.build_blocks import select
from scripts.build_blocks.orchestrator import build_session, load_tables


def test_scope_excludes_musc_and_the_other_rat(transformed_root):
    sessions, _, _ = load_tables(transformed_root)
    kept, skipped = select.select_sessions(sessions, rat_setting="")
    assert [s["session_id"] for s in kept] == ["NS14_rec1_20150219_001"]
    assert {session_id for session_id, _ in skipped} == {"NS14_rec2_20150219_002", "JL1_rec1_20140715_001"}


def test_in_scope_session_builds_without_crashing(transformed_root, protocol):
    import pyarrow.parquet as pq

    sessions, epochs_by_session, runs_by_session = load_tables(transformed_root)
    session_row = next(s for s in sessions if s["session_id"] == "NS14_rec1_20150219_001")
    table = pq.read_table(transformed_root / "frames" / f"{session_row['session_id']}.parquet")
    frames = {name: table.column(name).to_numpy(zero_copy_only=False) for name in table.column_names}

    blocks, info = build_session(session_row, epochs_by_session[session_row["session_id"]],
                                  runs_by_session[session_row["session_id"]], frames, protocol)

    assert blocks is not None, info
    for epoch_name, counts in info["cut_counts"].items():
        epoch = next(e for e in epochs_by_session[session_row["session_id"]] if e["epoch"] == epoch_name)
        assert sum(counts.values()) == epoch["frame_end"] - epoch["frame_start"] + 1
