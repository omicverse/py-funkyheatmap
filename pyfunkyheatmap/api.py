"""Top-level ``funky_heatmap`` entry point."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .figure import FunkyHeatmap, compose_figure
from .position import PositionArguments, coerce_position_args
from .positions import calculate_geom_positions
from .verify import (
    verify_column_groups,
    verify_column_info,
    verify_data,
    verify_legends,
    verify_palettes,
    verify_row_groups,
    verify_row_info,
)


def funky_heatmap(
    data,
    column_info: pd.DataFrame | None = None,
    row_info: pd.DataFrame | None = None,
    column_groups: pd.DataFrame | None = None,
    row_groups: pd.DataFrame | None = None,
    palettes: dict[str, Any] | None = None,
    legends: list[dict[str, Any]] | None = None,
    position_args: PositionArguments | None = None,
    scale_column: bool = True,
    add_abc: bool = True,
    *,
    fig=None,
    ax=None,
    fig_scale: float = 0.25,
    dpi: int = 100,
) -> FunkyHeatmap:
    """Render a funky heatmap from a pandas DataFrame.

    Parameters mirror the R ``funky_heatmap`` signature; see the package
    README for full semantics. Returns a :class:`FunkyHeatmap` bundling the
    matplotlib figure and the underlying geometry tables.
    """
    position_args = coerce_position_args(position_args)
    data = verify_data(data)
    column_info = verify_column_info(column_info, data)
    row_info = verify_row_info(row_info, data)
    column_groups = verify_column_groups(column_groups, column_info)
    row_groups = verify_row_groups(row_groups, row_info)
    palettes = verify_palettes(palettes, column_info, data)
    legends = verify_legends(legends, palettes, column_info, data)

    geom_positions = calculate_geom_positions(
        data=data,
        column_info=column_info,
        row_info=row_info,
        column_groups=column_groups,
        row_groups=row_groups,
        palettes=palettes,
        position_args=position_args,
        scale_column=scale_column,
        add_abc=add_abc,
    )

    fh = compose_figure(
        geom_positions,
        position_args,
        fig=fig,
        ax=ax,
        fig_scale=fig_scale,
        dpi=dpi,
        legends=legends,
        palettes=palettes,
    )
    return fh
