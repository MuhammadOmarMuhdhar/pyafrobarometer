"""The Dataset wrapper and its provenance record."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import pandas as pd

from pyafrobarometer import metadata
from pyafrobarometer.errors import CodebookError, HarmonizationError


@dataclass(frozen=True)
class Provenance:
    source_urls: tuple[str, ...]
    retrieved_at: str
    rounds: tuple[int, ...]
    countries: tuple[str, ...]
    language: str
    years: tuple[int, ...] = field(default_factory=tuple)
    codebook_url: str | None = None
    codebook_path: Path | None = None


class Dataset:
    def __init__(
        self,
        df: pd.DataFrame,
        *,
        variables: pd.DataFrame,
        provenance: Provenance,
        meta: dict[str, Any],
        source_map: dict[str, str] | None = None,
        harmonized: bool = False,
        round_meta: dict[int, dict[str, Any]] | None = None,
        round_source_map: dict[int, dict[str, str]] | None = None,
    ) -> None:
        self._df = df
        self._variables = variables.copy()
        self.provenance = provenance
        self._meta = dict(meta)
        self._source_map = dict(source_map or {})
        self.harmonized = harmonized
        self._round_meta = dict(round_meta or {})
        self._round_source_map = dict(round_source_map or {})

    @property
    def rounds(self) -> list[int]:
        return list(self.provenance.rounds)

    @property
    def countries(self) -> list[str]:
        return list(self.provenance.countries)

    @property
    def round_meta(self) -> dict[int, dict[str, Any]]:
        return {round_number: dict(meta) for round_number, meta in self._round_meta.items()}

    @property
    def round_source_map(self) -> dict[int, dict[str, str]]:
        return {
            round_number: dict(mapping)
            for round_number, mapping in self._round_source_map.items()
        }

    def variables(self) -> pd.DataFrame:
        return cast(pd.DataFrame, self._variables.copy())

    def _source(self, column: str) -> str:
        return self._source_map.get(column, column)

    def to_pandas(
        self,
        labels: bool = False,
        normalize_missing: bool = False,
    ) -> pd.DataFrame:
        frame = self._df.copy()
        if self._round_meta and "round" in frame.columns:
            for column in frame.columns:
                result = frame[column].astype(object)
                for round_number, meta in self._round_meta.items():
                    mask = frame["round"] == round_number
                    if not bool(mask.any()):
                        continue
                    sources = self._round_source_map.get(
                        round_number, self._source_map
                    )
                    source = sources.get(str(column), str(column))
                    series = frame.loc[mask, column]
                    if normalize_missing:
                        codes = metadata.missing_codes(meta, source)
                        if codes:
                            series = series.where(~series.isin(codes), pd.NA)
                    if labels:
                        mapping = metadata.value_labels(meta, source)
                        if mapping:
                            series = metadata.decode_column(series, mapping)
                    result.loc[mask] = series.tolist()
                frame[column] = result
            return cast(pd.DataFrame, frame)
        for column in frame.columns:
            source = self._source(str(column))
            if normalize_missing:
                codes = metadata.missing_codes(self._meta, source)
                if codes:
                    frame[column] = frame[column].where(~frame[column].isin(codes), pd.NA)
            if labels:
                mapping = metadata.value_labels(self._meta, source)
                if mapping:
                    frame[column] = metadata.decode_column(frame[column], mapping)
        return cast(pd.DataFrame, frame)

    def subset(
        self,
        countries: str | list[str] | None = None,
        columns: str | list[str] | None = None,
    ) -> Dataset:
        frame = self._df.copy()
        if countries is not None:
            wanted = [countries] if isinstance(countries, str) else list(countries)
            lowered = {name.casefold() for name in wanted}
            if "country" in frame.columns:
                keys = frame["country"]
            elif "COUNTRY" in frame.columns:
                keys = metadata.decode_column(
                    frame["COUNTRY"], metadata.value_labels(self._meta, "COUNTRY")
                )
            else:
                raise HarmonizationError(
                    "No country column is available; load with harmonize=True to filter countries"
                )
            frame = frame[keys.astype(str).str.casefold().isin(lowered)]
        if columns is not None:
            selected = [columns] if isinstance(columns, str) else list(columns)
            frame = frame[selected]
        return Dataset(
            frame,
            variables=self._variables,
            provenance=self.provenance,
            meta=self._meta,
            source_map=self._source_map,
            harmonized=self.harmonized,
            round_meta=self._round_meta,
            round_source_map=self._round_source_map,
        )

    def citation(self) -> str:
        countries = ", ".join(self.countries) if self.countries else "All Countries"
        rounds = ", ".join(str(number) for number in self.rounds)
        label = "Rounds" if len(self.rounds) > 1 else "Round"
        parts = [f"Afrobarometer Data, {countries}", f"{label} {rounds}"]
        if self.provenance.years:
            parts.append(", ".join(str(year) for year in self.provenance.years))
        return ", ".join(parts) + ", available at http://www.afrobarometer.org."

    def codebook(self) -> Path:
        if self.provenance.codebook_path is not None:
            return Path(self.provenance.codebook_path)
        if self.provenance.codebook_url:
            from pyafrobarometer.codebook import download_codebook

            return download_codebook(self.provenance.codebook_url)
        raise CodebookError("No codebook is available for this dataset")

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        try:
            return getattr(self._df, name)
        except AttributeError as exc:
            raise AttributeError(f"Dataset has no attribute {name!r}") from exc

    def __getitem__(self, key: Any) -> Any:
        return self._df[key]

    def __len__(self) -> int:
        return len(self._df)

    def __iter__(self) -> Any:
        return iter(self._df.columns)

    def __repr__(self) -> str:
        return (
            f"<Dataset rounds={self.rounds} rows={len(self._df)} "
            f"columns={len(self._df.columns)} harmonized={self.harmonized}>"
        )
