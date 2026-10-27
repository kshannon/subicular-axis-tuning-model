# subicular-axis-tuning-model

Describing how axis tuning develops in subicular neural cells.

This README a guide to running the project and to ensure maximum reproducibility/replicability.

## Setup
Install pixi for env control, which builds a `pixi.lock` and `.pixi/` resources.
```bash
curl -fsSL https://pixi.sh/install.sh | bash
git clone git@github.com:kshannon/subicular-axis-tuning-model.git
cd subicular-axis-tuning-model
pixi install
```

## Environment

`pixi.toml` lists what the project needs. `pixi.lock` records the exact versions that were installed, so everyone gets the same environment.

Run things inside it:

```bash
pixi run python script.py   # one command
pixi shell                  # a shell with the environment active
```

There are two environments:

- `default`: Python 3.12, PyTorch, NumPy, SciPy, pandas, matplotlib, seaborn, RatInABox, and the dev tools (pytest, Jupyter, nbstripout, papermill). Runs on Apple Silicon and Linux.
- `cuda`: the same, with a GPU build of PyTorch. Linux only. Install with `pixi install -e cuda` and run with `pixi run -e cuda ...`.

To add a package, add it to `pixi.toml` and run `pixi install`. That updates `pixi.lock`. Commit both files together.

## Editor

`.vscode/settings.json` points VS Code at the pixi Python and turns on pytest, Ruff and notebook formatting. `.vscode/extensions.json` lists the recommended extensions, VS Code offers to install them when the folder is opened.

## Agents

`AGENTS.md` tells coding agents how to work in this project: their role as a research collaborator, what they may do on their own, and what needs the researcher's approval. `CLAUDE.md` points Claude Code at it.

`docs/` holds the project's working record, which the agents read before acting:

- `PROJECT_BRIEF.md`: the scientific question and the current plan.
- `EXPERIMENT_PROTOCOL.md`: how experiments are validated and tested.
- `RESEARCH_LOG.md`: what was run, what was found, and what was decided.
- `MODELING_DECISIONS.md`: the modeling choices and why they were made.
