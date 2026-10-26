import json

import pandas as pd
import pytest

from pyafrobarometer.errors import HarmonizationError
from pyafrobarometer.harmonize import schema

INDEX = pd.DataFrame(
    [
        {
            "name": "Q37A",
            "round": 9,
            "kind": "question",
            "value_labels": json.dumps({"0": "Not at all", "3": "A lot", "9": "DK"}),
        },
        {
            "name": "q43a",
            "round": 2,
            "kind": "question",
            "value_labels": json.dumps({"0": "Not at all", "3": "A lot", "9": "DK"}),
        },
        {
            "name": "COUNTRY",
            "round": 9,
            "kind": "canonical",
            "value_labels": json.dumps({"3": "Benin"}),
        },
    ]
)


def payload():
    return {
        "version": 1,
        "questions": {
            "trust_president": {
                "description": "Trust in the President",
                "kind": "coded",
                "values": {0: "Not at all", 3: "A lot"},
                "rounds": {
                    9: {
                        "var": "Q37A",
                        "label": "Trust the president",
                        "recode": {0: 0, 3: 3},
                        "missing": [9],
                    },
                    2: {"var": "q43a", "label": "Trust the president", "missing": [9]},
                },
            },
            "interview_date": {
                "description": "Interview date",
                "kind": "text",
                "rounds": {9: {"var": "DATEINTR", "label": "Interview date"}},
            },
        },
    }


def test_parse_minimal_concept():
    questions = schema.parse_questions(payload())
    trust = questions["trust_president"]
    assert trust.kind == "coded"
    assert trust.values == {0: "Not at all", 3: "A lot"}
    assert trust.rounds[9].var == "Q37A"
    assert trust.rounds[9].recode == {0: 0, 3: 3}
    assert trust.rounds[9].missing == (9,)


def test_parse_text_concept():
    questions = schema.parse_questions(payload())
    assert questions["interview_date"].kind == "text"
    assert questions["interview_date"].values == {}


def test_validate_coded_requires_values():
    data = payload()
    del data["questions"]["trust_president"]["values"]
    questions = schema.parse_questions(data)
    assert any("values" in problem for problem in schema.validate_questions(questions))


def test_validate_text_rejects_recode():
    data = payload()
    data["questions"]["interview_date"]["rounds"][9]["recode"] = {1: 2}
    questions = schema.parse_questions(data)
    assert any("text" in problem for problem in schema.validate_questions(questions))


def test_validate_bad_recode_target():
    data = payload()
    data["questions"]["trust_president"]["rounds"][9]["recode"] = {0: 7}
    questions = schema.parse_questions(data)
    assert any("recode" in problem for problem in schema.validate_questions(questions))


def test_validate_uncovered_native_code():
    data = payload()
    data["questions"]["trust_president"]["rounds"][9]["recode"] = {0: 0}
    index = INDEX.copy()
    index.loc[index["name"] == "Q37A", "value_labels"] = json.dumps(
        {"0": "Not at all", "2": "Somewhat", "3": "A lot", "9": "DK"}
    )
    questions = schema.parse_questions(data)
    problems = schema.validate_questions(questions, index)
    assert any("uncovered" in problem for problem in problems)


def test_validate_exclude_requires_reason():
    data = payload()
    data["questions"]["trust_president"]["rounds"][9] = {"exclude": True}
    questions = schema.parse_questions(data)
    assert any("reason" in problem for problem in schema.validate_questions(questions))


def test_validate_duplicate_source_variable():
    data = payload()
    data["questions"]["other"] = {
        "description": "Other",
        "kind": "coded",
        "values": {0: "No", 1: "Yes"},
        "rounds": {9: {"var": "q37a", "label": "Other"}},
    }
    questions = schema.parse_questions(data)
    problems = schema.validate_questions(questions, INDEX)
    assert any("assigned to more than one" in problem for problem in problems)


def test_validate_missing_recode_overlap():
    data = payload()
    data["questions"]["trust_president"]["rounds"][9]["recode"] = {0: 0, 3: 3, 9: 0}
    questions = schema.parse_questions(data)
    assert any("missing" in problem for problem in schema.validate_questions(questions))


def test_validate_collision_with_raw_and_canonical():
    data = payload()
    data["questions"]["q37a"] = {
        "description": "Collision",
        "kind": "coded",
        "values": {0: "No", 1: "Yes"},
        "rounds": {9: {"var": "Q37A", "label": "Collision"}},
    }
    data["questions"]["country"] = {
        "description": "Collision",
        "kind": "coded",
        "values": {0: "No", 1: "Yes"},
        "rounds": {9: {"var": "COUNTRY", "label": "Collision"}},
    }
    questions = schema.parse_questions(data)
    problems = schema.validate_questions(questions, INDEX)
    assert any("collides" in problem for problem in problems)


def test_validate_var_absent_from_round():
    data = payload()
    data["questions"]["trust_president"]["rounds"][9]["var"] = "Q99"
    questions = schema.parse_questions(data)
    problems = schema.validate_questions(questions, INDEX)
    assert any("Q99" in problem for problem in problems)


def test_resolve_column_case_insensitive():
    assert schema.resolve_column("Q37A", ["Q37A", "Q1"]) == "Q37A"
    assert schema.resolve_column("q43a", ["Q43A", "Q1"]) == "Q43A"


def test_resolve_column_absent_returns_none():
    assert schema.resolve_column("Q99", ["Q37A"]) is None


def test_resolve_column_ambiguous_raises():
    with pytest.raises(HarmonizationError):
        schema.resolve_column("Q37A", ["Q37A", "q37a"])
