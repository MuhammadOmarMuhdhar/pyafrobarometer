import importlib.util

from pyafrobarometer.catalog import CatalogEntry

spec = importlib.util.spec_from_file_location(
    "update_catalog", "scripts/update_catalog.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def entry(**kw):
    base = {
        "kind": "merged",
        "round": 10,
        "country": None,
        "year": 2025,
        "language": "en",
        "data_url": "https://www.afrobarometer.org/x.sav",
        "codebook_url": None,
        "page_url": "https://www.afrobarometer.org/p",
        "filename": "x.sav",
        "size_bytes": None,
    }
    base.update(kw)
    return CatalogEntry(**base)


def test_manifest_payload_roundtrip():
    payload = mod.manifest_payload([entry()])
    assert payload["version"] == 1 and payload["entries"][0]["round"] == 10


def test_merge_metadata_index_replaces_same_round():
    existing = {"version": 1, "variables": [{"name": "Q1", "round": 9}]}
    new = [{"name": "Q1", "round": 10}, {"name": "Q2", "round": 10}]
    out = mod.merge_metadata_index(existing, new)
    assert [v["round"] for v in out["variables"]] == [9, 10, 10]


def test_index_records_include_missing_codes():
    records = mod._index_records(
        {
            "column_names": ["Q37A"],
            "column_names_to_labels": {"Q37A": "Trust president"},
            "variable_value_labels": {"Q37A": {9: "Don’t know"}},
            "missing_ranges": {},
        },
        9,
    )
    assert records[0]["missing_codes"] == [9]
    assert "concept" in records[0]


def test_validate_links_reports_non_200(monkeypatch):
    class R:
        status_code = 404

    problems = mod.validate_links([entry()], head=lambda *a, **k: R())
    assert problems and "404" in problems[0]


def test_validate_crosswalk_reports_missing_variable():
    from pyafrobarometer.harmonize.crosswalk import canonical_map, family_map

    names = {m[5].var for m in canonical_map().values() if 5 in m}
    names |= {m[5].var for m in family_map().values() if 5 in m}
    meta = {"column_names": sorted(names)}
    assert mod.validate_crosswalk(meta, 5) == []
    meta["column_names"].remove("Q59A")
    assert any("trust_president" in p for p in mod.validate_crosswalk(meta, 5))
