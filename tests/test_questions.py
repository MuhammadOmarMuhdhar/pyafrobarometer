import pandas as pd
import pytest

from pyafrobarometer.errors import HarmonizationError
from pyafrobarometer.harmonize import canonical, schema
from pyafrobarometer.harmonize.crosswalk import (
    LEGACY_QUESTIONS,
    family_map,
    family_rounds,
    question_map,
)


def test_verified_family_mappings():
    m = family_map()
    assert m["trust_president"][5].var == "Q59A"
    assert m["trust_president"][9].var == "Q37A"
    assert m["trust_president"][1].recode == {1: 0, 2: 1, 3: 2, 4: 3}
    assert m["trust_police"][7].var == "Q43G"
    assert m["satisfaction_democracy"][9].var == "Q31"
    assert m["social_media_news"][6].var == "Q12E"
    assert family_rounds("trust_courts") == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    assert family_rounds("trust_army") == [1, 2, 3, 5, 6, 7, 8, 9, 10]
    assert family_rounds("social_media_news") == [6, 7, 8, 9, 10]
    assert family_rounds("neighbours_homosexuals") == [6, 7, 8, 9, 10]


def test_apply_families():
    df = pd.DataFrame({"Q37A": [0, 3], "Q37B": [1, 2]})
    out, mapping = canonical.apply_families(
        df, round_number=9, families=["trust_president", "trust_parliament"]
    )
    assert out.columns.tolist() == [
        "Q37A",
        "Q37B",
        "trust_president",
        "trust_parliament",
    ]
    assert mapping == {"trust_president": "Q37A", "trust_parliament": "Q37B"}


def test_lowercase_source_variable_resolves():
    df = pd.DataFrame({"q43a": [0, 3]})
    out, mapping = canonical.apply_families(
        df, round_number=2, families=["trust_president"]
    )
    assert out["trust_president"].tolist() == [0, 3]
    assert mapping["trust_president"] == "q43a"


def test_r1_trust_recode():
    df = pd.DataFrame({"trspre": [1, 2, 3, 4]})
    out, mapping = canonical.apply_families(
        df, round_number=1, families=["trust_president"]
    )
    assert out["trust_president"].tolist() == [0, 1, 2, 3]
    assert mapping["trust_president"] == "trspre"


def test_missing_family_strict_raises_with_available_rounds():
    df = pd.DataFrame({"Q40": [0]})
    with pytest.raises(HarmonizationError, match="available in rounds"):
        canonical.apply_families(
            df, round_number=1, families=["satisfaction_democracy"]
        )


def test_missing_family_non_strict_adds_nan():
    df = pd.DataFrame({"Q37A": [0]})
    with pytest.warns(UserWarning):
        out, mapping = canonical.apply_families(
            df, round_number=1, families=["social_media_news"], strict=False
        )
    assert out["social_media_news"].isna().all()
    assert "social_media_news" not in mapping


def test_mapped_variable_absent_has_specific_message():
    df = pd.DataFrame({"Q40": [0]})
    with pytest.raises(HarmonizationError, match="absent"):
        canonical.apply_families(df, round_number=9, families=["trust_president"])


def test_question_map_reads_questions_section():
    q = question_map()
    assert q["trust_president"].kind == "coded"
    assert q["trust_president"].values[0] == "Not at all"
    assert q["trust_president"].rounds[2].var.lower() == "q43a"


def test_legacy_names_are_preserved():
    q = question_map()
    assert "trust_president" in q
    assert len(LEGACY_QUESTIONS) == 32


def _catalog(questions):
    return schema.parse_questions({"questions": questions})


def test_apply_questions_maps_source():
    catalog = _catalog(
        {
            "trust_president": {
                "description": "Trust",
                "kind": "coded",
                "values": {0: "No", 1: "Yes"},
                "rounds": {9: {"var": "Q37A", "label": "Trust", "missing": [-1, 9]}},
            }
        }
    )
    df = pd.DataFrame({"Q37A": [0, 1]})
    out, mapping = canonical.apply_questions(
        df, round_number=9, questions=["trust_president"], catalog=catalog
    )
    assert out["trust_president"].tolist() == [0, 1]
    assert mapping == {"trust_president": "Q37A"}


