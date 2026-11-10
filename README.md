# Site branch for the SfN 2026 poster

Orphan branch `gh-pages`: a single static page (`index.html`, Tailwind and Alpine from CDNs, no build step) with the poster's figures under `figures/`. GitHub Pages serves it from the branch root; `.nojekyll` keeps Jekyll out of the way.

Edit on the `main` branch side: the figures come from `results/sfn-2026/sfn_2026_figures/figure_2` and `figure_5`, the text from `results/sfn-2026/sfn_2026_poster/`. A copy script on main (`scripts/sfn_2026/build_site.py`, to come) refreshes `figures/` here; commit and push this branch to publish.
