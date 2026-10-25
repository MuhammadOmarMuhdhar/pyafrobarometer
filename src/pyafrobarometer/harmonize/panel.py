"""Build multi-round panel frames from harmonized datasets."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from pyafrobarometer.errors import HarmonizationError

PANEL_KEYS = ["round", "country", "year"]


def concat_frames(
    frames: Sequence[pd.DataFrame], *, variables: Sequence[str]
) -> pd.DataFrame:
    columns = PANEL_KEYS + list(variables)
    missing = sorted(
        {
            name
            for frame in frames
            for name in variables
            if name not in frame.columns
        }
    )
    if missing:
        raise HarmonizationError(
            f"Cannot build panel; variables missing from one or more rounds: "
            f"{', '.join(missing)}"
        )
    prepared: list[pd.DataFrame] = []
    for frame in frames:
        working = frame.copy()
        for key in PANEL_KEYS:
            if key not in working.columns:
                working[key] = pd.NA
        prepared.append(working[columns])
    if not prepared:
        return pd.DataFrame(columns=columns)
    return pd.concat(prepared, ignore_index=True)
