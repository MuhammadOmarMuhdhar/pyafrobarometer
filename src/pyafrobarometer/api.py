"""High-level public API composing catalog, cache, I/O, and harmonization."""

from __future__ import annotations

import hashlib
import json
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
    HarmonizationError,
    NotFoundError,
)
from pyafrobarometer.harmonize import canonical as harmonize
from pyafrobarometer.harmonize.crosswalk import (
    canonical_map,
    family_descriptions,
    family_map,
)
from pyafrobarometer.harmonize.panel import concat_frames

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


def _remember_file(url: str, path: Path, *, sha256: str, round_number: int | None) -> None:
    state = cache.read_state()
    files = state.get("files")
    if not isinstance(files, dict):
        files = {}
    files[url] = {
        "path": str(path),
        "sha256": sha256,
        "size": path.stat().st_size,
        "round": round_number,
    }
    state["files"] = files
    cache.write_state(state)


def _download_url(url: str) -> Path:
    cached = _cached_file(url)
    if cached is not None:
        return cached
    filename = PurePosixPath(urlparse(url).path).name or "download"
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
    dest = cache.cache_file(f"files/{digest}-{filename}")
    result = fetch.download(url, dest)
    path = dest
    if filename.lower().endswith(".zip"):
        path = io.safe_extract_sav(dest, dest.parent / f"extracted-{digest}")
    _remember_file(url, path, sha256=result.sha256, round_number=None)
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
    if filename.lower().endswith(".zip"):
        path = io.safe_extract_sav(dest, dest.parent / f"extracted-{digest}")
    _remember_file(
        entry.data_url, path, sha256=result.sha256, round_number=entry.round
    )
    return path


def _country_values(frame: pd.DataFrame, meta: dict[str, Any]) -> pd.Series | None:
    for name in ("country", "COUNTRY", "COUNTRY_ALPHA"):
        if name not in frame.columns:
            continue
        if name == "COUNTRY_ALPHA":
            return frame[name]
        labels = metadata.value_labels(meta, name)
        if labels:
            return metadata.decode_column(frame[name], labels)
        return frame[name]
    return None


def _unique_countries(frame: pd.DataFrame, meta: dict[str, Any]) -> list[str]:
    keys = _country_values(frame, meta)
    if keys is None:
        return []
    values = keys.dropna().astype(str)
    return [str(value) for value in pd.unique(values)]


def _load_one(
    path: Path,
    *,
    round_number: int | None,
    variables: list[str] | None,
    countries: list[str] | None,
    harmonize_requested: bool,
    strict: bool,
) -> tuple[pd.DataFrame, dict[str, Any], dict[str, str], list[str]]:
    frame, meta = io.read_frame(path)

    if countries:
        keys = _country_values(frame, meta)
        if keys is None:
            raise HarmonizationError(
                "No country column is available to filter; load with harmonize=True"
            )
        wanted = {name.casefold() for name in countries}
        frame = frame[keys.astype(str).str.casefold().isin(wanted)]
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
        families = family_map()
        known_canonical = set(canonical_map())
        if variables is None:
            requested_families = [
                name
                for name, rounds in families.items()
                if round_number in rounds
                and rounds[round_number].var in frame.columns
            ]
        else:
            unknown = [
                name
                for name in variables
                if name not in families and name not in known_canonical
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
            requested_families = [name for name in variables if name in families]
        frame, family_sources = harmonize.apply_families(
            frame,
            round_number=round_number,
            families=requested_families,
            strict=strict,
        )
        source_map.update(family_sources)
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


def _build_variables(meta: dict[str, Any], source_map: dict[str, str]) -> pd.DataFrame:
    variables = metadata.variable_info(meta)
    variables["source_var"] = variables["name"]
    labels_by_name = dict(zip(variables["name"], variables["label"], strict=False))
    descriptions = family_descriptions()
    for output, source in source_map.items():
        mask = variables["name"] == output
        if bool(mask.any()):
            variables.loc[mask, "source_var"] = source
            continue
        row = {
            "name": output,
            "label": labels_by_name.get(source, descriptions.get(output, output)),
            "value_labels": metadata.value_labels(meta, source),
            "missing_codes": metadata.missing_codes(meta, source),
            "source_var": source,
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
                entry.country.casefold(): entry
                for entry in candidates
                if entry.kind == "country" and entry.country
            }
            if all(name.casefold() in by_country for name in country_list):
                selected.extend(
                    by_country[name.casefold()] for name in country_list
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
            "countries": None,
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


def families() -> pd.DataFrame:
    mapping = family_map()
    descriptions = family_descriptions()
    rows = [
        {
            "family": family,
            "description": descriptions.get(family, ""),
            "rounds": sorted(rounds),
            "variables": {
                round_number: item.var
                for round_number, item in sorted(rounds.items())
            },
        }
        for family, rounds in mapping.items()
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
        for entry in select_entries(
            candidates, rounds=round_list, countries=country_list
        ):
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
        if round_number is not None:
            rounds_used.append(round_number)
        country_values.extend(all_countries)

    if not frames:
        raise NotFoundError("No data matched the requested rounds and countries")
    combined = frames[0] if len(frames) == 1 else pd.concat(frames, ignore_index=True)
    meta = _merge_meta(metas)
    variable_frame = _build_variables(meta, source_map)
    provenance = Provenance(
        source_urls=tuple(source_urls),
        retrieved_at=_timestamp(),
        rounds=tuple(rounds_used),
        countries=tuple(dict.fromkeys(country_values)),
        language=language,
        years=tuple(years),
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
    provenances: list[Provenance] = []
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
        provenances.append(dataset.provenance)
    combined = concat_frames(frames, variables=variable_list)
    provenance = Provenance(
        source_urls=tuple(
            url for item in provenances for url in item.source_urls
        ),
        retrieved_at=_timestamp(),
        rounds=tuple(round_list),
        countries=tuple(_string_list(countries) or ()),
        language="en",
        years=tuple(year for item in provenances for year in item.years),
    )
    return Dataset(
        combined,
        variables=pd.DataFrame(
            columns=["name", "label", "value_labels", "missing_codes", "source_var"]
        ),
        provenance=provenance,
        meta={},
        harmonized=True,
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
    return (
        f"Afrobarometer Data, {countries_text}, {label} {rounds_text}, "
        "available at http://www.afrobarometer.org."
    )


def cache_dir() -> Path:
    return cache.cache_root()


def clear_cache(round: int | None = None) -> None:
    cache.clear_cache(round)
