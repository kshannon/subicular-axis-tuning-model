"""
Build a block dataset from the transformed lab data tables, run as pixi run build-blocks.
"""

import argparse
import sys
from pathlib import Path

import yaml

from . import select
from .orchestrator import build_dataset, load_tables

REPO_ROOT = Path(__file__).resolve().parents[2]
LOCAL_CONFIG = REPO_ROOT / "configs" / "local.yaml"
PROTOCOL_PATH = Path(__file__).resolve().parent / "build_protocol.yaml"
THRESHOLD_KEYS = ("pause_step_s", "jump_px", "max_gap_frames", "min_block_s")


def local_config():
    """
    The machine local paths of configs/local.yaml as a dict, empty when the file is absent.
    """
    if not LOCAL_CONFIG.is_file():
        return {}
    return yaml.safe_load(LOCAL_CONFIG.read_text()) or {}


def local_path(key, config):
    """
    The folder under key in the given config dict, a KeyError naming the key when it is missing.
    """
    if not config.get(key):
        raise KeyError(f"configs/local.yaml has no {key}")
    return Path(str(config[key])).expanduser()


def refuse(message):
    """
    Print a configuration problem to stderr and exit 2.
    """
    print(f"build_blocks: {message}", file=sys.stderr)
    raise SystemExit(2)


def load_protocol(path):
    """
    build_protocol.yaml validated by hand: rat is one of select.ALLOWED_RATS or empty, conditions are known, the four cut thresholds are positive numbers.
    """
    if not path.is_file():
        refuse(f"{path} is missing")
    raw = yaml.safe_load(path.read_text()) or {}
    rat = raw.get("rat") or ""
    if rat and rat not in select.ALLOWED_RATS:
        refuse(f"build_protocol.yaml rat {rat!r} not in {select.ALLOWED_RATS}")
    conditions = raw.get("conditions") or []
    unknown = sorted(set(conditions) - set(select.ALLOWED_CONDITIONS))
    if unknown:
        refuse(f"build_protocol.yaml conditions {unknown} not in {select.ALLOWED_CONDITIONS}")
    for key in THRESHOLD_KEYS:
        if not isinstance(raw.get(key), (int, float)) or raw[key] <= 0:
            refuse(f"build_protocol.yaml {key} must be a positive number")
    return {"rat": rat, "conditions": tuple(conditions), **{key: raw[key] for key in THRESHOLD_KEYS}}


def parse_args(argv):
    """
    The command line: --dry-run, --only PREFIX and --description TEXT, required unless --dry-run.
    """
    parser = argparse.ArgumentParser(
        prog="build_blocks", description="Build a block dataset from the transformed lab data tables.")
    parser.add_argument("--dry-run", action="store_true", help="print what would be built, then stop")
    parser.add_argument("--only", metavar="PREFIX", help="sessions whose id is PREFIX or continues it after an underscore")
    parser.add_argument("--description", metavar="TEXT",
                        help="what changed in scope or selection since the last build, part of the dataset folder's name")
    args = parser.parse_args(argv)
    if not args.dry_run and not args.description:
        parser.error("--description is required unless --dry-run")
    return args


def roots(config):
    """
    The resolved transformed data folder and the resolved BLOCK_DATA output folder, or exit 2 naming what is wrong.
    """
    try:
        transformed, block_data = (local_path(key, config).resolve() for key in ("TRANSFORMED_LAB_DATA", "BLOCK_DATA"))
    except KeyError as error:
        refuse(error.args[0])
    if not transformed.is_dir():
        refuse(f"TRANSFORMED_LAB_DATA {transformed} is not a folder")
    if block_data == transformed or transformed in block_data.parents:  # type: ignore
        refuse(f"BLOCK_DATA {block_data} is the transformed data or inside it")
    if block_data in transformed.parents:
        refuse(f"BLOCK_DATA {block_data} contains the transformed data {transformed}")
    repo = REPO_ROOT.resolve()
    if block_data == repo or repo in block_data.parents:
        refuse(f"BLOCK_DATA {block_data} is the repository {repo} or inside it")
    return transformed, block_data


def selected_sessions(sessions, protocol, only):
    """
    The sessions in scope under the protocol's rat setting, further narrowed by --only, and the ones left out with why.
    """
    kept, skipped = select.select_sessions(sessions, protocol["rat"])
    if only is not None:
        kept = [s for s in kept if s["session_id"] == only or s["session_id"].startswith(only + "_")]
    return kept, skipped


def dry_run(sessions, skipped, protocol):
    """
    Print the sessions that would build, the skipped ones with why, and the protocol in effect.
    """
    print("dry run, nothing is written")
    print(f"protocol: rat={protocol['rat'] or 'all'} conditions={protocol['conditions']}")
    print(f"sessions to build ({len(sessions)}):")
    for session in sessions:
        print(f"  {session['session_id']}  {session['subject_id']}  {session['protocol']}")
    print(f"skipped ({len(skipped)}):")
    for session_id, reason in skipped:
        print(f"  {session_id}: {reason}")


def summarize(run_name, manifest):
    """
    Print how many sessions built and failed, and where the dataset landed.
    """
    counts = manifest["counts"]
    print(f"{counts['sessions_built']} sessions built, {counts['sessions_failed']} failed, {counts['blocks_written']} blocks written")
    for session_id, reason in manifest["failed"].items():
        print(f"  failed: {session_id} ({reason})")
    print(f"dataset: {run_name}")


def main(argv=None, config=None):
    """
    Run the builder: 0 when every selected session built, 1 when any failed, SystemExit 2 for a bad setup.
    """
    args = parse_args(argv)
    protocol = load_protocol(PROTOCOL_PATH)
    transformed_root, block_data_root = roots(local_config() if config is None else config)
    sessions, epochs_by_session, runs_by_session = load_tables(transformed_root)
    kept, skipped = selected_sessions(sessions, protocol, args.only)
    if args.dry_run:
        dry_run(kept, skipped, protocol)
        return 0
    run_name, manifest = build_dataset(transformed_root, block_data_root, args.description, PROTOCOL_PATH, REPO_ROOT,
                                        kept, epochs_by_session, runs_by_session, protocol)
    summarize(run_name, manifest)
    return 1 if manifest["counts"]["sessions_failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
