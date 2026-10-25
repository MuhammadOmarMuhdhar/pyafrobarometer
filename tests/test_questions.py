import pandas as pd
import pytest

from pyafrobarometer.errors import HarmonizationError
from pyafrobarometer.harmonize import canonical
from pyafrobarometer.harmonize.crosswalk import family_map, family_rounds


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
