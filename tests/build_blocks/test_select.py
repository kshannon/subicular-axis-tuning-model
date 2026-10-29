"""
Selection: muscimol, acsf, dark, JL1HPCData and non NS14/15/16 sessions are never selected, rotation sessions and their variant epoch are.
"""

from scripts.build_blocks import select


def session(session_id, subject_id, protocol):
    return {"session_id": session_id, "subject_id": subject_id, "protocol": protocol}


def test_rats_in_scope_defaults_to_all_three_when_empty():
    assert select.rats_in_scope("") == select.ALLOWED_RATS
    assert select.rats_in_scope(None) == select.ALLOWED_RATS
    assert select.rats_in_scope("NS15") == ("NS15",)


def test_muscimol_acsf_dark_and_other_rats_are_skipped():
    sessions = [
        session("a", "NS14", "standard"),
        session("b", "NS14", "infusion"),       # muscimol or acsf, by transform_lab_data's own tagging
        session("c", "NS14", "dark"),
        session("d", "JL1", "standard"),         # a different rat's folder, e.g. JL1HPCData
        session("e", "NS15", "rotation"),
    ]
    kept, skipped = select.select_sessions(sessions, rat_setting="")
    assert [s["session_id"] for s in kept] == ["a", "e"]
    assert {session_id for session_id, _ in skipped} == {"b", "c", "d"}


def test_rat_setting_narrows_within_the_allowed_three():
    sessions = [session("a", "NS14", "standard"), session("b", "NS15", "standard")]
    kept, skipped = select.select_sessions(sessions, rat_setting="NS15")
    assert [s["session_id"] for s in kept] == ["b"]
    assert [session_id for session_id, _ in skipped] == ["a"]


def epoch(name, condition):
    return {"epoch": name, "condition": condition, "frame_start": 1, "frame_end": 10}


def test_selected_epochs_keeps_baseline_and_rotation_variant():
    epochs = [epoch("arena", "baseline"), epoch("track", "baseline"), epoch("variant", "rot90")]
    assert select.select_epochs(epochs) == epochs


def test_selected_epochs_drops_infusion_and_dark_tagged_epochs():
    epochs = [epoch("arena", "musc_bilateral"), epoch("track", "musc_bilateral"), epoch("variant", "musc_bilateral")]
    assert select.select_epochs(epochs) == []
