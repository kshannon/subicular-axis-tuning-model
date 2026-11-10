"""Refresh the site's figures and data from the main worktree: copies the poster figure parts (downscaled for the web), the figure 5 blocks, the certificate as a JS file and the two poster documents. Reads results/ of the main worktree only; writes under this folder. Run from this folder: python build_site.py"""
import csv
import json
import shutil
from pathlib import Path

from PIL import Image

HERE = Path(__file__).parent
MAIN = HERE.parent / "subicular-axis-tuning-model"
FIGURES = MAIN / "results" / "sfn-2026" / "sfn_2026_figures"
RESULTS_NB = MAIN / "results" / "sfn-2026" / "sfn_2026_results_section"
POSTER_DOCS = MAIN / "tmp" / "sfn_2026_poster"   # Kyle keeps the speech and brief in the gitignored tmp folder
MAX_WIDTH = 1800   # px, the widest a figure is shown

FIGURE_2 = ["12_chance_boxes_grey.png", "13_counts_and_fit.png", "13_counts_and_fit_legend.png", "14_trained_against_chance.png", "14_trained_against_chance_labelled.png", "14_trained_against_chance_legend.png"]


def copy_image(src: Path, dst: Path) -> None:
    im = Image.open(src)
    if im.width > MAX_WIDTH:
        im = im.resize((MAX_WIDTH, round(im.height * MAX_WIDTH / im.width)), Image.LANCZOS)
    dst.parent.mkdir(parents=True, exist_ok=True)
    im.save(dst, optimize=True)
    print(f"{dst.relative_to(HERE)}  {im.width}x{im.height}  {dst.stat().st_size // 1024} KB")


for name in FIGURE_2:
    copy_image(FIGURES / "figure_2" / name, HERE / "figures" / name)
blocks = sorted((FIGURES / "figure_5").glob("*_block.png"))
for src in blocks:
    copy_image(src, HERE / "figures" / "figure_5" / src.name)
copy_image(FIGURES / "figure_5" / "final_07_figure_5.png", HERE / "figures" / "figure_5" / "final_07_figure_5.png")

rows = list(csv.DictReader(open(RESULTS_NB / "certificate.csv")))
for r in rows:
    r["ok"] = r["ok"] == "True"
(HERE / "data").mkdir(exist_ok=True)
(HERE / "data" / "certificate.js").write_text("window.CERT = " + json.dumps(rows, ensure_ascii=False) + ";\n")
print(f"data/certificate.js  {len(rows)} statements, {sum(r['ok'] for r in rows)} hold")

(HERE / "docs").mkdir(exist_ok=True)
for name in ("speech_3min.md", "presentation_brief.md"):
    shutil.copy(POSTER_DOCS / name, HERE / "docs" / name)
    print(f"docs/{name}")
