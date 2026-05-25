"""pyfunkyheatmap — funky heatmaps for pandas DataFrames.

Refactored Python port of the R package
[funkyheatmap](https://funkyheatmap.github.io/funkyheatmap/) following the
omicverse-rebuildr engineering protocol.

The public surface is intentionally compact:

* :func:`funky_heatmap` — main entry point, takes a :class:`pandas.DataFrame`
  and returns a :class:`FunkyHeatmap` object backed by a matplotlib figure.
* :func:`position_arguments` — build a layout configuration mapping.
* :func:`scale_minmax` — min-max scale a numeric vector to [0, 1].
* :func:`verify_*` — independently usable input validators.
"""

from .api import funky_heatmap
from .position import position_arguments
from .scale import scale_minmax
from .verify import (
    verify_column_groups,
    verify_column_info,
    verify_data,
    verify_legends,
    verify_palettes,
    verify_row_groups,
    verify_row_info,
)
from .figure import FunkyHeatmap

__all__ = [
    "FunkyHeatmap",
    "funky_heatmap",
    "position_arguments",
    "scale_minmax",
    "verify_column_groups",
    "verify_column_info",
    "verify_data",
    "verify_legends",
    "verify_palettes",
    "verify_row_groups",
    "verify_row_info",
]

__version__ = "0.1.7"
