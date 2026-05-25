"""matplotlib-based rendering for funky heatmaps.

The :class:`FunkyHeatmap` wraps both the geometry tables and the resulting
:class:`matplotlib.figure.Figure` so that callers can inspect the data behind
each glyph (``fh.geom_positions["rect_data"]``) without re-running the
pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from typing import Any

import numpy as np
import pandas as pd

import matplotlib.image as mpimg
import matplotlib.patches as mpatches
import matplotlib.path as mpath
from matplotlib.figure import Figure

from .position import PositionArguments
from .verify import _is_na


# horizontal/vertical alignment mapping
_HJUST = {0.0: "left", 0.5: "center", 1.0: "right"}
_VJUST = {0.0: "bottom", 0.5: "center", 1.0: "top"}


def _hjust_to_ha(h: float) -> str:
    if h <= 0.25:
        return "left"
    if h >= 0.75:
        return "right"
    return "center"


def _vjust_to_va(v: float) -> str:
    if v <= 0.25:
        return "bottom"
    if v >= 0.75:
        return "top"
    return "center"


def _safe_color(value, default="#444444"):
    if _is_na(value):
        return default
    if isinstance(value, str) and not value.strip():
        return default
    return value


def _rounded_rect_path(
    xmin: float, xmax: float, ymin: float, ymax: float, radius: float
) -> mpath.Path:
    """Construct a closed rounded-rectangle path via cubic Bézier corners.

    Cap the radius at half the shortest side so corners can never invert.
    """
    w = xmax - xmin
    h = ymax - ymin
    r = max(0.0, min(radius, w / 2, h / 2))
    if r == 0:
        verts = [
            (xmin, ymin),
            (xmax, ymin),
            (xmax, ymax),
            (xmin, ymax),
            (xmin, ymin),
        ]
        codes = [mpath.Path.MOVETO] + [mpath.Path.LINETO] * 4
        return mpath.Path(verts, codes)
    # cubic Bezier offset for a quarter-circle approximation
    k = r * (1 - 0.5522847498)
    verts = [
        (xmin + r, ymin),                                   # MOVETO bottom-left start
        (xmax - r, ymin), (xmax - k, ymin), (xmax, ymin + k), (xmax, ymin + r),  # bottom + bottom-right corner
        (xmax, ymax - r), (xmax, ymax - k), (xmax - k, ymax), (xmax - r, ymax),  # right + top-right corner
        (xmin + r, ymax), (xmin + k, ymax), (xmin, ymax - k), (xmin, ymax - r),  # top + top-left corner
        (xmin, ymin + r), (xmin, ymin + k), (xmin + k, ymin), (xmin + r, ymin),  # left + bottom-left corner
    ]
    codes = (
        [mpath.Path.MOVETO]
        + [mpath.Path.LINETO, mpath.Path.CURVE4, mpath.Path.CURVE4, mpath.Path.CURVE4] * 4
    )
    return mpath.Path(verts, codes)


@dataclass
class FunkyHeatmap:
    """Bundle of geometry tables + the matplotlib figure that renders them."""

    geom_positions: dict[str, Any]
    position_args: PositionArguments
    figure: Figure
    bounds: dict[str, float] = field(default_factory=dict)
    width: float = 0.0
    height: float = 0.0

    def save(self, path, **savefig_kwargs):
        """Persist the figure to disk. Keyword args are forwarded to
        ``matplotlib.figure.Figure.savefig``.
        """
        self.figure.savefig(path, **savefig_kwargs)

    def _ipython_display_(self):  # pragma: no cover - notebook integration
        from IPython.display import display
        display(self.figure)


def _compute_bounds(geom: dict[str, Any]) -> dict[str, float]:
    xs_min: list[float] = []
    xs_max: list[float] = []
    ys_min: list[float] = []
    ys_max: list[float] = []

    column_pos = geom["column_pos"]
    if column_pos is not None and not column_pos.empty:
        xs_min += column_pos["xmin"].tolist()
        xs_max += column_pos["xmax"].tolist()

    row_pos = geom["row_pos"]
    if row_pos is not None and not row_pos.empty:
        ys_min += row_pos["ymin"].tolist()
        ys_max += row_pos["ymax"].tolist()

    seg = geom["segment_data"]
    if isinstance(seg, pd.DataFrame) and not seg.empty:
        xs_min += seg["x"].tolist() + seg["xend"].tolist()
        xs_max += seg["x"].tolist() + seg["xend"].tolist()
        ys_min += seg["y"].tolist() + seg["yend"].tolist()
        ys_max += seg["y"].tolist() + seg["yend"].tolist()

    for key in ("rect_data", "funkyrect_data", "pie_data", "text_data"):
        df = geom[key]
        if isinstance(df, pd.DataFrame) and not df.empty:
            if "xmin" in df.columns:
                xs_min += df["xmin"].dropna().tolist()
                xs_max += df["xmax"].dropna().tolist()
            if "ymin" in df.columns:
                ys_min += df["ymin"].dropna().tolist()
                ys_max += df["ymax"].dropna().tolist()

    cd = geom["circle_data"]
    if isinstance(cd, pd.DataFrame) and not cd.empty:
        xs_min += (cd["x0"] - cd["r"]).tolist()
        xs_max += (cd["x0"] + cd["r"]).tolist()
        ys_min += (cd["y0"] - cd["r"]).tolist()
        ys_max += (cd["y0"] + cd["r"]).tolist()

    def _safe_min(xs):
        xs = [x for x in xs if isinstance(x, (int, float, np.floating, np.integer)) and isfinite(float(x))]
        return float(min(xs)) if xs else 0.0

    def _safe_max(xs):
        xs = [x for x in xs if isinstance(x, (int, float, np.floating, np.integer)) and isfinite(float(x))]
        return float(max(xs)) if xs else 1.0

    return {
        "minimum_x": _safe_min(xs_min),
        "maximum_x": _safe_max(xs_max),
        "minimum_y": _safe_min(ys_min),
        "maximum_y": _safe_max(ys_max),
    }


def compose_figure(
    geom_positions: dict[str, Any],
    position_args: PositionArguments,
    *,
    fig: Figure | None = None,
    ax=None,
    fig_scale: float = 0.25,
    dpi: int = 100,
    legends: list[dict[str, Any]] | None = None,
    palettes: dict[str, Any] | None = None,
) -> FunkyHeatmap:
    """Render ``geom_positions`` to a matplotlib figure.

    ``fig_scale`` mirrors the R package's heuristic ``width = (max_x - min_x) / 4``
    — one user-coordinate unit becomes roughly ``fig_scale`` inches.
    """
    bounds = _compute_bounds(geom_positions)
    xmin = bounds["minimum_x"] - position_args.get("expand_xmin", 0.0)
    xmax = bounds["maximum_x"] + position_args.get("expand_xmax", 0.0)
    ymin = bounds["minimum_y"] - position_args.get("expand_ymin", 0.0)
    ymax = bounds["maximum_y"] + position_args.get("expand_ymax", 0.0)

    width = (xmax - xmin) * fig_scale
    height = (ymax - ymin) * fig_scale

    # reserve a compact strip for the legend bar. We add slack so the
    # strip + gap is visibly separated from the main heatmap.
    legend_h = 0
    if legends:
        enabled = [l for l in legends if l.get("enabled", True)]
        if enabled:
            legend_h = 0.7  # inches: strip itself ~0.6 + ~0.1 gap

    if fig is None:
        fig = Figure(
            figsize=(max(width, 2.0), max(height, 2.0) + legend_h),
            dpi=dpi,
        )
    # main axes occupy the top portion of the figure; the bottom portion is
    # left for the legend strip (which `compose_legend_strip` will populate).
    if ax is None:
        if legend_h > 0:
            # split: bottom ``legend_h`` inches → legend, rest → main, with
            # a generous gap so labels in the legend can't crowd the main
            # data even after tight-bbox cropping.
            total_h = max(height, 2.0) + legend_h
            legend_frac = legend_h / total_h
            gap_frac = 0.025
            ax = fig.add_axes((0.04, legend_frac + gap_frac, 0.92,
                               1 - legend_frac - gap_frac - 0.02))
        else:
            ax = fig.add_subplot(111)

    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    # `adjustable="datalim"` keeps the axes box at the position we asked for
    # (so the bottom of the heatmap never spills into the legend strip);
    # the data limits are nudged outward instead to preserve 1:1 aspect.
    ax.set_aspect("equal", adjustable="datalim")
    ax.axis("off")

    # ---- row backgrounds --------------------------------------------------
    rp = geom_positions["row_pos"]
    cp = geom_positions["column_pos"]
    if isinstance(rp, pd.DataFrame) and not rp.empty and "colour_background" in rp.columns:
        bg = rp[rp["colour_background"]]
        if not bg.empty and not cp.empty:
            row_space = geom_positions["viz_params"]["row_space"]
            bx0 = cp["xmin"].min() - 0.25
            bx1 = cp["xmax"].max() + 0.25
            for _, row in bg.iterrows():
                ax.add_patch(
                    mpatches.Rectangle(
                        (bx0, row["ymin"] - row_space / 2),
                        bx1 - bx0,
                        (row["ymax"] - row["ymin"]) + row_space,
                        facecolor="#DDDDDD",
                        edgecolor="none",
                        zorder=0,
                    )
                )

    # ---- segments ---------------------------------------------------------
    seg = geom_positions["segment_data"]
    if isinstance(seg, pd.DataFrame) and not seg.empty:
        for _, s in seg.iterrows():
            colour = _safe_color(s.get("colour", "black") if "colour" in s.index else "black", "black")
            lw_raw = s.get("size", 0.5) if "size" in s.index else 0.5
            lw = 0.5 if _is_na(lw_raw) else float(lw_raw)
            ls_raw = s.get("linetype", "solid") if "linetype" in s.index else "solid"
            if _is_na(ls_raw):
                ls_raw = "solid"
            ls = {"solid": "-", "dashed": "--", "dotted": ":"}.get(str(ls_raw), str(ls_raw))
            ax.plot(
                [s["x"], s["xend"]],
                [s["y"], s["yend"]],
                color=colour,
                linewidth=lw,
                linestyle=ls,
                zorder=1,
            )

    # ---- rectangles -------------------------------------------------------
    rd = geom_positions["rect_data"]
    if isinstance(rd, pd.DataFrame) and not rd.empty:
        for _, r in rd.iterrows():
            alpha = float(r["alpha"]) if "alpha" in r and not _is_na(r["alpha"]) else 1.0
            border = bool(r["border"]) if "border" in r and not _is_na(r["border"]) else True
            border_colour = r.get("border_colour", "black")
            if _is_na(border_colour) or not border:
                edge = "none"
            else:
                edge = _safe_color(border_colour, "black")
            face = _safe_color(r.get("colour", "#444444"))
            ax.add_patch(
                mpatches.Rectangle(
                    (r["xmin"], r["ymin"]),
                    r["xmax"] - r["xmin"],
                    r["ymax"] - r["ymin"],
                    facecolor=face,
                    edgecolor=edge,
                    linewidth=0.25,
                    alpha=alpha,
                    zorder=2,
                )
            )

    # ---- circles ----------------------------------------------------------
    cd = geom_positions["circle_data"]
    if isinstance(cd, pd.DataFrame) and not cd.empty:
        for _, c in cd.iterrows():
            face = _safe_color(c.get("colour", "#444444"))
            ax.add_patch(
                mpatches.Circle(
                    (c["x0"], c["y0"]),
                    radius=c["r"],
                    facecolor=face,
                    edgecolor="black",
                    linewidth=0.25,
                    zorder=3,
                )
            )

    # ---- funky rectangles -------------------------------------------------
    fr = geom_positions["funkyrect_data"]
    if isinstance(fr, pd.DataFrame) and not fr.empty:
        for _, r in fr.iterrows():
            face = _safe_color(r.get("colour", "#444444"))
            path = _rounded_rect_path(
                r["xmin"], r["xmax"], r["ymin"], r["ymax"], r["corner_size"]
            )
            ax.add_patch(
                mpatches.PathPatch(
                    path,
                    facecolor=face,
                    edgecolor="black",
                    linewidth=0.25,
                    zorder=3,
                )
            )

    # ---- pie --------------------------------------------------------------
    pd_ = geom_positions["pie_data"]
    if isinstance(pd_, pd.DataFrame) and not pd_.empty:
        for _, p in pd_.iterrows():
            face = _safe_color(p.get("colour", "#444444"))
            theta1 = float(np.degrees(p["rad_start"])) - 90.0
            theta2 = float(np.degrees(p["rad_end"])) - 90.0
            ax.add_patch(
                mpatches.Wedge(
                    (p["x0"], p["y0"]),
                    r=p["r"],
                    theta1=theta1,
                    theta2=theta2,
                    facecolor=face,
                    edgecolor="black",
                    linewidth=0.25,
                    zorder=3,
                )
            )

    # ---- images -----------------------------------------------------------
    # R uses ``cowplot::draw_image(x = xmin, y = ymin, width, height)`` so the
    # image fills the data cell exactly.
    img = geom_positions["img_data"]
    if isinstance(img, pd.DataFrame) and not img.empty:
        for _, row in img.iterrows():
            path = row.get("path")
            if _is_na(path):
                continue
            try:
                im = mpimg.imread(path)
            except (FileNotFoundError, OSError):
                continue
            x0 = row["xmin"]
            y0 = row["ymin"]
            width = row.get("width", row["xmax"] - row["xmin"])
            height = row.get("height", row["ymax"] - row["ymin"])
            ax.imshow(
                im,
                extent=(x0, x0 + width, y0, y0 + height),
                aspect="auto",
                zorder=4,
            )

    # ---- text -------------------------------------------------------------
    td = geom_positions["text_data"]
    if isinstance(td, pd.DataFrame) and not td.empty:
        for _, t in td.iterrows():
            label = t.get("label_value", "")
            if _is_na(label):
                continue
            label = str(label)
            if label == "" or label.lower() == "nan":
                continue
            hjust = float(t.get("hjust", 0.5)) if not _is_na(t.get("hjust", 0.5)) else 0.5
            vjust = float(t.get("vjust", 0.5)) if not _is_na(t.get("vjust", 0.5)) else 0.5
            angle = float(t.get("angle", 0.0)) if not _is_na(t.get("angle", 0.0)) else 0.0
            size = float(t.get("size", 4.0)) if not _is_na(t.get("size", 4.0)) else 4.0
            fontface = t.get("fontface", "plain")
            if _is_na(fontface):
                fontface = "plain"
            weight = "bold" if "bold" in str(fontface) else "normal"
            style = "italic" if "italic" in str(fontface) else "normal"
            colour = _safe_color(t.get("colour", "black"), "black")

            xmin = t["xmin"]
            xmax = t["xmax"]
            ymin = t["ymin"]
            ymax = t["ymax"]
            # alphax/alphay from compose_ggplot
            a = np.deg2rad(angle)
            cosa = round(np.cos(a), 2)
            sina = round(np.sin(a), 2)
            alphax = (
                (1 - hjust if cosa < 0 else hjust) * abs(cosa)
                + (1 - vjust if sina > 0 else vjust) * abs(sina)
            )
            alphay = (
                (1 - hjust if sina < 0 else hjust) * abs(sina)
                + (1 - vjust if cosa < 0 else vjust) * abs(cosa)
            )
            x = (1 - alphax) * xmin + alphax * xmax
            y = (1 - alphay) * ymin + alphay * ymax
            ax.text(
                x,
                y,
                str(label),
                ha=_hjust_to_ha(hjust),
                va=_vjust_to_va(vjust),
                rotation=angle,
                color=colour,
                fontsize=size * 2.4,  # ggplot size 4 ≈ matplotlib fontsize 10
                fontweight=weight,
                fontstyle=style,
                zorder=5,
            )

    if legends:
        from .legends import compose_legend_strip
        # legend strip lives entirely within the bottom ``legend_h`` inches.
        # Use the actual figure height (which may have been expanded by
        # subplots/aspect adjustments) so the strip fraction is consistent
        # with the main-axes fraction.
        actual_fig_h = fig.get_figheight()
        legend_frac = legend_h / actual_fig_h
        compose_legend_strip(fig, legends, palettes or {},
                             top_anchor=legend_frac * 0.85)

    return FunkyHeatmap(
        geom_positions=geom_positions,
        position_args=position_args,
        figure=fig,
        bounds=bounds,
        width=width,
        height=height + legend_h,
    )
