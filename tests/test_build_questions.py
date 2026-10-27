import importlib.util
import json
import sys

import pandas as pd

spec = importlib.util.spec_from_file_location(
    "build_questions", "scripts/build_questions.py"
)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def row(name, label, round_number, labels, missing=None):
    return {
        "name": name,
        "label": label,
        "round": round_number,
        "kind": "question",
        "value_labels": json.dumps(labels),
        "missing_codes": [] if missing is None else missing,
    }


def test_normalize_label_strips_question_prefix_and_punctuation():
    assert mod.normalize_label("Q43A. Trust the President?") == "trust the president"
    assert mod.normalize_label("Q43a: Trust  the President") == "trust the president"


def test_slugify_strips_stopwords():
    assert mod.slugify("Trust the President") == "trust_president"
    assert mod.slugify("Attend a demonstration or protest march") == (
        "attend_demonstration_protest_march"
    )


def test_exact_groups_across_rounds_become_one_candidate():
    index = pd.DataFrame(
        [
            row("Q41A", "Trust the president", 8, {0: "No", 1: "Yes"}),
            row("Q37A", "Trust the president", 9, {0: "No", 1: "Yes"}),
        ]
    )
    candidates = mod.build_candidates(index, fuzzy_threshold=None)
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.name == "trust_president"
    assert set(candidate.rounds) == {8, 9}
    assert candidate.rounds[8]["var"] == "Q41A"
    assert candidate.rounds[9]["var"] == "Q37A"
    assert candidate.values == {0: "No", 1: "Yes"}
    assert candidate.exact is True


def test_canonical_source_variables_are_skipped():
    index = pd.DataFrame(
        [
            row("gender", "Gender", 8, {1: "Male", 2: "Female"}),
            row("gender", "Gender", 9, {1: "Male", 2: "Female"}),
            {
                "name": "gender",
                "label": "Gender",
                "round": 9,
                "kind": "canonical",
                "value_labels": "{}",
                "missing_codes": [],
            },
        ]
    )
    assert mod.build_candidates(index, fuzzy_threshold=None) == []


def test_singleton_groups_are_skipped():
    index = pd.DataFrame([row("Q1", "Only once", 9, {0: "No"})])
    assert mod.build_candidates(index, fuzzy_threshold=None) == []


def test_duplicate_slugs_get_suffix():
    index = pd.DataFrame(
        [
            row("A8", "The president", 8, {0: "No", 1: "Yes"}),
            row("A9", "The president", 9, {0: "No", 1: "Yes"}),
            row("B8", "President", 8, {0: "No", 1: "Yes"}),
            row("B9", "President", 9, {0: "No", 1: "Yes"}),
        ]
    )
    names = [c.name for c in mod.build_candidates(index, fuzzy_threshold=None)]
    assert names == ["president", "president_2"]


def test_legacy_preserves_names_and_recodes():
    index = pd.DataFrame(
        [
            row(
                "trspre",
                "Trust the president",
                1,
                {
                    1: "I do not trust them at all/Never",
                    2: "I distrust them somewhat/Sometimes",
                    3: "I trust them somewhat/Most times",
                    4: "I trust them a lot/Always",
                    9: "DK",
                },
                [9],
            ),
            row(
                "Q37A",
                "Trust the president",
                10,
                {0: "Not at all", 1: "A little", 2: "Somewhat", 3: "A lot", 9: "DK"},
                [9],
            ),
        ]
    )
    legacy = mod.legacy_from_yaml(
        {
            "families": {
                "trust_president": {
                    "rounds": {
                        1: {"var": "trspre", "recode": {"1": 0, "2": 1, "3": 2, "4": 3}},
                        10: "Q37A",
                    }
                }
            }
        }
    )
    candidates = mod.build_candidates(index, legacy)
    candidate = next(c for c in candidates if c.name == "trust_president")
    assert candidate.rounds[1]["recode"] == {1: 0, 2: 1, 3: 2, 4: 3}
    assert candidate.values is not None
    assert candidate.values[0] == "Not at all"
    assert candidate.exact is False


