"""High-level public API composing catalog, cache, I/O, and harmonization."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import warnings
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, cast
from urllib.parse import urlparse

import pandas as pd

from pyafrobarometer import cache, catalog, fetch, io, metadata, search
from pyafrobarometer.catalog import CatalogEntry, resolve_catalog
from pyafrobarometer.codebook import extract_text as extract_pdf_text
from pyafrobarometer.codebook import get_codebook
from pyafrobarometer.dataset import Dataset, Provenance
from pyafrobarometer.errors import (
    AfrobarometerError,
    HarmonizationError,
    NotFoundError,
)
from pyafrobarometer.harmonize import canonical as harmonize
from pyafrobarometer.harmonize.crosswalk import (
    LEGACY_QUESTIONS,
    canonical_map,
    family_descriptions,
    family_map,
    question_map,
)
from pyafrobarometer.harmonize.panel import concat_frames
from pyafrobarometer.harmonize.schema import QuestionDefinition, resolve_column
from pyafrobarometer.names import normalize_country

ROUND_COLUMNS = ["round", "year", "countries", "data_url", "codebook_url", "language"]


def _round_list(rounds: Any) -> list[int] | None:
    if rounds is None:
        return None
    if isinstance(rounds, int) and not isinstance(rounds, bool):
        return [rounds]
    return [int(round_number) for round_number in rounds]


def _string_list(values: Any) -> list[str] | None:
    if values is None:
        return None
    if isinstance(values, str):
        return [values]
    return [str(value) for value in values]


def _source_list(source: Any) -> list[Any] | None:
    if source is None:
        return None
    if isinstance(source, (str, Path)):
        return [source]
    return list(source)


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _is_data_file(url: str) -> bool:
    return urlparse(url).path.lower().endswith((".sav", ".sav.zip", ".dta"))


def _cached_file(url: str) -> Path | None:
    state = cache.read_state()
    files = state.get("files")
    if not isinstance(files, dict):
        return None
    record = files.get(url)
    if not isinstance(record, dict):
        return None
    raw = record.get("path")
    if not isinstance(raw, str):
        return None
    path = Path(raw)
    if not path.exists():
        return None
    expected = record.get("size")
    if isinstance(expected, int) and path.stat().st_size != expected:
        return None
    return path


def _remember_file(
    url: str,
    path: Path,
    *,
    sha256: str,
    round_number: int | None,
    archive: Path | None = None,
    extract_dir: Path | None = None,
) -> None:
    record: dict[str, Any] = {
        "path": str(path),
        "sha256": sha256,
        "size": path.stat().st_size,
        "round": round_number,
    }
    if archive is not None:
        record["archive"] = str(archive)
    if extract_dir is not None:
        record["extract_dir"] = str(extract_dir)

    def update(state: dict[str, Any]) -> None:
        files = state.get("files")
        if not isinstance(files, dict):
            files = {}
        files[url] = record
        state["files"] = files

    cache.mutate_state(update)


def _extract_archive(url: str, dest: Path, digest: str) -> tuple[Path, Path]:
    extract_dir = dest.parent / f"extracted-{digest}"
    with cache.url_lock(url + "#extract"):
        if extract_dir.exists():
            existing = sorted(extract_dir.rglob("*.sav"))
            if existing:
                return existing[0], extract_dir
        return io.safe_extract_sav(dest, extract_dir), extract_dir


def _download_url(url: str) -> Path:
    cached = _cached_file(url)
    if cached is not None:
        return cached
    filename = PurePosixPath(urlparse(url).path).name or "download"
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
    dest = cache.cache_file(f"files/{digest}-{filename}")
    result = fetch.download(url, dest)
    path = dest
    archive: Path | None = None
    extract_dir: Path | None = None
    if filename.lower().endswith(".zip"):
        archive = dest
        path, extract_dir = _extract_archive(url, dest, digest)
    _remember_file(
        url,
        path,
        sha256=result.sha256,
        round_number=None,
        archive=archive,
        extract_dir=extract_dir,
    )
    return path


def _source_path(item: Any) -> Path:
    if isinstance(item, Path):
        return item
    text = str(item)
    if text.lower().startswith(("http://", "https://")):
        return _download_url(text)
    return Path(text)


def _download_entry(entry: CatalogEntry) -> Path:
    if not _is_data_file(entry.data_url):
        html = fetch.fetch_text(entry.page_url)
        data_url, codebook_url = catalog.extract_resource_links(html, entry.page_url)
        if data_url is None:
            if catalog.has_csv_link(html, entry.page_url):
                raise NotFoundError(
                    f"Round {entry.round} only offers CSV data at {entry.page_url}; "
                    "CSV is not supported in v1 (SAV or DTA is required)"
                )
            raise NotFoundError(
                f"No downloadable data file found for round {entry.round} at {entry.page_url}"
            )
        entry = replace(
            entry,
            data_url=data_url,
            codebook_url=codebook_url or entry.codebook_url,
            filename=PurePosixPath(urlparse(data_url).path).name,
        )
    cached = _cached_file(entry.data_url)
    if cached is not None:
        return cached
    filename = entry.filename or PurePosixPath(urlparse(entry.data_url).path).name
    digest = hashlib.sha256(entry.data_url.encode("utf-8")).hexdigest()
    dest = cache.cache_file(f"files/{digest}-{filename}")
    result = fetch.download(entry.data_url, dest)
    path = dest
    archive = None
    extract_dir = None
    if filename.lower().endswith(".zip"):
        archive = dest
        path, extract_dir = _extract_archive(entry.data_url, dest, digest)
    _remember_file(
        entry.data_url,
        path,
        sha256=result.sha256,
        round_number=entry.round,
        archive=archive,
        extract_dir=extract_dir,
    )
    return path


def _country_values(frame: pd.DataFrame, meta: dict[str, Any]) -> pd.Series | None:
    for name in ("country", "COUNTRY", "COUNTRY_ALPHA"):
        actual = name if name in frame.columns else resolve_column(name, frame.columns)
        if actual is None:
            continue
        if actual.casefold() == "country_alpha":
            return frame[actual]
        labels = metadata.value_labels(meta, actual)
        if labels:
            return metadata.decode_column(frame[actual], labels)
        return frame[actual]
    return None


def _unique_countries(frame: pd.DataFrame, meta: dict[str, Any]) -> list[str]:
    keys = _country_values(frame, meta)
    if keys is None:
        return []
    values = keys.dropna().astype(str)
    return [str(value) for value in pd.unique(values)]


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _metadata_for(path: Path, round_number: int | None) -> dict[str, Any]:
    if round_number is None:
        return io.read_metadata(path)
    digest = _file_sha256(path)
    cache_path = cache.cache_file(f"metadata/round-{round_number}.json")
    if cache_path.exists():
        try:
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = None
        if (
            isinstance(payload, dict)
            and payload.get("sha256") == digest
            and isinstance(payload.get("meta"), dict)
        ):
            return cast(dict[str, Any], payload["meta"])
    meta = io.read_metadata(path)
    try:
        fd, tmp_name = tempfile.mkstemp(
            dir=cache_path.parent, prefix=".meta-", suffix=".json"
        )
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump({"sha256": digest, "meta": meta}, handle, default=str)
        os.replace(tmp_name, cache_path)
    except (OSError, TypeError):
        pass
    return meta


def _select_usecols(
    meta: dict[str, Any],
    *,
    round_number: int | None,
    variables: list[str] | None,
    harmonize_requested: bool,
) -> list[str] | None:
    names = list(meta.get("column_names") or [])
    if not harmonize_requested and variables is None:
        return None
    needed: set[str] = set()
    for name in ("country", "COUNTRY", "COUNTRY_ALPHA"):
        actual = name if name in names else resolve_column(name, names)
        if actual is not None:
            needed.add(actual)
    if harmonize_requested and round_number is not None:
        for rounds in canonical_map().values():
            spec = rounds.get(round_number)
            if spec is not None:
                actual = resolve_column(spec.var, names)
                if actual is not None:
                    needed.add(actual)
        actual_within = resolve_column("withinwt_hh", names)
        if actual_within is not None:
            needed.add(actual_within)
        questions = question_map()
        selected = (
            list(LEGACY_QUESTIONS)
            if variables is None
            else [name for name in variables if name in questions]
        )
        for name in selected:
            entry = questions[name].rounds.get(round_number)
            if entry is None or entry.exclude or entry.var is None:
                continue
            actual = resolve_column(entry.var, names)
            if actual is not None:
                needed.add(actual)
        if variables is not None:
            known = set(questions) | set(canonical_map())
            for variable in variables:
                if variable in known:
                    continue
                actual = resolve_column(variable, names)
                if actual is not None:
                    needed.add(actual)
    elif variables is not None:
        for variable in variables:
            actual = resolve_column(variable, names)
            if actual is not None:
                needed.add(actual)
    return sorted(needed) or None


def _load_one(
    path: Path,
    *,
    round_number: int | None,
    variables: list[str] | None,
    countries: list[str] | None,
    harmonize_requested: bool,
    strict: bool,
) -> tuple[pd.DataFrame, dict[str, Any], dict[str, str], list[str]]:
    meta = _metadata_for(path, round_number)
    usecols = _select_usecols(
        meta,
        round_number=round_number,
        variables=variables,
        harmonize_requested=harmonize_requested,
    )
    frame, _ = io.read_frame(path, usecols=usecols)

    if countries:
        keys = _country_values(frame, meta)
        if keys is None:
            raise HarmonizationError(
                "No country column is available to filter; load with harmonize=True"
            )
        wanted = {normalize_country(name) for name in countries}
        normalized = keys.map(
            lambda value: normalize_country(value) if pd.notna(value) else ""
        )
        frame = frame[normalized.isin(wanted)]
        if frame.empty:
            raise NotFoundError(
                f"No data for {', '.join(countries)} in round {round_number}"
            )
    all_countries = _unique_countries(frame, meta)

    source_map: dict[str, str] = {}
    if harmonize_requested:
        if round_number is None:
            raise HarmonizationError(
                "rounds= is required to harmonize data loaded from a local source"
            )
        frame, canonical_sources = harmonize.apply_canonical(
            frame, round_number=round_number, meta=meta
        )
        source_map.update(canonical_sources)
        questions = question_map()
        known_canonical = set(canonical_map())
        if variables is None:
            requested_questions = [
                name
                for name in LEGACY_QUESTIONS
                if name in questions
                and round_number in questions[name].rounds
                and not questions[name].rounds[round_number].exclude
                and resolve_column(
                    questions[name].rounds[round_number].var or "", frame.columns
                )
                is not None
            ]
        else:
            unknown = [
                name
                for name in variables
                if name not in questions
                and name not in known_canonical
                and resolve_column(name, frame.columns) is None
            ]
            missing_canonical = [
                name
                for name in variables
                if name in known_canonical and name not in source_map
            ]
            if unknown or missing_canonical:
                message = (
                    "Requested harmonized variables are unavailable: "
                    + ", ".join(unknown + missing_canonical)
                )
                if strict:
                    raise HarmonizationError(message)
                warnings.warn(message, UserWarning, stacklevel=3)
            requested_questions = [name for name in variables if name in questions]
        frame, question_sources = harmonize.apply_questions(
            frame,
            round_number=round_number,
            questions=requested_questions,
            strict=strict,
        )
        source_map.update(question_sources)
    elif variables is not None:
        missing = [name for name in variables if name not in frame.columns]
        if missing:
            message = "Requested variables are unavailable: " + ", ".join(missing)
            if strict:
                raise HarmonizationError(message)
            warnings.warn(message, UserWarning, stacklevel=3)
        existing = [name for name in variables if name in frame.columns]
        frame = frame[existing]

    frame["round"] = round_number
    frame["year"] = pd.NA
    return frame, meta, source_map, all_countries


def _merge_meta(metas: list[dict[str, Any]]) -> dict[str, Any]:
    if not metas:
        return {}
    merged: dict[str, Any] = dict(metas[0])
    for meta in metas[1:]:
        for key in (
            "variable_value_labels",
            "missing_ranges",
            "missing_user_values",
            "column_names_to_labels",
        ):
            existing = merged.get(key)
            incoming = meta.get(key)
            if isinstance(existing, dict) and isinstance(incoming, dict):
                merged[key] = {**existing, **incoming}
        names = list(merged.get("column_names") or [])
        for name in meta.get("column_names") or []:
            if name not in names:
                names.append(name)
        merged["column_names"] = names
    return merged


def _concept_missing(question: QuestionDefinition) -> list[int]:
    return sorted(
        {
            code
            for entry in question.rounds.values()
            if not entry.exclude
            for code in entry.missing
        }
    )


def _build_variables(
    meta: dict[str, Any],
    source_map: dict[str, str],
    round_source_map: dict[int, dict[str, str]] | None = None,
) -> pd.DataFrame:
    variables = metadata.variable_info(meta)
    variables["source_var"] = variables["name"]
    variables["source_vars"] = pd.Series(
        [{} for _ in range(len(variables))],
        dtype=object,
        index=variables.index,
    )
    labels_by_name = dict(zip(variables["name"], variables["label"], strict=False))
    descriptions = family_descriptions()
    questions = question_map()
    round_sources = round_source_map or {}
    for output, source in source_map.items():
        question = questions.get(output)
        source_vars = {
            round_number: mapping[output]
            for round_number, mapping in sorted(round_sources.items())
            if output in mapping
        }
        mask = variables["name"] == output
        if bool(mask.any()):
            index = variables.index[mask][0]
            variables.at[index, "source_var"] = source
            variables.at[index, "source_vars"] = cast(Any, source_vars)
            continue
        if question is not None:
            row = {
                "name": output,
                "label": question.description,
                "value_labels": dict(question.values),
                "missing_codes": _concept_missing(question),
                "source_var": (
                    source_vars[min(source_vars)] if source_vars else source
                ),
                "source_vars": source_vars,
            }
        else:
            row = {
                "name": output,
                "label": labels_by_name.get(source, descriptions.get(output, output)),
                "value_labels": metadata.value_labels(meta, source),
                "missing_codes": metadata.missing_codes(meta, source),
                "source_var": source,
                "source_vars": source_vars,
            }
        variables = pd.concat([variables, pd.DataFrame([row])], ignore_index=True)
    return variables


def select_entries(
    entries: list[CatalogEntry] | tuple[CatalogEntry, ...],
    *,
    rounds: Any,
    countries: Any = None,
) -> list[CatalogEntry]:
    round_list = _round_list(rounds) or []
    country_list = _string_list(countries) or []
    selected: list[CatalogEntry] = []
    for round_number in round_list:
        candidates = [entry for entry in entries if entry.round == round_number]
        if not candidates:
            raise NotFoundError(f"No data is available for round {round_number}")
        merged = next(
            (entry for entry in candidates if entry.kind == "merged"), None
        )
        if country_list:
            by_country = {
                normalize_country(entry.country): entry
                for entry in candidates
                if entry.kind == "country" and entry.country
            }
            if all(normalize_country(name) in by_country for name in country_list):
                selected.extend(
                    by_country[normalize_country(name)] for name in country_list
                )
            elif merged is not None:
                selected.append(merged)
            else:
                raise NotFoundError(
                    f"No country data is available for round {round_number}"
                )
        elif merged is not None:
            selected.append(merged)
        else:
            selected.append(candidates[0])
    return selected


def rounds(refresh: bool = False) -> pd.DataFrame:
    entries = [
        entry for entry in resolve_catalog(refresh=refresh) if entry.kind == "merged"
    ]
    rows = [
        {
            "round": entry.round,
            "year": entry.year,
            "countries": entry.countries_count,
            "data_url": entry.data_url,
            "codebook_url": entry.codebook_url,
            "language": entry.language,
        }
        for entry in entries
    ]
    frame = pd.DataFrame(rows, columns=ROUND_COLUMNS)
    return cast(pd.DataFrame, frame.sort_values(["round", "language"]).reset_index(drop=True))


def countries(round: int | None = None, *, refresh: bool = False) -> list[str]:
    index = search.load_index()
    if round is not None and not index.empty:
        index = index[index["round"].astype(int) == round]
    names: list[str] = []
    for _, row in index.iterrows():
        if str(row["name"]).casefold() not in {"country", "country_alpha"}:
            continue
        raw = row["value_labels"]
        if not isinstance(raw, str):
            continue
        try:
            mapping = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(mapping, dict):
            continue
        for value in mapping.values():
            text = str(value)
            if text not in names:
                names.append(text)
    if names:
        return names
    entries = resolve_catalog(refresh=refresh)
    fallback = sorted(
        {
            entry.country
            for entry in entries
            if entry.country and (round is None or entry.round == round)
        }
    )
    if fallback:
        return fallback
    raise NotFoundError(
        "Could not determine countries from the metadata index or catalog"
    )


def questions() -> pd.DataFrame:
    rows = [
        {
            "name": name,
            "description": spec.description,
            "kind": spec.kind,
            "rounds": sorted(
                round_number
                for round_number, entry in spec.rounds.items()
                if not entry.exclude
            ),
            "variables": {
                round_number: entry.var
                for round_number, entry in sorted(spec.rounds.items())
                if not entry.exclude and entry.var is not None
            },
            "values": spec.values.copy(),
        }
        for name, spec in sorted(question_map().items())
    ]
    return cast(
        pd.DataFrame,
        pd.DataFrame(
            rows,
            columns=["name", "description", "kind", "rounds", "variables", "values"],
        ),
    )


def question(name: str) -> pd.DataFrame:
    spec = question_map().get(name)
    if spec is None:
        raise HarmonizationError(f"Unknown question: {name}")
    rows = [
        {
            "round": round_number,
            "var": entry.var,
            "label": entry.label,
            "recode": dict(entry.recode),
            "missing": list(entry.missing),
            "excluded": entry.exclude,
            "reason": entry.reason,
        }
        for round_number, entry in sorted(spec.rounds.items())
    ]
    return cast(
        pd.DataFrame,
        pd.DataFrame(
            rows,
            columns=[
                "round",
                "var",
                "label",
                "recode",
                "missing",
                "excluded",
                "reason",
            ],
        ),
    )


def families() -> pd.DataFrame:
    warnings.warn(
        "families() is deprecated; use questions() instead",
        DeprecationWarning,
        stacklevel=2,
    )
    mapping = family_map()
    descriptions = family_descriptions()
    rows = [
        {
            "family": family,
            "description": descriptions.get(family, ""),
            "rounds": sorted(mapping[family]),
            "variables": {
                round_number: item.var
                for round_number, item in sorted(mapping[family].items())
            },
        }
        for family in LEGACY_QUESTIONS
        if family in mapping
    ]
    return cast(
        pd.DataFrame,
        pd.DataFrame(rows, columns=["family", "description", "rounds", "variables"]),
    )


def load(
    rounds: Any = None,
    countries: Any = None,
    variables: Any = None,
    labels: bool = False,
    normalize_missing: bool = False,
    harmonize: bool = False,
    language: str = "en",
    source: Any = None,
    refresh: bool = False,
    strict: bool = True,
) -> Dataset:
    round_list = _round_list(rounds)
    country_list = _string_list(countries)
    variable_list = _string_list(variables)
    source_list = _source_list(source)

    plans: list[tuple[Path, int | None, CatalogEntry | None]] = []
    if source_list is None:
        entries = resolve_catalog(refresh=refresh)
        if round_list is None:
            round_list = sorted(
                {entry.round for entry in entries if entry.kind == "merged"}
            )
        candidates = [
            entry
            for entry in entries
            if entry.round in set(round_list) and entry.language == language
        ]
        for entry in select_entries(candidates, rounds=round_list):
            plans.append((_download_entry(entry), entry.round, entry))
    else:
        for index, item in enumerate(source_list):
            if round_list is not None and index < len(round_list):
                round_number = round_list[index]
            elif round_list is not None and len(round_list) == 1:
                round_number = round_list[0]
            else:
                round_number = None
            if harmonize and round_number is None:
                raise HarmonizationError(
                    "rounds= is required to harmonize data loaded from a local source"
                )
            plans.append((_source_path(item), round_number, None))

    frames: list[pd.DataFrame] = []
    metas: list[dict[str, Any]] = []
    source_urls: list[str] = []
    rounds_used: list[int] = []
    years: list[int] = []
    country_values: list[str] = []
    source_map: dict[str, str] = {}
    codebook_url: str | None = None
    round_meta: dict[int, dict[str, Any]] = {}
    round_source_map: dict[int, dict[str, str]] = {}

    for path, round_number, catalog_entry in plans:
        frame, meta, applied, all_countries = _load_one(
            path,
            round_number=round_number,
            variables=variable_list,
            countries=country_list,
            harmonize_requested=harmonize,
            strict=strict,
        )
        if catalog_entry is not None and catalog_entry.year is not None:
            frame["year"] = catalog_entry.year
            years.append(catalog_entry.year)
        frames.append(frame)
        metas.append(meta)
        source_map.update(applied)
        if round_number is not None:
            round_meta[round_number] = meta
            round_source_map[round_number] = applied
        source_urls.append(
            catalog_entry.data_url if catalog_entry is not None else str(path)
        )
        if catalog_entry is not None and codebook_url is None:
            codebook_url = catalog_entry.codebook_url
        if round_number is not None:
            rounds_used.append(round_number)
        country_values.extend(all_countries)

    if not frames:
        raise NotFoundError("No data matched the requested rounds and countries")
    combined = frames[0] if len(frames) == 1 else pd.concat(frames, ignore_index=True)
    meta = _merge_meta(metas)
    variable_frame = _build_variables(meta, source_map, round_source_map)
    provenance = Provenance(
        source_urls=tuple(source_urls),
        retrieved_at=_timestamp(),
        rounds=tuple(rounds_used),
        countries=tuple(dict.fromkeys(country_values)),
        language=language,
        years=tuple(years),
        codebook_url=codebook_url,
    )
    dataset = Dataset(
        combined,
        variables=variable_frame,
        provenance=provenance,
        meta=meta,
        source_map=source_map,
        harmonized=harmonize,
        round_meta=round_meta,
        round_source_map=round_source_map,
    )
    if labels or normalize_missing:
        converted = dataset.to_pandas(
            labels=labels, normalize_missing=normalize_missing
        )
        dataset = Dataset(
            converted,
            variables=variable_frame,
            provenance=provenance,
            meta=meta,
            source_map=source_map,
            harmonized=harmonize,
            round_meta=round_meta,
            round_source_map=round_source_map,
        )
    return dataset


def search_variables(
    query: str,
    rounds: Any = None,
    limit: int = 20,
    fuzzy: bool = True,
) -> pd.DataFrame:
    return search.search_variables(
        query, rounds=rounds, limit=limit, fuzzy=fuzzy
    )


def codebook(
    round: int,
    country: str | None = None,
    extract_text: bool = False,
) -> Path:
    entries = resolve_catalog()
    candidates = [
        entry
        for entry in entries
        if entry.round == round
        and (country is None or (entry.country or "").casefold() == country.casefold())
        and entry.language == "en"
    ]
    if not candidates:
        raise NotFoundError(f"No codebook is available for round {round}")
    entry = next(
        (item for item in candidates if item.kind == "merged"), candidates[0]
    )
    path = get_codebook(entry)
    if not extract_text:
        return path
    text_path = path.with_suffix(path.suffix + ".txt")
    text_path.write_text(extract_pdf_text(path), encoding="utf-8")
    return text_path


def panel(
    rounds: Any,
    variables: Any,
    countries: Any = None,
    labels: bool = False,
    strict: bool = True,
) -> Dataset:
    round_list = _round_list(rounds) or []
    variable_list = _string_list(variables) or []
    frames: list[pd.DataFrame] = []
    datasets: list[Dataset] = []
    for round_number in round_list:
        dataset = load(
            rounds=round_number,
            countries=countries,
            variables=variable_list,
            labels=labels,
            harmonize=True,
            strict=strict,
        )
        frames.append(dataset.to_pandas(labels=labels))
        datasets.append(dataset)
    combined = concat_frames(frames, variables=variable_list)
    provenances = [dataset.provenance for dataset in datasets]
    round_meta: dict[int, dict[str, Any]] = {}
    round_source_map: dict[int, dict[str, str]] = {}
    variable_frames: list[pd.DataFrame] = []
    for dataset in datasets:
        round_meta.update(dataset.round_meta)
        round_source_map.update(dataset.round_source_map)
        variable_frames.append(dataset.variables())
    if variable_frames:
        variables_frame = pd.concat(variable_frames, ignore_index=True)
        if variable_list:
            variables_frame = variables_frame[
                variables_frame["name"].isin(variable_list)
            ]
        variables_frame = variables_frame.drop_duplicates(
            subset=["name"]
        ).reset_index(drop=True)
    else:
        variables_frame = pd.DataFrame(
            columns=[
                "name",
                "label",
                "value_labels",
                "missing_codes",
                "source_var",
                "source_vars",
            ]
        )
    provenance = Provenance(
        source_urls=tuple(
            url for item in provenances for url in item.source_urls
        ),
        retrieved_at=_timestamp(),
        rounds=tuple(round_list),
        countries=tuple(_string_list(countries) or ()),
        language="en",
        years=tuple(year for item in provenances for year in item.years),
        codebook_url=next(
            (item.codebook_url for item in provenances if item.codebook_url), None
        ),
    )
    return Dataset(
        combined,
        variables=variables_frame,
        provenance=provenance,
        meta={},
        harmonized=True,
        round_meta=round_meta,
        round_source_map=round_source_map,
    )


def citation(rounds: Any = None, countries: Any = None) -> str:
    round_list = _round_list(rounds)
    country_list = _string_list(countries) or []
    countries_text = ", ".join(country_list) if country_list else "All Countries"
    label = "Rounds" if round_list and len(round_list) > 1 else "Round"
    rounds_text = (
        ", ".join(str(number) for number in round_list)
        if round_list
        else "All Rounds"
    )
    years: list[int] = []
    if round_list:
        try:
            entries = resolve_catalog()
        except AfrobarometerError:
            entries = []
        by_round = {
            entry.round: entry.year
            for entry in entries
            if entry.kind == "merged" and entry.year is not None
        }
        years = [by_round[number] for number in round_list if number in by_round]
    parts = [f"Afrobarometer Data, {countries_text}", f"{label} {rounds_text}"]
    if years:
        parts.append(", ".join(str(year) for year in dict.fromkeys(years)))
    return ", ".join(parts) + ", available at http://www.afrobarometer.org."


def cache_dir() -> Path:
    return cache.cache_root()


def clear_cache(round: int | None = None) -> None:
    cache.clear_cache(round)
