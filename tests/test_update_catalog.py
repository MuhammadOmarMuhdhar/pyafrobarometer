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


def test_index_records_tag_concept_and_legacy_family():
    records = mod._index_records(
        {
            "column_names": ["Q37A", "Q35B"],
            "column_names_to_labels": {
                "Q37A": "Trust president",
                "Q35B": "Access information",
            },
            "variable_value_labels": {"Q37A": {0: "No"}, "Q35B": {0: "No"}},
            "missing_ranges": {},
        },
        9,
    )
    by_name = {record["name"]: record for record in records}
    assert by_name["Q37A"]["concept"] == "trust_president"
    assert by_name["Q37A"]["family"] == "trust_president"
    assert (
        by_name["Q35B"]["concept"]
        == "access_information_local_government_development_plan_budget"
    )
    assert by_name["Q35B"]["family"] is None


def test_index_records_tag_canonical_concept():
    records = mod._index_records(
        {
            "column_names": ["COUNTRY"],
            "column_names_to_labels": {"COUNTRY": "Country"},
            "variable_value_labels": {"COUNTRY": {3: "Benin"}},
            "missing_ranges": {},
        },
        9,
    )
    assert records[0]["kind"] == "canonical"
    assert records[0]["concept"] == "country"
    assert records[0]["source_var"] == "country"
    assert records[0]["family"] is None


def test_validate_crosswalk_reports_missing_non_legacy_question():
    from pyafrobarometer.harmonize.crosswalk import canonical_map, question_map

    names = set()
    for rounds in canonical_map().values():
        spec = rounds.get(9)
        if spec is not None:
            names.add(spec.var)
    for question in question_map().values():
        entry = question.rounds.get(9)
        if entry is not None and not entry.exclude and entry.var:
            names.add(entry.var)
    names.discard("Q35B")
    problems = mod.validate_crosswalk({"column_names": sorted(names)}, 9)
    assert any(
        "access_information_local_government_development_plan_budget" in problem
        for problem in problems
    )


def test_validate_crosswalk_accepts_lowercase_r2_sources():
    from pyafrobarometer.harmonize.crosswalk import canonical_map, question_map

    names = set()
    for rounds in canonical_map().values():
        spec = rounds.get(2)
        if spec is not None:
            names.add(spec.var.lower())
    for question in question_map().values():
        entry = question.rounds.get(2)
        if entry is not None and not entry.exclude and entry.var:
            names.add(entry.var.lower())
    assert mod.validate_crosswalk({"column_names": sorted(names)}, 2) == []


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
