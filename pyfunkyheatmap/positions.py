"""Geometry layout — translate verified frames into per-geom DataFrames.

Each public ``calculate_*`` function takes verified inputs (the same the R
versions take) and returns the corresponding geometry table.

The output of :func:`calculate_geom_positions` is a dict with the same keys
as the R ``lst()`` return — ``row_pos``, ``column_pos``, ``rect_data``,
``circle_data``, ``funkyrect_data``, ``pie_data``, ``img_data``,
``text_data``, ``segment_data``, ``viz_params`` — so downstream rendering
code can be ported one geom at a time.
"""

from __future__ import annotations

from math import pi
from typing import Any, Callable

import numpy as np
import pandas as pd

from .position import PositionArguments
from .scale import scale_minmax
from .verify import _is_na


# ---------------------------------------------------------------------------
# row / column positions
# ---------------------------------------------------------------------------

def calculate_row_positions(
    row_info: pd.DataFrame, row_height: float, row_space: float, row_bigspace: float
) -> pd.DataFrame:
    rp = row_info.copy().reset_index(drop=True)
    groups = rp["group"].astype(object).where(rp["group"].notna(), "")
    rp["group"] = groups
    rp["group_i"] = rp.groupby("group").cumcount() + 1
    rp["row_i"] = np.arange(1, len(rp) + 1)
    rp["colour_background"] = rp["group_i"] % 2 == 1
    # do_spacing = c(FALSE, diff(as.integer(factor(group))) != 0)
    group_codes = pd.Categorical(rp["group"]).codes
    diff = np.diff(group_codes, prepend=group_codes[0])
    rp["do_spacing"] = diff != 0
    rp.loc[rp.index[0], "do_spacing"] = False
    rp["ysep"] = np.where(rp["do_spacing"], row_bigspace, row_space)
    rp["y"] = -(rp["row_i"] * row_height + np.cumsum(rp["ysep"]))
    rp["ymin"] = rp["y"] - row_height / 2
    rp["ymax"] = rp["y"] + row_height / 2
    return rp


def calculate_column_positions(
    column_info: pd.DataFrame, col_width: float, col_space: float, col_bigspace: float
) -> pd.DataFrame:
    cp = column_info.copy().reset_index(drop=True)
    cp["group"] = cp["group"].astype(object).where(cp["group"].notna(), "")
    group_codes = pd.Categorical(cp["group"]).codes
    diff = np.diff(group_codes, prepend=group_codes[0])
    cp["do_spacing"] = diff != 0
    cp.loc[cp.index[0], "do_spacing"] = False

    overlay = cp["overlay"].to_numpy(dtype=bool)
    width = cp["width"].to_numpy(dtype=float)
    xsep = np.empty(len(cp), dtype=float)
    for i in range(len(cp)):
        if overlay[i]:
            xsep[i] = 0.0 if i == 0 else -width[i - 1]
        elif cp.loc[i, "do_spacing"]:
            xsep[i] = col_bigspace
        else:
            xsep[i] = col_space
    cp["xsep"] = xsep

    xwidth = np.where(
        overlay & (width < 0),
        width - xsep,
        np.where(overlay, -xsep, width),
    )
    cp["xwidth"] = xwidth
    cp["xmax"] = np.cumsum(xwidth + xsep)
    cp["xmin"] = cp["xmax"] - cp["xwidth"]
    cp["x"] = cp["xmin"] + cp["xwidth"] / 2
    return cp


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _score_to_funky_rectangle(row: pd.Series) -> dict[str, Any] | None:
    midpoint = 0.8
    sv = row["size_value"]
    if _is_na(sv):
        return None
    xmin = row["xmin"]
    xmax = row["xmax"]
    ymin = row["ymin"]
    ymax = row["ymax"]
    if sv >= midpoint:
        trans = (sv - midpoint) / (1 - midpoint) / 2 + 0.5
        corner_size = (0.9 - 0.8 * trans) * min(xmax - xmin, ymax - ymin)
    else:
        x = (xmin + xmax) / 2
        y = (ymin + ymax) / 2
        corner_size = 0.5
        trans = sv / midpoint
        w = (trans * 0.9 + 0.1) * min(xmax - xmin, ymax - ymin)
        xmin = x - w / 2
        xmax = x + w / 2
        ymin = y - w / 2
        ymax = y + w / 2
    return {
        "xmin": xmin,
        "xmax": xmax,
        "ymin": ymin,
        "ymax": ymax,
        "corner_size": corner_size,
        "size_value": sv,
        "color_value": row.get("color_value", np.nan),
        "colour": row.get("colour", "#444444FF"),
    }


