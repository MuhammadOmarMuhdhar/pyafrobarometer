#!/usr/bin/env python3
"""Build and validate the reviewed question concept crosswalk."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
import warnings
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from pyafrobarometer import metadata
from pyafrobarometer.errors import HarmonizationError
from pyafrobarometer.harmonize import schema

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "did",
    "do",
    "does",
    "for",
    "how",
    "in",
    "is",
    "many",
    "much",
    "of",
    "often",
    "or",
    "respondent",
    "the",
    "to",
    "you",
    "your",
}


@dataclass(frozen=True)
class Candidate:
    name: str
    description: str
    kind: str
    values: dict[int, str] | None
    rounds: dict[int, dict[str, Any]]
    exact: bool
    confidence: float


def _ascii(text: Any) -> str:
    return unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()


def normalize_label(text: Any) -> str:
    value = _ascii(text).lower().replace("’", "'")
    value = re.sub(r"^q\d+[a-z]?[\.\):\s-]+", "", value)
    value = re.sub(r"^\[[^\]]*\][\s:.-]*", "", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def normalize_value_label(text: Any) -> str:
    value = _ascii(text).lower().replace("’", "'")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def slugify(text: Any) -> str:
    words = [word for word in normalize_label(text).split() if word not in STOPWORDS]
    slug = "_".join(words)[:80].rstrip("_")
    return slug or "question"


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _parse_labels(raw: Any) -> dict[int, str]:
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


def _parse_missing(raw: Any) -> list[int]:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return []
    if not isinstance(raw, (list, tuple)):
        return []
    return [code for code in (_as_int(value) for value in raw) if code is not None]


def _recode_labels(
    labels: Mapping[int, str],
    missing: Iterable[int],
    recode: Mapping[int, int | None] | None = None,
) -> dict[int, str]:
    missing_set = set(missing)
    recoded: dict[int, str] = {}
    for code, label in labels.items():
        if code in missing_set:
            continue
        target: int | None = code
        if recode is not None and code in recode:
            target = recode[code]
        if target is None:
            continue
        recoded[target] = str(label)
    return recoded


def value_signature(
    labels: Mapping[int, str],
    missing: Iterable[int],
    recode: Mapping[int, int | None] | None = None,
) -> tuple[tuple[int, str], ...]:
    recoded = _recode_labels(labels, missing, recode)
    return tuple(
        sorted((code, normalize_value_label(label)) for code, label in recoded.items())
    )


def infer_values(
    rounds: Mapping[int, Mapping[int, str]],
    missing: Mapping[int, Iterable[int]],
    recodes: Mapping[int, Mapping[int, int | None]] | None = None,
) -> dict[int, str] | None:
    recoded: dict[int, dict[int, str]] = {}
    for round_number, labels in rounds.items():
        values = _recode_labels(
            labels,
            missing.get(round_number, ()),
            recodes.get(round_number) if recodes else None,
        )
        if values:
            recoded[round_number] = values
    if not recoded:
        return None
    code_sets = {frozenset(values) for values in recoded.values()}
    if len(code_sets) != 1:
        return None
    latest = max(recoded)
    return dict(recoded[latest])


def legacy_from_yaml(payload: Mapping[str, Any]) -> dict[str, dict[int, dict[str, Any]]]:
    section = payload.get("families")
    if not isinstance(section, dict):
        return {}
    result: dict[str, dict[int, dict[str, Any]]] = {}
    for family, spec in section.items():
        if not isinstance(spec, dict):
            continue
        rounds_raw = spec.get("rounds")
        if not isinstance(rounds_raw, dict):
            continue
        rounds: dict[int, dict[str, Any]] = {}
        for key, value in rounds_raw.items():
            round_number = _as_int(key)
            if round_number is None:
                continue
            if isinstance(value, str):
                var = value
                recode: dict[int, int | None] | None = None
            elif isinstance(value, dict):
                var = value.get("var")
                raw_recode = value.get("recode")
                recode = None
                if isinstance(raw_recode, dict):
                    recode = {
                        int(code): (None if target is None else int(target))
                        for code, target in raw_recode.items()
                    }
            else:
                continue
            if not isinstance(var, str) or not var:
                continue
            rounds[round_number] = {"var": var, "recode": recode}
        if rounds:
            result[str(family)] = rounds
    return result


def _missing_for(row: Mapping[str, Any], labels: dict[int, str], name: str) -> list[int]:
    declared = _parse_missing(row.get("missing_codes"))
    if declared:
        return declared
    meta = {
        "variable_value_labels": {name: labels},
        "missing_ranges": {},
        "missing_user_values": {},
    }
    return metadata.missing_codes(meta, name)


def _row_map(index: pd.DataFrame) -> dict[tuple[int, str], Mapping[str, Any]]:
    rows: dict[tuple[int, str], Mapping[str, Any]] = {}
    for row in index.to_dict("records"):
        if str(row.get("kind")) != "question":
            continue
        round_number = _as_int(row.get("round"))
        name = row.get("name")
        if round_number is None or not isinstance(name, str):
            continue
        rows[(round_number, name.casefold())] = row
    return rows


def _rounds_payload(
    rounds: Mapping[int, Mapping[str, Any]],
) -> dict[int, dict[str, Any]]:
    payload: dict[int, dict[str, Any]] = {}
    for round_number, entry in rounds.items():
        payload[round_number] = {
            "var": entry["var"],
            "label": entry.get("label", ""),
            "recode": dict(entry.get("recode") or {}),
            "missing": list(entry.get("missing") or []),
        }
    return payload


def _signatures(
    labels: Mapping[int, Mapping[int, str]],
    missing: Mapping[int, Iterable[int]],
    recodes: Mapping[int, Mapping[int, int | None]] | None,
) -> list[tuple[tuple[int, str], ...]]:
    return [
        value_signature(
            labels[round_number],
            missing.get(round_number, ()),
            recodes.get(round_number) if recodes else None,
        )
        for round_number in sorted(labels)
    ]


def _legacy_candidate(
    name: str,
    rounds: Mapping[int, Mapping[str, Any]],
    rows: Mapping[tuple[int, str], Mapping[str, Any]],
) -> Candidate:
    labels: dict[int, dict[int, str]] = {}
    missing: dict[int, list[int]] = {}
    recodes: dict[int, dict[int, int | None]] = {}
    payload_rounds: dict[int, dict[str, Any]] = {}
    for round_number, spec in rounds.items():
        row = rows.get((round_number, str(spec["var"]).casefold()))
        raw_labels = _parse_labels(row.get("value_labels")) if row else {}
        labels[round_number] = raw_labels
        missing[round_number] = (
            _missing_for(row, raw_labels, str(row.get("name"))) if row else []
        )
        if spec.get("recode"):
            recodes[round_number] = dict(spec["recode"])
        payload_rounds[round_number] = {
            "var": spec["var"],
            "label": str(row.get("label")) if row else "",
            "recode": dict(spec.get("recode") or {}),
            "missing": missing[round_number],
        }
    values = infer_values(labels, missing, recodes)
    signatures = _signatures(labels, missing, recodes)
    exact = bool(signatures) and len(set(signatures)) == 1 and all(signatures)
    description = payload_rounds[max(payload_rounds)]["label"] if payload_rounds else name
    return Candidate(
        name=name,
        description=description or name,
        kind="coded" if any(labels.values()) else "text",
        values=values,
        rounds=payload_rounds,
        exact=exact,
        confidence=100.0,
    )




def _match_label(label: str, target: Mapping[int, str]) -> int | None:
    normalized = normalize_value_label(label)
    for code, candidate in sorted(target.items()):
        if normalize_value_label(candidate) == normalized:
            return code
    try:
        from rapidfuzz import fuzz
    except ImportError:
        return None
    best_code: int | None = None
    best_score = 0.0
    for code, candidate in target.items():
        score = float(fuzz.WRatio(normalized, normalize_value_label(candidate)))
        if score > best_score:
            best_score = score
            best_code = code
    return best_code if best_score >= 88.0 else None


def infer_values_and_recodes(
    rounds: Mapping[int, Mapping[int, str]],
    missing: Mapping[int, Iterable[int]],
) -> tuple[dict[int, str] | None, dict[int, dict[int, int | None]] | None]:
    recoded: dict[int, dict[int, str]] = {}
    for round_number, labels in rounds.items():
        values = _recode_labels(labels, missing.get(round_number, ()), None)
        if values:
            recoded[round_number] = values
    if not recoded:
        return None, None
    latest = max(recoded)
    target = recoded[latest]
    recodes: dict[int, dict[int, int | None]] = {}
    for round_number, values in recoded.items():
        if round_number == latest:
            recodes[round_number] = {}
            continue
        mapping: dict[int, int | None] = {}
        mapped = 0
        for code, label in values.items():
            target_code = _match_label(label, target)
            mapping[code] = target_code
            if target_code is not None:
                mapped += 1
        if mapped == 0:
            return None, None
        recodes[round_number] = {
            code: target_code
            for code, target_code in mapping.items()
            if target_code != code
        }
    return dict(target), recodes


def _group_candidate(
    label: str,
    items: list[Mapping[str, Any]],
) -> Candidate:
    labels: dict[int, dict[int, str]] = {}
    missing: dict[int, list[int]] = {}
    payload_rounds: dict[int, dict[str, Any]] = {}
    for row in items:
        round_number = _as_int(row.get("round"))
        if round_number is None:
            continue
        name = str(row.get("name"))
        raw_labels = _parse_labels(row.get("value_labels"))
        labels[round_number] = raw_labels
        missing[round_number] = _missing_for(row, raw_labels, name)
        payload_rounds[round_number] = {
            "var": name,
            "label": str(row.get("label")),
            "recode": {},
            "missing": missing[round_number],
        }
    values, recodes = infer_values_and_recodes(labels, missing)
    if recodes is not None:
        for round_number, recode in recodes.items():
            payload_rounds[round_number]["recode"] = recode
    signatures = _signatures(labels, missing, recodes)
    identity = recodes is not None and all(not recode for recode in recodes.values())
    exact = (
        values is not None
        and identity
        and bool(signatures)
        and len(set(signatures)) == 1
        and all(signatures)
    )
    description = str(items[-1].get("label")) if items else label
    return Candidate(
        name=slugify(label),
        description=description,
        kind="coded" if any(labels.values()) else "text",
        values=values,
        rounds=payload_rounds,
        exact=exact,
        confidence=100.0 if exact else 90.0,
    )


def _same_values(left: Candidate, right: Candidate) -> bool:
    if left.values is None or right.values is None:
        return left.values is None and right.values is None
    return set(left.values) == set(right.values)


def _fuzzy_merge(candidates: list[Candidate], threshold: float) -> list[Candidate]:
    try:
        from rapidfuzz import fuzz
    except ImportError:
        warnings.warn(
            "rapidfuzz is not installed; skipping fuzzy question matching",
            UserWarning,
            stacklevel=2,
        )
        return candidates
    merged: list[Candidate] = []
    for candidate in candidates:
        match: Candidate | None = None
        for existing in merged:
            if existing.kind != candidate.kind or not _same_values(existing, candidate):
                continue
            score = float(
                fuzz.WRatio(
                    normalize_label(existing.description),
                    normalize_label(candidate.description),
                )
            )
            if score >= threshold:
                match = existing
                break
        if match is None:
            merged.append(candidate)
            continue
        rounds = dict(match.rounds)
        for round_number, entry in candidate.rounds.items():
            rounds.setdefault(round_number, entry)
        merged[merged.index(match)] = Candidate(
            name=match.name,
            description=match.description,
            kind=match.kind,
            values=match.values,
            rounds=rounds,
            exact=False,
            confidence=max(match.confidence, candidate.confidence),
        )
    return merged


def build_candidates(
    index: pd.DataFrame,
    legacy: Mapping[str, Mapping[int, Mapping[str, Any]]] | None = None,
    fuzzy_threshold: float | None = 90.0,
) -> list[Candidate]:
    rows = _row_map(index)
    canonical_vars = {
        str(row.get("name", "")).casefold()
        for row in index.to_dict("records")
        if str(row.get("kind")) == "canonical"
    }
    legacy_map = dict(legacy or {})
    used: set[tuple[int, str]] = set()
    candidates: list[Candidate] = []

    for name, rounds in sorted(legacy_map.items()):
        candidates.append(_legacy_candidate(name, rounds, rows))
        for round_number, spec in rounds.items():
            used.add((round_number, str(spec["var"]).casefold()))

    groups: dict[str, list[Mapping[str, Any]]] = {}
    for row in index.to_dict("records"):
        if str(row.get("kind")) != "question":
            continue
        round_number = _as_int(row.get("round"))
        name = row.get("name")
        if round_number is None or not isinstance(name, str):
            continue
        if (round_number, name.casefold()) in used:
            continue
        if name.casefold() in canonical_vars:
            continue
        groups.setdefault(normalize_label(row.get("label")), []).append(row)

    for label, items in sorted(groups.items()):
        rounds = [
            _as_int(item.get("round"))
            for item in items
            if _as_int(item.get("round")) is not None
        ]
        if not rounds or len(rounds) != len(set(rounds)):
            continue
        if len(set(rounds)) < 2:
            continue
        candidates.append(_group_candidate(label, items))

    if fuzzy_threshold is not None and len(candidates) > 1:
        legacy_names = set(legacy_map)
        legacy_candidates = [c for c in candidates if c.name in legacy_names]
        grouped_candidates = [c for c in candidates if c.name not in legacy_names]
        candidates = legacy_candidates + _fuzzy_merge(grouped_candidates, fuzzy_threshold)

    seen: dict[str, int] = {}
    result: list[Candidate] = []
    for candidate in sorted(candidates, key=lambda item: item.name):
        base = candidate.name
        count = seen.get(base, 0) + 1
        seen[base] = count
        name = base if count == 1 else f"{base}_{count}"
        result.append(
            Candidate(
                name=name,
                description=candidate.description,
                kind=candidate.kind,
                values=candidate.values,
                rounds=candidate.rounds,
                exact=candidate.exact,
                confidence=candidate.confidence,
            )
        )
    return result


DEFAULT_INDEX = Path("src/pyafrobarometer/metadata_index.json")
DEFAULT_QUESTIONS = Path("src/pyafrobarometer/crosswalk/questions.yaml")
DEFAULT_PROPOSED = Path("build/questions.proposed.yaml")


def load_index(path: Path) -> pd.DataFrame:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    variables = payload.get("variables") if isinstance(payload, dict) else None
    if not isinstance(variables, list):
        raise TypeError(f"{path} has no variables list")
    return pd.DataFrame(variables)


def load_truth(path: Path) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        return {"version": 1, "questions": {}}
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise TypeError(f"{path} is not a YAML mapping")
    questions = payload.get("questions")
    if not isinstance(questions, dict):
        raise TypeError(f"{path} is not in questions format; run --bootstrap")
    payload["version"] = int(payload.get("version", 1))
    return payload


def write_yaml(path: Path, payload: Mapping[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(dict(payload), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def _sorted_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    questions = payload.get("questions")
    if not isinstance(questions, dict):
        questions = {}
    return {
        "version": int(payload.get("version", 1)),
        "questions": {name: questions[name] for name in sorted(questions)},
    }


def candidate_payload(candidate: Candidate) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "description": candidate.description,
        "kind": candidate.kind,
    }
    if candidate.values is not None:
        payload["values"] = {
            int(code): str(label) for code, label in sorted(candidate.values.items())
        }
    rounds: dict[int, dict[str, Any]] = {}
    for round_number, entry in sorted(candidate.rounds.items()):
        round_payload: dict[str, Any] = {
            "var": entry["var"],
            "label": entry.get("label", ""),
        }
        recode = entry.get("recode") or {}
        if recode:
            round_payload["recode"] = {
                int(code): target for code, target in sorted(recode.items())
            }
        missing = entry.get("missing") or []
        if missing:
            round_payload["missing"] = sorted(int(code) for code in missing)
        rounds[int(round_number)] = round_payload
    payload["rounds"] = rounds
    return payload


def merge_candidate(payload: dict[str, Any], candidate: Candidate) -> bool:
    questions = payload.setdefault("questions", {})
    if not isinstance(questions, dict):
        raise TypeError("questions must be a mapping")
    existing = questions.get(candidate.name)
    serialized = candidate_payload(candidate)
    if existing is None:
        questions[candidate.name] = serialized
        return True
    if not isinstance(existing, dict):
        return False
    rounds = existing.setdefault("rounds", {})
    if not isinstance(rounds, dict):
        return False
    changed = False
    for round_number, entry in serialized["rounds"].items():
        if round_number not in rounds:
            rounds[round_number] = entry
            changed = True
    return changed


def unassigned_repeated_labels(
    index: pd.DataFrame, truth: Mapping[str, Any]
) -> list[str]:
    assigned: set[tuple[int, str]] = set()
    questions = truth.get("questions")
    if isinstance(questions, dict):
        for spec in questions.values():
            if not isinstance(spec, dict):
                continue
            rounds = spec.get("rounds")
            if not isinstance(rounds, dict):
                continue
            for round_number, entry in rounds.items():
                if not isinstance(entry, dict) or entry.get("exclude"):
                    continue
                var = entry.get("var")
                parsed = _as_int(round_number)
                if parsed is not None and isinstance(var, str):
                    assigned.add((parsed, var.casefold()))

    canonical_vars = {
        str(row.get("name", "")).casefold()
        for row in index.to_dict("records")
        if str(row.get("kind")) == "canonical"
    }
    groups: dict[str, list[tuple[int, str]]] = {}
    for row in index.to_dict("records"):
        if str(row.get("kind")) != "question":
            continue
        round_number = _as_int(row.get("round"))
        name = row.get("name")
        if round_number is None or not isinstance(name, str):
            continue
        if name.casefold() in canonical_vars:
            continue
        groups.setdefault(normalize_label(row.get("label")), []).append(
            (round_number, name)
        )

    unassigned: list[str] = []
    for label, items in groups.items():
        rounds = {round_number for round_number, _ in items}
        if len(rounds) < 2:
            continue
        if not any(
            (round_number, name.casefold()) in assigned
            for round_number, name in items
        ):
            unassigned.append(label)
    return sorted(unassigned)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--proposed", type=Path, default=DEFAULT_PROPOSED)
    parser.add_argument("--legacy", type=Path)
    parser.add_argument("--bootstrap", action="store_true")
    parser.add_argument("--propose", action="store_true")
    parser.add_argument("--accept-exact", action="store_true")
    parser.add_argument("--accept", action="append", default=[])
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--strict-coverage", action="store_true")
    args = parser.parse_args(argv)

    try:
        index = load_index(args.index)
        legacy = (
            legacy_from_yaml(yaml.safe_load(args.legacy.read_text(encoding="utf-8")) or {})
            if args.legacy
            else {}
        )
        candidates = build_candidates(index, legacy)
    except (OSError, ValueError, TypeError, json.JSONDecodeError, yaml.YAMLError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    legacy_names = set(legacy)
    modes = (
        args.bootstrap,
        args.propose,
        args.accept_exact,
        bool(args.accept),
        args.validate,
    )
    if not any(modes):
        parser.print_help()
        return 1

    if args.bootstrap:
        truth: dict[str, Any] = {"version": 1, "questions": {}}
        proposed: dict[str, Any] = {"version": 1, "questions": {}}
        for candidate in candidates:
            if candidate.name in legacy_names:
                if candidate.kind == "coded" and candidate.values is None:
                    print(
                        f"error: legacy concept {candidate.name} has no inferable values",
                        file=sys.stderr,
                    )
                    return 1
                merge_candidate(truth, candidate)
            elif candidate.exact and (
                candidate.kind == "text" or candidate.values is not None
            ):
                merge_candidate(truth, candidate)
            else:
                merge_candidate(proposed, candidate)
        write_yaml(args.questions, _sorted_payload(truth))
        write_yaml(args.proposed, _sorted_payload(proposed))

    if args.propose:
        try:
            truth = load_truth(args.questions)
        except (OSError, ValueError, TypeError, yaml.YAMLError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        proposed = {"version": 1, "questions": {}}
        for candidate in candidates:
            existing = truth["questions"].get(candidate.name)
            if existing is None:
                merge_candidate(proposed, candidate)
                continue
            rounds = existing.get("rounds") if isinstance(existing, dict) else {}
            if not isinstance(rounds, dict) or any(
                round_number not in rounds for round_number in candidate.rounds
            ):
                merge_candidate(proposed, candidate)
        write_yaml(args.proposed, _sorted_payload(proposed))

    if args.accept_exact or args.accept:
        try:
            truth = load_truth(args.questions)
        except (OSError, ValueError, TypeError, yaml.YAMLError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        accepted = set(args.accept)
        known = {candidate.name for candidate in candidates} | set(
            truth.get("questions", {})
        )
        unknown = sorted(accepted - known)
        if unknown:
            print("error: unknown concepts: " + ", ".join(unknown), file=sys.stderr)
            return 1
        for candidate in candidates:
            if args.accept_exact and not (
                candidate.exact or candidate.name in legacy_names
            ):
                continue
            if accepted and candidate.name not in accepted:
                continue
            if candidate.kind == "coded" and candidate.values is None and not accepted:
                continue
            merge_candidate(truth, candidate)
        write_yaml(args.questions, _sorted_payload(truth))

    if args.validate:
        try:
            truth = load_truth(args.questions)
            questions = schema.parse_questions(truth)
        except (
            OSError,
            ValueError,
            TypeError,
            yaml.YAMLError,
            HarmonizationError,
        ) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        problems = schema.validate_questions(questions, index)
        unassigned = (
            unassigned_repeated_labels(index, truth) if args.strict_coverage else []
        )
        for problem in problems:
            print(problem)
        if unassigned:
            print("unassigned repeated labels: " + ", ".join(unassigned))
        return 1 if problems or (args.strict_coverage and unassigned) else 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
