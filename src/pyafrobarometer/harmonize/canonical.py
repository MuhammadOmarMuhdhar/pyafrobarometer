"""Apply the canonical crosswalk to a survey frame."""

from __future__ import annotations

import warnings
from collections.abc import Sequence
from typing import Any

import pandas as pd

from pyafrobarometer import metadata
from pyafrobarometer.errors import HarmonizationError
from pyafrobarometer.harmonize.crosswalk import Mapping, canonical_map, family_map


def _recode(series: pd.Series, recode: dict[int, int]) -> pd.Series:
    def convert(value: Any) -> Any:
        if pd.isna(value):
            return value
        try:
            key = int(value)
        except (TypeError, ValueError):
            return value
        return recode.get(key, value)

    return series.map(convert)


def apply_canonical(
    df: pd.DataFrame,
    *,
    round_number: int,
    meta: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, str]]:
    frame = df.copy()
    applied: dict[str, str] = {}
    for name, rounds in canonical_map().items():
        spec: Mapping | None = rounds.get(round_number)
        if spec is None:
            continue
        source = spec.var
        if name == "weight" and "withinwt_hh" in df.columns:
            source = "withinwt_hh"
        if source not in df.columns:
            warnings.warn(
                f"Canonical variable {name!r} needs {source!r}, which is absent in "
                f"round {round_number}; omitting it",
                UserWarning,
                stacklevel=2,
            )
            continue
        series = df[source]
        if spec.recode:
            series = _recode(series, spec.recode)
        if spec.decode_country:
            series = metadata.decode_column(
                series, metadata.value_labels(meta, source)
            )
        frame[name] = series
        applied[name] = source
    return frame, applied


def apply_families(
    df: pd.DataFrame,
    *,
    round_number: int,
    families: Sequence[str],
    strict: bool = True,
) -> tuple[pd.DataFrame, dict[str, str]]:
    frame = df.copy()
    applied: dict[str, str] = {}
    crosswalk = family_map()
    for family in families:
        rounds = crosswalk.get(family)
        if rounds is None:
            raise HarmonizationError(f"Unknown question family: {family}")
        available = sorted(rounds)
        spec = rounds.get(round_number)
        if spec is None or spec.var not in df.columns:
            message = (
                f"{family} is available in rounds {available} but not round {round_number}"
            )
            if strict:
                raise HarmonizationError(message)
            warnings.warn(message, UserWarning, stacklevel=2)
            frame[family] = pd.NA
            continue
        series = df[spec.var]
        if spec.recode:
            series = _recode(series, spec.recode)
        frame[family] = series
        applied[family] = spec.var
    return frame, applied