def test_infer_values_and_recodes_reverses_scale():
    values, recodes = mod.infer_values_and_recodes(
        {
            8: {1: "Very easy", 2: "Easy", 3: "Difficult", 4: "Very difficult"},
            9: {1: "Very difficult", 2: "Difficult", 3: "Easy", 4: "Very easy"},
        },
        {},
    )
    assert values == {
        1: "Very difficult",
        2: "Difficult",
        3: "Easy",
        4: "Very easy",
    }
    assert recodes[8] == {1: 4, 2: 3, 3: 2, 4: 1}


def test_infer_values_returns_none_for_different_code_sets():
    assert (
        mod.infer_values(
            {1: {0: "No", 1: "Yes"}, 2: {0: "No", 1: "Yes", 2: "Sometimes"}},
            {},
        )
        is None
    )


def test_infer_values_uses_latest_round_labels():
    assert mod.infer_values(
        {1: {0: "No", 1: "Yes"}, 2: {0: "No", 1: "Yes"}},
        {},
    ) == {0: "No", 1: "Yes"}


def test_missing_prefers_index_codes_and_falls_back_to_labels():
    index = pd.DataFrame(
        [
            row("Q1", "Trust", 9, {0: "No", 7: "Never tried", 9: "Don’t know"}, [7]),
            row("Q2", "Trust", 10, {0: "No", 9: "Don’t know"}, []),
        ]
    )
    candidates = mod.build_candidates(index, fuzzy_threshold=None)
    with_codes = next(c for c in candidates if c.name == "trust")
    assert with_codes.rounds[9]["missing"] == [7]
    assert with_codes.rounds[10]["missing"] == [9]


def test_fuzzy_merges_wording_variants():
    index = pd.DataFrame(
        [
            row("Q41A", "Trust the president", 8, {0: "No", 1: "Yes"}),
            row("Q37A", "Trust the president", 9, {0: "No", 1: "Yes"}),
            row("Q52A", "Trust in the president", 6, {0: "No", 1: "Yes"}),
            row("Q43A", "Trust in the president", 7, {0: "No", 1: "Yes"}),
        ]
    )
    candidates = mod.build_candidates(index)
    assert len(candidates) == 1
    assert set(candidates[0].rounds) == {6, 7, 8, 9}
    assert candidates[0].exact is False


def write_index(path, rows):
    path.write_text(json.dumps({"version": 1, "variables": rows}))


def bootstrap(tmp_path):
    index = pd.DataFrame(
        [
            row("Q41A", "Trust president", 8, {0: "No", 1: "Yes"}),
            row("Q37A", "Trust president", 9, {0: "No", 1: "Yes"}),
            row("Q7", "Economic condition", 8, {0: "Bad", 1: "Good"}),
            row(
                "Q8",
                "Economic condition",
                9,
                {0: "Bad", 1: "Good", 2: "Neither"},
            ),
        ]
    )
    index_path = tmp_path / "index.json"
    write_index(index_path, index.to_dict("records"))
    truth = tmp_path / "questions.yaml"
    proposed = tmp_path / "proposed.yaml"
    code = mod.main(
        [
            "--bootstrap",
            "--index",
            str(index_path),
            "--questions",
            str(truth),
            "--proposed",
            str(proposed),
        ]
    )
    assert code == 0
    return index_path, truth, proposed


def test_bootstrap_writes_exact_to_truth_and_ambiguous_to_proposed(tmp_path):
    import yaml

    _, truth, proposed = bootstrap(tmp_path)
    truth_data = yaml.safe_load(truth.read_text())
    proposed_data = yaml.safe_load(proposed.read_text())
    assert "trust_president" in truth_data["questions"]
    assert "economic_condition" in proposed_data["questions"]
    assert "economic_condition" not in truth_data["questions"]


