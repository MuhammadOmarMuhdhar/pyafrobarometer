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


def test_duplicate_slugs_get_suffix():
    index = pd.DataFrame(
        [
            row("A", "The president", 9, {0: "No", 1: "Yes"}),
            row("B", "President", 10, {0: "No", 1: "Yes"}),
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
            row("Q37A", "Trust in the president", 9, {0: "No", 1: "Yes"}),
        ]
    )
    candidates = mod.build_candidates(index)
    assert len(candidates) == 1
    assert set(candidates[0].rounds) == {8, 9}
    assert candidates[0].exact is False
