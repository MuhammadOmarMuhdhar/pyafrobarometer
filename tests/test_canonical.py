import pandas as pd
import pytest

from pyafrobarometer.harmonize import canonical
from pyafrobarometer.harmonize.crosswalk import canonical_map


def meta_for(names):
    country_labels = {3.0: "Benin", 14.0: "Ghana"}
    return {
        "column_names": names,
        "column_labels": names,
        "variable_value_labels": {
            "COUNTRY": country_labels,
            "country": country_labels,
            "Q37A": {0.0: "No", 9.0: "DK"},
        },
        "missing_ranges": {},
    }


def test_crosswalk_verified_values():
    m = canonical_map()
    assert m["country"][1].var == "country" and m["country"][5].var == "COUNTRY_ALPHA"
    assert not m["country"][5].decode_country and m["country"][9].decode_country
    assert m["respondent_id"][1].var == "refnumb" and m["respondent_id"][2].var == "respno"
    assert m["weight"][4].var == "Withinwt" and m["weight"][8].var == "withinwt_ea"
    assert m["gender"][9].var == "Q100" and m["education"][4].var == "Q89"
    assert 1 not in m["interview_date"]


def test_apply_canonical_r1():
    df = pd.DataFrame(
        {
            "country": [3, 14],
            "refnumb": ["A", "B"],
            "area": [1, 2],
            "urbrur": [1, 2],
            "age": [30, 40],
            "gender": [1, 2],
            "educ": [3, 4],
            "withinwt": [1.0, 2.0],
        }
    )
    out, mapping = canonical.apply_canonical(
        df, round_number=1, meta=meta_for(list(df.columns))
    )
    assert out["country"].tolist() == ["Benin", "Ghana"]
    assert out["respondent_id"].tolist() == ["A", "B"]
    assert mapping["weight"] == "withinwt" and "interview_date" not in mapping


def test_apply_canonical_r9():
    df = pd.DataFrame(
        {
            "COUNTRY": [3, 14],
            "RESPNO": ["A", "B"],
            "REGION": [1, 2],
            "URBRUR": [1, 2],
            "Q1": [30, 40],
            "Q100": [1, 2],
            "Q94": [3, 4],
            "DATEINTR": ["x", "y"],
            "withinwt_ea": [1.0, 2.0],
            "Q37A": [0, 9],
        }
    )
    out, mapping = canonical.apply_canonical(
        df, round_number=9, meta=meta_for(list(df.columns))
    )
    assert out["country"].tolist() == ["Benin", "Ghana"]
    assert out["gender"].tolist() == [1, 2]
    assert out["education"].tolist() == [3, 4]
    assert out["weight"].tolist() == [1.0, 2.0]
    assert mapping["education"] == "Q94"


def test_apply_canonical_r2_lowercase_names():
    df = pd.DataFrame({"country": [3], "respno": ["A"], "q80": [30], "q96": [1]})
    out, mapping = canonical.apply_canonical(
        df, round_number=2, meta=meta_for(list(df.columns))
    )
    assert out["age"].tolist() == [30]
    assert mapping["age"] == "q80"


def test_missing_mapping_is_omitted_with_warning():
    df = pd.DataFrame({"COUNTRY": [3]})
    with pytest.warns(UserWarning):
        out, mapping = canonical.apply_canonical(
            df, round_number=9, meta=meta_for(["COUNTRY"])
        )
    assert "age" not in out.columns and "age" not in mapping