def _make_geom_data_processor(
    data: pd.DataFrame,
    column_pos: pd.DataFrame,
    row_pos: pd.DataFrame,
    scale_column: bool,
    palettes: dict[str, Any],
) -> Callable[[list[str] | str, Callable[[pd.DataFrame], pd.DataFrame] | None], pd.DataFrame]:
    """Return a per-geom processor that mirrors ``make_geom_data_processor`` in R."""
    column_pos = column_pos.copy()
    drop_cols = [c for c in ("group", "name", "do_spacing") if c in column_pos.columns]
    column_pos = column_pos.drop(columns=drop_cols)
    column_pos = column_pos.rename(
        columns={"id": "column_id", "id_color": "column_color", "id_size": "column_size"}
    )
    if "label" not in column_pos.columns:
        column_pos["label"] = np.nan
    if "scale" not in column_pos.columns:
        column_pos["scale"] = True

    def processor(geom_types, fun=None):
        if isinstance(geom_types, str):
            geom_types = [geom_types]
        sub = column_pos[column_pos["geom"].isin(geom_types)].copy().reset_index(drop=True)
        if sub.empty:
            return pd.DataFrame()
        out_rows: list[pd.DataFrame] = []
        for _, csel in sub.iterrows():
            cid = csel["column_id"]
            csel_label = csel["label"] if not _is_na(csel["label"]) else cid
            data_sel = pd.DataFrame(
                {
                    "row_id": data["id"].to_numpy(),
                    "value": data[cid].to_numpy(),
                }
            )
            data_sel["column_id"] = cid

            if not _is_na(csel["column_color"]):
                data_sel["color_value"] = data[csel["column_color"]].to_numpy()
            else:
                data_sel["color_value"] = np.nan
            if not _is_na(csel["column_size"]):
                data_sel["size_value"] = data[csel["column_size"]].to_numpy()
            else:
                data_sel["size_value"] = np.nan

            # label
            if not _is_na(csel_label) and csel_label in data.columns:
                col = data[csel_label]
                if isinstance(col, pd.DataFrame):
                    col = col.iloc[:, 0]
                data_sel["label_value"] = col.to_numpy()

            # merge with column_sel (broadcast scalars)
            for col in sub.columns:
                if col in ("column_id",):
                    continue
                data_sel[col] = csel[col]

            # merge row_pos (ysep / y / ymin / ymax)
            data_sel = data_sel.merge(
                row_pos[["id", "ysep", "y", "ymin", "ymax"]].rename(
                    columns={"id": "row_id"}
                ),
                on="row_id",
                how="left",
            )

            # scale, if requested
            if scale_column and bool(csel["scale"]):
                if pd.api.types.is_numeric_dtype(data_sel["value"]):
                    data_sel["value"] = scale_minmax(data_sel["value"].to_numpy())
                if pd.api.types.is_numeric_dtype(data_sel["color_value"]) and not data_sel["color_value"].isna().all():
                    data_sel["color_value"] = scale_minmax(data_sel["color_value"].to_numpy())
                if pd.api.types.is_numeric_dtype(data_sel["size_value"]) and not data_sel["size_value"].isna().all():
                    data_sel["size_value"] = scale_minmax(data_sel["size_value"].to_numpy())

            if fun is not None:
                data_sel = fun(data_sel)

            if data_sel is None or len(data_sel) == 0:
                continue
            if "value" in data_sel.columns:
                data_sel = data_sel.drop(columns=["value"])

            # determine colours from palette
            palette = csel["palette"]
            if not _is_na(palette) and palette in palettes:
                pal = palettes[palette]
                col_values: list = []
                for cv in data_sel["color_value"]:
                    if _is_na(cv):
                        col_values.append(None)
                    elif isinstance(cv, (int, np.integer, float, np.floating)) and isinstance(pal, list):
                        idx = int(round(float(cv) * (len(pal) - 1)))
                        idx = max(0, min(len(pal) - 1, idx))
                        col_values.append(pal[idx])
                    elif isinstance(pal, dict):
                        col_values.append(pal.get(cv))
                    elif isinstance(pal, list):
                        # categorical-as-list: index by category position
                        col_values.append(pal[hash(cv) % len(pal)])
                    else:
                        col_values.append(None)
                data_sel["colour"] = [
                    "#444444FF" if c is None else c for c in col_values
                ]

            out_rows.append(data_sel)

        if not out_rows:
            return pd.DataFrame()
        return pd.concat(out_rows, ignore_index=True)

    return processor


