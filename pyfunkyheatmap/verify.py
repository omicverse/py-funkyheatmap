"""Input validators (``verify_*``). One per public R function.

Each validator mutates a *copy* of the input frame and returns it, never the
original — this matches the R contract and is cheaper than the user thinks
(pandas copies are shallow over object columns).
"""

from __future__ import annotations

import json
from typing import Any

import numpy as np
import pandas as pd

from .palettes import DEFAULT_PALETTES, is_color

_VALID_GEOMS = {"funkyrect", "circle", "rect", "bar", "pie", "text", "image"}


def _as_dataframe(x: Any, name: str) -> pd.DataFrame:
    if isinstance(x, pd.DataFrame):
        return x.copy()
    if isinstance(x, dict):
        return pd.DataFrame(x)
    if isinstance(x, np.ndarray):
        return pd.DataFrame(x)
    raise TypeError(f"{name} must be a DataFrame (got {type(x).__name__}).")


def _is_na(value) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and np.isnan(value):
        return True
    if isinstance(value, str):
        return False
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _na_mask(series: pd.Series) -> np.ndarray:
    return series.map(_is_na).to_numpy(dtype=bool)


def _to_title(s: str) -> str:
    return " ".join(part.capitalize() for part in s.replace("_", " ").split())


# ---------------------------------------------------------------------------
# verify_data
# ---------------------------------------------------------------------------

def verify_data(data) -> pd.DataFrame:
    """Ensure ``data`` is a DataFrame with an ``id`` column."""
    df = _as_dataframe(data, "data")
    if df.shape[0] < 1 or df.shape[1] < 1:
        raise ValueError("data must have at least one row and one column.")
    if "id" not in df.columns:
        if df.index.name or not isinstance(df.index, pd.RangeIndex):
            df = df.reset_index().rename(columns={df.index.name or "index": "id"})
        else:
            raise ValueError(
                "data must contain a column 'id' (or a non-default index)."
            )
    return df


# ---------------------------------------------------------------------------
# verify_column_info
# ---------------------------------------------------------------------------

def _infer_geom(series: pd.Series) -> str:
    if pd.api.types.is_numeric_dtype(series):
        return "funkyrect"
    if pd.api.types.is_bool_dtype(series):
        return "text"
    sample = series.dropna()
    if len(sample) > 0 and all(
        isinstance(v, dict)
        and all(isinstance(k, str) for k in v.keys())
        and all(isinstance(x, (int, float, np.floating, np.integer)) for x in v.values())
        for v in sample
    ):
        return "pie"
    return "text"


