"""Crosswalk loading for canonical variables and question families."""

from __future__ import annotations

import importlib.resources
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import yaml

from pyafrobarometer.errors import HarmonizationError
from pyafrobarometer.harmonize.schema import QuestionDefinition, parse_questions

SUPPORTED_ROUNDS = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
LEGACY_QUESTIONS = (
    "trust_president",
    "trust_parliament",
    "trust_police",
    "trust_courts",
    "trust_electoral_commission",
    "trust_army",
    "trust_ruling_party",
    "trust_opposition",
    "support_democracy",
    "reject_one_party_rule",
    "reject_military_rule",
    "reject_one_man_rule",
    "satisfaction_democracy",
    "corruption_president",
    "corruption_police",
    "corruption_judges",
    "bribe_police",
    "radio_news",
    "television_news",
    "newspaper_news",
    "internet_news",
    "social_media_news",
    "internet_use",
    "econ_country_present",
    "econ_personal_present",
    "lived_poverty_food",
    "lived_poverty_water",
    "lived_poverty_medical",
    "lived_poverty_fuel",
    "free_to_say",
    "felt_unsafe_walking",
    "neighbours_homosexuals",
)

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


@lru_cache(maxsize=1)
def _question_map_cached() -> dict[str, QuestionDefinition]:
    config = _load("crosswalk/questions.yaml")
    if "questions" not in config:
        raise HarmonizationError(
            "questions.yaml has no questions section; run the migration generator"
        )
    return parse_questions(config)


def question_map() -> dict[str, QuestionDefinition]:
    return dict(_question_map_cached())


def family_map() -> dict[str, dict[int, Mapping]]:
    result: dict[str, dict[int, Mapping]] = {}
    for name, question in question_map().items():
        rounds: dict[int, Mapping] = {}
        for round_number, entry in question.rounds.items():
            if entry.exclude or entry.var is None:
                continue
            recode = {
                code: target
                for code, target in entry.recode.items()
                if target is not None
            }
            rounds[round_number] = Mapping(var=entry.var, recode=recode or None)
        if rounds:
            result[name] = rounds
    return result


def family_rounds(family: str) -> list[int]:
    rounds = family_map().get(family)
    if rounds is None:
        raise HarmonizationError(f"Unknown question family: {family}")
    return sorted(rounds)


def question_descriptions() -> dict[str, str]:
    return {
        name: question.description
        for name, question in question_map().items()
    }


def family_descriptions() -> dict[str, str]:
    return question_descriptions()