def test_accept_exact_is_idempotent_and_preserves_existing(tmp_path):
    import yaml

    index_path, truth, _ = bootstrap(tmp_path)
    data = yaml.safe_load(truth.read_text())
    data["questions"]["trust_president"]["description"] = "Reviewed description"
    truth.write_text(yaml.safe_dump(data, sort_keys=False))
    for _ in range(2):
        code = mod.main(
            [
                "--accept-exact",
                "--index",
                str(index_path),
                "--questions",
                str(truth),
            ]
        )
        assert code == 0
    updated = yaml.safe_load(truth.read_text())
    assert updated["questions"]["trust_president"]["description"] == "Reviewed description"
    assert len(updated["questions"]) == len(data["questions"])


def test_accept_named_merges_one_proposal(tmp_path):
    import yaml

    index_path, truth, _proposed = bootstrap(tmp_path)
    code = mod.main(
        [
            "--accept",
            "economic_condition",
            "--index",
            str(index_path),
            "--questions",
            str(truth),
        ]
    )
    assert code == 0
    assert "economic_condition" in yaml.safe_load(truth.read_text())["questions"]


def test_validate_reports_bad_var_and_returns_one(tmp_path, capsys):
    import yaml

    index_path = tmp_path / "index.json"
    write_index(
        index_path,
        [row("Q37A", "Trust president", 9, {0: "No", 1: "Yes"})],
    )
    truth = tmp_path / "questions.yaml"
    truth.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "questions": {
                    "bad": {
                        "description": "Bad",
                        "kind": "coded",
                        "values": {0: "No"},
                        "rounds": {9: {"var": "NOPE", "label": "Bad"}},
                    }
                },
            },
            sort_keys=False,
        )
    )
    code = mod.main(
        ["--validate", "--index", str(index_path), "--questions", str(truth)]
    )
    output = capsys.readouterr()
    assert code == 1
    assert "NOPE" in output.out + output.err


def test_strict_coverage_ignores_canonical_variables(tmp_path):
    index_path = tmp_path / "index.json"
    write_index(
        index_path,
        [
            row("Q101", "Gender of respondent", 8, {1: "Male", 2: "Female"}),
            row("Q101", "Gender of respondent", 9, {1: "Male", 2: "Female"}),
            {
                "name": "Q101",
                "label": "Gender",
                "round": 9,
                "kind": "canonical",
                "value_labels": "{}",
                "missing_codes": [],
            },
        ],
    )
    truth = tmp_path / "questions.yaml"
    truth.write_text("version: 1\nquestions: {}\n")
    code = mod.main(
        [
            "--validate",
            "--strict-coverage",
            "--index",
            str(index_path),
            "--questions",
            str(truth),
        ]
    )
    assert code == 0


def test_strict_coverage_fails_unassigned_repeated_label(tmp_path):
    import yaml

    index_path = tmp_path / "index.json"
    write_index(
        index_path,
        [
            row("Q41A", "Trust president", 8, {0: "No", 1: "Yes"}),
            row("Q37A", "Trust president", 9, {0: "No", 1: "Yes"}),
        ],
    )
    truth = tmp_path / "questions.yaml"
    truth.write_text("version: 1\nquestions: {}\n")
    code = mod.main(
        [
            "--validate",
            "--strict-coverage",
            "--index",
            str(index_path),
            "--questions",
            str(truth),
        ]
    )
    assert code == 1

    truth.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "questions": {
                    "trust_president": {
                        "description": "Trust president",
                        "kind": "coded",
                        "values": {0: "No", 1: "Yes"},
                        "rounds": {
                            8: {"var": "Q41A", "label": "Trust president"},
                            9: {"var": "Q37A", "label": "Trust president"},
                        },
                    }
                },
            },
            sort_keys=False,
        )
    )
    code = mod.main(
        [
            "--validate",
            "--strict-coverage",
            "--index",
            str(index_path),
            "--questions",
            str(truth),
        ]
    )
    assert code == 0
