"""Question concept schema, parsing, and validation."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from pyafrobarometer.errors import HarmonizationError

SUPPORTED_ROUNDS = range(1, 11)
_SLUG = re.compile(r"^[a-z0-9_]+$")


@dataclass(frozen=True)
class QuestionRound:
    var: str | None
    label: str | None
    recode: dict[int, int | None] = field(default_factory=dict)
    missing: tuple[int, ...] = ()
    exclude: bool = False
    reason: str | None = None


@dataclass(frozen=True)
class QuestionDefinition:
    name: str
    description: str
    kind: str
    values: dict[int, str] = field(default_factory=dict)
    rounds: dict[int, QuestionRound] = field(default_factory=dict)


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _parse_values(raw: Any) -> dict[int, str]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise HarmonizationError("values must be a mapping")
    values: dict[int, str] = {}
    for key, label in raw.items():
        code = _as_int(key)
        if code is None:
            raise HarmonizationError(f"values code {key!r} is not an integer")
        values[code] = str(label)
    return values


def _parse_recode(raw: Any) -> dict[int, int | None]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise HarmonizationError("recode must be a mapping")
    recode: dict[int, int | None] = {}
    for key, target in raw.items():
        code = _as_int(key)
        if code is None:
            raise HarmonizationError(f"recode code {key!r} is not an integer")
        if target is None:
            recode[code] = None
            continue
        value = _as_int(target)
        if value is None:
            raise HarmonizationError(f"recode target {target!r} is not an integer or null")
        recode[code] = value
    return recode


def _parse_missing(raw: Any) -> tuple[int, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, (list, tuple)):
        raise HarmonizationError("missing must be a list of integers")
    values: list[int] = []
    for item in raw:
        code = _as_int(item)
        if code is None:
            raise HarmonizationError(f"missing code {item!r} is not an integer")
        values.append(code)
    return tuple(values)


def parse_questions(payload: Mapping[str, Any]) -> dict[str, QuestionDefinition]:
    section = payload.get("questions")
    if not isinstance(section, dict):
        raise HarmonizationError("questions.yaml has no questions section")
    result: dict[str, QuestionDefinition] = {}
    for name, raw in section.items():
        if not isinstance(raw, dict):
            raise HarmonizationError(f"question {name!r} is not a mapping")
        rounds_raw = raw.get("rounds")
        if not isinstance(rounds_raw, dict):
            raise HarmonizationError(f"question {name!r} has no rounds mapping")
        rounds: dict[int, QuestionRound] = {}
        for key, entry in rounds_raw.items():
            round_number = _as_int(key)
            if round_number is None:
                raise HarmonizationError(f"question {name!r} has non-integer round {key!r}")
            if not isinstance(entry, dict):
                raise HarmonizationError(
                    f"question {name!r} round {round_number} is not a mapping"
                )
            var = entry.get("var")
            label = entry.get("label")
            reason = entry.get("reason")
            if var is not None and not isinstance(var, str):
                raise HarmonizationError(
                    f"question {name!r} round {round_number} var is not a string"
                )
            if label is not None and not isinstance(label, str):
                raise HarmonizationError(
                    f"question {name!r} round {round_number} label is not a string"
                )
            if reason is not None and not isinstance(reason, str):
                raise HarmonizationError(
                    f"question {name!r} round {round_number} reason is not a string"
                )
            rounds[round_number] = QuestionRound(
                var=var,
                label=label,
                recode=_parse_recode(entry.get("recode")),
                missing=_parse_missing(entry.get("missing")),
                exclude=bool(entry.get("exclude", False)),
                reason=reason,
            )
        result[str(name)] = QuestionDefinition(
            name=str(name),
            description=str(raw.get("description", name)),
            kind=str(raw.get("kind", "coded")),
            values=_parse_values(raw.get("values")),
            rounds=rounds,
        )
    return result


def _value_labels(row: Any) -> dict[int, str]:
    raw = row.get("value_labels") if hasattr(row, "get") else None
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return {}
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return {}
    if not isinstance(raw, dict):
        return {}
    labels: dict[int, str] = {}
    for key, label in raw.items():
        code = _as_int(key)
        if code is not None:
            labels[code] = str(label)
    return labels


def validate_questions(
    questions: Mapping[str, QuestionDefinition],
    index: pd.DataFrame | None = None,
) -> list[str]:
    problems: list[str] = []
    rows_by_round: dict[int, list[Any]] = {}
    names_by_round: dict[int, set[str]] = {}
    if index is not None and not index.empty:
        for row in index.to_dict("records"):
            round_number = _as_int(row.get("round"))
            if round_number is None:
                continue
            rows_by_round.setdefault(round_number, []).append(row)
            names_by_round.setdefault(round_number, set()).add(
                str(row.get("name", "")).casefold()
            )

    all_index_names = {
        str(row.get("name", "")).casefold()
        for row in (index.to_dict("records") if index is not None else [])
    }
    claims: dict[tuple[int, str], str] = {}

    for name, question in questions.items():
        if not _SLUG.match(name):
            problems.append(f"{name}: name must be a lowercase slug")
        if question.kind not in {"coded", "text"}:
            problems.append(f"{name}: kind must be 'coded' or 'text'")
        if question.kind == "coded" and not question.values:
            problems.append(f"{name}: coded concepts require values")
        if question.kind == "text" and question.values:
            problems.append(f"{name}: text concepts must not define values")
        if name.casefold() in all_index_names:
            problems.append(f"{name}: name collides with a raw or canonical variable")

        for round_number, entry in question.rounds.items():
            if round_number not in SUPPORTED_ROUNDS:
                problems.append(f"{name}: round {round_number} is outside 1-10")
            if entry.exclude:
                if not entry.reason:
                    problems.append(f"{name} round {round_number}: exclude requires a reason")
                if entry.recode:
                    problems.append(f"{name} round {round_number}: excluded rounds cannot recode")
                if entry.missing:
                    problems.append(
                        f"{name} round {round_number}: excluded rounds cannot declare missing"
                    )
                continue
            if not entry.var:
                problems.append(f"{name} round {round_number}: var is required")
            if not entry.label:
                problems.append(f"{name} round {round_number}: label is required")
            if question.kind == "text" and entry.recode:
                problems.append(f"{name} round {round_number}: text concepts cannot recode")
            for code, target in entry.recode.items():
                if target is None:
                    continue
                if target not in question.values:
                    problems.append(
                        f"{name} round {round_number}: recode target {target} is not in values"
                    )
                if code in entry.missing:
                    problems.append(
                        f"{name} round {round_number}: code {code} is both missing and recoded"
                    )
            for code in question.values:
                if code in entry.missing:
                    problems.append(
                        f"{name} round {round_number}: value code {code} is also missing"
                    )
            if entry.var:
                key = (round_number, entry.var.casefold())
                owner = claims.get(key)
                if owner is not None and owner != name:
                    problems.append(
                        f"{name} round {round_number}: {entry.var} is assigned to more than "
                        f"one concept ({owner} and {name})"
                    )
                else:
                    claims[key] = name

                if index is not None and rows_by_round:
                    matches = [
                        row
                        for row in rows_by_round.get(round_number, [])
                        if str(row.get("name", "")).casefold() == entry.var.casefold()
                    ]
                    if not matches:
                        problems.append(
                            f"{name} round {round_number}: var {entry.var} is absent from the index"
                        )
                    elif question.kind == "coded":
                        labels = _value_labels(matches[0])
                        native = {code for code in labels if code not in entry.missing}
                        covered = set(entry.recode) | set(question.values)
                        uncovered = sorted(native - covered)
                        if uncovered:
                            problems.append(
                                f"{name} round {round_number}: uncovered native codes "
                                f"{uncovered}"
                            )
    return problems


def resolve_column(name: str, columns: Iterable[str]) -> str | None:
    matches = [column for column in columns if column.casefold() == name.casefold()]
    if not matches:
        return None
    if len(matches) > 1:
        raise HarmonizationError(
            f"Variable {name!r} is ambiguous; matches {', '.join(matches)}"
        )
    return matches[0]
