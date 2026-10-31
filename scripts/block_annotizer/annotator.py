"""
The Annotator window: steps through a dataset's blocks, draws each on its RatInABox environment with a time cursor, heading and speed under a slider and the block's occupancy, and takes the keys that mark, annotate and judge.
"""

import textwrap

import numpy as np

from scripts.block_annotizer import environments
from scripts.block_annotizer.datasets import ARENA_ENVIRONMENT, ENVIRONMENT_WORDS, read_block
from scripts.block_annotizer.figures import draw_occupancy, draw_rose, environment_for, limits, short_commit
from scripts.block_annotizer.store import VERDICTS

PHASE_COLORS = {"outbound": "tab:blue", "return": "tab:orange", "dwell": "tab:green", "pause": "tab:red",
                "forage": "tab:purple"}
PATH_ALPHA = 0.3
STEP_SECONDS = 1.0
ANNOTATION_COLOR = "gold"
CAPTION_WIDTH = 190

KEYS = """keys: n next block, p previous, g go to a block, left/right one frame, up/down one second,
      [ mark start at the cursor, ] mark end, a annotate the marked stretch, x drop this block's last annotation,
      v verdict and note for the block, N a dated note on the dataset, o toggle the outline, h these keys, q quit"""


def describe(index, total, row, checks, store):
    """
    Print the block's row, its session's warnings, its verdict and its annotations to the terminal.
    """
    env = ENVIRONMENT_WORDS.get(row["environment"], row["environment"])
    print(f"\n[{index + 1}/{total}] {row['block_id']}  {env}  {float(row['duration_s']):.1f} s  "
          f"{row['n_frames']} frames at {row['rate_hz']} Hz  frames {row['frame_start']} to {row['frame_end']}")
    print(f"  runs {row['n_runs']} (clean {row['n_clean_runs']})  trips {row['n_trips']} (complete "
          f"{row['n_complete_trips']})  heading lost {row['heading_lost_s']} s filled {row['heading_filled_s']} s "
          f"held {row['heading_held_s']} s  rotation {np.rad2deg(float(row['rotation_rad'])):.1f} deg"
          + (f"  measured {float(row['maze_deg_measured']):.1f} deg" if row.get("maze_deg_measured") else ""))
    track = checks.get(row["session_id"], {}).get("registration", {}).get("track")
    if track:
        print(f"  registration: scale {track['scale_px_per_m']:.0f} px/m from x {track['scale_x_px_per_m']:.0f} and y "
              f"{track['scale_y_px_per_m']:.0f}, start {track['start_offset_measured_m']:.3f} m above the bottom corridor")
    warnings = checks.get(row["session_id"], {}).get("warnings", {})
    flagged = []
    for name, value in warnings.items():
        if isinstance(value, dict) and value.get("status") not in (None, "ok"):
            flagged.append(f"{name} {value.get('status')} ({value.get('detail', '')})")
        elif isinstance(value, dict):
            for epoch_name, items in value.items():
                if isinstance(items, list) and items:
                    flagged.append(f"{name} {epoch_name}: {', '.join(map(str, items))}")
    print("  warnings: " + ("; ".join(flagged) if flagged else "none"))
    note = store.notes.get(row["block_id"])
    print("  verdict: " + (f"{note['verdict']}  {note['note']}" if note else "not yet given"))
    for a in store.for_block(row["block_id"]):
        print(f"  {a['annotation_id'].rsplit('_', 1)[1]} frames {a['frame_start']} to {a['frame_end']} "
              f"({a['t_start']} to {a['t_end']} s) {a['tag']}: {a['note']}")


def ask(prompt, default=""):
    """
    One line from the terminal, the default when the line is empty.
    """
    answer = input(prompt).strip()
    return answer or default


