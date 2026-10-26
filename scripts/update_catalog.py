#!/usr/bin/env python3
"""Refresh the baked Afrobarometer catalog manifest and metadata index."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Any

from pyafrobarometer import api, fetch, io, metadata
from pyafrobarometer.catalog import CatalogEntry, resolve_catalog
from pyafrobarometer.errors import DownloadError
from pyafrobarometer.harmonize.crosswalk import canonical_map, family_map

PACKAGE_DIR = Path(__file__).resolve().parents[1] / "src" / "pyafrobarometer"
MANIFEST_PATH = PACKAGE_DIR / "manifest.json"
METADATA_INDEX_PATH = PACKAGE_DIR / "metadata_index.json"


def manifest_payload(entries: Sequence[CatalogEntry]) -> dict[str, Any]:
    ordered = sorted(
        entries, key=lambda item: (item.round, item.kind, item.country or "", item.language)
    )
    return {
        "version": 1,
        "generated_at": date.today().isoformat(),
        "entries": [asdict(item) for item in ordered],
    }


def merge_metadata_index(
    existing: Mapping[str, Any], new: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    variables = existing.get("variables")
    kept = [
        item
        for item in (variables if isinstance(variables, list) else [])
        if item.get("round") not in {entry.get("round") for entry in new}
    ]
    version = existing.get("version", 1)
    return {
        "version": int(version) if isinstance(version, int) else 1,
        "variables": kept + list(new),
    }


def validate_links(
    entries: Sequence[CatalogEntry], *, head: Any = None
) -> list[str]:
    probe = head or fetch.http_head
    problems: list[str] = []
    for entry in entries:
        for url in (entry.data_url, entry.codebook_url):
            if not url:
                continue
            try:
                response = probe(url)
            except (DownloadError, OSError) as exc:
                problems.append(f"{url} could not be reached: {exc}")
                continue
            status = getattr(response, "status_code", 0)
            if status != 200:
                problems.append(f"{url} returned HTTP {status}")
    return problems


def validate_crosswalk(meta: Mapping[str, Any], round_number: int) -> list[str]:
    names = {str(name).casefold() for name in meta.get("column_names") or []}
    problems: list[str] = []
    for canonical, rounds in canonical_map().items():
        spec = rounds.get(round_number)
        if spec is not None and spec.var.casefold() not in names:
            problems.append(
                f"canonical {canonical} expects {spec.var} in round {round_number}"
            )
    for family, rounds in family_map().items():
        spec = rounds.get(round_number)
        if spec is not None and spec.var.casefold() not in names:
            problems.append(
                f"family {family} expects {spec.var} in round {round_number}"
            )
    return problems


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=".update-", suffix=".json")
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True, ensure_ascii=False)
            handle.write("\n")
        os.replace(tmp, path)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise


def _index_records(
    meta: Mapping[str, Any], round_number: int
) -> list[dict[str, Any]]:
    canonical_sources: dict[str, str] = {}
    for canonical, rounds in canonical_map().items():
        spec = rounds.get(round_number)
        if spec is not None:
            canonical_sources[spec.var] = canonical
    families_by_var: dict[str, str] = {}
    for family, rounds in family_map().items():
        spec = rounds.get(round_number)
        if spec is not None:
            families_by_var[spec.var] = family

    records: list[dict[str, Any]] = []
    for item in metadata.variable_info(dict(meta)).to_dict("records"):
        name = str(item["name"])
        kind = "canonical" if name in canonical_sources else "question"
        records.append(
            {
                "name": name,
                "label": str(item["label"]),
                "round": round_number,
                "kind": kind,
                "family": families_by_var.get(name),
                "concept": None,
                "source_var": canonical_sources.get(name) if kind == "canonical" else None,
                "value_labels": json.dumps(item["value_labels"], ensure_ascii=False),
                "missing_codes": list(item["missing_codes"]),
            }
        )
    return records


def _metadata_rounds(value: str | None, entries: Sequence[CatalogEntry]) -> list[int]:
    available = sorted({item.round for item in entries if item.kind == "merged"})
    if not available:
        return []
    if value is None:
        return available
    if value == "all":
        return available
    return [int(part) for part in value.split(",") if part.strip()]


def _load_metadata(entries: Sequence[CatalogEntry], round_number: int) -> dict[str, Any] | None:
    candidate = next(
        (
            item
            for item in entries
            if item.kind == "merged"
            and item.round == round_number
            and item.language == "en"
        ),
        None,
    )
    if candidate is None:
        return None
    path = api._download_entry(candidate)
    return io.read_metadata(path)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write manifest and index")
    parser.add_argument("--validate", action="store_true", help="validate links and mappings")
    parser.add_argument(
        "--metadata-rounds",
        default=None,
        help="'all', a comma-separated list of rounds, or the latest round by default",
    )
    args = parser.parse_args(argv)

    entries = resolve_catalog(refresh=True)
    problems: list[str] = []
    if args.validate:
        problems.extend(validate_links(entries))

    metas: dict[int, dict[str, Any]] = {}
    metadata_rounds = _metadata_rounds(args.metadata_rounds, entries)
    if args.write or args.validate:
        for round_number in metadata_rounds:
            meta = _load_metadata(entries, round_number)
            if meta is None:
                problems.append(f"no merged entry for round {round_number}")
                continue
            metas[round_number] = meta
            if args.validate:
                problems.extend(validate_crosswalk(meta, round_number))

    if args.write:
        _write_json(MANIFEST_PATH, manifest_payload(entries))
        if METADATA_INDEX_PATH.exists():
            existing = json.loads(METADATA_INDEX_PATH.read_text(encoding="utf-8"))
        else:
            existing = {"version": 1, "variables": []}
        new_records: list[dict[str, Any]] = []
        for round_number, meta in metas.items():
            new_records.extend(_index_records(meta, round_number))
        _write_json(METADATA_INDEX_PATH, merge_metadata_index(existing, new_records))

    for problem in problems:
        print(problem)
    print(
        f"catalog entries: {len(entries)}; metadata rounds: {metadata_rounds}; "
        f"problems: {len(problems)}"
    )
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