def verify_column_info(column_info, data: pd.DataFrame) -> pd.DataFrame:
    if column_info is None:
        ci = pd.DataFrame({"id": list(data.columns)})
    else:
        ci = _as_dataframe(column_info, "column_info")

    if "id" not in ci.columns:
        raise ValueError("column_info must contain an 'id' column.")
    if not all(cid in data.columns for cid in ci["id"]):
        missing = [cid for cid in ci["id"] if cid not in data.columns]
        raise ValueError(f"column_info$id refers to missing columns: {missing}")

    # options: parse JSON, spread to columns
    if "options" in ci.columns:
        def _parse(opt):
            if _is_na(opt):
                return {}
            if isinstance(opt, str):
                return json.loads(opt)
            if isinstance(opt, dict):
                return dict(opt)
            return dict(opt)
        parsed = ci["options"].map(_parse).tolist()
        ci = ci.drop(columns=["options"]).reset_index(drop=True)
        # collect new columns first to choose object dtype upfront so we don't
        # silently coerce strings to float NaN -> str
        new_cols: dict[str, list] = {}
        for row_idx, opt in enumerate(parsed):
            for key, value in opt.items():
                if key not in ci.columns and key not in new_cols:
                    new_cols[key] = [np.nan] * len(ci)
                if key in new_cols:
                    new_cols[key][row_idx] = value
                else:
                    ci.at[row_idx, key] = value
        for key, values in new_cols.items():
            ci[key] = pd.array(values, dtype="object")

    # name — mirror R: only derive when the column is *entirely* missing.
    # Per-cell NaN stays NaN, so the column-label code can filter them out
    # (matching R `filter(.data$name != "")` where NA is dropped).
    if "name" not in ci.columns:
        ci["name"] = [_to_title(str(x)) for x in ci["id"]]

    # geom — infer per column
    if "geom" not in ci.columns:
        ci["geom"] = [_infer_geom(data[cid]) for cid in ci["id"]]
    bad = ~ci["geom"].isin(_VALID_GEOMS)
    if bad.any():
        bad_ids = ci.loc[bad, "id"].tolist()
        raise ValueError(f"Invalid geom types for columns: {bad_ids}")

    # id_color (with id_colour alias)
    if "id_colour" in ci.columns:
        ci["id_color"] = ci["id_colour"]
        ci = ci.drop(columns=["id_colour"])
    if "id_color" not in ci.columns:
        ci["id_color"] = np.nan
    new_color = []
    for cid, geom, idc in zip(ci["id"], ci["geom"], ci["id_color"]):
        if not _is_na(idc):
            new_color.append(idc)
        elif geom in ("text", "image"):
            new_color.append(np.nan)
        else:
            new_color.append(cid)
    ci["id_color"] = new_color

    # id_size
    if "id_size" not in ci.columns:
        ci["id_size"] = np.nan
    new_size = []
    for cid, geom, ids in zip(ci["id"], ci["geom"], ci["id_size"]):
        if not _is_na(ids):
            new_size.append(ids)
        elif geom in ("text", "image", "rect"):
            new_size.append(np.nan)
        else:
            new_size.append(cid)
    ci["id_size"] = new_size

    # group
    if "group" not in ci.columns:
        ci["group"] = np.nan
    ci["group"] = ci["group"].where(ci["group"].astype(object) != "", np.nan)

    # palette
    if "palette" not in ci.columns or ci["palette"].map(_is_na).all():
        ci["palette"] = [
            np.nan if g in ("text", "image") else ("categorical_palette" if g == "pie" else "numerical_palette")
            for g in ci["geom"]
        ]

    # width
    if "width" not in ci.columns:
        ci["width"] = [
            6.0 if g == "text" else (4.0 if g == "bar" else 1.0)
            for g in ci["geom"]
        ]
    ci["width"] = ci["width"].fillna(1.0).astype(float)

    # overlay
    if "overlay" not in ci.columns:
        ci["overlay"] = False
    ci["overlay"] = ci["overlay"].fillna(False).astype(bool)

    # legend (defaults to True except for text)
    if "legend" not in ci.columns:
        ci["legend"] = np.nan
    ci["legend"] = [
        (g != "text") if _is_na(l) else bool(l)
        for g, l in zip(ci["geom"], ci["legend"])
    ]

    # draw_outline
    if "draw_outline" not in ci.columns:
        ci["draw_outline"] = True
    ci["draw_outline"] = ci["draw_outline"].fillna(True).astype(bool)

    return ci.reset_index(drop=True)


# ---------------------------------------------------------------------------
# verify_row_info
# ---------------------------------------------------------------------------

def verify_row_info(row_info, data: pd.DataFrame) -> pd.DataFrame:
    if row_info is None:
        return pd.DataFrame({"id": list(data["id"]), "group": [np.nan] * len(data)})
    ri = _as_dataframe(row_info, "row_info")
    if "id" not in ri.columns:
        raise ValueError("row_info must contain an 'id' column.")
    if not all(rid in set(data["id"]) for rid in ri["id"]):
        missing = [rid for rid in ri["id"] if rid not in set(data["id"])]
        raise ValueError(f"row_info$id refers to missing rows: {missing}")
    if "group" not in ri.columns:
        ri["group"] = np.nan
    return ri.reset_index(drop=True)


# ---------------------------------------------------------------------------
# verify_column_groups / verify_row_groups
# ---------------------------------------------------------------------------