def test_apply_questions_forces_missing_na():
    catalog = _catalog(
        {
            "trust_president": {
                "description": "Trust",
                "kind": "coded",
                "values": {0: "No", 1: "Yes"},
                "rounds": {9: {"var": "Q37A", "label": "Trust", "missing": [-1, 9]}},
            }
        }
    )
    df = pd.DataFrame({"Q37A": [0, 9, -1, 1]})
    out, _ = canonical.apply_questions(
        df, round_number=9, questions=["trust_president"], catalog=catalog
    )
    values = out["trust_president"].tolist()
    assert values[0] == 0
    assert pd.isna(values[1])
    assert pd.isna(values[2])
    assert values[3] == 1


def test_apply_questions_recode_null_na():
    catalog = _catalog(
        {
            "pay_bribe": {
                "description": "Bribe",
                "kind": "coded",
                "values": {0: "Never", 1: "Once", 2: "Often"},
                "rounds": {
                    9: {
                        "var": "Q61A",
                        "label": "Bribe",
                        "recode": {1: 2, 7: None},
                        "missing": [9],
                    }
                },
            }
        }
    )
    df = pd.DataFrame({"Q61A": [0, 1, 7, 9]})
    out, _ = canonical.apply_questions(
        df, round_number=9, questions=["pay_bribe"], catalog=catalog
    )
    values = out["pay_bribe"].tolist()
    assert values[0] == 0
    assert values[1] == 2
    assert pd.isna(values[2])
    assert pd.isna(values[3])


def test_apply_questions_text_passthrough():
    catalog = _catalog(
        {
            "interviewer_comment": {
                "description": "Comment",
                "kind": "text",
                "rounds": {9: {"var": "Q1TEXT", "label": "Comment"}},
            }
        }
    )
    df = pd.DataFrame({"Q1TEXT": ["hello", "world"]})
    out, mapping = canonical.apply_questions(
        df, round_number=9, questions=["interviewer_comment"], catalog=catalog
    )
    assert out["interviewer_comment"].tolist() == ["hello", "world"]
    assert mapping == {"interviewer_comment": "Q1TEXT"}


def test_apply_questions_excluded_round():
    catalog = _catalog(
        {
            "close_political_party": {
                "description": "Closeness",
                "kind": "coded",
                "values": {0: "No", 1: "Yes"},
                "rounds": {
                    2: {"exclude": True, "reason": "records party name"},
                    3: {"var": "Q85", "label": "Closeness"},
                },
            }
        }
    )
    df = pd.DataFrame({"Q85": [0]})
    with pytest.raises(HarmonizationError, match="records party name"):
        canonical.apply_questions(
            df, round_number=2, questions=["close_political_party"], catalog=catalog
        )
    with pytest.warns(UserWarning, match="records party name"):
        out, mapping = canonical.apply_questions(
            df,
            round_number=2,
            questions=["close_political_party"],
            catalog=catalog,
            strict=False,
        )
    assert out["close_political_party"].isna().all()
    assert "close_political_party" not in mapping


def test_apply_questions_lowercase_source():
    catalog = _catalog(
        {
            "trust_president": {
                "description": "Trust",
                "kind": "coded",
                "values": {0: "No", 1: "Yes"},
                "rounds": {2: {"var": "Q43A", "label": "Trust"}},
            }
        }
    )
    df = pd.DataFrame({"q43a": [0, 3]})
    out, mapping = canonical.apply_questions(
        df, round_number=2, questions=["trust_president"], catalog=catalog
    )
    assert out["trust_president"].tolist() == [0, 3]
    assert mapping["trust_president"] == "q43a"
