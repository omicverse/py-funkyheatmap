"""Legend-panel renderers matching the R funkyheatmap layout 1:1.

R places each legend as a compact tile:
* a bold title above
* for rect/bar/funkyrect/circle: a row of N **discrete** colored stops, one
  per label, with the label beneath each stop
* for text: small colored swatches next to vertically-stacked value/label rows
* for pie: a half-pie with labels arrayed beside it

Each renderer draws into a unit-square axes (xlim/ylim = [0,1] with a small
margin) so :func:`compose_legend_strip` can pack them side-by-side without
worrying about absolute coordinates.
"""

from __future__ import annotations

from math import pi
from typing import Any, Mapping

import matplotlib.patches as mpatches
import numpy as np
from matplotlib.axes import Axes

from .palettes import DEFAULT_PALETTES
from .verify import _is_na


_TITLE_SIZE = 8
_LABEL_SIZE = 7


def _resolve_palette(name, palettes: Mapping[str, Any]) -> list[str]:
    if name is None:
        return ["#444444"]
    if isinstance(name, list):
        return list(name)
    if isinstance(name, dict):
        return list(name.values())
    if isinstance(name, str):
        if name in palettes:
            return _resolve_palette(palettes[name], palettes)
        if name in DEFAULT_PALETTES["numerical"]:
            return list(DEFAULT_PALETTES["numerical"][name])
        if name in DEFAULT_PALETTES["categorical"]:
            return list(DEFAULT_PALETTES["categorical"][name])
    return ["#444444"]


