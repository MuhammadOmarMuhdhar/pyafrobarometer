"""Variable search over the shipped metadata index."""

from __future__ import annotations

import importlib.resources
import json
from collections.abc import Iterable
from typing import cast

import pandas as pd

from pyafrobarometer.errors import CatalogError

INDEX_COLUMNS = [
    "name",
    "label",
    "round",
    "kind",
    "family",
    "source_var",
    "value_labels",
]
RESULT_COLUMNS = [
    "name",
    "label",
    "round",
    "kind",
    "family",
    "source_var",
    "score",
]


def load_index() -> pd.DataFrame:
    resource = importlib.resources.files("pyafrobarometer").joinpath(
        "metadata_index.json"
    )
    try:
        payload = json.loads(resource.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CatalogError(f"Could not read the metadata index: {exc}") from exc
    variables = payload.get("variables") if isinstance(payload, dict) else None
    if not isinstance(variables, list):
        raise CatalogError("Metadata index has no variables list")
    return cast(pd.DataFrame, pd.DataFrame(variables, columns=INDEX_COLUMNS))


def _round_filter(rounds: int | Iterable[int] | None) -> set[int] | None:
    if rounds is None:
        return None
    if isinstance(rounds, int):
        return {rounds}
    return {int(round_number) for round_number in rounds}


def _score(query: str, name: str, label: str, fuzzy: bool) -> float:
    haystack = f"{name} {label}".casefold()
    needle = query.casefold()
    if fuzzy:
        try:
            from rapidfuzz import fuzz
        except ImportError:
            pass
        else:
            return float(fuzz.WRatio(needle, haystack))
    return 100.0 if needle in haystack else 0.0


def search_variables(
    query: str,
    *,
    rounds: int | Iterable[int] | None = None,
    limit: int = 20,
    fuzzy: bool = True,
    index: pd.DataFrame | None = None,
) -> pd.DataFrame:
    frame = (load_index() if index is None else index.copy())
    if frame.empty:
        return cast(pd.DataFrame, pd.DataFrame(columns=RESULT_COLUMNS))
    wanted = _round_filter(rounds)
    if wanted is not None:
        frame = frame[frame["round"].astype(int).isin(wanted)]
    if frame.empty:
        return cast(pd.DataFrame, pd.DataFrame(columns=RESULT_COLUMNS))

    scores = [
        _score(query, str(row["name"]), str(row["label"]), fuzzy)
        for _, row in frame.iterrows()
    ]
    result = frame.assign(score=scores)
    if fuzzy:
        result = result[result["score"] >= 60.0]
    else:
        result = result[result["score"] > 0.0]
    result = result.sort_values(["score", "round"], ascending=[False, False])
    result = result.head(limit).reset_index(drop=True)
    return cast(pd.DataFrame, result[RESULT_COLUMNS])
