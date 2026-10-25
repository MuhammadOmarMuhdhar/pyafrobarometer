"""Crosswalk loading for canonical variables and question families."""

from __future__ import annotations

import importlib.resources
from dataclasses import dataclass
from typing import Any

import yaml

from pyafrobarometer.errors import HarmonizationError

SUPPORTED_ROUNDS = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)

_MISSING = object()


@dataclass(frozen=True)
class Mapping:
    var: str
    decode_country: bool = False
    recode: dict[int, int] | None = None


def _load(relative: str) -> dict[str, Any]:
    resource = importlib.resources.files("pyafrobarometer").joinpath(relative)
    try:
        raw = resource.read_text(encoding="utf-8")
    except OSError as exc:
        raise HarmonizationError(f"Could not read crosswalk {relative}: {exc}") from exc
    data = yaml.safe_load(raw)
    if not isinstance(data, dict):
        raise HarmonizationError(f"Crosswalk {relative} is not a YAML mapping")
    return data


def _recode_map(value: Any) -> dict[int, int] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise HarmonizationError(f"recode must be a mapping, got {value!r}")
    return {int(key): int(item) for key, item in value.items()}


def canonical_map() -> dict[str, dict[int, Mapping]]:
    config = _load("crosswalk/canonical.yaml")
    section = config.get("canonical")
    if not isinstance(section, dict):
        raise HarmonizationError("canonical.yaml has no canonical section")
    result: dict[str, dict[int, Mapping]] = {}
    for name, spec in section.items():
        if not isinstance(spec, dict):
            raise HarmonizationError(f"canonical entry {name!r} is not a mapping")
        defaults = {key: value for key, value in spec.items() if not isinstance(key, int)}
        rounds: dict[int, Mapping] = {}
        for round_number in SUPPORTED_ROUNDS:
            value = spec.get(round_number, _MISSING)
            if value is _MISSING:
                settings = dict(defaults)
            elif value is None:
                continue
            elif isinstance(value, dict):
                settings = {**defaults, **value}
            else:
                raise HarmonizationError(
                    f"canonical entry {name!r} round {round_number} must be a mapping or null"
                )
            variable = settings.get("var")
            if not isinstance(variable, str) or not variable:
                continue
            rounds[round_number] = Mapping(
                var=variable,
                decode_country=bool(settings.get("decode_country", False)),
                recode=_recode_map(settings.get("recode")),
            )
        result[str(name)] = rounds
    return result


def family_map() -> dict[str, dict[int, Mapping]]:
    config = _load("crosswalk/questions.yaml")
    section = config.get("families")
    if not isinstance(section, dict):
        raise HarmonizationError("questions.yaml has no families section")
    result: dict[str, dict[int, Mapping]] = {}
    for family, spec in section.items():
        if not isinstance(spec, dict):
            raise HarmonizationError(f"family {family!r} is not a mapping")
        rounds_raw = spec.get("rounds")
        if not isinstance(rounds_raw, dict):
            raise HarmonizationError(f"family {family!r} has no rounds mapping")
        rounds: dict[int, Mapping] = {}
        for key, value in rounds_raw.items():
            if isinstance(value, str):
                rounds[int(key)] = Mapping(var=value)
            elif isinstance(value, dict):
                variable = value.get("var")
                if not isinstance(variable, str) or not variable:
                    raise HarmonizationError(
                        f"family {family!r} round {key} has no var"
                    )
                rounds[int(key)] = Mapping(
                    var=variable, recode=_recode_map(value.get("recode"))
                )
            else:
                raise HarmonizationError(
                    f"family {family!r} round {key} must be a string or mapping"
                )
        result[str(family)] = rounds
    return result


def family_rounds(family: str) -> list[int]:
    rounds = family_map().get(family)
    if rounds is None:
        raise HarmonizationError(f"Unknown question family: {family}")
    return sorted(rounds)


def family_descriptions() -> dict[str, str]:
    config = _load("crosswalk/questions.yaml")
    section = config.get("families")
    if not isinstance(section, dict):
        raise HarmonizationError("questions.yaml has no families section")
    descriptions: dict[str, str] = {}
    for family, spec in section.items():
        description = spec.get("description") if isinstance(spec, dict) else None
        descriptions[str(family)] = str(description or "")
    return descriptions