def _sample_palette(pal: list[str], n: int) -> list[str]:
    """Pick ``n`` equally-spaced colours from a palette (inclusive of ends)."""
    if n <= 0 or not pal:
        return []
    if n == 1:
        return [pal[len(pal) // 2]]
    idxs = np.linspace(0, len(pal) - 1, n).astype(int)
    return [pal[i] for i in idxs]


def _draw_text_legend(ax: Axes, legend: dict, palettes) -> None:
    """Replicate R ``create_text_legend``: title + value/label rows w/ swatches.

    R puts ``value`` (e.g. "Scaled") in the left column and ``label`` (e.g.
    "+") in the right column. We add a small colored chip next to each value
    so the legend visually carries the colour mapping.
    """
    title = legend.get("title", "")
    values = legend.get("values") or []
    labels = legend.get("labels") or []
    n = min(len(values), len(labels))

    ax.text(0.0, 0.95, title, ha="left", va="top",
            fontsize=_TITLE_SIZE, fontweight="bold")

    if n == 0:
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off"); return

    # R lays out as label (`+` / `-`) on the LEFT, value (`Scaled` /
    # `Unscaled`) on the RIGHT — see ``create_text_legend`` in
    # ``funkyheatmap-ref/R/create_legends.R``:
    #   tibble(x = start_x + .5, label_value = as.character(name))
    #   tibble(x = start_x + 2*.5 + label_width, label_value = value)
    # where ``name = labels`` and ``value = values``.
    row_h = min(0.45, 0.55 / n)
    for i in range(n):
        y = 0.55 - i * row_h
        # label (e.g. "+" / "-")
        ax.text(0.05, y, str(labels[i]), ha="left", va="center",
                fontsize=_LABEL_SIZE, fontweight="bold")
        # value (e.g. "Scaled" / "Unscaled")
        ax.text(0.30, y, str(values[i]), ha="left", va="center", fontsize=_LABEL_SIZE)

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")


def _draw_discrete_stops_legend(ax: Axes, legend: dict, palettes) -> None:
    """Render a sequential-palette legend.

    Layout (matches R ``create_rect_legend`` for the discrete case and
    ggplot's ``guide_colourbar`` for the continuous case):

    * Bold title at top.
    * Below: either N square colour stops (discrete) OR a continuous gradient
      bar (when ``legend["continuous"]`` is True, OR when the label set is
      the auto-generated 11-stop ramp ``["0","","0.2",...,"1"]`` — that's
      what R's vignette default uses for `funky_heatmap` outputs without
      explicit legend labels, and R draws it as a continuous bar).
    * Label centred under each tick.
    """
    title = legend.get("title", legend.get("palette", ""))
    pal = _resolve_palette(legend.get("palette"), palettes)
    labels = legend.get("labels")
    if labels is None or len(labels) == 0:
        labels = [""] * 5
    n = len(labels)

    pad = 0.03
    inner = 1.0 - 2 * pad

    is_auto_ramp = (
        n >= 7
        and sum(1 for v in labels if v in ("", " ", None)) >= n // 2
    )
    is_continuous = bool(legend.get("continuous", is_auto_ramp))

    if is_continuous:
        # title for continuous bar
        ax.text(0.0, 0.95, title, ha="left", va="top",
                fontsize=_TITLE_SIZE, fontweight="bold")
        from matplotlib.colors import LinearSegmentedColormap
        cmap = LinearSegmentedColormap.from_list("_leg", pal, N=256)
        gradient = np.linspace(0, 1, 256).reshape(1, -1)
        bar_y0, bar_y1 = 0.55, 0.80
        ax.imshow(
            gradient,
            aspect="auto",
            cmap=cmap,
            extent=(pad, pad + inner, bar_y0, bar_y1),
            zorder=1,
        )
        ax.add_patch(
            mpatches.Rectangle(
                (pad, bar_y0), inner, bar_y1 - bar_y0,
                fill=False, edgecolor="black", linewidth=0.4
            )
        )
        for i, lab in enumerate(labels):
            if lab in ("", " ", None):
                continue
            x = pad + inner * i / max(n - 1, 1)
            ax.text(x, 0.42, str(lab),
                    ha="center", va="top", fontsize=_LABEL_SIZE)
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    else:
        # discrete SQUARE stops. We stay in axes coords [0, 1] × [0, 1] and
        # ask matplotlib for the axes physical aspect (inches wide / tall) at
        # draw time, then pick a stop side that is square in PHYSICAL units.
        stops = _sample_palette(pal, n)

        fig = ax.figure
        bbox = ax.get_position()
        ax_w_in = bbox.width  * fig.get_figwidth()
        ax_h_in = bbox.height * fig.get_figheight()
        # axes physical aspect = h / w
        if ax_w_in <= 0 or ax_h_in <= 0:
            aspect = 1.0
        else:
            aspect = ax_h_in / ax_w_in

        # stop height (axes-y fraction) we want
        target_stop_h = 0.45  # use ~45% of axes height for the stop row
        # the equivalent axes-x fraction that gives a physical square is
        # target_stop_h * aspect (since 1 axes-y unit = ax_h_in inches and
        # 1 axes-x unit = ax_w_in inches; square <=> dy * ax_h_in = dx * ax_w_in
        # <=> dx = dy * (ax_h_in / ax_w_in) = dy * aspect)
        stop_w_ax = target_stop_h * aspect

        # total horizontal span used by n stops; centre it
        total_w = stop_w_ax * n
        if total_w > 0.96:
            # not enough room → shrink stops to fit
            stop_w_ax = 0.96 / n
            target_stop_h = stop_w_ax / max(aspect, 1e-6)
            total_w = stop_w_ax * n
        left = (1.0 - total_w) / 2

        # vertical layout: label row at bottom (~0.05 - 0.18), stop row centred,
        # title row at top (~0.85)
        stop_bottom = 0.30
        stop_top = stop_bottom + target_stop_h

        ax.text(left, 0.92, title, ha="left", va="top",
                fontsize=_TITLE_SIZE, fontweight="bold")
        for i in range(n):
            col = stops[i] if i < len(stops) else stops[-1]
            ax.add_patch(
                mpatches.Rectangle(
                    (left + i * stop_w_ax, stop_bottom),
                    stop_w_ax, target_stop_h,
                    facecolor=col, edgecolor="black", linewidth=0.4,
                )
            )
            ax.text(left + (i + 0.5) * stop_w_ax, stop_bottom - 0.05,
                    str(labels[i]),
                    ha="center", va="top", fontsize=_LABEL_SIZE)
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
        return

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")


def _draw_circle_stops_legend(ax: Axes, legend: dict, palettes) -> None:
    """Like :func:`_draw_discrete_stops_legend` but stops are circles."""
    title = legend.get("title", legend.get("palette", ""))
    pal = _resolve_palette(legend.get("palette"), palettes)
    labels = legend.get("labels")
    if labels is None or len(labels) == 0:
        labels = [""] * 5
    n = len(labels)
    stops = _sample_palette(pal, n)
    sizes = legend.get("size") or [1.0] * n

    title_y = 0.95
    label_y = 0.20

    ax.text(0.0, title_y, title, ha="left", va="top",
            fontsize=_TITLE_SIZE, fontweight="bold")

    pad = 0.03
    inner = 1.0 - 2 * pad
    stop_w = inner / n
    max_r = min(stop_w * 0.45, 0.18)
    for i in range(n):
        cx = pad + (i + 0.5) * stop_w
        col = stops[i] if i < len(stops) else stops[-1]
        r = max_r * (float(sizes[i]) if i < len(sizes) else 1.0)
        ax.add_patch(
            mpatches.Circle((cx, 0.48), r,
                            facecolor=col, edgecolor="black", linewidth=0.4)
        )
        ax.text(cx, label_y, str(labels[i]),
                ha="center", va="top", fontsize=_LABEL_SIZE)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")


def _draw_pie_legend(ax: Axes, legend: dict, palettes) -> None:
    title = legend.get("title", "")
    labels = legend.get("labels") or []
    pal = _resolve_palette(legend.get("palette"), palettes)
    n = max(len(labels), 1)
    ax.text(0.0, 0.95, title, ha="left", va="top",
            fontsize=_TITLE_SIZE, fontweight="bold")
    for i, lab in enumerate(labels):
        wedge = 180.0 / n
        theta1 = i * wedge - 90.0
        theta2 = (i + 1) * wedge - 90.0
        ax.add_patch(
            mpatches.Wedge((0.22, 0.45), 0.18, theta1, theta2,
                           facecolor=pal[i % len(pal)],
                           edgecolor="black", linewidth=0.4)
        )
        ax.text(0.50, 0.75 - i * 0.16, str(lab),
                ha="left", va="center", fontsize=_LABEL_SIZE)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")


def _draw_image_legend(ax: Axes, legend: dict, palettes) -> None:
    title = legend.get("title", "")
    values = legend.get("values") or []
    ax.text(0.0, 0.95, title, ha="left", va="top",
            fontsize=_TITLE_SIZE, fontweight="bold")
    for i, v in enumerate(values):
        ax.text(0.05, 0.7 - i * 0.2, str(v), ha="left", va="center",
                fontsize=_LABEL_SIZE)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")


_LEGEND_HANDLERS = {
    "text":      _draw_text_legend,
    "rect":      _draw_discrete_stops_legend,
    "bar":       _draw_discrete_stops_legend,
    "funkyrect": _draw_discrete_stops_legend,
    "circle":    _draw_circle_stops_legend,
    "pie":       _draw_pie_legend,
    "image":     _draw_image_legend,
}


def compose_legend_strip(
    fig,
    legends: list[dict],
    palettes: Mapping[str, Any],
    *,
    top_anchor: float = 0.08,
) -> None:
    """Stack legend panels side-by-side across the bottom of ``fig``.

    Each panel is a 1×1 axes in its own slot. We give equal horizontal slots
    to every enabled legend; that's a heuristic but matches R's
    ``patchwork::wrap_plots(..., widths = legend_widths)`` reasonably well.
    """
    enabled = [l for l in legends
               if l.get("enabled", True) and l.get("geom") in _LEGEND_HANDLERS]
    if not enabled:
        return
    n = len(enabled)
    bottom = 0.012
    strip_height = max(top_anchor - bottom - 0.005, 0.04)

    # Reserve a touch of figure-side padding so the leftmost / rightmost
    # legend's labels don't get clipped.
    left_pad = 0.04
    right_pad = 0.02
    avail = 1.0 - left_pad - right_pad
    width_each = avail / n

    for i, legend in enumerate(enabled):
        ax = fig.add_axes(
            (left_pad + i * width_each, bottom, width_each * 0.96, strip_height)
        )
        handler = _LEGEND_HANDLERS[legend["geom"]]
        handler(ax, legend, palettes)
