"""Legend-panel renderers — 1:1 visual port of ``create_legends.R``.

Strategy
--------
Every panel is drawn in axes-fraction coords ``[0, 1] × [0, 1]`` (no
``aspect='equal'``), with glyph dimensions computed from the panel's
*physical* size (inches) so square cells render as physical squares.

* Each legend has an intrinsic R-coord size ``(w, h)``. :func:`compose_legend_strip`
  allocates each panel a physical width = ``strip_h_in * (w / h)`` so each
  panel's physical aspect equals its R aspect.
* Inside the panel we draw with the panel's actual physical aspect:
    - title: axes-fraction (0, 0.95), top-left.
    - glyphs: width/height computed in inches, then converted to
      axes-fraction via the panel's physical width/height.
    - labels: axes-fraction y ≈ 0.10, centred under each glyph.
"""

from __future__ import annotations

from typing import Any, Mapping

import matplotlib.patches as mpatches
import matplotlib.path as mpath
import numpy as np
from matplotlib.axes import Axes
from matplotlib.colors import LinearSegmentedColormap

from .palettes import DEFAULT_PALETTES
from .verify import _is_na


_TITLE_SIZE = 8
_LABEL_SIZE = 7

_LEGEND_SPACE = 0.2  # R: gap between sized-stop cells, in data units