def ask_verdict(current):
    """
    A verdict from VERDICTS and a note, enter keeping the current ones.
    """
    while True:
        verdict = ask(f"  verdict {'/'.join(VERDICTS)} [{current.get('verdict', '')}]: ", current.get("verdict", ""))
        if verdict in VERDICTS:
            break
        print(f"  one of {VERDICTS}")
    note = ask(f"  note [{current.get('note', '')}]: ", current.get("note", ""))
    return verdict, note


class Annotator:
    """
    The window: the path with its outline and a time cursor, heading and speed against time with a slider, the block's occupancy and heading rose, and the keys that step, mark and annotate.
    """

    def __init__(self, run_root, blocks, checks, manifest, store, start=0):
        import matplotlib.pyplot as plt
        self.plt = plt
        for key in [k for k in plt.rcParams if k.startswith("keymap.")]:
            plt.rcParams[key] = []
        self.run_root, self.blocks, self.checks, self.manifest, self.store = run_root, blocks, checks, manifest, store
        self.index, self.outline_on, self.marks = start, True, [None, None]
        self.fig = plt.figure(figsize=(14, 9))
        grid = self.fig.add_gridspec(4, 3, height_ratios=[3, 3, 1.1, 1.1], hspace=0.5, wspace=0.35, top=0.92,
                                     bottom=0.16, left=0.06, right=0.98)
        self.ax_path = self.fig.add_subplot(grid[0:2, 0:2])
        self.ax_occ = self.fig.add_subplot(grid[0, 2])
        self.ax_rose = self.fig.add_subplot(grid[1, 2], projection="polar")
        self.ax_head = self.fig.add_subplot(grid[2, :])
        self.ax_speed = self.fig.add_subplot(grid[3, :], sharex=self.ax_head)
        self.ax_slider = self.fig.add_axes([0.08, 0.015, 0.86, 0.02])
        self.caption = self.fig.text(0.5, 0.05, "", ha="center", va="bottom", fontsize=8, color="0.3")
        self.fig.canvas.mpl_connect("key_press_event", self.on_key)
        self.show_block()

    @property
    def row(self):
        return self.blocks[self.index]

    def show_block(self):
        """
        Load the current block and draw everything from scratch.
        """
        from matplotlib.widgets import Slider
        row = self.row
        self.frames = read_block(self.run_root, row["block_id"])
        self.marks = [None, None]
        self.cursor = 0
        f = self.frames
        self.t, self.x, self.y = f["t"].to_numpy(), f["x"].to_numpy(), f["y"].to_numpy()
        self.heading, self.speed = f["heading"].to_numpy(), f["speed"].to_numpy()
        self.env = environment_for(row["environment"], self.x, self.y)
        self.xlim, self.ylim = limits(self.env, self.x, self.y)
        for ax in (self.ax_path, self.ax_occ, self.ax_rose, self.ax_head, self.ax_speed, self.ax_slider):
            ax.clear()
        self.draw_path()
        draw_occupancy(self.ax_occ, self.x, self.y, self.xlim, self.ylim)
        draw_rose(self.ax_rose, self.heading)
        self.draw_traces()
        self.draw_annotations()
        rate = float(row["rate_hz"])
        self.slider = Slider(self.ax_slider, "t (s)", 0.0, float(self.t[-1]), valinit=0.0, valstep=1.0 / rate)
        self.slider.on_changed(self.on_slider)
        self.draw_cursor()
        env = ENVIRONMENT_WORDS.get(row["environment"], row["environment"])
        self.fig.suptitle(f"{row['block_id']}   {env}   {row['session_id']}   {float(row['duration_s']):.0f} s, "
                          f"{row['n_frames']} frames   block {self.index + 1} of {len(self.blocks)}", fontsize=11)
        measured = (f", measured rotation {float(row['maze_deg_measured']):.1f} deg" if row.get("maze_deg_measured")
                    else "")
        outline_words = ("the RatInABox arena of nominal diameter on the block's median position"
                         if row["environment"] == ARENA_ENVIRONMENT
                         else "the RatInABox triple T, the paper's envelope and corridors turned by the nominal rotation "
                              "about the room centre" + measured)
        self.caption.set_text(textwrap.fill(
            f"Dataset {self.run_root.name}, commit {short_commit(self.manifest)}. Path in room metres coloured by phase, "
            f"grey walls are {outline_words}. The slider moves the cursor (black dot and heading tick, black line in "
            f"the traces). Yellow spans are saved annotations, dashed lines the current marks.", CAPTION_WIDTH))
        describe(self.index, len(self.blocks), row, self.checks, self.store)
        self.fig.canvas.draw_idle()

    def draw_path(self):
        ax = self.ax_path
        phases = self.frames["phase"].to_numpy()
        for phase, color in PHASE_COLORS.items():
            on = phases == phase
            if on.any():
                ax.scatter(self.x[on], self.y[on], s=3, color=color, alpha=PATH_ALPHA, label=f"{phase} ({int(on.sum())})",
                           zorder=2)
        self.outline_artists = environments.draw(ax, self.env)
        for artist in self.outline_artists:
            artist.set_visible(self.outline_on)
        ax.set_xlim(*self.xlim)
        ax.set_ylim(*self.ylim)
        ax.set_aspect("equal")
        ax.set_xlabel("x (m)")
        ax.set_ylabel("y (m)")
        for handle in ax.legend(fontsize=7, loc="upper right", markerscale=3).legend_handles:
            handle.set_alpha(1)
        self.cursor_dot, = ax.plot([], [], "o", color="black", ms=7, zorder=5)
        self.cursor_tick, = ax.plot([], [], "-", color="black", lw=2, zorder=5)
        self.highlight = ax.scatter([], [], s=14, facecolors="none", edgecolors="black", linewidths=0.6, zorder=3)

    def draw_traces(self):
        degrees = np.rad2deg(np.arctan2(np.sin(self.heading), np.cos(self.heading)))
        self.ax_head.scatter(self.t, degrees, s=2, color="tab:blue")
        self.ax_head.set_ylabel("heading (deg)")
        self.ax_head.set_ylim(-180, 180)
        self.ax_head.set_yticks([-180, -90, 0, 90, 180])
        self.ax_speed.plot(self.t, self.speed, lw=0.8, color="tab:gray")
        self.ax_speed.set_ylabel("speed (m/s)")
        self.ax_speed.set_xlabel("t (s) from the block's first frame")
        self.ax_head.set_xlim(0, float(self.t[-1]))
        self.cursor_lines = [ax.axvline(0, color="black", lw=1) for ax in (self.ax_head, self.ax_speed)]
        self.mark_lines = []
        self.annotation_artists = []

    def draw_annotations(self):
        """
        Shade every saved annotation on the traces and outline its frames on the path.
        """
        for artist in self.annotation_artists:
            artist.remove()
        self.annotation_artists = []
        frame = self.frames["frame"].to_numpy()
        inside = np.zeros(len(frame), dtype=bool)
        for a in self.store.for_block(self.row["block_id"]):
            lo, hi = int(a["frame_start"]), int(a["frame_end"])
            on = (frame >= lo) & (frame <= hi)
            inside |= on
            t0, t1 = float(a["t_start"]), float(a["t_end"])
            for ax in (self.ax_head, self.ax_speed):
                self.annotation_artists.append(ax.axvspan(t0, t1, color=ANNOTATION_COLOR, alpha=0.35, zorder=0))
            self.annotation_artists.append(self.ax_head.text(t0, 170, a["tag"], fontsize=7, va="top"))
        self.highlight.set_offsets(np.column_stack([self.x[inside], self.y[inside]]) if inside.any() else np.empty((0, 2)))

    def draw_marks(self):
        for line in self.mark_lines:
            line.remove()
        self.mark_lines = []
        for mark in self.marks:
            if mark is not None:
                for ax in (self.ax_head, self.ax_speed):
                    self.mark_lines.append(ax.axvline(self.t[mark], color="black", lw=1, ls="--"))
        self.fig.canvas.draw_idle()

    def draw_cursor(self):
        i = self.cursor
        self.cursor_dot.set_data([self.x[i]], [self.y[i]])
        tick = 0.08 * (self.xlim[1] - self.xlim[0])
        self.cursor_tick.set_data([self.x[i], self.x[i] + tick * np.cos(self.heading[i])],
                                  [self.y[i], self.y[i] + tick * np.sin(self.heading[i])])
        for line in self.cursor_lines:
            line.set_xdata([self.t[i], self.t[i]])
        self.fig.canvas.draw_idle()

    def on_slider(self, value):
        self.cursor = int(np.clip(np.searchsorted(self.t, value), 0, len(self.t) - 1))
        self.draw_cursor()

    def move(self, frames):
        self.slider.set_val(float(self.t[int(np.clip(self.cursor + frames, 0, len(self.t) - 1))]))

    def step(self, blocks):
        self.index = int(np.clip(self.index + blocks, 0, len(self.blocks) - 1))
        self.show_block()

    def annotate(self):
        """
        Save the marked stretch with a tag and note typed in the terminal.
        """
        if self.marks[0] is None or self.marks[1] is None:
            print("  mark a start with [ and an end with ] first")
            return
        lo, hi = sorted(self.marks)
        frame = self.frames["frame"].to_numpy()
        print(f"  annotating frames {frame[lo]} to {frame[hi]} ({self.t[lo]:.2f} to {self.t[hi]:.2f} s)")
        tag = ask("  tag (one word, empty cancels): ")
        if not tag:
            print("  cancelled")
            return
        note = ask("  note: ")
        a = self.store.add(self.row, frame[lo], frame[hi], self.t[lo], self.t[hi], tag.split()[0], note)
        print(f"  saved {a['annotation_id']}")
        self.marks = [None, None]
        self.draw_marks()
        self.draw_annotations()
        self.fig.canvas.draw_idle()

    def on_key(self, event):
        key = event.key
        rate = float(self.row["rate_hz"])
        if key == "n":
            self.step(1)
        elif key == "p":
            self.step(-1)
        elif key == "g":
            target = ask("  block id, its prefix, or its number: ")
            ids = [r["block_id"] for r in self.blocks]
            hits = [i for i, b in enumerate(ids) if b == target or b.startswith(target)] if target else []
            if target.isdigit() and 1 <= int(target) <= len(ids):
                hits = [int(target) - 1]
            if len(hits) == 1:
                self.index = hits[0]
                self.show_block()
            else:
                print(f"  {len(hits)} blocks match")
        elif key == "right":
            self.move(1)
        elif key == "left":
            self.move(-1)
        elif key == "up":
            self.move(int(STEP_SECONDS * rate))
        elif key == "down":
            self.move(-int(STEP_SECONDS * rate))
        elif key == "[":
            self.marks[0] = self.cursor
            self.draw_marks()
        elif key == "]":
            self.marks[1] = self.cursor
            self.draw_marks()
        elif key == "a":
            self.annotate()
        elif key == "x":
            dropped = self.store.drop_last(self.row["block_id"])
            print(f"  dropped {dropped['annotation_id']}" if dropped else "  nothing to drop")
            self.draw_annotations()
            self.fig.canvas.draw_idle()
        elif key == "v":
            verdict, note = ask_verdict(self.store.notes.get(self.row["block_id"], {}))
            self.store.set_verdict(self.row["block_id"], verdict, note)
            print(f"  saved verdict {verdict}")
        elif key == "N":
            text = ask("  dataset note: ")
            if text:
                self.store.add_dataset_note(text)
                print(f"  appended to {self.store.md_path.name}")
        elif key == "o":
            self.outline_on = not self.outline_on
            for artist in self.outline_artists:
                artist.set_visible(self.outline_on)
            self.fig.canvas.draw_idle()
        elif key == "h":
            print(KEYS)
        elif key == "q":
            self.plt.close(self.fig)
