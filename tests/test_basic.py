"""Smoke tests for the public API."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import numpy as np
import pandas as pd
import pytest

from pyfunkyheatmap import (
    FunkyHeatmap,
    funky_heatmap,
    position_arguments,
    scale_minmax,
    verify_column_info,
    verify_data,
)


@pytest.fixture
def simple_df():
    rng = np.random.default_rng(42)
    return pd.DataFrame(
        {
            "id": [f"m{i}" for i in range(5)],
            "x": rng.uniform(0, 1, 5),
            "y": rng.uniform(0, 1, 5),
            "label": ["A", "B", "C", "D", "E"],
        }
    )


def test_scale_minmax_basic():
    out = scale_minmax(np.array([1.0, 2.0, 3.0]))
    np.testing.assert_allclose(out, [0.0, 0.5, 1.0])


def test_scale_minmax_constant_returns_nan():
    out = scale_minmax(np.array([4.0, 4.0, 4.0]))
    assert np.isnan(out).all()


def test_verify_data_adds_id_from_index():
    df = pd.DataFrame({"x": [1, 2]}, index=["a", "b"])
    df.index.name = "id"
    verified = verify_data(df)
    assert "id" in verified.columns
    assert list(verified["id"]) == ["a", "b"]


def test_verify_column_info_infers_geom(simple_df):
    ci = verify_column_info(None, simple_df)
    geoms = dict(zip(ci["id"], ci["geom"]))
    assert geoms["x"] == "funkyrect"
    assert geoms["label"] == "text"


def test_funky_heatmap_default(simple_df):
    fh = funky_heatmap(simple_df)
    assert isinstance(fh, FunkyHeatmap)
    assert fh.figure is not None
    assert fh.width > 0 and fh.height > 0


def test_funky_heatmap_with_groups(simple_df):
    ci = pd.DataFrame(
        {
            "id": ["label", "x", "y"],
            "name": ["Label", "Metric X", "Metric Y"],
            "geom": ["text", "funkyrect", "circle"],
            "group": ["meta", "scores", "scores"],
        }
    )
    cg = pd.DataFrame({"group": ["meta", "scores"], "level1": ["Info", "Scores"]})
    fh = funky_heatmap(simple_df, column_info=ci, column_groups=cg)
    # we expect one rect per column group plus the inferred geoms
    assert len(fh.geom_positions["funkyrect_data"]) == 5
    assert len(fh.geom_positions["circle_data"]) == 5


def test_position_arguments_override():
    pa = position_arguments(row_height=2.0, col_annot_angle=45)
    assert pa.row_height == 2.0
    assert pa["col_annot_angle"] == 45


def test_unknown_position_argument_raises():
    with pytest.raises(TypeError):
        position_arguments(not_a_field=1.0)