# ---------------------------------------------------------------------------
# main driver
# ---------------------------------------------------------------------------

def calculate_geom_positions(
    data: pd.DataFrame,
    column_info: pd.DataFrame,
    row_info: pd.DataFrame,
    column_groups,
    row_groups,
    palettes: dict[str, Any],
    position_args: PositionArguments,
    scale_column: bool,
    add_abc: bool,
) -> dict[str, Any]:
    row_height = position_args["row_height"]
    row_space = position_args["row_space"]
    row_bigspace = position_args["row_bigspace"]
    col_width = position_args["col_width"]
    col_space = position_args["col_space"]
    col_bigspace = position_args["col_bigspace"]
    col_annot_offset = position_args["col_annot_offset"]
    col_annot_angle = position_args["col_annot_angle"]

    # row annotation flag
    if "group" not in row_info.columns or row_info["group"].map(_is_na).all():
        row_info = row_info.copy()
        row_info["group"] = ""
        row_groups = pd.DataFrame({"group": [""]})
        plot_row_annotation = False
    else:
        plot_row_annotation = True

    row_pos = calculate_row_positions(row_info, row_height, row_space, row_bigspace)

    if "group" not in column_info.columns or column_info["group"].map(_is_na).all():
        column_info = column_info.copy()
        column_info["group"] = ""
        plot_column_annotation = False
    else:
        plot_column_annotation = True

    column_pos = calculate_column_positions(column_info, col_width, col_space, col_bigspace)

    processor = _make_geom_data_processor(
        data, column_pos, row_pos, scale_column, palettes
    )

    # --- circles -----------------------------------------------------------
    def _circle_fn(dat: pd.DataFrame) -> pd.DataFrame:
        out = dat.copy()
        out["x0"] = out["x"]
        out["y0"] = out["y"]
        out["r"] = row_height / 2 * out["size_value"].astype(float)
        return out

    circle_data = processor("circle", _circle_fn)

    # --- rectangles --------------------------------------------------------
    rect_data = processor("rect", lambda d: d)

    # --- funkyrect ---------------------------------------------------------
    fr_raw = processor("funkyrect", lambda d: d)
    if not fr_raw.empty:
        records = [
            _score_to_funky_rectangle(row) for _, row in fr_raw.iterrows()
        ]
        funkyrect_data = pd.DataFrame([r for r in records if r is not None])
    else:
        funkyrect_data = pd.DataFrame()

    # --- bar ---------------------------------------------------------------
    def _bar_fn(dat: pd.DataFrame) -> pd.DataFrame:
        out = dat.copy()
        if "hjust" not in out.columns:
            out["hjust"] = 0.0
        out["hjust"] = out["hjust"].fillna(0.0).astype(float)
        sv = out["size_value"].astype(float).fillna(0.0)
        out["xmin"] = out["xmin"] + (1 - sv) * out["xwidth"] * out["hjust"]
        out["xmax"] = out["xmax"] - (1 - sv) * out["xwidth"] * (1 - out["hjust"])
        return out

    bar_data = processor("bar", _bar_fn)

    # --- bar guides --------------------------------------------------------
    def _bar_guides_fn(dat: pd.DataFrame) -> pd.DataFrame:
        if "draw_outline" in dat.columns:
            dat = dat[dat["draw_outline"].fillna(True).astype(bool)]
        if dat.empty:
            return dat
        # per-column-id: take the first row, gather xmin/xmax
        firsts = dat.groupby("column_id").first().reset_index()[["column_id", "xmin", "xmax"]]
        sides = pd.concat(
            [
                firsts.rename(columns={"xmin": "x"})[["x"]].assign(xend=lambda d: d["x"]),
                firsts.rename(columns={"xmax": "x"})[["x"]].assign(xend=lambda d: d["x"]),
            ],
            ignore_index=True,
        )
        rp_seg = row_pos[["ymin", "ymax"]].rename(
            columns={"ymin": "y", "ymax": "yend"}
        )
        sides["_k"] = 1
        rp_seg = rp_seg.copy()
        rp_seg["_k"] = 1
        out = sides.merge(rp_seg, on="_k").drop(columns=["_k"])
        out["palette"] = np.nan
        out["size_value"] = np.nan
        out["color_value"] = np.nan
        return out

    barguides_data = processor("bar", _bar_guides_fn)

    segment_data: pd.DataFrame | None = None
    if not barguides_data.empty:
        bg = barguides_data.copy()
        bg["colour"] = "black"
        bg["size"] = 0.5
        bg["linetype"] = "dashed"
        segment_data = bg

    # --- text --------------------------------------------------------------
    def _text_fn(dat: pd.DataFrame) -> pd.DataFrame:
        out = dat.copy()
        out["colour"] = "black"
        # preserve NaN; only stringify real values so the renderer can skip empties.
        out["label_value"] = out["label_value"].map(
            lambda v: v if _is_na(v) else str(v)
        )
        return out

    text_data = processor("text", _text_fn)

    # --- pie ---------------------------------------------------------------
    def _pie_fn(dat: pd.DataFrame) -> pd.DataFrame:
        # size_value is a dict -> expand to rows of (color_value, size_value)
        rows = []
        for _, r in dat.iterrows():
            v = r["size_value"]
            if not isinstance(v, dict):
                continue
            total = sum(x for x in v.values() if np.isfinite(x))
            if total <= 0:
                continue
            cum = 0.0
            for cat, val in v.items():
                if not np.isfinite(val) or val <= 0:
                    continue
                pct = val / total
                rad = pct * 2 * pi
                rad_start = cum
                rad_end = cum + rad
                cum = rad_end
                rows.append(
                    {
                        **{k: r[k] for k in r.index if k not in ("color_value", "size_value")},
                        "color_value": cat,
                        "size_value": val,
                        "x0": r["x"],
                        "y0": r["y"],
                        "pct": pct,
                        "rad": rad,
                        "rad_start": rad_start,
                        "rad_end": rad_end,
                        "r0": 0.0,
                        "r": row_height / 2,
                    }
                )
        return pd.DataFrame(rows)

    pie_data = processor("pie", _pie_fn)

    # --- image -------------------------------------------------------------
    def _img_fn(dat: pd.DataFrame) -> pd.DataFrame:
        out = dat.copy()
        out["path"] = out.get("value", out.get("label_value"))
        if "directory" in out.columns:
            out["path"] = [
                v if (_is_na(v) or _is_na(d)) else f"{d}/{v}"
                for v, d in zip(out["path"], out["directory"])
            ]
        if "extension" in out.columns:
            out["path"] = [
                v if (_is_na(v) or _is_na(e)) else f"{v}.{e}"
                for v, e in zip(out["path"], out["extension"])
            ]
        out["y0"] = out["y"] - row_height
        out["height"] = row_height
        out["width"] = row_height
        return out

    img_data = processor("image", _img_fn)

    # ---------- row annotation ---------------------------------------------
    if plot_row_annotation and row_groups is not None:
        long = row_groups.melt(
            id_vars="group", var_name="level", value_name="name"
        )
        long = long.merge(
            row_pos[["group", "ymin", "ymax"]], on="group", how="left"
        )
        ann = (
            long.groupby("name")
            .agg(ymin=("ymin", "min"), ymax=("ymax", "max"))
            .reset_index()
        )
        ann["y"] = (ann["ymin"] + ann["ymax"]) / 2
        ann["xmin"] = -0.5
        ann["xmax"] = 5
        ann = ann[~ann["name"].map(_is_na) & (ann["name"] != "")]
        if not ann.empty:
            extra = pd.DataFrame(
                {
                    "xmin": ann["xmin"],
                    "xmax": ann["xmax"],
                    "ymin": ann["ymax"] + row_space,
                    "label_value": [str(n).replace("\n", " ") for n in ann["name"]],
                    "hjust": 0.0,
                    "vjust": 0.5,
                    "fontface": "bold",
                }
            )
            extra["ymax"] = extra["ymin"] + row_height
            text_data = pd.concat([text_data, extra], ignore_index=True)

    # ---------- column annotation ------------------------------------------
    if plot_column_annotation and column_groups is not None:
        long_cols = [c for c in column_groups.columns if c not in ("group", "palette")]
        long = column_groups.melt(
            id_vars=["group", "palette"] if "palette" in column_groups.columns else ["group"],
            value_vars=long_cols,
            var_name="level",
            value_name="name",
        )
        if "palette" not in long.columns:
            long["palette"] = np.nan
        # R aggregates per group across ALL its child columns:
        #   left_join(column_pos %>% select("group", "xmin", "xmax"), by = "group")
        # then later groups by `level, name, palette` and takes min(xmin)/max(xmax).
        # Using drop_duplicates here would collapse multi-column groups to their
        # first column's extent, breaking ribbon width. Aggregate explicitly.
        group_extents = (
            column_pos.groupby("group")
            .agg(xmin=("xmin", "min"), xmax=("xmax", "max"))
            .reset_index()
        )
        long = long.merge(group_extents, on="group", how="left")

        level_order = list(column_groups.columns)
        # level heights
        lh_records = []
        text_pct = 0.9
        for lvl in long["level"].unique():
            sub = long[long["level"] == lvl]
            max_newlines = max((str(n).count("\n") if not _is_na(n) else 0) for n in sub["name"])
            h = (max_newlines + 1) * text_pct + (1 - text_pct)
            lh_records.append(
                {
                    "level": lvl,
                    "max_newlines": max_newlines,
                    "height": h,
                    "levelmatch": level_order.index(lvl) if lvl in level_order else 99,
                }
            )
        level_heights = pd.DataFrame(lh_records).sort_values(
            "levelmatch", ascending=False
        )
        level_heights["ysep"] = row_space
        level_heights["ymax"] = col_annot_offset + np.cumsum(level_heights["height"] + level_heights["ysep"]) - level_heights["ysep"]
        level_heights["ymin"] = level_heights["ymax"] - level_heights["height"]
        level_heights["y"] = (level_heights["ymin"] + level_heights["ymax"]) / 2

        agg = (
            long.groupby(["level", "name", "palette"], dropna=False)
            .agg(xmin=("xmin", "min"), xmax=("xmax", "max"))
            .reset_index()
        )
        agg["x"] = (agg["xmin"] + agg["xmax"]) / 2
        agg = agg.merge(level_heights, on="level", how="left")
        agg = agg[~agg["name"].map(_is_na)]
        # keep only labels containing letters
        agg = agg[agg["name"].astype(str).str.contains("[A-Za-z]", regex=True, na=False)]

        # midpoint colour per palette
        def _pal_mid(pname):
            if _is_na(pname) or pname not in palettes:
                return "#777777"
            pal = palettes[pname]
            if isinstance(pal, list):
                return pal[len(pal) // 2]
            if isinstance(pal, dict):
                vals = list(pal.values())
                return vals[len(vals) // 2] if vals else "#777777"
            return "#777777"

        agg["colour"] = [_pal_mid(p) for p in agg["palette"]]

        # R: `alpha = ifelse(.data$levelmatch == 1, 1, .25)` — top level gets
        # full opacity (so the bold white abc letters read against the colored
        # ribbon), sub-levels at 0.25.
        rect_extra = pd.DataFrame(
            {
                "xmin": agg["xmin"],
                "xmax": agg["xmax"],
                "ymin": agg["ymin"],
                "ymax": agg["ymax"],
                "colour": agg["colour"],
                "alpha": np.where(agg["levelmatch"] == 0, 1.0, 0.25),
                "border": False,
            }
        )
        rect_data = pd.concat([rect_data, rect_extra], ignore_index=True)

        text_extra = pd.DataFrame(
            {
                "xmin": agg["xmin"],
                "xmax": agg["xmax"],
                "ymin": agg["ymin"],
                "ymax": agg["ymax"],
                "hjust": 0.5,
                "vjust": 0.5,
                "fontface": [
                    "bold" if lm == 0 else "plain" for lm in agg["levelmatch"]
                ],
                "colour": np.where(agg["levelmatch"] == 0, "white", "black"),
                "label_value": agg["name"].astype(str),
            }
        )
        text_data = pd.concat([text_data, text_extra], ignore_index=True)

        if add_abc:
            top = agg[agg["levelmatch"] == 0].sort_values("x").reset_index(drop=True)
            if not top.empty:
                letters = "abcdefghijklmnopqrstuvwxyz"
                abc = pd.DataFrame(
                    {
                        "xmin": top["xmin"] + col_space,
                        "xmax": top["xmax"] - col_space,
                        "ymin": top["ymin"],
                        "ymax": top["ymax"],
                        "hjust": 0.0,
                        "vjust": 0.5,
                        "fontface": "bold",
                        "colour": "white",
                        "label_value": [f"{letters[i]})" for i in range(len(top))],
                    }
                )
                text_data = pd.concat([text_data, abc], ignore_index=True)

    # ---------- column name labels -----------------------------------------
    # R: `filter(.data$name != "")` — NA names also dropped (NA != "" -> NA -> FALSE)
    name_mask = column_pos["name"].map(lambda v: not _is_na(v) and str(v) != "")
    cn = column_pos[name_mask].copy()
    if not cn.empty:
        seg_extra = pd.DataFrame(
            {"x": cn["x"], "xend": cn["x"], "y": -0.3, "yend": -0.1, "size": 0.5}
        )
        segment_data = (
            pd.concat([segment_data, seg_extra], ignore_index=True)
            if segment_data is not None
            else seg_extra
        )
        tn_extra = pd.DataFrame(
            {
                "xmin": cn["xmin"],
                "xmax": cn["xmax"],
                "ymin": 0,
                "ymax": col_annot_offset,
                "angle": col_annot_angle,
                "vjust": 0,
                "hjust": 0,
                "label_value": cn["name"].astype(str),
            }
        )
        text_data = pd.concat([text_data, tn_extra], ignore_index=True)

    # ---------- merge bars into rects --------------------------------------
    if not bar_data.empty:
        rect_data = pd.concat([rect_data, bar_data], ignore_index=True)
    bar_data = pd.DataFrame()

    # ---------- 100% pies -> circles ---------------------------------------
    if not pie_data.empty:
        pie_data["pct"] = (pie_data["rad_end"] - pie_data["rad_start"]) / (2 * pi)
        full = pie_data[pie_data["pct"] >= 1 - 1e-10].copy()
        pie_data = pie_data[pie_data["pct"] < 1 - 1e-10]
        if not full.empty:
            full = full.drop(columns=[c for c in ("label_value",) if c in full.columns])
            full["color_value"] = 1
            circle_data = pd.concat([circle_data, full], ignore_index=True)

    return {
        "row_pos": row_pos,
        "column_pos": column_pos,
        "segment_data": segment_data if segment_data is not None else pd.DataFrame(),
        "rect_data": rect_data,
        "circle_data": circle_data,
        "funkyrect_data": funkyrect_data,
        "pie_data": pie_data,
        "img_data": img_data,
        "text_data": text_data,
        "viz_params": {"row_space": row_space},
    }