def verify_column_groups(column_groups, column_info: pd.DataFrame):
    if column_groups is None:
        if not column_info["group"].map(_is_na).all():
            cg = (
                column_info[["group"]]
                .dropna()
                .drop_duplicates()
                .reset_index(drop=True)
            )
        else:
            return None
    else:
        cg = _as_dataframe(column_groups, "column_groups")
    if "group" not in cg.columns:
        raise ValueError("column_groups must contain a 'group' column.")
    if "palette" not in cg.columns:
        cg["palette"] = np.nan
    extras = [c for c in cg.columns if c not in ("group", "palette")]
    if not extras:
        cg["level1"] = [_to_title(str(g)) for g in cg["group"]]
    return cg.reset_index(drop=True)


def verify_row_groups(row_groups, row_info: pd.DataFrame):
    if row_groups is None:
        if not row_info["group"].map(_is_na).all():
            rg = (
                row_info[["group"]]
                .dropna()
                .drop_duplicates()
                .reset_index(drop=True)
            )
        else:
            return None
    else:
        rg = _as_dataframe(row_groups, "row_groups")
    if "group" not in rg.columns:
        raise ValueError("row_groups must contain a 'group' column.")
    extras = [c for c in rg.columns if c != "group"]
    if not extras:
        rg["level1"] = [_to_title(str(g)) for g in rg["group"]]
    return rg.reset_index(drop=True)


# ---------------------------------------------------------------------------
# verify_palettes
# ---------------------------------------------------------------------------

def verify_palettes(palettes, column_info: pd.DataFrame, data: pd.DataFrame) -> dict[str, Any]:
    if palettes is None:
        palettes = {}
    elif isinstance(palettes, pd.DataFrame):
        palettes = dict(zip(palettes.iloc[:, 0], palettes.iloc[:, 1]))
    elif not isinstance(palettes, dict):
        raise TypeError("palettes must be a dict, DataFrame, or None.")
    palettes = dict(palettes)

    col_info_palettes = [p for p in column_info["palette"].unique() if not _is_na(p)]
    rotation = {"numerical": 0, "categorical": 0}
    rot_names = {
        "numerical": list(DEFAULT_PALETTES["numerical"].keys()),
        "categorical": list(DEFAULT_PALETTES["categorical"].keys()),
    }
    # Skip the duplicate "Grays" alias for rotation order.
    rot_names["numerical"] = [n for n in rot_names["numerical"] if n != "Grays"]

    for palette_id in col_info_palettes:
        if palette_id not in palettes:
            # find a column using this palette
            sub = column_info[column_info["palette"] == palette_id]
            geom = sub.iloc[0]["geom"]
            cid = sub.iloc[0]["id"]
            if geom == "pie":
                ptype = "categorical"
            elif pd.api.types.is_numeric_dtype(data[cid]):
                ptype = "numerical"
            else:
                ptype = "categorical"
            idx = rotation[ptype] % len(rot_names[ptype])
            palettes[palette_id] = rot_names[ptype][idx]
            rotation[ptype] += 1

        pal_value = palettes[palette_id]
        if isinstance(pal_value, str):
            if pal_value in DEFAULT_PALETTES["numerical"]:
                palettes[palette_id] = list(DEFAULT_PALETTES["numerical"][pal_value])
            elif pal_value in DEFAULT_PALETTES["categorical"]:
                cols = column_info[column_info["palette"] == palette_id]
                cats: list = []
                for _, row in cols.iterrows():
                    cid = row["id"]
                    geom = row["geom"]
                    if cid not in data.columns:
                        continue
                    col = data[cid]
                    if isinstance(col, pd.DataFrame):
                        col = col.iloc[:, 0]
                    if geom == "pie":
                        vals = [
                            k
                            for d in col.dropna()
                            for k in (d.keys() if isinstance(d, dict) else [])
                        ]
                    else:
                        vals = col.dropna().tolist()
                    cats.extend(vals)
                seen = []
                for v in cats:
                    if v not in seen:
                        seen.append(v)
                base = DEFAULT_PALETTES["categorical"][pal_value]
                if len(base) < len(seen):
                    raise ValueError(
                        f"Palette '{pal_value}' has {len(base)} colors but "
                        f"{len(seen)} categories needed."
                    )
                palettes[palette_id] = {cat: base[i] for i, cat in enumerate(seen)}
            else:
                # treat as a single colour, expand to a one-stop palette
                palettes[palette_id] = [pal_value]
    return palettes


