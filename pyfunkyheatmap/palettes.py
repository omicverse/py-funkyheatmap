"""Color palette utilities.

We replicate ``RColorBrewer::brewer.pal`` for the handful of palettes that
funkyheatmap defaults to (``Blues``, ``Reds``, ``YlOrBr``, ``Greens``,
``Greys``, ``Set1``, ``Set2``, ``Set3``, ``Dark2``). The colour stops are
copied verbatim from the ``RColorBrewer`` source distribution and then
interpolated with a 101-step linear ramp ("smear") that matches R's
``grDevices::colorRampPalette``.
"""

from __future__ import annotations

from typing import Iterable

import numpy as np
from matplotlib.colors import LinearSegmentedColormap, to_rgb

# Verbatim from RColorBrewer (n=9). Lower-n palettes are produced by slicing
# the n=9 table the same way R does.
_BREWER_9 = {
    "Blues": [
        "#F7FBFF", "#DEEBF7", "#C6DBEF", "#9ECAE1", "#6BAED6",
        "#4292C6", "#2171B5", "#08519C", "#08306B",
    ],
    "Reds": [
        "#FFF5F0", "#FEE0D2", "#FCBBA1", "#FC9272", "#FB6A4A",
        "#EF3B2C", "#CB181D", "#A50F15", "#67000D",
    ],
    "YlOrBr": [
        "#FFFFE5", "#FFF7BC", "#FEE391", "#FEC44F", "#FE9929",
        "#EC7014", "#CC4C02", "#993404", "#662506",
    ],
    "Greens": [
        "#F7FCF5", "#E5F5E0", "#C7E9C0", "#A1D99B", "#74C476",
        "#41AB5D", "#238B45", "#006D2C", "#00441B",
    ],
    "Greys": [
        "#FFFFFF", "#F0F0F0", "#D9D9D9", "#BDBDBD", "#969696",
        "#737373", "#525252", "#252525", "#000000",
    ],
}

# Categorical palettes — RColorBrewer maximum n.
_BREWER_CAT = {
    "Set1": [
        "#E41A1C", "#377EB8", "#4DAF4A", "#984EA3", "#FF7F00",
        "#FFFF33", "#A65628", "#F781BF", "#999999",
    ],
    "Set2": [
        "#66C2A5", "#FC8D62", "#8DA0CB", "#E78AC3", "#A6D854",
        "#FFD92F", "#E5C494", "#B3B3B3",
    ],
    "Set3": [
        "#8DD3C7", "#FFFFB3", "#BEBADA", "#FB8072", "#80B1D3",
        "#FDB462", "#B3DE69", "#FCCDE5", "#D9D9D9", "#BC80BD",
        "#CCEBC5", "#FFED6F",
    ],
    "Dark2": [
        "#1B9E77", "#D95F02", "#7570B3", "#E7298A", "#66A61E",
        "#E6AB02", "#A6761D", "#666666",
    ],
}


def brewer_pal(name: str, n: int | None = None) -> list[str]:
    """Look up a ColorBrewer palette by name. Returns hex strings."""
    if name in _BREWER_9:
        full = _BREWER_9[name]
        if n is None or n >= len(full):
            return list(full)
        # RColorBrewer slices a curated table for n < 9; for our defaults we
        # only ever call with n = 9 or the full categorical set, so a simple
        # head-slice suffices.
        return list(full[:n])
    if name in _BREWER_CAT:
        full = _BREWER_CAT[name]
        if n is None:
            return list(full)
        return list(full[:n])
    raise KeyError(f"Unknown ColorBrewer palette: {name!r}")


def _smear(colors: Iterable[str], n: int = 101) -> list[str]:
    """Mimic R ``colorRampPalette(cols)(n)`` — interpolate in RGB space."""
    cols = list(colors)
    cmap = LinearSegmentedColormap.from_list("_tmp", cols, N=n)
    rgba = cmap(np.linspace(0, 1, n))
    out = []
    for r, g, b, _ in rgba:
        out.append(
            "#{:02X}{:02X}{:02X}".format(
                int(round(r * 255)), int(round(g * 255)), int(round(b * 255))
            )
        )
    return out


def _build_default_palettes() -> dict[str, dict[str, list[str]]]:
    # numerical palettes are reversed and ramped to 101 steps, with
    # per-palette tweaks the R package applies.
    blues = list(reversed(brewer_pal("Blues") + ["#011636"]))
    reds = list(reversed(brewer_pal("Reds")[:7]))
    ylorbr = list(reversed(brewer_pal("YlOrBr")[:6]))
    greens = list(reversed(brewer_pal("Greens")[1:] + ["#00250F"]))
    greys = list(reversed(brewer_pal("Greys")[1:]))
    numerical = {
        "Blues": _smear(blues),
        "Reds": _smear(reds),
        "YlOrBr": _smear(ylorbr),
        "Greens": _smear(greens),
        "Greys": _smear(greys),
    }
    numerical["Grays"] = numerical["Greys"]
    categorical = {
        "Set3": brewer_pal("Set3"),
        "Set1": brewer_pal("Set1"),
        "Set2": brewer_pal("Set2"),
        "Dark2": brewer_pal("Dark2"),
    }
    return {"numerical": numerical, "categorical": categorical}


DEFAULT_PALETTES = _build_default_palettes()


def hex_to_rgb(color: str) -> tuple[float, float, float]:
    return to_rgb(color)


def is_color(s) -> bool:
    """Loose check: a non-NA string that matplotlib accepts as a color."""
    if s is None:
        return False
    if isinstance(s, float) and np.isnan(s):
        return False
    try:
        to_rgb(s)
        return True
    except (ValueError, TypeError):
        return False
