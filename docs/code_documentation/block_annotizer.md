# Block annotizer: what it shows and what it writes

What `scripts/block_annotizer/` does, kept up to date with the code. Run as `pixi run block-annotizer`.

## Modules

- `__main__.py`: the command line and the main loop, list the datasets, write the summary, or open the window.
- `annotator.py`: the `Annotator` window class, its keys and the terminal prompts.
- `figures.py`: the drawing as plain functions, the environment and limits, occupancy, heading rose, summary.
- `environments.py`: the triple T and the arena as RatInABox environments, from `scripts/build_blocks/maze.py`.
- `datasets.py`: finding a dataset under BLOCK_DATA and reading its files and blocks.
- `store.py`: the `Store` class that writes the `annotations/` folder.

## What it is for

A block dataset (`docs/code_documentation/build_blocks.md`) is the level of data an experiment
runs on. Before an experiment, someone should look at its blocks and record what they saw: which
blocks are fine, which to exclude and why, and which stretches of frames are odd. The annotizer is
that look. It reads a dataset and writes a sidecar folder beside the data. It never changes the
dataset's own files, so the manifest's content hash stays valid.

## The window

One block at a time, in `blocks.csv` order (by session, then arena, track, variant).

- The path in room metres, coloured by phase (outbound, return, dwell, pause, forage), with the grey
  walls of the RatInABox environment and a black cursor with a heading tick.
- Heading and speed against block time, sharing a slider that moves the cursor.
- The block's position occupancy (4 cm bins) and heading occupancy (10 degree bins, all frames,
  moving or not).
- The terminal prints the block's `blocks.csv` row, its session's track registration from
  `checks.json` (the scale with its x and y estimates, which agree when the perimeter is the right
  reference, and how far the start sits above the bottom corridor), its session's non ok warnings,
  its verdict and its annotations.

The outline is a RatInABox `Environment` built by `scripts/block_annotizer/environments.py` from
the constants in `scripts/build_blocks/maze.py`, the same geometry the registration used, so the
model can later run an agent in the very environment the blocks are read against. For `triple_t`
it is the paper's 1.60 by 1.25 m envelope as the boundary, the corridor walls of the outbound
centreline plus the perimeter return corridors (inferred from the paper's figure, as in
axis-of-travel-rnn), and the reward sites as objects. For `triple_t_rot45` and `triple_t_rot90` the
same is turned by the nominal angle about the room centre. That pivot is a drawing assumption, the
registration does not record where the maze was turned about, so a rotated outline that sits beside
the path rather than under it is not by itself a bad block. The block's measured rotation is printed
in the caption to compare. For `open_arena` it is a 32 sided circle of the nominal diameter centred
on the block's median position, since the registration holds no arena centre.

## Keys

| key | does |
|---|---|
| `n`, `p` | next and previous block |
| `g` | go to a block by id, prefix or number |
| left, right | move the cursor one frame |
| up, down | move the cursor one second |
| `[`, `]` | set the start and end mark at the cursor |
| `a` | annotate the marked stretch, tag and note typed in the terminal |
| `x` | drop this block's most recent annotation |
| `v` | the block's verdict (`ok`, `exclude`, `unsure`) and note |
| `N` | a dated note on the dataset as a whole |
| `o` | toggle the outline |
| `h` | print the keys |
| `q` | quit |

## `BLOCK_DATA/<run_name>/annotations/`

Created on first use. Every change is written at once.

### `annotations.csv`

One row per marked stretch.

| field | meaning |
|---|---|
| `annotation_id` | `{block_id}_a{NN}`, one above the highest number the block has, so a dropped number comes back |
| `block_id`, `session_id`, `environment` | copied from `blocks.csv` |
| `frame_start`, `frame_end` | the session's 1-based frame numbers, inclusive, the parquet's `frame` column |
| `t_start`, `t_end` | the same in seconds from the block's first frame |
| `tag` | one word, free, for example `tracking`, `dwell`, `off_track` |
| `note` | free text, may be empty |
| `author`, `created` | the login name and the UTC time |

### `notes.json`

One entry per block that was given a verdict, keyed by `block_id`: `verdict`, `note`, `author`,
`updated`. A block with no entry has not been judged. An experiment that wants only the blocks a
person passed joins `blocks.csv` to this file on `block_id` and keeps `verdict == "ok"`.

### `notes.md`

Dated lines about the dataset as a whole, appended by the `N` key or by hand.

### `summary_<environment>.png`

Written by `--summary`, one per environment present: position occupancy with the outline and the
heading rose, pooled over every block of that environment, titled and captioned with the dataset
name and commit.
