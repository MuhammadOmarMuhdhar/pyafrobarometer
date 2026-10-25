import pandas as pd

from pyafrobarometer import metadata

META = {
    "column_names": ["COUNTRY", "Q37A", "Q1"],
    "column_labels": ["Country", "Trust president", "Age"],
    "variable_value_labels": {
        "COUNTRY": {3.0: "Benin", 9.0: "Côte d'Ivoire"},
        "Q37A": {
            0.0: "Not at all",
            3.0: "A lot",
            8.0: "Refused",
            9.0: "Don't know",
            -1.0: "Missing",
        },
    },
    "missing_ranges": {"Q37A": {"lo": 8.0, "hi": 9.0}},
}


def test_variable_info():
    info = metadata.variable_info(META)
    assert list(info.columns) == ["name", "label", "value_labels", "missing_codes"]
    assert info.loc[info.name == "Q37A", "label"].item() == "Trust president"


def test_missing_codes_merges_metadata_and_fallback():
    codes = metadata.missing_codes(META, "Q37A")
    assert {8, 9, -1}.issubset(codes)
    assert 0 not in codes and 3 not in codes


def test_normalize_missing():
    df = pd.DataFrame({"Q37A": [0, 8, 9, -1]})
    out = metadata.normalize_missing(df, META, ["Q37A"])
    assert out["Q37A"].isna().tolist() == [False, True, True, True]


def test_decode_column_keeps_unknown_codes():
    out = metadata.decode_column(
        pd.Series([3, 9]), META["variable_value_labels"]["COUNTRY"]
    )
    assert out.tolist() == ["Benin", "Côte d'Ivoire"]


def test_country_codes_are_not_treated_as_missing():
    meta = {
        "column_names": ["COUNTRY", "Q37A"],
        "column_labels": ["Country", "Trust"],
        "variable_value_labels": {
            "COUNTRY": {8.0: "Cabo Verde", 9.0: "Côte d'Ivoire"},
            "Q37A": {8.0: "Refused", 9.0: "Don't know", -1.0: "Missing"},
        },
        "missing_ranges": {},
    }
    assert 8 not in metadata.missing_codes(meta, "COUNTRY")
    assert 9 not in metadata.missing_codes(meta, "COUNTRY")
    df = pd.DataFrame({"COUNTRY": [8, 9], "Q37A": [8, 9]})
    out = metadata.normalize_missing(df, meta)
    assert out["COUNTRY"].tolist() == [8, 9]
    assert out["Q37A"].isna().tolist() == [True, True]
