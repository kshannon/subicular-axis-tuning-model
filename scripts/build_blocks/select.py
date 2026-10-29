"""
Which sessions and epochs build_blocks works with: protocol, rat and epoch rules, and the reason a session or epoch is left out. Never excludes by anything other than these rules: a verdict after the build is how a person excludes.
"""

from .maze import ARENA, NOMINAL_ROTATION_DEG, TRACK, VARIANT

# Muscimol and acsf sessions carry protocol "infusion" (transform_lab_data's own TAGS mapping), dark sessions
# protocol "dark", an unrecognised tag "other": none of these are ever selected regardless of build_protocol.yaml.
SELECTED_PROTOCOLS = ("standard", "rotation")

# JL1HPCData is a different rat's folder (DATA_DICTIONARY.md: one folder per rat), excluded simply by never being
# one of these three. build_protocol.yaml's own `rat` setting only ever narrows within this set.
ALLOWED_RATS = ("NS14", "NS15", "NS16")

BASELINE_EPOCHS = ((ARENA, "baseline"), (TRACK, "baseline"))
VARIANT_CONDITIONS = tuple(NOMINAL_ROTATION_DEG)
ALLOWED_CONDITIONS = ("baseline", *VARIANT_CONDITIONS)

OUT_PROTOCOL = "protocol {protocol!r} not in {selected}"
OUT_RAT = "subject_id {subject_id!r} not in {rats}"


def rats_in_scope(rat_setting):
    """
    The rats build_protocol.yaml's rat setting selects: all of ALLOWED_RATS when it is empty, else just that one.
    """
    return ALLOWED_RATS if not rat_setting else (rat_setting,)


def select_sessions(sessions, rat_setting):
    """
    The sessions in scope and the skipped ones with why, from the sessions.csv rows and the rat setting.
    """
    rats = rats_in_scope(rat_setting)
    kept, skipped = [], []
    for session in sessions:
        if session["protocol"] not in SELECTED_PROTOCOLS:
            skipped.append((session["session_id"], OUT_PROTOCOL.format(protocol=session["protocol"], selected=SELECTED_PROTOCOLS)))
        elif session["subject_id"] not in rats:
            skipped.append((session["session_id"], OUT_RAT.format(subject_id=session["subject_id"], rats=rats)))
        else:
            kept.append(session)
    return kept, skipped


def select_epochs(epochs):
    """
    This session's epochs that build_blocks works with: arena/baseline, track/baseline, and a variant epoch under rot45 or rot90.
    """
    return [e for e in epochs if (e["epoch"], e["condition"]) in BASELINE_EPOCHS
            or (e["epoch"] == VARIANT and e["condition"] in VARIANT_CONDITIONS)]
