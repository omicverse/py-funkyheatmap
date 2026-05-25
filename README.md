# py-funkyheatmap

**Pure-Python port of the R package [funkyheatmap](https://funkyheatmap.github.io/funkyheatmap/), built under the [omicverse-rebuildr](../omicverse-rebuildr/README.md) reference-driven porting protocol.**

Generate publication-ready, dynbenchmark-style data-frame heatmaps with
funky rectangles, circles, bars, pies, and text — directly from
`pandas.DataFrame` inputs, rendered with matplotlib, no R / ggplot
dependency.

| | |
|---|---|
| **Upstream** | [funkyheatmap 0.5.2](https://github.com/funkyheatmap/funkyheatmap) (R, MIT) |
| **Algorithm class** | Visualisation / layout — adapted Class 1 (deterministic geometry) |
| **Parity gate** | `max\|Δ\|` over `funkyrect_data` / `circle_data` ≤ 1e-6 on canonical fixture |
| **Achieved parity** | `max\|Δ\| = 0.0` on `xmin / xmax / ymin / ymax / corner_size / color_value` |
| **License** | MIT (matches upstream) |

## Install

```bash
pip install -e .            # editable, from this directory
```

`pyfunkyheatmap` needs only `numpy`, `pandas`, `matplotlib` — no R, no
rpy2, no system-level dependencies.

## Quick start

```python
import pandas as pd
from pyfunkyheatmap import funky_heatmap

df = pd.DataFrame({
    "id":  ["A", "B", "C", "D"],
    "x":   [0.10, 0.55, 0.80, 0.95],
    "y":   [0.50, 0.25, 0.75, 0.60],
    "tag": ["alpha", "beta", "gamma", "delta"],
})
fh = funky_heatmap(df)
fh.save("out.png", dpi=150, bbox_inches="tight")
```

See:
* [`examples/tutorial.ipynb`](examples/tutorial.ipynb) — five-example tour (default heatmap → custom column info → pies → multi-group dynbenchmark layout → R⇄Python parity diff).
* [`examples/scIB.ipynb`](examples/scIB.ipynb) — Python equivalent of [the R `scIB` vignette](https://funkyheatmap.github.io/funkyheatmap/articles/scIB.html). Same fixture, same `column_info`, same legends.
* [`examples/dynbenchmark.ipynb`](examples/dynbenchmark.ipynb) — Python equivalent of [the R `dynbenchmark` vignette](https://funkyheatmap.github.io/funkyheatmap/articles/dynbenchmark.html). Reproduces the Saelens et al. (2019) figure off the bundled `dynbenchmark_data` object.

All three notebooks ship pre-executed so GitHub renders them inline.

## Public API

`funky_heatmap(data, column_info, row_info, column_groups, row_groups, palettes, legends, position_args, scale_column, add_abc, *, fig=None, ax=None, fig_scale=0.25, dpi=100)`

Mirrors the R `funky_heatmap` signature. Returns a `FunkyHeatmap` object with:

* `fh.figure` — the matplotlib `Figure`
* `fh.geom_positions` — dict of per-glyph DataFrames (`row_pos`,
  `column_pos`, `rect_data`, `circle_data`, `funkyrect_data`,
  `pie_data`, `img_data`, `text_data`, `segment_data`)
* `fh.bounds`, `fh.width`, `fh.height` — layout extents
* `fh.save(path, **kwargs)` — convenience wrapper around `Figure.savefig`

Side-API: `verify_data`, `verify_column_info`, `verify_row_info`,
`verify_column_groups`, `verify_row_groups`, `verify_palettes`,
`verify_legends`, `scale_minmax`, `position_arguments`. Each matches its
R counterpart.

## Refactoring notes

The port is not a literal R-to-Python transliteration:

1. **One dataclass for layout knobs.** `position_arguments(...)` returns a
   typed dataclass that supports `pa.row_height` *and* `pa["row_height"]`
   — both styles work, so R-style mapping access and Python attribute
   access stay open.
2. **Geometry tables are first-class.** The R package builds them
   internally and emits ggplot layers; we keep them on the result so
   downstream code (e.g. custom annotations, alternative renderers) can
   subclass without forking.
3. **No `cowplot` / `patchwork` / `ggforce`.** Rounded rectangles are
   drawn from a hand-rolled cubic-Bézier path; pies use
   `matplotlib.patches.Wedge`; layout is bare matplotlib.
4. **Default-palette parity.** The `RColorBrewer` colour stops for the
   `Blues / Reds / YlOrBr / Greens / Greys` and `Set1 / Set2 / Set3 /
   Dark2` palettes are copied verbatim and interpolated with the same
   linear RGB ramp that `colorRampPalette` uses, so `palettes="Blues"`
   produces the same hex strings as in R.

## Parity gate

```
$ Rscript tests/r_reference_driver.R data        # produces data/r_basic_*.csv + data/r_basic.png
$ pytest tests/                                  # 8 / 8 pass
$ python examples/build_tutorial.py              # rebuilds and re-executes the notebook
```

The pre-registered gate is `max|Δ|` over the funkyrect / circle geometry
columns on the canonical fixture (`tests/r_reference_driver.R`).
Achieved: `max|Δ| = 0.0` — every coordinate matches R bit-for-bit.

See [`RECONSTRUCTION_REPORT.md`](RECONSTRUCTION_REPORT.md) for the full
audit trail.

## Layout

```
pyfunkyheatmap/
├── __init__.py          public surface
├── api.py               funky_heatmap entry point
├── verify.py            verify_* validators (one per R counterpart)
├── position.py          PositionArguments dataclass
├── positions.py         calculate_geom_positions + row/column layout
├── scale.py             scale_minmax
├── palettes.py          DEFAULT_PALETTES + brewer_pal + smear
└── figure.py            compose_figure + FunkyHeatmap + matplotlib draw

examples/
├── build_tutorial.py    nbformat script that builds + executes tutorial.ipynb
└── tutorial.ipynb       pre-executed tutorial (5 examples + R parity diff)

tests/
├── r_reference_driver.R Rscript that produces data/r_basic_*.csv
└── test_basic.py        pytest, 8 tests

funkyheatmap-ref/        upstream R source vendored for reference
data/                    canonical fixture (R + Python outputs)
```
