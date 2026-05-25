# RECONSTRUCTION_REPORT — py-funkyheatmap v0.1.0

## 1 · Identity

| Field | Value |
|---|---|
| Package | `pyfunkyheatmap` |
| Upstream | [funkyheatmap](https://github.com/funkyheatmap/funkyheatmap) 0.5.2 (R, MIT) |
| Algorithm class | Visualisation — adapted Class 1 (deterministic geometry) |
| Parity gate | `max\|Δ\| ≤ 1e-6` over per-cell `(xmin, xmax, ymin, ymax, corner_size, color_value)` |
| Achieved parity | `max\|Δ\| = 0.0` on canonical fixture |
| Audit class | A (translation-only; no algebraic rewrites required) |
| LOC | ~900 (vs ~1400 R) |
| License | MIT (upstream) — matched |
| Date | 2026-05-24 |

## 2 · R function coverage audit

Functions exported by the upstream `NAMESPACE` (`/funkyheatmap-ref/NAMESPACE`):

| R export | Python equivalent | Status |
|---|---|---|
| `funky_heatmap` | `pyfunkyheatmap.funky_heatmap` | ✅ ported |
| `position_arguments` | `pyfunkyheatmap.position_arguments` | ✅ ported (dataclass) |
| `scale_minmax` | `pyfunkyheatmap.scale_minmax` | ✅ ported |
| `verify_data` | `pyfunkyheatmap.verify_data` | ✅ ported |
| `verify_column_info` | `pyfunkyheatmap.verify_column_info` | ✅ ported |
| `verify_row_info` | `pyfunkyheatmap.verify_row_info` | ✅ ported |
| `verify_column_groups` | `pyfunkyheatmap.verify_column_groups` | ✅ ported |
| `verify_row_groups` | `pyfunkyheatmap.verify_row_groups` | ✅ ported |
| `verify_palettes` | `pyfunkyheatmap.verify_palettes` | ✅ ported |
| `verify_legends` | `pyfunkyheatmap.verify_legends` | ✅ ported (legends layer renders inline; standalone legend strip is deferred) |
| `geom_rounded_rect` | `pyfunkyheatmap.figure._rounded_rect_path` | ✅ ported (internal — cubic-Bézier path) |

Internal R helpers (`calculate_geom_positions`, `calculate_row_positions`, `calculate_column_positions`, `make_geom_data_processor`, `score_to_funky_rectangle`, `compose_ggplot`, `compute_bounds`, `add_column_if_missing`, `is_color`, `if_list_to_tibble`) are ported into `pyfunkyheatmap.positions` / `figure` / `verify` / `palettes`.

### Ecosystem reuse

| External replacement | What we get | LOC saved |
|---|---|---|
| `matplotlib.patches` (Rectangle, Circle, Wedge, PathPatch) | All glyph rasterisation | ~150 |
| `matplotlib.colors.LinearSegmentedColormap` | RGB colour ramping (replaces `grDevices::colorRampPalette`) | ~30 |
| `pandas` groupby / merge / melt | All DataFrame reshaping that `dplyr`/`tidyr` did | ~250 |
| `numpy` | All vectorised arithmetic | — |

Net: roughly 500 LOC of R helpers replaced by ecosystem calls.

## 3 · Parity evidence

Canonical fixture: 8-row × 5-column toy frame; 3 numeric columns rendered
as 2× `funkyrect` + 1× `circle` (see `tests/r_reference_driver.R`). Both
sides read byte-identical input from `data/r_basic.csv`.

| Output table | Rows | Compared columns | max |Δ| | mean |Δ| | Pass? |
|---|---:|---|---:|---:|---|
| `funkyrect_data` | 16 | `xmin, xmax, ymin, ymax, corner_size, size_value, color_value` | **0.000000** | 0.000000 | ✅ |
| `circle_data` | 8 | `x0, y0, r, color_value, xmin, xmax, ymin, ymax` | **0.000000** | 0.000000 | ✅ |

Reproduce:

```bash
# in CMAP conda env
Rscript tests/r_reference_driver.R data

# in omicdev conda env
pytest tests/                       # 8 pass
python examples/build_tutorial.py   # re-runs notebook, last cell prints max|Δ|
```

## 4 · Acceleration evidence

This is a class-A port (translation-only); no algebraic rewrites were
attempted. The Python implementation already runs end-to-end on the
canonical fixture in ~0.4 s; we did not pursue further acceleration. If
performance is needed for ~1000+ row heatmaps, the obvious next step is
to batch the per-cell patch construction into a single `PatchCollection`
— admissibility class (E), exact identity.

## 5 · Code quality audit

| Check | Result |
|---|---|
| `pip install -e .` clean | ✅ |
| `pytest tests/` | ✅ 8/8 pass |
| Pre-executed `examples/tutorial.ipynb` (5 examples + parity diff) | ✅ |
| Image outputs embedded in notebook | ✅ 6 PNGs |
| License compatible (MIT⇄MIT) | ✅ |
| Upstream version pinned (0.5.2) | ✅ |
| No new conda env required | ✅ (works in `omicdev`) |
| R reference reproducible (`CMAP` env) | ✅ |

## 6 · Known limitations

* **Standalone legend strip.** The R package emits a strip of `legend`
  panels below the main plot via `patchwork::wrap_plots`. The Python
  port renders the main panel; per-palette legends are deferred (their
  geom positions are computed but they are not drawn as separate
  matplotlib axes yet). Workaround: legends are usually inferred from
  the colour ramp visible on the funkyrect glyphs themselves.
* **`magick` image geom.** Loaded via `matplotlib.image.imread`; falls
  back silently if a file does not exist. R's `magick` also supports
  URLs — not implemented.
* **Font sizing.** `ggplot size = 4` maps to roughly `matplotlib
  fontsize 10` via a 2.4× heuristic. Pixel-exact text positioning
  is not part of the parity gate.

None of these block the geometry parity gate or the published tutorial.

## 7 · Integration into omicverse

* Vendor location: `omicverse_traj_dev/py-funkyheatmap`.
* Public API: top-level `from pyfunkyheatmap import funky_heatmap`.
* Tutorial slot: `examples/tutorial.ipynb` — five-section notebook
  ending with the R⇄Python diff.
* Conda envs:
  * `omicdev` (Python) — package + tests + notebook execution.
  * `CMAP` (R) — produces the reference fixture via
    `tests/r_reference_driver.R`.

## 8 · Sign-off

| Field | Value |
|---|---|
| Author | omicverse-rebuildr agent session |
| Date | 2026-05-24 |
| Active time | ~1 working day |
| Final audit class | **A** (translation-only) |
| Parity gate | `max\|Δ\| = 0` on funkyrect / circle geometry — pass |
| Status | **Done.** Wheel-buildable, tests green, notebook pre-executed, R reference reproducible. |
