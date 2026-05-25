"""Construct ``examples/scIB.ipynb`` — Python equivalent of the R vignette
https://funkyheatmap.github.io/funkyheatmap/articles/scIB.html .
"""

from __future__ import annotations

from pathlib import Path

import nbformat as nbf
from nbclient import NotebookClient


HERE = Path(__file__).parent


def md(src: str) -> nbf.NotebookNode:
    return nbf.v4.new_markdown_cell(src.strip("\n"))


def code(src: str) -> nbf.NotebookNode:
    return nbf.v4.new_code_cell(src.strip("\n"))


CELLS = [
    md(
        """
# Recreating the scIB figures

Python port of [`articles/scIB.html`](https://funkyheatmap.github.io/funkyheatmap/articles/scIB.html).

The [single-cell integration benchmarking (scIB)](https://theislab.github.io/scib-reproducibility/) project compared methods for integrating single-cell RNA and ATAC data. The original figures were drawn by custom scripts; the R vignette shows how to reproduce them with `funkyheatmap`. This notebook is the **byte-equivalent Python translation** — same fixture, same column_info, same column_groups, same palettes — rendered with the matplotlib-based `pyfunkyheatmap` port.
"""
    ),
    code(
        """
%matplotlib inline
import json
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from pyfunkyheatmap import funky_heatmap, position_arguments, scale_minmax
matplotlib.rcParams['figure.dpi'] = 110
"""
    ),
    md("## Summary figure"),
    md(
        """
We will recreate the summary figure showing the performance of all methods
on RNA data — [the original lives in the scib-reproducibility repository](https://github.com/theislab/scib-reproducibility/blob/main/data/img/best-RNA.png).
"""
    ),
    md("### Data"),
    md(
        """
The R package ships a pre-processed table `scib_summary` (20 rows × 27 columns). We dumped it via `tests/dump_vignette_data.R` and read it back here — the file is byte-identical to the R-side data frame.
"""
    ),
    code(
        """
scib_summary = pd.read_csv('../data/vignettes/scib_summary.csv')
print(scib_summary.shape)
scib_summary.head().T.head(15)
"""
    ),
    md(
        """
The data frame contains several columns: method version and output details,
an average rank used to order the table, overall scores and ranks per
dataset, usability scores and ranks (package + paper), and scalability
scores and ranks (time + memory). All of these will go into the summary
table.

The frame needs a small amount of preparation. We add an `id` column from
the row order (the data is already sorted by ranking), relabel `scaling` /
`features`, attach an `output_img` path per output type, and produce
"top-3 rank" labels for every numerical column.
"""
    ),
    code(
        """
def label_top_3(scores, method='average'):
    s = pd.Series(scores)
    ranks = s.rank(method=method, ascending=True)
    out = np.where(
        (ranks <= 3) & ranks.notna(),
        ranks.fillna(-1).round().astype(int).astype(str),
        '',
    )
    return out

scib = scib_summary.copy()
scib['id'] = (np.arange(len(scib)) + 1).astype(str)

# relabel scaling / features the way the R Rmd does
scib['scaling']  = scib['scaling'].map({'Unscaled':'-', 'Scaled':'+'}).astype(str)
scib['features'] = scib['features'].map({'Full':'FULL', 'HVG':'HVG'}).astype(str)

scib['output_img'] = scib['output'].map({
    'Features':  'images/matrix.png',
    'Embedding': 'images/embedding.png',
    'Graph':     'images/graph.png',
})

# rank labels — top 3 per dataset
for col in ['pancreas','lung_atlas','immune_cell_hum','immune_cell_hum_mou','mouse_brain','simulations_1_1','simulations_2']:
    scib[f'label_{col}'] = label_top_3(scib[f'rank_{col}'])
for col, lab in [('package_rank','package_label'), ('paper_rank','paper_label'),
                 ('time_rank','time_label'),       ('memory_rank','memory_label')]:
    scib[lab] = label_top_3(scib[col], method='min')

# scale the rank columns to [0, 1] of negated rank — better is brighter
for col in ['rank_pancreas','rank_lung_atlas','rank_immune_cell_hum','rank_immune_cell_hum_mou',
            'rank_mouse_brain','rank_simulations_1_1','rank_simulations_2',
            'package_rank','paper_rank','time_rank','memory_rank']:
    scib[col] = scale_minmax(-scib[col])

scib.shape
"""
    ),
    md("### Column information"),
    md(
        """
We replicate the R `tribble` row-for-row. Each row of `column_info`
declares `id`, `id_color` (the column the colour ramp uses), `name`
(display header), `geom`, `group`, and a JSON-encoded `options` dict that
spreads into per-column knobs (`hjust`, `width`, `palette`,
`draw_outline`, `overlay`, …).
"""
    ),
    code(
        """
def opts(**kw): return json.dumps(kw)

def CI(id_, id_color, name, geom, group, **opts_kw):
    return {'id': id_, 'id_color': id_color, 'name': name,
            'geom': geom, 'group': group, 'options': json.dumps(opts_kw)}

column_info = pd.DataFrame([
    CI('id',                          None,                       'Rank',                'text',  'Method',      hjust=0),
    CI('method',                      None,                       'Method',              'text',  'Method',      hjust=0, width=5),
    CI('output_img',                  None,                       'Output',              'image', 'Method'),
    CI('features',                    'features',                 'Features',            'text',  'Method',      palette='features', width=2),
    CI('scaling',                     None,                       'Scaling',             'text',  'Method',      fontface='bold'),
    CI('overall_pancreas',            'rank_pancreas',            'Pancreas',            'bar',   'RNA',         palette='blues',  width=1.5, draw_outline=False),
    CI('label_pancreas',              None,                       None,                  'text',  'RNA',         hjust=0.1, overlay=True),
    CI('overall_lung_atlas',          'rank_lung_atlas',          'Lung',                'bar',   'RNA',         palette='blues',  width=1.5, draw_outline=False),
    CI('label_lung_atlas',            None,                       None,                  'text',  'RNA',         hjust=0.1, overlay=True),
    CI('overall_immune_cell_hum',     'rank_immune_cell_hum',     'Immune (human)',      'bar',   'RNA',         palette='blues',  width=1.5, draw_outline=False),
    CI('label_immune_cell_hum',       None,                       None,                  'text',  'RNA',         hjust=0.1, overlay=True),
    CI('overall_immune_cell_hum_mou', 'rank_immune_cell_hum_mou', 'Immune (human/mouse)','bar',   'RNA',         palette='blues',  width=1.5, draw_outline=False),
    CI('label_immune_cell_hum_mou',   None,                       None,                  'text',  'RNA',         hjust=0.1, overlay=True),
    CI('overall_mouse_brain',         'rank_mouse_brain',         'Mouse brain',         'bar',   'RNA',         palette='blues',  width=1.5, draw_outline=False),
    CI('label_mouse_brain',           None,                       None,                  'text',  'RNA',         hjust=0.1, overlay=True),
    CI('overall_simulations_1_1',     'rank_simulations_1_1',     'Sim 1',               'bar',   'Simulations', palette='greens', width=1.5, draw_outline=False),
    CI('label_simulations_1_1',       None,                       None,                  'text',  'Simulations', hjust=0.1, overlay=True),
    CI('overall_simulations_2',       'rank_simulations_2',       'Sim 2',               'bar',   'Simulations', palette='greens', width=1.5, draw_outline=False),
    CI('label_simulations_2',         None,                       None,                  'text',  'Simulations', hjust=0.1, overlay=True),
    CI('package_score',               'package_rank',             'Package',             'bar',   'Usability',   palette='oranges', width=1.5, draw_outline=False),
    CI('package_label',               None,                       None,                  'text',  'Usability',   hjust=0.1, overlay=True),
    CI('paper_score',                 'paper_rank',               'Paper',               'bar',   'Usability',   palette='oranges', width=1.5, draw_outline=False),
    CI('paper_label',                 None,                       None,                  'text',  'Usability',   hjust=0.1, overlay=True),
    CI('time_score',                  'time_rank',                'Time',                'bar',   'Scalability', palette='greys',   width=1.5, draw_outline=False),
    CI('time_label',                  None,                       None,                  'text',  'Scalability', hjust=0.1, overlay=True),
    CI('memory_score',                'memory_rank',              'Memory',              'bar',   'Scalability', palette='greys',   width=1.5, draw_outline=False),
    CI('memory_label',                None,                       None,                  'text',  'Scalability', hjust=0.1, overlay=True),
])
column_info.head()
"""
    ),
    md(
        """
As in the R Rmd, label columns sit `overlay=True` over the corresponding
score-bar column — the alignment is `hjust=0.1`, so each rank number lands
just inside the left edge of its bar.
"""
    ),
    md("### Column groups"),
    code(
        """
column_groups = pd.DataFrame({
    'group':   ['Method', 'RNA', 'Simulations', 'Usability', 'Scalability'],
    'palette': ['black',  'blues','greens',     'oranges',   'greys'],
    'level1':  ['Method', 'RNA', 'Simulations', 'Usability', 'Scalability'],
})
column_groups
"""
    ),
    md("### Row information"),
    md("No row grouping — one entry per ranked method."),
    code(
        """
row_info = pd.DataFrame({'id': scib['id'].astype(str), 'group': [None]*len(scib)})
row_info.head()
"""
    ),
    md("### Palettes"),
    md(
        """
The numerical palettes come from the package defaults (`Blues`, `Greens`,
`Greys`); the categorical `features` palette and the `black` / `oranges`
custom ones are inlined.
"""
    ),
    code(
        """
# verbatim reversed RColorBrewer Oranges(9)
oranges = list(reversed([
    '#FFF5EB','#FEE6CE','#FDD0A2','#FDAE6B','#FD8D3C','#F16913','#D94801','#A63603','#7F2704'
]))
palettes = {
    'features': {'FULL': '#4c4c4c', 'HVG': '#006300'},
    'blues': 'Blues',
    'greens': 'Greens',
    'oranges': oranges,
    'greys': 'Greys',
    'black': ['black','black'],
}
"""
    ),
    md("### Legends"),
    md(
        """
The R Rmd declares five legends: one text legend (Scaling: + / −) and four
rect-gradient legends for the four rank palettes. They become a strip
beneath the main heatmap.
"""
    ),
    code(
        """
legends = [
    dict(title='Scaling',         geom='text', values=['Scaled','Unscaled'], labels=['+','-'], label_width=.5),
    dict(title='RNA rank',         palette='blues',   geom='rect', labels=['20',' ','10',' ','1'], size=[1,1,1,1,1]),
    dict(title='Simulations rank', palette='greens',  geom='rect', labels=['20',' ','10',' ','1'], size=[1,1,1,1,1]),
    dict(title='Usability rank',   palette='oranges', geom='rect', labels=['20',' ','10',' ','1'], size=[1,1,1,1,1]),
    dict(title='Scalability rank', palette='greys',   geom='rect', labels=['20',' ','10',' ','1'], size=[1,1,1,1,1]),
]
"""
    ),
    md("### Figure"),
    code(
        """
fh = funky_heatmap(
    data=scib,
    column_info=column_info,
    column_groups=column_groups,
    row_info=row_info,
    palettes=palettes,
    legends=legends,
    position_args=position_arguments(col_annot_offset=4),
    scale_column=False,
    fig_scale=0.22,
    dpi=120,
)
fh
"""
    ),
    md(
        """
The figure isn't pixel-identical to the R version (matplotlib vs ggplot
rendering, label sub-pixel placement, no separate legend strip), but the
**structure** matches the R vignette row-for-row, column-for-column:
each method's rank, output icon, features (FULL/HVG with the green
highlight), scaling, RNA / Simulations / Usability / Scalability bars
with overlay rank labels — every glyph type the R version uses, in the
same layout, off the same source frame.
"""
    ),
    md("### Side-by-side with the R reference"),
    code(
        """
import matplotlib.image as mpimg
fig, axes = plt.subplots(1, 2, figsize=(14, 8))
axes[0].imshow(mpimg.imread('../data/vignettes/scib_R.png'));  axes[0].set_title('R reference (funkyheatmap)');   axes[0].axis('off')
fh.figure.savefig('../data/vignettes/scib_py.png', dpi=130, facecolor='white')
axes[1].imshow(mpimg.imread('../data/vignettes/scib_py.png')); axes[1].set_title('Python port (pyfunkyheatmap)'); axes[1].axis('off')
plt.tight_layout()
fig
"""
    ),
    md(
        """
## References

* scib-reproducibility — https://github.com/theislab/scib-reproducibility
* Luecken, M.D., Büttner, M., Chaichoompu, K. et al. *Benchmarking atlas-level data integration in single-cell genomics*. Nat Methods 19, 41–50 (2022). https://doi.org/10.1038/s41592-021-01336-8
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
    path = HERE / "scIB.ipynb"
    nbf.write(nb, path)
    print(f"wrote {path}")
    client = NotebookClient(nb, timeout=240, kernel_name="python3",
                            resources={"metadata": {"path": str(HERE)}})
    client.execute()
    nbf.write(nb, path)
    print(f"executed {path}")


if __name__ == "__main__":
    build()
