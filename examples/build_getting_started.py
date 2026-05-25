"""Construct ``examples/getting_started.ipynb`` — Python 1:1 port of
https://funkyheatmap.github.io/funkyheatmap/articles/funkyheatmap.html .
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
# Getting started with pyfunkyheatmap

Python port of the [Getting started](https://funkyheatmap.github.io/funkyheatmap/articles/funkyheatmap.html) R vignette.

We will use the classic `mtcars` dataset to showcase how to use **pyfunkyheatmap**, gradually adding features to the plot to show how to customise it.
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

matplotlib.rcParams['figure.dpi'] = 110
"""
    ),
    md("## Loading the data"),
    md(
        """
First, we load `mtcars`. We move the row names to a column named `id`, as
that is required by **pyfunkyheatmap** to display the row labels. We then
sort by the `mpg` column in descending order and keep the top 30 rows.
"""
    ),
    code(
        """
mtcars = pd.read_csv('../data/vignettes/mtcars.csv').rename(columns={'Unnamed: 0':'id'})
data = mtcars.sort_values('mpg', ascending=False).head(30).reset_index(drop=True)
data.head()
"""
    ),
    md("We can plot this data frame without any additional formatting, though it doesn't look very nice:"),
    code(
        """
funky_heatmap(data)
"""
    ),
    md("## Adding `column_info`"),
    md(
        """
We can add column information to the heatmap by specifying the `column_info`
argument. This should be a `DataFrame` with one row per heatmap column. The
required column is `id` (the data column to plot). All other columns are
optional and control the appearance.

If you want to group columns together (semantically related, or any other
logical grouping), specify the `group` column in `column_info`.
"""
    ),
    code(
        """
def opts(**kw): return json.dumps(kw)

cinfo = pd.DataFrame({
    'id': data.columns,
    'group': [None, 'Overall', 'Engine', 'Engine', 'Engine', 'Transmission',
              'Overall', 'Performance', 'Engine', 'Transmission',
              'Transmission', 'Engine'],
    'options': ['{}'] * 12,
})
cinfo
"""
    ),
    code(
        """
funky_heatmap(data, column_info=cinfo)
"""
    ),
    md(
        """
We can see that this doesn't work directly: we need to manually rearrange
the columns so that columns in the same group are adjacent to each other.
"""
    ),
    code(
        """
data = data[['id','qsec','mpg','wt','cyl','carb','disp','hp','vs','drat','am','gear']]

cinfo = pd.DataFrame({
    'id': data.columns,
    'group': [None, 'Performance', 'Overall', 'Overall',
              'Engine', 'Engine', 'Engine', 'Engine', 'Engine',
              'Transmission', 'Transmission', 'Transmission'],
    'options': ['{}'] * 12,
})
cinfo
"""
    ),
    code(
        """
funky_heatmap(data, column_info=cinfo)
"""
    ),
    md("We should probably also add a `name` column, to make the column labels more informative."),
    code(
        """
cinfo['name'] = ['Model','1/4 mile time','Miles per gallon','Weight',
                 'Number of cylinders','Carburetors','Displacement','Horsepower',
                 'Engine type','Rear axle ratio','Transmission','Forward gears']
funky_heatmap(data, column_info=cinfo)
"""
    ),
    md(
        """
This is better — at least the column groups are readable now. The column
groups themselves aren't very distinct visually, though. We can fix that by
adding a `palette` column to `column_info`.
"""
    ),
    md("## Adding palettes"),
    md(
        """
Adding a `palette` column on its own isn't enough — we also need to pass a
`palettes` dict, where keys correspond to the values in the `palette`
column and values are one of the predefined palettes:

For numerical data: `Blues`, `Reds`, `Greens`, `YlOrBr`, `Greys`.

For categorical data: `Set1`, `Set2`, `Set3`, `Dark2`.
"""
    ),
    code(
        """
cinfo['palette'] = [None, 'perf_palette',
                    'overall_palette', 'overall_palette',
                    'engine_palette', 'engine_palette', 'engine_palette',
                    'engine_palette', 'engine_palette',
                    'transmission_palette', 'transmission_palette', 'transmission_palette']

palettes = {
    'perf_palette':         'Blues',
    'overall_palette':      'Greens',
    'engine_palette':       'YlOrBr',
    'transmission_palette': 'Reds',
}

funky_heatmap(data, column_info=cinfo, palettes=palettes)
"""
    ),
    md("## Adding `column_groups`"),
    md(
        """
That's already a lot more visually distinct. It would be nice if we could
color the names of the column groups as well. We can do that by adding a
`column_groups` `DataFrame`.

It must have the following columns:
* `Category` (or any other label column) — the display name of the column group
* `group` — links each row to a `group` value in `column_info`
* `palette` — the palette to use for the column group
"""
    ),
    code(
        """
column_groups = pd.DataFrame({
    'Category': ['Performance','Overall','Engine','Transmission'],
    'group':    ['Performance','Overall','Engine','Transmission'],
    'palette':  ['perf_palette','overall_palette','engine_palette','transmission_palette'],
})
funky_heatmap(data, column_info=cinfo, column_groups=column_groups, palettes=palettes)
"""
    ),
    md("## Specifying geoms"),
    md(
        """
It makes sense to present some information differently. The number of
cylinders and carburetors are discrete values, so let's display them as
rectangles with a text overlay.
"""
    ),
    code(
        """
cinfo['geom'] = ['text','bar','bar','bar','rect','rect','funkyrect','funkyrect',
                 'circle','funkyrect','rect','rect']
funky_heatmap(data, column_info=cinfo, column_groups=column_groups, palettes=palettes)
"""
    ),
    md("This looks nice, but we don't have the text overlay yet — we add overlay text rows for the discrete columns."),
    code(
        """
def insert_overlay_at(df, *, before_iloc1, new_id, group, palette='black'):
    \"\"\"Insert a text-overlay row referencing `new_id` at 1-indexed position
    `before_iloc1` (matches R's ``add_row(..., .before=N)``).\"\"\"
    pos = before_iloc1 - 1
    if pos >= len(df):
        pos = len(df)
    row = {
        'id': new_id, 'group': group, 'name': '', 'geom': 'text',
        'options': json.dumps({'overlay': True}), 'palette': palette,
    }
    return pd.concat(
        [df.iloc[:pos], pd.DataFrame([row]), df.iloc[pos:]],
        ignore_index=True,
    )

# R does these four .before= inserts in order. Each shifts subsequent
# positions down by one.
cinfo = insert_overlay_at(cinfo, before_iloc1=6,  new_id='cyl',  group='Engine')
cinfo = insert_overlay_at(cinfo, before_iloc1=8,  new_id='carb', group='Engine')
cinfo = insert_overlay_at(cinfo, before_iloc1=14, new_id='am',   group='Transmission')
cinfo = insert_overlay_at(cinfo, before_iloc1=17, new_id='gear', group='Transmission')

palettes['black'] = ['black', 'black']
cinfo
"""
    ),
    code(
        """
funky_heatmap(data, column_info=cinfo, column_groups=column_groups, palettes=palettes)
"""
    ),
    md("This is starting to look like a nice visualisation."),
    md("## Customising legends"),
    md(
        """
We can customise the legends for each palette. If we want multiple legends
for one palette, just include multiple `legends` entries pointing to it.
"""
    ),
    code(
        """
# verbatim RColorBrewer Greys, reversed and without the lightest stop
greys9_rev = list(reversed(['#FFFFFF','#F0F0F0','#D9D9D9','#BDBDBD','#969696',
                            '#737373','#525252','#252525','#000000']))[:-1]
palettes['funky_palette_grey'] = greys9_rev

legends = [
    dict(palette='perf_palette',    geom='bar', title='1/4 mile time',
         labels=[f"{data['qsec'].min()}s"] + [''] * 8 + [f"{data['qsec'].max()}s"]),
    dict(palette='overall_palette', geom='bar', title='Miles per gallon',
         labels=[f"{data['mpg'].min()}mpg"] + [''] * 8 + [f"{data['mpg'].max()}mpg"]),
    dict(palette='overall_palette', geom='bar', title='Weight',
         labels=[f"{data['wt'].min()}lbs"]  + [''] * 8 + [f"{data['wt'].max()}lbs"]),
    dict(palette='funky_palette_grey', geom='funkyrect', title='Overall', enabled=True,
         labels=['0','','0.2','','0.4','','0.6','','0.8','','1']),
]
funky_heatmap(data, column_info=cinfo, column_groups=column_groups,
              palettes=palettes, legends=legends)
"""
    ),
    md(
        """
We can disable the `engine_palette` and `transmission_palette` legends by
adding entries with `enabled=False` — they don't add extra information now
that the columns are already colour-coded.
"""
    ),
    code(
        """
disabled_legends = [
    dict(palette='engine_palette',       enabled=False),
    dict(palette='transmission_palette', enabled=False),
]
legends = legends + disabled_legends
funky_heatmap(data, column_info=cinfo, column_groups=column_groups,
              palettes=palettes, legends=legends)
"""
    ),
    md("## Adding images"),
    md(
        """
The `transmission` and `engine type` columns are still uninformative —
they just contain 0/1. Let's replace those values with images. First we
remap the data values to image names, then we set the image directory and
extension via `column_info`.
"""
    ),
    code(
        """
data = data.copy()
data['am'] = data['am'].map({0: 'automatic', 1: 'manual'}).astype(str)
data['vs'] = data['vs'].map({0: 'vengine',  1: 'straight'}).astype(str)

cinfo = cinfo.copy()
cinfo['directory'] = None
cinfo['extension'] = None

# R: `cinfo <- cinfo[-14, ]` — drop the 14th 1-indexed row (the `am` overlay
# inserted earlier). Iloc 13 in Python.
cinfo = cinfo.reset_index(drop=True)
cinfo = cinfo.drop(index=13).reset_index(drop=True)

mask = cinfo['id'].isin(['vs', 'am'])
cinfo.loc[mask, 'directory'] = 'images'
cinfo.loc[mask, 'extension'] = 'png'
# R: `cinfo[c(11,13),"geom"] <- "image"` — 1-indexed rows 11 (vs) and 13 (am).
cinfo.loc[[10, 12], 'geom'] = 'image'

funky_heatmap(data, column_info=cinfo, column_groups=column_groups,
              palettes=palettes, legends=legends)
"""
    ),
    md("## Row grouping"),
    md(
        """
We can group rows together too. Let's highlight the Mercedes cars. We
rearrange the data so the Mercedes rows are at the top and pass a
`row_info` / `row_groups` pair.
"""
    ),
    code(
        """
row_info = pd.DataFrame({
    'id':    data['id'].to_numpy(),
    'group': ['Mercedes' if 'Merc' in str(x) else 'Other' for x in data['id']],
})
order = row_info['group'].argsort(kind='mergesort')
data = data.iloc[order].reset_index(drop=True)
row_info = row_info.iloc[order].reset_index(drop=True)

row_groups = pd.DataFrame({
    'level1': ['Mercedes', 'Other cars'],
    'group':  ['Mercedes', 'Other'],
})

funky_heatmap(data, column_info=cinfo, column_groups=column_groups,
              palettes=palettes, legends=legends,
              row_info=row_info, row_groups=row_groups)
"""
    ),
    md(
        """
Some final spacing tweaks: e.g. the `Transmission` column group needs a
little more room. We can do this by setting `width` in the `options` of
the relevant rows in `column_info`.

If you still want to fine-tune things, save the figure as `.svg` and edit
in a vector graphics editor.
"""
    ),
    code(
        """
def set_option(df, iloc, **opts):
    o = json.loads(df.iloc[iloc]['options']) if df.iloc[iloc]['options'] else {}
    o.update(opts)
    df.at[iloc, 'options'] = json.dumps(o)
    return df

cinfo = cinfo.copy()
for i, w in [(0, 6), (1, 6), (2, 3), (3, 3), (11, 1.85), (12, 1.85)]:
    cinfo = set_option(cinfo, i, width=w)

fh = funky_heatmap(data, column_info=cinfo, column_groups=column_groups,
                   palettes=palettes, legends=legends,
                   row_info=row_info, row_groups=row_groups)
fh.save('../data/vignettes/getting_started_py.png', dpi=140, facecolor='white')
fh
"""
    ),
    md("## Side-by-side with the R reference"),
    code(
        """
import matplotlib.image as mpimg
fig, axes = plt.subplots(1, 2, figsize=(16, 10))
axes[0].imshow(mpimg.imread('../data/vignettes/getting_started_R.png'));  axes[0].set_title('R reference (funkyheatmap)',  fontsize=12); axes[0].axis('off')
axes[1].imshow(mpimg.imread('../data/vignettes/getting_started_py.png')); axes[1].set_title('Python port (pyfunkyheatmap)', fontsize=12); axes[1].axis('off')
plt.tight_layout()
fig
"""
    ),
    md(
        """
This is the same layout as the R vignette, built up one step at a time
from a bare `funky_heatmap(data)` call to the fully styled figure.
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
    path = HERE / "getting_started.ipynb"
    nbf.write(nb, path)
    print(f"wrote {path}")
    client = NotebookClient(nb, timeout=300, kernel_name="python3",
                            resources={"metadata": {"path": str(HERE)}})
    client.execute()
    nbf.write(nb, path)
    print(f"executed {path}")


if __name__ == "__main__":
    build()
