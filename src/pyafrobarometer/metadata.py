"""Variable metadata, value labels, and missing-code handling."""

from __future__ import annotations

import re
from typing import Any, cast

import pandas as pd

FALLBACK_MISSING_CODES = (
    -1,
    8,
    9,
    93,
    94,
    95,
    96,
    97,
    98,
    99,
    997,
    998,
    999,
    9994,
    9995,
    9998,
    9999,
)


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError:
            return None
    return None


def _labels(meta: dict[str, Any], column: str) -> dict[int, str]:
    mapping = meta.get("variable_value_labels")
    if not isinstance(mapping, dict):
        return {}
    raw = mapping.get(column)
    if not isinstance(raw, dict):
        return {}
    labels: dict[int, str] = {}
    for key, value in raw.items():
        code = _as_int(key)
        if code is not None:
            labels[code] = str(value)
    return labels


def value_labels(meta: dict[str, Any], column: str) -> dict[int, str]:
    return _labels(meta, column)


def _looks_missing(label: str) -> bool:
    text = label.casefold().replace("’", "'").replace("‘", "'")
    return bool(re.search(r"\bdk\b", text)) or any(
        word in text
        for word in (
            "missing",
            "refused",
            "don't know",
            "dont know",
            "do not know",
            "no answer",
            "unknown",
            "not applicable",
            "not asked",
        )
    )


def _fallback_codes(labels: dict[int, str]) -> set[int]:
    return {
        code
        for code, label in labels.items()
        if code in FALLBACK_MISSING_CODES and _looks_missing(label)
    }


def missing_codes(meta: dict[str, Any], column: str) -> list[int]:
    codes: set[int] = set()
    ranges = meta.get("missing_ranges")
    if isinstance(ranges, dict):
        declared = ranges.get(column)
        if isinstance(declared, dict):
            low = _as_int(declared.get("lo"))
            high = _as_int(declared.get("hi"))
            if low is not None and high is not None:
                codes.update(range(low, high + 1))
    user_values = meta.get("missing_user_values")
    if isinstance(user_values, dict):
        declared_values = user_values.get(column)
        if isinstance(declared_values, (list, tuple, set)):
            for value in declared_values:
                code = _as_int(value)
                if code is not None:
                    codes.add(code)
    codes.update(_fallback_codes(_labels(meta, column)))
    return sorted(codes)


def decode_column(series: pd.Series, labels: dict[int, str]) -> pd.Series:
    def convert(value: Any) -> Any:
        if pd.isna(value):
            return pd.NA
        code = _as_int(value)
        if code is not None and code in labels:
            return labels[code]
        return value

    return cast(
        pd.Series,
        pd.Series([convert(value) for value in series], index=series.index, dtype=object),
    )


def normalize_missing(
    df: pd.DataFrame,
    meta: dict[str, Any],
    columns: list[str] | None = None,
) -> pd.DataFrame:
    out = df.copy()
    for column in columns if columns is not None else list(out.columns):
        if column not in out.columns:
            continue
        codes = missing_codes(meta, column)
        if codes:
            out[column] = out[column].where(~out[column].isin(codes), pd.NA)
    return cast(pd.DataFrame, out)


def variable_info(meta: dict[str, Any]) -> pd.DataFrame:
    names = list(meta.get("column_names") or [])
    label_map = meta.get("column_names_to_labels")
    label_list = list(meta.get("column_labels") or [])
    rows: list[dict[str, Any]] = []
    for index, name in enumerate(names):
        if isinstance(label_map, dict):
            label = label_map.get(name, "")
        elif index < len(label_list):
            label = label_list[index]
        else:
            label = ""
        rows.append(
            {
                "name": name,
                "label": label,
                "value_labels": value_labels(meta, name),
                "missing_codes": missing_codes(meta, name),
            }
        )
    return cast(
        pd.DataFrame,
        pd.DataFrame(rows, columns=["name", "label", "value_labels", "missing_codes"]),
    )
