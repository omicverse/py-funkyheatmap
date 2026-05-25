"""Numeric scaling utilities."""

from __future__ import annotations

import numpy as np
import pandas as pd


def scale_minmax(x):
    """Min-max scale a numeric vector to [0, 1].

    Mirrors R ``scale_minmax``: ``(x - min) / (max - min)`` with NaN-aware
    reduction. A constant vector returns NaN for every element (the R
    package's behaviour). Scalars, lists, numpy arrays and pandas Series are
    all accepted; output type mirrors input.
    """
    arr = np.asarray(x, dtype=float)
    if arr.size == 0:
        return arr
    mn = np.nanmin(arr)
    mx = np.nanmax(arr)
    if mx == mn:
        out = np.full_like(arr, np.nan, dtype=float)
    else:
        out = (arr - mn) / (mx - mn)
    if isinstance(x, pd.Series):
        return pd.Series(out, index=x.index, name=x.name)
    return out
