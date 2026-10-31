"""
The drawing work as plain functions: a block's RatInABox environment and plot limits, the position occupancy image, the heading rose, and the pooled summary figure per environment.
"""

import textwrap
from collections import defaultdict

import numpy as np
import pandas as pd

from scripts.block_annotizer import environments
from scripts.block_annotizer.datasets import ARENA_ENVIRONMENT, ENVIRONMENT_ROTATION_DEG, ENVIRONMENT_WORDS, read_block

SUMMARY_PNG = "summary_{environment}.png"
OCCUPANCY_BIN_M = 0.04
HEADING_BINS = 36
MARGIN_M = 0.05


def environment_for(environment, x, y):
    """
    The block's RatInABox environment: the triple T at its nominal rotation, or the arena on the block's median position.
    """
    if environment == ARENA_ENVIRONMENT:
        return environments.arena((float(np.nanmedian(x)), float(np.nanmedian(y))))
    return environments.triple_t(ENVIRONMENT_ROTATION_DEG.get(environment, 0.0))


def limits(env, x, y):
    """
    The square x and y limits covering the frames and the environment with a margin.
    """
    ex0, ex1, ey0, ey1 = env.extent
    x0, x1 = min(np.nanmin(x), ex0) - MARGIN_M, max(np.nanmax(x), ex1) + MARGIN_M
    y0, y1 = min(np.nanmin(y), ey0) - MARGIN_M, max(np.nanmax(y), ey1) + MARGIN_M
    side = max(x1 - x0, y1 - y0)
    return (x0, x0 + side), (y0, y0 + side)


def draw_occupancy(ax, x, y, xlim, ylim):
    """
    Time per OCCUPANCY_BIN_M square bin as an image.
    """
    bins = [np.arange(xlim[0], xlim[1] + OCCUPANCY_BIN_M, OCCUPANCY_BIN_M),
            np.arange(ylim[0], ylim[1] + OCCUPANCY_BIN_M, OCCUPANCY_BIN_M)]
    counts, _, _ = np.histogram2d(x, y, bins=bins)
    masked = np.ma.masked_equal(counts.T, 0)
    ax.imshow(masked, origin="lower", extent=(bins[0][0], bins[0][-1], bins[1][0], bins[1][-1]), cmap="viridis",
              interpolation="nearest")
    ax.set_aspect("equal")
    ax.set_title(f"position occupancy, {int(OCCUPANCY_BIN_M * 100)} cm bins", fontsize=9)
    ax.tick_params(labelsize=7)


def draw_rose(ax, heading):
    """
    Frames per HEADING_BINS heading bin, a polar bar chart over every frame.
    """
    edges = np.linspace(-np.pi, np.pi, HEADING_BINS + 1)
    counts, _ = np.histogram(np.arctan2(np.sin(heading), np.cos(heading)), bins=edges)
    centres = edges[:-1] + np.pi / HEADING_BINS
    ax.bar(centres, counts, width=2 * np.pi / HEADING_BINS, color="tab:blue", alpha=0.7)
    ax.set_title(f"heading occupancy, {360 // HEADING_BINS} degree bins, all frames", fontsize=9, pad=12)
    ax.set_yticklabels([])
    ax.tick_params(labelsize=7)


def short_commit(manifest):
    """
    The first eight characters of the manifest's git commit, or a question mark.
    """
    return str(manifest.get("git_commit", "?"))[:8]


def summary(run_root, blocks, manifest, store):
    """
    One figure per environment pooling every block: position occupancy with the outline, and the heading rose, saved under annotations/.
    """
    import matplotlib.pyplot as plt
    by_environment = defaultdict(list)
    for row in blocks:
        by_environment[row["environment"]].append(row)
    for environment, rows in sorted(by_environment.items()):
        frames = pd.concat([read_block(run_root, row["block_id"]) for row in rows], ignore_index=True)
        x, y, heading = frames["x"].to_numpy(), frames["y"].to_numpy(), frames["heading"].to_numpy()
        env = environment_for(environment, x, y)
        xlim, ylim = limits(env, x, y)
        fig = plt.figure(figsize=(12, 5.8))
        ax_occ = fig.add_subplot(1, 2, 1)
        ax_rose = fig.add_subplot(1, 2, 2, projection="polar")
        draw_occupancy(ax_occ, x, y, xlim, ylim)
        environments.draw(ax_occ, env)
        ax_occ.set_xlim(*xlim)
        ax_occ.set_ylim(*ylim)
        draw_rose(ax_rose, heading)
        sessions = len({row["session_id"] for row in rows})
        seconds = sum(float(row["duration_s"]) for row in rows)
        env = ENVIRONMENT_WORDS.get(environment, environment)
        fig.suptitle(f"{env}: {len(rows)} blocks from {sessions} sessions, {seconds / 60:.1f} min, "
                     f"{len(frames)} frames", fontsize=12, y=0.97)
        fig.text(0.5, 0.02, textwrap.fill(
            f"Dataset {run_root.name}, commit {short_commit(manifest)}. Left, time spent per "
            f"{int(OCCUPANCY_BIN_M * 100)} cm bin in room metres over every block of this environment, grey walls are "
            f"the RatInABox environment. Right, frames per {360 // HEADING_BINS} degree heading bin over the same frames, all frames, "
            f"moving or not.", 160), ha="center", fontsize=8, color="0.3")
        fig.subplots_adjust(bottom=0.16, top=0.84)
        path = store.folder / SUMMARY_PNG.format(environment=environment)
        fig.savefig(path, dpi=130)
        plt.close(fig)
        print(f"{environment}: {len(rows)} blocks, {len(frames)} frames, wrote {path}")
