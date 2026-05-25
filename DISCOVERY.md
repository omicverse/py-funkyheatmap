# Discovery — funkyheatmap port

**Phase 0.5 of the omicverse-rebuildr protocol.**

## Existing port audit

| Candidate | Repo | Status | Decision |
|---|---|---|---|
| `funkyheatmappy` | https://github.com/funkyheatmap/funkyheatmappy | Independent Python port maintained by upstream authors. Uses Plotnine (ggplot-on-matplotlib). | **Not reused.** Plotnine introduces a heavy transitive dependency tree and is not under our control for the parity gate. We refactor into a matplotlib-only port that ships the geometry tables. |
| `funkyheatmapjs` | https://github.com/funkyheatmap/funkyheatmapjs | JavaScript / D3 web renderer. | Not applicable for the Python ecosystem. |
| `omicverse/py-funkyheatmap` | — | Does not exist. | **Proceed with port under this name.** |

## R dependency audit

| R dep | Used for | Python replacement | Reused or shimmed |
|---|---|---|---|
| `ggplot2` | rendering | matplotlib | shimmed (geom-by-geom) |
| `ggforce` | `geom_circle`, `geom_arc_bar` | matplotlib `patches.Circle`, `patches.Wedge` | shimmed |
| `patchwork` | `wrap_plots` | matplotlib subfigure layout | replaced by single-axes draw + optional legend strip |
| `cowplot` | `theme_nothing`, `draw_image` | `ax.axis('off')`, `ax.imshow` | shimmed |
| `RColorBrewer` | colour stops | hard-coded brewer tables in `palettes.py` | data lifted verbatim, MIT-compatible |
| `dplyr` / `tidyr` / `purrr` / `tibble` | DataFrame manipulation | pandas / numpy | replaced |
| `assertthat` | input checks | manual `ValueError` raises | replaced |
| `cli` | console messages | stdlib | dropped (silent) |
| `jsonlite` | parsing the `options` column | `json` (stdlib) | replaced |
| `stringr` | string utilities | stdlib | replaced |
| `magick` | image loading | `matplotlib.image.imread` | replaced |
| `Rdpack` | docs | sphinx / inline | dropped |

No upstream R dep is unportable; nothing requires shelling out to R at runtime.

## Conclusion

* No existing first-party Python port; the community port (`funkyheatmappy`) uses Plotnine and is not reused.
* Every R dependency has a pure-Python replacement; no rpy2 / R runtime required.
* Algorithm class: **visualisation / layout** — adapted Class 1 (deterministic numerical).
  Parity gate is per-cell geometry equality (`max|Δ| ≤ 1e-6` over `funkyrect_data` / `circle_data`).

**Decision: proceed with full port under `py-funkyheatmap` / `pyfunkyheatmap`.**
