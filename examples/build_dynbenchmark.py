"""Construct ``examples/dynbenchmark.ipynb`` — Python equivalent of
https://funkyheatmap.github.io/funkyheatmap/articles/dynbenchmark.html .
"""

from __future__ import annotations

from pathlib import Path

import nbformat as nbf
from nbclient import NotebookClient


HERE = Path(__file__).parent


def md(s): return nbf.v4.new_markdown_cell(s.strip("\n"))
def code(s): return nbf.v4.new_code_cell(s.strip("\n"))


CELLS = [
    md(
        """
# Recreating the dynbenchmark figures

Python port of [`articles/dynbenchmark.html`](https://funkyheatmap.github.io/funkyheatmap/articles/dynbenchmark.html).

In this notebook we reproduce the figures from
[Saelens et al. (2019), *A comparison of single-cell trajectory inference methods*](https://doi.org/10.1038/s41587-019-0071-9). The R vignette uses the bundled `dynbenchmark_data` object; we read the same fixture (exported via `tests/dump_vignette_data.R`) and feed it into `pyfunkyheatmap.funky_heatmap`.
"""
    ),
    md("## Load data"),
    md(
        """
The original R object is a list with five members: `data`, `column_info`,
`column_groups`, `row_info`, `row_groups`, and `palettes`. The dump script
writes each one to its canonical Python representation (CSV for tabular
parts, JSON for the palettes list and the per-cell list-columns).
"""
    ),
    code(
        """
%matplotlib inline
import json
from pathlib import Path
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from pyfunkyheatmap import funky_heatmap, position_arguments

matplotlib.rcParams['figure.dpi'] = 100

DATA = Path('../data/vignettes')

# main results frame — 51 methods × 159 columns
data = pd.read_csv(DATA / 'dynbenchmark_data.csv')

# decode list-columns: each cell is a JSON dict (named numeric vector in R)
with open(DATA / 'dynbenchmark_data_list_cols.txt') as f:
    list_cols = [line.strip() for line in f if line.strip()]

def _decode(cell):
    if isinstance(cell, float) and np.isnan(cell):
        return {}
    try:
        v = json.loads(cell)
    except (TypeError, json.JSONDecodeError):
        return {}
    return v if isinstance(v, dict) else {}

for col in list_cols:
    if col in data.columns:
        data[col] = data[col].map(_decode)

data.shape
"""
    ),
    md("## Process results"),
    md("The results table is one big data frame with 159 columns; here is a preview of a handful."),
    code(
        """
preview_cols = [
    'id',
    'method_source',
    'method_platform',
    'benchmark_overall_norm_correlation',
    'benchmark_overall_norm_featureimp_wcor',
    'benchmark_overall_norm_F1_branches',
    'benchmark_overall_norm_him',
    'benchmark_overall_overall',
]
data[preview_cols].head(8)
"""
    ),
    md(
        """
It's possible to use `funky_heatmap` to visualise a subset of the data
frame without providing additional metadata, but it will not have any of
the desired formatting.
"""
    ),
    code(
        """
g = funky_heatmap(data[preview_cols], fig_scale=0.2, dpi=100)
g
"""
    ),
    md("## Process column info"),
    md(
        """
Apart from the results themselves, the most important additional info is
the column info. This data frame contains information on how each column
should be formatted: which `geom`, which `group`, which `palette`, and a
JSON-encoded `options` dict that spreads into per-column overrides
(`width`, `legend`, `overlay`, …).
"""
    ),
    code(
        """
column_info = pd.read_csv(DATA / 'dynbenchmark_column_info.csv')
# strip wrapping quotes from any NA-coded strings R may have written
print('column_info shape:', column_info.shape)
column_info.head(10)
"""
    ),
    md(
        """
With just the data and the column info, we can already get a pretty good
funky heatmap. We restrict to the columns that actually appear in
`column_info` so unused 100+ columns don't have to be re-validated.
"""
    ),
    code(
        """
g = funky_heatmap(
    data,
    column_info=column_info,
    fig_scale=0.18,
    dpi=100,
)
g
"""
    ),
    md("## Finetuning the visualisation"),
    md("The figure can be fine-tuned by grouping the columns and rows and specifying custom palettes."),
    md("### Column groups"),
    code(
        """
column_groups = pd.read_csv(DATA / 'dynbenchmark_column_groups.csv')
column_groups
"""
    ),
    md("### Row info"),
    code(
        """
row_info = pd.read_csv(DATA / 'dynbenchmark_row_info.csv')
row_info.head(8)
"""
    ),
    md("### Row grouping"),
    code(
        """
row_groups = pd.read_csv(DATA / 'dynbenchmark_row_groups.csv')
row_groups
"""
    ),
    md("### Palettes"),
    code(
        """
with open(DATA / 'dynbenchmark_palettes.json') as f:
    palettes_raw = json.load(f)
# R serialises this as [{palette: name, colours: <list-or-dict>}, ...].
# A dict colours field encodes a *named* R palette (category -> hex); a list
# encodes an unnamed sequential ramp. Both are kept as-is for Python.
palettes = {entry['palette']: entry['colours'] for entry in palettes_raw}
list(palettes.keys())
"""
    ),
    md("## Generate funky heatmap"),
    md(
        """
The resulting visualisation contains all of the results by
[Saelens et al. (2019)](https://doi.org/10.1038/s41587-019-0071-9) in a single plot.

> Note that Figures 2 and 3 from the main paper and Supplementary Figure 2 were generated by making different subsets of the `column_info` and `column_groups` objects.
"""
    ),
    code(
        """
g = funky_heatmap(
    data=data,
    column_info=column_info,
    column_groups=column_groups,
    row_info=row_info,
    row_groups=row_groups,
    palettes=palettes,
    position_args=position_arguments(col_annot_offset=3.2),
    fig_scale=0.18,
    dpi=100,
)
g.save('../data/vignettes/dynbenchmark_py.png', dpi=130, facecolor='white')
print('saved dynbenchmark_py.png; w=', round(g.width,1), 'h=', round(g.height,1))
g
"""
    ),
    md(
        """
`funkyheatmap` automatically recommends a width and height for the
generated plot. To save the plot at the suggested dimensions:

```python
g.save('dynbenchmark.pdf', dpi=200)
```
"""
    ),
    md("### Side-by-side with the R reference"),
    code(
        """
import matplotlib.image as mpimg
fig, axes = plt.subplots(2, 1, figsize=(22, 28))
axes[0].imshow(mpimg.imread('../data/vignettes/dynbenchmark_R.png'));   axes[0].set_title('R reference (funkyheatmap)',  fontsize=20); axes[0].axis('off')
axes[1].imshow(mpimg.imread('../data/vignettes/dynbenchmark_py.png'));  axes[1].set_title('Python port (pyfunkyheatmap)', fontsize=20); axes[1].axis('off')
plt.tight_layout()
fig
"""
    ),
    md(
        """
## References

* Saelens, W., Cannoodt, R., Todorov, H. *et al.* **A comparison of single-cell trajectory inference methods.** *Nat Biotechnol* 37, 547–554 (2019). https://doi.org/10.1038/s41587-019-0071-9
* [`dynverse/dynbenchmark_results`](https://github.com/dynverse/dynbenchmark_results) — upstream raw results.
"""
    ),
]


def build():
    nb = nbf.v4.new_notebook()
    nb["cells"] = CELLS
    nb["metadata"] = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.10"},
    }
    path = HERE / "dynbenchmark.ipynb"
    nbf.write(nb, path)
    print(f"wrote {path}")
    client = NotebookClient(nb, timeout=600, kernel_name="python3",
                            resources={"metadata": {"path": str(HERE)}})
    client.execute()
    nbf.write(nb, path)
    print(f"executed {path}")


if __name__ == "__main__":
    build()