# ---------------------------------------------------------------------------
# palette helpers
# ---------------------------------------------------------------------------

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
    if n <= 0 or not pal:
        return []
    if n == 1:
        return [pal[len(pal) // 2]]
    idxs = np.round(np.linspace(0, len(pal) - 1, n)).astype(int)
    return [pal[i] for i in idxs]


# ---------------------------------------------------------------------------
# rounded rect path (mirror score_to_funky_rectangle)
# ---------------------------------------------------------------------------

def _rounded_rect_patch(xmin, xmax, ymin, ymax, radius, **kwargs):
    w = xmax - xmin
    h = ymax - ymin
    r = max(0.0, min(radius, w / 2, h / 2))
    if r == 0:
        verts = [(xmin, ymin), (xmax, ymin), (xmax, ymax),
                 (xmin, ymax), (xmin, ymin)]
        codes = [mpath.Path.MOVETO] + [mpath.Path.LINETO] * 4
        return mpatches.PathPatch(mpath.Path(verts, codes), **kwargs)
    k = r * (1 - 0.5522847498)
    verts = [
        (xmin + r, ymin),
        (xmax - r, ymin), (xmax - k, ymin), (xmax, ymin + k), (xmax, ymin + r),
        (xmax, ymax - r), (xmax, ymax - k), (xmax - k, ymax), (xmax - r, ymax),
        (xmin + r, ymax), (xmin + k, ymax), (xmin, ymax - k), (xmin, ymax - r),
        (xmin, ymin + r), (xmin, ymin + k), (xmin + k, ymin), (xmin + r, ymin),
    ]
    codes = (
        [mpath.Path.MOVETO]
        + [mpath.Path.LINETO, mpath.Path.CURVE4, mpath.Path.CURVE4, mpath.Path.CURVE4] * 4
    )
    return mpatches.PathPatch(mpath.Path(verts, codes), **kwargs)


def _ax_inches(ax: Axes) -> tuple[float, float]:
    fig = ax.figure
    bbox = ax.get_position()
    return bbox.width * fig.get_figwidth(), bbox.height * fig.get_figheight()


# ---------------------------------------------------------------------------
# intrinsic R-coord (w, h) — for proportional strip layout
# ---------------------------------------------------------------------------

def _legend_intrinsic_dims(legend: dict) -> tuple[float, float]:
    geom = legend.get("geom", "rect")
    # Use the R legend coord system: bar legend is 5 wide × 1 tall (+ title
    # + label rows). Sized-stops legend width = sum(sizes) + (n-1)*gap.
    # In all cases we count the cell-row height as 1.0 and add 2.0 for the
    # title + label rows.
    title_label_h = 2.0
    cell_h = 1.0
    h = title_label_h + cell_h
    if geom == "bar":
        return 5.0, h
    if geom in ("rect", "funkyrect", "circle"):
        sizes = legend.get("size")
        labels = legend.get("labels") or []
        if not sizes:
            n = max(len(labels), 1)
            sizes = list(np.linspace(0, 1, n))
        widths = [float(s) for s in sizes]
        total_w = sum(widths) + _LEGEND_SPACE * max(len(widths) - 1, 0)
        return max(total_w, 1.0), h
    if geom == "text":
        labels = legend.get("labels") or []
        values = legend.get("values") or []
        label_width = float(legend.get("label_width", 1.0) or 1.0)
        value_width = float(legend.get("value_width", 2.0) or 2.0)
        return 0.5 + label_width + 0.5 + value_width + 0.5, max(len(labels), 1) + 1.5
    if geom == "pie":
        return 3.0, h
    return 2.0, h


def _legend_intrinsic_width(legend: dict) -> float:
    return _legend_intrinsic_dims(legend)[0]


# ---------------------------------------------------------------------------
# vertical layout constants (axes-fraction)
# ---------------------------------------------------------------------------

_TITLE_AX_Y = 0.92
_CELL_AX_Y_CENTRE = 0.50
_LABEL_AX_Y = 0.10


# ---------------------------------------------------------------------------
# Text legend
# ---------------------------------------------------------------------------

def _draw_text_legend(ax: Axes, legend: dict, palettes) -> None:
    title = legend.get("title", "")
    values = legend.get("values") or []
    labels = legend.get("labels") or []
    n = min(len(values), len(labels))

    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    ax.text(0.05, _TITLE_AX_Y, title, ha="left", va="top",
            fontsize=_TITLE_SIZE, fontweight="bold")
    if n == 0:
        return
    row_h = min(0.4, 0.6 / n)
    for i in range(n):
        y = 0.7 - i * row_h
        ax.text(0.10, y, str(labels[i]), ha="left", va="center",
                fontsize=_LABEL_SIZE, fontweight="bold")
        ax.text(0.45, y, str(values[i]), ha="left", va="center",
                fontsize=_LABEL_SIZE)


# ---------------------------------------------------------------------------
# Continuous bar legend
# ---------------------------------------------------------------------------

def _draw_bar_legend(ax: Axes, legend: dict, palettes) -> None:
    title = legend.get("title", legend.get("palette", ""))
    pal = _resolve_palette(legend.get("palette"), palettes)
    labels = legend.get("labels") or []

    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")

    pad = 0.02
    inner = 1.0 - 2 * pad
    bar_y0, bar_y1 = 0.42, 0.65

    ax.text(pad, _TITLE_AX_Y, title, ha="left", va="top",
            fontsize=_TITLE_SIZE, fontweight="bold", clip_on=True)

    cmap = LinearSegmentedColormap.from_list("_leg", pal, N=256)
    grad = np.linspace(0, 1, 256).reshape(1, -1)
    ax.imshow(grad, aspect="auto", cmap=cmap,
              extent=(pad, pad + inner, bar_y0, bar_y1), zorder=1)
    ax.add_patch(mpatches.Rectangle(
        (pad, bar_y0), inner, bar_y1 - bar_y0,
        fill=False, edgecolor="black", linewidth=0.4))

    if labels:
        n = len(labels)
        for i, lab in enumerate(labels):
            if lab in ("", " ", None):
                continue
            # nudge the leftmost / rightmost labels inward so they don't
            # overflow into the adjacent panel
            x = pad + inner * i / max(n - 1, 1)
            if i == 0:
                ha = "left"
            elif i == n - 1:
                ha = "right"
            else:
                ha = "center"
            ax.text(x, _LABEL_AX_Y + 0.10, str(lab),
                    ha=ha, va="top", fontsize=_LABEL_SIZE,
                    clip_on=True)


# ---------------------------------------------------------------------------
# Sized-stops legend (rect / funkyrect / circle)
# ---------------------------------------------------------------------------

def _draw_sized_stops_legend(ax: Axes, legend: dict, palettes,
                             geom: str) -> None:
    title = legend.get("title", legend.get("palette", ""))
    pal = _resolve_palette(legend.get("palette"), palettes)
    labels = legend.get("labels") or []
    sizes = legend.get("size")
    if not labels:
        labels = [""] * (len(sizes) if sizes else 11)
    n = len(labels)
    if not sizes:
        sizes = list(np.linspace(0, 1, n))
    sizes = [float(s) for s in sizes]
    stops = _sample_palette(pal, n) or ["#CCCCCC"] * n

    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")

    # ---- physical dims ----
    ax_w_in, ax_h_in = _ax_inches(ax)
    # cell row occupies axes-y in [0.20, 0.78] — height fraction 0.58.
    cell_row_h_in = ax_h_in * 0.58
    # max cell side is bounded by both vertical and horizontal budget.
    # horizontal budget: n cells with widths size_i + (n-1)*gap_size cells
    # of side ``gap_size = LEGEND_SPACE`` factored out. We treat the cell
    # SIDE as the physical "unit" -> with max(size)=1, max_cell = unit.
    # Total horizontal extent = unit * (sum(sizes) + (n-1)*LEGEND_SPACE).
    total_units = sum(sizes) + _LEGEND_SPACE * max(n - 1, 0)
    unit_h_in = cell_row_h_in
    unit_w_in = ax_w_in * 0.96 / total_units if total_units > 0 else cell_row_h_in
    unit_in = min(unit_h_in, unit_w_in)

    # convert unit_in to axes-fraction for x and y separately
    unit_x = unit_in / ax_w_in if ax_w_in > 0 else 0.05
    unit_y = unit_in / ax_h_in if ax_h_in > 0 else 0.05

    # horizontal position: cumulative
    widths_x = [s * unit_x for s in sizes]
    gap_x = _LEGEND_SPACE * unit_x
    total_x = sum(widths_x) + gap_x * max(n - 1, 0)
    left = (1.0 - total_x) / 2

    centre_y = _CELL_AX_Y_CENTRE

    # title — left-aligned to the start of the stop row
    ax.text(left, _TITLE_AX_Y, title, ha="left", va="top",
            fontsize=_TITLE_SIZE, fontweight="bold")

    cx = left
    for i in range(n):
        sv = sizes[i]
        wx = widths_x[i]
        wy = sv * unit_y
        x0 = cx
        x1 = cx + wx
        y0 = centre_y - wy / 2
        y1 = centre_y + wy / 2
        col = stops[i] if i < len(stops) else stops[-1]
        if wx <= 0 or wy <= 0:
            cx = x1 + gap_x
            continue

        if geom == "circle":
            # circle inscribed in cell, drawn as Ellipse so it's circular
            # in physical units even though axes-x/y have different scales.
            ax.add_patch(mpatches.Ellipse(
                ((x0 + x1) / 2, centre_y), wx, wy,
                facecolor=col, edgecolor="black", linewidth=0.4))
        elif geom == "funkyrect":
            # R's score_to_funky_rectangle: for sv >= 0.8 full cell with
            # small corner; for sv < 0.8 shrunken cell with corner 0.5*side.
            midpoint = 0.8
            if sv >= midpoint:
                trans = (sv - midpoint) / (1 - midpoint) / 2 + 0.5
                cwx, cwy = wx, wy
                cx0, cx1, cy0, cy1 = x0, x1, y0, y1
                corner_data = (0.9 - 0.8 * trans) * min(cwx, cwy)
            else:
                # shrink to (trans*0.9 + 0.1) of full
                if sv > 0:
                    trans = sv / midpoint
                    scale = trans * 0.9 + 0.1
                else:
                    scale = 0.1
                cwx = wx * scale
                cwy = wy * scale
                mx = (x0 + x1) / 2
                my = centre_y
                cx0 = mx - cwx / 2
                cx1 = mx + cwx / 2
                cy0 = my - cwy / 2
                cy1 = my + cwy / 2
                corner_data = 0.5 * min(cwx, cwy)
            ax.add_patch(_rounded_rect_patch(
                cx0, cx1, cy0, cy1, corner_data,
                facecolor=col, edgecolor="black", linewidth=0.4))
        else:  # rect
            ax.add_patch(mpatches.Rectangle(
                (x0, y0), wx, wy,
                facecolor=col, edgecolor="black", linewidth=0.4))

        if labels[i] not in ("", " ", None):
            ax.text((x0 + x1) / 2, _LABEL_AX_Y + 0.10, str(labels[i]),
                    ha="center", va="top", fontsize=_LABEL_SIZE)
        cx = x1 + gap_x


# ---------------------------------------------------------------------------
# Pie legend
# ---------------------------------------------------------------------------

def _draw_pie_legend(ax: Axes, legend: dict, palettes) -> None:
    title = legend.get("title", "")
    labels = legend.get("labels") or []
    pal = _resolve_palette(legend.get("palette"), palettes)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    ax.text(0.0, _TITLE_AX_Y, title, ha="left", va="top",
            fontsize=_TITLE_SIZE, fontweight="bold")
    n = max(len(labels), 1)
    for i, lab in enumerate(labels):
        wedge = 180.0 / n
        theta1 = i * wedge - 90.0
        theta2 = (i + 1) * wedge - 90.0
        ax.add_patch(mpatches.Wedge(
            (0.22, 0.45), 0.18, theta1, theta2,
            facecolor=pal[i % len(pal)], edgecolor="black", linewidth=0.4))
        ax.text(0.50, 0.75 - i * 0.16, str(lab),
                ha="left", va="center", fontsize=_LABEL_SIZE)


def _draw_image_legend(ax: Axes, legend: dict, palettes) -> None:
    title = legend.get("title", "")
    values = legend.get("values") or []
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    ax.text(0.0, _TITLE_AX_Y, title, ha="left", va="top",
            fontsize=_TITLE_SIZE, fontweight="bold")
    for i, v in enumerate(values):
        ax.text(0.05, 0.7 - i * 0.2, str(v), ha="left", va="center",
                fontsize=_LABEL_SIZE)


_LEGEND_HANDLERS = {
    "text":      _draw_text_legend,
    "bar":       _draw_bar_legend,
    "rect":      lambda ax, l, p: _draw_sized_stops_legend(ax, l, p, "rect"),
    "funkyrect": lambda ax, l, p: _draw_sized_stops_legend(ax, l, p, "funkyrect"),
    "circle":    lambda ax, l, p: _draw_sized_stops_legend(ax, l, p, "circle"),
    "pie":       _draw_pie_legend,
    "image":     _draw_image_legend,
}


# ---------------------------------------------------------------------------
# Strip layout — proportional widths matching R's patchwork wrap_plots
# ---------------------------------------------------------------------------

def compose_legend_strip(
    fig,
    legends: list[dict],
    palettes: Mapping[str, Any],
    *,
    top_anchor: float = 0.08,
) -> None:
    enabled = [l for l in legends
               if l.get("enabled", True) and l.get("geom") in _LEGEND_HANDLERS]
    if not enabled:
        return

    bottom = 0.012
    strip_h_frac = max(top_anchor - bottom - 0.005, 0.04)
    strip_h_in = strip_h_frac * fig.get_figheight()
    fig_w_in = fig.get_figwidth()

    # ideal physical width per panel = strip_h_in * (data_w / data_h)
    dims = [_legend_intrinsic_dims(l) for l in enabled]
    ideal_widths_in = [strip_h_in * (w / h) for (w, h) in dims]
    total_ideal_in = sum(ideal_widths_in)

    # inter-panel gap so long titles (e.g. "Miles per gallon") don't spill
    # into the next panel
    gap_in = 0.25
    total_gap_in = gap_in * max(len(enabled) - 1, 0)

    left_pad = 0.03
    right_pad = 0.02
    avail_frac = 1.0 - left_pad - right_pad
    avail_in = avail_frac * fig_w_in

    # don't stretch beyond ideal; shrink uniformly if too crowded
    needed_in = total_ideal_in + total_gap_in
    scale = min(1.0, avail_in / needed_in) if needed_in > 0 else 1.0
    panel_widths_in = [w * scale for w in ideal_widths_in]
    gap_in_scaled = gap_in * scale

    used_in = sum(panel_widths_in) + gap_in_scaled * max(len(enabled) - 1, 0)
    extra_in = max(avail_in - used_in, 0.0)
    cursor_in = left_pad * fig_w_in + extra_in / 2

    for i, (legend, panel_w_in) in enumerate(zip(enabled, panel_widths_in)):
        left_frac = cursor_in / fig_w_in
        width_frac = panel_w_in / fig_w_in
        ax = fig.add_axes((left_frac, bottom, width_frac, strip_h_frac))
        cursor_in += panel_w_in
        if i < len(enabled) - 1:
            cursor_in += gap_in_scaled
        handler = _LEGEND_HANDLERS[legend["geom"]]
        handler(ax, legend, palettes)
