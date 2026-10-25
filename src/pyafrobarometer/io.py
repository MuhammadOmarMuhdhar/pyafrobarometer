"""SPSS and zip I/O with traversal protection."""

from __future__ import annotations

import zipfile
from collections.abc import Sequence
from pathlib import Path, PurePosixPath
from typing import Any

import pandas as pd
import pyreadstat

from pyafrobarometer.errors import CacheError


def safe_extract_sav(archive: Path, dest_dir: Path) -> Path:
    dest = dest_dir.resolve()
    dest.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(archive) as bundle:
            candidates: list[zipfile.ZipInfo] = []
            for member in bundle.infolist():
                parts = PurePosixPath(member.filename).parts
                if any(part == "__MACOSX" or part.startswith("._") for part in parts):
                    continue
                if member.is_dir() or not member.filename.lower().endswith(".sav"):
                    continue
                target = (dest / member.filename).resolve()
                if not target.is_relative_to(dest):
                    continue
                candidates.append(member)
            if len(candidates) != 1:
                raise CacheError(
                    f"Expected exactly one .sav member in {archive}, found {len(candidates)}"
                )
            member = candidates[0]
            bundle.extract(member, dest)
            return (dest / member.filename).resolve()
    except zipfile.BadZipFile as exc:
        raise CacheError(f"{archive} is not a valid zip archive: {exc}") from exc


def read_metadata(path: Path) -> dict[str, Any]:
    _, meta = pyreadstat.read_sav(str(path), metadataonly=True)
    return dict(vars(meta))


def read_frame(
    path: Path,
    *,
    usecols: Sequence[str] | None = None,
    apply_value_labels: bool = False,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    frame, meta = pyreadstat.read_sav(
        str(path),
        usecols=list(usecols) if usecols else None,
        apply_value_formats=apply_value_labels,
    )
    return frame, dict(vars(meta))
