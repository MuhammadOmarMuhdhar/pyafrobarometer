"""Apply the canonical crosswalk to a survey frame."""

from __future__ import annotations

import warnings
from collections.abc import Mapping as ABCMapping
from collections.abc import Sequence
from typing import Any

import pandas as pd

from pyafrobarometer import metadata
from pyafrobarometer.errors import HarmonizationError
from pyafrobarometer.harmonize.crosswalk import Mapping, canonical_map, question_map
from pyafrobarometer.harmonize.schema import (
    QuestionDefinition,
    resolve_column,
)


def _recode(series: pd.Series, recode: ABCMapping[int, int | None]) -> pd.Series:
    def convert(value: Any) -> Any:
        if pd.isna(value):
            return value
        try:
            key = int(value)
        except (TypeError, ValueError):
            return value
        target = recode.get(key, value)
        return pd.NA if target is None else target

    return series.map(convert)


def _mask_missing(series: pd.Series, missing: tuple[int, ...]) -> pd.Series:
    if not missing:
        return series
    codes = set(missing)

    def convert(value: Any) -> Any:
        if pd.isna(value):
            return value
        try:
            code = int(value)
        except (TypeError, ValueError):
            return value
        return pd.NA if code in codes else value

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
        actual = resolve_column(source, df.columns)
        if actual is None:
            warnings.warn(
                f"Canonical variable {name!r} needs {source!r}, which is absent in "
                f"round {round_number}; omitting it",
                UserWarning,
                stacklevel=2,
            )
            continue
        series = df[actual]
        if spec.recode:
            series = _recode(series, spec.recode)
        if spec.decode_country:
            series = metadata.decode_column(
                series, metadata.value_labels(meta, actual)
            )
        frame[name] = series
        applied[name] = actual
    return frame, applied


def apply_questions(
    df: pd.DataFrame,
    *,
    round_number: int,
    questions: Sequence[str],
    strict: bool = True,
    catalog: dict[str, QuestionDefinition] | None = None,
) -> tuple[pd.DataFrame, dict[str, str]]:
    frame = df.copy()
    applied: dict[str, str] = {}
    crosswalk = catalog if catalog is not None else question_map()
    for name in questions:
        question = crosswalk.get(name)
        if question is None:
            raise HarmonizationError(f"Unknown question family: {name}")
        available = sorted(
            number for number, entry in question.rounds.items() if not entry.exclude
        )
        entry = question.rounds.get(round_number)
        if entry is None or entry.exclude:
            message = (
                f"{name} is available in rounds {available} but not round {round_number}"
            )
            if entry is not None and entry.reason:
                message = f"{message} ({entry.reason})"
            if strict:
                raise HarmonizationError(message)
            warnings.warn(message, UserWarning, stacklevel=2)
            frame[name] = pd.NA
            continue
        source = entry.var
        actual = resolve_column(source, df.columns) if source else None
        if actual is None:
            message = (
                f"{name} maps to {source!r} in round {round_number}, but that "
                "variable is absent from this file"
            )
            if strict:
                raise HarmonizationError(message)
            warnings.warn(message, UserWarning, stacklevel=2)
            frame[name] = pd.NA
            continue
        series = _mask_missing(df[actual], entry.missing)
        if entry.recode:
            series = _recode(series, entry.recode)
        frame[name] = series
        applied[name] = actual
    return frame, applied


def apply_families(
    df: pd.DataFrame,
    *,
    round_number: int,
    families: Sequence[str],
    strict: bool = True,
) -> tuple[pd.DataFrame, dict[str, str]]:
    return apply_questions(
        df,
        round_number=round_number,
        questions=families,
        strict=strict,
    )