# ---------------------------------------------------------------------------
# verify_legends
# ---------------------------------------------------------------------------

def verify_legends(legends, palettes, column_info: pd.DataFrame, data: pd.DataFrame) -> list[dict[str, Any]]:
    """Match R ``verify_legends``: add one auto-legend per palette referenced
    in ``column_info``, regardless of any individual column's ``legend`` flag;
    disable text/image legends that have no explicit labels.
    """
    if legends is None:
        legends = []
    if not isinstance(legends, list):
        raise TypeError("legends must be a list of dicts.")
    legends = [dict(l) for l in legends]
    legend_palettes = {l.get("palette") for l in legends if "palette" in l}

    # R: palettes_in_col_info <- na.omit(unique(column_info$palette))
    #    used_palettes <- intersect(palettes_in_col_info, names(palettes))
    palettes_in_col_info = [
        p for p in column_info["palette"].unique() if not _is_na(p)
    ]
    used_palettes = [p for p in palettes_in_col_info if p in palettes]
    missing = [p for p in used_palettes if p not in legend_palettes]
    for p in missing:
        legends.append({"title": p, "palette": p, "enabled": True})

    # R default label set: 11 entries, 5 visible (0, 0.2, 0.4, 0.6, 0.8, 1).
    _DEFAULT_RAMP_LABELS = ["0", "", "0.2", "", "0.4", "", "0.6", "", "0.8", "", "1"]

    out: list[dict[str, Any]] = []
    for i, legend in enumerate(legends):
        legend = dict(legend)

        # enabled default
        legend.setdefault("enabled", True)
        if not legend["enabled"]:
            out.append(legend)
            continue

        # title default = palette name
        if "title" not in legend and "palette" in legend:
            legend["title"] = legend["palette"]
        legend.setdefault("title", "")

        # geom default = geom of first column referencing this palette
        if "geom" not in legend and "palette" in legend:
            pal = legend["palette"]
            sub = column_info[
                column_info["palette"].map(lambda v: not _is_na(v) and v == pal)
            ]
            if len(sub) > 0:
                legend["geom"] = sub.iloc[0]["geom"]
        legend.setdefault("geom", "rect")

        # labels defaults
        if "labels" not in legend or not legend["labels"]:
            geom = legend["geom"]
            if geom == "pie" and "palette" in legend:
                pal = palettes.get(legend["palette"], {})
                if isinstance(pal, dict):
                    legend["labels"] = list(pal.keys())
                else:
                    legend["labels"] = [str(i) for i in range(len(pal))]
            elif geom in ("circle", "funkyrect", "rect", "bar"):
                legend["labels"] = list(_DEFAULT_RAMP_LABELS)
            elif geom in ("text", "image"):
                # R disables the legend in this case.
                legend["enabled"] = False
                out.append(legend)
                continue
            else:
                legend["labels"] = []

        # size default
        if legend["geom"] in ("circle", "funkyrect", "rect"):
            if "size" not in legend:
                n = len(legend["labels"])
                legend["size"] = list(np.linspace(0, 1, n)) if n > 1 else [1.0]

        # color default
        if "colour" in legend and "color" not in legend:
            legend["color"] = legend.pop("colour")
        if "color" not in legend and "palette" in legend:
            pal = palettes.get(legend["palette"])
            if isinstance(pal, list) and pal:
                n = len(legend["labels"])
                if n > 0:
                    idxs = np.round(np.linspace(0, len(pal) - 1, n)).astype(int)
                    legend["color"] = [pal[i] for i in idxs]
                else:
                    legend["color"] = []
            elif isinstance(pal, dict):
                legend["color"] = list(pal.values())[: len(legend["labels"])]

        out.append(legend)

    return out
