"""Layout parameters (rows / columns / annotation offsets)."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Mapping


@dataclass
class PositionArguments:
    """Layout knobs for a funky heatmap. Mirrors R ``position_arguments()``.

    Accessing by attribute *or* by key works (``pa.row_height`` and
    ``pa["row_height"]`` both resolve), which keeps the calculation code
    portable between R-style and Python-style access patterns.
    """

    row_height: float = 1.0
    row_space: float = 0.1
    row_bigspace: float = 1.2
    col_width: float = 1.0
    col_space: float = 0.1
    col_bigspace: float = 0.5
    col_annot_offset: float = 3.0
    col_annot_angle: float = 30.0
    col_annot_size: float = 4.0     # column-header font size (ggplot units; × 2.4 → pt)
    cell_text_size: float = 4.0     # default font size for cell-level text (overlay labels etc.)
    col_annot_use_adjust_text: bool = False   # nudge column-header labels apart via adjustText
    col_annot_adjust_text_kwargs: Any = None  # forwarded to adjustText.adjust_text
    col_annot_stagger_h: float = 0.0          # deterministic 2-row stagger; alternates label y by this much
    expand_xmin: float = 0.0
    expand_xmax: float = 2.0
    expand_ymin: float = 0.0
    expand_ymax: float = 0.0

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        setattr(self, key, value)

    def __contains__(self, key: str) -> bool:
        return key in self.__dataclass_fields__

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def position_arguments(**overrides: Any) -> PositionArguments:
    """Build a :class:`PositionArguments` with optional overrides."""
    pa = PositionArguments()
    for key, value in overrides.items():
        if key not in pa:
            raise TypeError(f"Unknown position argument: {key!r}")
        pa[key] = value
    return pa


def coerce_position_args(value: Any) -> PositionArguments:
    if value is None:
        return position_arguments()
    if isinstance(value, PositionArguments):
        return value
    if isinstance(value, Mapping):
        return position_arguments(**dict(value))
    raise TypeError(
        "position_args must be PositionArguments, mapping, or None."
    )
