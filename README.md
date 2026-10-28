# subicular-axis-tuning-model

Follow this README to get started and recreate this project. We hop this ensures maximum reproducibility/replicability.

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

## Lab Data Transformation and Intitial Block Processing

`scripts/transform_lab_data/` converts the lab's MATLAB tracking and analysis files into
CSV tables and Parquet frames. It's a one-off script to prepare raw lab data.

Setup, once:

```bash
cp configs/local.example.yaml configs/local.yaml
```

Edit `configs/local.yaml`  to point `LAB_DATA` at the lab's raw data folder and `TRANSFORMED_LAB_DATA` at where the converted output should go. We offer different flavors of running this transformation depending on your use case:

```bash
pixi run transform-lab-data               # convert everything
pixi run transform-lab-data -- --dry-run  # print what would convert and write, nothing written
pixi run transform-lab-data -- --only NS14_rec27_20150219_001   # one session (or its prefix)
pixi run transform-lab-data -- --sample 2 # the first 2 sessions per subject, in recording order
pixi run pytest tests/transform_lab_data  # run the test suite for this script
```
